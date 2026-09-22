# Reaching OMOP for the AMT concepts its 2021 snapshot never had

*Item 15 of the SPINE backlog, 22 September 2026. `scripts/amt_indirect.py`, offline, writes only into
`out/compendium.duckdb`.*

## The gap

OMOP's `AMT` vocabulary is a **2021 snapshot**. Australian medicines have moved on, so a product listed since then
has no OMOP concept of its own, reaches no standard drug, and falls out of every OMOP-facing query:

| level | reaches a standard drug directly | of |
|---|---:|---:|
| TPUU (branded unit) | 19,208 | 24,634 |
| MPUU (generic unit) | 6,464 | 16,137 |

All 5,426 unreached branded units have an ingredient row and a generic unit; 5,086 have a strength. The information
to place them exists — just not in OMOP's copy of AMT.

## Two indirect routes, each a weaker claim than a direct mapping

**Generic.** A branded unit with no concept of its own is placed at its own generic unit's standard concept. The
claim is "this branded product is that clinical drug", which is exactly what the AMT `is a` edge already says; the
brand is simply not represented in the target. 3,480 branded units, 72 packs.

**Strength match.** A unit is matched to an RxNorm clinical drug whose DRUG_STRENGTH ingredient set and strengths
— reduced to base units by the item 13 machinery — are identical. The dose form cannot narrow this: AMT names its
dose form with a SNOMED concept and OMOP's drugs with an RxNorm one, and no relationship in the bundle joins the
two. So the rule is **uniqueness instead**: the fingerprint must identify exactly one generic drug in the whole
vocabulary, and where it does not, the strength alone is not evidence and nothing is written. 2,481 products.

Both are written into `omop_drug_indirect` with the route named, never into `omop_drug`. A query that needs a
direct mapping can still have one.

## Does the method reproduce the mappings we already have?

Both routes were run against the 19,179 and 12,972 products that **already** have a direct mapping, and the answer
compared with it. A method that cannot recover the known answers has no business filling the unknown ones. The test
is ancestry rather than equality, because the generic route proposes a clinical drug where the direct mapping found
a branded one — RxNorm expresses that as `Tradename of` and RxNorm Extension's supplier-specific concepts as
`Marketed form of`, and only `CONCEPT_ANCESTOR` covers both:

| | generic route | strength match |
|---|---:|---:|
| the generic of the concept the direct mapping found | 15,431 | 8,552 |
| the same concept | 2,038 | 3,927 |
| more specific than it | 4 | — |
| **different** | **1,706 (8.9 %)** | **493 (3.8 %)** |

**91.1 % and 96.2 % correct** on the known answers. The first draft of this check scored the generic route at 10 %
and the strength match at 2 %, because it demanded concept equality from a route whose whole purpose is to land on
the generic; and an earlier draft of the strength match itself matched 827,078 wrong candidates because it had no
dose form and no uniqueness rule. Both numbers are in the commit history rather than hidden — the check earned its
keep by catching them.

## What it buys

| | before | after |
|---|---:|---:|
| branded units reaching a standard drug | 19,208 (78.0 %) | **22,760 (92.4 %)** |
| generic units | 6,464 (40.1 %) | **8,854 (54.9 %)** |
| all products | 102,766 | **108,727** |

## Reproduce

```bash
.venv/bin/python scripts/drug_strength.py extract     # the strengths this depends on
.venv/bin/python scripts/amt_indirect.py              # ~20 s
```

```sql
-- every product that only reaches OMOP indirectly, and how
SELECT p.pt, i.route, i.standard_name
FROM omop_drug_indirect i JOIN product p ON p.id = i.product_id
WHERE p.level = 'TPUU' ORDER BY i.route, p.pt;

-- the cases where the method disagreed with a known mapping: worth a reviewer's eye
SELECT p.pt, c.route, c.proposed, c.actual
FROM omop_drug_indirect_check c JOIN product p ON p.id = c.product_id
WHERE c.verdict = 'different';
```
