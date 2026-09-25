#!/usr/bin/env python3
"""Every SNOMED CT-AU edition, rebuilt offline from the release's own history -- codes, hierarchy, attributes,
terms, reference sets and historical associations, one snapshot per edition, in one database.

The multigraph (out/graph.duckdb) holds one edition, the pin. A question about a *past* edition -- what was under
`Pregnancy, childbirth and puerperium finding` in the January 2023 edition, which products were oral NSAIDs in 2021 --
has so far needed a live terminology server. It need not: the RF2 *Full* files in the NCTS distribution carry every
version of every row since 2002, and an edition is a cut through them.

THE CUT IS NOT ONE DATE. An AU edition dated D bundles an *earlier* International release: the edition's own
module rows are those effective on or before D, but its International rows (modules 900000000000207008 core and
900000000000012004 model) are those effective on or before the International release the AU module *depended on*
at D. That dependency is not guessed: it is read from the Module Dependency reference set
(der2_ssRefset_ModuleDependencyFull), which records for every AU release which International release it was
built on -- 20210131 -> 20200731, 20220131 -> 20210731, 20230131 -> 20220731, 20240131 -> 20230731,
20250131 -> 20240201, 20260131 -> 20260101. Reconstructed that way, every one of the 2,500 expansions
Arepo-Medtech/data-golf-2026 cached from the live server is reproduced exactly (`check`); a single-date cut is
off by hundreds of concepts per edition (docs/snomed-editions.md).

    scripts/snomed_editions.py extract                 # the Full files out of the NCTS zip in ONTOLOGIES -> cache/rf2-full/
    scripts/snomed_editions.py build                   # out/snomed_editions.duckdb, the six editions the competition uses
    scripts/snomed_editions.py build --edition 20250131 --edition 20250731
    scripts/snomed_editions.py check ~/code/data-golf-2026/cache      # replay every cached (ecl, edition) expansion
    scripts/snomed_editions.py ecl 20230131 '<<248982007 MINUS <<118185001'
    scripts/snomed_editions.py ecl 20230131 '<<763158003:<<762951001=<<372665008' --names

Tables, all keyed by `edition` (the AU release date) and with SCTIDs as BIGINT:

    edition          edition, int_base (the International release it bundles), counts, how it was verified
    concept          id, active, module_id, definition_status_id, effective_time -- inactive concepts kept, flagged
    description      active descriptions: id, concept_id, type_id (FSN / synonym), term, case_significance_id
    term             one row per concept: fsn, and pt (preferred in the AU dialect refset, else GB, else US)
    relationship     active inferred relationships: id, source_id, type_id, destination_id, relationship_group
    concrete_value   active concrete values (strengths, counts): source_id, type_id, value, relationship_group
    refset_member    active simple-refset members: refset_id, referenced_component_id
    association      active historical associations: refset_id, referenced_component_id, target_component_id
    closure          the transitive is-a closure over active concepts: ancestor, descendant (proper -- self excluded)

Rules of the road: nothing is typed from memory (the base per edition comes from the release), licensed RF2 content
never enters git (cache/ and out/ are ignored), and `check` is the acceptance gate -- a reconstruction the live server
disagrees with is wrong until explained.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
ONT = Path(os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES")))
RELEASE = "AU1000036_20260831"
ZIP = Path(os.environ.get("AU_RF2_ZIP", ONT / "NCTS_SCT_RF2_DISTRIBUTION_32506021000036107-20260831-ALL.zip"))
FULL = REPO / "cache" / "rf2-full"
OUT = REPO / "out" / "snomed_editions.duckdb"

FILES = {   # what the build reads, by the path inside the zip's Full/ folder
    "concept": f"Terminology/sct2_Concept_Full_{RELEASE}.txt",
    "description": f"Terminology/sct2_Description_Full-en-au_{RELEASE}.txt",
    "definition": f"Terminology/sct2_TextDefinition_Full-en-au_{RELEASE}.txt",
    "relationship": f"Terminology/sct2_Relationship_Full_{RELEASE}.txt",
    "concrete": f"Terminology/sct2_RelationshipConcreteValues_Full_{RELEASE}.txt",
    "language": f"Refset/Language/der2_cRefset_LanguageFull-en-au_{RELEASE}.txt",
    "simple": f"Refset/Content/der2_Refset_SimpleFull_{RELEASE}.txt",
    "association": f"Refset/Content/der2_cRefset_AssociationFull_{RELEASE}.txt",
    "mdrs": f"Refset/Metadata/der2_ssRefset_ModuleDependencyFull_{RELEASE}.txt",
}
AU_MODULE = 32506021000036107
INT_CORE, INT_MODEL = 900000000000207008, 900000000000012004
IS_A, INFERRED = 116680003, 900000000000011006
FSN, SYNONYM, DEFINITION = 900000000000003001, 900000000000013009, 900000000000550004
PREFERRED = 900000000000548007
# What the live server's ECL term filter ({{term = "..."}}) searches, per edition -- MEASURED against the cached
# expansions, not assumed: editions up to 20240131 match FSNs and synonyms only; from 20250131 the server also matches
# text definitions (`<<404684003{{term="bilateral"}}` gains exactly the 299 / 325 concepts whose definitions say
# "bilateral", and adding definitions to the earlier editions adds 220-296 concepts the server did not return).
# Presumably the newer editions were indexed by a newer server release. A later edition inherits the latest rule.
TERM_FILTER_TYPES = {"20210131": "fsn,synonym", "20250131": "fsn,synonym,definition"}
DIALECTS = [32570271000036106, 900000000000508004, 900000000000509007]   # en-AU, en-GB, en-US: first that prefers a term wins
COMPETITION_EDITIONS = ["20210131", "20220131", "20230131", "20240131", "20250131", "20260131"]
OPTS = "delim='\\t', header=true, quote='', escape='', all_varchar=true"


def full(name: str) -> Path:
    return FULL / Path(FILES[name]).name


# ------------------------------------------------------------------------------------------------------ extract
def extract() -> int:
    if not ZIP.exists():
        print(f"REFUSED -- NCTS distribution not found: {ZIP} (set AU_RF2_ZIP)", file=sys.stderr)
        return 1
    FULL.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        names = {n.split("/Full/", 1)[1]: n for n in z.namelist() if "/Full/" in n}
        for key, rel in FILES.items():
            dst = full(key)
            if dst.exists():
                print(f"  present  {dst.name}")
                continue
            if rel not in names:
                print(f"REFUSED -- {rel} is not in the distribution", file=sys.stderr)
                return 1
            with z.open(names[rel]) as src, open(dst, "wb") as out:
                while chunk := src.read(1 << 24):
                    out.write(chunk)
            print(f"  extracted {dst.name} ({dst.stat().st_size / 1e6:,.0f} MB)")
    return 0


# -------------------------------------------------------------------------------------------------------- build
def int_base(con, edition: str) -> str:
    """The International release the AU module depended on at this AU release, from the module dependency refset.
    Refuses an edition the release history does not know: a date that was never an AU release has no content."""
    rows = con.execute(f"""SELECT targetEffectiveTime FROM read_csv('{full('mdrs')}', {OPTS})
        WHERE active = '1' AND moduleId = '{AU_MODULE}' AND referencedComponentId = '{INT_CORE}' AND effectiveTime = ?""",
                       [edition]).fetchall()
    if len({r[0] for r in rows}) != 1:
        raise SystemExit(f"REFUSED -- {edition} is not an AU release in the module dependency history ({len(rows)} rows)")
    return rows[0][0]


def snapshot(con, name: str, edition: str, base: str, cols: str, where: str = "true") -> str:
    """The rows of one Full file as they stood in `edition`: per component id, the latest row effective on or before
    the cut for its module (the International base for core and model, the edition date for everything else)."""
    view = f"snap_{name}"
    con.execute(f"DROP VIEW IF EXISTS {view}")
    con.execute(f"""CREATE TEMP VIEW {view} AS
        SELECT {cols} FROM (
            SELECT *, row_number() OVER (PARTITION BY id ORDER BY effectiveTime DESC) AS rn FROM full_{name}
            WHERE {where} AND effectiveTime <= CASE WHEN moduleId IN ('{INT_CORE}', '{INT_MODEL}') THEN '{base}' ELSE '{edition}' END)
        WHERE rn = 1""")
    return view


def build(editions: list[str]) -> int:
    missing = [full(k) for k in FILES if not full(k).exists()]
    if missing:
        print("REFUSED -- Full files missing (run `extract`):", *missing, sep="\n  ", file=sys.stderr)
        return 1
    if OUT.exists():
        OUT.unlink()
    OUT.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(OUT))
    con.execute("PRAGMA threads=8")
    t0 = time.time()
    print("reading the Full files (every version of every row):")
    for name in ("concept", "description", "definition", "relationship", "concrete", "language", "simple", "association"):
        con.execute(f"CREATE TEMP TABLE full_{name} AS SELECT * FROM read_csv('{full(name)}', {OPTS})")
        print(f"  {name:<14} {con.execute(f'SELECT count(*) FROM full_{name}').fetchone()[0]:>12,} rows   {time.time() - t0:5.0f}s", flush=True)
    con.execute("""CREATE TABLE edition (edition VARCHAR, int_base VARCHAR, term_filter_types VARCHAR, concepts_active BIGINT,
                   concepts_inactive BIGINT, descriptions BIGINT, relationships BIGINT, concrete_values BIGINT, refset_members BIGINT,
                   associations BIGINT, closure_pairs BIGINT, source VARCHAR, built VARCHAR)""")
    con.execute("CREATE TABLE concept (edition VARCHAR, id BIGINT, active BOOLEAN, module_id BIGINT, definition_status_id BIGINT, effective_time VARCHAR)")
    con.execute("CREATE TABLE description (edition VARCHAR, id BIGINT, concept_id BIGINT, type_id BIGINT, term VARCHAR, case_significance_id BIGINT)")
    con.execute("CREATE TABLE term (edition VARCHAR, concept_id BIGINT, fsn VARCHAR, pt VARCHAR, pt_refset_id BIGINT)")
    con.execute("CREATE TABLE relationship (edition VARCHAR, id BIGINT, source_id BIGINT, type_id BIGINT, destination_id BIGINT, relationship_group INTEGER)")
    con.execute("CREATE TABLE concrete_value (edition VARCHAR, id BIGINT, source_id BIGINT, type_id BIGINT, value VARCHAR, relationship_group INTEGER)")
    con.execute("CREATE TABLE refset_member (edition VARCHAR, refset_id BIGINT, referenced_component_id BIGINT)")
    con.execute("CREATE TABLE association (edition VARCHAR, refset_id BIGINT, referenced_component_id BIGINT, target_component_id BIGINT)")
    con.execute("CREATE TABLE closure (edition VARCHAR, ancestor BIGINT, descendant BIGINT)")
    for ed in editions:
        base = int_base(con, ed)
        print(f"edition {ed}  (International base {base}):", flush=True)
        c = snapshot(con, "concept", ed, base, "id, active, moduleId, definitionStatusId, effectiveTime")
        con.execute(f"""INSERT INTO concept SELECT '{ed}', id::BIGINT, active = '1', moduleId::BIGINT, definitionStatusId::BIGINT, effectiveTime FROM {c}""")
        con.execute(f"CREATE OR REPLACE TEMP TABLE act AS SELECT id FROM concept WHERE edition = '{ed}' AND active")
        d = snapshot(con, "description", ed, base, "id, active, conceptId, typeId, term, caseSignificanceId")
        con.execute(f"""INSERT INTO description SELECT '{ed}', id::BIGINT, conceptId::BIGINT, typeId::BIGINT, term, caseSignificanceId::BIGINT
                        FROM {d} WHERE active = '1' AND conceptId::BIGINT IN (SELECT id FROM act)""")
        # text definitions are descriptions too (type 900000000000550004), shipped in their own file
        td = snapshot(con, "definition", ed, base, "id, active, conceptId, typeId, term, caseSignificanceId")
        con.execute(f"""INSERT INTO description SELECT '{ed}', id::BIGINT, conceptId::BIGINT, typeId::BIGINT, term, caseSignificanceId::BIGINT
                        FROM {td} WHERE active = '1' AND conceptId::BIGINT IN (SELECT id FROM act)""")
        # the preferred term: the synonym a dialect refset marks preferred, the AU dialect first; the FSN is unique per concept
        lang = snapshot(con, "language", ed, base, "referencedComponentId, acceptabilityId, refsetId", where="active = '1' OR active = '0'")
        con.execute(f"""INSERT INTO term
            WITH pref AS (
                SELECT d.concept_id, d.term, l.refsetId::BIGINT AS refset_id,
                       row_number() OVER (PARTITION BY d.concept_id ORDER BY list_position({DIALECTS}, l.refsetId::BIGINT), d.id) AS rn
                FROM description d JOIN {lang} l ON l.referencedComponentId::BIGINT = d.id
                WHERE d.edition = '{ed}' AND d.type_id = {SYNONYM} AND l.acceptabilityId = '{PREFERRED}'
                  AND l.refsetId::BIGINT IN {tuple(DIALECTS)})
            SELECT '{ed}', a.id, f.term, p.term, p.refset_id
            FROM act a
            LEFT JOIN (SELECT concept_id, min(term) AS term FROM description WHERE edition = '{ed}' AND type_id = {FSN} GROUP BY 1) f ON f.concept_id = a.id
            LEFT JOIN pref p ON p.concept_id = a.id AND p.rn = 1""")
        r = snapshot(con, "relationship", ed, base, "id, active, sourceId, typeId, destinationId, relationshipGroup",
                     where=f"characteristicTypeId = '{INFERRED}'")
        con.execute(f"""INSERT INTO relationship SELECT '{ed}', id::BIGINT, sourceId::BIGINT, typeId::BIGINT, destinationId::BIGINT, relationshipGroup::INTEGER
                        FROM {r} WHERE active = '1' AND sourceId::BIGINT IN (SELECT id FROM act) AND destinationId::BIGINT IN (SELECT id FROM act)""")
        cv = snapshot(con, "concrete", ed, base, "id, active, sourceId, typeId, value, relationshipGroup", where=f"characteristicTypeId = '{INFERRED}'")
        con.execute(f"""INSERT INTO concrete_value SELECT '{ed}', id::BIGINT, sourceId::BIGINT, typeId::BIGINT, value, relationshipGroup::INTEGER
                        FROM {cv} WHERE active = '1' AND sourceId::BIGINT IN (SELECT id FROM act)""")
        s = snapshot(con, "simple", ed, base, "active, refsetId, referencedComponentId")
        con.execute(f"""INSERT INTO refset_member SELECT DISTINCT '{ed}', refsetId::BIGINT, referencedComponentId::BIGINT FROM {s} WHERE active = '1'""")
        a = snapshot(con, "association", ed, base, "active, refsetId, referencedComponentId, targetComponentId")
        con.execute(f"""INSERT INTO association SELECT DISTINCT '{ed}', refsetId::BIGINT, referencedComponentId::BIGINT, targetComponentId::BIGINT
                        FROM {a} WHERE active = '1'""")
        # the transitive closure over active is-a edges: proper ancestor -> descendant pairs, deduplicated per level
        con.execute(f"""INSERT INTO closure
            WITH RECURSIVE isa AS (SELECT source_id AS child, destination_id AS parent FROM relationship WHERE edition = '{ed}' AND type_id = {IS_A}),
            up(anc, des) AS (
                SELECT parent, child FROM isa
                UNION
                SELECT isa.parent, up.des FROM up JOIN isa ON isa.child = up.anc)
            SELECT '{ed}', anc, des FROM up""")
        n = lambda t, extra="": con.execute(f"SELECT count(*) FROM {t} WHERE edition = '{ed}' {extra}").fetchone()[0]
        counts = (n("concept", "AND active"), n("concept", "AND NOT active"), n("description"), n("relationship"), n("concrete_value"),
                  n("refset_member"), n("association"), n("closure"))
        tft = TERM_FILTER_TYPES[max(k for k in TERM_FILTER_TYPES if k <= ed)]
        con.execute("INSERT INTO edition VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [ed, base, tft, *counts, f"NCTS SNOMED CT-AU RF2 Full {RELEASE}; International base from der2_ssRefset_ModuleDependencyFull",
                     time.strftime("%Y-%m-%d %H:%M")])
        print(f"  concepts {counts[0]:,} active / {counts[1]:,} inactive; descriptions {counts[2]:,}; relationships {counts[3]:,}; "
              f"concrete {counts[4]:,}; refset members {counts[5]:,}; associations {counts[6]:,}; closure {counts[7]:,}   {time.time() - t0:5.0f}s", flush=True)
    for t, cols in (("concept", "edition, id"), ("description", "edition, concept_id"), ("term", "edition, concept_id"),
                    ("relationship", "edition, source_id"), ("relationship", "edition, destination_id"), ("relationship", "edition, type_id"),
                    ("closure", "edition, ancestor"), ("closure", "edition, descendant"), ("refset_member", "edition, refset_id")):
        con.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_{cols.split(', ')[1]} ON {t} ({cols})")
    con.close()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:,.0f} MB) in {time.time() - t0:.0f}s")
    return 0


# -------------------------------------------------------------------------------------------------------- check
def shape(ecl: str) -> str:
    s = re.sub(r'"[^"]*"', '"T"', ecl)
    s = re.sub(r"\d{6,}", "ID", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(ID OR ){3,}ID", "ID OR ... OR ID", s)
    s = re.sub(r"(<<ID OR ){3,}<<ID", "<<ID OR ... OR <<ID", s)
    return s


def check(cache_dir: Path, editions: list[str] | None, verbose: bool) -> int:
    """Replay every (ecl, edition) expansion the competition cached from the live server and compare code sets.
    Exact agreement is the gate; each disagreement is printed with what was missing and what was extra."""
    from snomed_ecl import Evaluator
    con = duckdb.connect(str(OUT), read_only=True)
    built = [r[0] for r in con.execute("SELECT edition FROM edition").fetchall()]
    files = sorted(p for p in cache_dir.glob("*/*.json") if p.parent.name in built and (not editions or p.parent.name in editions))
    by_shape: dict[str, Counter] = defaultdict(Counter)
    failures = []
    t0 = time.time()
    for i, p in enumerate(files, 1):
        d = json.loads(p.read_text())
        ecl, ed, want = d["ecl"], d["edition"], set(d["codes"])
        sh = shape(ecl)
        try:
            got = {str(x) for x in Evaluator(con, ed).expand(ecl)}
        except Exception as e:   # noqa: BLE001 -- a parse or evaluation failure is a finding, not a crash
            by_shape[sh]["error"] += 1
            failures.append((ed, ecl, f"ERROR {type(e).__name__}: {e}"))
            continue
        if got == want:
            by_shape[sh]["exact"] += 1
        else:
            by_shape[sh]["mismatch"] += 1
            miss, extra = sorted(want - got), sorted(got - want)
            failures.append((ed, ecl, f"cached {len(want):,} rebuilt {len(got):,}: missing {len(miss)} {miss[:6]} extra {len(extra)} {extra[:6]}"))
        if verbose or i % 250 == 0:
            print(f"  {i}/{len(files)}  {time.time() - t0:.0f}s", flush=True)
    total = Counter()
    for c in by_shape.values():
        total.update(c)
    print(f"\n{len(files)} cached expansions replayed in {time.time() - t0:.0f}s: exact {total['exact']}, mismatch {total['mismatch']}, error {total['error']}")
    print(f"\n{'shape':<70} {'exact':>6} {'mism':>5} {'err':>4}")
    for sh, c in sorted(by_shape.items(), key=lambda x: -sum(x[1].values())):
        print(f"{sh[:70]:<70} {c['exact']:>6} {c['mismatch']:>5} {c['error']:>4}")
    if failures:
        print(f"\n{len(failures)} disagreements:")
        for ed, ecl, why in failures[:60]:
            print(f"  {ed}  {ecl[:110]}\n      {why}")
    return 1 if failures else 0


def ecl_cmd(edition: str, ecl: str, names: bool) -> int:
    from snomed_ecl import Evaluator
    con = duckdb.connect(str(OUT), read_only=True)
    codes = sorted(Evaluator(con, edition).expand(ecl))
    if names:
        lab = dict(con.execute("SELECT concept_id, coalesce(pt, fsn) FROM term WHERE edition = ? AND concept_id IN (SELECT unnest(?))",
                               [edition, codes]).fetchall())
        for c in codes:
            print(c, lab.get(c, "(inactive)"))
    else:
        print(*codes, sep="\n")
    print(f"-- {len(codes)} concepts", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("extract")
    b = sub.add_parser("build")
    b.add_argument("--edition", action="append", help="AU release date (repeatable); default: the six competition editions")
    c = sub.add_parser("check")
    c.add_argument("cache_dir", type=Path, help="data-golf cache/ with <edition>/<sha1>.json expansions")
    c.add_argument("--edition", action="append")
    c.add_argument("-v", "--verbose", action="store_true")
    e = sub.add_parser("ecl")
    e.add_argument("edition")
    e.add_argument("ecl")
    e.add_argument("--names", action="store_true")
    a = ap.parse_args()
    if a.cmd == "extract":
        return extract()
    if a.cmd == "build":
        return build(a.edition or COMPETITION_EDITIONS)
    if a.cmd == "check":
        return check(a.cache_dir, a.edition, a.verbose)
    return ecl_cmd(a.edition, a.ecl, a.names)


if __name__ == "__main__":
    sys.exit(main())
