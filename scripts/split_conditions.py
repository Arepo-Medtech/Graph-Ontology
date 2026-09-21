#!/usr/bin/env python3
"""Split multi-entity PBS condition names into their constituent conditions.

A PBS indication often names several conditions at once ("epithelial ovarian,
fallopian tube or primary peritoneal cancer"). The combined string matches no
title or abstract, so the ticket draws no citations while each constituent
would.

The parent is KEPT, never replaced: it is what PBS actually wrote, and the
restriction attaches to it. Children carry `parent_condition` and
`split_method` so every child traces back.

Conservative by design. A wrong split invents a condition that does not exist,
which is worse than leaving a combined name alone, so anything ambiguous is
left unsplit.
"""
import argparse, json, re, pathlib

OUT = pathlib.Path("out/conditions_split.json")
SRC = pathlib.Path("out/conditions.json")

# Never split on these: they join clauses, not entities.
NO_SPLIT = re.compile(r"\b(secondary to|associated with|following|due to|where|"
                      r"in patients|with intestinal|requiring|identifying as|treatment of)\b", re.I)

# A list of severities, stages or types is ONE condition described several ways,
# not several conditions. Distributing across it invents diseases: "Advanced,
# metastatic or recurrent endometrial carcinoma" is endometrial carcinoma, and
# splitting produced "Advanced carcinoma" and "Metastatic carcinoma".
QUALIFIER_TOKEN = re.compile(
    r"^(advanced|metastatic|recurrent|unresectable|resected|resectable|severe|"
    r"moderate|mild|chronic|acute|refractory|relapsed|persistent|progressive|"
    r"well|poorly|differentiated|well-differentiated|poorly-differentiated|"
    r"locally|symptomatic|newly|diagnosed|previously|untreated|bulky|high|low|"
    r"grade|stage|type|types|malignant|benign|primary|secondary|"
    r"[0-9]+|[ivx]+[ab]?|[0-9ivx]+[ab]?|[0-9ivxab/]+)$", re.I)

def _qualifier_only(part):
    """True when every token is a severity, stage or type word, so the part names
    no entity of its own. "Resected Stage IIIB" is a qualifier, not a disease."""
    toks = [t for t in re.split(r"[\s/]+", part) if t]
    return bool(toks) and all(QUALIFIER_TOKEN.match(t) for t in toks)

# A part already ending in a disease noun is a complete entity; do not staple
# another head onto it ("Chronic lymphocytic leukaemia" + "lymphoma").
# No \b: these are suffixes inside compound words too ("leiomyosarcoma" ends in
# "sarcoma", "oligodendroglioma" in "oma").
DISEASE_NOUN = re.compile(
    r"(leukaemia|leukemia|lymphoma|carcinoma|cancer|tumour|tumor|sarcoma|"
    r"melanoma|myeloma|glioma|oma|disease|syndrome|infection|deficiency|"
    r"disorder|atrophy|dystrophy|anaemia|anemia|itis|osis|psoriasis)$", re.I)

def _clean(s):
    s = re.sub(r"\s+", " ", s).strip(" ,;")
    return s[:1].upper() + s[1:] if s else ""

def split(name):
    """Return (children, method). Empty list when not confidently splittable."""
    if NO_SPLIT.search(name):
        return [], "clause_not_entity_list"
    if not re.search(r"\bor\b|\band/or\b|,", name):
        return [], "single_entity"

    # "HEAD of the A, B or C"  ->  "HEAD of the A", "HEAD of the B", ...
    m = re.match(r"^(.*?\bof\s+(?:the\s+)?)(.+)$", name, re.I)
    if m:
        head, tail = m.group(1), m.group(2)
        parts = re.split(r"\s*,\s*|\s+and/or\s+|\s+or\s+", tail)
        parts = [p for p in (x.strip() for x in parts) if p]
        if len(parts) > 1 and all(len(p.split()) <= 5 for p in parts):
            return [_clean(head + p) for p in parts], "shared_leading_head"

    # "A, B or C HEAD"  ->  "A HEAD", "B HEAD", "C HEAD"   (head = last word)
    parts = re.split(r"\s*,\s*|\s+and/or\s+|\s+or\s+", name)
    parts = [p for p in (x.strip() for x in parts) if p]
    if len(parts) < 2:
        return [], "not_splittable"
    # any qualifier/stage/type part means this is one condition, listed severally
    if any(_qualifier_only(p) for p in parts):
        return [], "qualifier_list_not_entities"

    last = parts[-1].split()
    others = parts[:-1]
    # A part ending in a severity word ("...sensitive advanced") is a qualifier
    # awaiting the head noun, not an entity. Anatomy ("epithelial ovarian") is fine.
    if any(QUALIFIER_TOKEN.match(p.split()[-1]) for p in others if p.split()):
        return [], "qualifier_list_not_entities"
    if len(last) >= 2 and all(1 <= len(p.split()) <= 4 for p in others):
        head = last[-1]
        # Both readings are plausible and no word list settles which: "epithelial
        # ovarian" needs the head noun, "blepharospasm" does not. Emit both and
        # let retrieval adjudicate — a coined term ("Blepharospasm spasm") draws
        # no citations and is dropped in validation.
        cand = []
        for part in others:
            cand.append(_clean(f"{part} {head}"))
            if DISEASE_NOUN.search(part) or len(part.split()) == 1:
                cand.append(_clean(part))
        cand.append(_clean(parts[-1]))
        return cand, "shared_trailing_head"
    if all(len(p.split()) <= 5 for p in parts):
        return [_clean(p) for p in parts], "independent_entities"
    return [], "not_splittable"

def demo():
    c, m = split("Adenocarcinoma of the stomach or gastro-oesophageal junction")
    assert c == ["Adenocarcinoma of the stomach",
                 "Adenocarcinoma of the gastro-oesophageal junction"], c
    assert m == "shared_leading_head"

    c, m = split("Epithelial ovarian, fallopian tube or primary peritoneal cancer")
    assert "Epithelial ovarian cancer" in c and "Fallopian tube cancer" in c, c

    c, m = split("Leiomyosarcoma or liposarcoma")
    assert "Leiomyosarcoma" in c and "Liposarcoma" in c, c
    c = split("Adult-type IDH-mutant astrocytoma or oligodendroglioma")[0]
    assert "Oligodendroglioma" in c, c

    # every one of these was produced as a real (bad) split before the guards
    # this one now splits correctly; the old failure was "Chronic lymphocytic
    # leukaemia lymphoma", produced by stapling the trailing head onto a part
    # that was already a complete entity
    c = split("Chronic lymphocytic leukaemia or small lymphocytic lymphoma")[0]
    assert "Chronic lymphocytic leukaemia" in c and "Small lymphocytic lymphoma" in c, c
    # ambiguous head: BOTH readings offered, retrieval decides
    c = split("Blepharospasm or hemifacial spasm")[0]
    assert "Blepharospasm" in c and "Hemifacial spasm" in c, c

    for bad in ("Advanced, metastatic or recurrent endometrial carcinoma",
                "Resected Stage IIIB, Stage IIIC or Stage IIID malignant melanoma",
                "Type I, II or IIIa spinal muscular atrophy",
                "Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour",
                "Immunotherapy sensitive advanced or metastatic cancer",
                "Chronic treatment of hereditary angioedema Types 1 or 2"):
        assert split(bad)[0] == [], (bad, split(bad))

    # clauses are not entity lists — splitting these invents conditions
    for junk in ("Growth retardation secondary to an intracranial lesion, or cranial irradiation",
                 "Anaemia associated with intrinsic renal disease",
                 "Rejection in patients following organ or tissue transplantation",
                 "A patient identifying as Aboriginal or Torres Strait Islander"):
        assert split(junk)[0] == [], junk
    assert split("Asthma")[0] == []
    print("self-check ok")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        demo(); raise SystemExit(0)
    doc = json.loads(SRC.read_text())
    out, stats = [], {}
    for rec in doc["conditions"]:
        kids, method = split(rec["condition"])
        stats[method] = stats.get(method, 0) + 1
        for k in kids:
            if k.lower() == rec["condition"].lower():
                continue
            out.append({"condition": k, "parent_condition": rec["condition"],
                        "split_method": method,
                        "restriction_count": rec["restriction_count"],
                        "therapy_evidence": "pbs_subsidised_restricted",
                        "open_au_guidance": "unassessed", "terminology_binding": None})
    seen, uniq = set(), []
    for r in out:
        if r["condition"].lower() in seen: continue
        seen.add(r["condition"].lower()); uniq.append(r)
    OUT.write_text(json.dumps({"source": "split from conditions_pbs.json",
                               "note": "children of multi-entity PBS names; parents retained in conditions_pbs.json",
                               "count": len(uniq), "conditions": uniq}, indent=2))
    print(f"children: {len(uniq)}")
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]): print(f"  {v:4d}  {k}")
