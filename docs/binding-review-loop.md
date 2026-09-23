# The SNOMED binding review loop

**330 candidates sat at `snomed: null` in a 756 KB JSON with nowhere to record a decision.**
That is the same diagnosis Item 19 made of the 2,063-row RxNorm queue: *"Reading 2,063 rows in file
order is the wrong job, and it is the reason the review never happened."*

## What this does NOT do

> ### ⚠️ NOTHING IS AUTO-BOUND. EVER.
> The review file's own warning is the reason:
>
> *"Signals are LEXICAL triage, not verdicts. The 'plausible' tier is NOT safe: of 16 quarantined
> pregnancy candidates reviewed by hand, **6 carried no flag at all and every one was wrong**."*
>
> Someone already tested whether a lexical signal could stand in for a judgement, and it failed
> uniformly. The top hit for *Acute mania or mixed episodes* is *Progressive cavitating
> leukoencephalopathy* — validated, real, and completely wrong.

This is consistent with `binding_policy_v2`, which is unchanged: **exact or normalised match on display
or designation, within `<<404684003` or `<<71388002`, and the concept must have a parent** — an orphan
means retired, and is rejected. **Ranked hits are candidates, not bindings.**

## The worksheet

`docs/binding-review-queue.md`. Write your decision in the first column:

| you write | means | state written |
|---|---|---|
| *(empty)* | not yet reviewed | — |
| `918591000168102 KL 2026-09-23` | **BIND** this concept | `corrected_pending_attestation` |
| `! KL 2026-09-23 <why>` | ⚠️ **REJECT** — must not bind | `rejected` |
| `? KL 2026-09-23 <note>` | deferred; stays in the queue | — |

⚠️ **Anything unrecognised is treated as DEFERRED, never as a bind.** A decision is matched on condition
**and `sha`** (condition + top-hit code); if the candidate changes, the decision returns to the queue
rather than binding to a hit nobody saw.

## Ordered by what evidence settles, not by string similarity

| tier | rows | the job |
|---|---:|---|
| **A** Reject on hierarchy — no shared concept | 33 | confirm the rejection |
| **B** Reject on hierarchy — parents unrelated | 60 | confirm the rejection |
| **C** Wrong hierarchy — re-search as Procedure | 6 | re-search, do not bind |
| **D** Parent concept suggested instead | 1 | judge parent vs hit |
| **E** Hit is narrower than the condition | 87 | check it is not a sub-type |
| **F** ⚠️ *"Plausible"* — **THIS TIER IS NOT SAFE** | 130 | verify against the terminology |

**Tiers A–C were derived from the SNOMED hierarchy** — parents sharing no concept with the condition —
**not** from lexical agreement. **99 rows** are rejections a person confirms rather than judgements a
person makes, which is the cheapest and safest end of the queue.

## Run order

```bash
python3 scripts/binding_review.py             # rewrite the worksheet, preserving decisions
python3 scripts/binding_review.py --harvest   # worksheet -> reference/binding_corrections.json
python3 scripts/apply_corrections.py          # corrections -> reference/snomed_bindings.json
python3 scripts/binding_review.py --demo      # self-check
```

**The harvest writes into the existing `binding_corrections.json` and stops.** `apply_corrections.py` —
which already existed, and which exists so that *"improving the binder never discards a review"* — does
the application. Nothing here bypasses it, and pre-existing corrections are merged, not overwritten.

## Tested end to end, then reverted

| | |
|---|---|
| bind a row | correction written, `apply_corrections.py` set `snomed.concept_id` and dropped the stale candidates |
| reject a row | `method: rejected_by_human`, `snomed: null` |
| pre-existing PrEP correction | **survived the harvest** — 3 corrections total, 2 new |
| change a candidate's top hit | decision returned to the queue, **"1 returned"** |
| unrecognised decision text | treated as deferred, **never** as a bind |

## Live validation

`scripts/validate_bindings_ncts.py` checks each distinct candidate code against the **live NCTS**, pinned
to **SNOMED CT-AU 20260731**, and records whether it resolves and whether the display this repo holds
matches the terminology's.

> ⚠️ **FAIL-SAFE:** `validated: false` means **UNVALIDATED, never invalid.** A code that does not resolve
> is reported and left for a person. **Nothing is rebound or deleted on the strength of a false.**

It validates; it does not decide. Results in `reference/binding_validation.json`.

### Result, 2026-09-23

**301 distinct candidate codes checked · 301 validated · 0 unresolved · 0 display drift · all on
`20260731`.**

⚠️ **`20260731` is one release behind the server's default.** A newer edition, `20260831`, is live. Re-validating all 301 against both changes **one display and retires nothing** — see [`snomed-edition-pin.md`](snomed-edition-pin.md).

> ### ⚠️ READ THAT NARROWLY
> **301/301 does NOT mean the bindings are good.** It means the candidate data is *internally* sound:
> every code is a real, current concept in the pinned release, and every display this repo holds matches
> the terminology's.
>
> **It says nothing about whether any candidate is the RIGHT concept for its condition.**
> `719267003` — *Progressive cavitating leukoencephalopathy* — validated cleanly, and is the top hit for
> ***Acute mania or mixed episodes***. A validated code and a correct binding are different claims, and
> only the first one is machine-checkable.
>
> **All 330 rows still need a person.** The validation removed a failure mode (stale, retired or
> mis-transcribed codes); it removed no rows from the queue.
