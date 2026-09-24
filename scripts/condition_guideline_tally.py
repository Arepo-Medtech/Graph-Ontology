#!/usr/bin/env python3
"""Tally PBS conditions against guidelines, verification state and SNOMED bindings.

⚠️ MATCHING IS BY NAME, AND NAME MATCHING CANNOT SETTLE THIS. Exact normalised
match gives 59; token-containment gives 135; a loose content-word overlap gives
~202 and is mostly noise (it pairs Multiple myeloma with Multiple sclerosis).
The band is reported rather than a single figure, because the honest answer
needs the SNOMED bindings -- which is what the 349-candidate review queue is
for, and it is unfinished.

  python3 scripts/condition_guideline_tally.py
"""
import json, glob, os, re, collections
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from guidelines_source import guidelines_dir, guideline_url, guidelines_file, verification_dir
G = guidelines_dir()
def norm(s):
    s=s.lower().replace("’","'"); s=re.sub(r"'s\b","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()
conds=json.load(open("reference/conditions.json"))["conditions"]
binds={r["condition"]:r for r in json.load(open("reference/snomed_bindings.json"))["results"]}
cover=json.load(open(guidelines_file("reference/amh-topic-coverage.json")))
slugs={os.path.basename(f)[:-3] for f in glob.glob(os.path.join(G, "*.md"))}
# every name that identifies a guideline
names={}
for s in slugs: names.setdefault(norm(s.replace("-"," ")),s)
for t,sl in cover.items():
    if sl in slugs:
        for p in re.split(r" = | / ",t): names.setdefault(norm(p),sl)
prof={}
for f in glob.glob(os.path.join(verification_dir(), "*.verification.json")):
    d=json.load(open(f)); sl=os.path.basename(f).replace(".verification.json","")
    cl=d["claims"]; prof[sl]=(sum(1 for c in cl if c["verdict"] in ("pass","pass_image_transcription")),len(cl))
def match(cond):
    n=norm(cond); toks=n.split()
    if n in names: return names[n],"exact"
    # containment: the guideline name appears as a contiguous token run in the condition
    best=None
    for gn,sl in names.items():
        g=gn.split()
        if not g or len(g)>len(toks): continue
        for i in range(len(toks)-len(g)+1):
            if toks[i:i+len(g)]==g:
                if best is None or len(g)>best[2]: best=(sl,"contains",len(g))
    return (best[0],best[1]) if best else (None,None)
res=[(c,)+match(c["condition"]) for c in conds]
w=[(c,sl,how) for c,sl,how in res if sl]; wo=[c for c,sl,_ in res if not sl]
print(f"BASE 639 PBS condition families\n")
print(f"WITH a guideline .......... {len(w)}   (exact {sum(1 for *_,h in w if h=='exact')}, containment {sum(1 for *_,h in w if h=='contains')})")
print(f"WITHOUT a guideline ....... {len(wo)}\n")
B=collections.Counter(); EX=collections.defaultdict(list)
for c,sl,_ in w:
    p,t=prof.get(sl,(0,0)); r=p/t if t else 0
    b=("fully verified"if r==1 else"well verified (>=50%)"if r>=.5 else"weakly verified (<50%)"if p else"NOT verifiable (0%)")
    B[b]+=1; EX[b].append((c["condition"],sl,p,t))
print("WITH a guideline — how verified is that guideline:")
for b in ["fully verified","well verified (>=50%)","weakly verified (<50%)","NOT verifiable (0%)"]:
    print(f"   {B[b]:4d}  {b}")
tot=sum(B.values()); ver=B["fully verified"]+B["well verified (>=50%)"]
print(f"   ----\n   {ver:4d}  SUFFICIENT (>=50% of claims machine re-checked)")
print(f"   {tot-ver:4d}  INSUFFICIENT (<50%, incl. {B['NOT verifiable (0%)']} with nothing re-checkable)\n")
sn=collections.Counter()
for c in wo:
    r=binds.get(c["condition"],{})
    sn["bound"if r.get("snomed")else"candidates only"if r.get("method")=="candidate_unconfirmed"else"none"]+=1
print(f"WITHOUT a guideline ({len(wo)}):")
print(f"      0  have an AMH topic with no guideline — EMPTY BY CONSTRUCTION (AMH gap is 0)")
for k,v in sn.most_common(): print(f"   {v:4d}  SNOMED: {k}")
