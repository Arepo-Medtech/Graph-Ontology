#!/usr/bin/env python3
"""An evaluator for the subset of SNOMED CT Expression Constraint Language the edition database can answer offline.

Runs an ECL expression against one edition in out/snomed_editions.duckdb (scripts/snomed_editions.py) and returns the
matching concept ids -- what a terminology server's `ValueSet/$expand` would return for that edition. The subset is
the one actually used by the 2,500 expansions data-golf-2026 cached from the live server, each of which `check`
replays against this evaluator; anything outside it raises rather than guessing.

    <<X  <X  >>X  >X  <!X  >!X  X  *          descendants-or-self, descendants, ancestors-or-self, ancestors, children, parents
    ^R                                        members of a simple reference set
    A AND B   A OR B   A MINUS B   ( ... )     set algebra (one operator per level; parenthesise to mix)
    F : a = v , b = w                         refinement: a concept of F with an active relationship a -> v (and b -> w)
    F : { a = v , b = w }                     ... both in the same relationship group
    F : ( a = v OR b = w )                    ... either
    a may be ID, <<ID or * ; v may be ID, <<ID, *, or ( expression )
    F . a                                     dotted: the values of attribute a over F
    F {{ term = "words" }}                    term filter: every word is a case-insensitive prefix of a word of an active
    F {{ term = ("w1" "w2") }}                FSN or synonym (any of the strings)

Server semantics reproduced on purpose: `<<X` and `>>X` include X even when X is inactive (the server returns the
focus concept as given); descendants, ancestors and refinement values are active concepts only; the attribute
wildcard `*` matches any attribute type *except* is-a.

Every intermediate set lives in a DuckDB temp table, so a 200,000-concept focus refined by an attribute is one join,
not a Python loop; `Evaluator.expand` returns a Python set of ints.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

IS_A = 116680003
DESCRIPTION_TYPES = {"fsn": 900000000000003001, "synonym": 900000000000013009, "definition": 900000000000550004}

TOKEN = re.compile(r"""\s*(?:
    (?P<str>"[^"]*")        |
    (?P<num>\d+)            |
    (?P<kw>AND|OR|MINUS|term|match)\b |
    (?P<op><<|>>|<!|>!|<|>|\{\{|\}\}|[(){}:,.=^*!])
)""", re.X | re.I)


def tokenize(s: str) -> list[tuple[str, str]]:
    out, i = [], 0
    while i < len(s):
        m = TOKEN.match(s, i)
        if not m:
            if s[i:].strip() == "":
                break
            raise SyntaxError(f"cannot tokenise ECL at {s[i:i + 30]!r}")
        i = m.end()
        kind = m.lastgroup
        out.append((kind, m.group(kind).upper() if kind == "kw" else m.group(kind)))
    return out


# ----------------------------------------------------------------------------------------------------- AST
@dataclass
class Focus:                    # <<X, X, *, ^R
    op: str                     # '', '<<', '<', '>>', '>', '<!', '>!', '^', '*'
    code: int | None


@dataclass
class Nested:
    expr: "Node"
    op: str = ""                # a constraint operator applied to a parenthesised expression: <<(expr)


@dataclass
class Bool:
    op: str
    left: "Node"
    right: "Node"


@dataclass
class Attr:                     # a = v
    name_op: str                # '', '<<', '*'
    name: int | None
    value: "Node | str"         # Node, or '*'
    negate: bool = False


@dataclass
class Refinement:               # conjunction of attribute conditions and groups, with OR inside parentheses
    op: str                     # 'AND' | 'OR'
    parts: list                 # Attr | Group | Refinement


@dataclass
class Group:
    attrs: list                 # Attr, all in one relationship group


@dataclass
class Refined:
    focus: "Node"
    refinement: Refinement


@dataclass
class Dotted:
    expr: "Node"
    attr: Attr                  # only name_op / name used


@dataclass
class TermFilter:
    expr: "Node"
    terms: list[str] = field(default_factory=list)


Node = "Focus | Nested | Bool | Refined | Dotted | TermFilter"


class Parser:
    def __init__(self, s: str):
        self.t = tokenize(s)
        self.i = 0

    def peek(self, *want):
        if self.i < len(self.t) and self.t[self.i][1] in want:
            return self.t[self.i][1]
        return None

    def take(self, *want):
        if self.i >= len(self.t):
            raise SyntaxError(f"unexpected end of ECL, wanted {want}")
        k, v = self.t[self.i]
        if want and v not in want:
            raise SyntaxError(f"wanted {want} at token {self.i}, got {v!r}")
        self.i += 1
        return v

    def parse(self) -> Node:
        n = self.expr()
        if self.i != len(self.t):
            raise SyntaxError(f"trailing tokens from {self.t[self.i]}")
        return n

    def expr(self) -> Node:
        left = self.sub()
        while self.peek("AND", "OR", "MINUS"):
            op = self.take()
            left = Bool(op, left, self.sub(refine=False))
        # the server binds an unparenthesised refinement to the whole compound: `<<A OR <<B : a = v` is
        # `(<<A OR <<B) : a = v`, not `<<A OR (<<B : a = v)` -- measured against its cached expansions
        if isinstance(left, Bool) and self.peek(":"):
            self.take(":")
            left = Refined(left, self.refinement())
        return left

    def sub(self, refine: bool = True) -> Node:
        n = self.refined() if refine else self.simple()
        while self.peek("{{"):
            self.take("{{")
            kw = self.take("TERM", "MATCH")
            self.take("=")
            terms = []
            if self.peek("("):
                self.take("(")
                while not self.peek(")"):
                    terms.append(self.string())
                self.take(")")
            else:
                terms.append(self.string())
            self.take("}}")
            n = TermFilter(n, terms)
        while self.peek("."):
            self.take(".")
            n = Dotted(n, self.attr_name())
        return n

    def string(self) -> str:
        k, v = self.t[self.i]
        if k != "str":
            raise SyntaxError(f"wanted a string at token {self.i}, got {v!r}")
        self.i += 1
        s = v[1:-1]
        return s.split(":", 1)[1] if s.lower().startswith("match:") else s

    def refined(self) -> Node:
        f = self.simple()
        if self.peek(":"):
            self.take(":")
            return Refined(f, self.refinement())
        return f

    def simple(self) -> Node:
        op = ""
        if self.peek("<<", "<", ">>", ">", "<!", ">!"):
            op = self.take()
        if self.peek("("):
            self.take("(")
            inner = self.expr()
            self.take(")")
            return Nested(inner, op) if op else inner
        if self.peek("^"):
            self.take("^")
            members = Focus("^", int(self.take()))
            return Nested(members, op) if op else members
        if self.peek("*"):
            self.take("*")
            return Focus("*", None)
        return Focus(op, int(self.take()))

    def refinement(self) -> Refinement:
        parts = [self.ref_part()]
        op = "AND"
        while self.peek(",", "AND", "OR"):
            o = self.take()
            o = "AND" if o == "," else o
            if o != op and len(parts) > 1:
                raise SyntaxError("mixed AND/OR in one refinement level; parenthesise")
            op = o
            parts.append(self.ref_part())
        return Refinement(op, parts)

    def ref_part(self):
        if self.peek("("):
            self.take("(")
            r = self.refinement()
            self.take(")")
            return r
        if self.peek("{"):
            self.take("{")
            attrs = [self.attr()]
            while self.peek(","):
                self.take(",")
                attrs.append(self.attr())
            self.take("}")
            return Group(attrs)
        return self.attr()

    def attr_name(self) -> Attr:
        if self.peek("*"):
            self.take("*")
            return Attr("*", None, "*")
        op = self.take() if self.peek("<<", "<") else ""
        return Attr(op, int(self.take()), "*")

    def attr(self) -> Attr:
        a = self.attr_name()
        neg = False
        if self.peek("!"):
            self.take("!")
            neg = True
        self.take("=")
        if self.peek("*"):
            self.take("*")
            a.value = "*"
        else:
            a.value = self.simple()
        a.negate = neg
        return a


# ------------------------------------------------------------------------------------------------- evaluator
class Evaluator:
    """Evaluates parsed ECL against one edition; every set is a temp table named t<n> holding a column `id`."""

    def __init__(self, con, edition: str):
        self.con, self.ed = con, edition
        self.n = itertools.count()
        self.made: list[str] = []
        row = con.execute("SELECT term_filter_types FROM edition WHERE edition = ?", [edition]).fetchone()
        if row is None:
            raise LookupError(f"edition {edition} is not in the database")
        # which description types the server's term filter searches in this edition (measured; see snomed_editions.py)
        self.term_types = [DESCRIPTION_TYPES[k] for k in row[0].split(",")]

    def expand(self, ecl: str) -> set[int]:
        try:
            t = self.eval(Parser(ecl).parse())
            return {r[0] for r in self.con.execute(f"SELECT id FROM {t}").fetchall()}
        finally:
            for t in self.made:
                self.con.execute(f"DROP TABLE IF EXISTS {t}")
            self.made.clear()

    def tmp(self, sql: str, params=None) -> str:
        t = f"t{next(self.n)}"
        self.con.execute(f"CREATE TEMP TABLE {t} AS SELECT DISTINCT id FROM ({sql})", params or [])
        self.made.append(t)
        return t

    # -- sets ------------------------------------------------------------------------------------------------
    def focus(self, f: Focus) -> str:
        e = self.ed
        if f.op == "*":
            return self.tmp(f"SELECT id FROM concept WHERE edition = '{e}' AND active")
        if f.op == "^":
            return self.tmp(f"SELECT referenced_component_id AS id FROM refset_member WHERE edition = '{e}' AND refset_id = {f.code}")
        # the focus concept as given, active or not -- but only if the edition has it at all: a concept created
        # later, or one from another extension, is nothing to the server, not a seed
        return self.tmp(self.hier_sql(f.op, f"SELECT id FROM concept WHERE edition = '{e}' AND id = {f.code}"))

    def hier_sql(self, op: str, seed_sql: str) -> str:
        """Descendants / ancestors of a seed set, active only; the seed itself kept as given for <<, >>."""
        e = self.ed
        if op == "":
            return seed_sql
        if op in ("<<", "<"):
            rel = f"SELECT c.descendant AS id FROM closure c JOIN ({seed_sql}) s ON c.ancestor = s.id WHERE c.edition = '{e}'"
        elif op in (">>", ">"):
            rel = f"SELECT c.ancestor AS id FROM closure c JOIN ({seed_sql}) s ON c.descendant = s.id WHERE c.edition = '{e}'"
        elif op == "<!":
            rel = f"SELECT r.source_id AS id FROM relationship r JOIN ({seed_sql}) s ON r.destination_id = s.id WHERE r.edition = '{e}' AND r.type_id = {IS_A}"
        elif op == ">!":
            rel = f"SELECT r.destination_id AS id FROM relationship r JOIN ({seed_sql}) s ON r.source_id = s.id WHERE r.edition = '{e}' AND r.type_id = {IS_A}"
        else:
            raise NotImplementedError(op)
        return f"{rel} UNION {seed_sql}" if op in ("<<", ">>") else rel

    def eval(self, n: Node) -> str:
        if isinstance(n, Focus):
            return self.focus(n)
        if isinstance(n, Nested):
            inner = self.eval(n.expr)
            return self.tmp(self.hier_sql(n.op, f"SELECT id FROM {inner}"))
        if isinstance(n, Bool):
            a, b = self.eval(n.left), self.eval(n.right)
            setop = {"AND": "INTERSECT", "OR": "UNION", "MINUS": "EXCEPT"}[n.op]
            return self.tmp(f"SELECT id FROM {a} {setop} SELECT id FROM {b}")
        if isinstance(n, Refined):
            return self.refine(self.eval(n.focus), n.refinement)
        if isinstance(n, Dotted):
            src = self.eval(n.expr)
            return self.tmp(f"""SELECT r.destination_id AS id FROM relationship r JOIN {src} s ON r.source_id = s.id
                                WHERE r.edition = '{self.ed}' AND {self.attr_cond(n.attr)}""")
        if isinstance(n, TermFilter):
            src = self.eval(n.expr)
            conds = " OR ".join(self.term_cond(t) for t in n.terms)
            return self.tmp(f"""SELECT d.concept_id AS id FROM description d JOIN {src} s ON d.concept_id = s.id
                                WHERE d.edition = '{self.ed}' AND d.type_id IN ({', '.join(map(str, self.term_types))}) AND ({conds})""")
        raise NotImplementedError(type(n).__name__)

    # -- refinement -------------------------------------------------------------------------------------------
    def attr_cond(self, a: Attr) -> str:
        if a.name_op == "*":
            return f"r.type_id <> {IS_A}"
        if a.name_op == "":
            return f"r.type_id = {a.name}"
        t = self.tmp(self.hier_sql(a.name_op, f"SELECT {a.name} AS id"))
        return f"r.type_id IN (SELECT id FROM {t})"

    def value_cond(self, a: Attr) -> str:
        if a.value == "*":
            return "true"
        t = self.eval(a.value)
        return f"r.destination_id IN (SELECT id FROM {t})"

    def refine(self, focus: str, ref: Refinement) -> str:
        parts = []
        for p in ref.parts:
            if isinstance(p, Attr):
                parts.append(self.attr_match(focus, p))
            elif isinstance(p, Group):
                parts.append(self.group_match(focus, p))
            else:
                parts.append(self.refine(focus, p))
        setop = "INTERSECT" if ref.op == "AND" else "UNION"
        return self.tmp(f" {setop} ".join(f"SELECT id FROM {t}" for t in parts))

    def attr_match(self, focus: str, a: Attr) -> str:
        sql = f"""SELECT r.source_id AS id FROM relationship r JOIN {focus} s ON r.source_id = s.id
                  WHERE r.edition = '{self.ed}' AND {self.attr_cond(a)} AND {self.value_cond(a)}"""
        if a.negate:
            sql = f"SELECT id FROM {focus} EXCEPT {sql}"
        return self.tmp(sql)

    def group_match(self, focus: str, g: Group) -> str:
        """Every attribute of the group satisfied by relationships sharing one relationship group of the concept."""
        joins, conds = [], []
        for i, a in enumerate(g.attrs):
            joins.append(f"JOIN relationship r{i} ON r{i}.source_id = s.id AND r{i}.edition = '{self.ed}'"
                         + (f" AND r{i}.relationship_group = r0.relationship_group" if i else ""))
            conds.append(self.attr_cond(a).replace("r.", f"r{i}.") + " AND " + self.value_cond(a).replace("r.", f"r{i}."))
        return self.tmp(f"SELECT s.id FROM {focus} s {' '.join(joins)} WHERE {' AND '.join(conds)}")

    def term_cond(self, term: str) -> str:
        words = [w for w in re.split(r"[^a-z0-9]+", term.lower()) if w]
        if not words:
            return "false"
        return "(" + " AND ".join(
            "regexp_matches(lower(d.term), " + self.q("(^|[^a-z0-9])" + re.escape(w)) + ")" for w in words) + ")"

    @staticmethod
    def q(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"


if __name__ == "__main__":
    import sys
    for e in sys.argv[1:]:
        print(Parser(e).parse())
