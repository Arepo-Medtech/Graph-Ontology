# Merged branches — keep, do not delete

**Policy: these branches are retained.** They are fully merged into `master` and hold no unique commits,
but they are **not** to be deleted. This file is the single list of them.

**Last verified:** 2026-09-23 · `master` at `e878c81`

| branch | tip | commits | PR | merged | merge commit | in `master`? |
|---|---|---|---|---|---|---|
| **`conditions-snomed-binding`** | `d083591` | 9 | [#1](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/1) | 2026-09-21 | `4c610db` | ✅ yes |
| **`conditions-primary-care`** | `ee71e33` | 10 | [#2](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/2) | 2026-09-21 | `2e239bf` | ✅ yes |
| **`monograph-foundry`** | `7b3ed46` | 13 | [#3](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/3) | 2026-09-21 | `9e78d5d` | ✅ yes |
| ⚠️ **`attestation-loop`** | `e4114bc` | 1 | [#4](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/4) | 2026-09-23 | `25d5b24` | ✅ yes | 
| **`binding-review-loop`** | `80380c9` | 4 | [#5](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/5) | 2026-09-23 | `ecc0f6b` | ✅ yes |
| **`condition-guideline-tally`** | `0ec6aa3` | 2 | [#6](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/6) | 2026-09-23 | `56fe582` | ✅ yes |
| **`enrich-candidates-rerun`** | `6786077` | 1 | [#7](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/7) | 2026-09-23 | `ae64446` | ✅ yes |
| **`quarantine-development`** | `d020a71` | 2 | [#8](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/8) | 2026-09-23 | `f299086` | ✅ yes |
| **`restore-lost-bindings`** | `69ff084` | 1 | [#9](https://github.com/Arepo-Medtech/au-medicines-compendium/pull/9) | 2026-09-23 | `e878c81` | ✅ yes |

> ### ⚠️ `attestation-loop` NO LONGER EXISTS — it was deleted on merge
> It was merged with `gh pr merge --delete-branch` on **2026-09-23, before the retention policy was
> given.** The branch ref is gone from `origin` and locally.
>
> **Nothing is lost.** Its single commit `e4114bc` is in `master`'s history and its merge commit is
> `25d5b24`. **To restore the ref:**
>
> ```bash
> git branch attestation-loop e4114bc && git push origin attestation-loop
> ```
>
> Not done automatically — recreating a deleted remote branch is an outward-facing change.

---

## What each branch contributed

### `conditions-snomed-binding` — PR #1, 6 files
Condition families derived from PBS restrictions and bound to SNOMED CT-AU.

`docs/conditions.md` · `reference/body_systems.json` · `scripts/bind_conditions.py` ·
`scripts/bind_ontoserver.mjs` · `scripts/conditions_from_restrictions.py` · `scripts/pbs_pull.py`

### `conditions-primary-care` — PR #2, 2 files
Primary-care coverage derived from PBS items × ATC codes.

`docs/conditions.md` · `scripts/conditions_from_atc.py`

### `monograph-foundry` — PR #3, 17 files
Tickets, ledger, citation gate, splitter and verification — the machinery the guideline corpus is built
on. Also the origin of `reference/attestations.json`.

`.gitignore` · `docs/monograph-foundry.md` · `reference/attestations.json` · `reference/conditions.json` ·
`reference/conditions_split.json` · `reference/entail_verdicts.jsonl` · *(and 11 more)*

### `binding-review-loop` — PR #5, 10 files ✅ *(retained)*
The SNOMED binding review worksheet and harvest, live NCTS validation, the edition-pin bump to
`20260831`, and the binder re-run.

`docs/binder-rerun-20260831.md` · `docs/binding-review-loop.md` · `docs/binding-review-queue.md` ·
`docs/snomed-edition-pin.md` · `reference/binding_validation.json` ·
`reference/edition_diff_20260731_20260831.json` · `reference/snomed_bindings.json` ·
`scripts/bind_ontoserver.mjs` · `scripts/binding_review.py` · `scripts/validate_bindings_ncts.py`

### `condition-guideline-tally` — PR #6, 4 files ✅ *(retained)*
The conditions × guidelines × verification × SNOMED tally, and the join of under-verified guidelines
with SNOMED-bound conditions.

`docs/condition-guideline-tally.md` · `docs/underverified-and-bound.md` ·
`scripts/condition_guideline_tally.py` · `scripts/underverified_bound.py`

### `restore-lost-bindings` — PR #9, 3 files ✅ *(retained)*
Restored the 4 bindings lost to the 20260831 rename. Bound 261 → 265.

`docs/binding-review-queue.md` · `reference/binding_corrections.json` ·
`reference/snomed_bindings.json` · `reference/snomed_candidates_review.json`

### `quarantine-development` — PR #8, 4 files ✅ *(retained)*
Re-searched the 15 quarantined rows and surfaced clean alternatives inline. The rule was not weakened;
the input that tripped it was repaired. 7 stay quarantined, 3 got a clean alternative.

`docs/quarantine-development.md` · `docs/binding-review-queue.md` ·
`reference/quarantine_development.json` · `scripts/develop_quarantined.mjs` · `scripts/binding_review.py`

### `enrich-candidates-rerun` — PR #7, 4 files ✅ *(retained)*
Re-ran the triage enricher after the binder re-run: queue 330 → 349, quarantine restored by rule, and
quarantine promoted to the first tier of the review worksheet.

`docs/binding-review-loop.md` · `docs/binding-review-queue.md` ·
`reference/snomed_candidates_review.json` · `scripts/binding_review.py`

### `attestation-loop` — PR #4, 6 files ⚠️ *(ref deleted, see above)*
Closed the attestation loop: the dose queue became a committed record, and a rejected dose fails the
build.

`docs/attestation-loop.md` · `docs/attestation-queue.md` · `scripts/attestation.py` ·
`scripts/corpus_stats.py` · `scripts/dose_queue.py` · `scripts/verify.py`

---

## Re-verify this list

```bash
git fetch --prune origin
for b in conditions-snomed-binding conditions-primary-care monograph-foundry; do
  printf "%-28s %s  in-master:%s\n" "$b" "$(git rev-parse --short origin/$b)" \
    "$(git merge-base --is-ancestor origin/$b origin/master && echo YES || echo NO)"
done
```

⚠️ **Do not pass `--delete-branch` to `gh pr merge` on this repository.** That flag is what removed
`attestation-loop`.
