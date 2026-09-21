#!/usr/bin/env python3
"""Re-apply human binding decisions after a binder run.

A binder run rewrites snomed_bindings.json wholesale. Without this step every
improvement to the binder silently discards the review work done since the last
one — and the 348-candidate queue resets. Run it after every bind.

Corrections win over whatever the binder produced, and say so in the record.
"""
import json, pathlib, sys

BIND = pathlib.Path("reference/snomed_bindings.json")
CORR = pathlib.Path("reference/binding_corrections.json")

def apply(bindings, corrections):
    by = {c["condition"]: c for c in corrections}
    applied = missing = 0
    for r in bindings["results"]:
        c = by.get(r["condition"])
        if not c:
            continue
        if c["state"] == "rejected":
            r["snomed"] = None
            r["method"] = "rejected_by_human"
            r["why"] = c.get("why")
        else:
            r["snomed"] = {k: v for k, v in c.items()
                           if k not in ("condition", "state")} | {"state": c["state"]}
            r.pop("method", None); r.pop("candidates", None)
        applied += 1
    seen = {r["condition"] for r in bindings["results"]}
    missing = [c for c in by if c not in seen]
    return applied, missing

def demo():
    b = {"results": [{"condition": "A", "snomed": {"concept_id": "1"}},
                     {"condition": "B", "snomed": None, "method": "candidate_unconfirmed",
                      "candidates": [{"code": "9"}]},
                     {"condition": "C", "snomed": {"concept_id": "3"}}]}
    c = [{"condition": "B", "state": "corrected_pending_attestation", "concept_id": "2", "why": "w"},
         {"condition": "C", "state": "rejected", "why": "no"},
         {"condition": "GONE", "state": "attested", "concept_id": "4"}]
    n, missing = apply(b, c)
    assert n == 2, n
    assert b["results"][1]["snomed"]["concept_id"] == "2"
    assert b["results"][1]["snomed"]["state"] == "corrected_pending_attestation"
    assert "candidates" not in b["results"][1], "a corrected row keeps no stale candidates"
    assert b["results"][2]["snomed"] is None and b["results"][2]["method"] == "rejected_by_human"
    assert b["results"][0]["snomed"]["concept_id"] == "1", "uncorrected rows untouched"
    assert missing == ["GONE"], missing   # a correction for a vanished condition must be reported
    print("self-check ok")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo(); raise SystemExit(0)
    b = json.loads(BIND.read_text())
    c = json.loads(CORR.read_text())["corrections"]
    n, missing = apply(b, c)
    b["human_corrections_applied"] = n
    BIND.write_text(json.dumps(b, indent=2))
    print(f"applied {n} correction(s)")
    for m in missing:
        print(f"  WARNING: correction exists for a condition not in this run: {m}")
