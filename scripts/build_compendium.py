#!/usr/bin/env python
"""Build the AU medicines transcode compendium from local sources with DuckDB.

Sources
  RF2   SNOMED CT-AU snapshot (licensed NCTS content, READ only, never committed): descriptions,
        relationships, AU language refset. AMT lives inside it with the international drug-model tags:
          branded clinical drug (TPUU)  branded clinical drug package (TPP)
          containerized branded clinical drug package (CTPP)  clinical drug (MPUU)
          clinical drug package (MPP)  medicinal product form (MPF)  medicinal product (MP)
          product name (BRAND)
  PBS   Public API v3 latest schedule: items, AMT links, ATC codes and item-to-ATC relationships
  AMH   Curated, paraphrased clinical evidence metadata with direct links to the July 2026 edition
  RxNorm cache/rxcui_to_sctid.json (RxNav bridge) and cache/rxnorm_substances.json (rxnorm_enrich.py)

Output (out/, gitignored): compendium.duckdb plus parquet/CSV of the main tables.
Licence: SNOMED/AMT terms stay local (NCTS licence). PBS is CC BY (copyright notice retained).
AMH monograph text is not reproduced; records contain concise classifications and source links.
RxNorm is US public domain.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT",
                     "/Users/ken-lee-arepo/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260731/Snapshot")
REL = "20260731"
OUT = Path("out"); OUT.mkdir(exist_ok=True)
DB = OUT / "compendium.duckdb"
if DB.exists():
    DB.unlink()
con = duckdb.connect(str(DB))

ISA, PRODUCT_NAME, CONTAINS, ACTIVE_ING, PRECISE_ING, BOSS, DOSE_FORM = (
    "116680003", "774158006", "774160008", "127489000", "762949000", "732943007", "411116001")
AU_LANG, PREFERRED, FSN_TYPE = "32570271000036106", "900000000000548007", "900000000000003001"
LEVELS = {
    "branded clinical drug": "TPUU", "branded clinical drug package": "TPP",
    "containerized branded clinical drug package": "CTPP", "clinical drug": "MPUU",
    "clinical drug package": "MPP", "medicinal product form": "MPF", "medicinal product": "MP",
    "product name": "BRAND", "branded product": "TP_DEVICE",
    # legacy AMT v3 tags still present for some concepts
    "trade product unit of use": "TPUU", "trade product pack": "TPP", "containered trade product pack": "CTPP",
    "medicinal product unit of use": "MPUU", "medicinal product pack": "MPP",
}

# --- concept status ------------------------------------------------------------------------------
# The AU bundle as distributed here ships no sct2_Concept_Snapshot file, and inactive concepts keep
# active descriptions, so "has an active FSN" is NOT "is active" (557 inactive products leaked in
# before this check existed). Resolution order: (1) a Concept snapshot in the RF2 dir, (2) a Concept
# Full file at the release root or under Full/Terminology, collapsed to its latest row per id,
# (3) the OWL expression refset (every active concept has an active axiom; the root has none).
def _concept_status_sql():
    snap = glob.glob(f"{RF2}/Terminology/sct2_Concept_Snapshot*.txt")
    if snap:
        return "snapshot", f"SELECT id, active FROM read_csv('{snap[0]}', delim='\t', header=true, quote='', all_varchar=true)"
    root = os.path.dirname(RF2.rstrip("/"))
    full = glob.glob(f"{root}/sct2_Concept_Full*.txt") + glob.glob(f"{root}/Full/Terminology/sct2_Concept_Full*.txt")
    if full:
        return "full", (f"SELECT id, active FROM (SELECT id, active, row_number() OVER (PARTITION BY id ORDER BY effectiveTime DESC) rn "
                        f"FROM read_csv('{full[0]}', delim='\t', header=true, quote='', all_varchar=true)) WHERE rn=1")
    owl = glob.glob(f"{RF2}/Terminology/sct2_sRefset_OWLExpressionSnapshot*.txt")
    if owl:
        return "owl", (f"SELECT referencedComponentId AS id, max(active) AS active "
                       f"FROM read_csv('{owl[0]}', delim='\t', header=true, quote='', all_varchar=true) GROUP BY 1")
    raise SystemExit("no source for concept activeness (Concept snapshot, Concept Full, or OWL refset)")

CONCEPT_STATUS_SOURCE, _status_sql = _concept_status_sql()
print(f"loading RF2 … (concept status from {CONCEPT_STATUS_SOURCE})", flush=True)
con.execute(f"CREATE TABLE concept_status AS {_status_sql}")
con.execute(f"""
CREATE TABLE dsc AS SELECT id, active, moduleId, conceptId, typeId, term
  FROM read_csv('{RF2}/Terminology/sct2_Description_Snapshot-en-au_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
CREATE TABLE rel AS SELECT sourceId AS src, destinationId AS dst, typeId AS typ, CAST(relationshipGroup AS INT) AS grp
  FROM read_csv('{RF2}/Terminology/sct2_Relationship_Snapshot_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true)
  WHERE active='1' AND characteristicTypeId='900000000000011006';
CREATE TABLE lang AS SELECT referencedComponentId AS descId
  FROM read_csv('{RF2}/Refset/Language/der2_cRefset_LanguageSnapshot-en-au_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true)
  WHERE active='1' AND refsetId='{AU_LANG}' AND acceptabilityId='{PREFERRED}';
""")
con.execute(f"""
CREATE TABLE concept AS
WITH f AS (SELECT conceptId AS id, moduleId AS module, term AS fsn, regexp_extract(term, '\\(([^()]+)\\)$', 1) AS tag
           FROM dsc WHERE active='1' AND typeId='{FSN_TYPE}'
             AND conceptId IN (SELECT id FROM concept_status WHERE active='1')),
     p AS (SELECT d.conceptId AS id, any_value(d.term) AS pt FROM dsc d JOIN lang l ON l.descId=d.id
           WHERE d.active='1' AND d.typeId<>'{FSN_TYPE}' GROUP BY 1)
SELECT f.id, f.module, f.fsn, f.tag, coalesce(p.pt, regexp_replace(f.fsn, ' \\([^()]+\\)$', '')) AS pt,
       f.module NOT IN ('900000000000207008','900000000000012004') AS au_authored
FROM f LEFT JOIN p USING (id);
""")
lv = ", ".join(f"('{k}','{v}')" for k, v in LEVELS.items())
con.execute(f"CREATE TABLE level_map(tag VARCHAR, level VARCHAR); INSERT INTO level_map VALUES {lv};")
con.execute("""
CREATE TABLE product AS
SELECT c.id, c.pt, c.fsn, c.tag, m.level, c.au_authored FROM concept c JOIN level_map m USING (tag);
""")
print(con.sql("SELECT level, count(*) n FROM product GROUP BY 1 ORDER BY n DESC").df().to_string(index=False), flush=True)

# --- edges ------------------------------------------------------------------------------------
con.execute(f"""
CREATE TABLE brand_of   AS SELECT src AS product_id, dst AS brand_id FROM rel WHERE typ='{PRODUCT_NAME}';
CREATE TABLE parent_of  AS SELECT src AS child_id, dst AS parent_id FROM rel WHERE typ='{ISA}';
CREATE TABLE contains   AS SELECT src AS package_id, dst AS unit_id FROM rel WHERE typ='{CONTAINS}';
CREATE TABLE ingredient AS
  SELECT r.src AS product_id, r.grp,
         max(CASE WHEN r.typ='{ACTIVE_ING}'  THEN r.dst END) AS active_substance_id,
         max(CASE WHEN r.typ='{PRECISE_ING}' THEN r.dst END) AS precise_substance_id,
         max(CASE WHEN r.typ='{BOSS}'        THEN r.dst END) AS boss_substance_id
  FROM rel r WHERE r.typ IN ('{ACTIVE_ING}','{PRECISE_ING}','{BOSS}') GROUP BY 1,2;
CREATE TABLE dose_form  AS SELECT src AS product_id, dst AS dose_form_id FROM rel WHERE typ='{DOSE_FORM}';
""")

# --- generic resolution: TPUU -> MPUU (is-a), TPP -> MPP (is-a), CTPP -> TPP (is-a); packages -> unit
con.execute("""
CREATE TABLE unit_generic AS      -- TPUU -> nearest MPUU parent
  SELECT p.child_id AS tpuu_id, p.parent_id AS mpuu_id
  FROM parent_of p JOIN product a ON a.id=p.child_id AND a.level='TPUU' JOIN product b ON b.id=p.parent_id AND b.level='MPUU';
CREATE TABLE pack_generic AS      -- TPP -> MPP
  SELECT p.child_id AS tpp_id, p.parent_id AS mpp_id
  FROM parent_of p JOIN product a ON a.id=p.child_id AND a.level='TPP' JOIN product b ON b.id=p.parent_id AND b.level='MPP';
CREATE TABLE ctpp_tpp AS          -- CTPP -> TPP
  SELECT p.child_id AS ctpp_id, p.parent_id AS tpp_id
  FROM parent_of p JOIN product a ON a.id=p.child_id AND a.level='CTPP' JOIN product b ON b.id=p.parent_id AND b.level='TPP';
CREATE TABLE mpuu_mp AS           -- MPUU -> MP via is-a closure limited to MPF/MP (2 hops)
  WITH h1 AS (SELECT c.child_id AS mpuu_id, c.parent_id AS pid FROM parent_of c JOIN product a ON a.id=c.child_id AND a.level='MPUU'),
       h2 AS (SELECT h1.mpuu_id, p.parent_id AS pid FROM h1 JOIN parent_of p ON p.child_id=h1.pid)
  SELECT DISTINCT mpuu_id, pid AS mp_id FROM (SELECT * FROM h1 UNION ALL SELECT * FROM h2) u JOIN product b ON b.id=u.pid AND b.level IN ('MP','MPF');
""")

# --- PBS --------------------------------------------------------------------------------------
pbs_sources = {
    name: json.load(open(f"cache/pbs/{name}.json"))
    for name in ("amt-items", "items", "atc-codes", "item-atc-relationships")
}
pbs_schedules = {name: source.get("schedule_code") for name, source in pbs_sources.items()}
if any(schedule is None for schedule in pbs_schedules.values()) or len(set(pbs_schedules.values())) != 1:
    raise RuntimeError(f"PBS cache contains mixed schedules: {pbs_schedules}")
ai = pbs_sources["amt-items"]
it = pbs_sources["items"]
atc = pbs_sources["atc-codes"]
item_atc = pbs_sources["item-atc-relationships"]
(OUT / "_pbs_amt.json").write_text(json.dumps(ai["rows"]))
(OUT / "_pbs_item.json").write_text(json.dumps(it["rows"]))
(OUT / "_pbs_atc.json").write_text(json.dumps(atc["rows"]))
(OUT / "_pbs_item_atc.json").write_text(json.dumps(item_atc["rows"]))
con.execute("CREATE TABLE pbs_amt AS SELECT * FROM read_json_auto('out/_pbs_amt.json')")
con.execute("CREATE TABLE pbs_item AS SELECT * FROM read_json_auto('out/_pbs_item.json', maximum_object_size=100000000)")
con.execute("CREATE TABLE pbs_atc_code AS SELECT * FROM read_json_auto('out/_pbs_atc.json')")
con.execute("CREATE TABLE pbs_item_atc AS SELECT * FROM read_json_auto('out/_pbs_item_atc.json')")
con.execute("""
CREATE TABLE pbs AS
SELECT a.li_item_id, i.pbs_code, i.li_drug_name AS pbs_ingredient, i.brand_name AS pbs_brand, i.li_form AS pbs_form,
       i.manner_of_administration, i.program_code, a.schedule_code,
       CAST(a.amt_code AS VARCHAR) AS amt_code, a.concept_type_code AS pbs_level, a.preferred_term AS pbs_amt_term
FROM pbs_amt a LEFT JOIN (SELECT DISTINCT li_item_id, pbs_code, li_drug_name, brand_name, li_form, manner_of_administration, program_code FROM pbs_item) i USING (li_item_id);
""")

con.execute("""
CREATE TABLE pbs_tpuu AS          -- PBS rows attached to the trade unit they name directly or via a pack they list
SELECT DISTINCT t.id AS tpuu_id, p.pbs_code, p.pbs_brand, p.pbs_ingredient, p.li_item_id, p.pbs_level
FROM pbs p JOIN product t ON t.id=p.amt_code AND t.level='TPUU'
UNION
SELECT DISTINCT c.unit_id, p.pbs_code, p.pbs_brand, p.pbs_ingredient, p.li_item_id, p.pbs_level
FROM pbs p JOIN contains c ON c.package_id=p.amt_code JOIN product t ON t.id=c.unit_id AND t.level='TPUU';
""")

# PBS ATC classification is a therapeutic listing signal, not a complete Australian supplement
# registry and not proof of the purpose for which a patient uses a product.
con.execute("""
CREATE TABLE supplement_listing AS
WITH amt AS (
  SELECT li_item_id, schedule_code,
         list(DISTINCT concept_type_code ORDER BY concept_type_code) AS amt_levels,
         list(DISTINCT CAST(amt_code AS VARCHAR) ORDER BY CAST(amt_code AS VARCHAR)) AS amt_codes,
         list(DISTINCT preferred_term ORDER BY preferred_term) AS amt_terms
  FROM pbs_amt
  GROUP BY 1,2
), classified AS (
  SELECT DISTINCT
         i.schedule_code, i.pbs_code, i.li_item_id,
         i.brand_name, i.drug_name, i.li_drug_name, i.li_form, i.schedule_form,
         i.manner_of_administration, i.moa_preferred_term,
         i.benefit_type_code, i.program_code, i.first_listed_date, i.non_effective_date,
         r.atc_code, a.atc_description, a.atc_level, a.atc_parent_code,
         r.atc_priority_pct,
         CASE
           WHEN r.atc_code LIKE 'A11%' THEN 'vitamin'
           WHEN r.atc_code LIKE 'A12%' THEN 'mineral_supplement'
           WHEN r.atc_code LIKE 'B03A%' THEN 'iron_preparation'
         END AS supplement_family
  FROM pbs_item i
  JOIN pbs_item_atc r USING (pbs_code, schedule_code)
  JOIN pbs_atc_code a USING (atc_code, schedule_code)
  WHERE r.atc_code LIKE 'A11%' OR r.atc_code LIKE 'A12%' OR r.atc_code LIKE 'B03A%'
)
SELECT c.*, amt.amt_levels, amt.amt_codes, amt.amt_terms,
       'PBS ATC classification' AS classification_basis,
       'PBS-subsidised listings; absence does not establish that a product is unavailable in Australia' AS source_scope,
       'https://www.pbs.gov.au/medicine/item/' || c.pbs_code AS source_url
FROM classified c
LEFT JOIN amt USING (li_item_id, schedule_code);
""")

# --- curated clinical evidence ---------------------------------------------------------------
# Keep this layer separate from terminology and PBS classification. Its dimensions prevent a
# substance name from becoming an unconditional rule when route, timing, dose or role changes the
# conclusion. Entries are concise paraphrases; the licensed source remains authoritative.
evidence_path = Path("reference/amh_clinical_evidence.json")
evidence_rows = json.loads(evidence_path.read_text())
required_evidence_fields = {
    "evidence_id", "domain", "subject", "subject_kind", "route_scope", "pregnancy_window",
    "dose_context", "evidence_category", "recommendation", "summary", "source_title",
    "source_url", "source_edition", "accessed_date",
}
if not evidence_rows:
    raise RuntimeError(f"No clinical evidence records in {evidence_path}")
for row_number, row in enumerate(evidence_rows, start=1):
    missing = required_evidence_fields - row.keys()
    if missing:
        raise RuntimeError(f"Clinical evidence row {row_number} is missing {sorted(missing)}")
    if row["domain"] not in {"pregnancy_safety", "supplement_role", "therapeutic_role"}:
        raise RuntimeError(f"Unsupported clinical evidence domain: {row['domain']}")
    if not row["source_url"].startswith("https://amhonline.amh.net.au/"):
        raise RuntimeError(f"Clinical evidence row {row_number} has a non-AMH source URL")
evidence_ids = [row["evidence_id"] for row in evidence_rows]
if len(evidence_ids) != len(set(evidence_ids)):
    raise RuntimeError("Clinical evidence IDs must be unique")
(OUT / "_amh_clinical_evidence.json").write_text(json.dumps(evidence_rows))
con.execute("""
CREATE TABLE clinical_evidence AS
SELECT *,
       'Curated paraphrase; consult the linked licensed AMH monograph before clinical use' AS provenance_note
FROM read_json_auto('out/_amh_clinical_evidence.json');
CREATE TABLE pregnancy_safety_evidence AS
SELECT * FROM clinical_evidence WHERE domain='pregnancy_safety';
CREATE TABLE supplement_role_evidence AS
SELECT * FROM clinical_evidence WHERE domain='supplement_role';
CREATE TABLE therapeutic_role_evidence AS
SELECT * FROM clinical_evidence WHERE domain='therapeutic_role';
""")

# --- RxNorm -----------------------------------------------------------------------------------
rx_rows = []
b = json.load(open("cache/rxcui_to_sctid.json"))
for rxcui, rec in b.items():
    for g in rec["ingredients"]:
        if g.get("sctid"):
            rx_rows.append({"substance_id": g["sctid"], "rxcui_ingredient": g["rxcui"], "rxnorm_name": g["name"], "rxnorm_tty": g["tty"], "source": "synthea-bridge"})
p = Path("cache/rxnorm_substances.json")
if p.exists():
    for sctid, rec in json.load(open(p)).items():
        if rec.get("rxcui"):
            # v2 cache (rxnorm_resolve.py) records the method that produced each link; v1 was by-name only
            rx_rows.append({"substance_id": sctid, "rxcui_ingredient": rec["rxcui"], "rxnorm_name": rec.get("name"), "rxnorm_tty": rec.get("tty"), "source": rec.get("method", "rxnav-by-name")})
(OUT / "_rx.json").write_text(json.dumps(rx_rows or [{"substance_id": None, "rxcui_ingredient": None, "rxnorm_name": None, "rxnorm_tty": None, "source": None}]))
con.execute("CREATE TABLE rxnorm AS SELECT DISTINCT * FROM read_json_auto('out/_rx.json')")

# --- OMOP (OMOPHub bridge: cache/omophub_*.json from scripts/omophub_bridge.py) ------------------------------
# omop_drug: AMT product -> OMOP AMT concept -> standard drug concept (`Maps to`, RxNorm Extension / RxNorm)
# omop_substance: SNOMED substance -> OMOP concept -> RxNorm ingredient, plus agreement with the RxNav route
drug_rows, subst_rows = [], []
pm = Path("cache/omophub_amt_maps.json")
if pm.exists():
    for code, m in json.load(open(pm)).items():
        if not m.get("in_omop"):
            drug_rows.append({"product_id": code, "level": m.get("level", "").upper(), "amt_concept_id": None, "amt_concept_class": None,
                              "standard_concept_id": None, "standard_name": None, "standard_vocabulary": None, "standard_code": None, "in_omop": False})
            continue
        targets = m.get("targets") or []
        if m.get("self_standard"):
            targets = [{"target_concept_id": m["concept_id"], "target_name": None, "target_vocabulary": "AMT", "target_code": code}]
        for t in (targets or [None]):
            drug_rows.append({"product_id": code, "level": m.get("level", "").upper(), "amt_concept_id": m.get("concept_id"), "amt_concept_class": m.get("concept_class"),
                              "standard_concept_id": t["target_concept_id"] if t else None, "standard_name": t.get("target_name") if t else None,
                              "standard_vocabulary": t.get("target_vocabulary") if t else None, "standard_code": t.get("target_code") if t else None, "in_omop": True})
ps = Path("cache/omophub_substances.json")
if ps.exists():
    rxn = json.load(open(Path("cache/rxnorm_substances.json"))) if Path("cache/rxnorm_substances.json").exists() else {}
    for sid, rec in json.load(open(ps)).items():
        o = rec.get("omop") or {}
        rx_targets = [t for t in rec.get("targets") or [] if t.get("target_vocabulary") == "RxNorm"]
        rxnav = (rxn.get(sid) or {}).get("rxcui")
        omop_rxcuis = {str(t["target_code"]) for t in rx_targets}
        agreement = ("agree" if rxnav in omop_rxcuis else "disagree") if (rxnav and omop_rxcuis) else ("omop-only" if omop_rxcuis else ("rxnav-only" if rxnav else "neither"))
        subst_rows.append({"substance_id": sid, "omop_concept_id": o.get("concept_id"), "omop_vocabulary": o.get("vocabulary_id"), "omop_concept_class": o.get("concept_class_id"),
                           "omop_rxcui": ",".join(sorted(omop_rxcuis)) or None, "omop_rxnorm_name": (rx_targets[0].get("target_name") if rx_targets else None),
                           "rxnav_rxcui": rxnav, "agreement": agreement})
(OUT / "_omop_drug.json").write_text(json.dumps(drug_rows or [{"product_id": None, "level": None, "amt_concept_id": None, "amt_concept_class": None, "standard_concept_id": None, "standard_name": None, "standard_vocabulary": None, "standard_code": None, "in_omop": None}]))
(OUT / "_omop_substance.json").write_text(json.dumps(subst_rows or [{"substance_id": None, "omop_concept_id": None, "omop_vocabulary": None, "omop_concept_class": None, "omop_rxcui": None, "omop_rxnorm_name": None, "rxnav_rxcui": None, "agreement": None}]))
# explicit column types: an all-null placeholder row would otherwise be inferred as JSON and break the summary filters
con.execute("""CREATE TABLE omop_drug AS SELECT * FROM read_json_auto('out/_omop_drug.json', columns={product_id:'VARCHAR', level:'VARCHAR', amt_concept_id:'BIGINT',
    amt_concept_class:'VARCHAR', standard_concept_id:'BIGINT', standard_name:'VARCHAR', standard_vocabulary:'VARCHAR', standard_code:'VARCHAR', in_omop:'BOOLEAN'})""")
# review_status is filled by scripts/apply_standard_ingredients.py: flagged | rejected | superseded, NULL = no objection.
# Readers that turn a substance mapping into a product edge must use only rows where it is NULL.
con.execute("""CREATE TABLE omop_substance AS SELECT *, CAST(NULL AS VARCHAR) AS review_status FROM read_json_auto('out/_omop_substance.json', columns={substance_id:'VARCHAR', omop_concept_id:'BIGINT',
    omop_vocabulary:'VARCHAR', omop_concept_class:'VARCHAR', omop_rxcui:'VARCHAR', omop_rxnorm_name:'VARCHAR', rxnav_rxcui:'VARCHAR', agreement:'VARCHAR'})""")

# --- the wide transcode table: one row per TPUU ---------------------------------------------
con.execute("""
CREATE TABLE transcode AS
WITH ing AS (
  SELECT i.product_id,
         string_agg(DISTINCT s.pt, ' + ' ORDER BY s.pt) AS ingredients,
         list(DISTINCT coalesce(i.active_substance_id, i.precise_substance_id)) AS substance_ids,
         string_agg(DISTINCT bs.pt, ' + ' ORDER BY bs.pt) AS boss
  FROM ingredient i LEFT JOIN concept s ON s.id=coalesce(i.active_substance_id, i.precise_substance_id)
                    LEFT JOIN concept bs ON bs.id=i.boss_substance_id
  GROUP BY 1),
packs AS (SELECT c.unit_id AS tpuu_id, list(DISTINCT c.package_id) AS tpp_ids FROM contains c JOIN product p ON p.id=c.package_id AND p.level='TPP' GROUP BY 1),
ctpps AS (SELECT c.unit_id AS tpuu_id, list(DISTINCT c.package_id) AS ctpp_ids FROM contains c JOIN product p ON p.id=c.package_id AND p.level='CTPP' GROUP BY 1),
pbsu AS (SELECT tpuu_id, list(DISTINCT pbs_code) FILTER (WHERE pbs_code IS NOT NULL) AS pbs_codes,
                list(DISTINCT pbs_brand) FILTER (WHERE pbs_brand IS NOT NULL) AS pbs_brands FROM pbs_tpuu GROUP BY 1),
gmp AS (SELECT mm.mpuu_id, list(DISTINCT mp.pt) AS generic_mp FROM mpuu_mp mm JOIN concept mp ON mp.id=mm.mp_id GROUP BY 1),
rx AS (SELECT i.product_id, list(DISTINCT r.rxcui_ingredient) AS rxcuis, string_agg(DISTINCT r.rxnorm_name, ' + ') AS rxnorm_names
       FROM ingredient i JOIN rxnorm r ON r.substance_id=coalesce(i.active_substance_id, i.precise_substance_id) GROUP BY 1),
omop AS (SELECT product_id, any_value(amt_concept_id) AS omop_amt_concept_id, any_value(standard_concept_id) AS omop_drug_concept_id,
                any_value(standard_name) AS omop_drug_name, any_value(standard_vocabulary) AS omop_drug_vocabulary
         FROM omop_drug WHERE standard_concept_id IS NOT NULL GROUP BY 1)
SELECT t.id AS tpuu_id, t.pt AS tpuu_pt, t.fsn AS tpuu_fsn,
       bo.brand_id, bc.pt AS brand,
       ug.mpuu_id, mu.pt AS generic_mpuu,
       gmp.generic_mp,
       ing.ingredients, ing.substance_ids, ing.boss,
       df.pt AS dose_form,
       packs.tpp_ids, ctpps.ctpp_ids,
       pbsu.pbs_codes, pbsu.pbs_brands,
       rx.rxcuis, rx.rxnorm_names,
       omop.omop_amt_concept_id, omop.omop_drug_concept_id, omop.omop_drug_name, omop.omop_drug_vocabulary,
       t.au_authored
FROM product t
LEFT JOIN brand_of bo ON bo.product_id=t.id LEFT JOIN concept bc ON bc.id=bo.brand_id
LEFT JOIN unit_generic ug ON ug.tpuu_id=t.id LEFT JOIN concept mu ON mu.id=ug.mpuu_id
LEFT JOIN ing ON ing.product_id=t.id
LEFT JOIN (SELECT product_id, any_value(dose_form_id) AS dose_form_id FROM dose_form GROUP BY 1) d ON d.product_id=t.id LEFT JOIN concept df ON df.id=d.dose_form_id
LEFT JOIN packs ON packs.tpuu_id=t.id LEFT JOIN ctpps ON ctpps.tpuu_id=t.id
LEFT JOIN pbsu ON pbsu.tpuu_id=t.id LEFT JOIN gmp ON gmp.mpuu_id=ug.mpuu_id
LEFT JOIN rx ON rx.product_id=t.id
LEFT JOIN omop ON omop.product_id=t.id
WHERE t.level='TPUU';
""")

# --- brand table: one row per product-name concept --------------------------------------------
con.execute("""
CREATE TABLE brand AS
SELECT b.id AS brand_id, b.pt AS brand, b.au_authored,
       count(DISTINCT t.tpuu_id) AS n_tpuu,
       list(DISTINCT t.generic_mpuu) FILTER (WHERE t.generic_mpuu IS NOT NULL) AS generics,
       list(DISTINCT t.ingredients) FILTER (WHERE t.ingredients IS NOT NULL) AS ingredient_sets,
       list(DISTINCT pb) FILTER (WHERE pb IS NOT NULL) AS pbs_brand_names,
       list(DISTINCT pc) FILTER (WHERE pc IS NOT NULL) AS pbs_codes
FROM product b LEFT JOIN transcode t ON t.brand_id=b.id
LEFT JOIN unnest(t.pbs_brands) AS u1(pb) ON true LEFT JOIN unnest(t.pbs_codes) AS u2(pc) ON true
WHERE b.level='BRAND' GROUP BY 1,2,3;
""")

# --- brand alias: PBS brand strings -> AMT brand concept, best method wins ------------------------
con.execute("""
CREATE TABLE brand_alias AS
WITH pb AS (SELECT DISTINCT pbs_brand FROM pbs WHERE pbs_brand IS NOT NULL),
     bc AS (SELECT brand_id, brand, lower(brand) AS b, regexp_replace(lower(brand), '[^a-z0-9]', '', 'g') AS bn FROM brand),
     via_code AS (SELECT DISTINCT pt.pbs_brand, bo.brand_id, 'amt_code' AS method
                  FROM pbs_tpuu pt JOIN brand_of bo ON bo.product_id=pt.tpuu_id WHERE pt.pbs_brand IS NOT NULL),
     exact AS (SELECT pb.pbs_brand, bc.brand_id, 'exact_name' AS method FROM pb JOIN bc ON lower(pb.pbs_brand)=bc.b),
     norm AS (SELECT pb.pbs_brand, bc.brand_id, 'normalised_name' AS method FROM pb JOIN bc
              ON regexp_replace(lower(pb.pbs_brand), '[^a-z0-9]', '', 'g')=bc.bn),
     prefix AS (SELECT pb.pbs_brand, bc.brand_id, 'prefix_name' AS method FROM pb JOIN bc ON lower(pb.pbs_brand) LIKE bc.b || ' %'),
     allm AS (SELECT * FROM via_code UNION ALL SELECT * FROM exact UNION ALL SELECT * FROM norm UNION ALL SELECT * FROM prefix),
     ranked AS (SELECT *, row_number() OVER (PARTITION BY pbs_brand, brand_id ORDER BY
                  CASE method WHEN 'amt_code' THEN 1 WHEN 'exact_name' THEN 2 WHEN 'normalised_name' THEN 3 ELSE 4 END) AS rn FROM allm)
SELECT r.pbs_brand, r.brand_id, bc.brand AS amt_brand, r.method FROM ranked r JOIN bc USING (brand_id) WHERE rn=1;
""")
print("brand_alias:", con.sql("""SELECT method, count(DISTINCT pbs_brand) AS pbs_brands FROM brand_alias GROUP BY 1 ORDER BY 2 DESC""").df().to_string(index=False), flush=True)
print("PBS brand strings linked:", con.sql("SELECT count(DISTINCT pbs_brand) FROM brand_alias").fetchone()[0], "of",
      con.sql("SELECT count(DISTINCT pbs_brand) FROM pbs WHERE pbs_brand IS NOT NULL").fetchone()[0], flush=True)

# --- substance table ---------------------------------------------------------------------------
con.execute("""
CREATE TABLE substance AS
WITH used AS (SELECT coalesce(active_substance_id, precise_substance_id) AS sid, product_id FROM ingredient),
     np AS (SELECT sid, count(DISTINCT product_id) AS n_products FROM used GROUP BY 1),
     rx AS (SELECT substance_id AS sid, list(DISTINCT rxcui_ingredient) AS rxcuis, list(DISTINCT rxnorm_name) AS rxnorm_names FROM rxnorm GROUP BY 1),
     pn AS (SELECT u.sid, list(DISTINCT pt.pbs_ingredient) FILTER (WHERE pt.pbs_ingredient IS NOT NULL) AS pbs_ingredient_names
            FROM used u JOIN pbs_tpuu pt ON pt.tpuu_id=u.product_id GROUP BY 1),
     bn AS (SELECT u.sid, count(DISTINCT bo.brand_id) AS n_brands FROM used u JOIN brand_of bo ON bo.product_id=u.product_id GROUP BY 1)
SELECT s.id AS substance_id, s.pt AS substance, s.fsn, s.au_authored, np.n_products, bn.n_brands,
       rx.rxcuis, rx.rxnorm_names, pn.pbs_ingredient_names
FROM concept s JOIN np ON np.sid=s.id LEFT JOIN rx ON rx.sid=s.id LEFT JOIN pn ON pn.sid=s.id LEFT JOIN bn ON bn.sid=s.id
WHERE s.tag IN ('substance','AU substance');
""")

# --- exports -----------------------------------------------------------------------------------
for t in ["transcode", "brand", "brand_alias", "substance", "product", "pbs", "pbs_tpuu", "pbs_atc_code", "pbs_item_atc", "supplement_listing", "clinical_evidence", "pregnancy_safety_evidence", "supplement_role_evidence", "therapeutic_role_evidence", "rxnorm", "omop_drug", "omop_substance", "unit_generic", "pack_generic", "ctpp_tpp", "mpuu_mp", "ingredient", "contains", "brand_of"]:
    con.execute(f"COPY {t} TO 'out/{t}.parquet' (FORMAT PARQUET)")
for t in ["transcode", "brand", "brand_alias", "substance", "supplement_listing", "clinical_evidence", "pregnancy_safety_evidence", "supplement_role_evidence", "therapeutic_role_evidence"]:
    con.execute(f"COPY (SELECT * FROM {t}) TO 'out/{t}.csv' (HEADER)")

print("\n=== compendium summary ===")
print(con.sql("""SELECT
  (SELECT count(*) FROM transcode) AS tpuu_rows,
  (SELECT count(*) FROM transcode WHERE brand IS NOT NULL) AS with_brand,
  (SELECT count(*) FROM transcode WHERE generic_mpuu IS NOT NULL) AS with_generic,
  (SELECT count(*) FROM transcode WHERE ingredients IS NOT NULL) AS with_ingredients,
  (SELECT count(*) FROM transcode WHERE pbs_codes IS NOT NULL) AS with_pbs,
  (SELECT count(*) FROM transcode WHERE rxcuis IS NOT NULL) AS with_rxnorm,
  (SELECT count(*) FROM transcode WHERE omop_drug_concept_id IS NOT NULL) AS with_omop_drug,
  (SELECT count(*) FROM brand) AS brands,
  (SELECT count(*) FROM brand WHERE n_tpuu>0) AS brands_with_products,
  (SELECT count(*) FROM brand WHERE pbs_codes IS NOT NULL AND len(pbs_codes)>0) AS brands_on_pbs,
  (SELECT count(*) FROM substance) AS substances_used,
  (SELECT count(*) FROM substance WHERE rxcuis IS NOT NULL) AS substances_with_rxnorm,
  (SELECT count(*) FROM omop_substance WHERE omop_rxcui IS NOT NULL) AS substances_with_omop_rxnorm,
  (SELECT count(*) FROM omop_substance WHERE agreement='agree') AS substances_routes_agree,
  (SELECT count(*) FROM omop_substance WHERE agreement='disagree') AS substances_routes_disagree,
  (SELECT count(*) FROM supplement_listing) AS supplement_listings,
  (SELECT count(DISTINCT pbs_code) FROM supplement_listing) AS supplement_pbs_codes,
  (SELECT count(*) FROM pregnancy_safety_evidence) AS pregnancy_evidence_rows,
  (SELECT count(*) FROM supplement_role_evidence) AS supplement_role_evidence_rows,
  (SELECT count(*) FROM therapeutic_role_evidence) AS therapeutic_role_evidence_rows
""").df().T.to_string(header=False))
print("\nsample transcode rows:")
# DuckDB samples the FROM before WHERE, so filter in a subquery or the sample is usually empty
print(con.sql("SELECT tpuu_pt, brand, generic_mpuu, ingredients, dose_form, pbs_codes, rxnorm_names FROM (SELECT * FROM transcode WHERE pbs_codes IS NOT NULL AND rxcuis IS NOT NULL) USING SAMPLE 5").df().to_string(index=False, max_colwidth=45))
con.close()
print(f"\nwritten: {DB} + out/*.parquet + selected tables as CSV")
