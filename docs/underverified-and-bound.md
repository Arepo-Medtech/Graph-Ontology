# Under-verified guidelines, joined with SNOMED-bound conditions

**Generated 2026-09-23** by `scripts/underverified_bound.py`. Base: the **639 PBS condition
families**. ⚠️ Condition→guideline matching is by **token containment on names** and is an
estimate inside a 59–202 band — see [`condition-guideline-tally.md`](condition-guideline-tally.md).

**A** = insufficient guideline (**<50%** of its claims machine re-checkable) · **B** = bound to a SNOMED concept

| set | rows |
|---|---:|
| **A ∩ B** — ⚠️ **the sharp set** | **31** |
| A only | 38 |
| B only | 230 |
| **union** | **299** |

> ### ⚠️ WHY A ∩ B IS THE SET THAT MATTERS
> **The condition is pinned down terminologically, and most of what this compendium says about
> it cannot be checked from this repository.** A precise identifier attached to an unverifiable
> statement is worse than an imprecise one, because it invites downstream systems to trust it.


## A∩B  under-verified AND bound

| condition | PBS restr. | guideline | verified | SNOMED | concept display |
|---|---:|---|---:|---|---|
| Ulcerative colitis | 73 | [inflammatory-bowel-disease](../guidelines/inflammatory-bowel-disease.md) | 43/105 (41%) | `64766004` | Ulcerative colitis |
| Rheumatoid arthritis | 66 | [rheumatoid-arthritis](../guidelines/rheumatoid-arthritis.md) | 10/34 (29%) | `69896004` | Rheumatoid arthritis |
| Crohn disease | 62 | [inflammatory-bowel-disease](../guidelines/inflammatory-bowel-disease.md) | 43/105 (41%) | `34000006` | Crohn's disease |
| Pulmonary arterial hypertension | 45 | [pulmonary-arterial-hypertension](../guidelines/pulmonary-arterial-hypertension.md) | 0/40 (0%) | `11399002` | Pulmonary arterial hypertension |
| Parkinson disease | 39 | [parkinsons-disease](../guidelines/parkinsons-disease.md) | 0/39 (0%) | `49049000` | Parkinson's disease |
| Multiple sclerosis | 17 | [multiple-sclerosis](../guidelines/multiple-sclerosis.md) | 14/43 (33%) | `24700007` | Multiple sclerosis |
| Acne | 8 | [acne](../guidelines/acne.md) | 9/67 (13%) | `11381005` | Acne |
| Hypertension | 8 | [hypertension](../guidelines/hypertension.md) | 3/62 (5%) | `38341003` | Hypertension |
| Benign prostatic hyperplasia | 6 | [benign-prostatic-hyperplasia-and-prostatitis](../guidelines/benign-prostatic-hyperplasia-and-prostatitis.md) | 16/57 (28%) | `266569009` | Benign prostatic hyperplasia |
| Opioid dependence | 5 | [opioid-dependence](../guidelines/opioid-dependence.md) | 0/39 (0%) | `75544000` | Opioid dependence |
| Anovulatory infertility | 4 | [infertility](../guidelines/infertility.md) | 0/13 (0%) | `266609001` | Female infertility of anovulatory origin |
| Psoriasis | 4 | [psoriasis](../guidelines/psoriasis.md) | 0/33 (0%) | `9014002` | Psoriasis |
| Acne vulgaris | 3 | [acne](../guidelines/acne.md) | 9/67 (13%) | `88616000` | Acne vulgaris |
| Chronic thromboembolic pulmonary hypertension | 3 | [hypertension](../guidelines/hypertension.md) | 3/62 (5%) | `233947005` | Chronic thromboembolic pulmonary hypertension |
| Hypothyroidism | 3 | [thyroid-disorders](../guidelines/thyroid-disorders.md) | 0/50 (0%) | `40930008` | Hypothyroidism |
| Myoclonic epilepsy in infancy | 3 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `192990004` | Benign myoclonic epilepsy in infancy |
| Onychomycosis | 3 | [tinea-and-nail-infections](../guidelines/tinea-and-nail-infections.md) | 18/39 (46%) | `414941008` | Onychomycosis |
| Bipolar disorder | 2 | [bipolar-disorder](../guidelines/bipolar-disorder.md) | 0/55 (0%) | `13746004` | Bipolar disorder |
| Chronic hyperkalaemia | 2 | [potassium-disturbances](../guidelines/potassium-disturbances.md) | 0/17 (0%) | `40777006` | Chronic hyperkalaemia |
| Diarrhoea | 2 | [diarrhoea](../guidelines/diarrhoea.md) | 8/45 (18%) | `62315008` | Diarrhoea |
| Epilepsy | 2 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `84757009` | Epilepsy |
| Herpes zoster ophthalmicus | 2 | [conjunctivitis-and-eye-infections](../guidelines/conjunctivitis-and-eye-infections.md) | 48/100 (48%) | `87513003` | Herpes zoster ophthalmicus |
| Prostatitis | 2 | [benign-prostatic-hyperplasia-and-prostatitis](../guidelines/benign-prostatic-hyperplasia-and-prostatitis.md) | 16/57 (28%) | `9713002` | Prostatitis |
| Relapsing remitting multiple sclerosis | 2 | [multiple-sclerosis](../guidelines/multiple-sclerosis.md) | 14/43 (33%) | `426373005` | Relapsing remitting multiple sclerosis |
| Urinary incontinence | 2 | [urinary-incontinence](../guidelines/urinary-incontinence.md) | 17/40 (42%) | `165232002` | Urinary incontinence |
| Angina | 1 | [angina](../guidelines/angina.md) | 29/99 (29%) | `194828000` | Angina |
| Cystic acne | 1 | [acne](../guidelines/acne.md) | 9/67 (13%) | `13277001` | Cystic acne |
| Erectile dysfunction | 1 | [erectile-dysfunction](../guidelines/erectile-dysfunction.md) | 15/45 (33%) | `860914002` | Erectile dysfunction |
| Pyridoxine dependent epilepsy | 1 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `734434007` | Pyridoxine-dependent developmental and epileptic encephalopathy |
| Scalp psoriasis | 1 | [psoriasis](../guidelines/psoriasis.md) | 0/33 (0%) | `238608008` | Scalp psoriasis |
| Tinea pedis | 1 | [tinea-and-nail-infections](../guidelines/tinea-and-nail-infections.md) | 18/39 (46%) | `6020002` | Tinea pedis |

## A    under-verified, not bound

| condition | PBS restr. | guideline | verified | SNOMED | concept display |
|---|---:|---|---:|---|---|
| Chronic plaque psoriasis | 147 | [psoriasis](../guidelines/psoriasis.md) | 0/33 (0%) | `` |  |
| Fistulising Crohn disease | 19 | [inflammatory-bowel-disease](../guidelines/inflammatory-bowel-disease.md) | 43/105 (41%) | `` |  |
| Intractable focal onset seizures | 11 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Risk of hypoglycaemia secondary to growth hormone deficiency in neonates/infants | 7 | [hypoglycaemia](../guidelines/hypoglycaemia.md) | 0/7 (0%) | `` |  |
| Epileptic seizures | 6 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Idiopathic generalised epilepsy with primary generalised tonic-clonic seizures | 6 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Moderately severe Alzheimer disease | 6 | [alzheimers-disease](../guidelines/alzheimers-disease.md) | 0/39 (0%) | `` |  |
| Seizures | 6 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Infertility | 4 | [infertility](../guidelines/infertility.md) | 0/13 (0%) | `` |  |
| Acute mania | 3 | [bipolar-disorder](../guidelines/bipolar-disorder.md) | 0/55 (0%) | `` |  |
| Infections where resistance to amoxicillin is proven | 3 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Acute mania or mixed episodes | 2 | [bipolar-disorder](../guidelines/bipolar-disorder.md) | 0/55 (0%) | `` |  |
| Acute severe ulcerative colitis | 2 | [inflammatory-bowel-disease](../guidelines/inflammatory-bowel-disease.md) | 43/105 (41%) | `` |  |
| Anaerobic infections | 2 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Chronic stable plaque type psoriasis vulgaris | 2 | [psoriasis](../guidelines/psoriasis.md) | 0/33 (0%) | `` |  |
| Clinically definite relapsing-remitting multiple sclerosis | 2 | [multiple-sclerosis](../guidelines/multiple-sclerosis.md) | 14/43 (33%) | `` |  |
| Focal onset seizures | 2 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Gram-positive coccal infections | 2 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Invasive fungal infections including both yeasts and moulds | 2 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Seizures associated with tuberous sclerosis complex | 2 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Stage Parkinson disease | 2 | [parkinsons-disease](../guidelines/parkinsons-disease.md) | 0/39 (0%) | `` |  |
| Streptococcal infections | 2 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Atypical mycobacterial infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Candida infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Cardiac arrhythmias | 1 | [arrhythmias](../guidelines/arrhythmias.md) | 23/107 (21%) | `` |  |
| Contraception | 1 | [contraception](../guidelines/contraception.md) | 29/112 (26%) | `` |  |
| Diarrhoea of greater than 2 weeks duration | 1 | [diarrhoea](../guidelines/diarrhoea.md) | 8/45 (18%) | `` |  |
| Fungal infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Infertility indications other than that of Assisted Reproductive Technology | 1 | [infertility](../guidelines/infertility.md) | 0/13 (0%) | `` |  |
| Intractable childhood epilepsy | 1 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Intractable psoriasis | 1 | [psoriasis](../guidelines/psoriasis.md) | 0/33 (0%) | `` |  |
| Invasive mycosis infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Myoclonic epilepsy | 1 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Seizures of the Lennox-Gastaut syndrome | 1 | [epilepsy](../guidelines/epilepsy.md) | 0/51 (0%) | `` |  |
| Staphylococcal infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Supra-ventricular cardiac arrhythmias | 1 | [arrhythmias](../guidelines/arrhythmias.md) | 23/107 (21%) | `` |  |
| Upper and lower respiratory tract infections | 1 | [drug-choice-for-selected-infections](../guidelines/drug-choice-for-selected-infections.md) | 0/60 (0%) | `` |  |
| Ventricular cardiac arrhythmias | 1 | [arrhythmias](../guidelines/arrhythmias.md) | 23/107 (21%) | `` |  |

## B    bound, no guideline

| condition | PBS restr. | guideline | verified | SNOMED | concept display |
|---|---:|---|---:|---|---|
| Psoriatic arthritis | 76 |  | — | `156370009` | Psoriatic arthritis |
| Juvenile idiopathic arthritis | 55 |  | — | `410502007` | Juvenile idiopathic arthritis |
| Ankylosing spondylitis | 49 |  | — | `9631008` | Ankylosing spondylitis |
| Multiple myeloma | 42 |  | — | `109989006` | Multiple myeloma |
| Cystic fibrosis | 31 |  | — | `190905008` | Cystic fibrosis |
| Breast cancer | 27 |  | — | `254837009` | Malignant neoplasm of breast |
| Chronic Myeloid Leukaemia | 26 |  | — | `92818009` | Chronic myeloid leukaemia |
| Paroxysmal nocturnal haemoglobinuria | 26 |  | — | `1963002` | Paroxysmal nocturnal haemoglobinuria |
| Small lymphocytic lymphoma | 26 |  | — | `302841002` | Malignant lymphoma - small lymphocytic |
| Non-radiographic axial spondyloarthritis | 25 |  | — | `713777005` | Non-radiographic axial spondyloarthritis |
| Spinal muscular atrophy | 22 |  | — | `5262007` | Spinal muscular atrophy |
| Hidradenitis suppurativa | 21 |  | — | `59393003` | Hidradenitis suppurativa |
| Acute Myeloid Leukaemia | 19 |  | — | `91861009` | Acute myeloid leukaemia |
| Diabetes mellitus type 2 | 19 |  | — | `44054006` | Type 2 diabetes |
| Atypical haemolytic uraemic syndrome | 16 |  | — | `789660001` | Atypical haemolytic uraemic syndrome |
| Colorectal cancer | 16 |  | — | `1286877004` | Colorectal cancer |
| Acromegaly | 15 |  | — | `74107003` | Acromegaly |
| Systemic juvenile idiopathic arthritis | 15 |  | — | `201796004` | Systemic onset juvenile chronic arthritis |
| Thrombocytopenia | 12 |  | — | `302215000` | Thrombocytopenia |
| Malignant melanoma | 11 |  | — | `372244006` | Malignant melanoma |
| Schizophrenia | 11 |  | — | `58214004` | Schizophrenia |
| Eosinophilic oesophagitis | 9 |  | — | `235599003` | Eosinophilic oesophagitis |
| Androgen deficiency | 8 |  | — | `38825009` | Deficiency of testosterone biosynthesis |
| Diffuse large B-cell lymphoma | 8 |  | — | `109969005` | Diffuse non-Hodgkin's lymphoma, large cell |
| Fabry disease | 8 |  | — | `16652001` | Fabry's disease |
| Hyperphosphataemia | 8 |  | — | `20165001` | Hyperphosphataemia |
| Infection | 8 |  | — | `40733004` | Infection |
| Social anxiety disorder | 8 |  | — | `25501002` | Social phobia |
| Chronic graft versus host disease | 6 |  | — | `402356004` | Chronic graft-versus-host disease |
| Follicular lymphoma | 6 |  | — | `308121000` | Follicular lymphoma |
| Human immunodeficiency virus infection | 6 |  | — | `86406008` | HIV infection |
| Iron overload | 6 |  | — | `60737008` | Iron overload |
| Myelodysplastic syndrome | 6 |  | — | `109995007` | Myelodysplastic syndrome |
| Narcolepsy | 6 |  | — | `60380001` | Narcolepsy |
| Phenylketonuria | 6 |  | — | `190687004` | Phenylketonuria |
| Primary biliary cholangitis | 6 |  | — | `31712002` | Primary biliary cholangitis |
| Progressive familial intrahepatic cholestasis | 6 |  | — | `74162007` | Progressive intrahepatic cholestasis |
| Amyotrophic lateral sclerosis | 5 |  | — | `86044005` | Amyotrophic lateral sclerosis |
| Branch retinal vein occlusion with macular oedema | 5 |  | — | `232048009` | Branch retinal vein occlusion with macular oedema |
| Central retinal vein occlusion with macular oedema | 5 |  | — | `232039004` | Central retinal vein occlusion with macular oedema |
| Deep vein thrombosis | 5 |  | — | `128053003` | Deep venous thrombosis |
| Diabetic macular oedema | 5 |  | — | `312912001` | Macular oedema due to diabetes |
| Panic disorder | 5 |  | — | `371631005` | Panic disorder |
| Pulmonary embolism | 5 |  | — | `59282003` | Pulmonary embolism |
| Staphylococcal infection | 5 |  | — | `56038003` | Staphylococcal infection |
| Vasoactive intestinal peptide secreting tumour | 5 |  | — | `253005002` | Vasoactive intestinal peptide-secreting tumour |
| Chronic Myelomonocytic Leukaemia | 4 |  | — | `127225006` | Chronic myelomonocytic leukaemia |
| Chronic spontaneous urticaria | 4 |  | — | `302162004` | Chronic idiopathic urticaria |
| Chylous ascites | 4 |  | — | `52985009` | Chylous ascites |
| Cryptococcal meningitis | 4 |  | — | `14232007` | Cryptococcal meningitis |
| Detrusor overactivity | 4 |  | — | `786460007` | Detrusor overactivity |
| Faecal impaction | 4 |  | — | `44635007` | Faecal impaction |
| Growth hormone deficiency | 4 |  | — | `397827003` | Growth hormone deficiency |
| Herpes zoster | 4 |  | — | `4740000` | Herpes zoster |
| Hypercalcaemia | 4 |  | — | `66931009` | Hypercalcaemia |
| Hypercalcaemia of malignancy | 4 |  | — | `47709007` | Malignant hypercalcaemia |
| Hypocalcaemia | 4 |  | — | `5291005` | Hypocalcaemia |
| Idiopathic pulmonary fibrosis | 4 |  | — | `700250006` | Idiopathic pulmonary fibrosis |
| Kaposi sarcoma | 4 |  | — | `109385007` | Kaposi's sarcoma |
| Megacolon | 4 |  | — | `33995003` | Acquired megacolon |
| Micropenis | 4 |  | — | `34911001` | Congenital hypoplasia of penis |
| Polycythemia vera | 4 |  | — | `109992005` | Polycythaemia vera |
| Secondary hyperparathyroidism | 4 |  | — | `91478007` | Secondary hyperparathyroidism |
| Transplant rejection | 4 |  | — | `213148006` | Transplanted organ rejection |
| Zollinger-Ellison syndrome | 4 |  | — | `53132006` | Zollinger-Ellison syndrome |
| Acute coronary syndrome | 3 |  | — | `394659003` | Acute coronary syndrome |
| Anxiety | 3 |  | — | `48694002` | Anxiety |
| Aplastic anaemia | 3 |  | — | `306058006` | Aplastic anaemia |
| Bipolar I disorder | 3 |  | — | `371596008` | Bipolar I disorder |
| Central precocious puberty | 3 |  | — | `237816004` | Central precocious puberty |
| Chronic bronchitis | 3 |  | — | `63480004` | Chronic bronchitis |
| Chronic lymphocytic leukaemia | 3 |  | — | `92814006` | Chronic lymphocytic leukaemia |
| Chylothorax | 3 |  | — | `83035003` | Chylothorax |
| Depression | 3 |  | — | `35489007` | Depression |
| Fungal infection | 3 |  | — | `3218000` | Mycosis |
| Lupus nephritis | 3 |  | — | `68815009` | SLE glomerulonephritis syndrome |
| Mantle cell lymphoma | 3 |  | — | `443487006` | Mantle cell lymphoma |
| Neurofibromatosis type 1 | 3 |  | — | `92824003` | Neurofibromatosis type 1 |
| Obesity | 3 |  | — | `414916001` | Obesity |
| Obsessive-compulsive disorder | 3 |  | — | `191736004` | Obsessive-compulsive disorder |
| Oligodendroglioma | 3 |  | — | `443936004` | Oligodendroglioma |
| Osteomyelitis | 3 |  | — | `60168000` | Osteomyelitis |
| Paget disease of bone | 3 |  | — | `2089002` | Paget's disease of bone |
| Tumour-induced osteomalacia | 3 |  | — | `392559009` | Osteomalacia due to neoplasm |
| Uveitis | 3 |  | — | `128473001` | Uveitis |
| Vitamin D-resistant rickets | 3 |  | — | `82236004` | Familial x-linked hypophosphataemic vitamin D refractory rickets |
| Achondroplasia | 2 |  | — | `86268005` | Achondroplasia |
| Alcohol dependence | 2 |  | — | `66590003` | Alcohol dependence |
| Analgesia | 2 |  | — | `38433004` | No sensitivity to pain |
| Autosomal dominant polycystic kidney disease | 2 |  | — | `765330003` | Autosomal dominant polycystic kidney disease |
| Bacterial keratitis | 2 |  | — | `314557000` | Bacterial keratitis |
| Bronchiectasis | 2 |  | — | `12295008` | Bronchiectasis |
| Bronchospasm | 2 |  | — | `4386001` | Bronchospasm |
| Cellulitis | 2 |  | — | `128045006` | Cellulitis |
| Chronic eosinophilic leukaemia | 2 |  | — | `188733003` | Chronic eosinophilic leukaemia |
| Chronic granulomatous disease | 2 |  | — | `387759001` | Chronic granulomatous disease |
| Chronic renal failure | 2 |  | — | `90688005` | Chronic renal failure |
| Congenital neutropenia | 2 |  | — | `89655007` | Congenital neutropenia |
| Cranial diabetes insipidus | 2 |  | — | `45369008` | AVP-D - arginine vasopressin deficiency |
| Cutaneous squamous cell carcinoma | 2 |  | — | `254651007` | Squamous cell carcinoma of skin |
| Cutaneous T-cell lymphoma | 2 |  | — | `400122007` | Primary cutaneous T-cell lymphoma |
| Cytomegalovirus retinitis | 2 |  | — | `22455005` | Cytomegaloviral retinitis |
| Dermatofibrosarcoma protuberans | 2 |  | — | `276799004` | Dermatofibrosarcoma protuberans |
| Endocarditis | 2 |  | — | `56819008` | Endocarditis |
| Familial hypophosphataemia | 2 |  | — | `82236004` | Familial x-linked hypophosphataemic vitamin D refractory rickets |
| Fever | 2 |  | — | `386661006` | Fever |
| Fibrodysplasia ossificans progressiva | 2 |  | — | `82725007` | Progressive myositis ossificans |
| Gastrointestinal stromal tumour | 2 |  | — | `420120006` | Gastrointestinal stromal tumour |
| Generalized convulsive status epilepticus | 2 |  | — | `1299166008` | Generalised tonic-clonic status epilepticus |
| Giant cell arteritis | 2 |  | — | `414341000` | Giant cell arteritis |
| Glioblastoma multiforme | 2 |  | — | `393563007` | Glioblastoma multiforme |
| Glutaric aciduria type 1 | 2 |  | — | `360416003` | Glutaryl-CoA dehydrogenase deficiency |
| Gonorrhoea | 2 |  | — | `15628003` | Gonorrhoea |
| Hemifacial spasm | 2 |  | — | `13753008` | Hemifacial spasm |
| Herpes simplex keratitis | 2 |  | — | `9389005` | Herpes simplex keratitis |
| Hypereosinophilic syndrome | 2 |  | — | `393573009` | Hypereosinophilic syndrome |
| Hyperphenylalaninaemia | 2 |  | — | `68528007` | Hyperphenylalaninaemia |
| Hypomagnesaemia | 2 |  | — | `190855004` | Hypomagnesaemia |
| Hypoparathyroidism | 2 |  | — | `36976004` | Hypoparathyroidism |
| Keloid | 2 |  | — | `33659008` | Keloid scar |
| Leiomyosarcoma | 2 |  | — | `443719001` | Leiomyosarcoma |
| Liposarcoma | 2 |  | — | `254829001` | Liposarcoma |
| Maple syrup urine disease | 2 |  | — | `27718001` | Maple syrup urine disease |
| Merkel Cell Carcinoma | 2 |  | — | `253001006` | Merkel cell carcinoma |
| Methylmalonic acidaemia | 2 |  | — | `42393006` | Methylmalonic acidaemia |
| Mucositis | 2 |  | — | `95361005` | Mucositis |
| Myeloproliferative disorder | 2 |  | — | `425333006` | Myeloproliferative disorder |
| Nephrotic syndrome | 2 |  | — | `52254009` | Nephrotic syndrome |
| Pernicious anaemia | 2 |  | — | `84027009` | Pernicious anaemia |
| Pre-exposure prophylaxis against human immunodeficiency virus infection | 2 |  | — | `918591000168102` | Antiretroviral pre-exposure prophylaxis for HIV infection |
| Precursor B-cell acute lymphoblastic leukaemia | 2 |  | — | `277572006` | Precursor B-cell acute lymphoblastic leukaemia |
| Propionic acidaemia | 2 |  | — | `69080001` | Propionic acidaemia |
| Renal cell carcinoma | 2 |  | — | `702391001` | Renal cell carcinoma |
| Solar keratosis | 2 |  | — | `201101007` | Actinic keratosis |
| Spasmodic torticollis | 2 |  | — | `74333002` | Spasmodic torticollis |
| Strongyloidiasis | 2 |  | — | `1214006` | Infection caused by Strongyloides |
| Superficial basal cell carcinoma | 2 |  | — | `403914000` | Superficial basal cell carcinoma |
| Systemic lupus erythematosus | 2 |  | — | `55464009` | Systemic lupus erythematosus |
| Thiamine deficiency | 2 |  | — | `399357009` | Thiamin deficiency |
| Thyroid cancer | 2 |  | — | `363478007` | Malignant neoplasm of thyroid gland |
| Ulcerative proctitis | 2 |  | — | `10811000202109` | Ulcerative proctitis |
| Urethritis | 2 |  | — | `31822004` | Urethritis |
| Waldenstrom macroglobulinaemia | 2 |  | — | `190818004` | Waldenström macroglobulinaemia |
| Alopecia areata | 1 |  | — | `68225006` | Alopecia areata |
| Bacterial gastroenteritis | 1 |  | — | `274080003` | Bacterial gastroenteritis |
| Biliary atresia | 1 |  | — | `77480004` | Congenital biliary atresia |
| Blepharospasm | 1 |  | — | `59026006` | Blepharospasm |
| Bone infection | 1 |  | — | `111253001` | Infection of bone |
| Cataplexy | 1 |  | — | `46263000` | Cataplexy |
| Cervicitis | 1 |  | — | `37610005` | Inflammation of cervix |
| Chronic discoid lupus erythematosus | 1 |  | — | `238927000` | Chronic discoid lupus erythematosus |
| Chronic renal disease | 1 |  | — | `709044004` | Chronic kidney disease |
| Community acquired pneumonia | 1 |  | — | `385093006` | Community acquired pneumonia |
| Coronary artery disease | 1 |  | — | `53741008` | Coronary arteriosclerosis |
| Delayed puberty | 1 |  | — | `400003000` | Delayed puberty |
| Endophthalmitis | 1 |  | — | `1847009` | Endophthalmitis |
| Epididymo-orchitis | 1 |  | — | `197983000` | Orchitis and epididymitis |
| Gastric stasis | 1 |  | — | `235675006` | Gastroparesis syndrome |
| Giant cell tumour of bone | 1 |  | — | `697970009` | Giant cell tumour of bone |
| Glycogen storage disease | 1 |  | — | `29633007` | Glycogen storage disease |
| Haemodialysis | 1 |  | — | `302497006` | Haemodialysis |
| Hairy cell leukaemia | 1 |  | — | `118613001` | Hairy cell leukaemia |
| Hepatic encephalopathy | 1 |  | — | `13920009` | Hepatic encephalopathy |
| Homocystinuria | 1 |  | — | `11282001` | Homocystinuria |
| Hydatid disease | 1 |  | — | `74942003` | Echinococcosis |
| Hypogonadism | 1 |  | — | `48130008` | Hypogonadism |
| Invasive aspergillosis | 1 |  | — | `721798004` | Invasive aspergillosis |
| Isovaleric acidaemia | 1 |  | — | `87827003` | Isovaleryl-CoA dehydrogenase deficiency |
| Joint infection | 1 |  | — | `363162000` | Infectious disorder of joint |
| Lambert-Eaton myasthenic syndrome | 1 |  | — | `56989000` | Eaton-Lambert syndrome |
| Leprosy | 1 |  | — | `81004002` | Leprosy |
| Lichen simplex chronicus | 1 |  | — | `53891004` | Lichen simplex chronicus |
| Malaria | 1 |  | — | `61462000` | Malaria |
| Melanoma | 1 |  | — | `372244006` | Malignant melanoma |
| Meningococcal disease | 1 |  | — | `23511006` | Meningococcal infectious disease |
| Menorrhagia | 1 |  | — | `386692008` | Heavy menstrual bleeding |
| Nasopharyngeal carcinoma | 1 |  | — | `449248000` | Nasopharyngeal carcinoma |
| Nausea | 1 |  | — | `422587007` | Nausea |
| Necrobiosis lipoidica | 1 |  | — | `9418005` | Necrobiosis lipoidica |
| Oesophageal cancer | 1 |  | — | `363402007` | Malignant neoplasm of oesophagus |
| Onchocerciasis | 1 |  | — | `38539003` | Infection caused by Onchocerca volvulus |
| Painful mouth | 1 |  | — | `102616008` | Pain in mouth |
| Pelvic inflammatory disease | 1 |  | — | `198130006` | Pelvic inflammatory disease |
| Peptic ulcer | 1 |  | — | `13200003` | Peptic ulcer |
| Phaeochromocytoma | 1 |  | — | `302835009` | Phaeochromocytoma |
| Proctitis | 1 |  | — | `3951002` | Proctitis |
| Respiratory tract infection | 1 |  | — | `275498002` | Respiratory tract infection |
| Schistosomiasis | 1 |  | — | `10087007` | Infection caused by Schistosoma |
| Staphylococcus aureus infection | 1 |  | — | `406602003` | Infection caused by Staphylococcus aureus |
| Systemic aspergillosis | 1 |  | — | `240701006` | Systemic aspergillosis |
| Type 1 diabetes | 1 |  | — | `46635009` | Type 1 diabetes |
| Urinary symptoms | 1 |  | — | `249274008` | Urinary symptoms |
| Urinary tract infection | 1 |  | — | `68566005` | Urinary tract infection |

## B    bound, guideline is sufficient

| condition | PBS restr. | guideline | verified | SNOMED | concept display |
|---|---:|---|---:|---|---|
| Asthma | 82 | [asthma](../guidelines/asthma.md) | 22/22 (100%) | `195967001` | Asthma |
| Constipation | 27 | [constipation](../guidelines/constipation.md) | 48/48 (100%) | `14760008` | Constipation |
| Nausea and vomiting | 24 | [vomiting](../guidelines/vomiting.md) | 30/30 (100%) | `16932000` | Nausea and vomiting |
| HIV infection | 22 | [hiv](../guidelines/hiv.md) | 36/36 (100%) | `86406008` | HIV infection |
| Pain | 19 | [opioid-analgesic-stewardship-acute-pain](../guidelines/opioid-analgesic-stewardship-acute-pain.md) | 42/42 (100%) | `22253000` | Pain |
| Chronic obstructive pulmonary disease | 17 | [copd](../guidelines/copd.md) | 23/23 (100%) | `13645005` | COPD |
| Chronic heart failure | 12 | [heart-failure](../guidelines/heart-failure.md) | 12/14 (86%) | `48447003` | Chronic heart failure |
| Osteoporosis | 11 | [osteoporosis](../guidelines/osteoporosis.md) | 10/10 (100%) | `64859006` | Osteoporosis |
| Attention deficit hyperactivity disorder | 10 | [adhd](../guidelines/adhd.md) | 72/72 (100%) | `406506008` | Attention deficit hyperactivity disorder |
| Gastro-oesophageal reflux disease | 10 | [gord-and-dyspepsia](../guidelines/gord-and-dyspepsia.md) | 35/35 (100%) | `235595009` | Gastro-oesophageal reflux disease |
| Primary nocturnal enuresis | 10 | [nocturnal-enuresis](../guidelines/nocturnal-enuresis.md) | 42/42 (100%) | `450845009` | Primary nocturnal enuresis |
| Allergic asthma | 8 | [asthma](../guidelines/asthma.md) | 22/22 (100%) | `389145006` | Allergic asthma |
| Endometriosis | 8 | [endometriosis](../guidelines/endometriosis.md) | 32/45 (71%) | `129103003` | Endometriosis |
| Generalised anxiety disorder | 8 | [generalised-anxiety-disorder](../guidelines/generalised-anxiety-disorder.md) | 8/9 (89%) | `21897009` | Generalised anxiety disorder |
| Major depression | 8 | [major-depressive-disorder](../guidelines/major-depressive-disorder.md) | 11/11 (100%) | `370143000` | Major depressive disorder |
| Nicotine dependence | 7 | [smoking-cessation](../guidelines/smoking-cessation.md) | 55/55 (100%) | `56294008` | Nicotine dependence |
| Dry eye syndrome | 6 | [dry-eye-and-topical-eye-drug-principles](../guidelines/dry-eye-and-topical-eye-drug-principles.md) | 34/68 (50%) | `46152009` | Tear film insufficiency |
| Insomnia | 6 | [insomnia](../guidelines/insomnia.md) | 11/11 (100%) | `193462001` | Insomnia |
| Bone pain | 5 | [opioid-analgesic-stewardship-acute-pain](../guidelines/opioid-analgesic-stewardship-acute-pain.md) | 42/42 (100%) | `12584003` | Bone pain |
| Atopic dermatitis | 4 | [eczema](../guidelines/eczema.md) | 50/50 (100%) | `24079001` | Atopic dermatitis |
| Chronic constipation | 4 | [constipation](../guidelines/constipation.md) | 48/48 (100%) | `236069009` | Chronic constipation |
| Migraine | 4 | [migraine](../guidelines/migraine.md) | 9/9 (100%) | `37796009` | Migraine |
| Chronic migraine | 3 | [migraine](../guidelines/migraine.md) | 9/9 (100%) | `427419006` | Transformed migraine |
| Chronic suppurative otitis media | 3 | [otitis-media](../guidelines/otitis-media.md) | 34/34 (100%) | `38394007` | Chronic suppurative otitis media |
| Breakthrough pain | 2 | [opioid-analgesic-stewardship-acute-pain](../guidelines/opioid-analgesic-stewardship-acute-pain.md) | 42/42 (100%) | `879969009` | Breakthrough pain |
| Chronic kidney disease | 2 | [chronic-kidney-disease](../guidelines/chronic-kidney-disease.md) | 28/28 (100%) | `709044004` | Chronic kidney disease |
| Chronic rhinosinusitis with nasal polyps | 2 | [rhinosinusitis](../guidelines/rhinosinusitis.md) | 45/45 (100%) | `1285576009` | Chronic rhinosinusitis with multiple nasal polyps |
| Familial homozygous hypercholesterolaemia | 2 | [cardiovascular-disease-risk](../guidelines/cardiovascular-disease-risk.md) | 22/22 (100%) | `238078005` | Familial homozygous hypercholesterolaemia |
| Heart failure | 2 | [heart-failure](../guidelines/heart-failure.md) | 12/14 (86%) | `84114007` | Heart failure |
| Neuropathic pain | 2 | [opioid-analgesic-stewardship-acute-pain](../guidelines/opioid-analgesic-stewardship-acute-pain.md) | 42/42 (100%) | `247398009` | Neuropathic pain |
| Stroke | 2 | [stroke](../guidelines/stroke.md) | 71/71 (100%) | `230690007` | Stroke |
| Crusted scabies | 1 | [ectoparasites-scabies-and-pubic-lice](../guidelines/ectoparasites-scabies-and-pubic-lice.md) | 33/33 (100%) | `128870005` | Crusted scabies |
| Dysmenorrhoea | 1 | [dysmenorrhoea-and-premenstrual-syndrome](../guidelines/dysmenorrhoea-and-premenstrual-syndrome.md) | 29/44 (66%) | `266599000` | Dysmenorrhoea |
| Eczema | 1 | [eczema](../guidelines/eczema.md) | 50/50 (100%) | `43116000` | Eczema |
| Iron deficiency anaemia | 1 | [iron-deficiency](../guidelines/iron-deficiency.md) | 46/46 (100%) | `87522002` | Iron deficiency anaemia |
| Non-Q-wave myocardial infarction | 1 | [acute-coronary-syndromes](../guidelines/acute-coronary-syndromes.md) | 40/40 (100%) | `314207007` | Non-Q wave myocardial infarction |
| Osteoarthritis | 1 | [osteoarthritis-knee-clinical-care-standard](../guidelines/osteoarthritis-knee-clinical-care-standard.md) | 60/60 (100%) | `396275006` | Osteoarthritis |
