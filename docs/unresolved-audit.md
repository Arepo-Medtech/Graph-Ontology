# What the compendium does not know

**Generated 2026-09-22 · 58 guidelines · 2,285 claims · 236 `Unresolved` rows**

*Revised the same day: paediatric sepsis algorithm recovered from its images — see Finding 1.*

Every guideline ends with an `Unresolved` table. This is the audit of those tables read as a set — the
things this compendium records that it cannot answer, grouped so they can be acted on rather than
encountered one file at a time.

## The taxonomy, counted

| Kind | Count | What it means |
|---|---|---|
| **`input_unavailable`** | **127** | the source refers to something that was not retrieved. **The single largest category by far** |
| **`evidence_unsettled`** | **47** | the literature or the authorities disagree, and the source says so |
| **`observation`** | **21** | something true about the document rather than the medicine |
| **`out_of_scope`** | **19** | the source explicitly excludes it, and nothing here covers it |
| **`time_sensitive`** | **15** | the source's currency is in doubt or it has expired |
| **`access`** | **7** | licensed or subscription content, cited by reference and not reproduced |
| | **236** | |

**`input_unavailable` outnumbers everything else combined.** That is the honest shape of this work: the
commonest reason a question is open is not that medicine is uncertain, but that **the document points
somewhere the retrieval did not follow**.

## ⚠️ Finding 1 — clinical algorithms locked in images

**Thirteen decision algorithms across six guidelines exist only as pictures.** Text was retrieved; the
algorithm was not.

| Guideline | Images | What is inside them |
|---|---|---|
| **Acute asthma (children)** | **4** | salbutamol puff counts and intervals, ipratropium regimens, **steroid agent and dose**, oxygen targets, IV sequence |
| **Anaphylaxis (children)** | **2** | the **interval between IM adrenaline doses**, injection site, fluid and oxygen steps |
| **Febrile child** | **2** | the entire triage for **29 days–3 months** and **>3 months** |
| ~~**Sepsis (children)**~~ | ~~2~~ | ✅ **RESOLVED 2026-09-22** — images downloaded and read; algorithm transcribed into the guideline under verdict `pass_image_transcription` |
| **Seizures — acute management (children)** | **1** | the **sequence of agents and intervals between doses** |
| **Fitness to drive — seizures** | **2** | Figures 13 and 14, the decision trees summarising the whole chapter |

**Five of the six RCH paediatric guidelines in this compendium have their treatment algorithm in an image.**
The exception is **febrile seizure**, which has no algorithm to lose.

**Consequence, stated in each file:** those guidelines carry doses where the source gives them in text
(paediatric seizures, anaphylaxis, magnesium in asthma) but **cannot be used to sequence therapy**. Each says
so in its own body, not only in its table.

**This is not a defect in the sources.** A flowchart is a good way to present an emergency algorithm to a
clinician. It is a structural limit on *this* pipeline — and the most actionable item in this audit, because
it is fixable by retrieval rather than by judgement.

### ✅ Method established, 2026-09-22

**The paediatric sepsis flowcharts have now been downloaded and read**, and the algorithm is transcribed into
that guideline. **Eleven images across five guidelines remain.**

What it recovered, none of which existed in the retrieved text: the **time-banded structure (5 / 15 / 30 /
60 minutes)**; **fluid as 20 then 10 then 10 mL/kg to a 40 mL/kg ceiling**; **four antibiotic regimens in the
first two months of life**; the **adrenaline infusion recipe**; and — most consequentially —
**"There is a high risk of cardiac arrest associated with use of induction agents in children with septic
shock."**

⚠️ **It also carries a new and lesser verification basis.** Those claims take the verdict
**`pass_image_transcription`**: checked against the source, **but the source is a diagram**. They cannot be
re-checked by `scripts/verify.py`, and they are exposed to transcription error — misread digits especially —
in a way text quotes are not. **`verify.py` reports them separately and tells the reader to verify doses
against the image by eye.** They count toward `total` and **not** toward `pass`.

**Two cross-guideline hazards surfaced only once the diagram was legible:**

- **The adrenaline infusion is 6 mg in 1 L in paediatric sepsis and 1 mg in 1 L in paediatric anaphylaxis** —
  a **sixfold** concentration difference between two guidelines from the same hospital, **neither of which
  mentions the other**
- **Lumbar puncture waits for stabilisation in sepsis** but is done **without delay and ideally before
  antibiotics** in **febrile child**. Both are right for their patient; **the compendium is where they can be
  read side by side**

## ⚠️ Finding 2 — documents whose stated currency is wrong or expired

| Guideline | What the source says about itself |
|---|---|
| **Dementia** | **NHMRC approval expired 1 February 2021** |
| **Acute coronary syndromes** | **"has not been updated against the 2025 guidelines"**; replacement due **late 2027** |
| **Sepsis (children)** | **last updated March 2020**, newest reference **2018** — the oldest source here |
| **Febrile child** | reads **"Last update September 2022"** while **both its flowcharts are filenamed `Feb2025`** |
| **Osteoarthritis (knee and hip)** | **"currently being updated"** |
| **COPD** | surveillance **paused** |
| **Smoking cessation** | its 2021 vaping regulation was **superseded 1 October 2024** |
| **Venous thromboembolism prevention** | **under review** |

**Against which**: the **Stroke Clinical Care Standard** (11 June 2026), **sodium valproate** (2 June 2026)
and **febrile seizure** (February 2026) are months old. **The compendium holds both states from the same
issuers**, which is only visible across the set.

## ⚠️ Finding 3 — the first sixteen guidelines predate the taxonomy

**Sixteen guidelines carry no taxonomy-tagged `Unresolved` rows**: asthma, cardiovascular disease risk,
chlamydia and gonorrhoea, chronic kidney disease, COPD, generalised anxiety disorder, gout, heart failure,
insomnia, major depressive disorder, migraine, osteoporosis, stroke and TIA, syphilis, type 2 diabetes, UTI.

These are the earliest files. **Five of them also carry the pre-taxonomy verdict vocabulary** —
`not_quoted`, `not_asserted`, `searched_not_found`, `attested_not_sourced` — which is the **six-claim gap**
between 2,257 total and 2,251 pass. `scripts/verify.py` accepts that vocabulary and reports it as a note.

**They are not wrong; they are older.** But their gaps are not counted in the 236 above, so **the true number
of open items is higher than this audit states**, and a re-pass over the first sixteen would be the way to
find out by how much.

## ⚠️ Finding 4 — population listed as a risk factor without a basis

**Two RCH paediatric guidelines list Aboriginal and Torres Strait Islander (and, in one, Pacific Islander or
Māori) origin as a high-risk group** — in **febrile child**, alongside central lines and congenital heart
disease; in **sepsis (children)**, alongside neonates and immunocompromised children. **Neither states a
basis, a magnitude, or any accompanying guidance on culturally safe application.**

**The ACSQHC standards in this same compendium do the opposite**: stroke, stillbirth, hip fracture, delirium
and others carry explicit per-statement cultural safety recommendations, developed in consultation and
labelled as such.

**Across two guidelines this is a pattern rather than a lapse**, and it is recorded in both files. It is
flagged here because it is the kind of thing that should be seen as a set before attestation.

## What is genuinely unknowable

Not every open item is a retrieval failure. **47 `evidence_unsettled` rows** record real disagreement, and
the sharpest are worth naming:

- **Sodium valproate and paternal exposure** — one 2023 cohort positive; **the TGA and the Epilepsy Society
  of Australia both call it unsubstantiated**; later studies did not reproduce it; **the EMA signal procedure
  is still running** — and the product-information warning was added anyway
- **Sepsis-3 applied to children** — the paediatric guideline quotes the **adult-derived 2016 definition**
  while also citing the **2005 paediatric consensus**, and does not reconcile them
- **Routine laboratory monitoring on valproate** — the source states there is **not universal agreement**
- **Tecovirimat for mpox** — two RCTs showed no benefit; **stockpiles retained**
- **Partner treatment in bacterial vaginosis** — a single NEJM trial created the recommendation, and **the
  source does not cite it**

## Priority, if this list is to be worked

1. **Retrieve the eleven remaining algorithm images** and transcribe them — the method is established and the
   sepsis one is done. Largest clinical gap, and purely mechanical. **Each transcription adds
   `pass_image_transcription` claims that a person should check against the image.**
2. **Retrieve the state and territory sepsis pathways** the paediatric sepsis guideline says **must be
   followed** — in those jurisdictions this compendium's sepsis file is not the operative document.
3. **Re-pass the first sixteen guidelines** against the current contract and taxonomy.
4. **Decide the house position on Finding 4** before attestation.
5. **Re-verify the 51 guidelines whose retrieved sources are no longer on disk** — `scripts/verify.py`
   currently machine-checks only the seven written since it existed.

## Method

Counts are read directly from the `Unresolved` tables of `guidelines/*.md` by regex over the taxonomy
markers, and from `guidelines/*.verification.json` summaries. **They count rows, not severity.** A row
recording an unretrieved appendix and a row recording a missing resuscitation algorithm weigh the same here;
Findings 1–4 are the reading that the counts alone do not give.

**`verifier_class: single_verifier_uncalibrated` applies to this document as much as to the guidelines.**
