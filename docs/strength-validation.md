# Strength validation — AMT against OMOP's DRUG_STRENGTH

*Item 13 of the SPINE backlog, 22 September 2026. `scripts/drug_strength.py`, offline, writes only into
`out/compendium.duckdb`.*

## Where AMT keeps its strengths

Not in the relationship file. AMT states a strength as a **concrete value inside the concept's OWL axiom**:

```
ObjectSomeValuesFrom(:609096000 ObjectIntersectionOf(
    ObjectSomeValuesFrom(:732943007 :386895008)      -- basis of strength substance
    ObjectSomeValuesFrom(:732945000 :258684004)      -- numerator unit (mg)
    DataHasValue(:1142135004 "12"^^xsd:decimal)      -- numerator value
    DataHasValue(:1142136003 "1"^^xsd:decimal)))     -- denominator value
```

`sct2_Relationship_Snapshot` carries only concept-to-concept triples, so the compendium's `rel` table — 2.17 M rows
— never had a single strength. `drug_strength.py extract` walks the OWL expression refset, balancing parentheses to
find each role group, and writes **67,425 strengths for 39,939 products** (23,866 of 24,634 TPUUs, 15,808 MPUUs):

| style | data properties | rows |
|---|---|---:|
| total quantity | `999000041000168106` value, `999000051000168108` unit | 38,592 |
| concentration (AU extension) | `999000021000168100` value, `999000031000168102` unit | 18,929 |
| presentation | `1142135004` / `1142136003` over `732945000` / `732947008` | 6,724 |
| concentration (international) | `1142138002` / `1142137007` | 3,180 |

## Why the comparison has to go the long way round

The Athena bundle's DRUG_STRENGTH has 2,966,568 rows and **not one of them is AMT**: RxNorm Extension 2,756,719 and
RxNorm 209,849. So an AMT product can only be checked through the bridge the compendium already holds —
`omop_drug` (AMT product → standard RxNorm / RxNorm Extension concept) — and its ingredient through the substance →
RxCUI → RxNorm Ingredient chain, because DRUG_STRENGTH names ingredients as RxNorm Ingredient concepts, never as
SNOMED substances.

The two sources also **normalise differently**. AMT states a pack total ("remifentanil 1 mg vial") or a
concentration ("6 mg/mL"); OMOP states `amount_value`, or a numerator over a denominator ("30 mg / 5 mL"). Compared
naively, 6 looks different from 30. Both sides are therefore reduced to base units (mass in mg, volume in mL,
activity in units) and compared as a total *and* as a ratio. A unit outside the factor table is reported as not
comparable rather than as a disagreement.

## What it found

44,906 (product, ingredient) pairs over 25,028 products that reach OMOP:

| verdict | pairs |
|---|---:|
| same total | 29,076 |
| same concentration | 3,848 |
| within five per cent | 1,161 |
| differs by a clean power of ten | 475 |
| **different** | **1,415** |
| ingredient absent from OMOP's strength rows | 4,150 |
| ingredient not bridged to an RxNorm ingredient | 3,912 |
| a unit outside the factor table | 869 |

**32,924 pairs agree outright — 91.5 % of the 35,975 that are comparable at all — and 20,882 of the 25,028
products (83.4 %) agree on every one of their ingredients.**

The residue is not noise:

* **Within five per cent** (1,161) is editorial rounding between the two vocabularies: pyridoxine 9.7 mg against
  10.0, menthol 394 mg/mL against 390, methyl aminolevulinate 0.160 against 0.168.
* **A clean power of ten** (475) is a per-litre against per-millilitre or gram against milligram normalisation.
* **Different** (1,415, 3.9 % of comparable pairs) is dominated by multi-ingredient infusions and rehydration
  powders — Olimel, Hartmann's, Movicol, amino-acid bags — where the AMT product and the RxNorm Extension concept it
  maps to are *different pack sizes*, so the strengths legitimately differ. That is a finding about mapping
  precision at the pack level, not about either vocabulary's arithmetic, and it is where a reviewer's time is worth
  spending.

Coverage, honestly stated: 3,912 pairs cannot be checked because the substance has no RxNorm ingredient (the
compendium bridges 4,379 of 6,593 substances), and 4,150 because OMOP's strength rows for that drug do not mention
the ingredient at all — usually an excipient or a salt counter-ion AMT records and RxNorm does not.

## Reproduce

```bash
.venv/bin/python scripts/drug_strength.py extract      # ~1 min over the OWL refset
.venv/bin/python scripts/drug_strength.py validate     # ~5 s over the Athena CSVs
```

Then, for the cases worth a human eye:

```sql
SELECT p.pt, c.our_ingredient_name, c.amt_unit, c.amount_base, c.ratio_base, c.omop_amount_base, c.omop_ratio_base
FROM strength_check c JOIN product p ON p.id = c.product_id
WHERE c.verdict = 'different' ORDER BY p.pt;
```
