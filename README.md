# AU medicines transcode compendium

One local database that joins every level of the Australian Medicines Terminology to brand,
generic, ingredient, PBS listing and RxNorm identity. Built offline with DuckDB from three
sources; nothing is fuzzy-matched and every link carries its method.

| Source | What it contributes | Licence / handling |
|---|---|---|
| SNOMED CT-AU RF2 snapshot (NCTS) | AMT concepts at every level, `Has product name` (brand), `is a` (generic), active / precise ingredient, basis of strength, dose form, `Contains clinical drug` (pack → unit), AU preferred terms | Licensed. Read from disk (`AU_RF2_SNAPSHOT`), never committed |
| PBS Public API v3 | `amt-items` (PBS line item ↔ AMT code per level) and `items` (PBS code, brand name, form) | Commonwealth CC BY; copyright notice retained in `cache/pbs/*.json` |
| RxNorm via RxNav (NLM) | Ingredient identity (RxCUI, IN/PIN) for SNOMED substances, by exact or normalised name | US public domain |

## Levels (from FSN semantic tags)

| Level | AMT name | FSN tag in the AU release |
|---|---|---|
| TPUU | trade product unit of use | `(branded clinical drug)` |
| TPP | trade product pack | `(branded clinical drug package)` |
| CTPP | containered trade product pack | `(containerized branded clinical drug package)` |
| MPUU | medicinal product unit of use | `(clinical drug)` |
| MPP | medicinal product pack | `(clinical drug package)` |
| MPF / MP | medicinal product form / medicinal product | `(medicinal product form)` / `(medicinal product)` |
| BRAND | product name | `(product name)` |

Legacy AMT v3 tags (`trade product unit of use` …) are mapped to the same levels; those concepts
lack the v4 attributes and appear in `product` but not in `transcode`.

## Tables (`out/compendium.duckdb`, plus Parquet and CSV)

- **transcode** — one row per TPUU: `tpuu_id, tpuu_pt, brand_id, brand, mpuu_id, generic_mpuu,
  generic_mp[], ingredients, substance_ids[], boss, dose_form, tpp_ids[], ctpp_ids[], pbs_codes[],
  pbs_brands[], rxcuis[], rxnorm_names, au_authored`. PBS codes attach directly (TPUU in
  `amt-items`) or through any pack that contains the unit.
- **brand** — one row per product-name concept: products, generics, ingredient sets, PBS brand
  strings and PBS codes reached through its products.
- **brand_alias** — PBS `brand_name` string → AMT brand concept with `method` ∈
  `amt_code` (through a listed AMT code), `exact_name`, `normalised_name` (punctuation-insensitive,
  e.g. "Abiraterone Sandoz" ↔ "Abiraterone (Sandoz)"), `prefix_name` ("APO-Metformin XR 500" ↔
  "APO-Metformin XR").
- **substance** — every substance used as an ingredient: product and brand counts, RxCUIs, PBS
  ingredient strings.
- **product, pbs, pbs_tpuu, rxnorm, ingredient, contains, brand_of, unit_generic, pack_generic,
  ctpp_tpp, mpuu_mp** — the normalised building blocks.

## Build

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export AU_RF2_SNAPSHOT="/path/to/SnomedCT_Release_AU1000036_20260731/Snapshot"
.venv/bin/python scripts/pbs_pull.py        # ~4 min at the public tier's 1 request / 20 s
.venv/bin/python scripts/rxnorm_enrich.py   # optional, ~1–2 h; resolves all ingredient substances via RxNav
.venv/bin/python scripts/build_compendium.py
```

`cache/rxcui_to_sctid.json` seeds RxNorm links from the Synthea AU bridge built in
`Arepo-Medtech/data-golf-2026`; `rxnorm_enrich.py` extends them to every AMT ingredient.

## Query examples

```sql
-- every brand of atorvastatin with its PBS codes
SELECT brand, tpuu_pt, pbs_codes FROM transcode WHERE ingredients ILIKE '%atorvastatin%';

-- transcode a PBS brand string
SELECT a.pbs_brand, a.amt_brand, a.method, t.generic_mpuu, t.ingredients
FROM brand_alias a JOIN transcode t USING (brand_id) WHERE a.pbs_brand = 'Lipitor';

-- from a US RxNorm ingredient to Australian brands
SELECT DISTINCT brand FROM transcode WHERE list_contains(rxcuis, '83367');   -- atorvastatin
```

## Provenance rules
1. No identifier is typed from memory: brand, generic and ingredient links are read from RF2
   relationships; PBS links come from PBS's own `amt-items`; RxNorm links come from RxNav.
2. No fuzzy matching. Name-based links are exact, punctuation-normalised or prefix, and the
   method is recorded on the row.
3. Licensed terminology text never enters git. Only code is committed; `out/` and `cache/` are
   regenerated locally.
