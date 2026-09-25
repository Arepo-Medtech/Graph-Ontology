# Every SNOMED CT-AU edition, offline

*25 September 2026. Build: `scripts/snomed_editions.py`; ECL: `scripts/snomed_ecl.py`; output: `out/snomed_editions.duckdb`
(git-ignored, 6.3 GB, six editions, about three minutes from the Full files).*

The multigraph holds one edition, the pin. The Data Golf 2026 competition asks questions against **six** — the
January release of each year 2021–2026, whichever governs the encounter's date — and every one of its rules has so far
been resolved by querying the live NCTS/CSIRO terminology server edition by edition and caching the answer. The
answers live in `data-golf-2026/cache/<edition>/`: 2,462 `(ECL, edition) → codes` results. This build reproduces them
from the release on disk, with no server, and can therefore answer the *next* question the same way.

## The cut is not one date

The NCTS distribution ships RF2 **Full** files: every version of every row since 2002, with an `effectiveTime`. A
snapshot at date D is "for each component, its latest row effective on or before D". The obvious reconstruction of
edition 20230131 — every row ≤ 20230131 — is wrong by hundreds of concepts: `<<248982007` (the pregnancy findings)
comes out with 223 codes missing and 80 extra against the server's answer.

An AU edition dated D bundles an *earlier* International release. Its own module rows (AU 32506021000036107, AMT
900062011000036108 and the small AU modules) are those effective ≤ D; its International rows (core 900000000000207008,
model 900000000000012004) are those effective ≤ the International release the AU module *depended on* at D. That
dependency is recorded, per release, in the Module Dependency reference set (`der2_ssRefset_ModuleDependencyFull`),
so it is read, not guessed:

| AU edition | International base | `<<` closures cached | replay |
|---|---|---:|---|
| 20210131 | 20200731 | 15 (12,208 codes) | exact |
| 20220131 | 20210731 | 15 (11,582) | exact |
| 20230131 | 20220731 | 15 (11,609) | exact |
| 20240131 | 20230731 | 15 (12,935) | exact |
| 20250131 | 20240201 | 26 (14,093) | exact |
| 20260131 | 20260101 | 271 (28,337) | exact |

Before the refset was read, the same six dates were found by scanning every International release date and scoring
each against the cached closures: the minimum was zero mismatches at exactly these dates and hundreds at every
neighbour (the 20250131 scan first reported 20240601 because it had not looked earlier than June — a reminder that a
search finds the best of what it searched). The refset then confirmed all six. AU moved from a six-monthly to a
monthly International cadence during 2025: 20250131 still sits on 20240201, 20250630 on 20250601, and from then on
each AU release is one month behind International.

## What is in the database

All tables keyed by `edition` (the AU release date); SCTIDs are BIGINT.

| table | rows per edition (2026) | content |
|---|---:|---|
| `edition` | 1 | International base, what the term filter searches, counts, source, build time |
| `concept` | 546,711 active + 163,550 inactive | inactive concepts kept and flagged: a code in the data may be inactive in its edition |
| `description` | ~1.4 M | active FSNs, synonyms and text definitions of active concepts |
| `term` | 546,711 | one row per active concept: FSN and the preferred term (AU dialect refset, else GB, else US) |
| `relationship` | 2,166,842 | active inferred relationships: is-a and every attribute, with the relationship group |
| `concrete_value` | 497,225 | AMT strengths, pack sizes, counts (RF2 concrete values; none before 2022) |
| `refset_member` | 1,229,261 | active simple-refset members (`^refset` in ECL) |
| `association` | 299,452 | active historical associations: what replaced an inactive concept, and how |
| `closure` | 8,707,039 | the transitive is-a closure over active concepts, ancestor → descendant, self excluded |

## The ECL evaluator, and what the server actually does

`scripts/snomed_ecl.py` evaluates the subset of ECL the cached queries use — closures, `^refset`, AND/OR/MINUS,
attribute refinement with `*`, `<<attr`, groups `{}` and OR, dotted `.attr`, and `{{term = …}}` filters — as DuckDB
set operations on the edition tables. `snomed_editions.py check` replays all 2,462 cached expansions and demands
exact agreement. Four things the server does that a reading of the ECL specification would not predict, each found
by a disagreement and then reproduced on purpose:

1. **A focus concept is returned as given, active or not.** `<<15777000` (Prediabetes, inactive since 2002) returns
   itself; so does `>>`. But a concept the edition has never seen — `1269101009` before it was created, a US-extension
   code — returns nothing. Descendants, ancestors and refinement values are always active concepts only.
2. **An unparenthesised refinement binds to the whole compound.** `<<A OR <<B : *=<<C` is `(<<A OR <<B) : *=<<C`,
   not `<<A OR (<<B : *=<<C)`.
3. **The attribute wildcard excludes is-a.** `X : * = <<C` looks at every attribute but the hierarchy.
4. **The term filter searches text definitions only in the two newest editions.** In editions up to 20240131,
   `<<404684003{{term="bilateral"}}` matches FSNs and synonyms; from 20250131 it also matches text definitions
   — exactly the 299 (2025) and 325 (2026) concepts whose definitions contain the word, while adding definitions
   to the earlier editions would add 220–296 concepts the server did not return. Presumably the newer editions were
   indexed by a newer server release. The rule is recorded per edition in `edition.term_filter_types` and the
   evaluator reads it; a later edition inherits the latest rule until measured.

Word matching is the specification's: each query word, case-insensitively, is a prefix of a word of the description.

## Replay result

**2,462 cached expansions replayed in 175 s: 2,462 exact, 0 mismatches, 0 errors** (25 September 2026, all six
editions, 115 distinct query shapes). The road there, in order: a single-date cut (hundreds off per edition); the
two-cut rule from the module dependency refset (every plain closure exact; 23 disagreements left); focus-concept
existence and the `^` operator precedence (15 left); text definitions per edition (14 left); the compound refinement
binding (0). Each step was one observed disagreement, explained, then reproduced — never a special case for a code.

## Use

```bash
.venv/bin/python scripts/snomed_editions.py extract            # Full files out of the NCTS zip -> cache/rf2-full/ (3.7 GB)
.venv/bin/python scripts/snomed_editions.py build              # the six competition editions (~3 min)
.venv/bin/python scripts/snomed_editions.py check ~/code/data-golf-2026/cache
.venv/bin/python scripts/snomed_editions.py ecl 20230131 '<<248982007 MINUS <<118185001' --names
```

```sql
-- what changed for a concept between editions: its parents in each
SELECT edition, list(destination_id ORDER BY destination_id) FROM relationship
WHERE source_id = 198609003 AND type_id = 116680003 GROUP BY edition ORDER BY edition;

-- the concept an inactive code was replaced by, in the edition where the data used it
SELECT a.refset_id, a.target_component_id, t.pt FROM association a JOIN term t
  ON t.edition = a.edition AND t.concept_id = a.target_component_id
WHERE a.edition = '20240131' AND a.referenced_component_id = 15777000;
```

Licensed RF2 content stays in `cache/` and `out/`, both git-ignored; the scripts and this note are what the repository
carries. Any AU release date in the module-dependency history can be built (`--edition 20250731`); a date that was
never an AU release is refused, because it has no content.
