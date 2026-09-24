#!/usr/bin/env python3
"""Survey instruments: candidate pairs between LOINC's panels and total scores and SNOMED CT-AU's assessment scales and
score observables. No map joins them -- not LOINC, not Athena, not the LOINC Extension -- so these are FRAMES for a person,
never edges (a match on names is a gap-crossing).

The key is the instrument's acronym, held to three rules that the first drafts showed were needed:
  - on the SNOMED side it must spell the initials of the scale's own name (PHQ-9 <- Patient Health Questionnaire-9),
    so "RAI" (LOINC's Resident Assessment Instrument) cannot meet the Ritchie Articular Index;
  - case is kept (LOINC's ECog, Everyday Cognition, is not SNOMED's ECOG performance scale);
  - the two names share a content word, and an acronym that fans out to more than three SNOMED scales (ADL) is dropped.
Each pair carries a first reading (`my_read`) to speed a reviewer; it is a reading, not a confirmation.

    scripts/survey_candidates.py      # writes reference/survey_instrument_candidates.json
"""
import collections
import json
import os
import re

import duckdb

c = duckdb.connect('out/compendium.duckdb', read_only=True)
L = os.environ.get("LOINC_TABLE", os.path.expanduser("~/Documents/ONTOLOGIES/Loinc_2.83/LoincTable/Loinc.csv"))   # licensed; read in place
lt=c.execute(f"select LOINC_NUM, LONG_COMMON_NAME, CLASS from read_csv('{L}',header=true,all_varchar=true) where CLASSTYPE='4' and STATUS='ACTIVE'").fetchall()
sc=c.execute("""select c.id, c.pt, c.tag, list(distinct d.term) from concept c join dsc d on d.conceptId=c.id and d.active='1'
  where c.tag in ('assessment scale','observable entity') group by 1,2,3""").fetchall()
norm=lambda t: re.sub(r'[^A-Za-z0-9]','',t)   # case kept: ECog is not ECOG
def initials_ok(acr, name):
    """acronym letters are a subsequence of the name's word initials (with 'scale'/'score' allowed), digits appear in the name"""
    letters=re.sub(r'[^A-Za-z]','',acr).upper(); digits=re.sub(r'[^0-9]','',acr)
    words=[w for w in re.split(r'[\s\-/(),]+', name) if w]
    ini=''.join(w[0].upper() for w in words if w[0].isalpha())
    it=iter(ini)
    if len(letters)<3 or not all(ch in it for ch in letters): return False
    return all(d in re.sub(r'[^0-9]','',name) for d in digits) if digits else True
STOP={'CMS','CMSASSESSMENT','PHQ','MDS','OASIS','CCC','HHCC','NIDA','CDC','PROMIS','NMMDS','AHRQ','FACIT','NIHTOOLBOX','REPORTED','OBSERVED'}
def loinc_keys(name):
    ks=set()
    for m in re.findall(r'\[([^\[\]]+)\]\s*$', name):          # the trailing instrument tag
        for t in re.split(r'[ ,;]+', m):
            if re.search(r'[A-Z].*[A-Z]', t) and norm(t).upper() not in STOP: ks.add(norm(t))
    for m in re.findall(r'\(([A-Za-z][A-Za-z0-9\-]{1,13})\)', name):   # "(PHQ-9)"
        if sum(ch.isupper() for ch in m)>=2 and norm(m).upper() not in STOP: ks.add(norm(m))
    return ks
sidx=collections.defaultdict(set)
for i,pt,tag,terms in sc:
    for t in terms:
        for m in set(re.findall(r'\b([A-Z][A-Za-z]*[A-Z][A-Za-z0-9\-]*)\b', t)):
            k=norm(m)
            if len(k)>=3 and (initials_ok(k, pt) or any(initials_ok(k, tt) for tt in terms)):
                sidx[k].add((i,pt,tag))
pairs=set()
for num,name,cls in lt:
    k = 'panel' if cls.startswith('PANEL.') else ('score' if re.search(r'\bscore\b', name, re.I) else None)
    if not k: continue
    for a in loinc_keys(name):
        for i,pt,tag in sidx.get(a,()):
            if (k=='panel' and tag=='assessment scale') or (k=='score' and tag=='observable entity' and re.search(r'score', pt, re.I)):
                pairs.add((k,num,name,a,i,pt))

GENERIC = {'scale', 'score', 'scores', 'questionnaire', 'questionnaires', 'survey', 'index', 'test', 'assessment', 'inventory', 'inventories',
           'form', 'panel', 'total', 'item', 'items', 'version', 'screening', 'tool', 'measure', 'rating', 'instrument', 'short', 'long',
           'self', 'report', 'reported', 'of', 'and', 'the', 'for', 'in', 'with', 't', 'method', 'set', 'study', 'examination', 'exam',
           'evaluation', 'status'}
words = lambda t: {w[:6] for w in re.findall(r'[a-z]{3,}', (t or '').lower()) if w not in GENERIC}
fan = {k: len({i for i, _, _ in v}) for k, v in sidx.items()}
pairs = sorted(p for p in pairs if fan[p[3]] <= 3 and (words(p[2]) & words(p[5])))
# a first reading of each pair (24 Sep 2026), from the two names; a reviewer confirms or rejects
READ = {("91642-9", "273598001"): "different instrument (MOS Social Support Survey vs MOS SF-20)",
        ("91642-9", "273597006"): "different instrument (MOS Social Support Survey vs MOS SF-36)",
        ("70221-7", "481281000000100"): "different version (PCL-C vs PCL-5)",
        ("75842-5", "273364009"): "different instrument (Clinical Disease Activity Index, rheumatoid, vs Crohn's Disease Activity Index)",
        ("71952-6", "1037361000168104"): "different instrument (Child Development Inventory vs MacArthur-Bates CDI)",
        ("89211-7", "273306008"): "narrower instrument (BDI Fast Screen vs the Beck Depression Inventory)",
        ("77565-0", "443223005"): "subscale (BPI pain interference score vs the BPI score)",
        ("71942-7", "736043007"): "different version (CRAFFT vs CRAFFT 2.0)",
        ("89210-9", "273306008"): "SNOMED concept is broader (BDI-II vs the Beck Depression Inventory)",
        ("48543-3", "273481004"): "SNOMED concept is broader (GDS short version vs GDS)",
        ("86946-1", "713863004"): "SNOMED concept is broader (PAM-10 vs the Patient Activation Measure)",
        ("86933-9", "713863004"): "SNOMED concept is broader (PAM-13 vs the Patient Activation Measure)"}
SUBPANEL = re.compile(r"^(Transportation|Recreation|Job-related|Domestic|Quality of life|Pain|Function|Additional item|Memory|Visual)", re.I)
out = []
for kind, num, name, key, sct, pt in pairs:
    read = READ.get((num, sct)) or ("part of the instrument (a sub-panel), not the instrument" if kind == "panel" and SUBPANEL.search(name)
                                    else "likely the same instrument" if kind == "panel" else "likely the same total score")
    out.append({"kind": "panel -> assessment scale" if kind == "panel" else "total score -> score observable", "loinc": num,
                "loinc_name": name, "acronym": key, "sct": sct, "sct_name": pt, "my_read": read})
summary = {"pairs": len(out), "loinc_terms": len({o["loinc"] for o in out}), "snomed_concepts": len({o["sct"] for o in out}),
           "instruments": len({o["acronym"] for o in out}),
           "my_read": dict(collections.Counter(("likely same" if o["my_read"].startswith("likely") else o["my_read"].split(" (")[0]) for o in out))}
json.dump({"_note": "CANDIDATES, not edges: LOINC survey panels and total scores against SNOMED CT-AU assessment scales and score "
                    "observables, keyed by the instrument's acronym (scripts/survey_candidates.py). No published map exists. my_read is a first "
                    "reading from the names, for a reviewer to confirm. LOINC names under the LOINC licence notice; SNOMED CT-AU 20260831.",
           "summary": summary, "candidates": out}, open("reference/survey_instrument_candidates.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1))
