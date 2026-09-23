#!/usr/bin/env python3
"""Validate candidate SNOMED codes against the live NCTS, pinned to SNOMED CT-AU.

This does NOT decide a binding. It answers two narrower questions the worksheet
cannot: does the candidate code still resolve in the pinned release, and is the
display recorded in this repo the display the terminology actually returns?

⚠️ FAIL-SAFE, from the client's own contract: validated=false means UNVALIDATED,
never "invalid". A code that fails to resolve is reported as unresolved and left
for a person; nothing is deleted or rebound on the strength of it.

  python3 scripts/validate_bindings_ncts.py            # all distinct top-hit codes
  python3 scripts/validate_bindings_ncts.py --limit 20
"""
import json, re, subprocess, sys, os

CLIENT_DIR = "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed"
REVIEW = "reference/snomed_candidates_review.json"
OUT    = "reference/binding_validation.json"

def lookup(code):
    """-> (validated, display, version). Never raises on a bad code."""
    try:
        r = subprocess.run(["node", "--env-file=.env", "ncts-client.mjs", code],
                           cwd=CLIENT_DIR, capture_output=True, text=True, timeout=60)
    except Exception as e:
        return (None, None, f"client error: {e}")
    t = r.stdout
    ok = "validated: true" in t
    m = re.search(r"display: '([^']*)'", t)
    v = re.search(r"version/(\d+)", t)
    return (ok, m.group(1) if m else None, v.group(1) if v else None)

def main(argv):
    rev = json.load(open(REVIEW))
    pairs = {}
    for c in rev["candidates"]:
        t = c.get("top_hit") or {}
        if t.get("code"):
            pairs.setdefault(t["code"], t.get("display", ""))
    codes = sorted(pairs)
    if "--limit" in argv:
        codes = codes[:int(argv[argv.index("--limit") + 1])]
    res, unresolved, drift = [], 0, 0
    for n, code in enumerate(codes, 1):
        ok, disp, ver = lookup(code)
        d = {"code": code, "recorded_display": pairs[code], "validated": bool(ok),
             "ncts_display": disp, "version": ver}
        if not ok:
            unresolved += 1
            d["note"] = "UNVALIDATED - not confirmed present in the pinned release. NOT a finding of invalidity."
        elif disp and pairs[code] and disp.strip() != pairs[code].strip():
            drift += 1
            d["note"] = "DISPLAY DRIFT - the repo's recorded display differs from the terminology's"
        res.append(d)
        if n % 25 == 0:
            print(f"  {n}/{len(codes)}", flush=True)
    out = {"_note": "Live NCTS validation of candidate top-hit codes. Does NOT decide any binding.",
           "_failsafe": "validated=false means UNVALIDATED, never invalid. Nothing is rebound or "
                        "deleted on the strength of a false.",
           "checked_utc": "2026-09-23", "codes_checked": len(res),
           "validated": len(res) - unresolved, "unresolved": unresolved, "display_drift": drift,
           "results": res}
    open(OUT, "w").write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"{OUT}: {len(res)} codes, {len(res)-unresolved} validated, "
          f"{unresolved} UNRESOLVED, {drift} display drift")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
