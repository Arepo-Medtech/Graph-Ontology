# Source landscape for the remaining AMH topics

**Assessed 2026-09-22, after 8 guidelines of the AMH march (162 → 122 topics).**

This document exists because the march hit a wall that is not about effort, and the shape of the wall
determines which of the remaining **122 topics can be written at all**.

## The finding

**The open Australian prescribing literature for most of the remaining AMH topics is 10–30 years old.**
The current content lives in ***Therapeutic Guidelines*** and the **AMH** itself — both licensed, both cited
by reference in this compendium and never reproduced.

⚠️ This is a *coverage* problem, not a *licensing* complaint. It means a topic can be genuinely unwritable
from open sources at an acceptable standard, and that saying so is the correct output.

### Evidence: Australian Prescriber article dates for mapped gap topics

The AP sitemap (3,096 article URLs) was intersected with the gap list: **30 of the 122 remaining topics map
to an AP article**. The sitemap's `lastmod` dates all cluster in 2023–24 — **a site migration artefact, not
publication dates** — so the real citation year was read from each article. Of the eight substantive reviews
checked:

| Topic | Article | Actual publication |
|---|---|---|
| Eye infections | *Eye infections* | ⚠️ **Aust Prescr 1994** |
| Eating disorders | *Eating disorders* | ⚠️ **Aust Prescr 1998** |
| Hypothyroidism | *Managing subclinical hypothyroidism* | ⚠️ **Aust Prescr 1999** |
| Scabies | *The treatment of scabies* | ⚠️ **Aust Prescr 2000** |
| Head lice | *Treating head lice* | ⚠️ **Aust Prescr 2001** |
| Opioid dependence | *Drug treatment for opioid dependence* | ⚠️ **Aust Prescr 2001** |
| Acne | *Drug treatment of acne* | **Aust Prescr 2013** |
| Rosacea | *An update on the treatment of rosacea* | **Aust Prescr 2018** |

**Thyroid** was checked separately: *Thyroid function tests* is **2011** and *Modern management of thyroid
replacement therapy* is **2008**.

**Acne** was pursued to a second source — the RACGP *Acne: best practice management* PDF carries a **full
treatment algorithm** and is **"Reprinted from Australian Family Physician Vol 39, No 9, September 2010"**.
**Sixteen years old, and it is an algorithm.** Presenting it as current would be worse than leaving the topic
open.

**Many of the other 22 mapped articles are single-drug "new drug" comments** — opicapone, avanafil,
secukinumab, macitentan, dienogest, telotristat — which are not a basis for a management guideline whatever
their date.

## What this changes

**A guideline written off a 1998 or 2010 source is not a cheap win, it is a liability.** The corpus's value
is that a clinician can act on it. So the march now sorts the remaining 122 into three buckets rather than
working down the list in alphabetical order.

| Bucket | Meaning | Action |
|---|---|---|
| **Writable now** | a current, open, Australian source exists and is machine-readable | write |
| **Writable with effort** | source is open but PDF-only, JS-rendered, or state-based | write, slower |
| ⚠️ **Blocked** | the only current source is licensed (*Therapeutic Guidelines*, AMH) | **record as blocked; do not write from a stale open source** |

### Sources confirmed productive so far

| Source | Yield | Notes |
|---|---|---|
| **ACSQHC Clinical Care Standards** | 20 guidelines | exhausted — all published standards held |
| **ASHM STI guidelines** | 15 guidelines | exhausted |
| **RCH clinical practice guidelines** | 5 guidelines this march, ~10 total | **499 topics in the A–Z**; paediatric only; dates range **2019–2025** |
| **RACGP AJGP** | 1 guideline | open, current, continuously published, **no sitemap** — needs per-issue crawling or search |
| **Australian Prescriber** | 2 guidelines | open, **but the back catalogue is stale for these topics**; good where recent |

### Sources found unusable

| Source | Why |
|---|---|
| **Australasian Menopause Society** information sheets | JS-loaded index, **partly paid** |
| **Jean Hailes** | **fully JS-rendered** — server-rendered text arrives, **no hrefs**, so sub-pages cannot be discovered |
| **Otitis Media Guidelines** (national) | clinical algorithms delivered by **app and PDF only** |
| **Austroads** *Assessing Fitness to Drive* | **403 to direct fetch** |
| **Continence Health Australia** | consumer hub pages, no clinical detail |

## Next targets, in order

1. ⚠️ **Australian Immunisation Handbook** (health.gov.au) — open, continuously updated, authoritative.
   Closes **Immunisation** and **Vaccination**, and is the single highest-value remaining source.
2. **RCH A–Z remainder** — 499 topics indexed; intersect properly against the gap list rather than probing
   slugs one at a time.
3. **RACGP AJGP by issue** — crawl 2022–2026 issue indexes once, then match titles to the gap list. This is
   the only way to use a current masthead that publishes no sitemap.
4. **RANZCOG**, **NEDC**, **Australian Immunisation Handbook**, **state health clinical guidelines** for the
   topics those bodies own.
5. **Record as blocked** any topic whose only current source is licensed, with the licensed source named so
   a reader knows where to look.

**The honest end state for some of the 122 is a one-line entry saying which licensed source holds the
current answer.** That is more useful than a guideline built on a twenty-year-old article.
