#!/usr/bin/env python3
"""Look up drugs in the cached PBS schedule and emit an 'Australian context' table.

  python3 scripts/pbs_lookup.py allopurinol colchicine febuxostat
  python3 scripts/pbs_lookup.py --md naltrexone acamprosate disulfiram

Reads cache/pbs/items.json (PBS Public API v3). Matching is case-insensitive on
drug_name, then on li_drug_name, then substring. A drug that returns nothing is
reported as NOT FOUND rather than omitted -- absence from the PBS schedule is a
finding, not a blank.

benefit_type_code, as confirmed against the gout guideline's hand-built table:
  U unrestricted | R restricted benefit
  A authority required | S authority required (streamlined)

A program_code other than GE is appended. Glosses marked * are inferred from the
drugs the code contains in this cache, not from a published key; an unglossed
code is printed raw rather than guessed at.
"""
import json, os, sys, collections

BENEFIT = {"U": "unrestricted", "R": "restricted benefit",
           "A": "authority required", "S": "authority required (streamlined)"}
# program_code. GE (general schedule) is the unremarkable default and is not
# surfaced. These glosses are INFERRED from the drugs each code actually contains
# in this cache, not from a published PBS key -- they are labelled as inferred
# wherever they appear, and a code with no confident reading is printed raw.
PROGRAM = {"HB": "s100 highly specialised (community)",
           "HS": "s100 highly specialised (public hospital)",
           "R1": "s100 remote area Aboriginal health service",
           "PL": "palliative care schedule",
           "EP": "extemporaneous / compounding ingredient"}
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    p = os.path.join(HERE, "cache", "pbs", "items.json")
    return [r for r in json.load(open(p))["rows"] if r.get("drug_name")]


def find(rows, name):
    n = name.lower().strip()
    hits = [r for r in rows if (r.get("drug_name") or "").lower() == n]
    if not hits:
        hits = [r for r in rows if (r.get("li_drug_name") or "").lower() == n]
    if not hits:
        hits = [r for r in rows if n in (r.get("drug_name") or "").lower()]
    if not hits:
        # last resort: the schedule may name the salt-free moiety ("valproate"
        # for "sodium valproate"). Match the longest schedule name contained in
        # the query, and report what was matched so it is never silent.
        cand = sorted({r["drug_name"] for r in rows
                       if (r["drug_name"] or "").lower() in n and len(r["drug_name"]) > 4},
                      key=len, reverse=True)
        if cand:
            hits = [r for r in rows if r["drug_name"] == cand[0]]
            for h in hits:
                h = h.setdefault("_matched_as", cand[0])
    return hits


def summarise(hits):
    ben = sorted({r["benefit_type_code"] for r in hits})
    prog = sorted({r["program_code"] for r in hits})
    forms = sorted({(r.get("li_form") or "").strip() for r in hits if r.get("li_form")})
    return ben, prog, forms


def main(argv):
    md = "--md" in argv
    names = [a for a in argv if not a.startswith("--")]
    if not names:
        print(__doc__)
        return 2
    rows = load()
    if md:
        print("| Agent | PBS | Benefit type |")
        print("|---|---|---|")
    for name in names:
        hits = find(rows, name)
        if not hits:
            print(f"| {name.title()} | **not listed** | — |" if md
                  else f"{name}: NOT FOUND in schedule")
            continue
        ben, prog, forms = summarise(hits)
        btxt = " / ".join(BENEFIT.get(b, b) for b in ben)
        extra = [p for p in prog if p != "GE"]
        ptxt = "".join(
            f" · {PROGRAM[p]}*" if p in PROGRAM else f" · program {p}"
            for p in extra)
        if md:
            f = "; ".join(forms[:3]) + ("; …" if len(forms) > 3 else "")
            as_ = hits[0].get("_matched_as")
            tag = f" *(schedule lists as **{as_}**)*" if as_ else ""
            print(f"| {name.title()} | listed — {f}{ptxt}{tag} | **{btxt}** |")
        else:
            print(f"{name}: {len(hits)} items | benefit {ben} | programs {prog}")
            for f in forms[:8]:
                print(f"    {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
