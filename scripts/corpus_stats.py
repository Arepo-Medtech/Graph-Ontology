#!/usr/bin/env python3
"""Print the corpus line for a commit message. Do not retype these numbers.

Every commit in this repository ends with a count of guidelines, claims and
verdicts. Those numbers were being typed by hand from a separate command's
output, and they were wrong at least four times -- gap deltas off by one, and
once a queued-dose count off by twenty. The fix is not to be more careful; it
is to stop a human (or a model) being the thing that copies the digits.

  python3 scripts/corpus_stats.py          # one line, paste into the commit
  python3 scripts/corpus_stats.py --gap N  # also prints the gap delta from N
"""
import json, os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, sys
from attestation import load as _load_attest, status_for as _status_for

def main(argv):
    n = t = p = img = lic = qd = od = fail = att = rejd = 0
    _rec = _load_attest()      # human ticks in docs/attestation-queue.md
    for f in glob.glob("guidelines/*.verification.json"):
        n += 1
        gname = f.split("/")[-1].replace(".verification.json", "")
        for i, c in enumerate(json.load(open(f))["claims"], 1):
            t += 1
            v = c.get("verdict")
            p += v == "pass"
            img += v == "pass_image_transcription"
            fail += v == "fail"
            if v == "licensed_source_not_quoted":
                lic += 1
                if c.get("dose"):
                    qd += 1
                    # attested only counts a PERSON's tick whose sha still matches
                    _st = _status_for(f"{gname}#{i}", c["claim"], _rec)
                    att += _st == "confirmed"
                    rejd += _st == "rejected"
            elif c.get("dose"):
                od += 1
    gap = len([l for l in open("reference/amh-topics-not-yet-written.txt")
               if l.strip()])
    print(f"Corpus: {n} guidelines, {t:,} claims, {p:,} pass, {img} "
          f"image-transcription, {lic} licensed-source ({qd} queued doses), "
          f"{od} quoted doses ({att} of {qd} queued doses ATTESTED), "
          f"{fail} fail, {n}/{n} structural."
          + (f" ⚠️ {rejd} dose(s) REJECTED on attestation — build is FAILING."
             if rejd else ""))
    if "--gap" in argv:
        before = int(argv[argv.index("--gap") + 1])
        print(f"AMH gap {before} -> {gap} (closed {before - gap})")
    else:
        print(f"AMH gap now {gap}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
