"""End-to-end check of the pass_paraphrase_anchored verdict through verify.check.  python3 scripts/test_anchor_verify.py"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify, anchor

SRC = "Give cefalexin 20 mg/kg (max 750 mg) orally three times daily for 5 days. Review at 48 hours."
FRAG = "cefalexin 20 mg/kg (max 750 mg) orally three times daily for 5 days"
GOOD = "Cefalexin 20 mg/kg (up to 750 mg) by mouth, three times a day, for 5 days."


def run(claim, src=SRC):
    sf = tempfile.mktemp(); open(sf, "w").write(src)
    d = {"guideline": "x", "verified_utc": "t", "verifier": "v", "verifier_class": "single_verifier_uncalibrated",
         "method": "m", "retrieved_from": ["u"], "summary": {"total": 1, "pass": 0, "fail": 0},
         "claims": [{"claim": claim, "source": "S1", "verdict": "pass_paraphrase_anchored", "locator": "L",
                     "anchors": [anchor.make(FRAG)]}]}
    f = tempfile.mktemp(suffix=".json"); json.dump(d, open(f, "w"))
    return verify.check(f, sf)[0]


assert run(GOOD) == [], run(GOOD)
assert any("not in the anchored" in e for e in run("Cefalexin 25 mg/kg three times a day for 5 days."))
assert any("NOT A PARAPHRASE" in e for e in run("give cefalexin 20 mg kg max 750 mg orally three times daily for 5 days"))
assert any("ANCHOR NOT FOUND" in e for e in run(GOOD, SRC.replace("750", "500")))
print("anchored-paraphrase verify tests ok")
