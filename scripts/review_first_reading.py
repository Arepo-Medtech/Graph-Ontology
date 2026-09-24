#!/usr/bin/env python3
"""First readings for the three large review queues -- HPO -> SNOMED CT, SNOMED CT organism <-> NCBI taxon, MBS item ->
SNOMED CT procedure -- so a reviewer can accept the likely rows and read only the doubtful ones (the PBS queue had the
same, reference/pbs_indication_first_reading.json).

Two passes. A name rule settles the rows whose names agree once synonyms are compared; a reader (Claude, 24 Sep 2026)
reads the rest from a packet of names, synonyms and (for MBS) the item descriptor, and writes one code per row:

    hpo_snomed      S same phenotype   N narrower (SNOMED CT is a subtype)   B broader   R related, not the same   D different
    organism_ncbi   S same organism    M same organism, renamed or moved to another genus   K another rank   D another organism
    mbs_procedures  P the procedure the item funds   G a more general form of it   N a narrower form (a technique or site
                    the item does not require)   A part of the service, or related only   D a different procedure

    .venv/bin/python scripts/review_first_reading.py packets   # rule pass + cache/review/packet_<queue>_<n>.tsv to read
    #   a reader writes cache/review/read_<queue>_<n>.tsv: key <tab> code [<tab> note]
    .venv/bin/python scripts/review_first_reading.py packets --round r2   # only rows not read yet (new candidates)
    .venv/bin/python scripts/review_first_reading.py merge     # -> the readings files; then review_sheets.py make

Readings go to cache/review/<queue>_first_reading.json for the two UMLS-derived queues (never committed) and to
reference/mbs_procedure_first_reading.json for MBS (codes and readings only). A reading is not a decision.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb

DIR = Path("cache/review")
SHEETS = Path("out/review")
OUT = {"hpo_snomed": DIR / "hpo_snomed_first_reading.json", "organism_ncbi": DIR / "organism_ncbi_first_reading.json",
       "mbs_procedures": Path("reference/mbs_procedure_first_reading.json")}
PARTS = {"hpo_snomed": 2, "organism_ncbi": 1, "mbs_procedures": 6}
CODES = {
    "hpo_snomed": {"S": "likely the same phenotype", "N": "narrower (SNOMED CT is a subtype)", "B": "broader (SNOMED CT is more general)",
                   "R": "related, not the same", "D": "a different phenotype"},
    "organism_ncbi": {"S": "likely the same organism", "M": "the same organism, renamed or moved to another genus",
                      "K": "another rank", "D": "another organism"},
    "mbs_procedures": {"P": "likely the procedure the item funds", "G": "a more general form of the procedure",
                       "N": "narrower (a technique or site the item does not require)", "A": "part of the service, or related only",
                       "D": "a different procedure"},
}
ACCEPT = {"hpo_snomed": {"S"}, "organism_ncbi": {"S", "M"}, "mbs_procedures": {"P"}}
AU = Path(os.environ.get("AU_RF2_SNAPSHOT", os.path.expanduser("~/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/Snapshot")))
DESCR = AU / "Terminology/sct2_Description_Snapshot-en-au_AU1000036_20260831.txt"
STOP = set("the of a an in on and".split())


def stem(w: str) -> str:
    for a, b in (("ae", "a"), ("ies", "y"), ("es", ""), ("s", "")):
        if w.endswith(a) and len(w) > len(a) + 2 and not w.endswith(("ss", "us", "is")):
            return w[: -len(a)] + b
    return w


def bag(s: str) -> str:
    """A name with case, punctuation, word order, plurals and of / the set aside."""
    return " ".join(sorted(stem(w) for w in re.findall(r"[a-z0-9]+", s.lower().replace("-", " ")) if w not in STOP))


def sheet(q: str) -> list[dict]:
    return list(csv.DictReader(open(SHEETS / f"{q}.csv", encoding="utf-8-sig")))


def sct_names(con, ids) -> dict[str, set[str]]:
    con.execute("CREATE OR REPLACE TEMP TABLE ids (id VARCHAR)")
    con.executemany("INSERT INTO ids VALUES (?)", [(i,) for i in sorted(ids)])
    out = collections.defaultdict(set)
    for cid, t in con.execute(f"""SELECT conceptId, term FROM read_csv('{DESCR}', delim='\t', header=true, quote='', all_varchar=true) d
                                  JOIN ids ON ids.id = d.conceptId WHERE active = '1'""").fetchall():
        out[cid].add(t)
    return out


def hpo_names() -> dict[str, set[str]]:
    out, cur = collections.defaultdict(set), None
    for line in open("cache/hpo/hp.obo"):
        if line.startswith("[Term]"):
            cur = None
        elif line.startswith("id: HP:"):
            cur = line[4:].strip()
        elif cur and line.startswith("name: "):
            out[cur].add(line[6:].strip())
        elif cur and line.startswith("synonym: ") and " EXACT" in line:
            out[cur].add(line.split('"')[1])
    return out


def ncbi_names(con, ids) -> dict[str, set[str]]:
    con.execute("CREATE OR REPLACE TEMP TABLE ids (id VARCHAR)")
    con.executemany("INSERT INTO ids VALUES (?)", [(i,) for i in sorted(ids)])
    out = collections.defaultdict(set)
    for code, s in con.execute("""SELECT code, str FROM 'cache/umls/2026AA/mrconso.parquet' m JOIN ids ON ids.id = m.code
                                  WHERE sab = 'NCBI'""").fetchall():
        out[code].add(s)
    return out


def moved_genus(a: str, b: str) -> bool:
    """Two binomials with the same species epithet (allowing a gender ending) under different genera."""
    s, o = a.split(), b.split()
    return (len(s) == 2 and len(o) == 2 and s[0] != o[0] and s[0][0].isupper() and s[1].islower()
            and (s[1] == o[1] or s[1][:-2] == o[1][:-2]))


def packets(a) -> int:
    DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("ATTACH 'out/compendium.duckdb' AS cmp (READ_ONLY)")
    tag = lambda ids: dict(con.execute("SELECT id, tag FROM cmp.concept WHERE id IN (SELECT UNNEST(?))", [sorted(ids)]).fetchall())
    sfx = f"_{a.round}" if a.round else ""
    rules, todo = {}, {}
    done = set()                       # a later round packs only the rows no earlier round read
    if a.round:
        rules = json.load(open(DIR / "rule_readings.json"))
        done = set(rules) | {k for f in DIR.glob("keys_*.json") for k in json.load(open(f))}

    rows = sheet("hpo_snomed")
    sd, hs, tg = sct_names(con, {r["object_code"] for r in rows}), hpo_names(), tag({r["object_code"] for r in rows})
    for r in [r for r in rows if r["id"] not in done]:
        if {bag(x) for x in hs[r["subject_code"]] | {r["subject_name"]}} & {bag(x) for x in sd[r["object_code"]]}:
            rules[r["id"]] = "S"
        else:
            other = lambda s, n: "; ".join(sorted(x for x in s if x != n)[:4])
            todo.setdefault("hpo_snomed", []).append((r["id"], r["subject_name"], other(hs[r["subject_code"]], r["subject_name"]),
                                                      f"{r['object_name']} ({tg.get(r['object_code'], '?')})", other(sd[r["object_code"]], r["object_name"])))
    rows = sheet("organism_ncbi")
    sd, nc = sct_names(con, {r["subject_code"] for r in rows}), ncbi_names(con, {r["object_code"] for r in rows})
    for r in [r for r in rows if r["id"] not in done]:
        if {bag(x) for x in sd[r["subject_code"]] | {r["subject_name"]}} & {bag(x) for x in nc[r["object_code"]] | {r["object_name"]}}:
            rules[r["id"]] = "S"
        elif moved_genus(r["subject_name"], r["object_name"]):
            rules[r["id"]] = "M"
        else:
            other = lambda s, n: "; ".join(sorted(x for x in s if x != n)[:5])
            todo.setdefault("organism_ncbi", []).append((r["id"], r["subject_name"], other(sd[r["subject_code"]], r["subject_name"]),
                                                         r["object_name"], other(nc[r["object_code"]], r["object_name"])))
    rows = sheet("mbs_procedures")
    desc = {d.findtext("ItemNum"): re.sub(r"\s+", " ", d.findtext("Description") or "").strip()
            for d in ET.parse("cache/mbs/MBS-XML-20260801.XML").getroot().iter("Data")}
    for r in [r for r in rows if r["id"] not in done]:     # one packet line an item: its descriptor, then each candidate
        todo.setdefault("mbs_procedures", []).append((r["id"], r["subject_code"], desc.get(r["subject_code"], "")[:300], r["object_name"], ""))

    (DIR / "rule_readings.json").write_text(json.dumps(rules, indent=0) + "\n")
    for q, items in todo.items():
        n = max(1, min(PARTS[q], len(items) // 400))
        if q == "mbs_procedures":         # keep an item's candidates in one packet
            subjects = sorted({x[1] for x in items}, key=lambda s: int(re.sub(r"\D", "", s) or 0))
            part_of = {s: i * n // len(subjects) for i, s in enumerate(subjects)}
        for k in range(n):
            with open(DIR / f"packet_{q}{sfx}_{k + 1}.tsv", "w") as f:
                w = csv.writer(f, delimiter="\t", lineterminator="\n")
                if q == "mbs_procedures":
                    w.writerow(["key", "item", "descriptor", "candidate"])
                    last = None
                    for i, x in enumerate(items):
                        if part_of[x[1]] == k:
                            w.writerow([i, x[1], x[2] if x[1] != last else '(same item)', x[3]])
                            last = x[1]
                else:
                    w.writerow(["key", "subject", "subject_synonyms", "candidate", "candidate_synonyms"])
                    for i, x in enumerate(items):
                        if i * n // len(items) == k:
                            w.writerow([i, *x[1:]])
        (DIR / f"keys_{q}{sfx}.json").write_text(json.dumps([x[0] for x in items]) + "\n")
        print(f"  {q:<16} {len(items):>6} rows to read in {n} packet(s): {DIR}/packet_{q}{sfx}_*.tsv")
    print(f"  rule pass: {len(rules):,} rows settled by name -> {DIR / 'rule_readings.json'}")
    return 0


def merge(a) -> int:
    rules = json.load(open(DIR / "rule_readings.json"))
    for q in OUT:
        codes = {k: (c, "names agree once synonyms are compared" if c == "S" else "same species epithet, another genus")
                 for k, c in rules.items() if k.startswith(q + "|")}
        chk = DIR / f"rule_checked_{q}.tsv"     # rule rows read afterwards (an HPO 'exact' synonym can be loose)
        if chk.exists():
            for line in open(chk):
                k, c, note = (line.rstrip("\n").split("\t") + ["", ""])[:3]
                codes[k] = (c, (note + "; " if note else "") + "the names agree only through a synonym")
        missing = set()
        for kf in sorted(DIR.glob(f"keys_{q}*.json")):
            sfx = kf.stem[len(f"keys_{q}"):]
            keys = json.load(open(kf))
            missing |= set(keys)
            for p in sorted(DIR.glob(f"read_{q}{sfx}_*.tsv")):
                if not re.fullmatch(rf"read_{q}{sfx}_\d+\.tsv", p.name):
                    continue
                for line in open(p):
                    f = line.rstrip("\n").split("\t")
                    if not f[0].strip().isdigit():
                        continue
                    c = f[1].strip().upper()[:1] if len(f) > 1 else ""
                    if c not in CODES[q]:
                        print(f"  {p.name}: key {f[0]} has code {c!r}", file=sys.stderr)
                        continue
                    k = keys[int(f[0])]
                    codes[k] = (c, f[2].strip() if len(f) > 2 else "")
                    missing.discard(k)
        if q == "mbs_procedures" and Path("reference/mbs_out_of_scope.json").exists():   # anaesthesia time etc.: no procedure to read
            skip = set(json.load(open("reference/mbs_out_of_scope.json"))["out_of_scope"])
            codes = {k: v for k, v in codes.items() if k.split("|")[2] not in skip}
        readings = collections.defaultdict(dict)
        for k, (c, note) in codes.items():
            _, _, sc, _, oc = k.split("|")
            readings[sc][oc] = CODES[q][c] + (f" -- {note}" if note else "")
        fits = {sc for k, (c, _) in codes.items() for sc in [k.split("|")[2]] if c in ACCEPT[q]}
        for sc, r in readings.items():
            if sc not in fits:
                for oc in r:
                    r[oc] += " -- no candidate fits"
        summary = dict(collections.Counter(CODES[q][c] for c, _ in codes.values()).most_common())
        doc = {"_note": (f"First reading of the {q} review queue (scripts/review_first_reading.py; Claude, 24 Sep 2026): per subject "
                         "and candidate. Rows whose names agree once synonyms are compared were settled by rule; the rest were read. "
                         "'-- no candidate fits' marks a subject to answer 'none'. A reading, not a decision."),
               "rows": len(codes), "unread": len(missing), "subjects": len(readings),
               "subjects_with_a_likely_match": len(fits), "summary": summary, "readings": readings}
        OUT[q].write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print(f"  {q:<16} {len(codes):>6} rows read ({len(missing)} unread), {len(fits):,} of {len(readings):,} subjects with a likely match -> {OUT[q]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["packets", "merge"])
    ap.add_argument("--round", help="a later round: pack only rows not read yet, files suffixed _<round>")
    a = ap.parse_args()
    return {"packets": packets, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
