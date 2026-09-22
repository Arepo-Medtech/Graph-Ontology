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
| Scabies | *The treatment of scabies* | ⚠️ **Aust Prescr 2000** — ✅ **superseded: ASHM *Ectoparasites*, modified 30 June 2026** |
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
| **ASHM STI guidelines** | 16 guidelines | ⚠️ **NOT exhausted — this entry was wrong.** The *Ectoparasites* page closes **Scabies** and **Lice, pubic** and was available all along. ASHM also publishes **syndrome** pages (anogenital lumps and ulcers, cervicitis, epididymo-orchitis, genital dermatology, PID, urethritis, vaginal discharge) and **population** pages that were never checked against the gap list |
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

## ⚠️ Correction, same day

The first version of this document said ASHM was exhausted. **It was not.** The *Ectoparasites* page —
current, modified 30 June 2026, carrying full doses — closes two gap topics and was reachable the entire
time. The error was mine: I treated "the 15 pages I fetched" as "the site", and never re-read the ASHM index
I had already downloaded, which lists **ectoparasites plus a whole syndrome and population section**.

**The lesson for the remaining 122 is the opposite of the finding above**: before concluding a topic is
blocked, re-check the indexes already in hand. The stale-back-catalogue finding stands for Australian
Prescriber, but **"no current open source" must be established, not assumed.**

---

## ⚠️ Update 2026-09-22 — RACGP opened, and it was on this list the whole time

**RACGP's *Australian Journal of General Practice* and its predecessor *Australian Family Physician* are
open access, current, peer-reviewed and Australian.** Three guidelines were built from them in one session:

| Guideline | RACGP source | What it gave |
|---|---|---|
| **tinnitus** | *A review of tinnitus*, **AJGP 2018** | **42 of 50 claims quoted verbatim** — the whole clinical pathway. The AMH topic alone is five paragraphs |
| **vertigo 1.1** | *An approach to vertigo in general practice*, **AFP 2016** | **the Epley manoeuvre step by step** and its **contraindications**, which no other source held gives at all |
| **conjunctivitis and eye infections** | *Conjunctivitis: A review*, **AJGP 2024** | **9 AMH topics closed at once**, with **quotable doses** — ceftriaxone 1 g, azithromycin 1 g, chloramphenicol qid |

### ⚠️ The process failure worth naming

**Step 3 of the plan above already said to do this.** It was written, and then not done — the march went on
mining Australian Prescriber's stale back catalogue and treating AMH-only guidelines as the only option for
gap topics, while a current open masthead sat unqueried. ⚠️ **The ASHM correction above taught "establish,
don't assume"; this is the same error one level up — a source I had already identified as productive and
never opened.**

**RACGP publishes no sitemap**, which is why it was skipped: it does not yield to the crawl-the-sitemap
method that worked for Australian Prescriber. ⚠️ **A targeted search per gap topic finds its articles
immediately.** That is the method to use for the remaining topics.

### What RACGP changes about the remaining gap

⚠️ **Assume nothing is blocked until RACGP has been searched for it.** The clusters most likely to yield:

- **the rest of the eye cluster** — dry eye, the glaucomas, mydriasis/cycloplegia
- **urology** — BPH, prostatitis, erectile dysfunction, urinary incontinence, kidney stones
- **GI** — haemorrhoids, anal fissure, perianal disorders, diarrhoea, peptic ulcer, IBD
- **women's health** — contraception, dysmenorrhoea, endometriosis, PMS, infertility
- **mouth and dental** — dry mouth, gingivitis, oral ulcers, dental abscess
- **skin** — tinea, onychomycosis, cutaneous warts, androgenetic alopecia

### ⚠️ And what it does not change

**RACGP articles are reviews, not drug references.** They carry **some** doses and **not a full regimen
set**: the conjunctivitis review gives ceftriaxone and azithromycin and **no antiviral dose at all**, for
either indication that needs one. ⚠️ **The pattern that works is RACGP for the pathway, quoted; AMH for the
doses, paraphrased and queued for attestation** — and **where the two disagree, say so rather than
choosing.** All three guidelines above found a disagreement worth recording; ⚠️ **the conjunctivitis one is
a disagreement about a dose.**
