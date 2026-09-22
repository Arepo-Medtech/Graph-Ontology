# Route, and which salt is which base

*Item 16 of the SPINE backlog, 22 September 2026. `scripts/route_and_salt.py`, offline, writes only into
`out/compendium.duckdb`.*

## Route

Nothing in the compendium said whether a product is swallowed, injected or applied, and the spine's OMOP loader
left `drug_exposure.route_concept_id` empty for want of a source. There are two, and neither is a guess from text:

* **SNOMED's own dose-form model.** Every pharmaceutical dose form carries `Has dose form intended site`
  (`736474004`). 46,815 of the 48,326 products with a dose form get a route this way.
* **The PBS schedule's `manner_of_administration`** for a listed item, carried down from a pack to its units:
  15,303 products. Only the unambiguous PBS values are mapped; `APPLICATION` says nothing about where, so it is
  left unmapped rather than guessed at.

55,218 products now carry a route, 23,735 of the 24,634 branded units among them.

| route | products |
|---|---:|
| Oral | 28,273 |
| Parenteral | 12,021 |
| Cutaneous | 2,293 |
| Ocular | 1,136 |
| Pulmonary | 1,098 |
| Oromucosal | 529 |
| Nasal | 380 |
| Rectal | 301 |

Only 11 products have more than one route from the dose-form model. Where both sources speak — 6,900 products —
**they agree on 6,858 (99.4 %)**. The 42 that differ are worth reading rather than resolving: a fentanyl lozenge is
*oromucosal* to SNOMED and *buccal* to the PBS, an ear-drop combination is *cutaneous* to SNOMED and *otic* to the
PBS. Both are defensible; the table keeps both, tagged.

## Salt and base

AMT records a product's **precise ingredient** (the salt: "amlodipine besylate") and its **basis of strength** (the
base: "amlodipine") separately, which is how a strength can be stated against the active moiety. The two are
different concepts, and the relationship between them is not in SNOMED's hierarchy:

> Of the **497** salt-to-base pairs AMT implies across 1,985 products, **2** have the salt as a SNOMED descendant of
> its base.

So an ECL query written as `<<amlodipine` misses every product that names the salt. That is not a modelling error —
a salt is not a *kind of* its base — but it is a trap, and it is the same defect class that cost a Data Golf
submission a slot. `substance_salt_base` writes the 497 pairs out with their product counts so the relationship can
be used as data.

OMOP answers the same question the opposite way. Following each side's `Maps to` into the standard vocabulary:

| | pairs |
|---|---:|
| the salt and the base reach the **same** standard ingredient | 406 |
| they reach different ones | 42 |
| OMOP does not map the salt | 46 |
| the salt is not in OMOP | 2 |
| OMOP does not map the base | 1 |

**OMOP collapses the salt onto the active moiety for 406 of 497 pairs; SNOMED's hierarchy does so for 2.** Neither
is wrong — they answer different questions, and a query has to know which vocabulary it is standing in.

The 42 OMOP keeps apart are mostly cases where the "base" is an element or a class rather than a moiety: ferric
carboxymaltose against *iron*, ferrous fumarate against *iron*, sodium fluoride against *fluoride*, magnesium oxide
against *magnesium*, calcium pantothenate against *pantothenic acid*. OMOP treats the compound as its own
ingredient, which for an iron infusion is the clinically useful answer.

### Policy

1. To find **every product containing a moiety**, use `substance_salt_base` to expand the base to its salts, or use
   the OMOP ingredient. Do not rely on `<<base` in SNOMED.
2. To state a **strength**, use the basis of strength, as AMT does — the numbers in `strength` are against the base.
3. When the base is an element or a class (iron, fluoride, magnesium), expect OMOP and AMT to differ, and say which
   one the answer is in.

## Reproduce

```bash
.venv/bin/python scripts/route_and_salt.py     # ~8 s
```

```sql
-- every oral product of a moiety, salts included
SELECT DISTINCT p.pt
FROM ingredient i JOIN product p ON p.id = i.product_id
JOIN product_route r ON r.product_id = p.id AND r.route_id = '738956005'
WHERE i.boss_substance_id = (SELECT substance_id FROM substance WHERE substance = 'Amlodipine')
ORDER BY p.pt;

-- the salts a base-only query would miss
SELECT salt, base, products FROM substance_salt_base WHERE NOT snomed_child_of_base ORDER BY products DESC;
```
