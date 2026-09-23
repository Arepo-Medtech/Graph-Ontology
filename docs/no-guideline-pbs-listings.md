# PBS conditions with no guideline — matched to their PBS listings

**Generated** by `scripts/no_guideline_pbs.py` from PBS schedule **4333** (PBS Public API v3) and the corpus on this branch. Full detail, including every PBS item code and restriction code, is in [`reference/no_guideline_pbs.json`](../reference/no_guideline_pbs.json).

| | |
|---|---:|
| conditions without a guideline | **493** |
| … matched to ≥1 current PBS restriction | **493** |
| … of which matched through a split parent | 57 |
| distinct PBS item codes covered | **3313** |
| restrictions by access | authority 1081 · streamlined 672 · restricted 289 |
| ⚠️ possible name-match misses (a guideline may already cover it) | 43 |

**How to read it.** *Without a guideline* is decided by `condition_guideline_tally.py`, which matches by name.
The **near-miss** column lists existing guidelines whose name tokens match regardless of order. Those rows may
already be covered and need a human look. **via parent** marks a split child whose PBS listing is its parent's
combined indication. Some splits are parsing fragments (e.g. *Definite*, *Bone*, *Fungal*) and are kept, flagged,
not silently dropped.

**Access:** A = authority required · S = streamlined authority · R = restricted benefit (counts of current restrictions).

| # | condition | restrictions (A/S/R) | drugs | PBS items | SNOMED | notes |
|---:|---|---|---|---:|---|---|
| 1 | Psoriatic arthritis | 76 (68/6/2) | Infliximab, Adalimumab, Secukinumab, Etanercept, Certolizumab pegol, Ustekinumab +8 | 72 | `156370009` |  |
| 2 | Juvenile idiopathic arthritis | 55 (48/7/0) | Adalimumab, Tocilizumab, Etanercept, Methotrexate, Tofacitinib | 115 | `410502007` |  |
| 3 | Ankylosing spondylitis | 49 (44/5/0) | Adalimumab, Infliximab, Etanercept, Certolizumab pegol, Secukinumab, Golimumab +4 | 64 | `9631008` |  |
| 4 | Multiple myeloma | 42 (28/13/1) | Lenalidomide, Pomalidomide, Daratumumab, Carfilzomib, Selinexor, Elranatamab +5 | 132 | `109989006` |  |
| 5 | Non-small cell lung cancer | 42 (22/20/0) | Atezolizumab, Erlotinib, Osimertinib, Afatinib, Crizotinib, Brigatinib +13 | 79 | `254637007` |  |
| 6 | Cystic fibrosis | 31 (20/11/0) | Ivacaftor, Lumacaftor with ivacaftor, Elexacaftor with tezacaftor and with ivacaftor, and ivacaftor, Vanzacaftor with tezacaftor and with deutivacaftor, Mannitol, Dornase alfa +1 | 47 | `190905008` |  |
| 7 | Breast cancer | 27 (18/3/6) | Abemaciclib, Medroxyprogesterone, Olaparib, Ribociclib, Exemestane, Tamoxifen +10 | 50 | `254837009` |  |
| 8 | Chronic Myeloid Leukaemia | 26 (16/10/0) | Dasatinib, Imatinib, Nilotinib, Asciminib, Ponatinib | 58 | `92818009` |  |
| 9 | Chronic lymphocytic leukaemia or small lymphocytic lymphoma | 26 (24/2/0) | Ibrutinib, Venetoclax, Acalabrutinib, Obinutuzumab, Idelalisib, Zanubrutinib | 42 | 2 candidates |  |
| 10 | Paroxysmal nocturnal haemoglobinuria | 26 (26/0/0) | Ravulizumab, Pegcetacoplan, Eculizumab, Iptacopan | 23 | `1963002` |  |
| 11 | Small lymphocytic lymphoma | 26 (24/2/0) | Ibrutinib, Venetoclax, Acalabrutinib, Obinutuzumab, Idelalisib, Zanubrutinib | 42 | `302841002` | via parent *Chronic lymphocytic leukaemia or small lymphocytic lymphoma* |
| 12 | Non-radiographic axial spondyloarthritis | 25 (25/0/0) | Certolizumab pegol, Golimumab, Secukinumab, Upadacitinib, Bimekizumab | 17 | `713777005` |  |
| 13 | Spinal muscular atrophy | 22 (22/0/0) | Onasemnogene abeparvovec, Risdiplam, Nusinersen | 79 | `5262007` |  |
| 14 | Hidradenitis suppurativa | 21 (20/1/0) | Adalimumab, Secukinumab, Bimekizumab | 30 | `59393003` |  |
| 15 | HER2 positive breast cancer | 20 (10/10/0) | Trastuzumab, Pertuzumab, Trastuzumab emtansine, Lapatinib, Trastuzumab deruxtecan, Paclitaxel, nanoparticle albumin-bound | 36 | 3 candidates |  |
| 16 | Acute Myeloid Leukaemia | 19 (16/3/0) | Azacitidine, Midostaurin, Gemtuzumab ozogamicin, Daunorubicin with cytarabine, Venetoclax, Decitabine with cedazuridine +1 | 29 | `91861009` |  |
| 17 | Diabetes mellitus type 2 | 19 (1/16/2) | Pioglitazone, Sitagliptin with metformin, Empagliflozin with metformin, Alogliptin with metformin, Linagliptin with metformin, Saxagliptin with metformin +13 | 100 | `44054006` | ⚠️ near-miss: `type-2-diabetes` |
| 18 | Chronic spasticity | 18 (1/16/1) | Baclofen, Dantrolene, Diazepam | 8 | 2 candidates |  |
| 19 | Short stature associated with biochemical growth hormone deficiency | 18 (18/0/0) | Somatropin, Somatrogon, Somapacitan | 77 | 3 candidates |  |
| 20 | Atypical haemolytic uraemic syndrome | 16 (16/0/0) | Ravulizumab, Eculizumab | 14 | `789660001` |  |
| 21 | Colorectal cancer | 16 (0/16/0) | Cetuximab, Panitumumab, Trifluridine with tipiracil, Encorafenib, Fruquintinib | 20 | `1286877004` | ⚠️ near-miss: `colorectal-cancer-family-history-screening`, `colorectal-cancer-population-screening`, `colorectal-cancer-prevention-and-management` |
| 22 | Pathological hyperprolactinaemia | 16 (0/0/16) | Cabergoline, Bromocriptine | 4 | 3 candidates |  |
| 23 | Acromegaly | 15 (4/9/2) | Octreotide, Lanreotide, Pegvisomant, Pasireotide, Bromocriptine | 40 | `74107003` |  |
| 24 | Acute lymphoblastic leukaemia | 15 (14/1/0) | Imatinib, Blinatumomab, Ponatinib, Inotuzumab ozogamicin, Dasatinib | 28 | 3 candidates |  |
| 25 | Systemic juvenile idiopathic arthritis | 15 (11/4/0) | Tocilizumab | 22 | `201796004` |  |
| 26 | Epithelial ovarian cancer | 14 (13/1/0) | Olaparib, Niraparib | 20 | 3 candidates | via parent *Epithelial ovarian, fallopian tube or primary peritoneal cancer* |
| 27 | Epithelial ovarian, fallopian tube or primary peritoneal cancer | 14 (13/1/0) | Olaparib, Niraparib | 20 | 3 candidates |  |
| 28 | Fallopian tube cancer | 14 (13/1/0) | Olaparib, Niraparib | 20 | 3 candidates | via parent *Epithelial ovarian, fallopian tube or primary peritoneal cancer* |
| 29 | Primary peritoneal cancer | 14 (13/1/0) | Olaparib, Niraparib | 20 | 3 candidates | via parent *Epithelial ovarian, fallopian tube or primary peritoneal cancer* |
| 30 | Clear cell variant renal cell carcinoma | 13 (3/10/0) | Sunitinib, Pazopanib, Everolimus, Axitinib, Sorafenib, Lenvatinib | 26 | 3 candidates |  |
| 31 | Short stature and slow growth | 13 (13/0/0) | Somatropin, Somatrogon, Somapacitan | 77 | 2 candidates |  |
| 32 | Thrombocytopenia | 12 (12/0/0) | Eltrombopag, Romiplostim, Avatrombopag | 10 | `302215000` | ⚠️ near-miss: `immune-thrombocytopenia-children` |
| 33 | Corticosteroid-responsive dermatoses | 11 (0/5/6) | Methylprednisolone, Betamethasone, Mometasone, Hydrocortisone, Clobetasol, Triamcinolone | 67 | — |  |
| 34 | Schizophrenia | 11 (0/11/0) | Clozapine, Olanzapine, Paliperidone, Risperidone, Aripiprazole, Quetiapine +6 | 98 | `58214004` |  |
| 35 | Short stature associated with chronic renal insufficiency | 11 (11/0/0) | Somatropin | 69 | 3 candidates |  |
| 36 | Barcelona Clinic Liver Cancer Stage B or Stage C hepatocellular carcinoma | 10 (0/10/0) | Atezolizumab, Durvalumab, Tremelimumab, Lenvatinib, Sorafenib | 16 | 3 candidates |  |
| 37 | Biochemical growth hormone deficiency and precocious puberty | 10 (10/0/0) | Somatropin | 69 | 3 candidates |  |
| 38 | Chronic treatment of hereditary angioedema Types 1 or 2 | 10 (10/0/0) | Garadacimab, Lanadelumab | 5 | 3 candidates | ⚠️ near-miss: `hereditary-angioedema-children` |
| 39 | Growth retardation secondary to an intracranial lesion, or cranial irradiation | 10 (10/0/0) | Somatropin | 69 | 3 candidates |  |
| 40 | Hypothalamic-pituitary disease secondary to a structural lesion, with hypothalamic obesity driven growth | 10 (10/0/0) | Somatropin | 69 | 1 candidates |  |
| 41 | Short stature associated with Turner syndrome | 10 (10/0/0) | Somatropin | 69 | 3 candidates |  |
| 42 | Short stature due to short stature homeobox gene disorders | 10 (10/0/0) | Somatropin | 69 | 3 candidates |  |
| 43 | Subfoveal choroidal neovascularisation | 10 (6/4/0) | Aflibercept, Ranibizumab, Faricimab, Brolucizumab | 29 | 3 candidates |  |
| 44 | Venous thromboembolism | 10 (0/10/0) | Rivaroxaban, Dabigatran etexilate, Apixaban, Fondaparinux | 21 | 3 candidates | ⚠️ near-miss: `venous-thromboembolism-prevention` |
| 45 | Bone metastases | 9 (0/8/1) | Denosumab, Pamidronic acid, Zoledronic acid, Ibandronic acid | 7 | 3 candidates |  |
| 46 | Chronic iron overload | 9 (3/6/0) | Deferasirox | 36 | 3 candidates |  |
| 47 | Eosinophilic oesophagitis | 9 (9/0/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Budesonide, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids | 16 | `235599003` |  |
| 48 | Functional carcinoid tumour | 9 (0/9/0) | Octreotide, Lanreotide | 24 | 3 candidates |  |
| 49 | Treatment refractory generalised myasthenia gravis | 9 (9/0/0) | Ravulizumab, Zilucoplan, Rozanolixizumab | 16 | 3 candidates |  |
| 50 | Androgen deficiency | 8 (8/0/0) | Testosterone | 9 | `38825009` |  |
| 51 | Chemotherapy-induced neutropenia | 8 (0/8/0) | Filgrastim, Lipegfilgrastim, Pegfilgrastim | 14 | 3 candidates |  |
| 52 | Chronic arthropathies | 8 (0/1/7) | Naproxen, Piroxicam, Paracetamol, Indometacin, Ibuprofen | 20 | 3 candidates |  |
| 53 | Cytomegalovirus infection and disease | 8 (0/8/0) | Valganciclovir, Maribavir, Ganciclovir, Valaciclovir | 11 | 1 candidates |  |
| 54 | Diffuse large B-cell lymphoma | 8 (6/2/0) | Epcoritamab, Glofitamab, Obinutuzumab | 14 | `109969005` |  |
| 55 | Fabry disease | 8 (8/0/0) | Pegunigalsidase alfa, Migalastat | 3 | `16652001` |  |
| 56 | Hyperphosphataemia | 8 (0/6/2) | Lanthanum, Calcium, Sevelamer, Sucroferric oxyhydroxide | 32 | `20165001` | ⚠️ near-miss: `hyperphosphataemia-children` |
| 57 | Infection | 8 (1/6/1) | Ciprofloxacin, Amoxicillin with clavulanic acid, Cefalexin, Amoxicillin, Roxithromycin, Vancomycin | 13 | `40733004` | ⚠️ near-miss: `bone-and-joint-infection-children`, `cerebral-palsy-chest-infection`, `urinary-tract-infection-children` |
| 58 | SARS-CoV-2 infection | 8 (0/8/0) | Molnupiravir, Nirmatrelvir and ritonavir | 2 | 3 candidates |  |
| 59 | Social anxiety disorder | 8 (0/0/8) | Escitalopram | 6 | `25501002` | ⚠️ near-miss: `anxiety-children` |
| 60 | A patient identifying as Aboriginal or Torres Strait Islander | 7 (0/0/7) | Paracetamol, Folic acid, Chloramphenicol, Glucose and ketone indicator-urine, Electrolyte replacement, oral, Aspirin +2 | 12 | 2 candidates |  |
| 61 | Castration resistant metastatic carcinoma of the prostate | 7 (6/1/0) | Olaparib, Talazoparib, Abiraterone, Cabazitaxel, Enzalutamide, Abiraterone and methylprednisolone +1 | 15 | 3 candidates |  |
| 62 | Malignant gastrointestinal stromal tumour | 7 (5/2/0) | Imatinib, Sunitinib, Ripretinib | 19 | 3 candidates |  |
| 63 | Renal allograft rejection | 7 (0/7/0) | Mycophenolic acid, Everolimus, Sirolimus | 26 | 3 candidates |  |
| 64 | Type IIIB/IIIC spinal muscular atrophy | 7 (7/0/0) | Risdiplam, Nusinersen | 12 | 3 candidates |  |
| 65 | Acute allergic reaction with anaphylaxis | 6 (6/0/0) | Adrenaline (epinephrine) | 7 | 3 candidates | ⚠️ near-miss: `acute-anaphylaxis`, `anaphylaxis-children` |
| 66 | Advanced, metastatic or recurrent endometrial carcinoma | 6 (0/6/0) | Dostarlimab, Durvalumab, Lenvatinib | 10 | 3 candidates |  |
| 67 | Chronic graft versus host disease | 6 (0/6/0) | Methoxsalen, Ruxolitinib | 6 | `402356004` |  |
| 68 | Follicular lymphoma | 6 (5/1/0) | Lenalidomide, Obinutuzumab, Tafasitamab, Bendamustine | 18 | `308121000` |  |
| 69 | Hereditary tyrosinaemia type 1 | 6 (6/0/0) | Nitisinone | 10 | 3 candidates |  |
| 70 | Human immunodeficiency virus infection | 6 (1/5/0) | Darunavir, Abacavir, Darunavir with cobicistat | 6 | `86406008` |  |
| 71 | Iron overload | 6 (0/6/0) | Deferiprone | 6 | `60737008` |  |
| 72 | Major depressive disorders | 6 (0/0/6) | Desvenlafaxine, Mirtazapine, Escitalopram, Citalopram, Venlafaxine, Fluvoxamine +6 | 64 | 3 candidates |  |
| 73 | Myelodysplastic syndrome | 6 (6/0/0) | Azacitidine, Lenalidomide, Decitabine with cedazuridine | 10 | `109995007` |  |
| 74 | Narcolepsy | 6 (6/0/0) | Armodafinil, Dexamfetamine, Modafinil | 5 | `60380001` |  |
| 75 | Phenylketonuria | 6 (0/0/6) | Amino acid formula with vitamins and minerals without phenylalanine, Glycomacropeptide and essential amino acids with vitamins and minerals, Glycomacropeptide formula with long chain polyunsaturated fatty acids and docosahexaenoic acid and low in phenylalanine, Amino acid formula with vitamins and minerals, low phenylalanine and supplemented with docosahexaenoic acid and arachidonic acid, Amino acid formula with vitamins, minerals and long chain polyunsaturated fatty acids without phenylalanine, Amino acid formula with fat, carbohydrate, vitamins, minerals and trace elements without phenylalanine +9 | 41 | `190687004` |  |
| 76 | Primary biliary cholangitis | 6 (3/3/0) | Ursodeoxycholic acid, Obeticholic acid, Elafibranor | 9 | `31712002` |  |
| 77 | Progressive familial intrahepatic cholestasis | 6 (6/0/0) | Odevixibat | 24 | `74162007` |  |
| 78 | Pseudomonas aeruginosa infection | 6 (0/5/1) | Tobramycin | 6 | 3 candidates |  |
| 79 | Scleroderma oesophagus | 6 (2/2/2) | Esomeprazole, Omeprazole, Lansoprazole, Pantoprazole, Rabeprazole | 34 | 1 candidates |  |
| 80 | Urea cycle disorders | 6 (0/2/4) | Arginine with carbohydrate, Citrulline, Sodium phenylbutyrate, Essential amino acids formula with vitamins and minerals, Essential amino acids formula with minerals and vitamin c, Citrulline with carbohydrate +1 | 9 | 3 candidates |  |
| 81 | Wounds | 6 (5/0/1) | Dressing-foam-silver, Dressing with silver, Dressing-foam-heavy exudate, Dressing hydrofibre with silver, Dressing alginate with silver (deep wound), Dressing-foam with silver and silicone +1 | 22 | 3 candidates | ⚠️ near-miss: `tetanus-prone-wounds` |
| 82 | Amyotrophic lateral sclerosis | 5 (5/0/0) | Riluzole, Edaravone | 6 | `86044005` |  |
| 83 | Basal cell carcinoma | 5 (5/0/0) | Vismodegib, Sonidegib | 2 | 3 candidates |  |
| 84 | Branch retinal vein occlusion with macular oedema | 5 (3/2/0) | Aflibercept, Ranibizumab, Faricimab, Dexamethasone | 16 | `232048009` |  |
| 85 | Carcinoma of the prostate | 5 (0/1/4) | Leuprorelin, Leuprorelin and bicalutamide, Triptorelin, Goserelin and bicalutamide, Goserelin, Degarelix +2 | 23 | 3 candidates |  |
| 86 | Central retinal vein occlusion with macular oedema | 5 (3/2/0) | Aflibercept, Ranibizumab, Faricimab, Dexamethasone | 16 | `232039004` |  |
| 87 | Deep vein thrombosis | 5 (0/5/0) | Rivaroxaban, Apixaban | 7 | `128053003` |  |
| 88 | Diabetic macular oedema | 5 (2/3/0) | Aflibercept, Faricimab, Dexamethasone | 16 | `312912001` |  |
| 89 | Mycobacterium avium complex infection | 5 (0/5/0) | Azithromycin, Rifabutin | 4 | 3 candidates |  |
| 90 | Non-functional gastroenteropancreatic neuroendocrine tumour | 5 (0/5/0) | Lanreotide, Octreotide | 6 | 3 candidates |  |
| 91 | Non-infectious uveitis | 5 (4/1/0) | Adalimumab | 23 | 3 candidates |  |
| 92 | Panic disorder | 5 (1/0/4) | Sertraline, Alprazolam, Paroxetine | 9 | `371631005` |  |
| 93 | Pulmonary embolism | 5 (0/5/0) | Rivaroxaban, Apixaban | 7 | `59282003` |  |
| 94 | Short stature and poor body composition due to Prader-Willi syndrome | 5 (5/0/0) | Somatropin | 33 | 3 candidates |  |
| 95 | Soft tissue sarcoma | 5 (0/5/0) | Pazopanib | 6 | 3 candidates |  |
| 96 | Staphylococcal infection | 5 (0/0/5) | Flucloxacillin, Dicloxacillin | 12 | `56038003` |  |
| 97 | Urothelial cancer | 5 (0/5/0) | Avelumab, Enfortumab vedotin | 8 | — |  |
| 98 | Vasoactive intestinal peptide secreting tumour | 5 (0/5/0) | Octreotide | 15 | `253005002` |  |
| 99 | Anorectal congenital abnormalities | 4 (0/0/4) | Bisacodyl, Sorbitol with sodium citrate dihydrate and sodium lauryl sulfoacetate | 8 | 3 candidates |  |
| 100 | Behavioural disturbances | 4 (1/3/0) | Risperidone | 10 | 3 candidates |  |
| 101 | Cardiac allograft rejection | 4 (0/4/0) | Everolimus, Mycophenolic acid | 14 | 3 candidates |  |
| 102 | Chronic Myelomonocytic Leukaemia | 4 (4/0/0) | Azacitidine, Decitabine with cedazuridine | 6 | `127225006` |  |
| 103 | Chronic pouchitis | 4 (4/0/0) | Vedolizumab | 2 | 1 candidates |  |
| 104 | Chronic spontaneous urticaria | 4 (2/2/0) | Omalizumab | 14 | `302162004` | ⚠️ near-miss: `urticaria-children` |
| 105 | Chylous ascites | 4 (0/2/2) | Triglycerides - medium chain, formula, Triglycerides, medium chain, Protein hydrolysate formula with medium chain triglycerides | 6 | `52985009` |  |
| 106 | Combined intolerance to cows' milk protein, soy protein and protein hydrolysate formulae | 4 (4/0/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids | 19 | — |  |
| 107 | Constitutional delay of growth | 4 (4/0/0) | Testosterone | 9 | 1 candidates | via parent *Constitutional delay of growth or puberty* |
| 108 | Constitutional delay of growth or puberty | 4 (4/0/0) | Testosterone | 9 | 3 candidates |  |
| 109 | Constitutional delay of puberty | 4 (4/0/0) | Testosterone | 9 | 1 candidates | via parent *Constitutional delay of growth or puberty* |
| 110 | Cows' milk protein enteropathy | 4 (4/0/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids | 19 | 3 candidates |  |
| 111 | Cows' milk protein enteropathy with failure to thrive | 4 (4/0/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids | 19 | 3 candidates |  |
| 112 | Cryptococcal meningitis | 4 (0/4/0) | Fluconazole | 4 | `14232007` |  |
| 113 | Detrusor overactivity | 4 (0/0/4) | Oxybutynin, Propantheline | 6 | `786460007` |  |
| 114 | Differentiated thyroid cancer | 4 (0/4/0) | Cabozantinib, Lenvatinib | 8 | `1255086008` |  |
| 115 | Enthesitis/spondylitis related juvenile idiopathic arthritis | 4 (3/1/0) | Adalimumab | 18 | 3 candidates |  |
| 116 | Erythrodermic stage III-IVa T4 M0 Cutaneous T-cell lymphoma | 4 (0/4/0) | Methoxsalen | 4 | 3 candidates |  |
| 117 | Faecal impaction | 4 (0/2/2) | Macrogol 3350 | 4 | `44635007` |  |
| 118 | Grade II to IV acute graft versus host disease | 4 (0/4/0) | Ruxolitinib | 8 | 3 candidates |  |
| 119 | Growth hormone deficiency | 4 (4/0/0) | Somatropin | 5 | `397827003` |  |
| 120 | Herpes zoster | 4 (0/4/0) | Famciclovir, Aciclovir, Valaciclovir | 4 | `4740000` | ⚠️ near-miss: `herpes-zoster-vaccination` |
| 121 | Hodgkin lymphoma | 4 (4/0/0) | Brentuximab vedotin | 8 | 3 candidates |  |
| 122 | Hypercalcaemia | 4 (1/2/1) | Sodium acid phosphate, Calcitonin salmon, Milk powder -- synthetic | 4 | `66931009` |  |
| 123 | Hypercalcaemia of malignancy | 4 (0/4/0) | Pamidronic acid, Zoledronic acid | 6 | `47709007` |  |
| 124 | Hypocalcaemia | 4 (0/2/2) | Calcium, Calcitriol | 6 | `5291005` | ⚠️ near-miss: `hypocalcaemia-children` |
| 125 | Idiopathic pulmonary fibrosis | 4 (4/0/0) | Nintedanib, Pirfenidone | 4 | `700250006` |  |
| 126 | Intestinal malabsorption including short bowel syndrome | 4 (3/1/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids, Protein hydrolysate formula with medium chain triglycerides | 11 | 3 candidates |  |
| 127 | Kaposi sarcoma | 4 (0/4/0) | Doxorubicin - pegylated liposomal | 2 | `109385007` |  |
| 128 | Megacolon | 4 (0/0/4) | Bisacodyl, Sorbitol with sodium citrate dihydrate and sodium lauryl sulfoacetate | 8 | `33995003` |  |
| 129 | Micropenis | 4 (4/0/0) | Testosterone | 9 | `34911001` |  |
| 130 | Pathological hypersecretory conditions including Zollinger-Ellison syndrome and idiopathic hypersecretion | 4 (2/2/0) | Esomeprazole | 8 | 2 candidates |  |
| 131 | Polycythemia vera | 4 (4/0/0) | Ruxolitinib | 4 | `109992005` |  |
| 132 | Pubertal induction | 4 (4/0/0) | Testosterone | 9 | — |  |
| 133 | Secondary hyperparathyroidism | 4 (1/3/0) | Cinacalcet | 15 | `91478007` |  |
| 134 | Solid tumours with confirmed neurotrophic tropomyosin receptor kinase gene fusion | 4 (4/0/0) | Larotrectinib | 12 | 2 candidates |  |
| 135 | Terminal malignant neoplasia | 4 (0/0/4) | Bisacodyl, Sorbitol with sodium citrate dihydrate and sodium lauryl sulfoacetate | 8 | 3 candidates |  |
| 136 | Transplant rejection | 4 (0/4/0) | Ciclosporin | 12 | `213148006` |  |
| 137 | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour | 4 (3/1/0) | Sunitinib, Everolimus | 12 | 3 candidates |  |
| 138 | Untreated multiple myeloma | 4 (4/0/0) | Daratumumab, Lenalidomide | 22 | 3 candidates |  |
| 139 | Zollinger-Ellison syndrome | 4 (0/2/2) | Omeprazole, Pantoprazole | 14 | `53132006` |  |
| 140 | Acute coronary syndrome | 3 (0/3/0) | Ticagrelor, Prasugrel | 4 | `394659003` |  |
| 141 | Acute promyelocytic leukaemia | 3 (0/3/0) | Arsenic | 4 | 3 candidates |  |
| 142 | Acute severe generalised myasthenia gravis | 3 (3/0/0) | Ravulizumab, Zilucoplan, Rozanolixizumab | 16 | 3 candidates |  |
| 143 | Adult-type IDH-mutant astrocytoma or oligodendroglioma | 3 (0/3/0) | Vorasidenib | 2 | 3 candidates |  |
| 144 | Anxiety | 3 (3/0/0) | Oxazepam, Diazepam | 6 | `48694002` | ⚠️ near-miss: `anxiety-children`, `generalised-anxiety-disorder` |
| 145 | Aplastic anaemia | 3 (3/0/0) | Eltrombopag | 12 | `306058006` | ⚠️ near-miss: `anaemia-children` |
| 146 | Bipolar I disorder | 3 (0/3/0) | Olanzapine, Quetiapine, Risperidone, Asenapine | 26 | `371596008` | ⚠️ near-miss: `bipolar-disorder` |
| 147 | Bridging therapy for generalised myasthenia gravis | 3 (3/0/0) | Ravulizumab, Zilucoplan, Rozanolixizumab | 16 | 3 candidates |  |
| 148 | Central precocious puberty | 3 (0/0/3) | Leuprorelin, Triptorelin | 4 | `237816004` |  |
| 149 | Chemotherapy refractory Peripheral T-cell Lymphoma | 3 (3/0/0) | Pralatrexate, Romidepsin | 8 | 3 candidates |  |
| 150 | Chronic bronchitis | 3 (0/0/3) | Doxycycline, Amoxicillin | 7 | `63480004` |  |
| 151 | Chronic lymphocytic leukaemia | 3 (2/1/0) | Obinutuzumab, Venetoclax | 4 | `92814006` |  |
| 152 | Chronic stable atherosclerotic disease | 3 (0/3/0) | Rivaroxaban | 3 | 3 candidates |  |
| 153 | Chylothorax | 3 (0/1/2) | Triglycerides - medium chain, formula, Triglycerides, medium chain | 5 | `83035003` |  |
| 154 | Cows' milk protein enteropathy and intolerance to soy protein | 3 (0/3/0) | Protein hydrolysate formula with medium chain triglycerides | 1 | 3 candidates |  |
| 155 | Depression | 3 (0/0/3) | Mianserin, Phenelzine | 5 | `35489007` |  |
| 156 | Dietary management of conditions requiring a highly restrictive therapeutic diet | 3 (0/0/3) | Vitamins, minerals and trace elements with carbohydrate, Vitamins, minerals and trace elements formula | 3 | 1 candidates |  |
| 157 | Dietary management of conditions requiring a source of medium chain triglycerides | 3 (0/0/3) | Triglycerides - medium chain, formula, Protein formula with carbohydrate, fat, vitamins and minerals | 6 | — |  |
| 158 | Elevated intra-ocular pressure | 3 (0/0/3) | Bimatoprost with timolol, Brinzolamide with brimonidine, Travoprost with timolol, Latanoprost with timolol, Dorzolamide with timolol, Brimonidine with timolol +1 | 24 | 3 candidates |  |
| 159 | Extensive-stage small cell lung cancer | 3 (0/3/0) | Atezolizumab, Durvalumab | 14 | 3 candidates |  |
| 160 | Fungal infection | 3 (1/2/0) | Fluconazole, Posaconazole | 5 | 3 candidates |  |
| 161 | High risk and intermediate-2 risk myelofibrosis | 3 (2/1/0) | Ruxolitinib, Momelotinib, Fedratinib | 16 | 2 candidates |  |
| 162 | Hyperlipoproteinaemia type 1 | 3 (0/1/2) | Triglycerides - medium chain, formula, Triglycerides, medium chain | 5 | 1 candidates |  |
| 163 | Hyperphenylalaninaemia due to phenylketonuria | 3 (3/0/0) | Sapropterin | 4 | 3 candidates |  |
| 164 | Hypophosphataemic rickets | 3 (0/3/0) | Calcitriol, Sodium acid phosphate | 4 | 3 candidates |  |
| 165 | Immunotherapy sensitive advanced or metastatic cancer | 3 (0/3/0) | Nivolumab, Ipilimumab, Pembrolizumab | 6 | 3 candidates |  |
| 166 | Infection where resistance to amoxicillin is suspected | 3 (0/0/3) | Amoxicillin with clavulanic acid | 8 | 3 candidates |  |
| 167 | Intermediate-1 risk myelofibrosis | 3 (2/1/0) | Ruxolitinib, Momelotinib, Fedratinib | 16 | 3 candidates |  |
| 168 | Labial herpes | 3 (0/3/0) | Famciclovir | 1 | 3 candidates | via parent *Oral or labial herpes* |
| 169 | Local intra-articular or peri-articular infiltration | 3 (0/0/3) | Methylprednisolone, Betamethasone, Triamcinolone | 6 | 1 candidates |  |
| 170 | Long chain fatty acid oxidation disorders | 3 (0/1/2) | Triglycerides - medium chain, formula, Triglycerides, medium chain | 5 | 3 candidates |  |
| 171 | Lupus nephritis | 3 (3/0/0) | Obinutuzumab | 4 | `68815009` |  |
| 172 | Mantle cell lymphoma | 3 (2/1/0) | Ibrutinib, Bendamustine, Zanubrutinib, Acalabrutinib | 8 | `443487006` |  |
| 173 | Maternal hyperphenylalaninaemia due to phenylketonuria | 3 (3/0/0) | Sapropterin | 3 | 3 candidates |  |
| 174 | Neurofibromatosis type 1 | 3 (3/0/0) | Selumetinib | 2 | `92824003` |  |
| 175 | Obesity | 3 (3/0/0) | Orlistat | 1 | `414916001` |  |
| 176 | Obsessive-compulsive disorder | 3 (0/0/3) | Fluvoxamine, Fluoxetine, Sertraline, Paroxetine, Clomipramine | 15 | `191736004` |  |
| 177 | Obstructive hypertrophic cardiomyopathy | 3 (3/0/0) | Mavacamten | 8 | 3 candidates |  |
| 178 | Oligodendroglioma | 3 (0/3/0) | Vorasidenib | 2 | `443936004` | via parent *Adult-type IDH-mutant astrocytoma or oligodendroglioma* |
| 179 | Oral | 3 (0/3/0) | Famciclovir | 1 | 3 candidates | via parent *Oral or labial herpes*; ⚠️ near-miss: `oral-hypoglycaemic-poisoning-children` |
| 180 | Oral herpes | 3 (0/3/0) | Famciclovir | 1 | 3 candidates | via parent *Oral or labial herpes* |
| 181 | Oral or labial herpes | 3 (0/3/0) | Famciclovir | 1 | 3 candidates |  |
| 182 | Osteomyelitis | 3 (0/3/0) | Cefalexin, Fusidic acid, Flucloxacillin, Dicloxacillin | 4 | `60168000` |  |
| 183 | Paediatric high grade glioma | 3 (3/0/0) | Dabrafenib, Trametinib | 9 | 3 candidates |  |
| 184 | Paediatric low grade glioma | 3 (3/0/0) | Dabrafenib, Trametinib | 6 | 3 candidates |  |
| 185 | Paget disease of bone | 3 (1/1/1) | Calcitonin salmon, Pamidronic acid, Risedronic acid, Zoledronic acid | 4 | `2089002` |  |
| 186 | Peri-articular infiltration | 3 (0/0/3) | Methylprednisolone, Betamethasone, Triamcinolone | 6 | 3 candidates | via parent *Local intra-articular or peri-articular infiltration* |
| 187 | Primary hyperoxaluria type 1 | 3 (3/0/0) | Lumasiran | 2 | 1 candidates |  |
| 188 | Pyridoxine non-responsive homocystinuria | 3 (0/0/3) | Amino acid formula with vitamins and minerals without methionine, Amino acid formula with fat, carbohydrate without methionine, Amino acid formula with vitamins and minerals without methionine and supplemented with arachidonic acid and docosahexaenoic acid | 8 | 3 candidates |  |
| 189 | Resected early stage non-small cell lung cancer | 3 (0/3/0) | Atezolizumab | 6 | 3 candidates |  |
| 190 | Squamous cell cancer of the hypopharynx | 3 (0/3/0) | Cetuximab | 4 | 3 candidates | via parent *Squamous cell cancer of the larynx, oropharynx or hypopharynx* |
| 191 | Squamous cell cancer of the larynx | 3 (0/3/0) | Cetuximab | 4 | 1 candidates | via parent *Squamous cell cancer of the larynx, oropharynx or hypopharynx* |
| 192 | Squamous cell cancer of the larynx, oropharynx or hypopharynx | 3 (0/3/0) | Cetuximab | 4 | 3 candidates |  |
| 193 | Squamous cell cancer of the oropharynx | 3 (0/3/0) | Cetuximab | 4 | 3 candidates | via parent *Squamous cell cancer of the larynx, oropharynx or hypopharynx* |
| 194 | Systemic light chain amyloidosis | 3 (2/0/1) | Daratumumab, Bortezomib | 6 | 3 candidates |  |
| 195 | Tumour-induced osteomalacia | 3 (3/0/0) | Burosumab | 6 | `392559009` |  |
| 196 | Type I, II or IIIa spinal muscular atrophy | 3 (3/0/0) | Risdiplam, Nusinersen | 6 | 3 candidates |  |
| 197 | Type III Short bowel syndrome with intestinal failure | 3 (3/0/0) | Teduglutide | 6 | 3 candidates |  |
| 198 | Urothelial carcinoma | 3 (0/3/0) | Nivolumab, Durvalumab | 4 | 3 candidates |  |
| 199 | Use in patients receiving palliative care | 3 (0/1/2) | Clonazepam, Metoclopramide, Haloperidol, Hyoscine | 8 | 3 candidates |  |
| 200 | Uveitis | 3 (0/0/3) | Prednisolone with phenylephrine, Betamethasone | 3 | `128473001` |  |
| 201 | Vitamin D-resistant rickets | 3 (0/3/0) | Calcitriol, Sodium acid phosphate | 4 | `82236004` |  |
| 202 | Achondroplasia | 2 (2/0/0) | Vosoritide | 3 | `86268005` |  |
| 203 | Adenocarcinoma of the gastro-oesophageal junction | 2 (0/2/0) | Trifluridine with tipiracil | 2 | 3 candidates | via parent *Adenocarcinoma of the stomach or gastro-oesophageal junction* |
| 204 | Adenocarcinoma of the stomach | 2 (0/2/0) | Trifluridine with tipiracil | 2 | 1 candidates | via parent *Adenocarcinoma of the stomach or gastro-oesophageal junction* |
| 205 | Adenocarcinoma of the stomach or gastro-oesophageal junction | 2 (0/2/0) | Trifluridine with tipiracil | 2 | 3 candidates |  |
| 206 | Adjuvant management of breast cancer | 2 (0/2/0) | Zoledronic acid | 2 | 3 candidates |  |
| 207 | Adverse effects occurring with all of the base-priced drugs | 2 (2/0/0) | Eprosartan | 2 | 1 candidates |  |
| 208 | Aggressive systemic mastocytosis with eosinophilia | 2 (1/1/0) | Imatinib | 8 | 3 candidates |  |
| 209 | Alcohol dependence | 2 (0/2/0) | Acamprosate, Naltrexone | 2 | `66590003` |  |
| 210 | Anaemia associated with intrinsic renal disease | 2 (0/2/0) | Darbepoetin alfa, Epoetin alfa, Epoetin lambda, Methoxy polyethylene glycol-epoetin beta | 80 | 3 candidates | ⚠️ near-miss: `anaemia-children` |
| 211 | Anaemias associated with vitamin B12 deficiency | 2 (0/0/2) | Hydroxocobalamin | 4 | 3 candidates |  |
| 212 | Analgesia | 2 (0/0/2) | Paracetamol | 3 | `38433004` | via parent *Analgesia or fever* |
| 213 | Analgesia or fever | 2 (0/0/2) | Paracetamol | 3 | 3 candidates |  |
| 214 | Androgenisation | 2 (0/2/0) | Cyproterone | 2 | 3 candidates |  |
| 215 | Antibiotic associated pseudomembranous colitis | 2 (2/0/0) | Vancomycin | 2 | 3 candidates |  |
| 216 | Anticipated emergency treatment of an acute attack of hereditary angioedema | 2 (2/0/0) | Icatibant | 1 | 1 candidates | ⚠️ near-miss: `hereditary-angioedema-children` |
| 217 | Assisting autologous peripheral blood progenitor cell transplantation | 2 (0/2/0) | Filgrastim | 10 | — |  |
| 218 | Assisting bone marrow transplantation | 2 (0/2/0) | Filgrastim | 10 | 3 candidates |  |
| 219 | Autosomal dominant polycystic kidney disease | 2 (1/1/0) | Tolvaptan | 10 | `765330003` |  |
| 220 | Bacterial keratitis | 2 (2/0/0) | Ciprofloxacin, Ofloxacin | 4 | `314557000` |  |
| 221 | Blepharospasm or hemifacial spasm | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex | 3 | 3 candidates |  |
| 222 | Bronchiectasis | 2 (0/0/2) | Doxycycline | 6 | `12295008` |  |
| 223 | Bronchospasm | 2 (0/1/1) | Terbutaline, Salbutamol | 2 | `4386001` |  |
| 224 | Bulky or Stage III/IV follicular lymphoma | 2 (2/0/0) | Obinutuzumab | 4 | 1 candidates |  |
| 225 | CD30 positive cutaneous T-cell lymphoma | 2 (2/0/0) | Brentuximab vedotin | 4 | 1 candidates |  |
| 226 | CD30 positive peripheral T-cell lymphoma | 2 (2/0/0) | Brentuximab vedotin | 4 | 3 candidates | via parent *CD30 positive peripheral T-cell lymphoma, non-cutaneous type* |
| 227 | CD30 positive peripheral T-cell lymphoma, non-cutaneous type | 2 (2/0/0) | Brentuximab vedotin | 4 | 3 candidates |  |
| 228 | CD30 positive systemic anaplastic large cell lymphoma | 2 (2/0/0) | Brentuximab vedotin | 4 | 3 candidates |  |
| 229 | Calcium malabsorption | 2 (0/0/2) | Calcium | 4 | — |  |
| 230 | Cellulitis | 2 (0/0/2) | Cefazolin | 2 | `128045006` | ⚠️ near-miss: `cellulitis-and-skin-infections-children`, `periorbital-and-orbital-cellulitis-children` |
| 231 | Cholangiocarcinoma | 2 (0/2/0) | Ivosidenib, Futibatinib | 2 | 3 candidates |  |
| 232 | Chronic cyclical neutropenia | 2 (0/2/0) | Filgrastim | 10 | 3 candidates |  |
| 233 | Chronic eosinophilic leukaemia | 2 (1/1/0) | Imatinib | 8 | `188733003` | via parent *Chronic eosinophilic leukaemia or Hypereosinophilic syndrome* |
| 234 | Chronic eosinophilic leukaemia or Hypereosinophilic syndrome | 2 (1/1/0) | Imatinib | 8 | 3 candidates |  |
| 235 | Chronic granulomatous disease | 2 (0/2/0) | Interferon gamma-1b | 2 | `387759001` |  |
| 236 | Chronic neutropenia | 2 (0/2/0) | Filgrastim | 10 | 3 candidates |  |
| 237 | Chronic renal failure | 2 (0/2/0) | Protein formula with vitamins and minerals, and low in potassium, phosphorus, calcium, chloride and vitamin A, Whey protein formula supplemented with amino acids, long chain polyunsaturated fatty acids, vitamins and minerals, and low in protein, phosphate, potassium and lactose, Whey protein formula supplemented with amino acids, vitamins and minerals, and low in protein, phosphate, potassium and lactose | 3 | `90688005` |  |
| 238 | Chronic severe dry eye disease with keratitis | 2 (2/0/0) | Ciclosporin | 2 | 3 candidates |  |
| 239 | Chronic sialorrhea | 2 (0/2/0) | IncobotulinumtoxinA | 2 | — |  |
| 240 | Chronic treatment of Acute Hepatic Porphyria | 2 (2/0/0) | Givosiran | 1 | 3 candidates |  |
| 241 | Congenital neutropenia | 2 (0/2/0) | Filgrastim | 10 | `89655007` |  |
| 242 | Cows' milk anaphylaxis | 2 (2/0/0) | Amino acid formula with fat, carbohydrate, vitamins, minerals, trace elements and medium chain triglycerides, Amino acids-synthetic, formula, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids and medium chain triglycerides, Amino acid synthetic formula supplemented with long chain polyunsaturated fatty acids, Amino acid formula supplemented with prebiotics, probiotics and long chain polyunsaturated fatty acids | 10 | 1 candidates | ⚠️ near-miss: `anaphylaxis-children` |
| 243 | Cranial diabetes insipidus | 2 (0/2/0) | Desmopressin | 4 | `45369008` | ⚠️ near-miss: `diabetes-insipidus-children` |
| 244 | Cutaneous T-cell lymphoma | 2 (2/0/0) | Mogamulizumab, Vorinostat | 6 | `400122007` |  |
| 245 | Cutaneous squamous cell carcinoma | 2 (2/0/0) | Cemiplimab | 4 | `254651007` |  |
| 246 | Cystic fibrosis - homozygous for the F508del mutation | 2 (2/0/0) | Tezacaftor with ivacaftor and ivacaftor | 2 | 3 candidates |  |
| 247 | Cystic fibrosis - one residual function mutation | 2 (2/0/0) | Tezacaftor with ivacaftor and ivacaftor | 2 | 3 candidates |  |
| 248 | Cytomegalovirus retinitis | 2 (0/2/0) | Valganciclovir, Ganciclovir | 3 | `22455005` |  |
| 249 | Dermatofibrosarcoma protuberans | 2 (1/1/0) | Imatinib | 10 | `276799004` |  |
| 250 | Dermatophyte infection | 2 (2/0/0) | Terbinafine | 1 | 2 candidates |  |
| 251 | Disorders of erythropoiesis | 2 (0/2/0) | Desferrioxamine | 4 | 3 candidates |  |
| 252 | Drug interactions expected to occur with all of the base-priced drugs | 2 (2/0/0) | Eprosartan | 2 | 3 candidates |  |
| 253 | Drug interactions occurring with all of the base-priced drugs | 2 (2/0/0) | Eprosartan | 2 | 3 candidates |  |
| 254 | Dynamic equinus foot deformity | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex, IncobotulinumtoxinA | 4 | 3 candidates |  |
| 255 | Endocarditis | 2 (0/0/2) | Vancomycin | 4 | `56819008` |  |
| 256 | Endogenous Cushing's syndrome | 2 (2/0/0) | Osilodrostat | 4 | 3 candidates |  |
| 257 | Endometrial cancer | 2 (0/0/2) | Medroxyprogesterone | 6 | 1 candidates |  |
| 258 | Facial lipoatrophy | 2 (2/0/0) | Poly-l-lactic acid | 2 | 1 candidates |  |
| 259 | Familial hypophosphataemia | 2 (0/2/0) | Sodium acid phosphate | 2 | `82236004` | ⚠️ near-miss: `hypophosphataemia-children` |
| 260 | Fat malabsorption | 2 (0/2/0) | Triglycerides, medium chain, Protein hydrolysate formula with medium chain triglycerides | 3 | 3 candidates |  |
| 261 | Fever | 2 (0/0/2) | Paracetamol | 3 | `386661006` | via parent *Analgesia or fever*; ⚠️ near-miss: `acute-rheumatic-fever-and-rhd`, `fever-and-petechiae-children`, `fever-in-returned-traveller-children` |
| 262 | Fibrodysplasia ossificans progressiva | 2 (1/1/0) | Palovarotene | 9 | `82725007` |  |
| 263 | Follicular B-cell non-Hodgkin's lymphoma | 2 (1/1/0) | Idelalisib | 4 | 3 candidates |  |
| 264 | Fungal | 2 (0/2/0) | Miconazole, Terbinafine | 5 | 3 candidates | via parent *Fungal or yeast infection* |
| 265 | Fungal or yeast infection | 2 (0/2/0) | Miconazole, Terbinafine | 5 | 3 candidates |  |
| 266 | Gastrointestinal stromal tumour | 2 (1/1/0) | Imatinib | 8 | `420120006` |  |
| 267 | Generalized convulsive status epilepticus | 2 (2/0/0) | Midazolam | 8 | `1299166008` |  |
| 268 | Giant cell arteritis | 2 (2/0/0) | Tocilizumab | 4 | `414341000` |  |
| 269 | Glioblastoma multiforme | 2 (0/0/2) | Temozolomide, Carmustine | 6 | `393563007` |  |
| 270 | Glutaric aciduria type 1 | 2 (0/0/2) | Amino acid formula with vitamins and minerals without lysine and low in tryptophan | 4 | `360416003` |  |
| 271 | Gonorrhoea | 2 (1/0/1) | Ciprofloxacin, Ceftriaxone | 2 | `15628003` | ⚠️ near-miss: `chlamydia-and-gonorrhoea` |
| 272 | Growth failure with primary insulin-like growth factor-1 deficiency | 2 (2/0/0) | Mecasermin | 1 | 3 candidates |  |
| 273 | HER2 positive adenocarcinoma of the gastro-oesophageal junction | 2 (0/2/0) | Trastuzumab | 4 | 1 candidates | via parent *HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction* |
| 274 | HER2 positive adenocarcinoma of the stomach | 2 (0/2/0) | Trastuzumab | 4 | 3 candidates | via parent *HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction* |
| 275 | HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction | 2 (0/2/0) | Trastuzumab | 4 | — |  |
| 276 | Hemifacial spasm | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex | 3 | `13753008` | via parent *Blepharospasm or hemifacial spasm* |
| 277 | Hereditary transthyretin amyloidosis | 2 (2/0/0) | Vutrisiran | 2 | 2 candidates |  |
| 278 | Herpes simplex keratitis | 2 (0/0/2) | Aciclovir | 2 | `9389005` |  |
| 279 | High risk locally advanced carcinoma of the cervix | 2 (0/2/0) | Pembrolizumab | 2 | 3 candidates |  |
| 280 | High-risk neuroblastoma | 2 (2/0/0) | Eflornithine | 4 | 3 candidates |  |
| 281 | Hypereosinophilic syndrome | 2 (1/1/0) | Imatinib | 8 | `393573009` | via parent *Chronic eosinophilic leukaemia or Hypereosinophilic syndrome* |
| 282 | Hyperkinetic extrapyramidal disorders | 2 (0/2/0) | Tetrabenazine | 2 | 3 candidates |  |
| 283 | Hyperphenylalaninaemia | 2 (2/0/0) | Sapropterin | 2 | `68528007` |  |
| 284 | Hyperphenylalaninaemia due to tetrahydrobiopterin deficiency | 2 (2/0/0) | Sapropterin | 2 | 3 candidates |  |
| 285 | Hypomagnesaemia | 2 (0/1/1) | Magnesium | 3 | `190855004` | ⚠️ near-miss: `hypomagnesaemia-children` |
| 286 | Hypoparathyroidism | 2 (0/2/0) | Calcitriol | 2 | `36976004` |  |
| 287 | Idiopathic menorrhagia | 2 (0/0/2) | Levonorgestrel | 1 | — |  |
| 288 | Idiopathic multicentric Castleman disease | 2 (2/0/0) | Siltuximab | 4 | 3 candidates |  |
| 289 | Infection where positive bacteriological evidence confirms that this antibiotic is an appropriate therapeutic agent | 2 (0/0/2) | Ceftriaxone, Tobramycin, Cefazolin | 8 | 1 candidates |  |
| 290 | Keloid | 2 (0/0/2) | Betamethasone, Triamcinolone | 4 | `33659008` |  |
| 291 | Leiomyosarcoma | 2 (0/2/0) | Trabectedin | 4 | `443719001` | via parent *Leiomyosarcoma or liposarcoma* |
| 292 | Leiomyosarcoma or liposarcoma | 2 (0/2/0) | Trabectedin | 4 | 3 candidates |  |
| 293 | Lichen planus hypertrophic | 2 (0/0/2) | Betamethasone, Triamcinolone | 4 | 3 candidates |  |
| 294 | Liposarcoma | 2 (0/2/0) | Eribulin | 2 | `254829001` |  |
| 295 | Malignant neoplasia | 2 (2/0/0) | Oxazepam, Temazepam, Nitrazepam | 4 | 2 candidates |  |
| 296 | Maple syrup urine disease | 2 (0/0/2) | Amino acid formula with vitamins and minerals without valine, leucine and isoleucine, Isoleucine with carbohydrate, Valine with carbohydrate, Amino acid formula without valine, leucine and isoleucine, Amino acid formula with fat, carbohydrate without valine, leucine and isoleucine, Amino acid formula with vitamins and minerals without valine, leucine, isoleucine and supplemented with arachidonic acid and docosahexaenoic acid | 15 | `27718001` |  |
| 297 | Medullary thyroid cancer | 2 (0/2/0) | Selpercatinib | 2 | 3 candidates |  |
| 298 | Megaloblastic anaemias | 2 (0/0/2) | Folinic acid | 2 | 3 candidates |  |
| 299 | Merkel Cell Carcinoma | 2 (0/2/0) | Avelumab | 4 | `253001006` |  |
| 300 | Methylmalonic acidaemia | 2 (0/0/2) | Amino acid formula with vitamins and minerals without methionine, threonine and valine and low in isoleucine | 4 | `42393006` |  |
| 301 | Mixed episodes | 2 (0/2/0) | Ziprasidone, Asenapine | 6 | 1 candidates | via parent *Acute mania or mixed episodes* |
| 302 | Mucositis | 2 (0/0/2) | Benzydamine | 2 | `95361005` |  |
| 303 | Mycosis fungoides cutaneous T-cell lymphoma | 2 (2/0/0) | Chlormethine | 1 | 1 candidates |  |
| 304 | Myelodysplastic | 2 (1/1/0) | Imatinib | 8 | 3 candidates | via parent *Myelodysplastic or myeloproliferative disorder* |
| 305 | Myelodysplastic disorder | 2 (1/1/0) | Imatinib | 8 | 3 candidates | via parent *Myelodysplastic or myeloproliferative disorder* |
| 306 | Myelodysplastic or myeloproliferative disorder | 2 (1/1/0) | Imatinib | 8 | 3 candidates |  |
| 307 | Myeloproliferative disorder | 2 (1/1/0) | Imatinib | 8 | `425333006` | via parent *Myelodysplastic or myeloproliferative disorder* |
| 308 | Nephrotic syndrome | 2 (0/2/0) | Ciclosporin | 10 | `52254009` | ⚠️ near-miss: `nephrotic-syndrome-children` |
| 309 | Neuromyelitis optica spectrum disorder | 2 (2/0/0) | Ravulizumab | 8 | 3 candidates |  |
| 310 | Pernicious anaemia | 2 (0/0/2) | Hydroxocobalamin | 4 | `84027009` | ⚠️ near-miss: `anaemia-children` |
| 311 | Pre-exposure prophylaxis against human immunodeficiency virus infection | 2 (0/0/2) | Tenofovir with emtricitabine | 6 | 3 candidates |  |
| 312 | Precursor B-cell acute lymphoblastic leukaemia | 2 (2/0/0) | Blinatumomab | 2 | `277572006` |  |
| 313 | Preservation of bone mineral density | 2 (2/0/0) | Risedronic acid, Alendronic acid with colecalciferol | 8 | 3 candidates |  |
| 314 | Preterm birth | 2 (0/2/0) | Progesterone | 2 | 3 candidates |  |
| 315 | Primary and relapsing superficial urothelial carcinoma of the bladder | 2 (0/0/2) | Mycobacterium bovis (Bacillus Calmette and Guerin), Tice strain, Mycobacterium bovis (Bacillus Calmette and Guerin (BCG)) Danish 1331 strain | 4 | 2 candidates |  |
| 316 | Primary axillary hyperhidrosis | 2 (0/2/0) | Botulinum toxin type A purified neurotoxin complex, Glycopyrronium | 2 | 3 candidates |  |
| 317 | Progressive fibrosing Interstitial lung disease | 2 (2/0/0) | Nintedanib | 2 | 3 candidates |  |
| 318 | Proliferative diabetic retinopathy and/or Diabetic macular oedema | 2 (1/1/0) | Ranibizumab | 4 | 3 candidates |  |
| 319 | Propionic acidaemia | 2 (0/0/2) | Amino acid formula with vitamins and minerals without methionine, threonine and valine and low in isoleucine | 4 | `69080001` |  |
| 320 | Proven | 2 (0/0/2) | Ceftriaxone, Cefazolin, Tobramycin | 8 | 3 candidates | via parent *Septicaemia, proven* |
| 321 | Reduction of breast cancer risk | 2 (0/0/2) | Tamoxifen | 2 | 3 candidates |  |
| 322 | Rejection in patients following organ or tissue transplantation | 2 (0/2/0) | Tacrolimus | 18 | 3 candidates |  |
| 323 | Renal cell carcinoma | 2 (0/2/0) | Cabozantinib | 6 | `702391001` |  |
| 324 | Septicaemia | 2 (0/0/2) | Ceftriaxone, Cefazolin, Tobramycin | 8 | 3 candidates | via parent *Septicaemia, proven* |
| 325 | Septicaemia, proven | 2 (0/0/2) | Ceftriaxone, Cefazolin, Tobramycin | 8 | — |  |
| 326 | Septicaemia, suspected | 2 (0/0/2) | Ceftriaxone, Cefazolin, Tobramycin | 8 | — |  |
| 327 | Solar keratosis | 2 (2/0/0) | Imiquimod, Diclofenac | 3 | `201101007` |  |
| 328 | Spasmodic torticollis | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, IncobotulinumtoxinA, Botulinum toxin type A purified neurotoxin complex | 4 | `74333002` |  |
| 329 | Spasticity of the lower limb following an acute event | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex | 3 | 3 candidates |  |
| 330 | Spasticity of the upper limb | 2 (0/2/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex, IncobotulinumtoxinA | 4 | 3 candidates |  |
| 331 | Stage IIIB/ IIIC or Stage IV non-small cell lung cancer | 2 (2/0/0) | Amivantamab | 4 | 2 candidates |  |
| 332 | Stage IV non-small cell lung cancer | 2 (2/0/0) | Amivantamab | 4 | 3 candidates | via parent *Stage IIIB/ IIIC or Stage IV non-small cell lung cancer* |
| 333 | Stimulation of follicular development | 2 (0/2/0) | Lutropin alfa, Follitropin alfa with lutropin alfa | 2 | 3 candidates |  |
| 334 | Strongyloidiasis | 2 (0/2/0) | Ivermectin, Albendazole | 2 | `1214006` |  |
| 335 | Superficial basal cell carcinoma | 2 (2/0/0) | Imiquimod | 3 | `403914000` |  |
| 336 | Suspected | 2 (0/0/2) | Ceftriaxone, Cefazolin, Tobramycin | 8 | 3 candidates | via parent *Septicaemia, suspected* |
| 337 | Suspected Plasmodium falciparum malaria | 2 (0/0/2) | Atovaquone with proguanil, Artemether with lumefantrine | 2 | 3 candidates | ⚠️ near-miss: `malaria-children` |
| 338 | Systemic embolism | 2 (0/2/0) | Rivaroxaban, Apixaban, Dabigatran etexilate | 16 | — | via parent *Stroke or systemic embolism* |
| 339 | Systemic lupus erythematosus | 2 (2/0/0) | Anifrolumab | 2 | `55464009` |  |
| 340 | Thiamine deficiency | 2 (0/2/0) | Thiamine | 2 | `399357009` |  |
| 341 | Thyroid cancer | 2 (0/2/0) | Liothyronine | 2 | `363478007` |  |
| 342 | Transthyretin amyloid cardiomyopathy | 2 (2/0/0) | Tafamidis | 1 | 1 candidates |  |
| 343 | Triple-negative breast cancer | 2 (0/2/0) | Sacituzumab govitecan | 4 | `706970001` |  |
| 344 | Tuberous sclerosis complex | 2 (1/1/0) | Everolimus | 6 | 3 candidates |  |
| 345 | Tyrosinaemia | 2 (0/0/2) | Amino acid formula with vitamins and minerals without phenylalanine and tyrosine, Glycomacropeptide and essential amino acids with vitamins and minerals, Glycomacropeptide and essential amino acid formula with vitamins, minerals, and low in tyrosine and phenylalanine, Amino acid formula with fat, carbohydrate, vitamins, minerals and trace elements without phenylalanine and tyrosine, Amino acid formula with fat, carbohydrate without phenylalanine and tyrosine, Amino acid formula with vitamins and minerals, without phenylalanine, tyrosine and supplemented with arachidonic acid and docosahexaenoic acid +1 | 13 | 3 candidates |  |
| 346 | Ulcerative proctitis | 2 (0/0/2) | Mesalazine | 4 | `10811000202109` |  |
| 347 | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour or extra-pancreatic neuroendocrine tumour | 2 (0/2/0) | Cabozantinib | 6 | 2 candidates |  |
| 348 | Urethritis | 2 (0/0/2) | Doxycycline, Azithromycin | 5 | `31822004` |  |
| 349 | Urothelial toxicity | 2 (0/0/2) | Mesna | 4 | — |  |
| 350 | Venous ulcer | 2 (0/0/2) | Bandage-compression | 1 | 3 candidates |  |
| 351 | Vitamin B12 deficiencies other than pernicious anaemia | 2 (0/0/2) | Hydroxocobalamin | 4 | 3 candidates | ⚠️ near-miss: `anaemia-children` |
| 352 | Von Hippel-Lindau disease | 2 (2/0/0) | Belzutifan | 1 | 1 candidates |  |
| 353 | WHO Class III, IV or V lupus nephritis | 2 (0/2/0) | Mycophenolic acid | 4 | 3 candidates |  |
| 354 | Waldenstrom macroglobulinaemia | 2 (2/0/0) | Zanubrutinib | 1 | `190818004` |  |
| 355 | X-linked hypophosphataemia | 2 (2/0/0) | Burosumab | 6 | 3 candidates | ⚠️ near-miss: `hypophosphataemia-children` |
| 356 | Yeast infection | 2 (0/2/0) | Miconazole, Terbinafine | 5 | — | via parent *Fungal or yeast infection* |
| 357 | Ablation of thyroid remnant tissue | 1 (0/0/1) | Thyrotropin alfa | 1 | 3 candidates |  |
| 358 | Above pressure injury | 1 (0/0/1) | Protein formula with arginine, vitamin C, vitamin E and zinc | 1 | 3 candidates |  |
| 359 | Acute bacterial enterocolitis | 1 (1/0/0) | Norfloxacin | 1 | 3 candidates |  |
| 360 | Acute myelogenous leukaemia | 1 (0/0/1) | Idarubicin | 2 | 2 candidates |  |
| 361 | Adenocarcinoma of the pancreas | 1 (0/1/0) | Paclitaxel, nanoparticle albumin-bound | 2 | 3 candidates |  |
| 362 | Alopecia areata | 1 (0/0/1) | Betamethasone, Triamcinolone | 2 | `68225006` |  |
| 363 | Anti-neutrophil cytoplasmic autoantibody associated vasculitis | 1 (1/0/0) | Avacopan | 1 | 3 candidates |  |
| 364 | Anticipated premature ovarian failure | 1 (0/0/1) | Goserelin | 1 | 3 candidates |  |
| 365 | Anxiety states | 1 (1/0/0) | Bromazepam, Flunitrazepam | 3 | — | via parent *Phobic or anxiety states*; ⚠️ near-miss: `anxiety-children` |
| 366 | Bacterial gastroenteritis | 1 (1/0/0) | Ciprofloxacin | 3 | `274080003` | ⚠️ near-miss: `gastroenteritis-children` |
| 367 | Biliary atresia | 1 (0/1/0) | Protein hydrolysate formula with medium chain triglycerides | 1 | `77480004` |  |
| 368 | Blepharospasm | 1 (0/1/0) | IncobotulinumtoxinA | 1 | `59026006` |  |
| 369 | Bone | 1 (1/0/0) | Ciprofloxacin | 3 | 3 candidates | via parent *Bone or joint infection*; ⚠️ near-miss: `bone-and-joint-infection-children` |
| 370 | Bone infection | 1 (1/0/0) | Ciprofloxacin | 3 | `111253001` | via parent *Bone or joint infection*; ⚠️ near-miss: `bone-and-joint-infection-children` |
| 371 | Bone or joint infection | 1 (1/0/0) | Ciprofloxacin | 3 | 1 candidates | ⚠️ near-miss: `bone-and-joint-infection-children` |
| 372 | Bulky or stage III or IV indolent non-Hodgkin's lymphoma | 1 (0/1/0) | Bendamustine | 2 | 3 candidates |  |
| 373 | CD30 positive Hodgkin lymphoma | 1 (1/0/0) | Brentuximab vedotin | 2 | 3 candidates |  |
| 374 | Castration resistant non-metastatic carcinoma of the prostate | 1 (1/0/0) | Darolutamide, Apalutamide, Enzalutamide | 3 | 3 candidates |  |
| 375 | Castration sensitive carcinoma of the prostate | 1 (1/0/0) | Apalutamide, Darolutamide, Abiraterone and methylprednisolone | 3 | 3 candidates |  |
| 376 | Cataplexy | 1 (0/0/1) | Clomipramine | 1 | `46263000` |  |
| 377 | Cerebrospinal fluid glucose transporter defect | 1 (0/1/0) | Triglycerides, medium chain | 2 | 3 candidates |  |
| 378 | Cervicitis | 1 (0/0/1) | Azithromycin | 1 | `37610005` |  |
| 379 | Chelation of elevated copper levels | 1 (1/0/0) | Trientine | 1 | 3 candidates |  |
| 380 | Chronic Breathlessness | 1 (0/0/1) | Morphine | 2 | — |  |
| 381 | Chronic discoid lupus erythematosus | 1 (0/0/1) | Betamethasone, Triamcinolone | 2 | `238927000` |  |
| 382 | Chronic liver failure with fat malabsorption | 1 (0/1/0) | Protein hydrolysate formula with medium chain triglycerides | 1 | 3 candidates |  |
| 383 | Chronic pulmonary histoplasmosis infection | 1 (0/1/0) | Itraconazole | 2 | 3 candidates |  |
| 384 | Chronic renal disease | 1 (0/1/0) | Magnesium | 1 | `709044004` |  |
| 385 | Combined deficiency of human growth hormone and gonadotrophins | 1 (0/0/1) | Chorionic gonadotrophin | 1 | 3 candidates |  |
| 386 | Community acquired pneumonia | 1 (0/1/0) | Amoxicillin | 1 | `385093006` | ⚠️ near-miss: `community-acquired-pneumonia-children` |
| 387 | Complicated urinary tract infection | 1 (1/0/0) | Norfloxacin | 1 | 1 candidates | ⚠️ near-miss: `urinary-tract-infection-children` |
| 388 | Corneal grafts | 1 (0/0/1) | Prednisolone with phenylephrine | 1 | 3 candidates |  |
| 389 | Coronary artery disease | 1 (0/1/0) | Bivalirudin | 1 | 3 candidates |  |
| 390 | Cryopyrin associated periodic syndromes | 1 (0/1/0) | Anakinra | 2 | 3 candidates |  |
| 391 | Definite | 1 (1/0/0) | Voriconazole | 3 | 3 candidates | via parent *Definite or probable invasive aspergillosis* |
| 392 | Definite aspergillosis | 1 (1/0/0) | Voriconazole | 3 | — | via parent *Definite or probable invasive aspergillosis* |
| 393 | Definite or probable invasive aspergillosis | 1 (1/0/0) | Voriconazole | 3 | — |  |
| 394 | Delayed puberty | 1 (0/0/1) | Chorionic gonadotrophin | 1 | `400003000` | via parent *Hypogonadism or delayed puberty* |
| 395 | Disorders of keratinisation | 1 (0/1/0) | Acitretin | 2 | 3 candidates |  |
| 396 | Disseminated pulmonary histoplasmosis infection | 1 (0/1/0) | Itraconazole | 2 | 3 candidates |  |
| 397 | Endophthalmitis | 1 (0/0/1) | Vancomycin | 2 | `1847009` |  |
| 398 | Enterokinase deficiency | 1 (0/1/0) | Protein hydrolysate formula with medium chain triglycerides | 1 | 2 candidates |  |
| 399 | Epididymo-orchitis | 1 (1/0/0) | Ciprofloxacin | 3 | 3 candidates |  |
| 400 | Eradication of Helicobacter pylori | 1 (0/0/1) | Esomeprazole and clarithromycin and amoxicillin | 2 | 3 candidates |  |
| 401 | Eye inflammation | 1 (0/0/1) | Prednisolone with phenylephrine | 1 | 3 candidates |  |
| 402 | Gastric and gastroesophageal junction adenocarcinoma | 1 (1/0/0) | Durvalumab | 2 | 3 candidates |  |
| 403 | Gastric stasis | 1 (0/1/0) | Metoclopramide | 1 | `235675006` | via parent *Nausea or gastric stasis* |
| 404 | Gastro-oesophageal cancer | 1 (0/1/0) | Tislelizumab | 2 | 3 candidates |  |
| 405 | Gastro-oesophageal junction cancer | 1 (1/0/0) | Nivolumab | 2 | 3 candidates | via parent *Oesophageal cancer or gastro-oesophageal junction cancer* |
| 406 | Germ cell neoplasms | 1 (0/0/1) | Bleomycin | 2 | 3 candidates |  |
| 407 | Giant cell tumour of bone | 1 (0/1/0) | Denosumab | 2 | `697970009` |  |
| 408 | Glycogen storage disease | 1 (0/0/1) | Amylopectin, modified long chain | 1 | `29633007` |  |
| 409 | Granulomata | 1 (0/0/1) | Betamethasone, Triamcinolone | 2 | 3 candidates |  |
| 410 | Gyrate atrophy of the choroid and retina | 1 (0/0/1) | Essential amino acids formula with vitamins and minerals, Essential amino acids formula with minerals and vitamin c, Essential amino acids formula | 3 | 3 candidates |  |
| 411 | HER2-low breast cancer | 1 (1/0/0) | Trastuzumab deruxtecan | 2 | 3 candidates |  |
| 412 | Haemodialysis | 1 (0/0/1) | Enoxaparin | 7 | 3 candidates |  |
| 413 | Hairy cell leukaemia | 1 (0/1/0) | Cladribine | 2 | `118613001` |  |
| 414 | Hepatic encephalopathy | 1 (1/0/0) | Rifaximin | 1 | `13920009` |  |
| 415 | High risk of recurrence clear cell variant renal cell carcinoma | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates | via parent *Intermediate or high risk of recurrence clear cell variant renal cell carcinoma* |
| 416 | Homocystinuria | 1 (1/0/0) | Betaine | 1 | `11282001` |  |
| 417 | Hookworm infestation | 1 (0/1/0) | Albendazole | 1 | 1 candidates |  |
| 418 | Hormone sensitive carcinoma of the prostate | 1 (1/0/0) | Enzalutamide | 1 | 3 candidates |  |
| 419 | Hydatid disease | 1 (0/1/0) | Albendazole | 1 | `74942003` |  |
| 420 | Hypogonadism | 1 (0/0/1) | Chorionic gonadotrophin | 1 | `48130008` | via parent *Hypogonadism or delayed puberty* |
| 421 | Hypogonadism or delayed puberty | 1 (0/0/1) | Chorionic gonadotrophin | 1 | 3 candidates |  |
| 422 | Hypsarrhythmia | 1 (0/0/1) | Tetracosactide | 1 | 3 candidates | via parent *Hypsarrhythmia and/or infantile spasms* |
| 423 | Inborn errors of protein metabolism | 1 (0/0/1) | Carbohydrate, fat, vitamins, minerals and trace elements and supplemented with arachidonic acid and docosahexaenoic acid, Triglycerides, medium chain and long chain with glucose polymer, Carbohydrate, fat, vitamins, minerals and trace elements, Triglycerides, long chain with glucose polymer | 4 | 3 candidates |  |
| 424 | Infection suspected or proven to be due to a susceptible organism | 1 (1/0/0) | Amoxicillin | 1 | 3 candidates |  |
| 425 | Intermediate | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates | via parent *Intermediate or high risk of recurrence clear cell variant renal cell carcinoma* |
| 426 | Intermediate or high risk of recurrence clear cell variant renal cell carcinoma | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates |  |
| 427 | Invasive aspergillosis | 1 (1/0/0) | Posaconazole | 1 | `721798004` |  |
| 428 | Isovaleric acidaemia | 1 (0/0/1) | Glycine with carbohydrate | 1 | `87827003` |  |
| 429 | Joint infection | 1 (1/0/0) | Ciprofloxacin | 3 | `363162000` | via parent *Bone or joint infection*; ⚠️ near-miss: `bone-and-joint-infection-children` |
| 430 | Lambert-Eaton myasthenic syndrome | 1 (1/0/0) | Amifampridine | 1 | `56989000` |  |
| 431 | Leprosy | 1 (1/0/0) | Rifampicin | 2 | `81004002` |  |
| 432 | Lichen simplex chronicus | 1 (0/0/1) | Betamethasone, Triamcinolone | 2 | `53891004` |  |
| 433 | Limited-stage small cell lung cancer | 1 (0/1/0) | Durvalumab | 2 | 3 candidates |  |
| 434 | Locally advanced, metastatic or recurrent biliary tract cancer | 1 (0/1/0) | Durvalumab | 2 | 1 candidates |  |
| 435 | Lymphoma | 1 (0/0/1) | Bleomycin | 2 | 3 candidates |  |
| 436 | Malaria | 1 (1/0/0) | Quinine | 1 | `61462000` | ⚠️ near-miss: `malaria-children` |
| 437 | Menorrhagia | 1 (0/0/1) | Mefenamic acid | 1 | `386692008` |  |
| 438 | Mycobacterium ulcerans infection | 1 (1/0/0) | Rifampicin | 4 | 1 candidates |  |
| 439 | Nasopharyngeal carcinoma | 1 (0/1/0) | Toripalimab | 2 | `449248000` |  |
| 440 | Nausea | 1 (0/1/0) | Metoclopramide | 1 | `422587007` | via parent *Nausea or gastric stasis* |
| 441 | Nausea or gastric stasis | 1 (0/1/0) | Metoclopramide | 1 | 3 candidates |  |
| 442 | Necrobiosis lipoidica | 1 (0/0/1) | Betamethasone, Triamcinolone | 2 | `9418005` |  |
| 443 | Neurogenic urinary retention | 1 (0/0/1) | Phenoxybenzamine | 2 | 3 candidates |  |
| 444 | Non-infectious posterior segment uveitis | 1 (1/0/0) | Dexamethasone | 1 | 1 candidates |  |
| 445 | Oesophageal cancer | 1 (1/0/0) | Nivolumab | 2 | `363402007` | via parent *Oesophageal cancer or gastro-oesophageal junction cancer* |
| 446 | Oesophageal cancer or gastro-oesophageal junction cancer | 1 (1/0/0) | Nivolumab | 2 | 1 candidates |  |
| 447 | Onchocerciasis | 1 (0/1/0) | Ivermectin | 1 | `38539003` |  |
| 448 | Painful mouth | 1 (0/1/0) | Benzydamine | 1 | `102616008` |  |
| 449 | Patients requiring administration of fluorouracil by intravenous infusion | 1 (0/0/1) | Fluorouracil | 2 | 1 candidates |  |
| 450 | Patients requiring administration of fluorouracil by intravenous injection | 1 (0/0/1) | Fluorouracil | 2 | 1 candidates |  |
| 451 | Patients requiring doses greater than 20 mg per week | 1 (0/0/1) | Methotrexate | 1 | 1 candidates |  |
| 452 | Patients unable to take a solid dose form of an ACE inhibitor | 1 (0/0/1) | Captopril | 1 | 2 candidates |  |
| 453 | Patients undergoing in-vitro fertilisation | 1 (0/0/1) | Clomifene | 1 | 3 candidates |  |
| 454 | Pelvic inflammatory disease | 1 (0/0/1) | Doxycycline | 3 | `198130006` |  |
| 455 | Peptic ulcer | 1 (0/1/0) | Omeprazole, Esomeprazole, Lansoprazole, Pantoprazole, Rabeprazole | 10 | `13200003` | ⚠️ near-miss: `peptic-ulcer-disease` |
| 456 | Perichondritis of the pinna | 1 (1/0/0) | Ciprofloxacin | 3 | 3 candidates |  |
| 457 | Peroxisomal biogenesis disorders | 1 (0/0/1) | Arachidonic acid and docosahexaenoic acid with carbohydrate | 1 | 3 candidates |  |
| 458 | Phaeochromocytoma | 1 (0/0/1) | Phenoxybenzamine | 2 | `302835009` |  |
| 459 | Phobic | 1 (1/0/0) | Bromazepam, Flunitrazepam | 3 | 3 candidates | via parent *Phobic or anxiety states* |
| 460 | Phobic disorders | 1 (0/0/1) | Clomipramine | 1 | 1 candidates |  |
| 461 | Phobic or anxiety states | 1 (1/0/0) | Bromazepam, Flunitrazepam | 3 | 3 candidates | ⚠️ near-miss: `anxiety-children` |
| 462 | Phobic states | 1 (1/0/0) | Bromazepam, Flunitrazepam | 3 | — | via parent *Phobic or anxiety states* |
| 463 | Pneumocystis carinii pneumonia | 1 (0/1/0) | Atovaquone | 1 | 1 candidates |  |
| 464 | Pneumocystis jiroveci pneumonia | 1 (0/1/0) | Trimethoprim with sulfamethoxazole | 1 | 3 candidates |  |
| 465 | Primary severe restless legs syndrome | 1 (0/0/1) | Pramipexole | 2 | 3 candidates |  |
| 466 | Probable invasive aspergillosis | 1 (1/0/0) | Voriconazole | 3 | 3 candidates | via parent *Definite or probable invasive aspergillosis* |
| 467 | Proctitis | 1 (0/0/1) | Prednisolone | 1 | `3951002` |  |
| 468 | Rehydration in intestinal failure | 1 (1/0/0) | Electrolyte replacement, oral | 1 | 3 candidates |  |
| 469 | Resected gastric and gastroesophageal junction adenocarcinoma | 1 (1/0/0) | Durvalumab | 2 | 3 candidates |  |
| 470 | Resected non-small cell lung cancer | 1 (1/0/0) | Alectinib | 1 | 3 candidates |  |
| 471 | Respiratory tract infection | 1 (1/0/0) | Ciprofloxacin | 3 | `275498002` |  |
| 472 | Schistosomiasis | 1 (0/1/0) | Praziquantel | 2 | `10087007` |  |
| 473 | Secondarily infected traumatic skin lesions | 1 (0/0/1) | Mupirocin | 1 | 3 candidates |  |
| 474 | Solid tumours with confirmed neurotrophic tropomyosin receptor kinase gene fusion where treatment with this drug is/was initiated in a child | 1 (1/0/0) | Larotrectinib | 3 | — |  |
| 475 | Spasticity of the upper limb following an acute event | 1 (0/1/0) | Clostridium botulinum type A toxin - haemagglutinin complex, Botulinum toxin type A purified neurotoxin complex, IncobotulinumtoxinA | 4 | 3 candidates |  |
| 476 | Squamous cell carcinoma of the larynx | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates | via parent *Squamous cell carcinoma of the oral cavity, pharynx or larynx* |
| 477 | Squamous cell carcinoma of the oral cavity | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates | via parent *Squamous cell carcinoma of the oral cavity, pharynx or larynx* |
| 478 | Squamous cell carcinoma of the oral cavity, pharynx or larynx | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates |  |
| 479 | Squamous cell carcinoma of the pharynx | 1 (0/1/0) | Pembrolizumab | 2 | 3 candidates | via parent *Squamous cell carcinoma of the oral cavity, pharynx or larynx* |
| 480 | Staphylococcus aureus infection | 1 (0/1/0) | Mupirocin | 2 | `406602003` |  |
| 481 | Systemic aspergillosis | 1 (0/1/0) | Itraconazole | 2 | `240701006` |  |
| 482 | Systemic histoplasmosis | 1 (0/1/0) | Itraconazole | 2 | — |  |
| 483 | Systemic sporotrichosis | 1 (0/1/0) | Itraconazole | 2 | — |  |
| 484 | Tapeworm infestation | 1 (0/1/0) | Albendazole | 1 | 3 candidates |  |
| 485 | Terminal disease | 1 (1/0/0) | Bromazepam, Flunitrazepam | 3 | 3 candidates |  |
| 486 | Termination of an intra-uterine pregnancy | 1 (0/1/0) | Mifepristone and misoprostol | 1 | 3 candidates |  |
| 487 | The onset of lactation | 1 (0/0/1) | Bromocriptine, Cabergoline | 2 | 3 candidates |  |
| 488 | Triple negative breast cancer | 1 (0/1/0) | Pembrolizumab | 2 | `706970001` |  |
| 489 | Type 1 diabetes | 1 (0/0/1) | Insulin detemir, Insulin degludec | 3 | `46635009` |  |
| 490 | Urinary symptoms | 1 (0/0/1) | Sodium citro-tartrate | 2 | `249274008` |  |
| 491 | Urinary tract infection | 1 (0/1/0) | Cefalexin, Trimethoprim | 2 | `68566005` | ⚠️ near-miss: `urinary-tract-infection-children` |
| 492 | Use in a hospital | 1 (0/0/1) | Hydrocortisone | 4 | 1 candidates |  |
| 493 | Whipworm infestation | 1 (0/1/0) | Albendazole | 1 | 1 candidates |  |

---

**PBS copyright notice (retained as the licence requires):**

> Copyright (c) 2024 Department of Health, Commonwealth of Australia
> Permission is granted to use and redistribute this content, as long as all copyright statements are retained. Permission is not granted to modify this content.
> For further copyright information of this content, please refer to: https://www.health.gov.au/using-our-websites/copyright
