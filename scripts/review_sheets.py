#!/usr/bin/env python3
"""Review sheets for the queues that wait for a person, and the one file their decisions go into (workstream 4).

Every queue in docs/review-queues.md that crossed a gap by name -- a survey instrument, a PBS indication text, an MBS
item, an HPO phenotype or SNOMED organism whose names differ from their UMLS partner, a RadLex anatomy term -- has its
candidates written as a spreadsheet, one row per candidate, with the names and (where there is one) my first reading.
A reviewer fills in one column and the harvest step turns the rows into decisions:

    .venv/bin/python scripts/review_sheets.py make                  # -> out/review/<queue>.csv, undecided rows only
    #   in the 'decision' column:  y = this candidate is right   n = it is not   none = no candidate on this subject is
    #   (the note column is kept; leave 'decision' blank to skip a row)
    .venv/bin/python scripts/review_sheets.py harvest --reviewer "Name"   # -> reference/candidate_decisions.json
    .venv/bin/python scripts/review_sheets.py status                # how much each queue has left

reference/candidate_decisions.json holds codes and verdicts only (no names); build_edges.py loads every accepted
decision as an edge -- method "confirmed by <reviewer> <date>", tier `decision` -- and the next `make` leaves decided
subjects out. The sheets carry licensed names (SNOMED CT, LOINC, UMLS-derived pairs), so they stay in out/ (git-ignored).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sys
from pathlib import Path

DECISIONS = Path("reference/candidate_decisions.json")
SHEETS = Path("out/review")
COLS = ["id", "queue", "subject_vocab", "subject_code", "subject_name", "rank", "object_vocab", "object_code", "object_name", "first_reading",
        "decision", "note"]
# queue -> (predicate an accepted decision loads as, what the reviewer decides)
QUEUES = {
    "survey_instruments": ("person:same_as", "same instrument?"),
    "pbs_indications": ("person:same_as", "the SNOMED CT condition the PBS listing means"),
    "mbs_procedures": ("person:funds_procedure", "the SNOMED CT procedure the MBS item funds (a billing rule is not an equivalence)"),
    "hpo_snomed": ("person:same_as", "same phenotype? (a sample was right 34 of 40; errors are narrowings)"),
    "organism_ncbi": ("person:same_as", "same organism? (most are reclassifications)"),
    "radlex_anatomy": ("person:same_as", "the SNOMED CT body structure for this RadLex term"),
}


def load_decisions() -> dict:
    if DECISIONS.exists():
        return json.load(open(DECISIONS))
    return {"_note": ("Decisions a person has made on the review queues (scripts/review_sheets.py). Codes and verdicts only. "
                      "decision: accept (this candidate is right) | reject (it is not) | none (no candidate on this subject is). "
                      "build_edges.py loads every accept as an edge, tier 'decision'."),
            "queues": {q: {"predicate": p, "question": d} for q, (p, d) in QUEUES.items()}, "decisions": []}


def candidates():
    """Every queue's candidate rows: (queue, s_vocab, s_code, s_name, rank, o_vocab, o_code, o_name, first_reading)."""
    out = []
    p = Path("reference/survey_instrument_candidates.json")
    if p.exists():
        for i, r in enumerate(json.load(open(p))["candidates"]):
            out.append(("survey_instruments", "LOINC", r["loinc"], r["loinc_name"], 1, "SCT", r["sct"], r["sct_name"], r.get("my_read", "")))
    p = Path("reference/pbs_indication_bindings.json")
    fr = Path("reference/pbs_indication_first_reading.json")
    pbs_read = json.load(open(fr))["readings"] if fr.exists() else {}
    if p.exists():
        for r in json.load(open(p))["results"]:
            if r.get("bound"):
                continue
            for k, c in enumerate(r.get("candidates") or [], 1):
                out.append(("pbs_indications", "PBS_INDICATION", str(r["indication_prescribing_txt_id"]), r["text"], k, "SCT",
                            c["concept_id"], c["display"],
                            pbs_read.get(str(r["indication_prescribing_txt_id"]), {}).get(c["concept_id"], "")))
    extra = Path("reference/pbs_indication_candidates_more.json")      # the second search, after the first candidates
    if extra.exists():
        first_n = {}
        for row in out:
            if row[0] == "pbs_indications":
                first_n[row[2]] = max(first_n.get(row[2], 0), row[4])
        for sid, v in json.load(open(extra))["results"].items():
            for k, c in enumerate(v["candidates"], first_n.get(sid, 0) + 1):
                out.append(("pbs_indications", "PBS_INDICATION", sid, v["text"], k, "SCT", c["concept_id"], c["display"],
                            pbs_read.get(sid, {}).get(c["concept_id"], "")))
    p = Path("reference/mbs_procedure_candidates.json")
    if p.exists():
        for r in json.load(open(p))["results"]:
            head = (r.get("exact_head_match") or {}).get("concept_id")
            for k, c in enumerate(r.get("candidates") or [], 1):
                out.append(("mbs_procedures", "MBS", r["item"], r.get("query", ""), k, "SCT", c["concept_id"], c["display"],
                            "exact head phrase" if c["concept_id"] == head else ""))
    for q, f, sv, so, ov, oc, on_ in (("hpo_snomed", "cache/umls/hpo_snomed_candidates.tsv", "HP", "hpo_id", "SCT", "snomed_code", "au_name"),
                                      ("organism_ncbi", "cache/umls/sct_ncbi_candidates.tsv", "SCT", "sct", "NCBITAXON", "ncbi_taxon", "ncbi_name"),
                                      ("radlex_anatomy", "cache/radlex/radlex_sct_candidates.tsv", "RADLEX", "rid", "SCT", "sct", "sct_name")):
        if Path(f).exists():
            sname = {"hpo_snomed": "hp_name", "organism_ncbi": "sct_name", "radlex_anatomy": "radlex_name"}[q]
            rank = {}
            for r in csv.DictReader(open(f), delimiter="\t"):
                rank[r[so]] = rank.get(r[so], 0) + 1
                out.append((q, sv, r[so], r[sname], rank[r[so]], ov, r[oc], r[on_], ""))
    return out


def make(a) -> int:
    dec = load_decisions()
    decided = {(d["queue"], d["subject"]["vocab"], d["subject"]["code"]) for d in dec["decisions"]
               if d["decision"] in ("accept", "none")}
    SHEETS.mkdir(parents=True, exist_ok=True)
    rows_all = candidates()
    held = set()                      # a pair the graph already carries (another route found it since) needs no review
    if Path("out/graph.duckdb").exists():
        import duckdb
        con = duckdb.connect("out/graph.duckdb", read_only=True)
        con.execute("CREATE TEMP TABLE cand (sv VARCHAR, sc VARCHAR, ov VARCHAR, oc VARCHAR)")
        con.executemany("INSERT INTO cand VALUES (?, ?, ?, ?)", sorted({(r[1], r[2], r[5], r[6]) for r in rows_all}))
        held = {tuple(r) for r in con.execute("""
            SELECT c.* FROM cand c JOIN edge e ON e.s_vocab = c.sv AND e.s_code = c.sc AND e.o_vocab = c.ov AND e.o_code = c.oc
                WHERE e.state <> 'rejected' AND e.tier <> 'inadmissible'
            UNION SELECT c.* FROM cand c JOIN edge e ON e.o_vocab = c.sv AND e.o_code = c.sc AND e.s_vocab = c.ov AND e.s_code = c.oc
                WHERE e.state <> 'rejected' AND e.tier <> 'inadmissible'""").fetchall()}
    by = {}
    for row in rows_all:
        if (row[1], row[2], row[5], row[6]) in held:
            continue
        if a.queue and row[0] != a.queue:
            continue
        if (row[0], row[1], row[2]) in decided:
            continue
        by.setdefault(row[0], []).append(row)
    for q, rows in by.items():
        with open(SHEETS / f"{q}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            for r in rows:
                # the id carries every code as text: a spreadsheet turns a long SNOMED CT id in a number column into
                # 3.361E+12, so the harvest reads the codes from here
                w.writerow(["|".join((r[0], r[1], r[2], r[5], r[6]))] + list(r) + ["", ""])
        print(f"  {q:<20} {len(rows):>6} rows, {len({r[2] for r in rows}):>5} subjects -> {SHEETS / (q + '.csv')}   ({QUEUES[q][1]})")
    return 0


def harvest(a) -> int:
    dec = load_decisions()
    date = a.date or datetime.date.today().isoformat()
    key = lambda d: (d["queue"], d["subject"]["vocab"], d["subject"]["code"], (d.get("object") or {}).get("code"))
    have = {key(d): i for i, d in enumerate(dec["decisions"])}
    added, changed = 0, 0
    for sheet in sorted(SHEETS.glob("*.csv")):
        for r in csv.DictReader(open(sheet, encoding="utf-8-sig")):
            v = (r.get("decision") or "").strip().lower()
            if not v:
                continue
            if v not in ("y", "yes", "n", "no", "none"):
                print(f"  skipped {sheet.name}: decision {v!r} for {r['subject_code']} (use y / n / none)", file=sys.stderr)
                continue
            if r.get("id"):
                q_, sv_, sc_, ov_, oc_ = r["id"].split("|")
            else:                         # a sheet written before the id column: refuse codes a spreadsheet has reformatted
                q_, sv_, sc_, ov_, oc_ = r["queue"], r["subject_vocab"], r["subject_code"], r["object_vocab"], r["object_code"]
                if any("e+" in x.lower() for x in (sc_, oc_)):
                    print(f"  skipped {sheet.name}: a code was reformatted by the spreadsheet ({sc_} / {oc_}); run `make` again",
                          file=sys.stderr)
                    continue
            d = {"queue": q_, "subject": {"vocab": sv_, "code": sc_},
                 "object": None if v == "none" else {"vocab": ov_, "code": oc_},
                 "decision": {"y": "accept", "yes": "accept", "n": "reject", "no": "reject", "none": "none"}[v],
                 "reviewer": a.reviewer, "date": date, **({"note": r["note"].strip()} if (r.get("note") or "").strip() else {})}
            k = key(d)
            if k in have:
                dec["decisions"][have[k]] = d
                changed += 1
            else:
                have[k] = len(dec["decisions"])
                dec["decisions"].append(d)
                added += 1
    DECISIONS.write_text(json.dumps(dec, indent=1, ensure_ascii=False) + "\n")
    print(f"harvest: {added} new, {changed} updated decision(s) by {a.reviewer} -> {DECISIONS}; rerun `make` for the rows left")
    return 0


def status(a) -> int:
    dec = load_decisions()
    cand = candidates()
    for q in QUEUES:
        subj = {r[2] for r in cand if r[0] == q}
        ds = [d for d in dec["decisions"] if d["queue"] == q]
        done = {d["subject"]["code"] for d in ds if d["decision"] in ("accept", "none")}
        acc = sum(d["decision"] == "accept" for d in ds)
        print(f"  {q:<20} {len(subj):>6} subjects   decided {len(done & subj):>5}   accepted {acc:>5}   left {len(subj - done):>6}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--queue", choices=list(QUEUES))
    h = sub.add_parser("harvest")
    h.add_argument("--reviewer", required=True)
    h.add_argument("--date")
    sub.add_parser("status")
    a = ap.parse_args()
    if not DECISIONS.exists():
        DECISIONS.write_text(json.dumps(load_decisions(), indent=1) + "\n")
    return {"make": make, "harvest": harvest, "status": status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
