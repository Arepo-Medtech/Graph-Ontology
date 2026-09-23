#!/usr/bin/env python3
"""Bind free-text conditions to SNOMED CT-AU -- exact matches become edges, everything else becomes a frame for a person.

Two sets of text are dead ends in the multigraph: the 653 PBS indication conditions ("clear cell variant renal cell
carcinoma (RCC)") and the 374 corpus conditions the binder could not bind. Text to concept is a GAP, so the rule is the
one the design fixed: a match may collapse to an edge only when it is exact -- the normalised text equals a SNOMED
CT-AU preferred term or synonym -- and otherwise the answer is a candidate frame, left for a person, never an edge.

Normalisation, in order, stopping at the first exact hit: the text as given; without parentheticals ("(RCC)");
without leading severity / course words ("severe", "moderate to severe", "active", "chronic", "locally advanced or
metastatic" ...). A stripped qualifier is recorded, not lost -- it is the adjective or temporality the design says
rides on the edge.

As a check between two implementations (not a precision measurement), the same matcher is run over the 265 corpus
conditions the existing binder already bound, and agreement is reported.

Uses the live Ontoserver (CSIRO public, SNOMED CT-AU 20260831 -- the edition the binder is pinned to).

    scripts/bind_indications.py        # writes reference/pbs_indication_bindings.json, reference/corpus_condition_candidates.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://r4.ontoserver.csiro.au/fhir"
EDITION = "http://snomed.info/sct/32506021000036107/version/20260831"
ECL = "<< 404684003 OR << 243796009 OR << 272379006"          # clinical finding, situation, event
QUALIFIERS = ["locally advanced or metastatic", "moderate to severe", "severe", "moderate", "mild", "active", "chronic",
              "acute", "advanced", "metastatic", "recurrent", "relapsed", "refractory", "uncontrolled", "persistent",
              "previously untreated", "stage iv", "stage iii"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def variants(text: str) -> list[tuple[str, str | None]]:
    out = [(text, None)]
    bare = re.sub(r"\s*\([^)]*\)", "", text).strip()
    if bare != text:
        out.append((bare, None))
    for base in list(dict.fromkeys([text, bare])):
        rest, stripped = base, []
        while True:                                   # "Severe active X" -> "active X" -> "X": strip repeatedly
            low = rest.lower()
            q = next((q for q in QUALIFIERS if low.startswith(q + " ")), None)
            if q is None:
                break
            rest = rest[len(q) + 1:]
            stripped.append(q)
            out.append((rest, " + ".join(stripped)))
    seen, uniq = set(), []
    for v, q in out:
        if norm(v) and norm(v) not in seen:
            seen.add(norm(v))
            uniq.append((v, q))
    return uniq


def expand(text: str, count: int = 10) -> list[dict]:
    q = {"url": "http://snomed.info/sct/32506021000036107?fhir_vs=ecl/" + ECL, "filter": text, "count": count,
         "includeDesignations": "true", "system-version": f"http://snomed.info/sct|{EDITION}"}
    url = f"{BASE}/ValueSet/$expand?{urllib.parse.urlencode(q)}"
    for i in range(3):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/fhir+json"}), timeout=60))
            return d.get("expansion", {}).get("contains", [])
        except urllib.error.HTTPError:
            return []
        except Exception:
            time.sleep(2 + 3 * i)
    return []


def bind(text: str) -> dict:
    first = None
    for v, qualifier in variants(text):
        hits = expand(v)
        time.sleep(0.3)
        first = first if first is not None else hits
        nv = norm(v)
        for h in hits:
            terms = [(h.get("display", ""), "exact_display")] + [
                (d.get("value", ""), "exact_synonym") for d in h.get("designation", []) if d.get("language", "en").startswith("en")]
            for term, method in terms:
                if norm(term) == nv:
                    return {"text": text, "bound": {"concept_id": h["code"], "display": h.get("display"),
                            "method": method if v == text else "normalised_" + method.split("_", 1)[1],
                            "matched_variant": v, "stripped_qualifier": qualifier}}
    return {"text": text, "bound": None,
            "candidates": [{"concept_id": h["code"], "display": h.get("display")} for h in (first or [])[:5]]}


def main() -> int:
    pbs = json.load(open("cache/pbs/indications.json"))["rows"]
    b = json.load(open("reference/snomed_bindings.json"))["results"]
    bound_corpus = [(r["condition"], r["snomed"]["concept_id"]) for r in b if r.get("snomed")]
    unbound_corpus = [r["condition"] for r in b if not r.get("snomed")]
    t0 = time.time()
    out_pbs = []
    for i, r in enumerate(pbs, 1):
        res = bind(r["condition"])
        res.update({"indication_prescribing_txt_id": r["indication_prescribing_txt_id"],
                    "pbs_severity": r.get("severity"), "pbs_episodicity": r.get("episodicity")})
        out_pbs.append(res)
        if i % 100 == 0:
            print(f"  PBS {i}/{len(pbs)}  {time.time() - t0:.0f}s", flush=True)
    out_unbound = []
    for i, c in enumerate(unbound_corpus, 1):
        out_unbound.append(bind(c))
        if i % 100 == 0:
            print(f"  corpus unbound {i}/{len(unbound_corpus)}  {time.time() - t0:.0f}s", flush=True)
    agree = total = 0
    disagreements = []
    for c, sid in bound_corpus:
        res = bind(c)
        if res["bound"]:
            total += 1
            if res["bound"]["concept_id"] == sid:
                agree += 1
            else:
                disagreements.append({"condition": c, "binder": sid, "this": res["bound"]["concept_id"], "display": res["bound"]["display"]})
    summary = {
        "pbs_indications": len(out_pbs), "pbs_bound": sum(1 for x in out_pbs if x["bound"]),
        "pbs_bound_by_method": {m: sum(1 for x in out_pbs if x["bound"] and x["bound"]["method"] == m)
                                for m in sorted({x["bound"]["method"] for x in out_pbs if x["bound"]})},
        "corpus_unbound": len(out_unbound), "corpus_newly_bound": sum(1 for x in out_unbound if x["bound"]),
        "check_against_existing_binder": {"corpus_bound": len(bound_corpus), "this_matcher_also_bound": total,
                                          "same_concept": agree, "different_concept": len(disagreements),
                                          "note": "agreement between two exact-match implementations, not a precision measurement"},
        "edition": EDITION, "server": BASE, "seconds": round(time.time() - t0)}
    note = ("Exact matches only are edges (pbs:indication_is). Rows with bound=null carry up to five candidates for a person "
            "(corrected_pending_attestation); they are a frame, not an answer.")
    Path("reference/pbs_indication_bindings.json").write_text(json.dumps(
        {"_note": note, "summary": summary, "results": out_pbs}, indent=1, ensure_ascii=False))
    Path("reference/corpus_condition_candidates.json").write_text(json.dumps(
        {"_note": "Corpus conditions the binder could not bind, re-tried with the same exact-match rule; newly exact-bound ones "
                  "should be applied through binding_corrections.json by a person, the rest carry candidates.",
         "disagreements_with_existing_binder": disagreements, "results": out_unbound}, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
