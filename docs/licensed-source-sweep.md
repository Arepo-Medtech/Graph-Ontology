# Consolidation sweep — the licensed-source set

**Run 2026-09-22**, after the set reached **9 guidelines and 303 claims**. The sweep asked one
question: **can a person actually re-verify these claims?** No `source_text` is stored for a
licensed claim by design, so the **locator is the entire provenance**. If the locator does not
resolve, the claim is unverifiable in practice however well-formed it looks.

**Scope:** 9 guidelines, 303 `licensed_source_not_quoted` claims, of which **68 are doses**.

---

## What was wrong

### 1 · Bundled locators — 87 claims

Eight of the nine guidelines shared **one locator across every monograph claim**:

> *"AMH Medicines, drug monographs levodopa with benserazide/carbidopa, pramipexole, rotigotine,
> rasagiline, entacapone, amantadine, July 2026 release"*

Eight dose claims carried that string. It tells the attester the dose is **in one of six
documents** and gives **a URL for none of them**. The locator was structurally valid — `verify.py`
accepted it, because `verify.py` checks a locator is *present*, not that it *resolves*.

⚠️ **Only `vertigo`, written last, named one monograph per locator.** The pattern had matured; the
eight earlier files had not been brought forward.

### 2 · One locator named no drug at all — 7 claims

`acne` carried *"drug monographs under Dermatological drugs > Drugs for acne"* — **a chapter, not a
document**. That chapter holds **10 monographs**.

### 3 · Ambiguous drug names — the serious one

Five cited names map to **more than one AMH monograph**, and the locator did not say which:

| Name as cited | AMH actually has | Consequence if the wrong one is opened |
|---|---|---|
| ⚠️ **methotrexate** | **Methotrexate (immunomodulator)** and **Methotrexate (oncology)** | ⚠️ **the psoriasis dose is 10–15 mg ONCE A WEEK; the oncology monograph is a different order of magnitude.** This is the one that could kill someone |
| **ciclosporin** | **Ciclosporin** and **Ciclosporin (eye)** | wrong route entirely |
| **ivermectin** | **Ivermectin** (oral anthelmintic) and **Ivermectin (skin)** | oral dose read for a topical indication |
| **metronidazole** | **Metronidazole**, **(skin)**, **(vaginal)** | three routes, three regimens |
| **brimonidine** | **Brimonidine (eye)** and **Brimonidine (skin)** | glaucoma drops read for facial erythema |

**Buprenorphine** and **methadone** — which also have two monographs each — **were** disambiguated,
so the practice existed. It was applied inconsistently.

### 4 · Monographs filed outside the guideline's own chapter — 8 cases

The locator named the drug and let the reader assume it lived near the topic. It often does not:

| Guideline | Drug | AMH files it under |
|---|---|---|
| ⚠️ **opioid-dependence** | **naltrexone** | **Psychotropic drugs → Drugs for ALCOHOL dependence** |
| **psoriasis** | **acitretin** | **Dermatological drugs → Drugs for ACNE → Retinoids (oral)** |
| **psoriasis** | **methotrexate**, **ciclosporin** | **Immunomodulators and anti-inflammatories** |
| **thyroid-disorders** | **propranolol** | **Cardiovascular drugs → Antihypertensives → Beta-blockers** |
| **eating-disorders** | **lisdexamfetamine** | **Psychotropic drugs → Drugs for ADHD → Psychostimulants** |
| **rosacea** | **azelaic acid** | **Dermatological drugs → Drugs for ACNE → Other drugs** |
| **acne**, **rosacea** | **doxycycline, minocycline, erythromycin** | **Anti-infectives → Antibacterials** |

### 5 · Two regimen claims were not in the dose queue

The `dose` flag had been applied to **amounts**. It had not been applied to **course durations**,
though `head-lice` already flagged *"repeat after 7 days"* on exactly that reasoning. Two
`thyroid-disorders` claims were reclassified:

- **antithyroid drugs in Graves' disease are usually given for 12 to 18 months**
- ⚠️ **antithyroid drugs around radioactive iodine — stopped at least 4 days before, restarted no sooner than stated**

⚠️ **This widened the definition of `dose` from 66 claims to 68.** It is a definitional change, not
a discovery, and is recorded here rather than absorbed silently into the count.

---

## What was done

**Every named monograph was resolved against AMH's own 1,234-entry drug index**, live, on the day of
the sweep — **41 monographs, all present**. Then `scripts/resolve_locators.py` re-pointed **87
locators**, each now naming **one monograph, by AMH's exact title, with its full URL**:

> *"AMH Medicines, drug monograph **'Methotrexate (immunomodulator)'** at
> `https://amhonline.amh.net.au/chapters/immunomodulators-anti-inflammatories/other-immunomodulators/methotrexate-immunomodulator`,
> July 2026 release, read under subscription 2026-09-22"*

**The monograph is read off the claim text, never guessed** — the claim names its drug. Combination
names are matched and consumed first, so *"adapalene with benzoyl peroxide"* does not also match
*"adapalene"*. ⚠️ **A claim naming no monograph, or one outside the guideline's own retrieved set,
is left alone and reported.** None were: **87 of 87 resolved, 0 unresolved.**

**`retrieved_from` was rebuilt** from the URLs actually used — `acne` went from **1 URL to 15**.

**`scripts/dose_queue.py`** exports **`out/attestation-queue.md`**: all **68** dose claims,
**grouped by monograph with a live link**, so one monograph is opened once rather than once per
claim. **43 sources, 68 claims.**

---

## What this sweep did **not** do

| | |
|---|---|
| ⚠️ **It did not re-read AMH** | It confirmed **every locator resolves to a real page**. It did **not** confirm the claim matches what that page says. **That is still the attestation, and it is still outstanding for all 303.** |
| ⚠️ **It did not check the paraphrases** | Whether a paraphrase is faithful is exactly what `single_verifier_uncalibrated` records as unchecked |
| **It did not touch claim text, verdicts or `source_text`** | Only locators, `retrieved_from`, and two `dose` flags changed |
| **It did not cover the 3,389 quoted claims** | Those are machine re-checkable and were verified by `verify.py` in the same run: **89/89 pass, 0 fail** |

## The standing hole

> ⚠️ **303 claims, including all 68 doses, remain attested by nobody.** The sweep made them
> **findable**. It did not make them **verified**, and no amount of tooling can — the source is
> behind a subscription and the check is a person's to make.

## Corpus after the sweep

**89 guidelines · 3,811 claims · 3,389 pass · 113 image-transcription · 303 licensed-source
(68 doses) · 0 fail · 89/89 structural.**
