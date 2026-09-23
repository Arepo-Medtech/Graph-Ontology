# SNOMED binding review queue

**349 candidates at `snomed: null`.** Source `reference/snomed_candidates_review.json`. Nothing here is bound.

> ### ⚠️ THE 'PLAUSIBLE' TIER IS NOT SAFE
> The review file's own warning: *"Signals are LEXICAL triage, not verdicts. The 'plausible' tier
> is NOT safe: of 16 quarantined pregnancy candidates reviewed by hand, **6 carried no flag at all
> and every one was wrong**."* **Nothing is auto-bound.** Lexical agreement is not evidence — the
> top hit for *Acute mania or mixed episodes* is *Progressive cavitating leukoencephalopathy*.

> ### Write your decision in the first column
> | you write | means | state written to `binding_corrections.json` |
> |---|---|---|
> | *(empty)* | not yet reviewed | — |
> | `918591000168102 KL 2026-09-23` | **BIND** this concept | `corrected_pending_attestation` |
> | `! KL 2026-09-23 <why>` | ⚠️ **REJECT** — must NOT bind | `rejected` |
> | `? KL 2026-09-23 <note>` | deferred; stays in the queue | — |
>
> ⚠️ **Anything unrecognised is treated as DEFERRED, never as a bind.** A decision is matched on
> condition **and `sha`** (condition + top-hit code) — if the candidate changes, the decision
> returns to the queue rather than binding to a hit nobody saw.

**Order is by what evidence settles, cheapest first.** Tiers A–C were derived from the SNOMED
hierarchy — parents sharing no concept with the condition — **not** from string similarity.

**0 decided · 349 outstanding.**

## Run order
```bash
python3 scripts/binding_review.py             # rewrite this file
python3 scripts/binding_review.py --harvest  # -> reference/binding_corrections.json
python3 scripts/apply_corrections.py         # -> reference/snomed_bindings.json
```


## A. ⚠️ QUARANTINED — pregnancy or reproductive, MANUAL REVIEW REGARDLESS OF SIGNAL

*15 rows — review by hand; do not trust any signal.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Contraception | `988afb96` | `308419002` Contraception call | Patient call procedure | ⚠️ QUARANTINED: pregnancy_or_reproductive, parents_unrelated, narrower | 2 |
|  | Diarrhoea of greater than 2 weeks duration | `1507c98a` | `429715006` Gestation greater than 20 weeks | Finding of length of gestation | ⚠️ QUARANTINED: pregnancy_or_reproductive, parents_unrelated | 2 |
|  | Facial lipoatrophy | `44b40364` | `773331001` Nestor Guillermo progeria syndrome | Autosomal recessive hereditary disorder; Fetal and/or neonatal disorder of integument | ⚠️ QUARANTINED: pregnancy_or_reproductive, off_domain, parents_unrelated | 0 |
|  | Maternal hyperphenylalaninaemia due to phenylketonuria | `43bc9f6b` | `713187004` Polyhydramnios due to maternal disease | Polyhydramnios | ⚠️ QUARANTINED: pregnancy_or_reproductive, parents_unrelated | 2 |
|  | Mixed episodes | `92298448` | `774084003` Neonatal antiphospholipid syndrome | Antiphospholipid syndrome; Neonatal disorder | ⚠️ QUARANTINED: pregnancy_or_reproductive, off_domain, parents_unrelated | 0 |
|  | Preterm birth | `15ec004f` | `773691007` Congenital erosive and vesicular dermatosis | Congenital anomaly of skin; Idiopathic disease | ⚠️ QUARANTINED: pregnancy_or_reproductive, off_domain, parents_unrelated | 2 |
|  | Septicaemia | `89afe845` | `137701000119106` Antepartum septicaemia | Complication occurring during pregnancy; Sepsis | ⚠️ QUARANTINED: pregnancy_or_reproductive, parents_unrelated, narrower | 2 |
|  | Termination of an intra-uterine pregnancy | `ad8c3ff1` | `18302006` Hysterotomy and termination of pregnancy | Obstetrical hysterotomy; Operation on gravid uterus | ⚠️ QUARANTINED: pregnancy_or_reproductive | 2 |
|  | The onset of lactation | `b994b60b` | `1172841001` Combined oxidative phosphorylation defect type 30 | Autosomal recessive hereditary disorder; Disorder of skeletal muscle | ⚠️ QUARANTINED: pregnancy_or_reproductive, off_domain, parents_unrelated | 2 |
|  | Secondarily infected traumatic skin lesions | `4a6a7c96` | `715223009` Fetal varicella syndrome | Embryofetopathy due to infection; Varicella-zoster virus infection | ⚠️ QUARANTINED: pregnancy_or_reproductive, parent_better | 2 |
|  | Upper and lower respiratory tract infections | `22c99bf8` | `763532008` Familial nasal acilia | Congenital disease; Familial disease | ⚠️ QUARANTINED: pregnancy_or_reproductive, parent_better | 2 |
|  | Complicated urinary tract infection | `556788e0` | `609491002` Induced termination of pregnancy complicated by urinary tract infection | Infectious disease in mother complicating pregnancy, childbirth AND/OR puerperium; Procedure related finding | ⚠️ QUARANTINED: pregnancy_or_reproductive, narrower | 0 |
|  | Anaemia associated with intrinsic renal disease | `5302bc38` | `472326004` Fetal hypertrophic cardiomyopathy associated with renal disease | Cardiomyopathy associated with another disorder; Fetal hypertrophic cardiomyopathy | ⚠️ QUARANTINED: pregnancy_or_reproductive | 2 |
|  | Patients undergoing in-vitro fertilisation | `1bdc71d2` | `52637005` In vitro fertilisation | Assisted fertilisation | ⚠️ QUARANTINED: pregnancy_or_reproductive | 2 |
|  | Risk of hypoglycaemia secondary to growth hormone deficiency in neonates/infants | `f5cc8e80` | `1231283007` Congenital isolated adrenocorticotropic hormone deficiency | Autosomal recessive hereditary disorder; Congenital disease | ⚠️ QUARANTINED: pregnancy_or_reproductive | 2 |

## B. Reject on hierarchy — no shared concept

*33 rows — confirm the rejection.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Acute mania or mixed episodes | `531fb49d` | `719267003` Progressive cavitating leukoencephalopathy | Autosomal recessive hereditary disorder; Hereditary disorder of nervous system | off_domain, parents_unrelated | 2 |
|  | Adult-type IDH-mutant astrocytoma or oligodendroglioma | `6a7a1c04` | `1260467009` Large congenital pigmented melanocytic naevus of skin | Congenital pigmented melanocytic naevus of skin; Genetic disease | off_domain, parents_unrelated | 2 |
|  | Adverse effects occurring with all of the base-priced drugs | `be358f59` | `73442001` Stevens-Johnson syndrome | Hypersensitivity condition; Stevens-Johnson syndrome, toxic epidermal necrolysis spectrum | off_domain, parents_unrelated | 0 |
|  | Behavioural disturbances | `995e0b19` | `609585002` Sundowning | Mental state finding | off_domain, parents_unrelated | 2 |
|  | Biochemical growth hormone deficiency and precocious puberty | `25f624ad` | `770941005` Alopecia, progressive neurological defect, endocrinopathy syndrome | Developmental hereditary disorder; Genetic intellectual disability | off_domain, parents_unrelated | 2 |
|  | Candida infections | `4fdca6b9` | `763713000` Idiopathic CD4 lymphocytopenia | CD4 T lymphocyte deficiency; Idiopathic disease | off_domain, parents_unrelated | 1 |
|  | Cardiac arrhythmias | `5b756ebe` | `719823007` Ventricular extrasystoles with syncope, perodactyly and Robin sequence syndrome | Congenital abnormality of oral cavity; Congenital anomaly of digit | off_domain, parents_unrelated | 2 |
|  | Chronic spasticity | `5f7fe452` | `787175002` ANK3-related intellectual disability, sleep disturbance syndrome | Autosomal recessive hereditary disorder; Developmental hereditary disorder | off_domain, parents_unrelated | 1 |
|  | Cytomegalovirus infection and disease | `1b7542ac` | `721015008` HEC syndrome | Communicating hydrocephalus; Congenital cataract | off_domain, parents_unrelated | 0 |
|  | Disabling pain | `dfb381db` | `715657008` Familial avascular necrosis of head of femur | Autosomal dominant hereditary disorder; Hereditary disorder of musculoskeletal system | off_domain, parents_unrelated | 0 |
|  | Drug interactions expected to occur with all of the base-priced drugs | `21613421` | `1367520006` Clavien-Dindo classification grade II | Clavien-Dindo classification finding | off_domain, parents_unrelated | 2 |
|  | Epithelial ovarian cancer | `d7afdca4` | `363443007` Malignant neoplasm of ovary | Malignant neoplasm of female genital organ; Malignant neoplasm of intraabdominal organ | off_domain, parents_unrelated | 2 |
|  | Fungal infections | `21741182` | `1335927007` T-cell negative B-cell positive severe combined immunodeficiency | Severe combined immunodeficiency disease | off_domain, parents_unrelated | 2 |
|  | Growth retardation secondary to an intracranial lesion, or cranial irradiation | `e286a4ed` | `763630007` Satoyoshi syndrome | Alopecia; Autoimmune skin disease | off_domain, parents_unrelated | 2 |
|  | High risk and intermediate-2 risk myelofibrosis | `92cadde0` | `1229871006` Primary squamous cell carcinoma of nasal cavity and paranasal sinus | Primary squamous cell carcinoma of accessory sinus; Primary squamous cell carcinoma of nasal cavity | off_domain, parents_unrelated | 1 |
|  | Hookworm infestation | `6c2470a7` | `105694003` Disease caused by Ancylostomatoidea | Infection caused by Nematoda | off_domain, parents_unrelated | 0 |
|  | Hyperphenylalaninaemia due to phenylketonuria | `7df60135` | `16021003` Artefact due to freezing | Artefact | off_domain, parents_unrelated | 2 |
|  | Hypogonadism or delayed puberty | `ed85f8c4` | `770941005` Alopecia, progressive neurological defect, endocrinopathy syndrome | Developmental hereditary disorder; Genetic intellectual disability | off_domain, parents_unrelated | 2 |
|  | Infection suspected or proven to be due to a susceptible organism | `9948374c` | `1296950006` Fear of own body smell | Fear of body smell | off_domain, parents_unrelated | 2 |
|  | Infection where positive bacteriological evidence confirms that this antibiotic is an appropriate therapeutic agent | `521c10d3` | `1149448005` AAP/EFP 2017 Classification of Periodontal and Peri‐implant Diseases and Conditions generalised periodontitis Stage 4 Grade C | Generalised periodontitis | off_domain, parents_unrelated | 0 |
|  | Infection where resistance to amoxicillin is suspected | `90543967` | `1231176005` Congenital fistula of commissure of lips | Congenital fistula of lip | off_domain, parents_unrelated | 2 |
|  | Infections where resistance to amoxicillin is proven | `a9b771b9` | `1231176005` Congenital fistula of commissure of lips | Congenital fistula of lip | off_domain, parents_unrelated | 2 |
|  | Intractable focal onset seizures | `48be15b6` | `770431001` GRIN2A developmental and epileptic encephalopathy | Abnormal nervous system function; Autosomal dominant hereditary disorder | off_domain, parents_unrelated | 0 |
|  | Invasive fungal infections including both yeasts and moulds | `e334dc2a` | `1234831009` MIRAGE syndrome | Adrenogenital disorder; Autosomal dominant hereditary disorder | off_domain, parents_unrelated | 2 |
|  | Migraine attack | `fd2d2e81` | `1197429000` Cathepsin A-related arteriopathy, strokes, leukoencephalopathy | Autosomal dominant hereditary disorder; Cardiovascular system hereditary disorder | off_domain, parents_unrelated | 0 |
|  | Pathological hypersecretory conditions including Zollinger-Ellison syndrome and idiopathic hypersecretion | `ecd58ed2` | `1366188001` Vascular Ehlers-Danlos, polymicrogyria syndrome | Cardiovascular system hereditary disorder; Ehlers-Danlos syndrome | off_domain, parents_unrelated | 1 |
|  | Patients requiring doses greater than 20 mg per week | `28759593` | `725286002` HMG-CoA synthase deficiency | Autosomal recessive hereditary disorder; Disorder of fatty acid metabolism | off_domain, parents_unrelated | 0 |
|  | Phobic disorders | `e3f313b6` | `386808001` Phobia | Fear | off_domain, parents_unrelated | 0 |
|  | Short stature and slow growth | `d7af4a15` | `726081005` Hereditary hypophosphataemic rickets with hypercalciuria | Autosomal recessive hypophosphataemic bone disease; Hereditary disorder of the urinary system | off_domain, parents_unrelated | 1 |
|  | Stage IIIB/ IIIC or Stage IV non-small cell lung cancer | `c16d8d28` | `1269223003` Paraneoplastic uveitis | Paraneoplastic syndrome; Uveitis | off_domain, parents_unrelated | 1 |
|  | Supra-ventricular cardiac arrhythmias | `def340d4` | `766883006` Familial dilated cardiomyopathy with conduction defect due to lamin A/C mutation | Autosomal dominant hereditary disorder; Cardiovascular system hereditary disorder | off_domain, parents_unrelated | 0 |
|  | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour or extra-pancreatic neuroendocrine tumour | `574a0d9c` | `768937006` Extragonadal teratoma | Teratoma | off_domain, parents_unrelated | 1 |
|  | Whipworm infestation | `6bb6e440` | `3752003` Trichuriasis | Disease caused by Trichinelloidea; Intestinal nematode infection | off_domain, parents_unrelated | 0 |

## C. Reject on hierarchy — parents unrelated

*60 rows — confirm the rejection.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | A patient identifying as Aboriginal or Torres Strait Islander | `bedd1e61` | `1200271000168100` Vaccination of Aboriginal or Torres Strait Islander person | Active immunisation | parents_unrelated | 0 |
|  | Adenocarcinoma of the stomach | `8249fabe` | `771474005` Gastric adenocarcinoma and proximal polyposis of stomach | Autosomal dominant hereditary disorder; Digestive system hereditary disorder | parents_unrelated, narrower | 0 |
|  | Analgesia or fever | `3103f983` | `240453002` Oroya fever | Haemolytic anaemia caused by Bartonella; Infection caused by Bartonella bacilliformis | parents_unrelated, narrower | 2 |
|  | Androgenisation | `b363e519` | `131061007` Abnormal androgen | Hormone abnormality | parents_unrelated, narrower | 2 |
|  | CD30 positive Hodgkin lymphoma | `844908e0` | `702785000` Large cell anaplastic lymphoma T cell and null cell type | Mature T-cell AND/OR natural killer cell neoplasm | parents_unrelated | 2 |
|  | Cholangiocarcinoma | `9aa17302` | `1290690001` Metastatic cholangiocarcinoma | Malignant adenomatous neoplasm; Metastatic malignant neoplasm | parents_unrelated, narrower | 2 |
|  | Combined deficiency of human growth hormone and gonadotrophins | `f18a4fdd` | `22063003` Isolated deficiency of hormone other than HGH (human growth hormone) | Disorder of endocrine system | parents_unrelated | 2 |
|  | Cows' milk protein enteropathy | `9c676b29` | `141001000119104` Milk protein enteropathy | Intestinal disease | parents_unrelated | 2 |
|  | Cystic fibrosis - one residual function mutation | `bec5858d` | `441520002` Carrier of cystic fibrosis gene mutation | Carrier of disorder | parents_unrelated | 2 |
|  | Definite | `f6c6dba4` | `609370009` Frankl behavioural rating definitely negative | Finding of Frankl behavioural rating scale | parents_unrelated, narrower | 2 |
|  | Disorders of erythropoiesis | `23abd730` | `61164006` Erythropoietic coproporphyria | Hereditary coproporphyria | parents_unrelated, narrower | 2 |
|  | Endogenous Cushing's syndrome | `459c9dbb` | `47270006` Cushing's syndrome | Disorder of adrenal gland | parents_unrelated, narrower | 2 |
|  | Eradication of Helicobacter pylori | `6da70f00` | `281897000` Helicobacter eradication therapy | Regimes and therapies | parents_unrelated, narrower | 2 |
|  | Erythrodermic stage III-IVa T4 M0 Cutaneous T-cell lymphoma | `2f01caf3` | `404114005` Erythrodermic mycosis fungoides | Mycosis fungoides | parents_unrelated | 2 |
|  | Established atherosclerotic cardiovascular disease with hypertriglyceridaemia | `6cc66a91` | `1156813002` Gaucher disease with ophthalmoplegia and cardiovascular calcification | Subacute neuronopathic Gaucher's disease | parents_unrelated | 2 |
|  | Fistulising Crohn disease | `7a0319e6` | `34000006` Crohn's disease | Inflammatory bowel disease | parents_unrelated, narrower | 2 |
|  | Focal onset seizures | `845992d6` | `1260117009` Combined focal and generalised epilepsy | Epilepsy | parents_unrelated | 2 |
|  | Gram-positive coccal infections | `6fe80687` | `194394004` Gram positive sepsis | Bacterial sepsis | parents_unrelated | 2 |
|  | Granulomata | `2965aff3` | `317226009` Granulocytosis | White blood cell disorder | parents_unrelated | 2 |
|  | Haemophilus influenzae type B | `e702edb0` | `1156927006` Haemophilus influenzae type b immune | Finding of immunity | parents_unrelated, narrower | 2 |
|  | HER2 positive breast cancer | `a84ec77d` | `878807001` HER2-positive gastric cancer | Malignant neoplasm of stomach | parents_unrelated, narrower | 2 |
|  | HER2-low breast cancer | `6990f544` | `1381317004` Human epidermal growth factor receptor 2 low | Human epidermal growth factor receptor 2 gene amplification detected | parents_unrelated | 2 |
|  | Hyperlipoproteinaemia type 1 | `cc4146bc` | `275598004` Hyperlipoproteinaemia, type I | Familial chylomicronemia syndrome | parents_unrelated | 0 |
|  | Hypothalamic-pituitary disease secondary to a structural lesion, with hypothalamic obesity driven growth | `66db1525` | `1255269005` Hypothalamic adipsic hypernatraemia syndrome | Adipsia; Chronic hypernatraemia | parents_unrelated | 0 |
|  | Hypsarrhythmia | `29756f13` | `442511009` Progressive encephalopathy with oedema, hypsarrhythmia and optic atrophy syndrome | Autosomal hereditary disorder; Hereditary degenerative disease of central nervous system | parents_unrelated, narrower | 2 |
|  | Hypsarrhythmia and/or infantile spasms | `fecfdc75` | `342291000119102` Infantile and/or juvenile cataract | Cataract | parents_unrelated | 2 |
|  | Idiopathic multicentric Castleman disease | `697c4535` | `1156805003` Multicentric Castleman disease | Angiofollicular lymph node hyperplasia | parents_unrelated, narrower | 2 |
|  | Inborn errors of protein metabolism | `fedaf2a3` | `13837003` Inborn errors of metabolism screen | Screening for disorder | parents_unrelated, narrower | 2 |
|  | Infantile spasms | `27e9e713` | `1340127006` Infantile epileptic spasms syndrome | Epilepsy; Neurodevelopmental disorder | parents_unrelated, narrower | 2 |
|  | Initial moderate to severe genital herpes | `e602e475` | `8771000119104` Bilateral moderate to severe visual impairment | Bilateral visual impairment | parents_unrelated | 2 |
|  | Intermediate | `18dc091e` | `432991000` Intermediate syndrome | Neurological disorder | parents_unrelated, narrower | 2 |
|  | Local intra-articular or peri-articular infiltration | `1c74d2e4` | `1781000032103` Internal fixation of intra-articular fracture of tibial articular surface of knee with repair or reconstruction of ligaments | Internal fixation of tibia; Operation on ligament | parents_unrelated | 2 |
|  | Moderately severe Alzheimer disease | `815307a7` | `26929004` Alzheimer's disease | Cerebral degeneration presenting primarily with dementia; Dementia | parents_unrelated | 2 |
|  | Myelodysplastic | `76bac0b7` | `109995007` Myelodysplastic syndrome | Malignant haematopoietic neoplasm; Myeloproliferative disorder | parents_unrelated, narrower | 2 |
|  | Myelodysplastic disorder | `b5fa3bd9` | `109995007` Myelodysplastic syndrome | Malignant haematopoietic neoplasm; Myeloproliferative disorder | parents_unrelated, narrower | 2 |
|  | Neurogenic urinary retention | `44b95ecf` | `267064002` Urinary retention | Disorder of bladder | parents_unrelated | 2 |
|  | Neuromyelitis optica spectrum disorder | `d1b91576` | `25044007` Neuromyelitis optica | Demyelination of spinal cord; Immune-mediated neuropathy | parents_unrelated | 2 |
|  | Oral | `ad0c8d0e` | `361274000` Oral apraxia | Apraxia of speech | parents_unrelated, narrower | 2 |
|  | Pathological hyperprolactinaemia | `b3dd104e` | `232128004` Pathological hypermetropia | Hypermetropia | parents_unrelated, narrower | 2 |
|  | Phobic | `32c915a1` | `386810004` Phobic disorder | Anxiety disorder; Phobia | parents_unrelated, narrower | 2 |
|  | Pneumocystis carinii pneumonia | `70c56e2f` | `415123009` Pneumocystis jirovecii immunofluorescence | Measurement of microbial antibody | parents_unrelated, narrower | 2 |
|  | Primary severe restless legs syndrome | `cdc4996e` | `32914008` Restless legs syndrome | Disorder of lower limb; Sleep related movement disorder | parents_unrelated | 2 |
|  | Progressive fibrosing Interstitial lung disease | `3f642f39` | `233703007` Interstitial lung disease | Disorder of connective tissue; Disorder of soft tissue of thoracic cavity | parents_unrelated | 2 |
|  | Proven | `287e6c9c` | `25950000` Disease, alleged but not proven | Clinical finding | parents_unrelated, narrower | 2 |
|  | Pyridoxine non-responsive homocystinuria | `18fb3ac1` | `191260004` Pyridoxine-responsive sideroblastic anaemia | Sideroblastic anaemia | parents_unrelated | 2 |
|  | Seizures | `f46089a7` | `407621003` Daily seizures | Epilepsy monitoring status | parents_unrelated, narrower | 2 |
|  | Seizures of the Lennox-Gastaut syndrome | `440537c0` | `230418006` Lennox-Gastaut syndrome | Developmental and epileptic encephalopathy | parents_unrelated, narrower | 2 |
|  | Solid tumours with confirmed neurotrophic tropomyosin receptor kinase gene fusion | `6f6641c6` | `786710002` Solid neoplasm with neurotrophic receptor tyrosine kinase gene fusion | Genetic disease; Malignant neoplastic disease | parents_unrelated | 1 |
|  | Staphylococcal infections | `e0b58357` | `56038003` Staphylococcal infection | Disease caused by Gram-positive coccus | parents_unrelated | 2 |
|  | Streptococcal infections | `1ac87006` | `85769006` Streptococcal infection | Disease caused by Gram-positive coccus | parents_unrelated | 2 |
|  | Tapeworm infestation | `ebb663ab` | `86133004` Tapeworm infection | Helminth infection | parents_unrelated, narrower | 2 |
|  | Tuberous sclerosis complex | `18d67d6d` | `7199000` Tuberous sclerosis syndrome | Autosomal dominant hereditary disorder; Disorder of the central nervous system | parents_unrelated, narrower | 2 |
|  | Tyrosinaemia | `bcf23c27` | `410056006` Tyrosinaemia type 1 | Autosomal recessive hereditary disorder; Clinical manifestation of enzyme deficiency | parents_unrelated, narrower | 2 |
|  | Untreated multiple myeloma | `7e0f7d00` | `109989006` Multiple myeloma | Malignant haematopoietic neoplasm; Plasma cell neoplasm | parents_unrelated | 2 |
|  | Urea cycle disorders | `656f9456` | `36444000` Disorder of the urea cycle metabolism | Disorder of amino acid and organic acid metabolism | parents_unrelated, narrower | 2 |
|  | Urothelial carcinoma | `1279fa81` | `1208459005` Micropapillary urothelial carcinoma | Malignant neoplastic disease | parents_unrelated, narrower | 2 |
|  | Use in a hospital | `6c1d7683` | `713835001` Declined consent for use of patient data in risk stratification for unplanned hospital admission | Consent status | parents_unrelated, narrower | 1 |
|  | Von Hippel-Lindau disease | `f97c7068` | `405835004` Von Hippel-Lindau disease mutation carrier detection test | Molecular genetic test | parents_unrelated, narrower | 1 |
|  | WHO Class III, IV or V lupus nephritis | `fd424b31` | `76521009` SLE glomerulonephritis syndrome, WHO class III | Focal AND segmental proliferative glomerulonephritis; SLE glomerulonephritis syndrome | parents_unrelated | 2 |
|  | Wounds | `31f61e01` | `284752001` Damaging own wounds | Deliberate self-harm | parents_unrelated, narrower | 2 |

## D. Wrong hierarchy — re-search as Procedure

*6 rows — re-search, do not bind.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Assisting autologous peripheral blood progenitor cell transplantation | `e94cd9f6` | `425983008` Autologous peripheral blood stem cell transplant | Autogenous transplant; Peripheral blood stem cell transplant | — | 2 |
|  | Assisting bone marrow transplantation | `7682b341` | `23719005` Bone marrow transplant | Haemopoietic stem cell transplant | — | 2 |
|  | Dietary management of conditions requiring a highly restrictive therapeutic diet | `6771bbe9` | `1362129009` Intermittent fasting | Fasting | off_domain, parents_unrelated | 0 |
|  | Patients requiring administration of fluorouracil by intravenous infusion | `11bf7f5f` | `116792006` Intravenous infusion of cytomegalovirus immunoglobulin | Administration of Cytomegalovirus immunoglobulin, human; Administration of immunoglobulin by intravenous route | — | 0 |
|  | Patients requiring administration of fluorouracil by intravenous injection | `a1579b02` | `1230099001` Preparation of injection for self administration by subject | Preparation for procedure | parents_unrelated | 1 |
|  | Stimulation of follicular development | `20f9ec6b` | `723544007` Trichodysplasia spinulosa caused by Polyomavirus | Disease caused by Polyomavirus; Hair follicle disorder | parent_better | 2 |

## E. Parent concept suggested instead

*14 rows — judge parent vs hit.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Bone or joint infection | `7978f7f9` | `1197494003` Hyaline fibromatosis syndrome | Benign neoplasm of bone; Fibromatosis | parent_better | 0 |
|  | Bronchospasm and dyspnoea associated with chronic obstructive pulmonary disease | `05e4a681` | `106001000119101` COPD co-occurrent with acute bronchitis | Acute bronchitis; Acute exacerbation of chronic obstructive airways disease | parent_better | 2 |
|  | Chronic severe atopic dermatitis | `ff832b02` | `1336113009` CADINS disease | Atopic dermatitis; Autosomal dominant hereditary disorder | parent_better | 0 |
|  | Chronic severe pain | `176246df` | `230648001` Abdominal cutaneous nerve entrapment syndrome | Abdominal wall pain; Chronic abdominal pain | parent_better | 2 |
|  | Chronic treatment of Acute Hepatic Porphyria | `02ea00b0` | `64081000` 5-aminolevulinic acid dehydratase deficiency | Autosomal recessive hereditary disorder; Congenital porphyria | parent_better | 2 |
|  | Fungal or yeast infection | `71ae167c` | `3218000` Mycosis | Infection | parent_better | 2 |
|  | High risk of unstable angina | `7e231b19` | `4557003` Preinfarction syndrome | Angina | parent_better | 2 |
|  | Hyperkinetic extrapyramidal disorders | `0d6d8652` | `406506008` Attention deficit hyperactivity disorder | Developmental mental disorder; Disorders of attention and motor control | parent_better | 2 |
|  | Labial herpes | `07ff938d` | `1475003` Cold sore | Infection of lip; Oral infection caused by herpes simplex virus | parent_better | 2 |
|  | Mycobacterium ulcerans infection | `a84eb61e` | `15845006` Buruli ulcer | Atypical mycobacterial infection; Cutaneous infectious disease caused by Mycobacteria | parent_better | 0 |
|  | Nausea or gastric stasis | `51096051` | `235675006` Gastroparesis syndrome | Dysmotility of stomach; Gastric motor function disorder | parent_better | 2 |
|  | Oesophageal cancer or gastro-oesophageal junction cancer | `e07d66ed` | `230314007` Sandifer syndrome | Gastro-oesophageal reflux disease; Intermittent torticollis | parent_better | 0 |
|  | Scleroderma oesophagus | `b067d670` | `31848007` CREST syndrome | Degenerative disorder of extremity; Disorder of digit | parent_better | 0 |
|  | Systemic light chain amyloidosis | `ff6ac794` | `23132008` AL amyloidosis | Amyloidosis; Light chain disease | parent_better | 2 |

## F. Hit is narrower than the condition

*93 rows — check it is not a sub-type.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Acute bacterial enterocolitis | `cdfa156e` | `236016008` Acute haemorrhagic enterocolitis | Acute gastrointestinal haemorrhage; Acute inflammatory disease | narrower | 2 |
|  | Acute lymphoblastic leukaemia | `39bc4109` | `277573001` Common acute lymphoblastic leukaemia | Precursor B-cell acute lymphoblastic leukaemia | narrower | 2 |
|  | Acute myelogenous leukaemia | `393be4eb` | `359640008` Acute myeloid leukaemia without maturation, FAB M1 | Acute myeloid leukaemia | narrower | 1 |
|  | Acute promyelocytic leukaemia | `5c0497a1` | `285769009` Acute promyelocytic leukaemia - hypogranular variant | Acute promyelocytic leukaemia, FAB M3 | narrower | 2 |
|  | Aggressive systemic mastocytosis with eosinophilia | `7ad14869` | `397008008` Aggressive lymphadenopathic mastocytosis with eosinophilia | Malignant mastocytosis; Neoplasm of lymph node | narrower | 2 |
|  | Anaemias associated with vitamin B12 deficiency | `60468ad3` | `191142007` Vitamin B12 deficiency anaemia due to malabsorption with proteinuria | Megaloblastic anaemia due to vitamin B>12< deficiency | narrower | 2 |
|  | Anaerobic infections | `f2adbb3b` | `264575002` Superadded anaerobic infection | Infection caused by anaerobic bacteria; Superimposed infection | narrower | 2 |
|  | Basal cell carcinoma | `abbb8735` | `402524007` Basal cell carcinoma - adamantinoid | Basal cell carcinoma of skin | narrower | 2 |
|  | Bone | `324ee8c1` | `409778008` Bone abscess | Abscess; Bone inflammatory disease | narrower | 2 |
|  | Bone metastases | `3a96f3fc` | `91281000119103` Metastatic adenocarcinoma to bone | Metastatic adenocarcinoma; Metastatic malignant neoplasm to bone | narrower | 2 |
|  | Bordetella pertussis | `53f24034` | `122206002` Bordetella pertussis culture | Bordetella culture | narrower | 2 |
|  | Cancer pain | `ba023699` | `879973007` Breakthrough cancer pain | Breakthrough pain; Pain due to neoplastic disease | narrower | 2 |
|  | Cardiac allograft rejection | `d851185d` | `233933006` Cardiac transplant rejection | Disorder of transplanted heart; Transplanted organ rejection | narrower | 2 |
|  | CD30 positive cutaneous T-cell lymphoma | `97515436` | `128875000` Primary cutaneous CD30+ large T-cell lymphoma | Large cell anaplastic lymphoma T cell and null cell type; Primary cutaneous large T-cell lymphoma | narrower | 0 |
|  | Chemotherapy-induced neutropenia | `60f4605a` | `276628009` Chloramphenicol-induced neutropenia | Neutropenia due to drug | narrower | 2 |
|  | Chronic asthma | `e8c13046` | `195949008` Chronic asthmatic bronchitis | Asthmatic bronchitis; Chronic bronchitis | narrower | 2 |
|  | Chronic gout | `082c55cb` | `73877009` Chronic tophaceous gout | Chronic metabolic disorder; Gouty tophus | narrower | 2 |
|  | Chronic hepatitis B infection | `d8c5114b` | `735451005` Chronic viral hepatitis D | Chronic viral hepatitis; Viral hepatitis D | narrower | 2 |
|  | Chronic hepatitis C infection | `3841a132` | `838377003` Chronic hepatitis C co-occurrent with human immunodeficiency virus infection | Chronic hepatitis C; HIV infection | narrower | 2 |
|  | Chronic kidney disease with Type 2 diabetes | `fc1c336c` | `771000119108` Chronic kidney disease due to type 2 diabetes | Chronic kidney disease; Renal disorder due to type 2 diabetes | narrower | 2 |
|  | Chronic neutropenia | `d60de373` | `234423001` Chronic benign neutropenia | Chronic disease of immune function; Neutropenic disorder | narrower | 2 |
|  | Chronic plaque psoriasis | `d2c1e82e` | `402307000` Chronic large plaque psoriasis | Plaque psoriasis | narrower | 2 |
|  | Chronic pouchitis | `f095de5d` | `1217704000` Chronic antibiotic-refractory pouchitis | Chronic digestive system disorder; Ileal pouchitis | narrower | 0 |
|  | Chronic stable atherosclerotic disease | `a77c192d` | `724441006` Non-atherosclerotic chronic arterial occlusive disease | Chronic disease of cardiovascular system; Peripheral arterial occlusive disease | narrower | 2 |
|  | Constitutional delay of growth | `c4790295` | `237813007` Constitutional delay of growth and puberty | Delayed puberty; Growth retardation | narrower | 0 |
|  | Constitutional delay of growth or puberty | `ae79998a` | `237813007` Constitutional delay of growth and puberty | Delayed puberty; Growth retardation | narrower | 2 |
|  | Constitutional delay of puberty | `a7ef936e` | `237813007` Constitutional delay of growth and puberty | Delayed puberty; Growth retardation | narrower | 0 |
|  | Corneal grafts | `26eb40f9` | `60656008` Corneal transplant | Eye transplant; Operative procedure on cornea | narrower | 2 |
|  | Corticosteroid-induced osteoporosis | `4e66a8bc` | `14651005` Drug-induced osteoporosis | Secondary osteoporosis | narrower | 2 |
|  | Cows' milk anaphylaxis | `07d0b021` | `241936009` Cow's milk protein-induced anaphylaxis | Allergic reaction to animal; Allergic reaction to chemical | narrower | 0 |
|  | Cystic fibrosis - homozygous for the F508del mutation | `46e6727b` | `1296528004` Cystic fibrosis due to homozygous deltaF508 mutation | Cystic fibrosis | narrower | 2 |
|  | Dermatophyte infection | `7e3447be` | `713734009` Infection caused by Dermatophyte co-occurrent with HIV infection | Dermatophytosis; HIV infection | narrower | 1 |
|  | Dynamic equinus foot deformity | `872e55b3` | `37718006` Acquired equinus deformity of foot | Acquired deformity of foot; Plantarflexion deformity of foot | narrower | 2 |
|  | Endometrial cancer | `e6bdc4b0` | `188192002` Malignant neoplasm of endometrium of corpus uteri | Malignant neoplasm of body of uterus; Neoplasm of endometrium | narrower | 0 |
|  | Epileptic seizures | `67766fcc` | `1366368009` Epileptic seizures induced by eating | Reflex seizures | narrower | 2 |
|  | Extensive-stage small cell lung cancer | `c991d753` | `683991000119103` Extensive stage primary small cell carcinoma of lung | Malignant neoplasm of lung parenchyma; Primary small cell carcinoma of lung | narrower | 2 |
|  | Eye inflammation | `a200fed6` | `1231722004` Inflammation of eyelid | Disorder of eyelid; Inflammation of specific body systems | narrower | 2 |
|  | Fallopian tube cancer | `50fc0336` | `48672005` Accessory fallopian tube | Congenital anomaly of fallopian tubes | narrower | 2 |
|  | Fat malabsorption | `3b04ebed` | `197494007` Intestinal malabsorption of fat | Intestinal malabsorption | narrower | 2 |
|  | Follicular B-cell non-Hodgkin's lymphoma | `48e04af0` | `109972003` Follicular non-Hodgkin's lymphoma, large cell | Follicular lymphoma | narrower | 2 |
|  | Functional carcinoid tumour | `31505c87` | `1287573002` Carcinoid tumour of bronchus | Malignant epithelial neoplasm of bronchus; Neuroendocrine neoplasm of bronchus | narrower | 2 |
|  | Fungal | `90512bea` | `372247004` Fungal arthritis | Fungal musculoskeletal infection; Infective arthritis | narrower | 2 |
|  | Genital herpes | `3590c7e0` | `33839006` Genital herpes simplex | Genital infection; Sexually transmissible infection caused by Herpes simplex virus | narrower | 2 |
|  | Grade II to IV acute graft versus host disease | `b3f42ea1` | `402355000` Acute graft-versus-host disease | Acute disease; Graft versus host disease | narrower | 2 |
|  | Hereditary transthyretin amyloidosis | `5d2ab2e1` | `1354544003` Hereditary ATTR amyloidosis | Autosomal dominant hereditary disorder; Hereditary amyloidosis | narrower | 1 |
|  | High-risk neuroblastoma | `cef2d989` | `169948004` High risk infant | Finding of increased risk level | narrower | 2 |
|  | Hodgkin lymphoma | `b623ac71` | `762690000` Classical Hodgkin lymphoma | Hodgkin's disease | narrower | 2 |
|  | Hormone sensitive carcinoma of the prostate | `db2d2a70` | `722103009` Hormone sensitive prostate cancer | Malignant neoplasm of prostate | narrower | 2 |
|  | Hypophosphataemic rickets | `171e8bb2` | `237889002` Autosomal dominant hypophosphataemic rickets | Arthropathy associated with another disorder; Autosomal dominant hypophosphataemic bone disease | narrower | 2 |
|  | Infertility | `ed777842` | `6738008` Female infertility | Disorder of female reproductive system; Female reproductive finding | narrower | 2 |
|  | Intractable childhood epilepsy | `ebe5286e` | `50866000` Childhood absence epilepsy | Idiopathic generalised epilepsy | narrower | 2 |
|  | Invasive mycosis infections | `9ab29757` | `1360080002` Invasive Scopulariopsis infection | Infection caused by Deuteromycetes; Invasive fungal infection | narrower | 0 |
|  | Leiomyosarcoma or liposarcoma | `af3e89b5` | `699355007` Leiomyosarcoma of orbit | Leiomyosarcoma; Sarcoma of orbit | narrower | 2 |
|  | Lymphoma | `10877b51` | `118617000` Burkitt's lymphoma | B-cell lymphoma | narrower | 2 |
|  | Malignant gastrointestinal stromal tumour | `3d697da2` | `16636051000119105` Primary malignant gastrointestinal stromal neoplasm of colon | Gastrointestinal stromal neoplasm of colon; Primary malignant mesenchymal neoplasm of colon | narrower | 2 |
|  | Malignant neoplasia | `f3bf03a9` | `94281000119101` Malignant multiple endocrine neoplasia type 2a | Multiple endocrine neoplasia, type 2 | narrower | 1 |
|  | Mycobacterium avium complex infection | `d3d09af2` | `186342000` Pulmonary Mycobacterium avium complex infection | Atypical mycobacterial infection of lung; Infection caused by Mycobacterium avium-intracellulare group | narrower | 2 |
|  | Myelodysplastic or myeloproliferative disorder | `c716493b` | `445738007` Myelodysplastic/myeloproliferative disease | Malignant haematopoietic neoplasm; Myeloproliferative disorder | narrower | 2 |
|  | Myoclonic epilepsy | `90177632` | `6204001` Juvenile myoclonic epilepsy | Idiopathic generalised epilepsy | narrower | 2 |
|  | Non-infectious uveitis | `b551484b` | `267619000` Non-infectious anterior uveitis | Anterior uveitis | narrower | 2 |
|  | Non-small cell lung cancer | `3347f0f5` | `723301009` Squamous non-small cell lung cancer | Non-small cell lung carcinoma | narrower | 2 |
|  | Opioid-induced constipation | `a8cd94fb` | `136801000119102` Therapeutic opioid induced constipation | Drug-induced constipation | narrower | 0 |
|  | Oral herpes | `27c1581f` | `235058001` Oral mucosal herpes | Infection of skin and/or mucous membrane caused by Herpes simplex virus; Oral infection caused by herpes simplex virus | narrower | 2 |
|  | Oral or labial herpes | `4a6b3b3c` | `235058001` Oral mucosal herpes | Infection of skin and/or mucous membrane caused by Herpes simplex virus; Oral infection caused by herpes simplex virus | narrower | 2 |
|  | Paediatric low grade glioma | `17fdbbb3` | `429408002` Low grade glioma of brain | Glioma of central nervous system; Neoplasm of brain | narrower | 2 |
|  | Pneumocystis jiroveci pneumonia | `34f17762` | `916081000168105` Pneumocystis jiroveci pneumonia prophylaxis | Administration of prophylactic antibiotic for respiratory infection; Pneumocystosis jirovecii pneumonia prophylaxis | narrower | 0 |
|  | Primary axillary hyperhidrosis | `9287aada` | `427794001` Primary focal hyperhidrosis | Localised hyperhidrosis | narrower | 2 |
|  | Primary hyperoxaluria type 1 | `e56fc382` | `734990008` Primary hyperoxaluria type III | Primary hyperoxaluria | narrower | 0 |
|  | Proliferative diabetic retinopathy and/or Diabetic macular oedema | `f390efcd` | `399862001` High risk proliferative retinopathy without macular oedema due to diabetes | High risk proliferative retinopathy due to diabetes | narrower | 2 |
|  | Pseudomonas aeruginosa infection | `a7cea46b` | `11218009` Infection caused by Pseudomonas aeruginosa | Bacterial infection caused by Pseudomonas | narrower | 2 |
|  | Renal allograft rejection | `4ac39c67` | `314002005` Corneal allograft rejection | Corneal graft disorder; Corneal graft rejection | narrower | 2 |
|  | Resected non-small cell lung cancer | `b6c93bf7` | `723301009` Squamous non-small cell lung cancer | Non-small cell lung carcinoma | narrower | 2 |
|  | SARS-CoV-2 infection | `3bcc4e98` | `1217296006` SARS-CoV-2 breakthrough infection | COVID-19; Infection following immunisation | narrower | 2 |
|  | Short stature associated with Turner syndrome | `0b877e07` | `205808005` Congenital malformation syndromes associated with short stature | Congenital malformation syndrome; Short stature disorder | narrower | 2 |
|  | Squamous cell cancer of the hypopharynx | `333884ee` | `1260021004` Adenoid squamous cell carcinoma of hypopharynx | Acantholytic squamous cell carcinoma; Malignant epithelial neoplasm of hypopharynx | narrower | 2 |
|  | Squamous cell cancer of the larynx | `8ae1f50c` | `405822008` Squamous cell carcinoma of larynx | Malignant neoplasm of larynx; Squamous cell carcinoma of head and/or neck | narrower | 2 |
|  | Squamous cell cancer of the oropharynx | `f61fc4d6` | `423464009` Squamous cell carcinoma of oropharynx | Malignant epithelial neoplasm of oropharynx; Squamous cell carcinoma of pharynx | narrower | 2 |
|  | Squamous cell carcinoma of the oral cavity | `efffd23d` | `733343005` Primary squamous cell carcinoma of oral cavity | Primary malignant neoplasm of oral cavity; Squamous cell carcinoma of mouth | narrower | 2 |
|  | Stage IV non-small cell lung cancer | `d8c72226` | `723301009` Squamous non-small cell lung cancer | Non-small cell lung carcinoma | narrower | 2 |
|  | Stage Parkinson disease | `c1ced39c` | `49049000` Parkinson's disease | Cerebral degeneration; Chronic brain syndrome | narrower | 2 |
|  | Stroke embolism | `7adaa70f` | `788881005` Cerebral ischaemic stroke due to aortic arch embolism | Embolic infarction; Embolic stroke | narrower | 2 |
|  | Subfoveal choroidal neovascularisation | `8ebcc881` | `75971007` Choroidal retinal neovascularisation | Disorder of choroid of eye; Disorder of ocular blood vessel | narrower | 2 |
|  | Suspected | `3130b1db` | `171399004` Examination for suspected neoplasm | Medical examination for suspected condition | narrower | 2 |
|  | Systemic embolism | `20031288` | `1382088008` Embolisation of portal-systemic shunt | Correction of portal-systemic shunt; Embolisation of abdominal vein | narrower | 2 |
|  | Terminal disease | `72c087c0` | `196977009` Crohn's disease of terminal ileum | Crohn's disease of ileum; Terminal ileitis | narrower | 2 |
|  | Terminal malignant neoplasia | `5f6d3a30` | `94281000119101` Malignant multiple endocrine neoplasia type 2a | Multiple endocrine neoplasia, type 2 | narrower | 2 |
|  | Transthyretin amyloid cardiomyopathy | `03a336dd` | `715655000` Transthyretin related familial amyloid cardiomyopathy | Cardiac familial non-neuropathic amyloidosis; Cardiovascular system hereditary disorder | narrower | 0 |
|  | Triple negative breast cancer | `0d044a4e` | `706970001` Triple negative malignant neoplasm of breast | Hormone receptor negative malignant neoplasm of breast; Human epidermal growth factor 2 negative carcinoma of breast | narrower | 2 |
|  | Triple-negative breast cancer | `461afe3d` | `706970001` Triple negative malignant neoplasm of breast | Hormone receptor negative malignant neoplasm of breast; Human epidermal growth factor 2 negative carcinoma of breast | narrower | 2 |
|  | Uveal melanoma | `8698602f` | `1197334002` Malignant melanoma of uveal tract | Malignant melanoma of eye; Neoplasm of uveal tract | narrower | 1 |
|  | Venous thromboembolism | `d0f013f9` | `1258883002` Thromboembolus of vein following surgical procedure | Postoperative complication; Thromboembolism of vein | narrower | 2 |
|  | Venous ulcer | `94b0e26b` | `1332169003` Venous ulcer of ankle | Ankle ulcer; Venous ulcer of lower limb | narrower | 2 |
|  | X-linked hypophosphataemia | `867e06c0` | `237655001` Hypoparathyroidism - X-linked | Hereditary disorder of endocrine system; Hypoparathyroidism | narrower | 2 |

## G. ⚠️ 'Plausible' — THIS TIER IS NOT SAFE

*128 rows — verify against the terminology.*

| decision | condition | sha | top hit | its parents | flags | other hits |
|---|---|---|---|---|---|---|
|  | Ablation of thyroid remnant tissue | `d185fd7e` | `56823000` Cervical thyroid remnant | Aberrant thyroid gland | — | 2 |
|  | Above pressure injury | `4b3cf98e` | `1163215007` Pressure injury | Injury of soft tissue; Lesion of soft tissue | — | 2 |
|  | Acute allergic reaction with anaphylaxis | `cdca2244` | `241929008` Acute allergic reaction | Acute disease; Allergic reaction | — | 2 |
|  | Acute severe generalised myasthenia gravis | `9237d1e1` | `718065008` Generalised severe aggressive periodontitis | Acute periodontitis; Generalised periodontitis | — | 2 |
|  | Acute severe ulcerative colitis | `936ae48a` | `128600008` Acute ulcerative colitis | Acute digestive system disorder; Acute inflammatory disease | — | 2 |
|  | Adenocarcinoma of the gastro-oesophageal junction | `75b89953` | `187734007` Malignant neoplasm of cardio-oesophageal junction of stomach | Malignant neoplasm of abdominal oesophagus; Malignant neoplasm of cardia of stomach | — | 2 |
|  | Adenocarcinoma of the pancreas | `ca83b742` | `700423003` Adenocarcinoma of pancreas | Malignant adenomatous neoplasm; Malignant neoplasm of pancreas | — | 2 |
|  | Adenocarcinoma of the stomach or gastro-oesophageal junction | `b3732f8f` | `187734007` Malignant neoplasm of cardio-oesophageal junction of stomach | Malignant neoplasm of abdominal oesophagus; Malignant neoplasm of cardia of stomach | — | 2 |
|  | Adjuvant management of breast cancer | `a02d720e` | `254837009` Malignant neoplasm of breast | Malignant neoplasm of thorax; Neoplasm of breast | — | 2 |
|  | Advanced, metastatic or recurrent endometrial carcinoma | `2cf0d5f6` | `1237490005` Metastatic carcinoma to genital organ | Malignant epithelial neoplasm; Metastatic malignant neoplasm to genital organ | — | 2 |
|  | Anorectal congenital abnormalities | `f01dae4e` | `276654001` Congenital anomaly | Congenital disease; Developmental disorder | — | 2 |
|  | Anti-neutrophil cytoplasmic autoantibody associated vasculitis | `713f9c18` | `866047004` Multiple mononeuropathy due to perinuclear antineutrophil cytoplasmic associated antibody associated vasculitis | Vasculitic mononeuritis multiplex; Vasculitic neuropathy | — | 2 |
|  | Antibiotic associated pseudomembranous colitis | `c9bf3264` | `397696004` Antibiotic enterocolitis | Drug-induced colitis; Enterocolitis | — | 2 |
|  | Anticipated emergency treatment of an acute attack of hereditary angioedema | `4fb58327` | `1230015008` Hereditary angioedema with C1Inh (C1 esterase inhibitor) deficiency | Hereditary angioedema | — | 0 |
|  | Anticipated premature ovarian failure | `fddff280` | `237788002` Premature ovarian insufficiency | Primary ovarian failure | — | 2 |
|  | Atypical mycobacterial infections | `2d8769d6` | `1279842008` Autosomal recessive mendelian susceptibility to mycobacterial disease due to partial JAK1 deficiency | Autosomal recessive hereditary disorder; Mendelian susceptibility to mycobacterial disease | — | 0 |
|  | Barcelona Clinic Liver Cancer Stage B or Stage C hepatocellular carcinoma | `f7128647` | `787091002` Adenocarcinoma of liver and intrahepatic biliary tract | Adenocarcinoma of liver; Malignant neoplasm of biliary tract | — | 2 |
|  | Blepharospasm or hemifacial spasm | `a7035176` | `13753008` Hemifacial spasm | Chronic disease of musculoskeletal system; Disorder of face | — | 2 |
|  | Bridging therapy for generalised myasthenia gravis | `7c98b7c1` | `31839002` Myasthenia gravis, adult form | Myasthenia gravis | — | 2 |
|  | Bulky or stage III or IV indolent non-Hodgkin's lymphoma | `62e6164b` | `726721002` Nodal marginal zone B-cell lymphoma | Marginal zone lymphoma | — | 2 |
|  | Bulky or Stage III/IV follicular lymphoma | `4067a8a0` | `1362026000` Nodal T-follicular helper cell lymphoma follicular type | T-cell lymphoma | — | 0 |
|  | Carcinoma of the prostate | `ad19690f` | `254900004` Carcinoma of prostate | Carcinoma of genital organ; Malignant neoplasm of prostate | — | 2 |
|  | Castration resistant metastatic carcinoma of the prostate | `64e3b0d1` | `1237422007` Metastatic carcinoma to prostate | Metastatic carcinoma to genital organ; Metastatic malignant neoplasm to prostate | — | 2 |
|  | Castration resistant non-metastatic carcinoma of the prostate | `75191576` | `1237422007` Metastatic carcinoma to prostate | Metastatic carcinoma to genital organ; Metastatic malignant neoplasm to prostate | — | 2 |
|  | Castration sensitive carcinoma of the prostate | `6fa7a94d` | `722103009` Hormone sensitive prostate cancer | Malignant neoplasm of prostate | — | 2 |
|  | CD30 positive peripheral T-cell lymphoma | `d80f4102` | `109977009` Peripheral T-cell lymphoma | Mature T-cell AND/OR natural killer cell neoplasm; T-cell lymphoma | — | 2 |
|  | CD30 positive peripheral T-cell lymphoma, non-cutaneous type | `91660d54` | `277613000` Cutaneous peripheral T-cell lymphoma | Peripheral T-cell lymphoma | — | 2 |
|  | CD30 positive systemic anaplastic large cell lymphoma | `ba635241` | `702785000` Large cell anaplastic lymphoma T cell and null cell type | Mature T-cell AND/OR natural killer cell neoplasm | — | 2 |
|  | Cerebrospinal fluid glucose transporter defect | `ae152e14` | `167740005` Cerebrospinal fluid glucose below reference range | CSF: glucose level - finding; Decreased glucose level | — | 2 |
|  | Chelation of elevated copper levels | `e1180969` | `737560000` Raised blood copper level | Blood copper abnormal; Heavy metal in blood specimen above reference range | — | 2 |
|  | Chemotherapy refractory Peripheral T-cell Lymphoma | `142bc250` | `109977009` Peripheral T-cell lymphoma | Mature T-cell AND/OR natural killer cell neoplasm; T-cell lymphoma | — | 2 |
|  | Chronic arthropathies | `520a1110` | `38850007` Chronic arthropathy | Arthropathy; Chronic disease of musculoskeletal system | — | 2 |
|  | Chronic cyclical neutropenia | `509d36e5` | `191347008` Cyclical neutropenia | Neutropenic disorder | — | 2 |
|  | Chronic eosinophilic leukaemia or Hypereosinophilic syndrome | `6b42869e` | `188733003` Chronic eosinophilic leukaemia | Chronic leukaemia; Chronic myeloproliferative disorder | — | 2 |
|  | Chronic iron overload | `9bd75dff` | `60737008` Iron overload | Disorder of iron metabolism; Mineral excess | — | 2 |
|  | Chronic liver failure with fat malabsorption | `ec7ff534` | `2053831000122108` Acute on chronic liver failure | Acute hepatic failure; Chronic hepatic failure | — | 2 |
|  | Chronic lymphocytic leukaemia or small lymphocytic lymphoma | `77d439e8` | `92814006` Chronic lymphocytic leukaemia | Lymphoid leukaemia | — | 1 |
|  | Chronic pulmonary histoplasmosis infection | `b014aafa` | `26427008` Chronic pulmonary histoplasmosis | Chronic infectious disease; Chronic lung disease | — | 2 |
|  | Chronic severe disabling pain | `1035ca48` | `82423001` Chronic pain | Pain | — | 2 |
|  | Chronic severe dry eye disease with keratitis | `8629a63f` | `785298001` Muscle eye brain disease with bilateral multicystic leukodystrophy | Congenital anomaly of eye; Congenital hereditary muscular dystrophy | — | 2 |
|  | Chronic stable plaque type psoriasis vulgaris | `eb0a1b63` | `402310007` Chronic stable plaque psoriasis | Plaque psoriasis | — | 2 |
|  | Chronic treatment of hereditary angioedema Types 1 or 2 | `c85e431d` | `234619000` Hereditary angioedema - type 1 | Angioedema due to disorder of kinin metabolism; Autosomal dominant hereditary disorder | — | 2 |
|  | Clear cell variant renal cell carcinoma | `cde254ef` | `254915003` Clear cell carcinoma of kidney | Malignant neoplasm of kidney parenchyma; Renal cell carcinoma | — | 2 |
|  | Clinically definite relapsing-remitting multiple sclerosis | `bc4ab6ee` | `426373005` Relapsing remitting multiple sclerosis | Multiple sclerosis | — | 2 |
|  | Combined immunoglobulin E mediated allergy to cows' milk protein and soy protein | `8ec2711d` | `1197205005` Combined immunodeficiency due to DOCK8 deficiency | Autosomal recessive hereditary disorder; Combined immunodeficiency disease | — | 2 |
|  | Cows' milk protein enteropathy and intolerance to soy protein | `5e91a6bf` | `773579007` Congenital chronic diarrhoea with protein-losing enteropathy | Chronic diarrhoea of infants AND/OR young children; Congenital disease | — | 2 |
|  | Cows' milk protein enteropathy with failure to thrive | `0cb55fe4` | `782555009` Cow's milk protein allergy | Allergy to cattle protein; Food allergy | — | 2 |
|  | Cryopyrin associated periodic syndromes | `64cd72a5` | `430079001` Cryopyrin associated periodic syndrome | Hereditary periodic fever | — | 2 |
|  | Differentiated thyroid cancer | `636b3e9b` | `786038001` Familial nonmedullary primary thyroid carcinoma | Familial neoplastic disease; Hereditary disorder of endocrine system | — | 0 |
|  | Disorders of keratinisation | `111fd669` | `277905003` Disorder of keratinisation | Abnormal keratinisation; Disorder of body system | — | 2 |
|  | Disseminated pulmonary histoplasmosis infection | `28226cd4` | `187054003` Pulmonary histoplasmosis | Fungal infection of lung; Histoplasmosis | — | 2 |
|  | Drug interactions occurring with all of the base-priced drugs | `7f969307` | `404204005` Drug interaction with drug | Medicine interaction | — | 2 |
|  | Elevated intra-ocular pressure | `eb61a01d` | `112222000` Raised intraocular pressure | Abnormal intraocular pressure | — | 2 |
|  | Enterokinase deficiency | `cd0a2b86` | `124498007` Deficiency of enteropeptidase | Specific enzyme deficiency | — | 1 |
|  | Enthesitis/spondylitis related juvenile idiopathic arthritis | `e7e75996` | `410801005` Juvenile idiopathic arthritis, enthesitis related arthritis | Enthesitis; Juvenile idiopathic arthritis | — | 2 |
|  | Epithelial ovarian, fallopian tube or primary peritoneal cancer | `03230a7a` | `716649003` Extraovarian primary peritoneal carcinoma | Primary malignant neoplasm of peritoneum | — | 2 |
|  | Established post-menopausal osteoporosis | `ea4c971d` | `32369003` Menopausal osteoporosis | Musculoskeletal disorder during menopause; Osteoporosis | — | 2 |
|  | Familial heterozygous hypercholesterolaemia | `1a9137db` | `238079002` Familial hypercholesterolaemia - heterozygous | Familial hypercholesterolaemia | — | 2 |
|  | Gastric and gastroesophageal junction adenocarcinoma | `95d3cdf4` | `771474005` Gastric adenocarcinoma and proximal polyposis of stomach | Autosomal dominant hereditary disorder; Digestive system hereditary disorder | — | 2 |
|  | Gastro-oesophageal cancer | `a134077b` | `363402007` Malignant neoplasm of oesophagus | Malignant neoplasm of digestive organ; Malignant neoplasm of upper gastrointestinal tract | — | 2 |
|  | Gastro-oesophageal junction cancer | `f6a79e30` | `187734007` Malignant neoplasm of cardio-oesophageal junction of stomach | Malignant neoplasm of abdominal oesophagus; Malignant neoplasm of cardia of stomach | — | 2 |
|  | Germ cell neoplasms | `0dc703db` | `402878003` Germ cell neoplasm | Neoplastic disease | — | 2 |
|  | Growth failure with primary insulin-like growth factor-1 deficiency | `cd4c163f` | `724385009` Growth delay due to insulin-like growth factor type 1 deficiency | Autosomal recessive hereditary disorder; Congenital disease | — | 2 |
|  | Gyrate atrophy of the choroid and retina | `e9976b3f` | `314467007` Gyrate atrophy | Chorioretinal atrophy; Clinical manifestation of enzyme deficiency | — | 2 |
|  | HER2 positive adenocarcinoma of the gastro-oesophageal junction | `49eb556c` | `187734007` Malignant neoplasm of cardio-oesophageal junction of stomach | Malignant neoplasm of abdominal oesophagus; Malignant neoplasm of cardia of stomach | — | 1 |
|  | HER2 positive adenocarcinoma of the stomach | `c63d998a` | `408647009` Adenocarcinoma of stomach | Malignant adenomatous neoplasm; Malignant neoplasm of stomach | — | 2 |
|  | Hereditary tyrosinaemia type 1 | `eef835db` | `410056006` Tyrosinaemia type 1 | Autosomal recessive hereditary disorder; Clinical manifestation of enzyme deficiency | — | 2 |
|  | High risk locally advanced carcinoma of the cervix | `5fe0fe87` | `773775004` High-grade neuroendocrine carcinoma of cervix uteri | Carcinoma of cervix; Neuroendocrine carcinoma | — | 2 |
|  | High risk of recurrence clear cell variant renal cell carcinoma | `39e33c2a` | `254915003` Clear cell carcinoma of kidney | Malignant neoplasm of kidney parenchyma; Renal cell carcinoma | — | 2 |
|  | Hyperphenylalaninaemia due to tetrahydrobiopterin deficiency | `7f0adb5e` | `68724006` Tetrahydrobiopterin synthesis defect | Autosomal recessive hereditary disorder; Disorder of tetrahydrobiopterin metabolism | — | 2 |
|  | Idiopathic generalised epilepsy with primary generalised tonic-clonic seizures | `cdc4ada6` | `230414008` Epilepsy with generalised tonic-clonic seizures alone | Idiopathic generalised epilepsy | — | 2 |
|  | Immunotherapy sensitive advanced or metastatic cancer | `67b65986` | `275266006` Metastasis to digestive organs | Malignant neoplasm of digestive organ; Metastatic malignant neoplasm | — | 2 |
|  | Intermediate or high risk of recurrence clear cell variant renal cell carcinoma | `bd3917e4` | `764961009` Hereditary primary clear cell renal cell carcinoma | Familial renal cell carcinoma; Primary clear cell carcinoma of kidney | — | 2 |
|  | Intermediate-1 risk myelofibrosis | `9c7da3f7` | `1363261009` Cytochrome P450 family 2 subfamily C member 9 *1/*11 intermediate metaboliser | CYP2C9 intermediate metaboliser | — | 2 |
|  | Intestinal malabsorption including short bowel syndrome | `7b480409` | `26629001` Short bowel syndrome | Disorder of small intestine; Malabsorption syndrome | — | 2 |
|  | Lichen planus hypertrophic | `b455d20a` | `68266006` Hypertrophic lichen planus | Lichen planus | — | 2 |
|  | Limited-stage small cell lung cancer | `b5c047db` | `723301009` Squamous non-small cell lung cancer | Non-small cell lung carcinoma | — | 2 |
|  | Locally advanced, metastatic or recurrent biliary tract cancer | `fe88e0bb` | `787091002` Adenocarcinoma of liver and intrahepatic biliary tract | Adenocarcinoma of liver; Malignant neoplasm of biliary tract | — | 0 |
|  | Long chain fatty acid oxidation disorders | `c52409e2` | `426387005` Long-chain fatty acid transport deficiency | Disorder of fatty acid metabolism; Metabolic disorder of transport | — | 2 |
|  | Major depressive disorders | `98d8dacb` | `370143000` Major depressive disorder | Depression | — | 2 |
|  | Medullary thyroid cancer | `0ac14a22` | `363478007` Malignant neoplasm of thyroid gland | Malignant neoplasm of endocrine gland; Malignant neoplasm of neck | — | 2 |
|  | Megaloblastic anaemias | `ab43da7e` | `53165003` Megaloblastic anaemia | Anaemia related to disturbed DNA synthesis; Macrocytic anaemia | — | 2 |
|  | Mycosis fungoides cutaneous T-cell lymphoma | `1005f00a` | `765328000` Classic mycosis fungoides | Mycosis fungoides | — | 0 |
|  | Non-familial hypercholesterolaemia | `6a02a8f0` | `398036000` Familial hypercholesterolaemia | Primary hypercholesterolaemia | — | 2 |
|  | Non-functional gastroenteropancreatic neuroendocrine tumour | `d25928ee` | `1208744003` Non-functioning neuroendocrine neoplasm of pancreas | Malignant epithelial neoplasm; Neuroendocrine neoplasm of pancreas | — | 2 |
|  | Non-infectious posterior segment uveitis | `7f7be7f7` | `870199008` Non-infectious posterior uveitis | Posterior uveitis | — | 0 |
|  | Obstructive hypertrophic cardiomyopathy | `c41b5b30` | `45227007` Hypertrophic obstructive cardiomyopathy | Hypertrophic cardiomyopathy; Left ventricular abnormality | — | 2 |
|  | Oesophageal candidiasis | `988c301b` | `20639004` Candidiasis of oesophagus | Disorder of oesophagus; Gastrointestinal candidiasis | — | 2 |
|  | Oropharyngeal candidiasis | `3c5e1025` | `1287345003` Candidiasis of oropharynx | Disorder of oropharynx; Infectious disease of digestive tract | — | 0 |
|  | Paediatric high grade glioma | `ce826433` | `369767007` High grade (lymphoma) | Histological grade finding | — | 2 |
|  | Patients unable to take a solid dose form of an ACE inhibitor | `6e8f69e2` | `1303415000` On maximum tolerated dose of angiotensin converting enzyme inhibitor therapy | On maximum tolerated dose | — | 1 |
|  | Peri-articular infiltration | `5970d537` | `231329004` Peribulbar infiltration | Ophthalmological infiltrations | — | 2 |
|  | Perichondritis of the pinna | `cc9eaa2f` | `34129005` Perichondritis of pinna | Disorder of pinna; Otitis | — | 2 |
|  | Peroxisomal biogenesis disorders | `90108b56` | `742876007` Peroxisome biogenesis disorder | Autosomal recessive hereditary disorder; Disorder of peroxisomal function | — | 2 |
|  | Phobic or anxiety states | `94f15d12` | `386810004` Phobic disorder | Anxiety disorder; Phobia | — | 2 |
|  | Preservation of bone mineral density | `757c3907` | `385342005` Bone density finding | Bone finding; Procedure related finding | — | 2 |
|  | Primary and relapsing superficial urothelial carcinoma of the bladder | `bb5a618b` | `1259712001` Primary plasmacytoid urothelial carcinoma of urinary bladder | Plasmacytoid urothelial carcinoma of urinary bladder; Primary transitional cell carcinoma of bladder | — | 1 |
|  | Primary peritoneal cancer | `00b2c064` | `363492001` Malignant neoplasm of peritoneum | Malignant neoplasm of connective tissue; Malignant neoplasm of soft tissue of abdomen | — | 2 |
|  | Probable invasive aspergillosis | `d6c27e8e` | `721798004` Invasive aspergillosis | Aspergillosis; Invasive fungal infection | — | 2 |
|  | Pruritus associated with chronic kidney disease | `f0f7551e` | `722150000` Chronic kidney disease due to systemic infection | Chronic kidney disease; Urinary complication | — | 2 |
|  | Reduction of breast cancer risk | `f693ac8b` | `866242004` At increased risk of malignant neoplasm of breast | At risk of malignancy | — | 2 |
|  | Rehydration in intestinal failure | `38ea958e` | `440295211000119108` Failure of intestine | Intestinal disease | — | 2 |
|  | Rejection in patients following organ or tissue transplantation | `d244c8a6` | `213148006` Transplanted organ rejection | Disorder affecting transplanted structure; Disorder following clinical procedure | — | 2 |
|  | Resected early stage non-small cell lung cancer | `1ae2d552` | `723301009` Squamous non-small cell lung cancer | Non-small cell lung carcinoma | — | 2 |
|  | Resected gastric and gastroesophageal junction adenocarcinoma | `a642edb2` | `771474005` Gastric adenocarcinoma and proximal polyposis of stomach | Autosomal dominant hereditary disorder; Digestive system hereditary disorder | — | 2 |
|  | Seizures associated with tuberous sclerosis complex | `a67f7956` | `698626001` Dementia associated with multiple sclerosis | Dementia associated with another disease | — | 2 |
|  | Short stature and poor body composition due to Prader-Willi syndrome | `bd5100a4` | `1229943004` SIM1-related Prader-Willi-like syndrome | Genetic syndromic childhood obesity; Prader-Willi-like syndrome | — | 2 |
|  | Short stature associated with biochemical growth hormone deficiency | `db727099` | `234533006` X-linked agammaglobulinaemia with growth hormone deficiency | Congenital agammaglobulinaemia; Developmental hereditary disorder | — | 2 |
|  | Short stature associated with chronic renal insufficiency | `1baa1558` | `205808005` Congenital malformation syndromes associated with short stature | Congenital malformation syndrome; Short stature disorder | — | 2 |
|  | Short stature due to short stature homeobox gene disorders | `fbb67308` | `763868006` Short stature homeobox related short stature | Congenital anomaly of skeletal bone; Congenital skeletal dysplasia | — | 2 |
|  | Soft tissue sarcoma | `6da20145` | `424952003` Sarcoma of soft tissue | Malignant neoplasm of soft tissue; Sarcoma | — | 2 |
|  | Spasticity of the lower limb following an acute event | `2fea8957` | `132111000119107` Acute deep venous thrombosis of lower limb due to and following coronary artery bypass grafting | Acute deep venous thrombosis of lower limb as complication of procedure; Complication of bypass graft | — | 2 |
|  | Spasticity of the upper limb | `5f460abe` | `783764008` Autosomal recessive spastic paraplegia type 56 | Autosomal recessive hereditary spastic paraplegia | — | 2 |
|  | Spasticity of the upper limb following an acute event | `10135c9c` | `134424008` Disorder due to and following burn of upper limb | Disorder due to and following burn; Disorder due to and following injury of upper limb | — | 2 |
|  | Squamous cell cancer of the larynx, oropharynx or hypopharynx | `d09db900` | `423464009` Squamous cell carcinoma of oropharynx | Malignant epithelial neoplasm of oropharynx; Squamous cell carcinoma of pharynx | — | 2 |
|  | Squamous cell carcinoma of the larynx | `f4a8bd39` | `405822008` Squamous cell carcinoma of larynx | Malignant neoplasm of larynx; Squamous cell carcinoma of head and/or neck | — | 2 |
|  | Squamous cell carcinoma of the oral cavity, pharynx or larynx | `5c795225` | `733343005` Primary squamous cell carcinoma of oral cavity | Primary malignant neoplasm of oral cavity; Squamous cell carcinoma of mouth | — | 2 |
|  | Squamous cell carcinoma of the pharynx | `499b2ccc` | `408649007` Squamous cell carcinoma of pharynx | Malignant epithelial neoplasm of pharynx; Squamous cell carcinoma of head and/or neck | — | 2 |
|  | Stroke or systemic embolism | `e44ce43a` | `48601000119107` Hemiplegia and/or hemiparesis following stroke | Late effect of nervous system injury; Paralytic syndrome on one side of the body | — | 2 |
|  | Suspected Plasmodium falciparum malaria | `2fb6999a` | `62676009` Falciparum malaria | Malaria | — | 2 |
|  | Treatment refractory generalised myasthenia gravis | `4cb7b572` | `770596007` Rippling muscle disease with myasthenia gravis | Myasthenia gravis; Rippling muscle disease | — | 2 |
|  | Type I, II or IIIa spinal muscular atrophy | `7ec88b14` | `128212001` Spinal muscular atrophy, type II | Spinal muscular atrophy | — | 2 |
|  | Type III Short bowel syndrome with intestinal failure | `f07b5cf5` | `716665002` Chronic failure of small intestine | Chronic digestive system disorder; Disorder of small intestine | — | 2 |
|  | Type IIIB/IIIC spinal muscular atrophy | `0628d0ef` | `128212001` Spinal muscular atrophy, type II | Spinal muscular atrophy | — | 2 |
|  | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour | `5db17516` | `1288045008` Well-differentiated neuroendocrine tumour | Malignant epithelial neoplasm; Neuroendocrine neoplasm, malignant | — | 2 |
|  | Use in patients receiving palliative care | `eec4b943` | `225967005` Self-care patient education | Patient education | — | 2 |
|  | Ventricular cardiac arrhythmias | `3c21b363` | `719823007` Ventricular extrasystoles with syncope, perodactyly and Robin sequence syndrome | Congenital abnormality of oral cavity; Congenital anomaly of digit | — | 2 |
|  | Vitamin B12 deficiencies other than pernicious anaemia | `51a53f7b` | `735452003` Hereditary vitamin B12 deficiency anaemia | Haemoglobin low; Hereditary disease | — | 2 |
