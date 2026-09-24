#!/usr/bin/env python3
"""A second search for PBS indication texts whose first candidates did not fit (reference/pbs_indication_first_reading.json).

The first search (scripts/bind_indications.py) sent the whole text to the Ontoserver, so a long indication ("Proven
vitamin B12 deficiencies other than pernicious anaemia") came back with whatever matched every word, and a general one
("non-small cell lung cancer") with only subtypes. This one queries the condition itself:

  - the framing a listing adds is dropped: Prevention of / Prophylaxis of / Management of / Treatment of / Eradication of
    / Reduction of / Anticipated / Proven / Established / Suspected / Untreated / Resectable / Resected / Intractable /
    Refractory / Treatment-resistant / Symptomatic / Paediatric / Stage ... ; parentheticals too;
  - "A or B", "A and/or B" and "A, B" are searched as their parts;
  - a plural head is made singular (infections -> infection), and SNOMED CT's wording is tried as well
    (cancer -> malignant neoplasm, infestation -> infection, tumour -> neoplasm);
  - hits are ranked: an exact name or synonym first, then the most general concept (fewest words beyond the query).

Up to 5 new candidates an indication, not already offered, go to reference/pbs_indication_candidates_more.json (codes
and SNOMED CT displays, like the first file); review_sheets.py adds them to the sheet after the first ones. Live
Ontoserver (CSIRO public), SNOMED CT-AU 20260831. A candidate is a frame for a person, never an edge.

    .venv/bin/python scripts/pbs_candidates_more.py      # ~5 min
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bind_indications import expand, norm   # the same Ontoserver, edition and ECL (clinical finding, situation, event)

READING = Path("reference/pbs_indication_first_reading.json")
BIND = Path("reference/pbs_indication_bindings.json")
OUT = Path("reference/pbs_indication_candidates_more.json")
FRAME = ["chronic treatment of", "adjuvant management of", "management of", "treatment of", "prevention of", "prophylaxis of",
         "eradication of", "reduction of", "anticipated", "proven", "established", "suspected", "untreated", "resectable",
         "resected", "intractable", "refractory", "treatment-resistant", "treatment resistant", "symptomatic", "paediatric",
         "stage iii or iv", "stage iii", "stage iv", "disabling", "local", "severe", "acute severe", "treatment refractory",
         "high risk of", "combined"]
WORDING = [("cancer", "malignant neoplasm"), ("cancer", "carcinoma"), ("infestation", "infection"), ("tumour", "neoplasm"), ("tumours", "neoplasm")]


def singular(w: str) -> str:
    for a, b in (("ies", "y"), ("oses", "osis"), ("ses", "sis"), ("s", "")):
        if w.endswith(a) and len(w) > len(a) + 3 and not w.endswith("ss") and not w.endswith("is"):
            return w[: -len(a)] + b
    return w


def queries(text: str) -> list[str]:
    t = re.sub(r"\s*\([^)]*\)", "", text).strip().rstrip(".")
    low = t.lower()
    changed = True
    while changed:
        changed = False
        for f in FRAME:
            if low.startswith(f + " "):
                low = low[len(f) + 1:]
                changed = True
    parts = [p.strip() for p in re.split(r",| and/or | or | and ", low) if p.strip()] if re.search(r",| and/or | or | and ", low) else [low]
    # the condition before a qualifying clause, and without a trailing "infection" / "attack": extra queries, not
    # replacements ("vitamin b12 deficiencies other than pernicious anaemia" -> "vitamin b12 deficiencies")
    cuts = [re.split(r" other than | including | with | of greater than | associated with | secondary to | following ", low)[0]]
    cuts += [re.sub(r" (infections?|attacks?|states?)$", "", c) for c in [low] + cuts]
    out = []
    for p in [low] + (parts if len(parts) > 1 else []) + cuts:
        words = p.split()
        if not words:
            continue
        head = words[:-1] + [singular(words[-1])]
        for q in (p, " ".join(head)):
            out.append(q)
            for a, b in WORDING:
                if re.search(rf"\b{a}\b", q):
                    out.append(re.sub(rf"\b{a}\b", b, q))
    seen, uniq = set(), []
    for q in out:
        if norm(q) and norm(q) not in seen and len(norm(q)) > 2:
            seen.add(norm(q))
            uniq.append(q)
    return uniq


def rank(hits: list[dict], q: str) -> list[tuple[int, int, dict]]:
    nq = norm(q)
    out = []
    for h in hits:
        names = [h.get("display", "")] + [d.get("value", "") for d in h.get("designation", []) if d.get("language", "en").startswith("en")]
        exact = any(norm(n) == nq for n in names)
        extra = min(len(norm(n).split()) for n in names if n) - len(nq.split())
        out.append((0 if exact else 1, max(extra, 0), h))
    return out


def local_exact(con, q: str) -> list[tuple[str, str]]:
    """Active SNOMED CT-AU clinical findings, disorders, situations and events with a description equal to the query
    once case and punctuation are set aside -- the general concept a relevance-ranked search can push out of its top 15."""
    return con.execute("SELECT DISTINCT d.cid, c.pt FROM descr d JOIN cmp.concept c ON c.id = d.cid WHERE d.n = ?", [norm(q)]).fetchall()


def main() -> int:
    reads = json.load(open(READING))["readings"]
    targets = {s for s, r in reads.items() if any("no candidate fits" in v for v in r.values())
               or not any(v.startswith(("likely the match", "the condition treated", "one of the conditions")) for v in r.values())}
    bind = {str(r["indication_prescribing_txt_id"]): r for r in json.load(open(BIND))["results"]}
    import duckdb, os
    au = Path(os.environ.get("AU_RF2_SNAPSHOT", os.path.expanduser("~/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/Snapshot")))
    con = duckdb.connect()
    con.execute("ATTACH 'out/compendium.duckdb' AS cmp (READ_ONLY)")
    con.create_function("nrm", norm, ["VARCHAR"], "VARCHAR")
    con.execute(f"""CREATE TABLE descr AS SELECT d.conceptId cid, nrm(d.term) n FROM read_csv('{au / "Terminology/sct2_Description_Snapshot-en-au_AU1000036_20260831.txt"}',
                    delim='\t', header=true, quote='', all_varchar=true) d JOIN cmp.concept c ON c.id = d.conceptId
                    WHERE d.active = '1' AND c.tag IN ('disorder', 'finding', 'situation', 'event')""")
    t0, out = time.time(), {}
    for i, s in enumerate(sorted(targets, key=int), 1):
        r = bind[s]
        have = {c["concept_id"] for c in r.get("candidates") or []}
        scored = {}
        for q in queries(r["text"]):
            for cid, pt in local_exact(con, q):
                if cid not in have:
                    scored[cid] = ((-1, 0), pt, q + " (exact, local release)")
            for ex, extra, h in rank(expand(q, count=15), q):
                if h["code"] in have:
                    continue
                key = (ex, extra)
                if h["code"] not in scored or key < scored[h["code"]][0]:
                    if scored.get(h["code"], ((9, 9),))[0][0] == -1:
                        continue
                    scored[h["code"]] = (key, h.get("display"), q)
            time.sleep(0.25)
        best = sorted(scored.items(), key=lambda kv: kv[1][0])[:5]
        out[s] = {"text": r["text"], "candidates": [{"concept_id": c, "display": d, "query": q, "exact_name": k[0] <= 0}
                                                    for c, (k, d, q) in best]}
        if i % 25 == 0:
            print(f"  {i}/{len(targets)}  {time.time() - t0:.0f}s", flush=True)
    doc = {"_note": "Second-search candidates for PBS indication texts whose first candidates did not fit (scripts/pbs_candidates_more.py): "
                    "the condition queried without the listing's framing, parts of 'A or B' searched apart, SNOMED CT wording tried; "
                    "live Ontoserver, SNOMED CT-AU 20260831. Frames for a person, never edges.",
           "edition": "http://snomed.info/sct/32506021000036107/version/20260831", "indications": len(out),
           "with_an_exact_name": sum(any(c["exact_name"] for c in v["candidates"]) for v in out.values()), "results": out}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(out)} indications, {doc['with_an_exact_name']} with an exact-name candidate -> {OUT} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
