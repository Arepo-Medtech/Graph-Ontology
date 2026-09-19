# PBS supplement listings

**Status:** structured, source-backed PBS coverage

**Bulk table:** `supplement_listing`

**Source families:** A11 vitamins, A12 mineral supplements, B03A iron preparations

**Coverage boundary:** PBS-subsidised listings, not the complete Australian market

## What this entry means

The compendium treats “supplement” as an explicit classification with provenance, rather than a
word inferred from a product name. The bulk entry joins PBS item records to the PBS version of the
WHO Anatomical Therapeutic Chemical (ATC) hierarchy:

| Compendium family | PBS ATC prefix | Meaning |
|---|---:|---|
| `vitamin` | A11 | Vitamins |
| `mineral_supplement` | A12 | Mineral supplements |
| `iron_preparation` | B03A | Iron preparations, including combinations represented in that branch |

This deliberately includes iron even though PBS places it under blood and blood-forming organs,
not under A12. A rule that searches only A12 would systematically miss PBS-listed iron products.

Each row preserves the PBS code, line-item identifier, brand and drug wording, formulation,
administration route, listing dates, ATC code and priority, linked AMT codes and terms, and a direct
PBS item URL. The source schedule is retained so records from different monthly schedules cannot be
silently combined.

## Interpretation rules

1. **Classification and purpose are separate facts.** An A12 classification says that PBS places
   the item in the mineral-supplement branch. It does not establish why a particular patient takes
   it or why PBS subsidises it.
2. **Ingredient wording is retained verbatim.** `drug_name`, `li_drug_name`, `li_form`, and
   `schedule_form` can disagree in granularity. Keep all of them and resolve the difference with
   item-level evidence rather than discarding one source field.
3. **Absence remains unknown.** PBS is a subsidy schedule, not a complete registry of supplements
   sold in Australia. A product missing from this table must not be labelled “not a supplement.”
4. **ATC priority is retained.** A PBS item can have more than one ATC relationship. Do not flatten
   those relationships without keeping `atc_priority_pct`.
5. **Restrictions are evidence about subsidised use.** They may help interpret purpose, but they do
   not redefine the product's ingredients or ATC classification.

## Primary-source entries

### Iron with folic acid — Ferro-f, PBS 10579T

| Field | Source-backed value |
|---|---|
| Ingredient/form | Ferrous fumarate 310 mg, equivalent to iron 100 mg, with folic acid 350 micrograms; oral |
| Classification | B03A iron preparations |
| Compendium treatment | `iron_preparation`; do not require A12 membership |
| Primary source | [PBS item 10579T](https://www.pbs.gov.au/medicine/item/10579T) |

### Calcium — Cal-500, PBS 11726E

| Field | Source-backed value |
|---|---|
| Ingredient/form | Calcium carbonate 1.25 g, equivalent to 500 mg elemental calcium |
| Classification | A12 mineral supplements |
| Subsidised-use evidence | PBS restriction text concerns hyperphosphataemia associated with chronic renal failure |
| Compendium treatment | Keep classification and subsidised purpose in different fields/evidence layers |
| Primary source | [PBS item 11726E](https://www.pbs.gov.au/medicine/item/11726E) |

### Magnesium — PBS 4321K

| Field | Source-backed value |
|---|---|
| Ingredient/form | Magnesium 37.4 mg as magnesium aspartate dihydrate; oral |
| Classification | A12 mineral supplements |
| Subsidised-use evidence | Hypomagnesaemia |
| Compendium treatment | `mineral_supplement`, with formulation and purpose retained separately |
| Primary source | [PBS item 4321K](https://www.pbs.gov.au/medicine/item/4321K) |

### Potassium combination — Chlorvescent, PBS 13486T

| Field | Source-backed value |
|---|---|
| Ingredient/form | Potassium chloride 595 mg, potassium bicarbonate 384 mg, and potassium carbonate 152 mg; total potassium 14 mmol |
| Classification | A12 mineral supplements |
| Data-quality lesson | Short drug-name fields can omit a constituent that appears in the official formulation |
| Compendium treatment | Preserve all PBS source fields and flag disagreement for reconciliation; do not choose the shortest string as truth |
| Primary source | [PBS item 13486T](https://www.pbs.gov.au/medicine/item/13486T) |

## Source references

- [PBS Schedule Data API announcement](https://www.pbs.gov.au/news/2024/12/new-pbs-schedule-data-api-and-api-csv-files)
- [PBS API v3 data dictionary](https://data.pbs.gov.au/download/api/files/2025-PBS-API-V3-Data-Dictionary-v3.3.11.pdf)
- [PBS A11 vitamins hierarchy](https://www.pbs.gov.au/browse/body-system?codes=a11&depth=2)
- [PBS A12 mineral supplements hierarchy](https://www.pbs.gov.au/browse/body-system?codes=a12&depth=2)
- [PBS B03A iron preparations hierarchy](https://www.pbs.gov.au/browse/body-system?codes=b03a&depth=3)

## Reuse in Makoha

Makoha can consume `supplement_family` as a sourced rule input and retain three outcomes:
`classified`, `not classified in the covered PBS families`, and `unknown outside PBS scope`.
Patient intent, clinical indication, and electrolyte exclusions should be separate rule inputs. This
keeps a deterministic rule explainable and prevents a therapeutic listing from becoming an
unsupported claim about patient behaviour.

The companion [AMH clinical evidence](clinical-evidence.md) layer adds route-, dose- and
role-sensitive distinctions for calcium, iron, iodine, magnesium sulfate and thiamine, plus negative
controls that expose over-broad chemical matching. Use those records to decide whether a medicine is
being used as supplementation; do not widen the PBS families solely by ingredient ancestry.

For a small set of records needing richer evidence, cache the assembled PBS item response:

```bash
.venv/bin/python scripts/pbs_item_detail.py 10579T 11726E 4321K 13486T
```

The command stores source responses under `cache/pbs/item-overview/`; cache and generated outputs
remain local because PBS and AMT terms are regenerated under their respective source conditions.
