#!/usr/bin/env python3
"""Adjudicate split candidates by retrieval.

The splitter emits both readings where the grammar is ambiguous
("Blepharospasm" and "Blepharospasm spasm"). A coined term draws no citations;
a real one does. PubMed decides, so no word list has to.

Writes the survivors back to conditions_split.json with their citation count,
and records every rejection so the discards are inspectable.
"""
import json, pathlib, foundry

SRC = pathlib.Path("out/conditions_split.json")

def main():
    doc = json.loads(SRC.read_text())
    kept, dropped = [], []
    for i, rec in enumerate(doc["conditions"], 1):
        try:
            refs = foundry.evidence(rec["condition"], n=8)
        except Exception as e:
            dropped.append({**rec, "reason": f"error: {e}"}); continue
        n = len(refs)
        if n:
            tiers = sorted({r["query_tier"] for r in refs})
            kept.append({**rec, "validation_citations": n, "validation_tier": tiers[0]})
        else:
            dropped.append({**rec, "reason": "no_citations_term_likely_coined"})
        if i % 20 == 0:
            print(f"  {i}/{len(doc['conditions'])}", flush=True)
    doc["conditions"] = kept
    doc["count"] = len(kept)
    doc["rejected"] = dropped
    doc["validation"] = "children with zero citations dropped as likely coined terms"
    SRC.write_text(json.dumps(doc, indent=2))
    print(f"\nkept {len(kept)}   dropped {len(dropped)}")
    print("\ndropped:")
    for d in dropped: print(f"   {d['condition']}")

if __name__ == "__main__":
    main()
