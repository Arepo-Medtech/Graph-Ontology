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
| **OMOP resolves it** | **45** | OMOP's own mapping, one source, reviewed and no problem seen — see the third pass below |
| **every product using it already reaches OMOP** | **52** | the substance is unresolved but nothing downstream is blocked |
| **a salt whose base resolves and carries the strength** | **31** | item 16's salt-to-base pairs: the products are reachable through the basis of strength |
| **resolved by scored route** | **147** | the OMOP code route, Tier 1 on the truth set, hand-checked wherever it renamed — `reference/rxnorm_route_resolutions.json` |
| **decided by review** | **13** | a person chose; recorded in `reference/rxnorm_substance_decisions.json` |
| OMOP's answer flagged: needs a person | 13 | OMOP's answer looks wrong on review — `reference/omop_substance_review.json` |
| route answer rejected: needs a person | 3 | the scored route's answer was refused on hand check |
| choose among candidates | 335 | the resolver found names; a person picks one |
| no candidate found | 504 | nothing to choose between; needs a fresh lookup, not a judgement |

**855 rows still need a person**, blocking **239 real products** (things anyone dispenses; see *What "blocked" was
counting* below). The evidence removed 1,070 rows from the queue, not the majority; the review passes and the scored
route below removed 144 more — and put 16 back that the queue had wrongly been calling resolved.

## Why the queue is short even so

The blocked products are concentrated. The file is sorted by how many products each row blocks:

| reading down the queue | covers |
|---|---|
| the first **19** rows | half the blocked **real** products |
| the first **50** rows | 80 % |

(Ranked by `real_products_blocked`. Before the scored route landed they were 28 and 72; on the old raw count, 216 and 576 — the change is
explained below, and it is the single biggest improvement to this queue's usefulness.)

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

## First review pass: the probiotics (23 September 2026)

Four rows, 37 products blocked. Decisions are recorded in `reference/rxnorm_substance_decisions.json` and read back
by the queue script, so re-running the resolver cannot discard them — the same arrangement
`reference/binding_corrections.json` gives the SNOMED bindings. All four are
`corrected_pending_attestation`: they were decided by evidence, not signed off by a named person.

| AMT substance | products | decision | rxcui |
|---|---:|---|---|
| Lactobacillus rhamnosus | 18 | Lacticaseibacillus rhamnosus | 100278 |
| Bifidobacterium lactis | 14 | Bifidobacterium animalis | 1550045 |
| Lactobacillus delbrueckii | 3 | Lactobacillus Delbrueckii *(resolver's candidate rejected)* | OMOP2721256 |
| Lactobacillus | 2 | Lactobacillus *(genus; unblocks nothing real)* | OMOP5051433 |

**Why these were quick.** Three of the four are the 2020 split of the *Lactobacillus* genus (Zheng et al.) meeting a
terminology that adopted the new names while AMT kept the old ones. That is a rename, not a clinical judgement.
*Lactobacillus rhamnosus* → *Lacticaseibacillus rhamnosus* is the whole of the first decision, and RxNorm carries no
valid species-level concept under the old name to compete with it.

**Two were decided by RxNorm itself, not by inference.** *Bifidobacterium lactis* has a retired RxNorm concept
(1150094, `invalid_reason=U`) carrying `Concept replaced by` → *Bifidobacterium animalis*; the deprecated genus
concept 6204 `Maps to` the RxNorm Extension genus concept. Following the vocabulary's own mappings beats reasoning
about taxonomy, and it is what was done.

**One resolver candidate was wrong and is rejected.** For *Lactobacillus delbrueckii* the resolver offered
`100272 Lactobacillus delbrueckii subsp. bulgaricus` — narrowing a species to one of its subspecies. *L. delbrueckii*
also has subspecies *delbrueckii*, *lactis* and *indicus*, and nothing says which is in the products: all three AMT
terms name the plain species (`Lactobacillus delbrueckii 250 million CFU` in a ten-organism capsule, its medicinal
product parent, and Probiotica (Nutra-Life) capsule), and no AMT substance anywhere mentions *bulgaricus*. The
species-level `OMOP2721256` is the honest target. This is the same failure the item 15 self-check caught twice:
a candidate that looks close is not a candidate that is right.

**A trap worth recording.** Do not resolve genus-level *Lactobacillus* by following OMOP mappings blindly.
`1147374 Lactobacillus sp` is invalid (U) and both `Concept replaced by` and `Maps to` send it to
`1310844 Bacillus coagulans` — a different organism entirely.

**What it is worth.** 37 of 2,104 blocked products, about 1.8 %. The two large rows are real; the genus row unblocks
nothing, because its two "products" are AMT groupers (*Lactobacillus only product*, *Lactobacillus-containing
product*) rather than marketed goods. It is recorded as decided so it stops consuming attention either way.

## Second review pass: the contrast agents (23 September 2026)

Six rows. Only one of them matters, and finding out why exposed a defect in this queue's ranking.

| AMT substance | real products | decision | rxcui |
|---|---:|---|---|
| Gadoteric acid | 23 | gadoterate meglumine | 1421151 |
| Iodised oil | 1 | ethiodized oil | 4125 |
| Gadoxetic acid | 0 | gadoxetate | 802624 |
| Iotroxic acid | 0 | IOTROXIC ACID *(resolver's candidate rejected)* | OMOP5171814 |
| Amidotrizoic acid | 0 | diatrizoic acid *(resolver's candidate rejected)* | 1546223 |
| Iodinated contrast media | 0 | **rejected** — a pharmacological class, not a substance | — |

**The one that pays.** *Gadoteric acid* sits behind 23 real goods: Clariscan and Dotarem 0.5 mmol/mL injection,
which are gadoterate meglumine. Athena holds no `gadoteric acid` and no bare `gadoterate`, so `1421151 gadoterate
meglumine` is the only target at any level. The resolver had offered nothing at all for this row.

**Two more resolver candidates rejected, both the same shape as the probiotic one.** AMT names an acid; the resolver
reached for a salt or an anion when an exact acid concept existed. *Iotroxic acid* was offered `52527 meglumine
iotroxinate` although `OMOP5171814 IOTROXIC ACID` is an exact match. *Amidotrizoic acid* was offered the anion
`3319 diatrizoate` although `1546223 diatrizoic acid` is the same molecule under its USAN name. Choosing the salt
would assert a formulation AMT does not state.

**One row must not be mapped at all.** *Iodinated contrast media* is a pharmacological class. It is recorded with
state `rejected`, which the queue script honours by dropping the row without assigning an ingredient.

## What "blocked" was counting

Working this slice showed that four of the six contrast rows were blocking nothing anyone can dispense. Their
"products" are AMT groupers — *Gadoxetic acid only product*, *Amidotrizoic acid-containing product in parenteral
dose form* — and a further class of them are plain SNOMED groupers (*Beta-lactam-containing product*) that the AMT
`product` table does not carry at all.

Counting those was a defect in this queue, and it was mine. Across the whole review set:

| what the 2,030 "blocked products" actually are | distinct |
|---|---:|
| medicinal product (MP — abstract) | 977 |
| medicinal product form (MPF — abstract) | 259 |
| clinical drug (MPUU — real) | 231 |
| branded clinical drug (TPUU — real) | 84 |
| branded product | 2 |

**84 % of the blocked count was groupers.** The queue therefore ranked substances by how many abstract concepts
mentioned them, which is close to ranking by how general the substance is — the opposite of what a work queue wants.

The fix: `real_products_blocked` counts only products at a dispensable level, and the queue sorts on it with the raw
count kept as a tie-break and still shown in its own column. Both numbers are reported, because the raw count is not
wrong, only differently useful. The effect on the work is large — **half the real blocked products are now covered by
the first 28 rows instead of 216**, and 80 % by 72 instead of 576.

One consequence worth stating: a row whose products are all groupers now sorts to the bottom rather than the top.
Four of the six contrast rows above are exactly that, and are recorded as decided anyway so they stop being read.

## Third pass: the 153 code-route resolutions, and what checking them found (23 September 2026)

The OMOP code route — SNOMED concept → `Maps to` → standard Ingredient — earned **Tier 1** on the truth set
(3,074 / 3,074, Wilson lower bound 0.9988; `scripts/route_scorer.py`). It answers 153 rows of this queue. They were
landed with a hand-checked sample, not blind.

**Why RxNav never found them: 144 of the 153 are RxNorm Extension concepts.** RxNorm Extension is OMOP's vocabulary
for drugs RxNorm never covered, and non-US substances are exactly what fills it. It also means they cannot go into
`rxnorm.rxcui_ingredient`, a column holding only genuine RxCUIs (0 of 4,530 rows are OMOP codes).
`scripts/apply_standard_ingredients.py` writes them to a new table, `substance_standard_ingredient`, where vocabulary
is a column. Run it after every build, as `apply_corrections.py` is run after every bind.

**The check** (stratified; `reference/rxnorm_route_resolutions.json` records which rows were read): every row where
the route disagreed with the resolver's candidate (32, a census); the 8 with most real products blocked; 8 seeded
random; then **every row where the route changed the substance's name** (18, a census) — because both errors the
first three strata found had that signature.

| | checked | wrong |
|---|---:|---:|
| route kept the name | 40 | **0** |
| route changed the name | 18 | **6** |

**The Tier 1 score did not transport to the hard population.** That was the covariate-shift risk stated before the
check; this measures it. For this route a changed name is the risk signal, and such answers are gaps that carry a
frame, not lookups that may collapse. The six:

| substance | route's answer | outcome |
|---|---|---|
| Tetanus antitoxin | tetanus toxoid **vaccine** | rejected — opposite interventions (passive vs active immunisation) |
| Plasminogen activator | urokinase | rejected — a class narrowed to one agent |
| Crotalidae polyvalent immune Fab | Crotalidae immune F(ab')2 | rejected — a different product; CroFab's ingredient is deprecated with no replacement |
| Clopenthixol | zuclopenthixol | overridden → `CLOPENTHIXOL` |
| Glycerophosphoric acid | glyceryl phosphate | overridden → `Glycerophosphoric Acid` (2 real products) |
| Polycarbophil | calcium polycarbophil | overridden → `Polycarbophil` |

Landed: **147** accepted (135 with the name kept — 40 read, 95 resting on code and name agreeing — and 12 renamed
but checked), 3 overrides as review decisions, 3 back with a person. Substances with a standard ingredient:
**4,530 → 4,689**.

**And the queue had been hiding some of it.** All six bad answers were already in `omop_substance` from the OMOP
bridge, marked `omop-only`, and this queue presented three of them — the tetanus toxoid one included — as **"OMOP
resolves it"**. That verdict trusted OMOP's single, unconfirmed answer unconditionally. Every one of the 61 rows
under it was an answer in which OMOP had changed the name, so all 61 were read:

| | rows |
|---|---:|
| no problem seen | 45 |
| flagged, wrong on the face of the names | 7 — including *Hepatitis **B** immunoglobulin → hepatitis **A** virus* and *mixed **low-alpha** tocopherols → **alpha** tocopherol* |
| flagged on reviewer recall (Tier 3) | 6 — e.g. *Chinese privet → **Ligusticum*** (privet is *Ligustrum*), *goji berry → **Berberis** lycium* |
| already rejected above | 3 |

**About a quarter of what this queue called resolved was wrong.** Flagged rows go back to a person with the reason
attached; `reference/omop_substance_review.json` assigns **no** replacement concepts, because recall-based flags are
Tier 3 and may point but not decide. `omop_substance` is left as a faithful record of what OMOP asserts; the queue
simply stops calling a flagged row resolved.

Finding recorded, not acted on: **OMOP carries two standard ingredients for edotreotide** — RxNorm Extension
`EDOTREOTIDE` and RxNorm `2199392`, which RxNorm itself spells *edotreotr**i**de*; probably why they were never linked.
