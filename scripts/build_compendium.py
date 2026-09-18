#!/usr/bin/env python
"""Build the AU medicines transcode compendium from local sources with DuckDB.

Sources
  RF2   SNOMED CT-AU snapshot (licensed NCTS content, READ only, never committed): descriptions,
        relationships, AU language refset. AMT lives inside it with the international drug-model tags:
          branded clinical drug (TPUU)  branded clinical drug package (TPP)
          containerized branded clinical drug package (CTPP)  clinical drug (MPUU)
          clinical drug package (MPP)  medicinal product form (MPF)  medicinal product (MP)
          product name (BRAND)
  PBS   Public API v3 latest schedule: amt-items (PBS line item -> AMT codes per level) + items (brand, form)
  RxNorm cache/rxcui_to_sctid.json (RxNav bridge) and cache/rxnorm_substances.json (rxnorm_enrich.py)

Output (out/, gitignored): compendium.duckdb plus parquet/CSV of the main tables.
Licence: SNOMED/AMT terms stay local (NCTS licence). PBS is CC BY (copyright notice retained).
RxNorm is US public domain.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT",
                     "/Users/ken-arepo/iCloud Drive (Archive)/Documents/Documents - Citrus-Arepo/ONTOLOGIES/"
                     "SnomedCT_Release_AU1000036_20260731/Snapshot")
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

print("loading RF2 …", flush=True)
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
           FROM dsc WHERE active='1' AND typeId='{FSN_TYPE}'),
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
ai = json.load(open("cache/pbs/amt-items.json")); it = json.load(open("cache/pbs/items.json"))
(OUT / "_pbs_amt.json").write_text(json.dumps(ai["rows"])); (OUT / "_pbs_item.json").write_text(json.dumps(it["rows"]))
con.execute("CREATE TABLE pbs_amt AS SELECT * FROM read_json_auto('out/_pbs_amt.json')")
con.execute("CREATE TABLE pbs_item AS SELECT * FROM read_json_auto('out/_pbs_item.json', maximum_object_size=100000000)")
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
            rx_rows.append({"substance_id": sctid, "rxcui_ingredient": rec["rxcui"], "rxnorm_name": rec.get("name"), "rxnorm_tty": rec.get("tty"), "source": "rxnav-by-name"})
(OUT / "_rx.json").write_text(json.dumps(rx_rows or [{"substance_id": None, "rxcui_ingredient": None, "rxnorm_name": None, "rxnorm_tty": None, "source": None}]))
con.execute("CREATE TABLE rxnorm AS SELECT DISTINCT * FROM read_json_auto('out/_rx.json')")

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
       FROM ingredient i JOIN rxnorm r ON r.substance_id=coalesce(i.active_substance_id, i.precise_substance_id) GROUP BY 1)
SELECT t.id AS tpuu_id, t.pt AS tpuu_pt, t.fsn AS tpuu_fsn,
       bo.brand_id, bc.pt AS brand,
       ug.mpuu_id, mu.pt AS generic_mpuu,
       gmp.generic_mp,
       ing.ingredients, ing.substance_ids, ing.boss,
       df.pt AS dose_form,
       packs.tpp_ids, ctpps.ctpp_ids,
       pbsu.pbs_codes, pbsu.pbs_brands,
       rx.rxcuis, rx.rxnorm_names,
       t.au_authored
FROM product t
LEFT JOIN brand_of bo ON bo.product_id=t.id LEFT JOIN concept bc ON bc.id=bo.brand_id
LEFT JOIN unit_generic ug ON ug.tpuu_id=t.id LEFT JOIN concept mu ON mu.id=ug.mpuu_id
LEFT JOIN ing ON ing.product_id=t.id
LEFT JOIN (SELECT product_id, any_value(dose_form_id) AS dose_form_id FROM dose_form GROUP BY 1) d ON d.product_id=t.id LEFT JOIN concept df ON df.id=d.dose_form_id
LEFT JOIN packs ON packs.tpuu_id=t.id LEFT JOIN ctpps ON ctpps.tpuu_id=t.id
LEFT JOIN pbsu ON pbsu.tpuu_id=t.id LEFT JOIN gmp ON gmp.mpuu_id=ug.mpuu_id
LEFT JOIN rx ON rx.product_id=t.id
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
for t in ["transcode", "brand", "substance", "product", "pbs", "pbs_tpuu", "rxnorm", "unit_generic", "pack_generic", "ctpp_tpp", "mpuu_mp", "ingredient", "contains", "brand_of"]:
    con.execute(f"COPY {t} TO 'out/{t}.parquet' (FORMAT PARQUET)")
for t in ["transcode", "brand", "substance"]:
    con.execute(f"COPY (SELECT * FROM {t}) TO 'out/{t}.csv' (HEADER)")

print("\n=== compendium summary ===")
print(con.sql("""SELECT
  (SELECT count(*) FROM transcode) AS tpuu_rows,
  (SELECT count(*) FROM transcode WHERE brand IS NOT NULL) AS with_brand,
  (SELECT count(*) FROM transcode WHERE generic_mpuu IS NOT NULL) AS with_generic,
  (SELECT count(*) FROM transcode WHERE ingredients IS NOT NULL) AS with_ingredients,
  (SELECT count(*) FROM transcode WHERE pbs_codes IS NOT NULL) AS with_pbs,
  (SELECT count(*) FROM transcode WHERE rxcuis IS NOT NULL) AS with_rxnorm,
  (SELECT count(*) FROM brand) AS brands,
  (SELECT count(*) FROM brand WHERE n_tpuu>0) AS brands_with_products,
  (SELECT count(*) FROM brand WHERE pbs_codes IS NOT NULL AND len(pbs_codes)>0) AS brands_on_pbs,
  (SELECT count(*) FROM substance) AS substances_used,
  (SELECT count(*) FROM substance WHERE rxcuis IS NOT NULL) AS substances_with_rxnorm
""").df().T.to_string(header=False))
print("\nsample transcode rows:")
print(con.sql("SELECT tpuu_pt, brand, generic_mpuu, ingredients, dose_form, pbs_codes, rxnorm_names FROM transcode WHERE pbs_codes IS NOT NULL AND rxcuis IS NOT NULL USING SAMPLE 5").df().to_string(index=False, max_colwidth=45))
con.close()
print(f"\nwritten: {DB} + out/*.parquet + transcode/brand/substance CSV")
