# Conditions × guidelines × verification × SNOMED

**Generated 2026-09-23** by `scripts/condition_guideline_tally.py`. Base: the **639 PBS condition
families** in `reference/conditions.json`.

> ### ⚠️ NAME MATCHING CANNOT SETTLE THIS, AND THE BAND IS WIDE
> | method | conditions matched to a guideline |
> |---|---:|
> | exact normalised name | **59** — floor |
> | **token containment** (*psoriasis* ⊂ *chronic plaque psoriasis*) | **135** — used below |
> | loose content-word overlap | ~202 — ceiling, **mostly noise** (pairs *Multiple myeloma* with *Multiple sclerosis*) |
>
> **The honest answer needs the SNOMED bindings, not string comparison.** That is precisely what the
> 349-candidate review queue is for, and it is unfinished. **Treat 135 as an estimate inside a band of
> 59–202, not a count.**

## Conditions WITH a guideline — 135

Measured on the guideline's own claims: `pass` and `pass_image_transcription` are machine re-checkable;
`licensed_source_not_quoted` is not.

| | conditions |
|---|---:|
| **fully verified** — 100% of claims machine re-checked | **60** |
| **well verified** — ≥50% | **6** |
| weakly verified — <50%, some quoted | 27 |
| ⚠️ **NOT verifiable** — **0%** machine re-checked | **42** |

**Against a ≥50% bar:**

| | conditions |
|---|---:|
| ✅ **SUFFICIENT** | **66** |
| ⚠️ **INSUFFICIENT** | **69** — of which **42 have nothing re-checkable at all** |

⚠️ **More than half the conditions that have a guideline are backed by one that is mostly or wholly
unverifiable from this repository** — because its source is AMH, which cannot be quoted. Those are the
guidelines the 621-dose attestation queue exists to close.

## Conditions WITHOUT a guideline — 504

### With a comparable AMH condition: **0**

⚠️ **This is empty by construction, not by coincidence.** All 227 entries in
`reference/amh-topic-coverage.json` point at a guideline that exists; the AMH gap is **0**. So *"has an
AMH topic but no guideline"* is necessarily an empty set.

**The real reading:** these 504 are conditions **AMH's therapeutic index does not cover** — largely
oncology, biologics and high-cost specialist therapy, which is exactly the skew
`reference/conditions.json` warns about, since PBS restrictions cover **restricted and authority items
only**.

### With a SNOMED concept

| | conditions |
|---|---:|
| **bound** to a concept | **193** |
| candidates only, unconfirmed | **287** |
| no concept at all | 24 |

**480 of 504 have a SNOMED concept or a candidate for one** — so the terminology layer reaches
substantially further than the guideline layer. **287 of them are waiting on the review queue.**

## The shape of it

| | count |
|---|---:|
| PBS conditions | **639** |
| — with a guideline | 135 |
| — — sufficiently verified | **66** |
| — — insufficiently verified | 69 |
| — without a guideline | 504 |
| — — bound to SNOMED | 193 |
| — — candidates awaiting review | 287 |
| — — nothing | 24 |

⚠️ **66 of 639 — about one in ten — is the count of PBS conditions with a guideline whose claims are
mostly machine re-checkable.** Every other figure above is a queue.
