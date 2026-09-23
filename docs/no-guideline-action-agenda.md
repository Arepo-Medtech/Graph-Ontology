# Action agenda: the 493 PBS conditions with no guideline

**Status:** started 2026-09-23. **Inputs:** `reference/no_guideline_pbs.json` (PR #14), `reference/no_guideline_triage.json` (`scripts/no_guideline_triage.py`), and `research/*` (source research, in progress).

## 1. Triage — what the 493 actually are

| kind | count | action |
|---|---:|---|
| **true gap** | **393** | research an Australian source, then author (tracks B–C) |
| near-miss | 37 | a guideline may already cover it. Human check: link it, or confirm the gap (often adult PBS indication vs a children's guideline) |
| duplicate | 45 | split child with the same PBS listing as its parent row. Covered when the parent is |
| admin | 9 | PBS listing policy or a procedure, not a disease (*base-priced drugs*, *patient identifying as…*, *assisting bone marrow transplantation*) |
| artefact | 9 | parsing fragment (*Oral*, *Proven*, *Definite*…). Candidate for removal from the condition list (a judgement call) |

## 2. True gaps by specialty (routing heuristic: name keywords, else dominant ATC class)

| specialty | gaps | PBS restrictions | top conditions | research group |
|---|---:|---:|---|---|
| Oncology (solid tumours) | 82 | 319 | Non-small cell lung cancer, Breast cancer, HER2 positive breast cancer, Epithelial ovarian, fallopian tube or primary peritoneal cancer | `oncology-solid` |
| Rheumatology | 13 | 241 | Psoriatic arthritis, Juvenile idiopathic arthritis, Ankylosing spondylitis, Non-radiographic axial spondyloarthritis | `specialty-mixed` |
| Haematological malignancy | 35 | 211 | Multiple myeloma, Chronic Myeloid Leukaemia, Chronic lymphocytic leukaemia or small lymphocytic lymphoma, Acute Myeloid Leukaemia | `haematology` |
| Endocrinology | 33 | 177 | Short stature associated with biochemical growth hormone deficiency, Pathological hyperprolactinaemia, Acromegaly, Short stature and slow growth | `endocrine-metabolic` |
| Neurology | 29 | 114 | Spinal muscular atrophy, Chronic spasticity, Treatment refractory generalised myasthenia gravis, Type IIIB/IIIC spinal muscular atrophy | `neuro-psych-eye` |
| Metabolic & genetic | 34 | 96 | Fabry disease, Hereditary tyrosinaemia type 1, Phenylketonuria, Urea cycle disorders | `endocrine-metabolic` |
| Infectious diseases | 33 | 82 | Cytomegalovirus infection and disease, SARS-CoV-2 infection, Human immunodeficiency virus infection, Pseudomonas aeruginosa infection | `infectious` |
| Haematology | 14 | 76 | Paroxysmal nocturnal haemoglobinuria, Atypical haemolytic uraemic syndrome, Chemotherapy-induced neutropenia, Deep vein thrombosis | `haematology` |
| Gastroenterology & hepatology | 27 | 75 | Eosinophilic oesophagitis, Primary biliary cholangitis, Progressive familial intrahepatic cholestasis, Anorectal congenital abnormalities | `specialty-mixed` |
| Respiratory | 11 | 54 | Cystic fibrosis, Pulmonary embolism, Idiopathic pulmonary fibrosis, Chronic bronchitis | `specialty-mixed` |
| Ophthalmology | 16 | 47 | Subfoveal choroidal neovascularisation, Branch retinal vein occlusion with macular oedema, Central retinal vein occlusion with macular oedema, Non-infectious uveitis | `neuro-psych-eye` |
| Dermatology | 7 | 43 | Hidradenitis suppurativa, Corticosteroid-responsive dermatoses, Chronic graft versus host disease, Solar keratosis | `specialty-mixed` |
| Musculoskeletal | 11 | 37 | Bone metastases, Chronic arthropathies, Hypercalcaemia of malignancy, Paget disease of bone | `specialty-mixed` |
| Women's health & urology | 12 | 32 | Androgen deficiency, Detrusor overactivity, Micropenis, Pubertal induction | `specialty-mixed` |
| Psychiatry & addiction | 6 | 27 | Schizophrenia, Major depressive disorders, Behavioural disturbances, Depression | `neuro-psych-eye` |
| Other (antidotes, diagnostics, nutrition) | 7 | 27 | Chronic iron overload, Iron overload, Hypercalcaemia, Disorders of erythropoiesis | `specialty-mixed` |
| Nephrology & transplant | 8 | 23 | Renal allograft rejection, Cardiac allograft rejection, Transplant rejection, Autosomal dominant polycystic kidney disease | `specialty-mixed` |
| Immunology (other) | 4 | 9 | Chronic pouchitis, Idiopathic multicentric Castleman disease, Neuromyelitis optica spectrum disorder, Cryopyrin associated periodic syndromes | `specialty-mixed` |
| Other | 8 | 9 | Strongyloidiasis, Hookworm infestation, Hydatid disease, Onchocerciasis | `infectious` |
| Cardiology | 3 | 5 | Obstructive hypertrophic cardiomyopathy, Neurogenic urinary retention, Phaeochromocytoma | `specialty-mixed` |

## 3. Tracks

**Track A — PBS access page (all gaps).** Quote each condition's PBS restriction criteria verbatim, unmodified, with the PBS copyright
statement retained. That tells a prescriber who qualifies, the initial and continuing criteria, and the authority type. It is **not**
treatment guidance and would be labelled as such. ⛔ **Blocked on Decision 1.**

**Track B — Australian specialty guidance (primary).** For each specialty, the source(s) found in `research/<group>.md`, authored with the
proven pipeline: verbatim fragments, `verify.py`, `number_guard.py`, and a licence footing per source (open / quote-with-attribution /
capped like Cancer Council).

**Track C — international evidence layer (where no Australian source exists).** Consensus and PubMed searches for current international
guidelines and trials (EULAR, BSR, ESMO, NICE…). Used as an **evidence pack** attached to the gap: citation, design, grade, licence.
International guidance is not presented as Australian practice, and verbatim quoting is only done where its licence allows
(e.g. EULAR 2023 is CC BY-NC-ND).

**Track D — attestation.** New dose claims from quotable sources are machine-checked. Anything paraphrased joins the existing attestation queue.

## 4. Sequencing
1. **Now:** source research for all gaps, 6 parallel researchers (running).
2. **Wave 1:** the highest-weight gaps with an open or quotable Australian source. Rheumatology biologics (PsA, JIA, AS, nr-axSpA),
   myeloma, CML/CLL, cystic fibrosis, SMA, PNH/aHUS, growth hormone, acromegaly, hidradenitis.
3. **Wave 2:** the remaining gaps that have a usable Australian source.
4. **Wave 3:** gaps with no usable Australian source get the Track C evidence pack, plus the Track A access page if Decision 1 allows.
5. **Throughout:** resolve the 37 near-misses and 9 artefacts (human judgement; this list does not change the condition list itself).

## 5. Decisions needed from the repository owner

1. **PBS and Commonwealth content terms (read 2026-09-23 — quoted, not interpreted):**
   - PBS API: *"Permission is granted to use and redistribute this content, as long as all copyright statements are retained. Permission is not granted to modify this content."*
   - pbs.gov.au: *"It may be reproduced in part for personal use as general reference material only, provided any copyright and disclaimer notices remain intact."*
   - health.gov.au: *"You must not use the whole or any part of the content on this website for any commercial purpose."*

   `reference/conditions.json` records the licence as "Commonwealth CC BY". **That is not what these pages say.** The health.gov.au
   commercial-use clause also bears on the 24 Immunisation Handbook guidelines already merged. Whether Track A can proceed, and on what
   footing, is the owner's call (and possibly legal advice), not an engineering one.
2. **Non-commercial (NC) licences:** are CC BY-NC / NC-ND sources acceptable, given the project may be commercial?
3. **Consensus:** the free tier returns 3 results per search. Connecting an account raises that.
4. **International guidance:** evidence layer only (as proposed), or also authored as clearly-labelled non-Australian guidelines?

## 6. Progress log
- 2026-09-23: triage complete (393 gaps / 37 near-miss / 45 duplicate / 9 admin / 9 artefact). Source research launched in 6 groups.
