# A topic was marked covered and had never been written

**2026-09-22, found while starting the neurology batch.**

## What happened

`reference/amh-topic-coverage.json` mapped AMH's **Epilepsy** topic — and its aliases
*Seizures* and *Convulsions* — to two guidelines in this set:

| AMH topic | Was mapped to | What that guideline actually is |
|---|---|---|
| **Epilepsy** | `fitness-to-drive-seizures-and-epilepsy` | ⚠️ **the Austroads LICENSING standard** — when a person may drive after a seizure |
| **Seizures** | `fitness-to-drive-seizures-and-epilepsy` | as above |
| **Convulsions** | `seizures-acute-management-children` | ⚠️ **the RCH ACUTE PAEDIATRIC protocol** |

⚠️ **Neither covers AMH's Epilepsy page**, which is about **when to start an antiseizure drug, which drug
for which seizure type, what to do when treatment fails, when to withdraw, and epilepsy in females.**
**None of that had been written.** The topic had been sitting on the covered list, counted as done.

This is the same class of error as the stale *Otitis externa* entry recorded in
[`gap-list-deduplication.md`](gap-list-deduplication.md), but worse: that one was **done and not crossed
off**. This one was **crossed off and not done.**

## Fixed

- **`guidelines/epilepsy.md` written** against AMH's Epilepsy topic and its *Choice of antiseizure drug*
  table, and the coverage entries re-pointed to it.
- The three related guidelines are cross-referenced from it so the boundary is explicit.

## The audit that found it, and what it did NOT conclude

The check was mechanical: **which covered topics map to a guideline whose header does not claim an AMH
topic?** That returned **35 guidelines**. ⚠️ **Most are legitimate** — this compendium deliberately closes a
topic from a *better* Australian source than AMH when one exists (COPD-X for COPD, the Heart Foundation
for atrial fibrillation, the Australian Asthma Handbook for asthma, the 2023 CVD risk guideline for
dyslipidaemia). **A guideline not built from AMH is not a gap.**

**The ones left for human judgement**, because the mapped guideline answers a narrower question than the
AMH page, are:

| AMH topic | Mapped to | Concern |
|---|---|---|
| **Pain**, **Acute pain** | `opioid-analgesic-stewardship-acute-pain` | a **stewardship standard**, not a general analgesia topic |
| **Osteoarthritis** | `osteoarthritis-knee-clinical-care-standard` | **knee-only standard**; `osteoarthritis-knee-and-hip` covers more |
| **Asthma** | `acute-asthma-children` | ⚠️ **points at the paediatric acute file**; the adult `asthma` guideline exists and is the better target — a **mapping** problem, not a coverage gap |
| **COPD** | `copd-clinical-care-standard` | the Standard over `copd`; both exist |

⚠️ **None of these was changed.** **Reopening a topic is a judgement about whether the corpus answers the
clinical question, and that is the attester's call, not the drafter's.** They are listed here so the call
can be made deliberately rather than never.

## What this does not change

**No claim, guideline or verdict elsewhere in the corpus was altered.** The gap count rises by one page
and immediately falls again, because the page was written in the same batch that found the error.
