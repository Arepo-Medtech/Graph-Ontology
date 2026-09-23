"""Flag any number in a pass claim that its own source_text does not contain.
The verbatim check proves the quote exists; this catches a claim that says more than its quote."""
import json, re, sys
NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")
def nums(s): return {n.replace(",", "") for n in NUM.findall(s)}
bad = 0
for p in sys.argv[1:]:
    for i, c in enumerate(json.load(open(p))["claims"]):
        if c["verdict"] != "pass": continue
        extra = nums(c["claim"]) - nums(c["source_text"])
        if extra:
            bad += 1; print(f"{p.split('/')[-1].split('.')[0]}#{i}: {sorted(extra)} :: {c['claim'][:110]}")
print(f"{bad} claim(s) with numbers not in their quote")
