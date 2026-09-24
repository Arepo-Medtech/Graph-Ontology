#!/usr/bin/env python3
"""SNOMED CT's own modelling rules, checked on the graph: every SNOMED attribute edge against the Machine Readable
Concept Model (MRCM) that ships in the SNOMED CT-AU release.

The MRCM is three reference sets in Refset/Metadata: Domain (which concepts form a domain -- clinical findings,
procedures, products ...), Attribute Domain (which attribute each domain may carry, grouped or not, and how many times)
and Attribute Range (what an attribute may point at). Their constraints are ECL, and the AU release uses a small subset
of it -- `<<` (self or descendant), `<` (descendant), `^` (member of a reference set), a bare concept id, and OR -- which
this evaluates over the graph's own is-a edges (SNOMED CT-AU and the LOINC Extension) and reference set memberships.
Rules for postcoordinated content, and rules whose range is a concrete value (`dec(>#0..)`: strengths, counts -- the
graph does not load RF2's concrete-value relationships), are reported as not checkable, never skipped silently.

Per edge (s --attribute--> o, role group g), from SNOMED CT-AU RF2 and the SNOMED CT LOINC Extension:
  attribute not in the MRCM   no active, applicable Attribute Domain row names the attribute
  domain                      s is in no domain the attribute is allowed in
  range                       o is outside the attribute's range
  grouping                    an ungrouped attribute in a role group, or a grouped one in group 0
  cardinality                 more of the attribute on s (or in one group) than the rule allows
and, per concept in a domain, a mandatory attribute (minimum cardinality >= 1) it lacks.

    .venv/bin/python scripts/mrcm_check.py        # after build_edges.py; ~1 min; -> out/mrcm_check.json
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
from pathlib import Path

import duckdb

ONT_ROOT = os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES"))
AU_RF2 = Path(os.environ.get("AU_RF2_SNAPSHOT", os.path.join(ONT_ROOT, "SnomedCT_Release_AU1000036_20260831/Snapshot")))
META = AU_RF2 / "Refset" / "Metadata"
FILES = {"domain": "der2_sssssssRefset_MRCMDomainSnapshot_AU1000036_20260831.txt",
         "attribute_domain": "der2_cissccRefset_MRCMAttributeDomainSnapshot_AU1000036_20260831.txt",
         "attribute_range": "der2_ssccRefset_MRCMAttributeRangeSnapshot_AU1000036_20260831.txt"}
GRAPH, OUT = Path("out/graph.duckdb"), Path("out/mrcm_check.json")
IS_A = "116680003"
# content types that apply to released (precoordinated) concepts; 723595009 is postcoordinated content only
PRECOORD = {"723596005": "all SNOMED CT content", "723594008": "all precoordinated content"}
STRENGTH = {"723597001": "mandatory", "723598006": "optional"}
TERM = re.compile(r"^\s*(<<|<|\^)?\s*(\d{6,18})\s*$")
SAMPLE = 10


def strip(ecl: str) -> str:
    """An ECL constraint with its |terms| removed (ids only: what the register keeps)."""
    return re.sub(r"\s+", " ", re.sub(r"\|[^|]*\|", "", ecl or "")).strip()


def parse(ecl: str):
    """The subset the AU MRCM uses: [(op, concept)] joined by OR, op in '<<', '<', '^', 'self'.
    Returns None for what this does not evaluate (a concrete range, a refinement)."""
    e = strip(ecl)
    if not e or re.match(r"^(dec|int|str)\(", e) or ":" in e or "{" in e:
        return None
    out = []
    for part in re.split(r"\s+OR\s+", e.strip("() ")):
        m = TERM.match(part.strip("() "))
        if not m:
            return None
        out.append((m.group(1) or "self", m.group(2)))
    return out


def card(s: str) -> tuple[int, int | None]:
    lo, hi = s.split("..")
    return int(lo), None if hi == "*" else int(hi)


def rules() -> dict:
    """The MRCM, active rows only: domains, and per attribute its domains (grouping, cardinality) and range."""
    con = duckdb.connect()
    rd = lambda f: f"read_csv('{META / FILES[f]}', delim='\t', header=true, all_varchar=true, quote='')"
    dom = {r[0]: {"constraint": r[1], "terms": parse(r[1]), "parent": r[2] or None} for r in con.execute(
        f"SELECT referencedComponentId, domainConstraint, parentDomain FROM {rd('domain')} WHERE active = '1'").fetchall()}
    attrs = collections.defaultdict(lambda: {"domains": [], "ranges": []})
    for a, d, g, c, cg, st, ct in con.execute(f"""SELECT referencedComponentId, domainId, grouped, attributeCardinality,
            attributeInGroupCardinality, ruleStrengthId, contentTypeId FROM {rd('attribute_domain')} WHERE active = '1'""").fetchall():
        attrs[a]["domains"].append({"domain": d, "grouped": g == "1", "cardinality": c, "in_group_cardinality": cg,
                                    "strength": STRENGTH.get(st, st), "content": PRECOORD.get(ct, "postcoordinated only"),
                                    "applies": ct in PRECOORD})
    for a, r, st, ct in con.execute(f"""SELECT referencedComponentId, rangeConstraint, ruleStrengthId, contentTypeId
            FROM {rd('attribute_range')} WHERE active = '1'""").fetchall():
        attrs[a]["ranges"].append({"constraint": r, "terms": parse(r), "strength": STRENGTH.get(st, st),
                                   "content": PRECOORD.get(ct, "postcoordinated only"), "applies": ct in PRECOORD})
    return {"domains": dom, "attributes": dict(attrs)}


def main() -> int:
    if not (META / FILES["domain"]).exists():
        print(f"MRCM reference sets not found under {META}", file=sys.stderr)
        return 1
    R = rules()
    con = duckdb.connect()
    con.execute(f"ATTACH '{GRAPH}' AS g (READ_ONLY)")
    con.execute("SET threads=8")
    # the attribute edges the check covers: SNOMED's own relationships, from the AU release and the LOINC Extension
    con.execute(f"""CREATE TEMP TABLE e AS SELECT s_code s, substr(predicate, 5) a, o_code o,
                    coalesce(TRY_CAST(attrs->>'group' AS INT), 0) grp, source
                    FROM g.edge WHERE predicate LIKE 'sct:%' AND predicate <> 'sct:{IS_A}' AND regexp_matches(predicate, '^sct:[0-9]+$')
                      AND source IN ('SNOMED CT-AU RF2', 'SNOMED CT LOINC Extension')""")
    # ECL terms, one table: (rule kind, key, op, focus)
    terms = []
    for d, v in R["domains"].items():
        terms += [("domain", d, op, f) for op, f in (v["terms"] or [])]
    unchecked = collections.Counter()
    for a, v in R["attributes"].items():
        rs = [r for r in v["ranges"] if r["applies"]]
        for r in rs:
            if r["terms"] is None:
                unchecked["range is a concrete value or a refinement (not evaluated)"] += 1
            terms += [("range", a, op, f) for op, f in (r["terms"] or [])]
    con.execute("CREATE TEMP TABLE t (kind VARCHAR, k VARCHAR, op VARCHAR, focus VARCHAR)")
    con.executemany("INSERT INTO t VALUES (?, ?, ?, ?)", terms)
    # descendants of every focus concept a '<<' or '<' term names, over the graph's is-a edges
    con.execute(f"""CREATE TEMP TABLE isa AS SELECT s_code c, o_code p FROM g.edge WHERE predicate = 'sct:{IS_A}'
                    AND state <> 'rejected'""")
    con.execute("""CREATE TEMP TABLE desc_ AS WITH RECURSIVE d(f, c) AS (
                       SELECT DISTINCT focus, focus FROM t WHERE op IN ('<<', '<')
                       UNION SELECT d.f, i.c FROM d JOIN isa i ON i.p = d.c)
                   SELECT DISTINCT f, c FROM d""")
    con.execute("""CREATE TEMP TABLE members AS SELECT DISTINCT o_code f, s_code c FROM g.edge
                   WHERE predicate = 'sct:in_refset' AND o_code IN (SELECT focus FROM t WHERE op = '^')""")
    match = lambda x: f"""((t.op = 'self' AND {x} = t.focus)
        OR (t.op = '<<' AND EXISTS (SELECT 1 FROM desc_ d WHERE d.f = t.focus AND d.c = {x}))
        OR (t.op = '<' AND {x} <> t.focus AND EXISTS (SELECT 1 FROM desc_ d WHERE d.f = t.focus AND d.c = {x}))
        OR (t.op = '^' AND EXISTS (SELECT 1 FROM members m WHERE m.f = t.focus AND m.c = {x})))"""
    # attribute -> the domains it may be used in (applicable to precoordinated content), with its rules there
    ad = [(a, x["domain"], x["grouped"], x["cardinality"], x["in_group_cardinality"], x["strength"])
          for a, v in R["attributes"].items() for x in v["domains"] if x["applies"]]
    con.execute("""CREATE TEMP TABLE ad (a VARCHAR, dom VARCHAR, grouped BOOLEAN, card VARCHAR, gcard VARCHAR, strength VARCHAR)""")
    con.executemany("INSERT INTO ad VALUES (?, ?, ?, ?, ?, ?)", ad)
    # the concepts in each domain (the edge sources suffice, plus every concept for the mandatory check)
    con.execute("""CREATE TEMP TABLE subj AS SELECT DISTINCT s c FROM e
                   UNION SELECT DISTINCT s_code FROM g.edge WHERE s_vocab = 'SCT' AND predicate = 'sct:116680003'""")
    con.execute(f"""CREATE TEMP TABLE in_dom AS SELECT DISTINCT t.k dom, s.c FROM subj s JOIN t ON t.kind = 'domain'
                    WHERE {match('s.c')}""")
    # per edge: domain and range verdicts
    con.execute(f"""CREATE TEMP TABLE rng_ok AS SELECT DISTINCT e.s, e.a, e.o FROM e JOIN t ON t.kind = 'range' AND t.k = e.a
                    WHERE {match('e.o')}""")
    con.execute("""CREATE TEMP TABLE ev AS SELECT e.*,
            EXISTS (SELECT 1 FROM ad WHERE ad.a = e.a) AS known,
            EXISTS (SELECT 1 FROM ad JOIN in_dom i ON i.dom = ad.dom WHERE ad.a = e.a AND i.c = e.s) AS dom_ok,
            EXISTS (SELECT 1 FROM t WHERE t.kind = 'range' AND t.k = e.a) AS has_range,
            EXISTS (SELECT 1 FROM rng_ok r WHERE r.s = e.s AND r.a = e.a AND r.o = e.o) AS rng_ok FROM e""")
    # the rules that govern an edge: the attribute's rules in every domain its source is in. A concept can be in several
    # (an AMT product is in the product domain and an AU sub-domain), so a grouping or cardinality rule is broken only
    # when every applicable rule is: grouping allowed if any rule allows it, the largest maximum wins.
    hi = lambda c: f"CASE WHEN split_part({c}, '..', 2) = '*' THEN NULL ELSE CAST(split_part({c}, '..', 2) AS INT) END"
    con.execute(f"""CREATE TEMP TABLE gov AS SELECT e.s, e.a, bool_or(ad.grouped) may_group, bool_or(NOT ad.grouped) may_ungroup,
                   CASE WHEN bool_or({hi('ad.card')} IS NULL) THEN NULL ELSE max({hi('ad.card')}) END card_hi,
                   CASE WHEN bool_or({hi('ad.gcard')} IS NULL) THEN NULL ELSE max({hi('ad.gcard')}) END gcard_hi,
                   string_agg(DISTINCT ad.card, ' / ') card, string_agg(DISTINCT ad.gcard, ' / ') gcard
                   FROM (SELECT DISTINCT s, a FROM e) e
                   JOIN ad ON ad.a = e.a JOIN in_dom i ON i.dom = ad.dom AND i.c = e.s GROUP BY 1, 2""")
    viol = []           # (class, attribute, source, s, o, detail)
    for s, a, o, grp, src, known, dom_ok, has_range, r_ok in con.execute("""SELECT s, a, o, grp, source, known, dom_ok, has_range, rng_ok
            FROM ev WHERE NOT known OR NOT dom_ok OR (has_range AND NOT rng_ok)""").fetchall():
        if not known:
            viol.append(("attribute not in the MRCM", a, src, s, o, None))
            continue
        if not dom_ok:
            viol.append(("domain: source outside every domain the attribute is allowed in", a, src, s, o, None))
        if has_range and not r_ok:
            viol.append(("range: target outside the attribute's range", a, src, s, o, None))
    for s, a, o, grp, src, may_group in con.execute("""SELECT e.s, e.a, e.o, e.grp, e.source, g.may_group FROM e JOIN gov g USING (s, a)
            WHERE (e.grp = 0 AND NOT g.may_ungroup) OR (e.grp <> 0 AND NOT g.may_group)""").fetchall():
        viol.append(("grouping: " + ("a grouped attribute outside a role group" if may_group else "an ungrouped attribute in a role group"),
                     a, src, s, o, f"group {grp}"))
    for s, a, n, card_, src in con.execute("""SELECT e.s, e.a, count(*), any_value(g.card), any_value(e.source) FROM e JOIN gov g USING (s, a)
            GROUP BY 1, 2 HAVING any_value(g.card_hi) IS NOT NULL AND count(*) > any_value(g.card_hi)""").fetchall():
        viol.append(("cardinality: more on the concept than the rule allows", a, src, s, None, f"{n} > {card_}"))
    for s, a, grp, n, gc, src in con.execute("""SELECT e.s, e.a, e.grp, count(*), any_value(g.gcard), any_value(e.source) FROM e
            JOIN gov g USING (s, a) WHERE e.grp <> 0 GROUP BY 1, 2, 3
            HAVING any_value(g.gcard_hi) IS NOT NULL AND count(*) > any_value(g.gcard_hi)""").fetchall():
        viol.append(("cardinality: more in one role group than the rule allows", a, src, s, None, f"{n} in group {grp} > {gc}"))
    # mandatory attributes: a concept in the domain (and in no narrower domain that relaxes it) lacking the attribute
    mand = con.execute("""SELECT ad.a, ad.dom, ad.card FROM ad WHERE ad.strength = 'mandatory'
                          AND TRY_CAST(split_part(ad.card, '..', 1) AS INT) >= 1""").fetchall()
    concrete = {a for a, v in R["attributes"].items() if v["ranges"] and all(r["terms"] is None for r in v["ranges"] if r["applies"])}
    for a, d, c in mand:
        missing = [s for (s,) in con.execute("""SELECT i.c FROM in_dom i WHERE i.dom = ?
                   AND i.c NOT IN (SELECT s FROM e WHERE a = ?) AND i.c <> ?""",
                   [d, a, next((f for k, op, f in [(x[1], x[2], x[3]) for x in terms if x[0] == 'domain'] if k == d), "")]).fetchall()]
        if a in concrete:           # a concrete-valued attribute (a count, a strength): RF2's concrete values are not in the graph
            unchecked[f"mandatory concrete-valued attribute {a} (not loaded): {len(missing):,} concepts not checked"] += 1
            continue
        viol += [("mandatory attribute missing", a, "SNOMED CT-AU RF2 or LOINC Extension", s, None, f"domain {d} requires {c}")
                 for s in missing]

    n_edges = con.execute("SELECT count(*) FROM e").fetchone()[0]
    by_class = collections.Counter(v[0] for v in viol)
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for v in viol:
        by[v[0]][(v[1], v[2])].append(v)
    label = dict(con.execute("SELECT code, name FROM g.node WHERE vocab = 'SCT' AND code IN (SELECT UNNEST(?))",
                             [sorted({v[1] for v in viol} | {v[3] for v in viol} | {v[4] for v in viol if v[4]})]).fetchall())
    classes = {}
    for cls, groups in sorted(by.items()):
        rows = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        classes[cls] = {"violations": by_class[cls], "by_attribute": [
            {"attribute": a, "attribute_name": label.get(a), "source": src, "count": len(vs),
             "sample": [{"s": v[3], "s_name": label.get(v[3]), "o": v[4], "o_name": label.get(v[4]) if v[4] else None,
                         **({"detail": v[5]} if v[5] else {})} for v in vs[:SAMPLE]]} for (a, src), vs in rows]}
    by_source = collections.Counter((v[0], v[2]) for v in viol)
    doc = {"_note": "SNOMED CT attribute edges against the MRCM of SNOMED CT-AU 20260831 (scripts/mrcm_check.py). Names are the "
                    "graph's; out/ is git-ignored.",
           "edges_checked": n_edges, "attributes_in_edges": con.execute("SELECT count(DISTINCT a) FROM e").fetchone()[0],
           "mrcm": {"domains": len(R["domains"]), "attributes": len(R["attributes"]),
                    "rules_not_checkable": dict(unchecked)},
           "violations": dict(by_class), "violations_by_source": {f"{c} | {s}": n for (c, s), n in sorted(by_source.items())},
           "classes": classes}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"MRCM: {n_edges:,} attribute edges checked against {len(R['domains'])} domains, {len(R['attributes'])} attributes")
    for c, n in sorted(by_class.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>9,}  {c}")
    for k, n in unchecked.items():
        print(f"  not checkable: {k}" + (f" ({n} rules)" if n > 1 else ""))
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
