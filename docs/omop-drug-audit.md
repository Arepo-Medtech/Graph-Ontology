# Auditing OMOP's product mappings, and a cross-wired OMOP release

*23 September 2026. `scripts/omop_drug_audit.py`, `scripts/apply_omop_drug_review.py`, `reference/omop_drug_review.json`.*

## Why this was run

`omop_drug` maps every AMT product to one standard drug through OMOP's own `Maps to`. At substance level the same
mechanism was right 40 of 40 when it kept a substance's name and wrong 6 of 18 when it changed it — tetanus
antitoxin to tetanus toxoid vaccine among them (`docs/rxnorm-review-queue.md`, third pass). This asks whether the
**108,727** product mappings (102,766 in `omop_drug`, 5,961 from item 15's indirect routes) carry the same failure.

## The witness must not be OMOP

The first thing the check showed was that OMOP cannot audit itself. Thirty-six citrus-bioflavonoid products
"matched" OMOP on strength against *flavone* — because OMOP had made the same wrong choice at substance and product
level, so the two agreed. Three witnesses were used instead, each independent of OMOP's product mapping:

| witness | what it compares | why it is independent |
|---|---|---|
| **ingredient** | RxNav's resolution of the product's AMT active substances against the OMOP drug's ingredients (`CONCEPT_ANCESTOR`) | `rxnorm_resolve.py` never consulted OMOP; salts lifted to ingredients through RxNorm's `Form of` |
| **brand** | the `[brand]` in OMOP's target name against the AMT product name | a string OMOP wrote about a different product cannot match by accident |
| **strength** | `strength_check`: AMT's OWL strengths against `DRUG_STRENGTH` | catches the right drug at the wrong strength, which the other two pass |

## What the ingredient witness found

| verdict | mappings |
|---|---:|
| agrees, fully witnessed | 96,640 (88.9%) |
| agrees on the witnessed ingredients | 3,187 |
| standard drug has extra ingredients | 203 |
| no independent witness | 3,033 |
| standard concept has no ingredient | 3,777 |
| **disagrees on a witnessed ingredient** | **1,887** |

A disagreement means one of two witnesses is wrong — not necessarily OMOP. Read by hand, the 1,887 are five
different things, and only one of them is an error:

1. **One ingredient, two concepts** — *cromolyn* / *cromoglycate*, *ispaghula* / *psyllium*, *heparin* / *Heparin
   Sodium*, *racemethionine* / *methionine*, *vitamin E* / *alpha tocopherol*. RxNorm holds both; nothing is wrong
   with the drug. The edotreotide finding at scale.
2. **Element versus salt** — *magnesium* / *magnesium oxide*, *fluoride ion* / *sodium fluoride*. A modelling
   choice.
3. **OMOP broadening** — ferric carboxymaltose (Ferinject), ferric derisomaltose (Monofer) and iron polymaltose all
   become **"iron"**; lonapegsomatropin becomes somatropin. Lossy — the IV irons differ in maximum dose and in
   hypophosphataemia risk — but not wrong. Kept.
4. **OMOP more specific than RxNav** — *doxorubicin* against *Doxorubicin pegylated liposomal* (Caelyx). OMOP
   right, the witness lossy. Kept.
5. **Errors.** Below.

## Error one: a cross-wired OMOP release

Grouping the disagreements by the date each `Maps to` became valid localised them:

| `Maps to` valid from | mappings | disagree | branded with the wrong brand |
|---|---:|---:|---:|
| 2016-09-30 | 37,977 | 0.76% | 0.29% |
| 2017-08-29 | 3,817 | 2.28% | 0.59% |
| 2021-06-30 | 59,883 | 2.26% | 0.60% |
| 2026-01-14 | 559 | 8.05% | 10.07% |
| **2026-02-03** | **91** | **37.36%** | **41.67%** |

The 2026-01-14 batch looked bad and is not: its ingredient disagreements are all multivitamins and amino-acid
infusions mapped to the right kind of product, and its brand "mismatches" are European spellings of the same brands
(*Sandimmun* → *[Sandimmune]*, *Voltaren* → *[Voltarene]*), every one with verified ingredients.

**The 2026-02-03 batch is cross-wired.** Products point at other products in the same batch — confirmed in Athena
itself (`Maps to`, valid from 20260203, not invalidated), and our bridge matched each AMT concept correctly:

| AMT product | OMOP's `Maps to` |
|---|---|
| Azamun 50 mg tablet (azathioprine) | choline salicylate oral gel [Bonjela] |
| Sandimmun 50 mg/mL injection (ciclosporin) | venlafaxine 75 MG ER capsule [Effexor] |
| Nuelin SR 250 mg (theophylline) | cyclosporine 50 MG/ML injection [Sandimmune] |
| NuvaRing | albuterol inhalation powder [Ventolin] |
| Emend IV 115 mg (fosaprepitant) | insulin aspart pen injector |
| Fiasp FlexTouch (insulin aspart) | salmon calcitonin nasal spray |
| Viekira Pak (hepatitis C regimen) | mycophenolic acid 360 MG |
| Persantin 25 mg | dipyridamole **100** MG *(right drug, wrong product — only the strength witness caught it)* |

**36 of the 91 are rejected.** The batch's remaining mappings were read one by one; those confirmed by the
ingredient witness and not contradicted by brand or strength are kept. Every older batch was screened for the
cross-wiring signature — a product sharing *no* ingredient with its target and carrying another product's brand —
and it does not recur: older disjoint mappings keep their own brand (*Metamucil* → *[Metamucil]*), and are
categories 1–4 above.

This is a defect in OMOP's vocabulary, not in the compendium, and it will return with every build until OHDSI
corrects it. **It is worth reporting upstream.**

## Error two: the wrong active ingredient

In older batches, single-ingredient products where the witnesses disagree and the drug is different:

| AMT substance | OMOP ingredient | products | why it matters |
|---|---|---:|---|
| **Hyoscine butylbromide** (Buscopan) | scopolamine | 61 | butylscopolamine is a quaternary gut antispasmodic that does not enter the brain; scopolamine (hyoscine hydrobromide) is a CNS-active antiemetic |
| **Factor VIII inhibitor bypassing fraction** (FEIBA) | factor VIII | 6 | FEIBA is given *because* the patient's inhibitors defeat factor VIII |
| **Procaine benzylpenicillin** | procaine | 4 | an antibiotic recorded as its local anaesthetic |
| **Podophyllotoxin** | podophyllin | 3 | purified compound against crude, more toxic resin |

**74 rejected.** Two further pairs are plausible either way and are left for a person, not rejected: *trolamine →
trolamine salicylate* (25) and *citric acid → sodium citrate* (5).

## How a rejection is applied

`scripts/apply_omop_drug_review.py`, run straight after the build:

- The refused answer moves to `refused_standard_concept_id` / `refused_standard_name`; the live
  `standard_concept_id` becomes NULL and `review_status` says why. Every reader already filters on
  `standard_concept_id IS NOT NULL`, so `transcode`, `atc_bridge.py`, `drug_strength.py`, `amt_indirect.py` and the
  review queue all stop using it with no code change. **A rejected mapping is ignorance, not an answer.**
- `transcode` rows for rejected TPUUs lose their `omop_drug_*` values and gain `omop_drug_review`.
- `out/omop_drug.parquet`, `out/transcode.parquet` and `out/transcode.csv` are re-exported, so the shipped files
  agree with the database. (Before this, *Azamun → Bonjela* was in `transcode.parquet`.)
- If OMOP later gives a different answer for a rejected product, the step refuses to apply that rejection and
  says so — the review no longer describes the data, and a person should look.

**The generic route then recovers some of them correctly.** With the bad direct mapping gone, item 15's indirect
route reached 17 of the 110 through their generic — *Azamun → azathioprine 50 MG*, *Persantin 25 → dipyridamole
25 MG*, *Efexor-XR → venlafaxine*, *Sandimmun injection → cyclosporine injection*, *Condyline → podofilox* — and all
17 are fully witnessed. None re-reached a wrong answer. The other 93 stay blank.

After application: disagreements 1,887 → 1,778; no rejected product retains a live mapping.

## The substance-level leak, closed in the same pass

`omop_substance` still records OMOP's substance answers faithfully, including the six bad ones and the 13 flagged
in the review queue. It now carries `review_status` (flagged / rejected / superseded), filled by
`apply_standard_ingredients.py`; the two readers that turn a substance answer into a product edge
(`amt_indirect.py`, `drug_strength.py`) use only unobjected rows. Measured: 0 products in `omop_drug_indirect` had
been built from a flagged substance; 97 `strength_check` rows moved to *ingredient not bridged* — 65 of them had
"agreed" on strength, against the wrong ingredient, because OMOP made the same choice twice.

## Reproduce

```bash
.venv/bin/python scripts/omop_drug_audit.py            # ~7 s; writes omop_drug_check + out/omop_drug_audit.json
.venv/bin/python scripts/apply_omop_drug_review.py     # set rejections aside; re-export omop_drug and transcode
```
