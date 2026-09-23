#!/usr/bin/env python3
"""Conditions with an INSUFFICIENT guideline, joined with those BOUND to SNOMED.

Two sets that answer different halves of the same question:

  A  insufficient guideline  -- <50% of the guideline's claims are machine
                               re-checkable, so what the compendium SAYS about
                               the condition largely cannot be checked here
  B  bound SNOMED concept    -- the condition IS pinned down terminologically

⚠️ A ∩ B is the sharp set: we know exactly what the condition is, and cannot
verify most of what we say about it. Those rows are listed first.

  python3 scripts/underverified_bound.py > docs/underverified-and-bound.md
"""
import json, glob, os, re, sys
def norm(s):
    s=s.lower().replace("’","'"); s=re.sub(r"'s\b","",s)
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()
conds=json.load(open("reference/conditions.json"))["conditions"]
binds={r["condition"]:r for r in json.load(open("reference/snomed_bindings.json"))["results"]}
cover=json.load(open("reference/amh-topic-coverage.json"))
slugs={os.path.basename(f)[:-3] for f in glob.glob("guidelines/*.md")}
names={}
for s in slugs: names.setdefault(norm(s.replace("-"," ")),s)
for t,sl in cover.items():
    if sl in slugs:
        for p in re.split(r" = | / ",t): names.setdefault(norm(p),sl)
prof={}
for f in glob.glob("guidelines/*.verification.json"):
    d=json.load(open(f)); sl=os.path.basename(f).replace(".verification.json","")
    cl=d["claims"]; prof[sl]=(sum(1 for c in cl if c["verdict"] in ("pass","pass_image_transcription")),len(cl))
def match(cond):
    n=norm(cond); toks=n.split()
    if n in names: return names[n]
    best=None
    for gn,sl in names.items():
        g=gn.split()
        if not g or len(g)>len(toks): continue
        for i in range(len(toks)-len(g)+1):
            if toks[i:i+len(g)]==g and (best is None or len(g)>best[1]): best=(sl,len(g))
    return best[0] if best else None

rows=[]
for c in conds:
    name=c["condition"]; sl=match(name)
    p,t=prof.get(sl,(0,0)) if sl else (0,0)
    pct=(p/t) if t else None
    ins = bool(sl) and pct is not None and pct<.5
    sn=binds.get(name,{}).get("snomed")
    if not (ins or sn): continue
    cat=("A∩B  under-verified AND bound" if ins and sn else
         "A    under-verified, not bound" if ins else
         "B    bound, no guideline" if not sl else
         "B    bound, guideline is sufficient")
    rows.append({"cat":cat,"condition":name,"guideline":sl or "",
                 "pass":p,"total":t,"pct":pct,
                 "concept":(sn or {}).get("concept_id",""),"display":(sn or {}).get("display",""),
                 "restr":c.get("restriction_count",0)})
order={"A∩B  under-verified AND bound":0,"A    under-verified, not bound":1,
       "B    bound, no guideline":2,"B    bound, guideline is sufficient":3}
rows.sort(key=lambda r:(order[r["cat"]],-r["restr"],r["condition"].lower()))
n=lambda k: sum(1 for r in rows if r["cat"].startswith(k))
o=[]
o.append("# Under-verified guidelines, joined with SNOMED-bound conditions\n")
o.append("**Generated 2026-09-23** by `scripts/underverified_bound.py`. Base: the **639 PBS condition")
o.append("families**. ⚠️ Condition→guideline matching is by **token containment on names** and is an")
o.append("estimate inside a 59–202 band — see [`condition-guideline-tally.md`](condition-guideline-tally.md).\n")
o.append("**A** = insufficient guideline (**<50%** of its claims machine re-checkable) · "
         "**B** = bound to a SNOMED concept\n")
o.append(f"| set | rows |\n|---|---:|\n| **A ∩ B** — ⚠️ **the sharp set** | **{n('A∩B')}** |"
         f"\n| A only | {n('A    ')} |\n| B only | {n('B    ')} |\n| **union** | **{len(rows)}** |\n")
o.append("> ### ⚠️ WHY A ∩ B IS THE SET THAT MATTERS")
o.append("> **The condition is pinned down terminologically, and most of what this compendium says about")
o.append("> it cannot be checked from this repository.** A precise identifier attached to an unverifiable")
o.append("> statement is worse than an imprecise one, because it invites downstream systems to trust it.\n")
cur=None
for r in rows:
    if r["cat"]!=cur:
        cur=r["cat"]
        o.append(f"\n## {cur}\n")
        o.append("| condition | PBS restr. | guideline | verified | SNOMED | concept display |")
        o.append("|---|---:|---|---:|---|---|")
    v=f"{r['pass']}/{r['total']} ({r['pct']*100:.0f}%)" if r["total"] else "—"
    g=f"[{r['guideline']}](../guidelines/{r['guideline']}.md)" if r["guideline"] else ""
    o.append(f"| {r['condition']} | {r['restr']} | {g} | {v} | `{r['concept']}` | {r['display']} |")
sys.stdout.write("\n".join(o)+"\n")
