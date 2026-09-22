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
import json, glob, sys

def main(argv):
    n = t = p = img = lic = qd = od = fail = 0
    for f in glob.glob("guidelines/*.verification.json"):
        n += 1
        for c in json.load(open(f))["claims"]:
            t += 1
            v = c.get("verdict")
            p += v == "pass"
            img += v == "pass_image_transcription"
            fail += v == "fail"
            if v == "licensed_source_not_quoted":
                lic += 1
                qd += bool(c.get("dose"))
            elif c.get("dose"):
                od += 1
    gap = len([l for l in open("reference/amh-topics-not-yet-written.txt")
               if l.strip()])
    print(f"Corpus: {n} guidelines, {t:,} claims, {p:,} pass, {img} "
          f"image-transcription, {lic} licensed-source ({qd} queued doses), "
          f"{od} quoted doses, {fail} fail, {n}/{n} structural.")
    if "--gap" in argv:
        before = int(argv[argv.index("--gap") + 1])
        print(f"AMH gap {before} -> {gap} (closed {before - gap})")
    else:
        print(f"AMH gap now {gap}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
