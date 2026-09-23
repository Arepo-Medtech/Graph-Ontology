#!/usr/bin/env python3
"""Check the transcription in reference/diagnostic_accuracy.json against the cached PubMed abstracts.

Two checks per record, both mechanical: (1) every number in `as_written` occurs as a number in the abstract of its PMID
(cache/pubmed/<pmid>.json, fetched by scripts/pubmed_fetch.py); (2) every value the record stores -- lr, its interval,
sensitivity, specificity and theirs -- equals one of those written numbers (or a percentage of one). A record passing
both was transcribed from its source; whether the finding and diagnosis are the right concepts is the binding's job,
and whether the pairing is clinically apt is a person's (the edges are corrected_pending_attestation).

    scripts/verify_diagnostic_accuracy.py      # writes reference/diagnostic_accuracy_verification.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# The binding of a finding to a SNOMED concept is a gap step with its own error rate. Every distinct binding was read
# against the source wording (23 Sep 2026); those read as wrong lost their fallback term and became candidates.
BINDING_REVIEW = {
    "reader": "the transcriber (not independent)",
    "finding": {"distinct_bindings_read": 203, "read_as_wrong": 17,
                "wrong": ["calf diameter -> Swollen calf", "vaginal discharge on examination -> Vaginal discharge",
                          "dry mucous membranes -> Aptyalism", "furrowed tongue -> Plicated tongue", "pulse differential -> Pulse deficit",
                          "tender anterior cervical nodes -> Cervical lymphadenitis", "major trauma -> Multiple traumatic injuries",
                          "toxic or moribund -> Moribund", "fever > 40 C -> Hyperpyrexia", "lower chest wall indrawing -> Intercostal recession",
                          "sensory deficit -> Absence of sensation", "Barlow and Ortolani -> Ortolani alone",
                          "dysuria, frequency or both -> Dysuria", "inguinal or axillary adenopathy -> Inguinal lymphadenopathy",
                          "severe snake envenomation -> Snake venom poisoning", "colorectal cancer -> Malignant neoplasm of colon (x2)"]},
    "test_score_prognosis": {"distinct_bindings_read": 79, "read_as_wrong": 14,
                "wrong": ["fever with presentation within 3 days -> Fever", "death or poor neurological outcome -> Death",
                          "retrognathia -> Congenital retrognathism", "systolic BP 140 or more -> Systolic hypertension",
                          "severe alcohol withdrawal -> Alcohol withdrawal delirium", "venom coagulopathy / thrombocytopenia -> Blood coagulation disorder (x2)",
                          "potentially lethal cardiac disorder -> Heart disease", "peritonsillar ultrasound, not intraoral -> Ultrasound of oral cavity (x4)",
                          "rheumatoid factor IgA -> Rheumatoid factor measurement", "inhibin B -> Inhibin measurement",
                          "bone and joint infection -> Osteomyelitis"]}}
SRC, CACHE, OUT = Path("reference/diagnostic_accuracy.json"), Path("cache/pubmed"), Path("reference/diagnostic_accuracy_verification.json")


def main() -> int:
    recs = json.load(open(SRC))["records"]
    rows, ok = [], 0
    for r in recs:
        f = CACHE / f"{r['pmid']}.json"
        if not f.exists():
            rows.append({"id": r["id"], "verified": False, "why": "abstract not cached -- run scripts/pubmed_fetch.py fetch " + r["pmid"]})
            continue
        nums = set(re.findall(r"\d+(?:\.\d+)?", json.load(open(f))["abstract"].replace("\u00b7", ".")))   # the Lancet writes 0·62
        missing = [w for w in r["as_written"] if w not in nums]
        written = [float(w) for w in r["as_written"]]
        stored = [v for v in [r.get("lr"), r.get("sens"), r.get("spec")] + (r.get("lr_ci") or []) + (r.get("lr_range") or []) + (r.get("sens_ci") or []) + (r.get("spec_ci") or [])
                  if v is not None]
        unmatched = [v for v in stored if not any(abs(v - w) < 1e-9 or abs(v * 100 - w) < 1e-6 for w in written)]
        good = not missing and not unmatched
        ok += good
        rows.append({"id": r["id"], "pmid": r["pmid"], "verified": good, "numbers_not_in_abstract": missing, "stored_values_not_written": unmatched})
    json.dump({"_note": "Output of scripts/verify_diagnostic_accuracy.py: transcription fidelity, record by record.",
               "records": len(recs), "verified": ok, "binding_review": BINDING_REVIEW, "rows": rows}, open(OUT, "w"), indent=1)
    print(f"verified {ok}/{len(recs)}")
    for x in rows:
        if not x["verified"]:
            print("  FAIL", x)
    return 0 if ok == len(recs) else 1


if __name__ == "__main__":
    sys.exit(main())
