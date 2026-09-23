#!/usr/bin/env python3
"""Bind the findings and diagnoses of reference/diagnostic_accuracy.json to SNOMED CT-AU -- exact matches only.

Text to concept is a gap, so the rule is bind_indications.py's: a term binds only when it equals (after normalising case
and punctuation) a SNOMED CT-AU 20260831 preferred term or synonym on the live Ontoserver, among clinical findings,
situations and events. Each record lists the terms to try, in order; the first exact hit wins. A record whose finding or
diagnosis binds to nothing stays a candidate -- it never becomes an edge.

    scripts/bind_diagnostic_accuracy.py      # writes reference/diagnostic_accuracy_bindings.json
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("bind_indications", Path(__file__).with_name("bind_indications.py"))
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)


FINDING = "<< 404684003 OR << 243796009 OR << 272379006"                        # finding, situation, event (bind_indications' ECL)
ECL = {"finding": FINDING, "prognosis": FINDING,
       "test": "<< 71388002 OR << 363787002 OR << 404684003 OR << 386053000",   # procedure, observable, result finding, evaluation procedure
       "score": "<< 273249006 OR << 363787002 OR << 254291000 OR << 404684003"}  # assessment scale, observable, staging & scales, finding


def bind_terms(terms: list[str], cache: dict, ecl: str = FINDING) -> dict | None:
    bi.ECL = ecl
    for t0 in terms:
        t = (ecl, t0)
        if t not in cache:
            hits, nt, cache[t] = bi.expand(t0), bi.norm(t0), None
            for h in hits:
                for term, how in [(h.get("display", ""), "exact_display")] + [
                        (d.get("value", ""), "exact_synonym") for d in h.get("designation", []) if d.get("language", "en").startswith("en")]:
                    if bi.norm(term) == nt and cache[t] is None:
                        cache[t] = {"concept_id": h["code"], "display": h.get("display"), "matched_term": t0, "method": how}
        if cache[t]:
            return cache[t]
    return None


def main() -> int:
    recs = json.load(open("reference/diagnostic_accuracy.json"))["records"]
    cache, out = {}, []
    for r in recs:
        kind = r.get("kind", "finding")
        row = {"id": r["id"], "finding": bind_terms(r["finding_terms"], cache, ECL[kind]), "diagnosis": bind_terms(r["diagnosis_terms"], cache)}
        for side, text, ecl in (("finding", r["finding_text"], ECL[kind]), ("diagnosis", r["diagnosis_text"], FINDING)):
            if row[side] is None:       # a frame for the person: the Ontoserver's nearest concepts to the source's own words
                bi.ECL = ecl
                row[side + "_candidates"] = [{"concept_id": h["code"], "display": h.get("display")} for h in bi.expand(text, 5)]
        out.append(row)
    both = sum(1 for x in out if x["finding"] and x["diagnosis"])
    Path("reference/diagnostic_accuracy_bindings.json").write_text(json.dumps(
        {"_note": "Output of scripts/bind_diagnostic_accuracy.py. Exact matches only; null = no exact SNOMED CT-AU term (a candidate, not an edge).",
         "edition": bi.EDITION, "server": bi.BASE, "bound_both": both, "records": len(out), "results": out}, indent=1, ensure_ascii=False) + "\n")
    print(f"both bound: {both}/{len(out)}")
    for x in out:
        print(f"  {x['id']:<34} finding: {(x['finding'] or {}).get('display') or '-- NONE --':<44} dx: {(x['diagnosis'] or {}).get('display') or '-- NONE --'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
