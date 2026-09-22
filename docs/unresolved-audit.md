# What the compendium does not know

**Generated 2026-09-22 · 63 guidelines · 2,555 claims · 395 `Unresolved` rows**

> ⚠️ **Corrected 2026-09-22.** The first version of this audit counted **236** rows and asserted that the
> sixteen earliest guidelines *"predate the taxonomy"*. **Both were wrong.** The counting regex required the
> taxonomy term to be **bold**; the earliest guidelines write it plain. **They use the same six-term taxonomy
> as everything else, and always did.** The real count is **380**, and **no guideline in this compendium lacks
> tagged `Unresolved` rows.** Finding 3 has been rewritten accordingly. The error was mine, not the files'.

*Revised the same day: **all thirteen algorithm images have been recovered** and **Finding 1 is closed**.
**93 claims now carry `pass_image_transcription`.***

Every guideline ends with an `Unresolved` table. This is the audit of those tables read as a set — the
things this compendium records that it cannot answer, grouped so they can be acted on rather than
encountered one file at a time.

## The taxonomy, counted

| Kind | Count | What it means |
|---|---|---|
| **`input_unavailable`** | **225** | the source refers to something that was not retrieved. **The single largest category by far** |
| **`evidence_unsettled`** | **64** | the literature or the authorities disagree, and the source says so |
| **`out_of_scope`** | **40** | the source explicitly excludes it, and nothing here covers it |
| **`observation`** | **27** | something true about the document rather than the medicine |
| **`time_sensitive`** | **13** | the source's currency is in doubt or it has expired |
| **`access`** | **11** | licensed or subscription content, cited by reference and not reproduced |
| | **380** | |

**`input_unavailable` outnumbers everything else combined.** That is the honest shape of this work: the
commonest reason a question is open is not that medicine is uncertain, but that **the document points
somewhere the retrieval did not follow**.

## ⚠️ Finding 1 — clinical algorithms locked in images

**Thirteen decision algorithms across six guidelines exist only as pictures.** Text was retrieved; the
algorithm was not.

| Guideline | Images | What is inside them |
|---|---|---|
| ~~**Acute asthma (children)**~~ | ~~4~~ | ✅ **RESOLVED 2026-09-22** — and it surfaced a **contradiction with the guideline's own key point 4** (see below) |
| ~~**Anaphylaxis (children)**~~ | ~~2~~ | ✅ **RESOLVED 2026-09-22** — recovered the **IM site (lateral mid-thigh)**, the **mg/kg rule behind the dose chart**, and the **5-minute repeat interval** |
| ~~**Febrile child**~~ | ~~2~~ | ✅ **RESOLVED 2026-09-22** — and it recovered the **empiric antibiotic agents**, absent from the text |
| ~~**Sepsis (children)**~~ | ~~2~~ | ✅ **RESOLVED 2026-09-22** — images downloaded and read; algorithm transcribed into the guideline under verdict `pass_image_transcription` |
| ~~**Seizures — acute management (children)**~~ | ~~1~~ | ✅ **RESOLVED 2026-09-22** — the five-minute gating, and that reassessment runs from **completion** of the infusion |
| ~~**Fitness to drive — seizures**~~ | ~~2~~ | ✅ **RESOLVED 2026-09-22** — ⚠️ **and these two contained nothing absent from the text.** See below |

**Five of the six RCH paediatric guidelines in this compendium had their treatment algorithm in an image.**
The exception is **febrile seizure**, which has no algorithm to lose. ✅ **All five have now been recovered.**
**Only the two Austroads decision trees remain.**

**Consequence, stated in each file:** those guidelines carry doses where the source gives them in text
(paediatric seizures, anaphylaxis, magnesium in asthma) but **cannot be used to sequence therapy**. Each says
so in its own body, not only in its table.

**This is not a defect in the sources.** A flowchart is a good way to present an emergency algorithm to a
clinician. It is a structural limit on *this* pipeline — and the most actionable item in this audit, because
it is fixable by retrieval rather than by judgement.

### ✅ Method established, 2026-09-22

**The paediatric sepsis flowcharts have now been downloaded and read**, and the algorithm is transcribed into
that guideline. ✅ **Finding 1 is closed. All thirteen images are recovered.**

⚠️ **But they were not all the same kind of thing.** The **eleven RCH paediatric flowcharts** contained
substantial clinical content found nowhere in their guidelines' text — a cardiac-arrest warning, a
contradiction with a guideline's own key point, drug regimens, an adrenaline interval, a line incompatibility,
an LP posture. The **two Austroads figures contained nothing new**: they are summaries of a section already
transcribed in full, exactly as the Standard describes them.

**"The content is in an image" is therefore not a uniform category, and cannot be triaged as one.** Whether a
diagram is load-bearing or decorative can only be established by looking at it — which is an argument for
retrieving every one, not for deprioritising the ones that look like summaries.

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
  mentions the other**. ⚠️ **Now confirmed from both documents' own diagrams, not inferred**
- **Lumbar puncture waits for stabilisation in sepsis** but is done **without delay and ideally before
  antibiotics** in **febrile child**. Both are right for their patient; **the compendium is where they can be
  read side by side**
- ⚠️ **Acute asthma key point 4 says "give steroids early in moderate, severe and life-threatening asthma".
  Its own moderate flowchart says "Avoid steroids" for 1–5 year olds.** The negative **Foster 2018** trial in
  preschool virus-associated wheeze is in the reference list and is the probable reason, but **the guideline
  does not reconcile them — and a reader working from the key points alone would give a steroid the flowchart
  withholds.** This was invisible while the algorithm was a picture
- **IM adrenaline in life-threatening asthma is the identical dose, route, site and interval as in
  anaphylaxis** — 10 microg/kg or 0.01 mL/kg of 1:1000, lateral thigh, every 5 minutes. **A sixth interlock
  between those two guidelines, specified only in the diagrams**
- **Aminophylline is a live second-line IV agent** in two asthma algorithms and **appears nowhere in that
  guideline's text**. It also carries a line-compatibility warning found only in the picture: **aminophylline
  and magnesium are not compatible in one IV line**
- ⚠️ **Lumbar puncture is "unless contraindicated" for infants 29 days–3 months and only "±" over 3
  months** in the febrile child charts. **One character carries the entire difference in meningitis posture
  between the two age bands**, and it existed only in the diagrams
- **Febrile child's empiric antibiotics — ceftriaxone, or cefazolin + gentamicin once meningitis is
  excluded — were in the pictures, not the text.** ⚠️ **The doses are in neither**
- **Paediatric seizure reassessment is timed from *completion* of the second-line infusion, not its start** —
  which, with phenytoin infusing at 1 mg/kg/min, materially changes when the next agent is due

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

## ⚠️ Finding 3 — the earliest guidelines are a different generation, and they have something the later ones lost

**Corrected.** The sixteen earliest guidelines were re-examined on 2026-09-22 against the current contract.
**They are not deficient. They follow an earlier but coherent version of it**, and the differences run both
ways.

**What they do that the later ones do not:**

⚠️ **Eleven carry a PBS layer** — `PBS Public API v3, Schedule 4333` as a cited source alongside the clinical
one: cardiovascular disease risk, COPD, generalised anxiety disorder, gout, heart failure, insomnia, major
depressive disorder, migraine, osteoporosis, type 2 diabetes, UTI. **The other fifty guidelines have no PBS
layer at all.**

**That is a regression, not an improvement.** The compendium's purpose is an Australian layer over clinical
guidance, and the newest files — the paediatric set, the sepsis set, the clinical care standards — carry PBS
information only where their source happened to mention it. **The earliest files went and got it.**

✅ **Partly repaired 2026-09-22.** `scripts/pbs_lookup.py` reads the cached PBS schedule and emits the table.
**Twelve more guidelines now carry a PBS layer — 23/61.** The tool was validated by **reproducing the gout
guideline's hand-built table exactly**, allopurinol through febuxostat, from an earlier session's manual work.

**Two things the lookup found that no source in this compendium states:**

- ⚠️ **Disulfiram is not on the PBS schedule at all.** A true negative, checked against every drug name in
  the cache. **An unsubsidised agent is an access fact**, and the alcohol guideline's sources do not mention
  it.
- **The schedule lists valproate without its salt**, so a literal search for *sodium valproate* returns
  nothing. That was a **false negative in my first pass**, caught before commit; the tool now falls back to
  the salt-free moiety and **prints what it matched** so the substitution is never silent.

⚠️ **PBS is not the right access layer everywhere.** The 38 guidelines still without one are largely
**clinical care standards and paediatric emergency guidelines**, where the agents are hospital-administered
and a community subsidy schedule says little. **That judgement belongs per guideline, not to a script run
over all of them.**

**Four declare the limits of Australian sourcing in their own headers**, in bold, in the first paragraph:
**gout**, **insomnia** and **migraine** each state *"No free Australian guideline exists"*, and
**osteoporosis** states *"Australian coverage is **partial**"*. They then lead on American, European or UK
guidance and attach PBS as the Australian layer. **That is the honest construction available at the time, and
it is declared rather than hidden.**

**What they lacked:** a **"Where this connects in the compendium"** table. ✅ **Retrofitted 2026-09-22 —
to all thirty-three guidelines that were missing one, not only the sixteen.** Every guideline in the
compendium now carries one: **61/61**.

**The retrofit found connections that did not exist when the files were written**, because the corpus has
since grown around them. Among them:

- ⚠️ **Migraine → sodium valproate.** Valproate is used **off label for migraine prevention** with efficacy
  comparable to topiramate or candesartan — and carries the full teratogenicity constraint. The migraine
  guideline predates the valproate one by a day and could not have said so.
- ⚠️ **Osteoporosis → sodium valproate.** **Valproate therapy of more than 10 years is associated with
  decreased bone mineral density.**
- ⚠️ **UTI → febrile child.** **UTI is the most common serious bacterial infection in children without a
  focus**, and the paediatric guideline carries the urine collection protocol with contamination rates that
  the adult one does not.
- ⚠️ **Genital herpes → paediatric sepsis and seizures.** **Neonatal HSV** is named in both, with aciclovir
  in the sepsis algorithms recovered from the flowchart images.
- ⚠️ **Type 2 diabetes → fitness to drive.** *Assessing Fitness to Drive* carries **its own diabetes
  chapter**; so does dementia.
- ⚠️ **Stroke and TIA → Stroke (ACSQHC).** The older Stroke Foundation guideline and the June 2026 standard
  built over it, where the standard **explicitly excludes TIA** — which is what the older file covers.
- ⚠️ **Donovanosis → acute rheumatic fever.** Both are conditions of the **same remote and under-served
  Australian communities**, and both are near-eliminated where access is good.

**Five carry the pre-taxonomy *verdict* vocabulary** — `not_quoted`, `not_asserted`, `searched_not_found`,
`attested_not_sourced` — which is the **six-claim gap** between `total` and `pass`. `scripts/verify.py`
accepts that vocabulary and reports it as a note. **The taxonomy in their `Unresolved` tables is the current
one; only the formatting differs.**

## ⚠️ Finding 4 — population listed as a risk factor without a basis

### ⚠️ Revised 2026-09-22: a fourth document takes the other approach

**Four Australian paediatric sepsis documents are now in this compendium.** **RCH, NSW and Queensland** each
list **Aboriginal and Torres Strait Islander** (Queensland adds **Pacific Islander or Māori**) origin as a risk
factor, **none with a stated basis, magnitude or cultural safety guidance**.

⚠️ **A fifth document joins them: bronchiolitis**, which lists **"Indigenous ethnicity"** — two words, no
basis, no magnitude, no cultural safety guidance — as a risk factor for severe disease. **It is the bluntest
of the five.**

**Western Australia does not name an ethnicity at all.** Its high-risk list reaches the same populations
through **rural and/or remote location · socioeconomic deprivation · delayed access to healthcare ·
cultural and linguistic diversity** — and it carries the practice through to care with **use an interpreter
for families with limited English proficiency**.

**WA is the jurisdiction with the largest remote population and the longest retrieval distances**, so this is
not a softening. It is a different construction of the same risk, and **each item names something a service
can change.**

⚠️ **This makes Finding 4 a choice rather than an omission.** Three documents categorise the patient; one
describes the barrier. **The compendium records both and adjudicates neither** — but a reader setting house
policy should decide deliberately, not inherit whichever document they opened first.

**Two RCH paediatric guidelines list Aboriginal and Torres Strait Islander (and, in one, Pacific Islander or
Māori) origin as a high-risk group** — in **febrile child**, alongside central lines and congenital heart
disease; in **sepsis (children)**, alongside neonates and immunocompromised children. **Neither states a
basis, a magnitude, or any accompanying guidance on culturally safe application.**

**The ACSQHC standards in this same compendium do the opposite**: stroke, stillbirth, hip fracture, delirium
and others carry explicit per-statement cultural safety recommendations, developed in consultation and
labelled as such.

**Across two guidelines this is a pattern rather than a lapse**, and it is recorded in both files. It is
flagged here because it is the kind of thing that should be seen as a set before attestation.

## ⚠️ Finding 5 — provenance was never recorded

**No guideline in this compendium recorded the URL it was built from**, until 2026-09-22.

Every file cites its source properly — *ACSQHC, Stroke Clinical Care Standard*; *Aust Prescr 2026;49(3)*,
with a DOI. **A citation names the work. It does not name the retrieval.** The ACSQHC standards, the ASHM
guidelines and the RCH clinical practice guidelines are all multi-page sites whose content moves; the
febrile child guideline's own **stated update date disagrees with its flowchart filenames**, which is exactly
the situation where knowing *which page, when* matters.

**Consequence**: `verifier_class: single_verifier_uncalibrated` was honest about *who* verified, and silent
about *what against*. `scripts/verify.py --source` can machine-check a guideline **only if someone still has
the retrieved text**, and for 48 of 61 nobody does.

✅ **`retrieved_from` and `retrieved_utc` are now fields** in the verification JSON, populated for the 13
guidelines retrieved this session. **`verify.py` prints a note for every file lacking them.**

⚠️ **This is the one finding in this audit that would have been cheap to prevent and is expensive to
repair.**

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

1. ✅ **Done.** All thirteen algorithm images are transcribed. **93 claims now carry
   `pass_image_transcription` and a person should check each dose against its image.**
2. ⚠️ **One of three done.** **NSW retrieved 2026-09-22** as its own file. It differs from the RCH guideline
   on a **hypoglycaemia threshold (3.0 vs 3.3 mmol/L)**, a **blood culture volume (one figure vs a seven-band
   weight table)**, an **oxygen target**, and a **60-minute time-to-antibiotic checkbox** the guideline does
   not have. ✅ **Queensland retrieved too** (May 2026, its own file). ⚠️ **Two of the three documents' differences
   are three-way and decision-changing — blood culture volume, and IM ceftriaxone dose and trigger.**
   ✅ **All three retrieved.** ⚠️ **Four documents now give four rules on blood culture technique and three
   on IM ceftriaxone.** See the four-way table in `sepsis-children-wa.md`.
3. ✅ **Connections tables done — 61/61.** ⚠️ **PBS layer: 23/61**, up from 11. `scripts/pbs_lookup.py`
   now generates the table from the cached schedule, and **reproduces the hand-built gout table exactly** —
   which is what validates it. **The remaining 38 are mostly clinical care standards and paediatric
   emergency guidelines, where PBS is not the relevant access layer**; that judgement should be made per
   guideline rather than by running the tool over everything.
4. **Decide the house position on Finding 4** before attestation.
5. ⚠️ **Blocked, and the reason is the finding.** **Not one of the 61 guidelines recorded the URL it was
   retrieved from.** The `Sources` tables give citations — author, title, publisher, year, sometimes a PMID
   or DOI — which name **the work**, not **the fetch**. For a multi-page site (the ACSQHC standards, ASHM,
   the RCH guidelines) a citation does not pin which page was read, so **a re-verification would be checking
   against a guess.**

   ✅ **Fixed going forward.** `retrieved_from` is now a field in `*.verification.json`, populated for the
   **13 guidelines retrieved in this session** — including the flowchart image URLs, which are the only
   record of where transcribed doses came from. **`scripts/verify.py` now prints a note for every file
   without it**, so the 48 that lack it are visible rather than assumed fine.

   **Reconstructing the 48 missing URLs is the remaining work**, and it is archaeology: for each, find the
   page whose text matches the recorded `source_text`. **That is the honest cost of not having recorded it at
   the time.**

## Method

Counts are read directly from the `Unresolved` tables of `guidelines/*.md` by regex over the taxonomy
markers, and from `guidelines/*.verification.json` summaries. **They count rows, not severity**, and they are matched **formatting-agnostically** after the first version
of this audit undercounted by requiring bold. A row
recording an unretrieved appendix and a row recording a missing resuscitation algorithm weigh the same here;
Findings 1–4 are the reading that the counts alone do not give.

**`verifier_class: single_verifier_uncalibrated` applies to this document as much as to the guidelines.**
