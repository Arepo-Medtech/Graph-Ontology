#!/usr/bin/env python3
"""Inconsistency detection over the graph's equivalence claims (workstream 3): the check that raises precision.

Every edge that claims two codes are the same thing (an exact match, a shared UMLS concept, Orphanet's exact alignment,
a gene's own cross-reference) is followed transitively, which gives equivalence clusters. In the vocabularies that are
one-to-one by design -- a MONDO disease, an Orphanet entry, an OMIM entry, an HGNC or NCBI gene, an HPO phenotype, a DOID
disease -- a cluster holding two codes of one vocabulary says two different things were declared the same: either the
source itself has a duplicate, or some edge on the path between them is wrong. For each such pair the shortest path is
traced, and the edges that turn up on the most paths -- the bridges -- are ranked into a precision queue.

Not equivalence, so not followed: gene -> protein (HGNC -> UniProt: histone H4 is encoded by 14 genes), a product or
substance mapping uphill (OMOP Maps to, ICD-10-CM Maps to), classifications and anything rejected or inadmissible.

    .venv/bin/python scripts/consistency.py        # after graph_report.py; ~1 min; -> out/consistency.json

The output names codes and names from licensed sources, so it stays in out/ (git-ignored); docs/consistency.md carries
the counts.
"""
from __future__ import annotations

import collections
import itertools
import json
import random
import sys
import time
from pathlib import Path

import duckdb

GRAPH, OUT = Path("out/graph.duckdb"), Path("out/consistency.json")
EQUIV = ("mondo:exact_match", "hgnc:xref", "drugcentral:rxnorm", "drugcentral:snomed", "sct:ncbitaxon_equivalent", "hp:umls_snomed",
         "umls:shared_cui", "umls:concept_member", "loinc:sct_concept", "radlex:fma_xref", "uberon:fma_match")
ANCHOR = ("MONDO", "ORPHA", "OMIM", "HGNC", "NCBIGENE", "HP", "DOID")
PAIRS_PER_CLUSTER = 20


def compute(con):
    """Equivalence clusters and their bridges over `con` (a connection to the graph): -> (rows, clusters, bridges, conflicts,
    traced). Shared with graph_report.py, which holds back the UMLS bridges on two or more conflict paths."""
    rows = con.execute(f"""SELECT s_vocab || ':' || s_code, o_vocab || ':' || o_code, predicate, method FROM edge
        WHERE state <> 'rejected' AND tier <> 'inadmissible'
          AND ((predicate IN {EQUIV} AND NOT (predicate = 'hgnc:xref' AND o_vocab = 'UNIPROT'))
               OR (predicate = 'orpha:xref' AND method = 'E'))
        ORDER BY 1, 2, 3, 4""").fetchall()               # a fixed order: the seeded sample of pairs must be the same every run
    adj, par = collections.defaultdict(list), {}

    def root(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a, b, p, m in rows:
        adj[a].append((b, p, m))
        adj[b].append((a, p, m))
        ra, rb = root(a), root(b)
        if ra != rb:
            par[ra] = rb
    clusters = collections.defaultdict(list)
    for x in par:
        clusters[root(x)].append(x)

    def path(s, t):
        prev, q = {s: None}, [s]
        for x in q:
            if x == t:
                break
            for y, p, m in adj[x]:
                if y not in prev:
                    prev[y] = (x, p, m)
                    q.append(y)
        out, x = [], t
        while prev.get(x):
            a, p, m = prev[x]
            out.append((a, x, p, m))
            x = a
        return out

    rng = random.Random(24)
    bridges, conflicts, traced = collections.Counter(), collections.Counter(), 0
    for mem in sorted((sorted(m) for m in clusters.values()), key=lambda m: m[0]):
        byv = collections.defaultdict(list)
        for x in mem:
            byv[x.split(":", 1)[0]].append(x)
        for v in ANCHOR:
            codes = byv.get(v, [])
            if len(codes) < 2:
                continue
            conflicts[v] += 1
            prs = list(itertools.combinations(sorted(codes), 2))
            for s, t in (rng.sample(prs, PAIRS_PER_CLUSTER) if len(prs) > PAIRS_PER_CLUSTER else prs):
                traced += 1
                for a, b, p, m in path(s, t):
                    bridges[(min(a, b), max(a, b), p, m)] += 1
    return rows, clusters, bridges, conflicts, traced


def main() -> int:
    t0 = time.time()
    con = duckdb.connect(str(GRAPH), read_only=True)
    rows, clusters, bridges, conflicts, traced = compute(con)
    size = dict(((p, m), n) for p, m, n in con.execute("SELECT predicate, method, count(*) FROM edge GROUP BY 1, 2").fetchall())
    fam = collections.Counter((p, m) for (_, _, p, m) in bridges)
    name = lambda k: (con.execute("SELECT name FROM node WHERE key = ?", [k]).fetchone() or [None])[0]
    sizes = sorted((len(v) for v in clusters.values()), reverse=True)
    out = {"_note": "equivalence clusters and their conflicts (scripts/consistency.py); codes and names from licensed sources -- out/ only",
           "equivalence_edges": len(rows), "clusters": len(clusters), "largest_clusters": sizes[:10],
           "clusters_with_two_codes_of_a_one_to_one_vocabulary": dict(conflicts.most_common()),
           "conflict_pairs_traced": traced,
           "bridge_edges_by_family": [{"predicate": p, "method": m, "bridge_edges": n, "family_edges": size.get((p, m)),
                                       "rate": round(n / size[(p, m)], 5) if size.get((p, m)) else None}
                                      for (p, m), n in sorted(fam.items(), key=lambda kv: -kv[1] / max(size.get(kv[0], 1), 1))],
           "precision_queue": [{"s": a, "s_name": name(a), "o": b, "o_name": name(b), "predicate": p, "method": m, "on_conflict_paths": n}
                               for (a, b, p, m), n in bridges.most_common(300)],
           "bridges_all": [[a, b, p, m, n] for (a, b, p, m), n in bridges.most_common()],
           "seconds": round(time.time() - t0)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("equivalence_edges", "clusters", "largest_clusters", "clusters_with_two_codes_of_a_one_to_one_vocabulary",
                                          "conflict_pairs_traced", "seconds")}, indent=1))
    for f in out["bridge_edges_by_family"][:10]:
        print(f"  {f['predicate']} | {f['method']}: {f['bridge_edges']} of {f['family_edges']} ({f['rate']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
