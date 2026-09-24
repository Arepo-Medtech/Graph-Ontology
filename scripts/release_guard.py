#!/usr/bin/env python3
"""The release guard (workstream 5): per-release limits on what a rebuild may lose, checked against a committed baseline.

A rebuild can shrink the graph without failing -- a source quietly narrower, a filter written too wide, a join that
drops rows. completeness.py guards the shares that matter clinically; this guards the counts underneath them:

  edges per predicate   usable edges (not rejected, not inadmissible). A predicate that vanishes, or loses more than
                        1% (and at least 10 edges), FAILS. One that grows by more than 25% (and at least 1,000) is a
                        WARNING: it may be a new source, or a load run twice.
  nodes per vocabulary  a vocabulary that vanishes or loses more than 1% (and at least 10 nodes) FAILS.
  consistency           (scripts/consistency.py) clusters holding two codes of a one-to-one vocabulary: a rise of more
                        than 5% (and at least 5 clusters) FAILS; the largest cluster more than doubling FAILS.
  islands               (graph_report.py) components or nodes outside the main one rising more than 5% (and at least
                        50) FAILS.

    .venv/bin/python scripts/release_guard.py                 # after graph_report.py and consistency.py; seconds
    .venv/bin/python scripts/release_guard.py --set-baseline  # accept this release (a deliberate change)

Exit 1 on any failure, naming each. The baseline (reference/release_guard_baseline.json) holds counts only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

GRAPH, REPORT, CONSIST = Path("out/graph.duckdb"), Path("out/graph_report.json"), Path("out/consistency.json")
BASELINE = Path("reference/release_guard_baseline.json")


def current() -> dict:
    con = duckdb.connect(str(GRAPH), read_only=True)
    cur = {"edges": dict(con.execute("""SELECT predicate, count(*) FILTER (WHERE state <> 'rejected' AND tier <> 'inadmissible')
                                        FROM edge GROUP BY 1 ORDER BY 1""").fetchall()),
           "nodes": dict(con.execute("SELECT vocab, count(*) FROM node GROUP BY 1 ORDER BY 1").fetchall()),
           "totals": dict(zip(("nodes", "edges", "usable_edges"), con.execute("""SELECT (SELECT count(*) FROM node), count(*),
                                count(*) FILTER (WHERE state <> 'rejected' AND tier <> 'inadmissible') FROM edge""").fetchone()))}
    if CONSIST.exists():
        c = json.load(open(CONSIST))
        cur["consistency"] = {"conflicts": c["clusters_with_two_codes_of_a_one_to_one_vocabulary"],
                              "largest_cluster": c["largest_clusters"][0] if c["largest_clusters"] else 0}
    if REPORT.exists():
        i = json.load(open(REPORT)).get("islands", {})
        cur["islands"] = {"components": i.get("components"), "nodes_outside_main": i.get("nodes_outside_it")}
    return cur


def compare(base: dict, cur: dict) -> tuple[list[str], list[str]]:
    fail, warn = [], []
    for kind, lose_pct, lose_min in (("edges", 0.01, 10), ("nodes", 0.01, 10)):
        for k, b in base.get(kind, {}).items():
            c = cur[kind].get(k)
            if c is None or (c == 0 and b > 0):
                fail.append(f"{kind[:-1]} family vanished: {k} (was {b:,})")
            elif b - c > max(lose_min, lose_pct * b):
                fail.append(f"{kind[:-1]} family shrank: {k} {b:,} -> {c:,} ({(c - b) / b:+.1%})")
        if kind == "edges":
            for k, c in cur[kind].items():
                b = base[kind].get(k)
                if b is None:
                    warn.append(f"new edge family: {k} ({c:,})")
                elif c - b > max(1000, 0.25 * b):
                    warn.append(f"edge family grew: {k} {b:,} -> {c:,} ({(c - b) / b:+.1%}) -- a new source, or a load run twice?")
    bc, cc = base.get("consistency"), cur.get("consistency")
    if bc and cc:
        for v, b in bc["conflicts"].items():
            c = cc["conflicts"].get(v, 0)
            if c - b > max(5, 0.05 * b):
                fail.append(f"conflicts rose: two {v} codes in one equivalence cluster {b:,} -> {c:,}")
        if cc["largest_cluster"] > 2 * max(bc["largest_cluster"], 1):
            fail.append(f"largest equivalence cluster {bc['largest_cluster']} -> {cc['largest_cluster']}")
    elif bc and not cc:
        warn.append("out/consistency.json missing: run scripts/consistency.py before the guard")
    bi, ci = base.get("islands"), cur.get("islands")
    if bi and ci:
        for k in ("components", "nodes_outside_main"):
            if (ci.get(k) or 0) - (bi.get(k) or 0) > max(50, 0.05 * (bi.get(k) or 0)):
                fail.append(f"islands grew: {k} {bi[k]:,} -> {ci[k]:,}")
    return fail, warn


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set-baseline", action="store_true")
    a = ap.parse_args()
    cur = current()
    base = json.load(open(BASELINE)) if BASELINE.exists() else {}
    fail, warn = compare(base, cur) if base else ([], ["no baseline yet: run with --set-baseline"])
    t = cur["totals"]
    print(f"graph {t['nodes']:,} nodes, {t['edges']:,} edges ({t['usable_edges']:,} usable), {len(cur['edges'])} edge families, "
          f"{len(cur['nodes'])} vocabularies")
    for w in warn:
        print("  WARN  " + w)
    for f in fail:
        print("  FAIL  " + f, file=sys.stderr)
    if a.set_baseline:
        BASELINE.write_text(json.dumps(cur, indent=1, sort_keys=True) + "\n")
        print(f"baseline written: {BASELINE}" + (f" (accepting {len(fail)} failure(s) above)" if fail else ""))
        return 0
    if fail:
        print(f"RELEASE GUARD FAILED: {len(fail)} limit(s) broken", file=sys.stderr)
        return 1
    print("release guard: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
