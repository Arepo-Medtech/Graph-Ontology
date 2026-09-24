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
  concept model         (scripts/mrcm_check.py) SNOMED attribute edges breaking the MRCM, by class (domain, range,
                        grouping, cardinality, mandatory attribute missing): a class rising by more than 5% (and at
                        least 5 edges) FAILS -- a new release or loader brought edges SNOMED's own rules forbid.
  concrete values       (build_edges.py concrete_value: SNOMED strengths, pack sizes, counts) per attribute, the same
                        limits as an edge family.
  loader ledger         (build_edges.py loader_ledger) more loaders with no declared ledger than the baseline FAILS -- a
                        new loader states its source rows and exclusions; a loader whose excluded share of its source
                        rises by more than 5 points (and at least 100 rows) is a WARNING: a filter now takes more.

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
MRCM = Path("out/mrcm_check.json")
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
    if "loader_ledger" in {t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}:
        cur["ledger"] = {l: {"available": a, "excluded": int(x or 0), "kind": k} for l, k, a, x in con.execute(
            "SELECT loader, any_value(kind), any_value(available), sum(rows) FROM loader_ledger GROUP BY 1 ORDER BY 1").fetchall()}
    if "concrete_value" in {t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}:
        cur["values"] = dict(con.execute("SELECT predicate, count(*) FROM concrete_value GROUP BY 1 ORDER BY 1").fetchall())
    if MRCM.exists():
        cur["mrcm"] = json.load(open(MRCM))["violations"]
    if REPORT.exists():
        i = json.load(open(REPORT)).get("islands", {})
        cur["islands"] = {"components": i.get("components"), "nodes_outside_main": i.get("nodes_outside_it")}
    return cur


def compare(base: dict, cur: dict) -> tuple[list[str], list[str]]:
    fail, warn = [], []
    for kind, lose_pct, lose_min in (("edges", 0.01, 10), ("nodes", 0.01, 10), ("values", 0.01, 10)):
        for k, b in base.get(kind, {}).items():
            c = cur.get(kind, {}).get(k)
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
    bm, cm = base.get("mrcm"), cur.get("mrcm")
    if bm is not None and cm is not None:
        for k in sorted(set(bm) | set(cm)):
            b, c = bm.get(k, 0), cm.get(k, 0)
            if c - b > max(5, 0.05 * b):
                fail.append(f"concept-model violations rose: {k} {b:,} -> {c:,}")
    elif bm is not None:
        warn.append("out/mrcm_check.json missing: run scripts/mrcm_check.py before the guard")
    bl, cl = base.get("ledger"), cur.get("ledger")
    if bl and cl:
        und = lambda d: sum(v["kind"] == "undeclared" for v in d.values())
        if und(cl) > und(bl):
            fail.append(f"loaders with no declared ledger {und(bl)} -> {und(cl)}: "
                        + ", ".join(k for k, v in cl.items() if v["kind"] == "undeclared" and bl.get(k, {}).get("kind") != "undeclared"))
        for k, v in cl.items():
            b = bl.get(k)
            if b and v["available"] and b["available"] and v["excluded"] - b["excluded"] >= 100 \
                    and v["excluded"] / v["available"] - b["excluded"] / b["available"] > 0.05:
                warn.append(f"loader excludes more: {k} {b['excluded'] / b['available']:.1%} -> {v['excluded'] / v['available']:.1%} of its source rows")
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
