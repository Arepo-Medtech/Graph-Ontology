#!/usr/bin/env python
"""Bind PBS-derived condition families to SNOMED CT-AU disorder concepts.

Method discipline matches the rest of the compendium: nothing is fuzzy-matched
and every link carries how it was made.

    exact_fsn         condition == FSN with its semantic tag removed
    exact_synonym     condition == an active synonym
    normalised_name   punctuation- and case-insensitive match
    unmatched         no binding; snomed stays null

Body system is NOT keyword-derived. Each bound concept's is-a ancestors are
computed by transitive closure and intersected with `reference/body_systems.json`.
That file ships empty on purpose: the concept ids for body-system roots must be
verified against the AU release in hand, not copied from memory. Populate it with

    python scripts/bind_conditions.py --list-ancestor-roots

which reports the most common high-level ancestors across bound conditions, with
their preferred terms, so they can be checked and named once.

Requires the RF2 snapshot (AU_RF2_SNAPSHOT); see README.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT", "")
IS_A = "116680003"
TAG = re.compile(r"\s*\((disorder|finding|situation|event)\)\s*$", re.I)
PUNCT = re.compile(r"[^a-z0-9]+")


def normalise(term: str) -> str:
    return PUNCT.sub(" ", term.lower()).strip()


def strip_tag(fsn: str) -> str:
    return TAG.sub("", fsn).strip()


def load_disorders(con: duckdb.DuckDBPyConnection, rf2: str) -> None:
    """Active descriptions of active concepts carrying a disorder/finding tag."""
    con.execute(f"""
      CREATE OR REPLACE TABLE description AS
      SELECT * FROM read_csv('{rf2}/Terminology/sct2_Description_Snapshot*.txt',
                             delim='\t', header=true, quote='', all_varchar=true)
      WHERE active = '1';
      CREATE OR REPLACE TABLE relationship AS
      SELECT * FROM read_csv('{rf2}/Terminology/sct2_Relationship_Snapshot*.txt',
                             delim='\t', header=true, quote='', all_varchar=true)
      WHERE active = '1' AND typeId = '{IS_A}';
      CREATE OR REPLACE TABLE fsn AS
      SELECT conceptId, term FROM description WHERE typeId = '900000000000003001'
        AND regexp_matches(term, '\\((disorder|finding)\\)$');
      CREATE OR REPLACE TABLE syn AS
      SELECT d.conceptId, d.term FROM description d
      JOIN (SELECT DISTINCT conceptId FROM fsn) f ON f.conceptId = d.conceptId
      WHERE d.typeId = '900000000000013009';
    """)


def bind(con: duckdb.DuckDBPyConnection, conditions: list[dict]) -> list[dict]:
    lookup_fsn, lookup_syn, lookup_norm = {}, {}, {}
    for cid, term in con.execute("SELECT conceptId, term FROM fsn").fetchall():
        lookup_fsn.setdefault(strip_tag(term), cid)
        lookup_norm.setdefault(normalise(strip_tag(term)), cid)
    for cid, term in con.execute("SELECT conceptId, term FROM syn").fetchall():
        lookup_syn.setdefault(term, cid)
        lookup_norm.setdefault(normalise(term), cid)

    for item in conditions:
        name = item["condition"]
        for method, table, key in (("exact_fsn", lookup_fsn, name),
                                   ("exact_synonym", lookup_syn, name),
                                   ("normalised_name", lookup_norm, normalise(name))):
            cid = table.get(key)
            if cid:
                item["snomed"] = {"concept_id": cid, "method": method, "ancestors": []}
                break
        else:
            item["snomed"] = None
    return conditions


def ancestors(con: duckdb.DuckDBPyConnection, concept_ids: list[str]) -> dict[str, list[str]]:
    if not concept_ids:
        return {}
    con.execute("CREATE OR REPLACE TEMP TABLE seed(id VARCHAR)")
    con.executemany("INSERT INTO seed VALUES (?)", [(c,) for c in concept_ids])
    rows = con.execute("""
      WITH RECURSIVE up(seed, id) AS (
        SELECT id, id FROM seed
        UNION
        SELECT u.seed, r.destinationId FROM up u
        JOIN relationship r ON r.sourceId = u.id
      )
      SELECT seed, id FROM up WHERE seed <> id
    """).fetchall()
    out: dict[str, list[str]] = collections.defaultdict(list)
    for seed, anc in rows:
        out[seed].append(anc)
    return out


def demo() -> None:
    """Verifies matching + closure against RF2-shaped fixtures, no snapshot needed."""
    con = duckdb.connect()
    con.execute("CREATE TABLE fsn(conceptId VARCHAR, term VARCHAR)")
    con.execute("CREATE TABLE syn(conceptId VARCHAR, term VARCHAR)")
    con.execute("CREATE TABLE relationship(sourceId VARCHAR, destinationId VARCHAR)")
    con.executemany("INSERT INTO fsn VALUES (?, ?)", [
        ("100", "Plaque psoriasis (disorder)"),
        ("200", "Asthma (disorder)"),
        ("300", "Crohn disease (disorder)")])
    con.executemany("INSERT INTO syn VALUES (?, ?)", [("300", "Regional enteritis")])
    con.executemany("INSERT INTO relationship VALUES (?, ?)", [
        ("100", "900"), ("900", "999"), ("200", "800")])

    items = [{"condition": "Plaque psoriasis"}, {"condition": "Regional enteritis"},
             {"condition": "plaque  PSORIASIS"}, {"condition": "Nonexistent condition"}]
    bound = bind(con, items)
    assert bound[0]["snomed"]["method"] == "exact_fsn", bound[0]
    assert bound[1]["snomed"]["method"] == "exact_synonym", bound[1]
    assert bound[2]["snomed"]["method"] == "normalised_name", bound[2]
    assert bound[3]["snomed"] is None, bound[3]

    anc = ancestors(con, ["100", "200"])
    assert sorted(anc["100"]) == ["900", "999"], anc   # transitive, not just direct
    assert anc["200"] == ["800"], anc
    assert strip_tag("Asthma (disorder)") == "Asthma"
    assert normalise("Crohn's  disease!") == "crohn s disease"
    print("self-check ok (fixtures; a real run needs AU_RF2_SNAPSHOT)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--list-ancestor-roots", action="store_true")
    parser.add_argument("--conditions", type=Path, default=Path("out/conditions.json"))
    args = parser.parse_args()
    if args.demo:
        demo()
        raise SystemExit(0)
    if not RF2 or not Path(RF2).exists():
        raise SystemExit("AU_RF2_SNAPSHOT is unset or missing - see README")

    payload = json.loads(args.conditions.read_text())
    con = duckdb.connect()
    load_disorders(con, RF2)
    conditions = bind(con, payload["conditions"])
    bound = [c for c in conditions if c["snomed"]]
    anc = ancestors(con, [c["snomed"]["concept_id"] for c in bound])
    for c in bound:
        c["snomed"]["ancestors"] = anc.get(c["snomed"]["concept_id"], [])

    if args.list_ancestor_roots:
        counts = collections.Counter(a for c in bound for a in c["snomed"]["ancestors"])
        for cid, n in counts.most_common(40):
            term = con.execute("SELECT term FROM fsn WHERE conceptId = ?", [cid]).fetchone()
            print(f"{n:5d}  {cid:18s}  {term[0] if term else '(no disorder FSN)'}")
        raise SystemExit(0)

    methods = collections.Counter(
        c["snomed"]["method"] if c["snomed"] else "unmatched" for c in conditions)
    payload["conditions"] = conditions
    args.conditions.write_text(json.dumps(payload, indent=2))
    for method, n in methods.most_common():
        print(f"{n:5d}  {method}")
