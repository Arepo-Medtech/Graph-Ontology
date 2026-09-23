#!/usr/bin/env python3
"""Walk the medical multigraph from one node, with the traversal rules the design requires.

    * a VISITED SET per path: a node may not repeat within one path, so the graph's cycles (salt <-> base, is-a with
      its reverse, drug -> class -> drugs in class -> drug) cannot loop;
    * a DEPTH CAP;
    * rejected edges are never followed -- a rejected mapping is ignorance, not an answer;
    * the predicates to follow are named, each forwards (subject -> object) or backwards (`~pred`, object -> subject).

    scripts/graph_walk.py SCT:6383011000036106 --follow pbs:lists,pbs:has_restriction,pbs:restricted_to --depth 3
    scripts/graph_walk.py SCT:22298006 --follow sct:116680003 --depth 4          # ancestors of myocardial infarction
    scripts/graph_walk.py SCT:22298006 --follow ~sct:116680003 --depth 1         # its direct children

Prints each node reached with its depth and the path of predicates that reached it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

GRAPH = Path("out/graph.duckdb")


def walk(con, start: str, follow: list[str], depth: int, limit: int = 200):
    fwd = [p for p in follow if not p.startswith("~")]
    back = [p[1:] for p in follow if p.startswith("~")]
    vocab, code = start.split(":", 1)
    return con.execute(f"""
        WITH RECURSIVE step AS (
            SELECT e.s_vocab AS fv, e.s_code AS fc, e.predicate AS pred, e.o_vocab AS tv, e.o_code AS tc FROM edge e
             WHERE e.state <> 'rejected' AND list_contains(?, e.predicate)
            UNION ALL
            SELECT e.o_vocab, e.o_code, '~' || e.predicate, e.s_vocab, e.s_code FROM edge e
             WHERE e.state <> 'rejected' AND list_contains(?, e.predicate)),
        w(vocab, code, depth, preds, visited) AS (
            SELECT ?, ?, 0, []::VARCHAR[], [? || ':' || ?]
            UNION ALL
            SELECT s.tv, s.tc, w.depth + 1, list_append(w.preds, s.pred), list_append(w.visited, s.tv || ':' || s.tc)
            FROM w JOIN step s ON s.fv = w.vocab AND s.fc = w.code
            WHERE w.depth < ? AND NOT list_contains(w.visited, s.tv || ':' || s.tc))   -- the visited set: no cycles
        SELECT w.vocab || ':' || w.code AS key, min(w.depth) AS depth, any_value(n.name) AS name,
               arg_min(array_to_string(w.preds, ' > '), w.depth) AS via
        FROM w LEFT JOIN node n ON n.vocab = w.vocab AND n.code = w.code
        WHERE w.depth > 0 GROUP BY 1 ORDER BY 2, 3 LIMIT ?""",
        [fwd, back, vocab, code, vocab, code, depth, limit]).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("start", help="node key, VOCAB:code")
    ap.add_argument("--follow", required=True, help="comma-separated predicates; prefix ~ to follow backwards")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()
    con = duckdb.connect(str(GRAPH), read_only=True)
    name = con.execute("SELECT name FROM node WHERE key = ?", [a.start]).fetchone()
    print(f"{a.start}  {name[0] if name else '(not in graph)'}")
    for key, d, nm, via in walk(con, a.start, a.follow.split(","), a.depth, a.limit):
        print(f"  {d}  {key:<28} {(nm or '')[:60]:<60} via {via}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
