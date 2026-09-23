#!/usr/bin/env python3
"""List every PBS condition WITHOUT a guideline, matched to its PBS restrictions and listed items.

The join uses provenance, not name guessing: each condition in reference/conditions.json keeps
the raw PBS indication strings it was derived from (`pbs_variants`). Those exact strings are
matched against the indication paragraph of each current restriction, then
restriction -> item-restriction-relationships -> items.

"Without a guideline" is whatever scripts/condition_guideline_tally.py decides, reused as-is.
That script matches by NAME, so some rows here are near-misses (see its docstring).

  python3 scripts/pbs_pull.py --tables restrictions item-restriction-relationships items
  python3 scripts/no_guideline_pbs.py
  python3 scripts/no_guideline_pbs.py --selftest
"""
import collections, contextlib, io, json, runpy, sys
sys.path.insert(0, "scripts")
from conditions_from_restrictions import indication

ACCESS = {"RESTRICTED": "restricted", "STREAMLINED": "streamlined", "AUTHORITY_REQUIRED": "authority"}


def join(conditions, restrictions, links, items, all_conditions=()):
    variants_of = {c["condition"]: c.get("pbs_variants") or [] for c in all_conditions}
    by_text = collections.defaultdict(list)
    for r in restrictions:
        t = indication(r.get("li_html_text"))
        if t:
            by_text[t].append(r)
    codes_for = collections.defaultdict(set)
    for l in links:
        codes_for[l["res_code"]].add(l["pbs_code"])
    item_by_code = {}
    for it in items:
        item_by_code.setdefault(it["pbs_code"], it)
    out = []
    for c in conditions:
        # a split child (e.g. "Fallopian tube cancer") has no variants of its own: inherit its parent's
        via = None if c.get("pbs_variants") else c.get("parent_condition")
        variants = c.get("pbs_variants") or variants_of.get(via, [])
        rs = {r["res_code"]: r for v in variants for r in by_text.get(v, [])}
        codes = sorted({p for rc in rs for p in codes_for.get(rc, ())})
        drugs = collections.Counter(item_by_code[p]["li_drug_name"] for p in codes if p in item_by_code)
        out.append({
            "condition": c["condition"],
            "via_parent": via,
            "restriction_count_derived": c.get("restriction_count"),
            "restrictions_current": len(rs),
            "access": dict(collections.Counter(ACCESS.get(r.get("authority_method"), r.get("authority_method")) for r in rs.values())),
            "drugs": [d for d, _ in drugs.most_common()],
            "pbs_codes": codes,
            "res_codes": sorted(rs),
            "programs": sorted({item_by_code[p]["program_code"] for p in codes if p in item_by_code}),
            "snomed": (c.get("terminology_binding") or {}).get("concept_id"),
            "snomed_candidates": len(c.get("snomed_candidates") or []),
        })
    return out


def selftest():
    li = "<h1>Listing</h1><p>Severe psoriatic arthritis</p><br/><p>criteria</p>"
    out = join([{"condition": "Psoriatic arthritis", "pbs_variants": ["Severe psoriatic arthritis"]}],
               [{"res_code": "R1", "li_html_text": li, "authority_method": "AUTHORITY_REQUIRED"},
                {"res_code": "R2", "li_html_text": "<h1>x</h1><p>Other</p>", "authority_method": "RESTRICTED"}],
               [{"res_code": "R1", "pbs_code": "1A"}, {"res_code": "R1", "pbs_code": "2B"}, {"res_code": "R2", "pbs_code": "3C"}],
               [{"pbs_code": "1A", "li_drug_name": "Adalimumab", "program_code": "HB"},
                {"pbs_code": "2B", "li_drug_name": "Adalimumab", "program_code": "HB"},
                {"pbs_code": "3C", "li_drug_name": "Other", "program_code": "GE"}])
    o = out[0]
    assert o["res_codes"] == ["R1"] and o["pbs_codes"] == ["1A", "2B"], o
    assert o["drugs"] == ["Adalimumab"] and o["access"] == {"authority": 1}, o
    kid = join([{"condition": "Arthritis", "parent_condition": "Psoriatic arthritis"}],
               [{"res_code": "R1", "li_html_text": li, "authority_method": "AUTHORITY_REQUIRED"}], [{"res_code": "R1", "pbs_code": "1A"}],
               [{"pbs_code": "1A", "li_drug_name": "Adalimumab", "program_code": "HB"}],
               [{"condition": "Psoriatic arthritis", "pbs_variants": ["Severe psoriatic arthritis"]}])[0]
    assert kid["via_parent"] == "Psoriatic arthritis" and kid["pbs_codes"] == ["1A"], kid
    assert near_misses("Diabetes mellitus type 2", ["type-2-diabetes", "asthma"]) == ["type-2-diabetes"]
    assert near_misses("Psoriatic arthritis", ["rheumatoid-arthritis"]) == []
    print("selftest ok")


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        tally = runpy.run_path("scripts/condition_guideline_tally.py")
    without = tally["wo"]
    tables = {t: json.load(open(f"cache/pbs/{t}.json")) for t in ("restrictions", "item-restriction-relationships", "items")}
    sched = {p["schedule_code"] for p in tables.values()}
    assert len(sched) == 1, f"mixed PBS schedules: {sched}"
    rows = join(without, tables["restrictions"]["rows"], tables["item-restriction-relationships"]["rows"], tables["items"]["rows"],
                json.load(open("reference/conditions.json"))["conditions"])
    rows.sort(key=lambda r: (-r["restrictions_current"], r["condition"]))
    copyright_ = tables["restrictions"]["copyright"][0]["content"]
    json.dump({"schedule_code": sched.pop(), "pbs_copyright": copyright_, "count": len(rows), "conditions": rows},
              open("reference/no_guideline_pbs.json", "w"), indent=1, ensure_ascii=False)
    return rows, copyright_, tables["restrictions"]["schedule_code"]


STOP = {"of", "the", "and", "or", "with", "in", "to", "for", "a", "an", "children", "adults", "adolescents", "management", "disease"}


def near_misses(condition, slugs):
    """Guidelines whose name tokens match the condition's regardless of order (e.g. 'Diabetes mellitus type 2'
    vs type-2-diabetes). The tally matches contiguous runs only, so it misses these."""
    ct = {t for t in condition.lower().replace("-", " ").split() if t not in STOP} - {"mellitus"}
    hits = []
    for s in slugs:
        st = {t for t in s.split("-") if t not in STOP}
        if st and ct and (st <= ct or ct <= st):
            hits.append(s)
    return hits


def render(rows, copyright_, schedule):
    import glob, os
    slugs = sorted(os.path.basename(f)[:-3] for f in glob.glob("guidelines/*.md"))
    acc = collections.Counter()
    for r in rows:
        for k, v in r["access"].items():
            acc[k] += v
    nm = {r["condition"]: near_misses(r["condition"], slugs) for r in rows}
    o = [f"# PBS conditions with no guideline — matched to their PBS listings\n",
         f"**Generated** by `scripts/no_guideline_pbs.py` from PBS schedule **{schedule}** (PBS Public API v3) and the "
         f"corpus on this branch. Full detail, including every PBS item code and restriction code, is in "
         f"[`reference/no_guideline_pbs.json`](../reference/no_guideline_pbs.json).\n",
         "| | |", "|---|---:|",
         f"| conditions without a guideline | **{len(rows)}** |",
         f"| … matched to ≥1 current PBS restriction | **{sum(1 for r in rows if r['restrictions_current'])}** |",
         f"| … of which matched through a split parent | {sum(1 for r in rows if r['via_parent'])} |",
         f"| distinct PBS item codes covered | **{len({p for r in rows for p in r['pbs_codes']})}** |",
         f"| restrictions by access | authority {acc['authority']} · streamlined {acc['streamlined']} · restricted {acc['restricted']} |",
         f"| ⚠️ possible name-match misses (a guideline may already cover it) | {sum(1 for v in nm.values() if v)} |\n",
         "**How to read it.** *Without a guideline* is decided by `condition_guideline_tally.py`, which matches by name.",
         "The **near-miss** column lists existing guidelines whose name tokens match regardless of order. Those rows may",
         "already be covered and need a human look. **via parent** marks a split child whose PBS listing is its parent's",
         "combined indication. Some splits are parsing fragments (e.g. *Definite*, *Bone*, *Fungal*) and are kept, flagged,",
         "not silently dropped.\n",
         "**Access:** A = authority required · S = streamlined authority · R = restricted benefit (counts of current restrictions).\n",
         "| # | condition | restrictions (A/S/R) | drugs | PBS items | SNOMED | notes |", "|---:|---|---|---|---:|---|---|"]
    for i, r in enumerate(rows, 1):
        a = r["access"]
        ars = f"{r['restrictions_current']} ({a.get('authority', 0)}/{a.get('streamlined', 0)}/{a.get('restricted', 0)})"
        drugs = ", ".join(r["drugs"][:6]) + (f" +{len(r['drugs']) - 6}" if len(r["drugs"]) > 6 else "")
        sn = f"`{r['snomed']}`" if r["snomed"] else (f"{r['snomed_candidates']} candidates" if r["snomed_candidates"] else "—")
        notes = []
        if r["via_parent"]:
            notes.append(f"via parent *{r['via_parent']}*")
        if nm[r["condition"]]:
            notes.append("⚠️ near-miss: " + ", ".join(f"`{s}`" for s in nm[r["condition"]][:3]))
        o.append(f"| {i} | {r['condition']} | {ars} | {drugs} | {len(r['pbs_codes'])} | {sn} | {'; '.join(notes)} |")
    o += ["\n---\n", "**PBS copyright notice (retained as the licence requires):**\n"] + [f"> {line}" for line in copyright_]
    open("docs/no-guideline-pbs-listings.md", "w").write("\n".join(o) + "\n")
    return nm


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        rows, cr, s = main()
        nm = render(rows, cr, s)
        print(f"  possible name-match misses: {sum(1 for v in nm.values() if v)}  -> docs/no-guideline-pbs-listings.md")
        print(f"{len(rows)} conditions without a guideline -> reference/no_guideline_pbs.json (PBS schedule {s})")
        print(f"  matched to >=1 current restriction: {sum(1 for r in rows if r['restrictions_current'])}")
