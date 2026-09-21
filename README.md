# AU medicines transcode compendium

One local database that joins every level of the Australian Medicines Terminology to brand,
generic, ingredient, PBS listing, clinical-evidence and RxNorm identity. Built offline with DuckDB from four
sources; nothing is fuzzy-matched and every link carries its method.

| Source | What it contributes | Licence / handling |
|---|---|---|
| SNOMED CT-AU RF2 snapshot (NCTS) | AMT concepts at every level, `Has product name` (brand), `is a` (generic), active / precise ingredient, basis of strength, dose form, `Contains clinical drug` (pack → unit), AU preferred terms | Licensed. Read from disk (`AU_RF2_SNAPSHOT`), never committed. Concept activeness comes from a Concept snapshot, else the Concept *Full* file at the release root collapsed to its latest row, else the OWL axiom refset — see [Concept status](#concept-status) |
| PBS Public API v3 | `items`, `amt-items`, `atc-codes`, and `item-atc-relationships`; selected `item-overview` evidence on demand | Commonwealth CC BY; copyright notice and source schedule retained in `cache/pbs/*.json` |
| AMH Medicines, July 2026 | Curated pregnancy-safety and supplement-role distinctions, including route, gestational window and dose context | Subscriber source; only concise paraphrased metadata, edition, access date and direct URLs are committed |
| RxNorm via RxNav (NLM) | Ingredient identity (RxCUI, IN/PIN/MIN) for SNOMED substances: RxNorm's own SNOMED CT id map first, then SNOMED ancestor (salts/hydrates), then name equality — see [RxNorm resolution](#rxnorm-resolution) | US public domain |

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
- **supplement_listing** — PBS items classified in A11 vitamins, A12 mineral supplements, or B03A
  iron preparations. Preserves product wording, formulation, route, ATC priority, linked AMT
  identifiers, source schedule and direct item URL. This is PBS subsidy coverage, not a complete
  registry of supplements sold in Australia; see [PBS supplement listings](docs/supplements.md).
- **clinical_evidence** — selected AMH-derived evidence records with subject type, route, pregnancy
  window, dose context, evidence category, recommendation, paraphrased summary and source provenance.
  **pregnancy_safety_evidence**, **supplement_role_evidence**, and **therapeutic_role_evidence** are domain-specific subsets; see
  [AMH clinical evidence](docs/clinical-evidence.md).
- **product**, **pbs**, **pbs_tpuu**, **rxnorm**, **ingredient**, **contains**, **brand_of**,
  **unit_generic**, **pack_generic**, **ctpp_tpp**, **mpuu_mp**, **pbs_atc_code**, and
  **pbs_item_atc** — the normalised building blocks.

## Concept status

Inactive SNOMED concepts keep active descriptions, so an active FSN does **not** mean an active
concept. The AU bundle as distributed here ships no `sct2_Concept_Snapshot` file, and until the
build checked concept status 557 inactive products (247 TPUU, 235 MP, 75 MPUU) were in `product`
and 247 inactive TPUUs in `transcode` — e.g. `21433011000036107 paracetamol (medicinal product)`,
inactivated 2024-09-30. `build_compendium.py` now resolves status in this order and prints which
source it used:

1. `Terminology/sct2_Concept_Snapshot*.txt` in `AU_RF2_SNAPSHOT`;
2. `sct2_Concept_Full*.txt` at the release root (or `Full/Terminology/`), latest row per concept;
3. the OWL expression refset — every active concept carries an active axiom (root excepted).

## Build

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export AU_RF2_SNAPSHOT="/path/to/SnomedCT_Release_AU1000036_20260731/Snapshot"
.venv/bin/python scripts/pbs_pull.py        # public tier: 1 request / 20 s
.venv/bin/python scripts/rxnorm_enrich.py   # optional, ~1–2 h; first pass, by name via RxNav
.venv/bin/python scripts/rxnorm_resolve.py  # optional, ~20 min; second pass, id map + ancestor + verified names
.venv/bin/python scripts/build_compendium.py
```

To refresh only selected schedule tables, pass their names explicitly. For records that need
restrictions, prescribing text, classification ancestry, or fuller formulation evidence, cache the
assembled item response on demand:

```bash
.venv/bin/python scripts/pbs_pull.py --tables atc-codes item-atc-relationships
.venv/bin/python scripts/pbs_item_detail.py 10579T 11726E 4321K 13486T
```

`cache/rxcui_to_sctid.json` seeds RxNorm links from the Synthea AU bridge built in
`Arepo-Medtech/data-golf-2026`; `rxnorm_enrich.py` extends them to every AMT ingredient and
`rxnorm_resolve.py` re-grades every link with auditable methods.

## RxNorm resolution

Every substance AMT uses as an active or precise ingredient gets one record in
`cache/rxnorm_substances.json` with a `method`, surfaced as `rxnorm.source`:

| method | meaning |
|---|---|
| `rxnav-snomedct-id` | RxNav id map (`idtype=SNOMEDCT`), i.e. RxNorm's own SNOMED CT US atoms. Authoritative; it corrected by-name errors such as *Morphine sulfate* → morphine hydrochloride. International concept ids only |
| `snomed-ancestor` | AU-authored salts/hydrates: nearest `is a` ancestor (≤ 3 hops) resolved by the id map whose preferred term is a prefix of the child's. `via_sctid`, `via_name`, `hops` are recorded |
| `rxnav-by-name-verified` | first-pass by-name hit whose RxNorm name or RxNorm synonym equals a SNOMED description after British→American normalisation |
| `rxnav-approximate-verified` | RxNav `approximateTerm` candidate passing the same equality test |
| `rxnav-name-preparation` | RxNorm `<name> preparation` / `<name> extract` forms for botanicals; lowest accepted tier |
| `rxnav-base-of-salt` | salt/ester/hydrate with no RxNorm entry of its own, linked to the base `IN` when every remaining token is a salt/hydrate word (e.g. *Mosapride citrate* → mosapride). Precision loss is deliberate and visible in the method |
| `rxnav-by-name-unverified` | first-pass hit that failed verification; **excluded** from the `rxnorm` table, listed in `out/rxnorm_review.tsv` |
| `not-applicable:<bucket>` | substance groupers and pharmacological classes (`… and/or … derivative`, `… inhibitor`, used as ingredients by international MP concepts), vaccine antigens/strains, allergen extracts, excipients, medical foods, cell/gene therapy: no RxNorm ingredient is expected |
| `unresolved` | nothing found; the top RxNav candidates are kept in `candidates` for review |

`out/rxnorm_resolution_report.md` lists counts per method and every legacy link that a stronger
method changed.

## Query examples

```sql
-- every brand of atorvastatin with its PBS codes
SELECT brand, tpuu_pt, pbs_codes FROM transcode WHERE ingredients ILIKE '%atorvastatin%';

-- transcode a PBS brand string
SELECT a.pbs_brand, a.amt_brand, a.method, t.generic_mpuu, t.ingredients
FROM brand_alias a JOIN transcode t USING (brand_id) WHERE a.pbs_brand = 'Lipitor';

-- from a US RxNorm ingredient to Australian brands
SELECT DISTINCT brand FROM transcode WHERE list_contains(rxcuis, '83367');   -- atorvastatin

-- PBS-listed vitamins, minerals and iron products, with source links
SELECT supplement_family, pbs_code, brand_name, li_form, atc_code, source_url
FROM supplement_listing
ORDER BY supplement_family, brand_name;

-- pregnancy rules that depend on timing, route or dose
SELECT subject, route_scope, pregnancy_window, dose_context, evidence_category, recommendation
FROM pregnancy_safety_evidence
ORDER BY subject;

-- supplement-role positives, exclusions and context-dependent cases
SELECT subject, evidence_category, dose_context, source_url
FROM supplement_role_evidence
ORDER BY evidence_category, subject;

-- condition-to-treatment relationships and nearby therapeutic-class boundaries
SELECT subject, evidence_category, dose_context, recommendation, source_url
FROM therapeutic_role_evidence
ORDER BY subject;
```

## Provenance rules
1. No identifier is typed from memory: brand, generic and ingredient links are read from RF2
   relationships; PBS links come from PBS's own `amt-items`; RxNorm links come from RxNav.
2. No fuzzy matching. Name-based links are exact, punctuation-normalised or prefix, and the
   method is recorded on the row.
3. Licensed RF2 terminology and AMH monograph text never enter git. The committed AMH reference
   records contain concise paraphrases and source links; `out/` and `cache/` are regenerated locally.
4. PBS therapeutic classification, PBS restriction text, ingredient identity and inferred patient
   purpose remain separate facts. Missing PBS coverage is recorded as unknown, not as a negative.
