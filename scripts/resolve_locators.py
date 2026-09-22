#!/usr/bin/env python3
"""Re-point bundled licensed-source locators at a single named AMH monograph.

A locator on a licensed_source_not_quoted claim is the ONLY thing a person has
to find the passage again -- no source_text is stored, by design. Early
guidelines wrote one bundled locator shared by every monograph claim ("drug
monographs levodopa..., pramipexole, rotigotine, rasagiline, entacapone,
amantadine"), which tells the attester the dose is in one of six documents and
gives a URL for none of them. This rewrites those to name the exact monograph
AMH itself names, with its path.

The monograph a claim belongs to is READ OFF THE CLAIM TEXT, not guessed:
the claim names its drug. Combination names are matched first and consumed, so
"adapalene with benzoyl peroxide" does not also match "adapalene". A claim that
names no monograph, or whose named monograph is not in the resolved table, is
LEFT ALONE and reported -- this never invents a locator it cannot justify.

Nothing else changes: no claim text, no verdict, no dose flag, no source_text
(licensed claims carry none and must not). Run with --write to apply.

  python3 scripts/resolve_locators.py            # report only
  python3 scripts/resolve_locators.py --write
"""
import json, glob, re, sys

BASE = "https://amhonline.amh.net.au"
import os
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# name -> [AMH title, path, claim-text patterns]. Every path was confirmed present
# in AMH's own drug index (1,234 entries) on 2026-09-22.
MONO = json.load(open(os.path.join(_HERE, "reference/amh-monograph-paths.json")))
REL = "July 2026 release, read under subscription 2026-09-22"

# Only these guidelines' claims are in scope, and within each only the drugs the
# ORIGINAL bundled locator already named -- so a stray word in a claim cannot
# pull in a monograph the author never read.
POOL = {
 "acne": ["adapalene-benzoyl-peroxide", "clindamycin-benzoyl-peroxide", "clindamycin-tretinoin",
          "adapalene", "tretinoin-skin", "trifarotene", "benzoyl-peroxide", "azelaic-acid",
          "clascoterone", "doxycycline", "minocycline", "erythromycin", "isotretinoin"],
 "eating-disorders": ["fluoxetine", "lisdexamfetamine"],
 "opioid-dependence": ["buprenorphine-naloxone", "buprenorphine-opioid-dependence",
                       "methadone-opioid-dependence", "naltrexone"],
 "parkinsons-disease": ["levodopa-benserazide-carbidopa", "pramipexole", "rotigotine",
                        "rasagiline", "entacapone", "amantadine"],
 "psoriasis": ["calcipotriol-betamethasone", "methotrexate-immunomodulator", "ciclosporin",
               "apremilast", "acitretin"],
 "rosacea": ["metronidazole-skin", "azelaic-acid", "ivermectin-skin", "brimonidine-skin",
             "doxycycline", "erythromycin", "isotretinoin"],
 "thyroid-disorders": ["levothyroxine", "liothyronine", "carbimazole", "propylthiouracil",
                       "propranolol"],
 "vertigo": ["betahistine", "cinnarizine-dimenhydrinate", "prochlorperazine"],
}


def match(text, pool):
    """Which monographs does this claim name? Longest pattern first, consumed."""
    t = " " + text.lower() + " "
    pats = sorted(((p, k) for k in pool for p in MONO[k][2]),
                  key=lambda x: -len(x[0]))
    hits = []
    for pat, key in pats:
        if key in hits:
            continue
        m = re.search(r"\b" + re.escape(pat) + r"\b", t)
        if m:
            hits.append(key)
            t = t[:m.start()] + " " * (m.end() - m.start()) + t[m.end():]
    return [k for k in pool if k in hits]      # stable, pool order


def locator_for(keys):
    if len(keys) == 1:
        title, path, _ = MONO[keys[0]]
        return f"AMH Medicines, drug monograph '{title}' at {BASE}{path}, {REL}"
    parts = "; ".join(f"'{MONO[k][0]}' at {BASE}{MONO[k][1]}" for k in keys)
    return f"AMH Medicines, drug monographs {parts}, {REL}"


def main(write):
    changed = untouched = 0
    for f in sorted(glob.glob("guidelines/*.verification.json")):
        name = f.split("/")[-1].replace(".verification.json", "")
        if name not in POOL:
            continue
        d = json.load(open(f))
        urls, hit = set(d.get("retrieved_from") or []), False
        for i, c in enumerate(d["claims"], 1):
            if c.get("verdict") != "licensed_source_not_quoted":
                continue
            loc = c.get("locator", "")
            if "monograph" not in loc:          # therapeutic-topic locators stay
                continue
            if "amhonline.amh.net.au" in loc:   # already resolved
                continue
            keys = match(c["claim"], POOL[name])
            if not keys:
                print(f"  UNRESOLVED {name} claim {i}: {c['claim'][:72]}")
                untouched += 1
                continue
            c["locator"] = locator_for(keys)
            urls.update(BASE + MONO[k][1] for k in keys)
            changed += 1
            hit = True
        if hit:
            d["retrieved_from"] = sorted(urls)
            if write:
                json.dump(d, open(f, "w"), indent=1, ensure_ascii=False)
            print(f"{'wrote' if write else 'would write'}  {name}: "
                  f"{len(d['retrieved_from'])} retrieved_from url(s)")
    print(f"\n{changed} locator(s) re-pointed, {untouched} left unresolved")
    return 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
