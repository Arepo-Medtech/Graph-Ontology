#!/usr/bin/env python3
"""Triage the no-guideline PBS conditions into work: true gaps by specialty, duplicates, artefacts, near-misses.

Input: reference/no_guideline_pbs.json (scripts/no_guideline_pbs.py) + cache/pbs item-atc tables.
Specialty is a ROUTING heuristic, not a classification: condition-name keywords first (a cancer is
oncology whatever drug treats it), else the dominant ATC level-2 class of the condition's PBS items.

  python3 scripts/no_guideline_triage.py            # -> reference/no_guideline_triage.json
  python3 scripts/no_guideline_triage.py --selftest
"""
import collections, glob, json, os, re, sys
sys.path.insert(0, "scripts")
from no_guideline_pbs import near_misses

NAME_RULES = [  # first match wins
    (r"cancer|carcinoma|melanoma|sarcoma|tumou?r|neoplas|glioma|blastoma|mesothelioma|adenocarcinoma", "Oncology (solid tumours)"),
    (r"leukaemia|lymphoma|myeloma|myelodysplast|myelofibrosis|polycythaemia|macroglobulin|mastocytosis|thrombocythaemia", "Haematological malignancy"),
    (r"arthritis|spondyl|lupus|vasculitis|giant cell|still|gout|scleroderma|systemic sclerosis", "Rheumatology"),
    (r"psoria|hidradenitis|dermatitis|urticaria|pemphig|acne|alopecia|vitiligo|dermatos|skin", "Dermatology"),
    (r"colitis|crohn|bowel|hepat|liver|biliary|cholangitis|pancrea|oesophag|gastr|coeliac", "Gastroenterology & hepatology"),
    (r"growth|stature|acromegaly|pituitar|prolactin|puberty|thyro|adrenal|cushing|hypogonad|diabet|parathyr|hypophosph|osteo", "Endocrinology"),
    (r"haemophilia|haemoglobinuria|uraemic|anaemia|thrombocytopenia|neutropenia|sickle|thalass|haemoly|willebrand|angioedema|thrombo", "Haematology"),
    (r"sclerosis|epilep|seizure|spasticity|dystonia|parkinson|muscular|myasthenia|neuropath|migraine|huntington|ataxia|spasm", "Neurology"),
    (r"schizo|depress|bipolar|anxiety|psychos|adhd|attention|dementia|behavioural|alcohol|opioid|nicotine|phobic", "Psychiatry & addiction"),
    (r"cystic fibrosis|pulmonary|asthma|copd|lung|respirat|bronch|idiopathic pulmonary", "Respiratory"),
    (r"macula|retin|uveitis|choroid|ocular|eye|glaucoma|keratitis", "Ophthalmology"),
    (r"kidney|renal|nephr|dialysis|transplant|allograft", "Nephrology & transplant"),
    (r"hiv|hepatitis|infection|fung|aspergill|candid|tubercul|cytomegalo|bacterial|viral|malaria|sepsis|mycos", "Infectious diseases"),
    (r"phenylketon|urea cycle|tyrosin|homocystin|metabol|lysosomal|gaucher|fabry|pompe|mucopolysacch|storage", "Metabolic & genetic"),
]
ATC_RULES = {"L01": "Oncology (solid tumours)", "L02": "Oncology (solid tumours)", "L03": "Haematology", "L04": "Immunology (other)",
             "H01": "Endocrinology", "H02": "Endocrinology", "H03": "Endocrinology", "H05": "Endocrinology", "A10": "Endocrinology",
             "A16": "Metabolic & genetic", "V06": "Metabolic & genetic", "B01": "Haematology", "B02": "Haematology", "B03": "Haematology",
             "B06": "Haematology", "J01": "Infectious diseases", "J02": "Infectious diseases", "J04": "Infectious diseases", "J05": "Infectious diseases",
             "J06": "Immunology (other)", "S01": "Ophthalmology", "R03": "Respiratory", "R05": "Respiratory", "R07": "Respiratory"}
FIRST = {"A": "Gastroenterology & hepatology", "C": "Cardiology", "D": "Dermatology", "G": "Women's health & urology", "M": "Musculoskeletal",
         "N": "Neurology", "R": "Respiratory", "S": "Ophthalmology", "V": "Other (antidotes, diagnostics, nutrition)"}


# PBS listing policy that the condition parser took for a disease (see docs/condition-list.md)
ADMIN = re.compile(r"^(a )?patients? (identifying|unable|who)|base-priced|^(adverse effects|drug interactions) (occurring|expected)|"
                   r"^assisting|^ablation of|^above |^transfer to|^the condition", re.I)


def specialty(name, atc2s):
    for pat, sp in NAME_RULES:
        if re.search(pat, name, re.I):
            return sp, "name"
    if atc2s:
        top = atc2s.most_common(1)[0][0]
        return ATC_RULES.get(top) or FIRST.get(top[:1], "Other"), f"atc:{top}"
    return "Unclassified", "none"


def triage(rows, atc_of, slugs):
    names = {r["condition"] for r in rows}
    out = []
    for r in rows:
        atc2 = collections.Counter(a[:3] for p in r["pbs_codes"] for a in atc_of.get(p, ()))
        sp, how = specialty(r["condition"], atc2)
        content = [w for w in re.findall(r"[a-z]+", r["condition"].lower()) if len(w) > 2]
        nm = near_misses(r["condition"], slugs)
        fragment = (len(content) <= 1 and not r["snomed"]
                    and not re.search(r"(aemia|oma|itis|osis|ism|rhythmia)$", r["condition"].lower()))
        if ADMIN.search(r["condition"]):
            kind = "admin"             # listing policy, not a condition
        elif r["via_parent"] and fragment:
            kind = "artefact"          # split fragment such as "Bone", "Definite", "Fungal" (real one-word diseases are bound or disease-shaped)
        elif r["via_parent"] and r["via_parent"] in names:
            kind = "duplicate"         # same PBS listing as its parent row, which is also a gap
        elif nm:
            kind = "near_miss"         # an existing guideline may already cover it
        else:
            kind = "gap"
        out.append({**{k: r[k] for k in ("condition", "via_parent", "restrictions_current", "access", "drugs", "snomed")},
                    "n_items": len(r["pbs_codes"]), "specialty": sp, "specialty_basis": how,
                    "atc2": [a for a, _ in atc2.most_common(3)], "kind": kind, "near_miss": nm})
    return out


def selftest():
    rows = [{"condition": "Epithelial ovarian, fallopian tube or primary peritoneal cancer", "via_parent": None, "restrictions_current": 14,
             "access": {}, "drugs": ["Olaparib"], "snomed": None, "pbs_codes": ["1A"]},
            {"condition": "Fallopian tube cancer", "via_parent": "Epithelial ovarian, fallopian tube or primary peritoneal cancer",
             "restrictions_current": 14, "access": {}, "drugs": ["Olaparib"], "snomed": None, "pbs_codes": ["1A"]},
            {"condition": "Bone", "via_parent": "Bone or joint infection", "restrictions_current": 1, "access": {}, "drugs": [], "snomed": None, "pbs_codes": []},
            {"condition": "Acromegaly", "via_parent": None, "restrictions_current": 15, "access": {}, "drugs": ["Octreotide"], "snomed": None, "pbs_codes": ["2B"]},
            {"condition": "Diabetes mellitus type 2", "via_parent": None, "restrictions_current": 19, "access": {}, "drugs": [], "snomed": None, "pbs_codes": []}]
    t = {x["condition"]: x for x in triage(rows, {"1A": ["L01XK01"], "2B": ["H01CB02"]}, ["type-2-diabetes"])}
    assert t["Fallopian tube cancer"]["kind"] == "duplicate", t["Fallopian tube cancer"]
    assert t["Bone"]["kind"] == "artefact"
    adm = triage([{"condition": "Drug interactions expected to occur with all of the base-priced drugs", "via_parent": None,
                   "restrictions_current": 1, "access": {}, "drugs": [], "snomed": None, "pbs_codes": []}], {}, [])[0]
    assert adm["kind"] == "admin", adm
    sep = triage([{"condition": "Septicaemia", "via_parent": "Septicaemia, proven", "restrictions_current": 1, "access": {}, "drugs": [],
                   "snomed": None, "pbs_codes": []}], {}, [])[0]
    assert sep["kind"] == "gap", sep
    assert t["Diabetes mellitus type 2"]["kind"] == "near_miss"
    assert t["Acromegaly"]["kind"] == "gap" and t["Acromegaly"]["specialty"] == "Endocrinology"
    assert t["Epithelial ovarian, fallopian tube or primary peritoneal cancer"]["specialty"] == "Oncology (solid tumours)"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); raise SystemExit(0)
    rows = json.load(open("reference/no_guideline_pbs.json"))["conditions"]
    atc_of = collections.defaultdict(list)
    for x in json.load(open("cache/pbs/item-atc-relationships.json"))["rows"]:
        atc_of[x["pbs_code"]].append(x["atc_code"])
    slugs = sorted(os.path.basename(f)[:-3] for f in glob.glob("guidelines/*.md"))
    out = triage(rows, atc_of, slugs)
    json.dump({"source": "reference/no_guideline_pbs.json + PBS item-atc-relationships (schedule 4333)", "count": len(out), "conditions": out},
              open("reference/no_guideline_triage.json", "w"), indent=1, ensure_ascii=False)
    k = collections.Counter(x["kind"] for x in out)
    print(dict(k))
    sp = collections.Counter(x["specialty"] for x in out if x["kind"] == "gap")
    for s, n in sp.most_common():
        print(f"  {n:4d}  {s}")
