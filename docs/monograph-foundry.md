# Monograph foundry

**Status:** ticket production runs; stage-4 verification is a screening pass only

Manufactures one content-addressed ticket per condition: Tier A / Tier B slots,
a bibliography that has passed a citation gate, a licence class, a version tuple
and an expiry. It never writes a disposition or a rendering.

## Pipeline

```
out/conditions.json ──► split_conditions ──► validate_splits ──► run_batch ──► out/tickets/*.json
                              │                    │                 │              │
                       both readings      retrieval drops       foundry +      entail (stage 4,
                       where ambiguous    coined terms          ledger         screening only)
```

| Script | Does | Self-check |
|---|---|---|
| `foundry.py` | builds one ticket: citation gate, spine, licence class, version tuple | `--demo` |
| `ledger.py` | append-only production record; the only state | `--demo` |
| `run_batch.py` | batches (default 42), resumable, pre-flights before spending a batch | `--demo` |
| `split_conditions.py` | splits multi-entity PBS names, parents retained | `--demo` |
| `validate_splits.py` | drops coined split children by retrieval | — (network) |
| `entail.py` | stage-4 topical verification harness | `demo` |
| `guidance_fetch.py` | fetches openly published AU guidance into Tier B markdown | `--demo` |

## What is versioned and what is not

`out/` is build output and gitignored. These four live in `reference/` because
they are work products, not artefacts a rebuild reproduces:

| File | Why versioned |
|---|---|
| `conditions.json` | the 639-condition spine everything else references; diffs are reviewable |
| `snomed_bindings.json` | 349 candidates awaiting human confirmation. A **work queue** that accumulates decisions — regenerating it discards them |
| `conditions_split.json` | 65 kept / 14 rejected split children, adjudicated by PubMed calls |
| `entail_verdicts.jsonl` | 40 verification judgements; the evidence for removing the trimmed tier |

Tickets, the ledger and fetched guidance stay under `out/`: they are rebuilt
from these plus the PBS cache.

## The ledger is the only state

`out/ledger.jsonl` is append-only and never rewritten. Batch membership,
resumption and status all derive from it; a failed condition is retried on the
next batch rather than skipped. It is generated, so it is not committed — it
belongs to whoever ran the batches.

Tickets carry `RETRIEVAL_VERSION`. Bumping it requeues everything once, which is
how a retrieval change reaches already-drafted tickets. An earlier `--redo-zero`
selected the first N in file order every pass and re-ran the same 42 while 151
zeros were never retried; the version stamp is what makes the loop converge.

## Citation gate

Stages 1–3 are deterministic (class 1):

1. **exists** — record retrievable
2. **resolves** — citation **re-derived from bibliographic fields**. The input
   PMID is only ever the query hint that found it; identifiers are the weakest
   field in a fabricated reference
3. **not retracted** — PubMed publication-type sync

Stage 4 is **not** the primer's claim entailment. These tickets carry no claims —
every section is `[NEEDS SYNTHESIS]` — so the only assertion a bibliography entry
makes is "this work is evidence about treating this condition". That is what
`entail.py` checks, stamped `topical_support_not_claim_entailment`.

It runs **one** verifier with no calibrated error rate, stamped
`single_verifier_uncalibrated`, and therefore sits **below** the duopoly bar: two
model families of different lineages, so that agreement means something. It is a
screening pass, not a certification.

## Retrieval tiers, and one that was removed

PubMed queries fall back: `strict` (guideline/SR/MA publication type AND therapy
MeSH) → `loose` (drop the design filter) → `bare`. The tier is recorded per
citation so a loose hit is never read as guideline-grade.

A `trimmed` tier once queried the head of long PBS names. Verification of 40
fallback citations found tier to be decisive: `loose` 3/24 unrelated (12.5%),
**`trimmed` 8/16 (50%)**. "Adjuvant management of breast cancer" trimmed to
"Adjuvant management" and returned endometrial, ovarian, salivary gland,
urothelial, pancreatic and rectal cancer. It fixed retrieval and broke precision,
and was removed — all 36 affected conditions went to zero citations, which is the
correct trade. A condition with no citations is visible to a reviewer; a
plausible wrong citation is not.

## Splitting, adjudicated by retrieval

A PBS indication often names several conditions at once. The combined string
matches nothing, so the ticket draws no citations while each constituent would.

Five rounds of regex guards kept producing coined terms — *Blepharospasm spasm*,
*Nausea stasis*, *Stroke embolism*. Encoding medical vocabulary in a word list
was not going to converge. The splitter now emits **both readings** where the
grammar is ambiguous and PubMed adjudicates: a coined term draws no citations and
is dropped. 79 candidates → 65 kept, 14 dropped, all but one genuine garbage.
Rejections are recorded, not discarded.

Parents are always kept: they are what PBS wrote and what the restriction
attaches to.

## Attestations

`reference/attestations.json` records `clinical_attestation` as a first-class
provenance type: a named clinician asserting an operative rule, with who, when,
role and rationale, graded `attested_practice` and kept distinct from literature.
Any literature disagreement is recorded alongside rather than overwritten.

Matching is **word-boundary**. Substring matching attached a nitrofurantoin renal
attestation to growth delay and dietary management, because `uti` occurs inside
*constit**uti**onal* and *therape**uti**c*.

## Current run

639 conditions, 3,284 admitted citations, 11 rejected by the gate, ~27%
zero-citation. 259 bound to SNOMED CT-AU, 349 candidates awaiting confirmation.
