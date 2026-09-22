# The RxNorm review queue

*Item 19 of the SPINE backlog, 22 September 2026. `scripts/rxnorm_review_queue.py`, offline.*

## What was waiting

`scripts/rxnorm_resolve.py` left `out/rxnorm_review.tsv`: 2,063 substances it could not resolve to an RxNorm
ingredient with confidence. Reading 2,063 rows in file order is the wrong job, and it is the reason the review never
happened. This script does not make the clinical judgement — it says **which rows still need one, and why** — using
evidence the compendium did not have when the file was written.

## What the evidence settles

| verdict | rows | what it means |
|---|---:|---|
| already classified: vaccine antigen or strain | 371 | the resolver had already ruled these out of scope |
| already classified: substance grouper or pharmacological class | 370 | " |
| already classified: allergen extract | 106 | " |
| already classified: medical food or formula | 61 | " |
| already classified: cell, gene or tissue therapy | 10 | " |
| already classified: excipient or vehicle | 2 | " |
| **OMOP resolves it** | **67** | OMOP's own SNOMED-to-RxNorm mapping answers the question the resolver could not |
| **every product using it already reaches OMOP** | **52** | the substance is unresolved but nothing downstream is blocked |
| **a salt whose base resolves and carries the strength** | **31** | item 16's salt-to-base pairs: the products are reachable through the basis of strength |
| choose among candidates | 373 | the resolver found names; a person picks one |
| no candidate found | 620 | nothing to choose between; needs a fresh lookup, not a judgement |

**993 rows still need a person**, and they block **2,104 products** between them. That is the honest number: the
evidence removed 1,070 rows from the queue, not the majority.

## Why the queue is short even so

The blocked products are concentrated. The file is sorted by how many products each row blocks:

| reading down the queue | covers |
|---|---|
| the first **210** rows | half the blocked products |
| the first **573** rows | 80 % |

And the two actions are different work, so the `verdict` column separates them:

* **choose among candidates** (373) is a judgement — *Lactobacillus rhamnosus* against RxNorm's
  *Lacticaseibacillus rhamnosus*, *Recombinant human neutral insulin* against *insulin isophane, human*.
* **no candidate found** (620) is a lookup — *Cilnidipine*, *Bilastine*, *Voglibose*, *Epoetin theta*: real
  medicines the resolver simply missed, several of which are not marketed in the United States and may genuinely
  have no RxNorm ingredient.

The head of the queue:

| products blocked | substance | action |
|---:|---|---|
| 31 | Normal human immunoglobulin | no candidate found |
| 23 | Gadoteric acid | no candidate found |
| 19 | Elasomeran | choose among candidates (SARS-CoV-2 mRNA-1273) |
| 18 | Bicarbonate | no candidate found |
| 18 | Lactobacillus rhamnosus | choose among candidates (Lacticaseibacillus rhamnosus) |
| 17 | Bretovameran | no candidate found |
| 15 | Recombinant human neutral insulin | choose among candidates (insulin isophane, human) |

Each row carries its evidence in the same file: product counts, how many of those products already reach OMOP, what
OMOP says about the substance, whether RxNav and OMOP agreed, the base substance when it is a salt, the legacy value
and up to three candidates.

## Reproduce

```bash
.venv/bin/python scripts/rxnorm_review_queue.py      # ~3 s; writes out/rxnorm_review_queue.tsv
```

```sql
-- or work it in the database
SELECT substance, verdict, products_blocked, candidate_1
FROM read_csv_auto('out/rxnorm_review_queue.tsv', delim='\t')
WHERE verdict IN ('choose among candidates', 'no candidate found')
ORDER BY products_blocked DESC LIMIT 50;
```
