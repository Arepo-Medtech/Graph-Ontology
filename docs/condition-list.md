# Condition list — all 639

**The single, combined list.** Source: `reference/conditions.json`, derived from **PBS Public API v3 `restrictions`**, latest schedule, Commonwealth CC BY. Generated 2026-09-23 from `master`.

> ### ⚠️ THE TWO FILES WERE ALREADY COMBINED
> `reference/conditions_split.json` holds **65 split children** adjudicated out of multi-entity PBS names. **All 65 are already present in the 639** — `conditions.json` records `split_children_merged: 60` and the true overlap is **65 of 65**. The union of the two files is **639, not 704.** A further **14 split children were rejected** as likely coined terms, having returned zero citations, and are deliberately absent.

> ### ⚠️ THE PRIMARY-CARE LIST DOES NOT EXIST
> `conditions-primary-care` (PR #2) does **not** produce a second condition list to merge. Its own script says so: *"ATC classifies drugs, not diseases. Only about 20 of 411 level-2/3 labels name a condition at all, so this does NOT fill the primary-care condition gap."* Its real output is **therapeutic areas**, its inferred conditions carry the weaker `atc_class_inferred` grade rather than `pbs_subsidised_restricted`, and it writes to `out/`, **which is gitignored and not present in this repo.** Nothing of it has ever been committed but the script.

> ### ⚠️ WHAT THIS LIST IS NOT
> **Not a complete list of treatable conditions.** PBS restrictions cover **restricted and authority items only**. Unrestricted benefits carry no restriction text, so conditions treated mainly with unrestricted drugs are **absent** — the set skews to oncology, biologics and high-cost specialist therapy. **Not derived from AMH or Therapeutic Guidelines.**

> ### ⚠️ ABOUT A DOZEN ENTRIES ARE NOT CONDITIONS
> They are artefacts of parsing PBS restriction prose — for example *"A patient identifying as Aboriginal or Torres Strait Islander"*, *"Patients unable to take a solid dose form of an ACE inhibitor"*, *"Ablation of thyroid remnant tissue"*, *"Above pressure injury"*. A crude screen flags 16 of 639 (3%), but several of those are false positives — *Acne*, *Pain* and *Treatment refractory generalised myasthenia gravis* are real. **The true rate is nearer 10–12 entries, about 2%.** They are left in rather than silently dropped; removing them is a judgement call, not a cleanup.

**639 conditions · 259 SNOMED-bound · 349 with candidates awaiting human confirmation · 31 unbound · 27 with a guideline in this compendium.**

| # | condition | PBS restrictions | variants | SNOMED | guideline | split child | parent |
|---|---|---|---|---|---|---|---|
| 1 | A patient identifying as Aboriginal or Torres Strait Islander | 7 | 1 | *2 cand.* |  |  |  |
| 2 | Ablation of thyroid remnant tissue | 1 | 1 | *3 cand.* |  |  |  |
| 3 | Above pressure injury | 1 | 1 | *3 cand.* |  |  |  |
| 4 | Achondroplasia | 2 | 1 | `` |  |  |  |
| 5 | Acne | 8 | 1 | `` | [acne](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/acne.md) |  |  |
| 6 | Acne vulgaris | 3 | 1 | `` |  |  |  |
| 7 | Acromegaly | 15 | 1 | `` |  |  |  |
| 8 | Acute allergic reaction with anaphylaxis | 6 | 1 | *3 cand.* |  |  |  |
| 9 | Acute bacterial enterocolitis | 1 | 1 | *3 cand.* |  |  |  |
| 10 | Acute coronary syndrome | 3 | 1 | `` |  |  |  |
| 11 | Acute lymphoblastic leukaemia | 15 | 1 | *3 cand.* |  |  |  |
| 12 | Acute mania | 3 | 1 |  |  |  |  |
| 13 | Acute mania or mixed episodes | 2 | 1 | *3 cand.* |  |  |  |
| 14 | Acute myelogenous leukaemia | 1 | 1 | *2 cand.* |  |  |  |
| 15 | Acute Myeloid Leukaemia | 19 | 2 | `` |  |  |  |
| 16 | Acute promyelocytic leukaemia | 3 | 1 | *3 cand.* |  |  |  |
| 17 | Acute severe generalised myasthenia gravis | 3 | 1 | *3 cand.* |  |  |  |
| 18 | Acute severe ulcerative colitis | 2 | 1 | *3 cand.* |  |  |  |
| 19 | Adenocarcinoma of the gastro-oesophageal junction | 2 | 0 | *3 cand.* |  | ✓ | Adenocarcinoma of the stomach or gastro-oesophageal junction |
| 20 | Adenocarcinoma of the pancreas | 1 | 1 | *3 cand.* |  |  |  |
| 21 | Adenocarcinoma of the stomach | 2 | 0 | *1 cand.* |  | ✓ | Adenocarcinoma of the stomach or gastro-oesophageal junction |
| 22 | Adenocarcinoma of the stomach or gastro-oesophageal junction | 2 | 1 | *3 cand.* |  |  |  |
| 23 | Adjuvant management of breast cancer | 2 | 1 | *3 cand.* |  |  |  |
| 24 | Adult-type IDH-mutant astrocytoma or oligodendroglioma | 3 | 1 | *3 cand.* |  |  |  |
| 25 | Advanced, metastatic or recurrent endometrial carcinoma | 6 | 1 | *3 cand.* |  |  |  |
| 26 | Adverse effects occurring with all of the base-priced drugs | 2 | 1 | *1 cand.* |  |  |  |
| 27 | Aggressive systemic mastocytosis with eosinophilia | 2 | 1 | *3 cand.* |  |  |  |
| 28 | Alcohol dependence | 2 | 1 | `` |  |  |  |
| 29 | Allergic asthma | 8 | 1 | `` |  |  |  |
| 30 | Alopecia areata | 1 | 1 | `` |  |  |  |
| 31 | Amyotrophic lateral sclerosis | 5 | 1 | `` |  |  |  |
| 32 | Anaemia associated with intrinsic renal disease | 2 | 1 | *3 cand.* |  |  |  |
| 33 | Anaemias associated with vitamin B12 deficiency | 2 | 1 | *3 cand.* |  |  |  |
| 34 | Anaerobic infections | 2 | 1 | *3 cand.* |  |  |  |
| 35 | Analgesia | 2 | 0 | `` |  | ✓ | Analgesia or fever |
| 36 | Analgesia or fever | 2 | 1 | *3 cand.* |  |  |  |
| 37 | Androgen deficiency | 8 | 1 | `` |  |  |  |
| 38 | Androgenisation | 2 | 1 | *3 cand.* |  |  |  |
| 39 | Angina | 1 | 1 | `` | [angina](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/angina.md) |  |  |
| 40 | Ankylosing spondylitis | 49 | 1 | `` |  |  |  |
| 41 | Anorectal congenital abnormalities | 4 | 1 | *3 cand.* |  |  |  |
| 42 | Anovulatory infertility | 4 | 1 | `` |  |  |  |
| 43 | Anti-neutrophil cytoplasmic autoantibody associated vasculitis | 1 | 1 | *3 cand.* |  |  |  |
| 44 | Antibiotic associated pseudomembranous colitis | 2 | 1 | *3 cand.* |  |  |  |
| 45 | Anticipated emergency treatment of an acute attack of hereditary angioedema | 2 | 1 | *1 cand.* |  |  |  |
| 46 | Anticipated premature ovarian failure | 1 | 1 | *3 cand.* |  |  |  |
| 47 | Anxiety | 3 | 1 | `` |  |  |  |
| 48 | Anxiety states | 1 | 0 |  |  | ✓ | Phobic or anxiety states |
| 49 | Aplastic anaemia | 3 | 1 | `` |  |  |  |
| 50 | Assisting autologous peripheral blood progenitor cell transplantation | 2 | 1 |  |  |  |  |
| 51 | Assisting bone marrow transplantation | 2 | 1 | *3 cand.* |  |  |  |
| 52 | Asthma | 82 | 4 | `` | [asthma](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/asthma.md) |  |  |
| 53 | Atopic dermatitis | 4 | 2 | `` |  |  |  |
| 54 | Attention deficit hyperactivity disorder | 10 | 1 | `` |  |  |  |
| 55 | Atypical haemolytic uraemic syndrome | 16 | 1 | `` |  |  |  |
| 56 | Atypical mycobacterial infections | 1 | 1 | *1 cand.* |  |  |  |
| 57 | Autosomal dominant polycystic kidney disease | 2 | 1 | `` |  |  |  |
| 58 | Bacterial gastroenteritis | 1 | 1 | `` |  |  |  |
| 59 | Bacterial keratitis | 2 | 1 | `` |  |  |  |
| 60 | Barcelona Clinic Liver Cancer Stage B or Stage C hepatocellular carcinoma | 10 | 2 | *3 cand.* |  |  |  |
| 61 | Basal cell carcinoma | 5 | 1 | *3 cand.* |  |  |  |
| 62 | Behavioural disturbances | 4 | 2 | *3 cand.* |  |  |  |
| 63 | Benign prostatic hyperplasia | 6 | 1 | `` |  |  |  |
| 64 | Biliary atresia | 1 | 1 | `` |  |  |  |
| 65 | Biochemical growth hormone deficiency and precocious puberty | 10 | 1 | *3 cand.* |  |  |  |
| 66 | Bipolar disorder | 2 | 1 | `` | [bipolar-disorder](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/bipolar-disorder.md) |  |  |
| 67 | Bipolar I disorder | 3 | 1 | `` |  |  |  |
| 68 | Blepharospasm | 1 | 1 | `` |  | ✓ | Blepharospasm or hemifacial spasm |
| 69 | Blepharospasm or hemifacial spasm | 2 | 1 | *3 cand.* |  |  |  |
| 70 | Bone | 1 | 0 | *3 cand.* |  | ✓ | Bone or joint infection |
| 71 | Bone infection | 1 | 0 | `` |  | ✓ | Bone or joint infection |
| 72 | Bone metastases | 9 | 1 | *3 cand.* |  |  |  |
| 73 | Bone or joint infection | 1 | 1 | *1 cand.* |  |  |  |
| 74 | Bone pain | 5 | 1 | `` |  |  |  |
| 75 | Bordetella pertussis | 1 | 1 | *3 cand.* |  |  |  |
| 76 | Branch retinal vein occlusion with macular oedema | 5 | 1 | `` |  |  |  |
| 77 | Breakthrough pain | 2 | 1 | `` |  |  |  |
| 78 | Breast cancer | 27 | 6 | `` |  |  |  |
| 79 | Bridging therapy for generalised myasthenia gravis | 3 | 1 | *3 cand.* |  |  |  |
| 80 | Bronchiectasis | 2 | 1 | `` |  |  |  |
| 81 | Bronchospasm | 2 | 1 | `` |  |  |  |
| 82 | Bronchospasm and dyspnoea associated with chronic obstructive pulmonary disease | 2 | 1 | *3 cand.* |  |  |  |
| 83 | Bulky or stage III or IV indolent non-Hodgkin's lymphoma | 1 | 1 | *3 cand.* |  |  |  |
| 84 | Bulky or Stage III/IV follicular lymphoma | 2 | 1 | *1 cand.* |  |  |  |
| 85 | Calcium malabsorption | 2 | 1 |  |  |  |  |
| 86 | Cancer pain | 3 | 1 | *3 cand.* |  |  |  |
| 87 | Candida infections | 1 | 1 | *2 cand.* |  |  |  |
| 88 | Carcinoma of the prostate | 5 | 4 | *3 cand.* |  |  |  |
| 89 | Cardiac allograft rejection | 4 | 1 | *3 cand.* |  |  |  |
| 90 | Cardiac arrhythmias | 1 | 1 | *3 cand.* |  |  |  |
| 91 | Castration resistant metastatic carcinoma of the prostate | 7 | 1 | *3 cand.* |  |  |  |
| 92 | Castration resistant non-metastatic carcinoma of the prostate | 1 | 1 | *3 cand.* |  |  |  |
| 93 | Castration sensitive carcinoma of the prostate | 1 | 1 | *3 cand.* |  |  |  |
| 94 | Cataplexy | 1 | 1 | `` |  |  |  |
| 95 | CD30 positive cutaneous T-cell lymphoma | 2 | 1 | *1 cand.* |  |  |  |
| 96 | CD30 positive Hodgkin lymphoma | 1 | 1 | *3 cand.* |  |  |  |
| 97 | CD30 positive peripheral T-cell lymphoma | 2 | 0 | *3 cand.* |  | ✓ | CD30 positive peripheral T-cell lymphoma, non-cutaneous type |
| 98 | CD30 positive peripheral T-cell lymphoma, non-cutaneous type | 2 | 1 | *3 cand.* |  |  |  |
| 99 | CD30 positive systemic anaplastic large cell lymphoma | 2 | 1 | *3 cand.* |  |  |  |
| 100 | Cellulitis | 2 | 1 | `` |  |  |  |
| 101 | Central precocious puberty | 3 | 1 | `` |  |  |  |
| 102 | Central retinal vein occlusion with macular oedema | 5 | 1 | `` |  |  |  |
| 103 | Cerebrospinal fluid glucose transporter defect | 1 | 1 | *3 cand.* |  |  |  |
| 104 | Cervicitis | 1 | 1 | `` |  |  |  |
| 105 | Chelation of elevated copper levels | 1 | 1 | *3 cand.* |  |  |  |
| 106 | Chemotherapy refractory Peripheral T-cell Lymphoma | 3 | 1 | *3 cand.* |  |  |  |
| 107 | Chemotherapy-induced neutropenia | 8 | 1 | *3 cand.* |  |  |  |
| 108 | Cholangiocarcinoma | 2 | 1 | *3 cand.* |  |  |  |
| 109 | Chronic arthropathies | 8 | 2 | *3 cand.* |  |  |  |
| 110 | Chronic asthma | 2 | 1 | *3 cand.* |  |  |  |
| 111 | Chronic Breathlessness | 1 | 1 |  |  |  |  |
| 112 | Chronic bronchitis | 3 | 1 | `` |  |  |  |
| 113 | Chronic constipation | 4 | 1 | `` |  |  |  |
| 114 | Chronic cyclical neutropenia | 2 | 1 | *3 cand.* |  |  |  |
| 115 | Chronic discoid lupus erythematosus | 1 | 1 | `` |  |  |  |
| 116 | Chronic eosinophilic leukaemia | 2 | 0 | `` |  | ✓ | Chronic eosinophilic leukaemia or Hypereosinophilic syndrome |
| 117 | Chronic eosinophilic leukaemia or Hypereosinophilic syndrome | 2 | 1 | *3 cand.* |  |  |  |
| 118 | Chronic gout | 2 | 1 | *3 cand.* |  |  |  |
| 119 | Chronic graft versus host disease | 6 | 2 | `` |  |  |  |
| 120 | Chronic granulomatous disease | 2 | 1 | `` |  |  |  |
| 121 | Chronic heart failure | 12 | 1 | `` |  |  |  |
| 122 | Chronic hepatitis B infection | 9 | 1 | *3 cand.* |  |  |  |
| 123 | Chronic hepatitis C infection | 7 | 1 | *3 cand.* |  |  |  |
| 124 | Chronic hyperkalaemia | 2 | 1 | `` |  |  |  |
| 125 | Chronic iron overload | 9 | 1 | *3 cand.* |  |  |  |
| 126 | Chronic kidney disease | 2 | 1 | `` | [chronic-kidney-disease](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/chronic-kidney-disease.md) |  |  |
| 127 | Chronic kidney disease with Type 2 diabetes | 1 | 1 | *3 cand.* |  |  |  |
| 128 | Chronic liver failure with fat malabsorption | 1 | 1 | *3 cand.* |  |  |  |
| 129 | Chronic lymphocytic leukaemia | 3 | 1 | `` |  | ✓ | Chronic lymphocytic leukaemia or small lymphocytic lymphoma |
| 130 | Chronic lymphocytic leukaemia or small lymphocytic lymphoma | 26 | 1 | *2 cand.* |  |  |  |
| 131 | Chronic migraine | 3 | 1 | `` |  |  |  |
| 132 | Chronic Myeloid Leukaemia | 26 | 1 | `` |  |  |  |
| 133 | Chronic Myelomonocytic Leukaemia | 4 | 1 | `` |  |  |  |
| 134 | Chronic neutropenia | 2 | 1 | *3 cand.* |  |  |  |
| 135 | Chronic obstructive pulmonary disease | 17 | 2 | `` |  |  |  |
| 136 | Chronic plaque psoriasis | 147 | 1 | *3 cand.* |  |  |  |
| 137 | Chronic pouchitis | 4 | 1 | *1 cand.* |  |  |  |
| 138 | Chronic pulmonary histoplasmosis infection | 1 | 1 | *3 cand.* |  |  |  |
| 139 | Chronic renal disease | 1 | 1 | `` |  |  |  |
| 140 | Chronic renal failure | 2 | 1 | `` |  |  |  |
| 141 | Chronic rhinosinusitis with nasal polyps | 2 | 1 | `` |  |  |  |
| 142 | Chronic severe atopic dermatitis | 9 | 1 | *1 cand.* |  |  |  |
| 143 | Chronic severe disabling pain | 10 | 1 | *3 cand.* |  |  |  |
| 144 | Chronic severe dry eye disease with keratitis | 2 | 1 | *3 cand.* |  |  |  |
| 145 | Chronic severe pain | 3 | 1 | *3 cand.* |  |  |  |
| 146 | Chronic sialorrhea | 2 | 1 |  |  |  |  |
| 147 | Chronic spasticity | 18 | 2 | *2 cand.* |  |  |  |
| 148 | Chronic spontaneous urticaria | 4 | 1 | `` |  |  |  |
| 149 | Chronic stable atherosclerotic disease | 3 | 1 | *3 cand.* |  |  |  |
| 150 | Chronic stable plaque type psoriasis vulgaris | 2 | 1 | *3 cand.* |  |  |  |
| 151 | Chronic suppurative otitis media | 3 | 1 | `` |  |  |  |
| 152 | Chronic thromboembolic pulmonary hypertension | 3 | 1 | `` |  |  |  |
| 153 | Chronic treatment of Acute Hepatic Porphyria | 2 | 1 | *3 cand.* |  |  |  |
| 154 | Chronic treatment of hereditary angioedema Types 1 or 2 | 10 | 1 | *3 cand.* |  |  |  |
| 155 | Chylothorax | 3 | 1 | `` |  |  |  |
| 156 | Chylous ascites | 4 | 1 | `` |  |  |  |
| 157 | Clear cell variant renal cell carcinoma | 13 | 1 | *3 cand.* |  |  |  |
| 158 | Clinically definite relapsing-remitting multiple sclerosis | 2 | 1 | *3 cand.* |  |  |  |
| 159 | Colorectal cancer | 16 | 1 | `` |  |  |  |
| 160 | Combined deficiency of human growth hormone and gonadotrophins | 1 | 1 | *3 cand.* |  |  |  |
| 161 | Combined immunoglobulin E mediated allergy to cows' milk protein and soy protein | 6 | 1 | *3 cand.* |  |  |  |
| 162 | Combined intolerance to cows' milk protein, soy protein and protein hydrolysate formulae | 4 | 1 |  |  |  |  |
| 163 | Community acquired pneumonia | 1 | 1 | `` |  |  |  |
| 164 | Complicated urinary tract infection | 1 | 1 | *1 cand.* |  |  |  |
| 165 | Congenital neutropenia | 2 | 1 | `` |  |  |  |
| 166 | Constipation | 27 | 1 | `` | [constipation](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/constipation.md) |  |  |
| 167 | Constitutional delay of growth | 4 | 0 | *1 cand.* |  | ✓ | Constitutional delay of growth or puberty |
| 168 | Constitutional delay of growth or puberty | 4 | 1 | *3 cand.* |  |  |  |
| 169 | Constitutional delay of puberty | 4 | 0 | *1 cand.* |  | ✓ | Constitutional delay of growth or puberty |
| 170 | Contraception | 1 | 1 | *3 cand.* | [contraception](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/contraception.md) |  |  |
| 171 | Corneal grafts | 1 | 1 | *3 cand.* |  |  |  |
| 172 | Coronary artery disease | 1 | 1 | *3 cand.* |  |  |  |
| 173 | Corticosteroid-induced osteoporosis | 8 | 1 | *3 cand.* |  |  |  |
| 174 | Corticosteroid-responsive dermatoses | 11 | 1 |  |  |  |  |
| 175 | Cows' milk anaphylaxis | 2 | 1 | *1 cand.* |  |  |  |
| 176 | Cows' milk protein enteropathy | 4 | 1 | *3 cand.* |  |  |  |
| 177 | Cows' milk protein enteropathy and intolerance to soy protein | 3 | 1 | *3 cand.* |  |  |  |
| 178 | Cows' milk protein enteropathy with failure to thrive | 4 | 1 | *3 cand.* |  |  |  |
| 179 | Cranial diabetes insipidus | 2 | 1 | `` |  |  |  |
| 180 | Crohn disease | 62 | 4 | `` |  |  |  |
| 181 | Crusted scabies | 1 | 1 | `` |  |  |  |
| 182 | Cryopyrin associated periodic syndromes | 1 | 1 | *3 cand.* |  |  |  |
| 183 | Cryptococcal meningitis | 4 | 1 | `` |  |  |  |
| 184 | Cutaneous squamous cell carcinoma | 2 | 1 | `` |  |  |  |
| 185 | Cutaneous T-cell lymphoma | 2 | 1 | `` |  |  |  |
| 186 | Cystic acne | 1 | 1 | `` |  |  |  |
| 187 | Cystic fibrosis | 31 | 1 | `` |  |  |  |
| 188 | Cystic fibrosis - homozygous for the F508del mutation | 2 | 1 | *3 cand.* |  |  |  |
| 189 | Cystic fibrosis - one residual function mutation | 2 | 1 | *3 cand.* |  |  |  |
| 190 | Cytomegalovirus infection and disease | 8 | 1 | *1 cand.* |  |  |  |
| 191 | Cytomegalovirus retinitis | 2 | 1 | `` |  |  |  |
| 192 | Deep vein thrombosis | 5 | 1 | `` |  |  |  |
| 193 | Definite | 1 | 0 | *3 cand.* |  | ✓ | Definite or probable invasive aspergillosis |
| 194 | Definite aspergillosis | 1 | 0 |  |  | ✓ | Definite or probable invasive aspergillosis |
| 195 | Definite or probable invasive aspergillosis | 1 | 1 |  |  |  |  |
| 196 | Delayed puberty | 1 | 0 | `` |  | ✓ | Hypogonadism or delayed puberty |
| 197 | Depression | 3 | 2 | `` |  |  |  |
| 198 | Dermatofibrosarcoma protuberans | 2 | 1 | `` |  |  |  |
| 199 | Dermatophyte infection | 2 | 1 | *2 cand.* |  |  |  |
| 200 | Detrusor overactivity | 4 | 1 | `` |  |  |  |
| 201 | Diabetes mellitus type 2 | 19 | 1 | `` |  |  |  |
| 202 | Diabetic macular oedema | 5 | 1 | `` |  | ✓ | Proliferative diabetic retinopathy and/or Diabetic macular oedema |
| 203 | Diarrhoea | 2 | 1 | `` | [diarrhoea](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/diarrhoea.md) |  |  |
| 204 | Diarrhoea of greater than 2 weeks duration | 1 | 1 | *3 cand.* |  |  |  |
| 205 | Dietary management of conditions requiring a highly restrictive therapeutic diet | 3 | 1 | *1 cand.* |  |  |  |
| 206 | Dietary management of conditions requiring a source of medium chain triglycerides | 3 | 1 |  |  |  |  |
| 207 | Differentiated thyroid cancer | 4 | 1 | `` |  |  |  |
| 208 | Diffuse large B-cell lymphoma | 8 | 1 | `` |  |  |  |
| 209 | Disabling pain | 3 | 1 | *1 cand.* |  |  |  |
| 210 | Disorders of erythropoiesis | 2 | 1 | *3 cand.* |  |  |  |
| 211 | Disorders of keratinisation | 1 | 1 | *3 cand.* |  |  |  |
| 212 | Disseminated pulmonary histoplasmosis infection | 1 | 1 | *3 cand.* |  |  |  |
| 213 | Drug interactions expected to occur with all of the base-priced drugs | 2 | 1 | *3 cand.* |  |  |  |
| 214 | Drug interactions occurring with all of the base-priced drugs | 2 | 1 | *3 cand.* |  |  |  |
| 215 | Dry eye syndrome | 6 | 1 | `` |  |  |  |
| 216 | Dynamic equinus foot deformity | 2 | 1 | *3 cand.* |  |  |  |
| 217 | Dysmenorrhoea | 1 | 1 | `` |  |  |  |
| 218 | Eczema | 1 | 1 | `` | [eczema](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/eczema.md) |  |  |
| 219 | Elevated intra-ocular pressure | 3 | 1 | *3 cand.* |  |  |  |
| 220 | Endocarditis | 2 | 1 | `` |  |  |  |
| 221 | Endogenous Cushing's syndrome | 2 | 1 | *3 cand.* |  |  |  |
| 222 | Endometrial cancer | 2 | 1 | *1 cand.* |  |  |  |
| 223 | Endometriosis | 8 | 1 | `` | [endometriosis](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/endometriosis.md) |  |  |
| 224 | Endophthalmitis | 1 | 1 | `` |  |  |  |
| 225 | Enterokinase deficiency | 1 | 1 | *2 cand.* |  |  |  |
| 226 | Enthesitis/spondylitis related juvenile idiopathic arthritis | 4 | 1 | *3 cand.* |  |  |  |
| 227 | Eosinophilic oesophagitis | 9 | 1 | `` |  |  |  |
| 228 | Epididymo-orchitis | 1 | 1 | *3 cand.* |  |  |  |
| 229 | Epilepsy | 2 | 1 | `` | [epilepsy](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/epilepsy.md) |  |  |
| 230 | Epileptic seizures | 6 | 1 | *3 cand.* |  |  |  |
| 231 | Epithelial ovarian cancer | 14 | 0 | *3 cand.* |  | ✓ | Epithelial ovarian, fallopian tube or primary peritoneal cancer |
| 232 | Epithelial ovarian, fallopian tube or primary peritoneal cancer | 14 | 2 | *3 cand.* |  |  |  |
| 233 | Eradication of Helicobacter pylori | 1 | 1 | *3 cand.* |  |  |  |
| 234 | Erectile dysfunction | 1 | 1 | `` | [erectile-dysfunction](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/erectile-dysfunction.md) |  |  |
| 235 | Erythrodermic stage III-IVa T4 M0 Cutaneous T-cell lymphoma | 4 | 1 | *3 cand.* |  |  |  |
| 236 | Established atherosclerotic cardiovascular disease with hypertriglyceridaemia | 2 | 1 | *3 cand.* |  |  |  |
| 237 | Established osteoporosis | 22 | 2 |  |  |  |  |
| 238 | Established post-menopausal osteoporosis | 2 | 1 | *3 cand.* |  |  |  |
| 239 | Extensive-stage small cell lung cancer | 3 | 1 | *3 cand.* |  |  |  |
| 240 | Eye inflammation | 1 | 1 | *3 cand.* |  |  |  |
| 241 | Fabry disease | 8 | 1 | `` |  |  |  |
| 242 | Facial lipoatrophy | 2 | 1 | *1 cand.* |  |  |  |
| 243 | Faecal impaction | 4 | 1 | `` |  |  |  |
| 244 | Fallopian tube cancer | 14 | 0 | *3 cand.* |  | ✓ | Epithelial ovarian, fallopian tube or primary peritoneal cancer |
| 245 | Familial heterozygous hypercholesterolaemia | 4 | 1 | *3 cand.* |  |  |  |
| 246 | Familial homozygous hypercholesterolaemia | 2 | 1 | `` |  |  |  |
| 247 | Familial hypophosphataemia | 2 | 1 | `` |  |  |  |
| 248 | Fat malabsorption | 2 | 2 | *3 cand.* |  |  |  |
| 249 | Fever | 2 | 0 | `` |  | ✓ | Analgesia or fever |
| 250 | Fibrodysplasia ossificans progressiva | 2 | 1 | `` |  |  |  |
| 251 | Fistulising Crohn disease | 19 | 1 | *3 cand.* |  |  |  |
| 252 | Focal onset seizures | 2 | 1 | *3 cand.* |  |  |  |
| 253 | Follicular B-cell non-Hodgkin's lymphoma | 2 | 1 | *3 cand.* |  |  |  |
| 254 | Follicular lymphoma | 6 | 2 | `` |  |  |  |
| 255 | Functional carcinoid tumour | 9 | 1 | *3 cand.* |  |  |  |
| 256 | Fungal | 2 | 0 | *3 cand.* |  | ✓ | Fungal or yeast infection |
| 257 | Fungal infection | 3 | 1 | *3 cand.* |  | ✓ | Fungal or yeast infection |
| 258 | Fungal infections | 1 | 1 | *3 cand.* |  |  |  |
| 259 | Fungal or yeast infection | 2 | 1 | *3 cand.* |  |  |  |
| 260 | Gastric and gastroesophageal junction adenocarcinoma | 1 | 1 | *3 cand.* |  |  |  |
| 261 | Gastric stasis | 1 | 0 | `` |  | ✓ | Nausea or gastric stasis |
| 262 | Gastro-oesophageal cancer | 1 | 1 | *3 cand.* |  |  |  |
| 263 | Gastro-oesophageal junction cancer | 1 | 0 | *3 cand.* |  | ✓ | Oesophageal cancer or gastro-oesophageal junction cancer |
| 264 | Gastro-oesophageal reflux disease | 10 | 2 | `` |  |  |  |
| 265 | Gastrointestinal stromal tumour | 2 | 1 | `` |  |  |  |
| 266 | Generalised anxiety disorder | 8 | 1 | `` | [generalised-anxiety-disorder](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/generalised-anxiety-disorder.md) |  |  |
| 267 | Generalized convulsive status epilepticus | 2 | 1 | `` |  |  |  |
| 268 | Genital herpes | 7 | 1 | *3 cand.* | [genital-herpes](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/genital-herpes.md) |  |  |
| 269 | Germ cell neoplasms | 1 | 1 | *3 cand.* |  |  |  |
| 270 | Giant cell arteritis | 2 | 1 | `` |  |  |  |
| 271 | Giant cell tumour of bone | 1 | 1 | `` |  |  |  |
| 272 | Glioblastoma multiforme | 2 | 1 | `` |  |  |  |
| 273 | Glutaric aciduria type 1 | 2 | 1 | `` |  |  |  |
| 274 | Glycogen storage disease | 1 | 1 | `` |  |  |  |
| 275 | Gonorrhoea | 2 | 1 | `` |  |  |  |
| 276 | Grade II to IV acute graft versus host disease | 4 | 1 | *3 cand.* |  |  |  |
| 277 | Gram-positive coccal infections | 2 | 1 | *3 cand.* |  |  |  |
| 278 | Granulomata | 1 | 1 | *3 cand.* |  |  |  |
| 279 | Growth failure with primary insulin-like growth factor-1 deficiency | 2 | 1 | *3 cand.* |  |  |  |
| 280 | Growth hormone deficiency | 4 | 1 | `` |  |  |  |
| 281 | Growth retardation secondary to an intracranial lesion, or cranial irradiation | 10 | 1 | *3 cand.* |  |  |  |
| 282 | Gyrate atrophy of the choroid and retina | 1 | 1 | *3 cand.* |  |  |  |
| 283 | Haemodialysis | 1 | 1 | *3 cand.* |  |  |  |
| 284 | Haemophilus influenzae type B | 1 | 1 | *3 cand.* |  |  |  |
| 285 | Hairy cell leukaemia | 1 | 1 | `` |  |  |  |
| 286 | Heart failure | 2 | 1 | `` | [heart-failure](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/heart-failure.md) |  |  |
| 287 | Hemifacial spasm | 2 | 0 | `` |  | ✓ | Blepharospasm or hemifacial spasm |
| 288 | Hepatic encephalopathy | 1 | 1 | `` |  |  |  |
| 289 | HER2 positive adenocarcinoma of the gastro-oesophageal junction | 2 | 0 | *1 cand.* |  | ✓ | HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction |
| 290 | HER2 positive adenocarcinoma of the stomach | 2 | 0 | *3 cand.* |  | ✓ | HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction |
| 291 | HER2 positive adenocarcinoma of the stomach or gastro-oesophageal junction | 2 | 1 |  |  |  |  |
| 292 | HER2 positive breast cancer | 20 | 3 | *3 cand.* |  |  |  |
| 293 | HER2-low breast cancer | 1 | 1 | *3 cand.* |  |  |  |
| 294 | Hereditary transthyretin amyloidosis | 2 | 1 | *2 cand.* |  |  |  |
| 295 | Hereditary tyrosinaemia type 1 | 6 | 1 | *3 cand.* |  |  |  |
| 296 | Herpes simplex keratitis | 2 | 1 | `` |  |  |  |
| 297 | Herpes zoster | 4 | 1 | `` |  |  |  |
| 298 | Herpes zoster ophthalmicus | 2 | 1 | `` |  |  |  |
| 299 | Hidradenitis suppurativa | 21 | 1 | `` |  |  |  |
| 300 | High risk and intermediate-2 risk myelofibrosis | 3 | 1 | *2 cand.* |  |  |  |
| 301 | High risk locally advanced carcinoma of the cervix | 2 | 1 | *3 cand.* |  |  |  |
| 302 | High risk of recurrence clear cell variant renal cell carcinoma | 1 | 0 | *3 cand.* |  | ✓ | Intermediate or high risk of recurrence clear cell variant renal cell carcinoma |
| 303 | High risk of unstable angina | 2 | 1 | *3 cand.* |  |  |  |
| 304 | High-risk neuroblastoma | 2 | 1 | *3 cand.* |  |  |  |
| 305 | HIV infection | 22 | 1 | `` |  |  |  |
| 306 | Hodgkin lymphoma | 4 | 1 | *3 cand.* |  |  |  |
| 307 | Homocystinuria | 1 | 1 | `` |  |  |  |
| 308 | Hookworm infestation | 1 | 1 | *1 cand.* |  |  |  |
| 309 | Hormone sensitive carcinoma of the prostate | 1 | 1 | *3 cand.* |  |  |  |
| 310 | Human immunodeficiency virus infection | 6 | 1 | `` |  |  |  |
| 311 | Human sarcoptic scabies | 2 | 1 |  |  |  |  |
| 312 | Hydatid disease | 1 | 1 | `` |  |  |  |
| 313 | Hypercalcaemia | 4 | 1 | `` |  |  |  |
| 314 | Hypercalcaemia of malignancy | 4 | 1 | `` |  |  |  |
| 315 | Hypereosinophilic syndrome | 2 | 0 | `` |  | ✓ | Chronic eosinophilic leukaemia or Hypereosinophilic syndrome |
| 316 | Hyperkinetic extrapyramidal disorders | 2 | 1 | *3 cand.* |  |  |  |
| 317 | Hyperlipoproteinaemia type 1 | 3 | 1 | *1 cand.* |  |  |  |
| 318 | Hyperphenylalaninaemia | 2 | 1 | `` |  |  |  |
| 319 | Hyperphenylalaninaemia due to phenylketonuria | 3 | 1 | *3 cand.* |  |  |  |
| 320 | Hyperphenylalaninaemia due to tetrahydrobiopterin deficiency | 2 | 1 | *3 cand.* |  |  |  |
| 321 | Hyperphosphataemia | 8 | 1 | `` |  |  |  |
| 322 | Hypertension | 8 | 2 | `` | [hypertension](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/hypertension.md) |  |  |
| 323 | Hypocalcaemia | 4 | 1 | `` |  |  |  |
| 324 | Hypogonadism | 1 | 0 | `` |  | ✓ | Hypogonadism or delayed puberty |
| 325 | Hypogonadism or delayed puberty | 1 | 1 | *3 cand.* |  |  |  |
| 326 | Hypomagnesaemia | 2 | 1 | `` |  |  |  |
| 327 | Hypoparathyroidism | 2 | 1 | `` |  |  |  |
| 328 | Hypophosphataemic rickets | 3 | 1 | *3 cand.* |  |  |  |
| 329 | Hypothalamic-pituitary disease secondary to a structural lesion, with hypothalamic obesity driven growth | 10 | 1 | *1 cand.* |  |  |  |
| 330 | Hypothyroidism | 3 | 1 | `` |  |  |  |
| 331 | Hypsarrhythmia | 1 | 0 | *3 cand.* |  | ✓ | Hypsarrhythmia and/or infantile spasms |
| 332 | Hypsarrhythmia and/or infantile spasms | 1 | 1 | *3 cand.* |  |  |  |
| 333 | Idiopathic generalised epilepsy with primary generalised tonic-clonic seizures | 6 | 1 | *3 cand.* |  |  |  |
| 334 | Idiopathic menorrhagia | 2 | 1 |  |  |  |  |
| 335 | Idiopathic multicentric Castleman disease | 2 | 1 | *3 cand.* |  |  |  |
| 336 | Idiopathic pulmonary fibrosis | 4 | 1 | `` |  |  |  |
| 337 | Immunotherapy sensitive advanced or metastatic cancer | 3 | 1 | *3 cand.* |  |  |  |
| 338 | Inborn errors of protein metabolism | 1 | 1 | *3 cand.* |  |  |  |
| 339 | Infantile spasms | 1 | 0 | *3 cand.* |  | ✓ | Hypsarrhythmia and/or infantile spasms |
| 340 | Infection | 8 | 1 | `` |  |  |  |
| 341 | Infection suspected or proven to be due to a susceptible organism | 1 | 1 | *3 cand.* |  |  |  |
| 342 | Infection where positive bacteriological evidence confirms that this antibiotic is an appropriate therapeutic agent | 2 | 1 | *1 cand.* |  |  |  |
| 343 | Infection where resistance to amoxicillin is suspected | 3 | 1 | *3 cand.* |  |  |  |
| 344 | Infections where resistance to amoxicillin is proven | 3 | 1 | *3 cand.* |  |  |  |
| 345 | Infertility | 4 | 1 | *3 cand.* | [infertility](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/infertility.md) |  |  |
| 346 | Infertility indications other than that of Assisted Reproductive Technology | 1 | 1 |  |  |  |  |
| 347 | Initial moderate to severe genital herpes | 2 | 1 | *3 cand.* |  |  |  |
| 348 | Insomnia | 6 | 1 | `` | [insomnia](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/insomnia.md) |  |  |
| 349 | Intermediate | 1 | 0 | *3 cand.* |  | ✓ | Intermediate or high risk of recurrence clear cell variant renal cell carcinoma |
| 350 | Intermediate or high risk of recurrence clear cell variant renal cell carcinoma | 1 | 1 | *3 cand.* |  |  |  |
| 351 | Intermediate-1 risk myelofibrosis | 3 | 1 | *3 cand.* |  |  |  |
| 352 | Intestinal malabsorption including short bowel syndrome | 4 | 1 | *3 cand.* |  |  |  |
| 353 | Intractable childhood epilepsy | 1 | 1 | *3 cand.* |  |  |  |
| 354 | Intractable focal onset seizures | 11 | 1 | *1 cand.* |  |  |  |
| 355 | Intractable psoriasis | 1 | 1 |  |  |  |  |
| 356 | Invasive aspergillosis | 1 | 1 | `` |  |  |  |
| 357 | Invasive fungal infections including both yeasts and moulds | 2 | 1 | *3 cand.* |  |  |  |
| 358 | Invasive mycosis infections | 1 | 1 | *1 cand.* |  |  |  |
| 359 | Iron deficiency anaemia | 1 | 1 | `` |  |  |  |
| 360 | Iron overload | 6 | 1 | `` |  |  |  |
| 361 | Isovaleric acidaemia | 1 | 1 | `` |  |  |  |
| 362 | Joint infection | 1 | 0 | `` |  | ✓ | Bone or joint infection |
| 363 | Juvenile idiopathic arthritis | 55 | 1 | `` |  |  |  |
| 364 | Kaposi sarcoma | 4 | 1 | `` |  |  |  |
| 365 | Keloid | 2 | 1 | `` |  |  |  |
| 366 | Labial herpes | 3 | 0 | *3 cand.* |  | ✓ | Oral or labial herpes |
| 367 | Lambert-Eaton myasthenic syndrome | 1 | 1 | `` |  |  |  |
| 368 | Leiomyosarcoma | 2 | 0 | `` |  | ✓ | Leiomyosarcoma or liposarcoma |
| 369 | Leiomyosarcoma or liposarcoma | 2 | 1 | *3 cand.* |  |  |  |
| 370 | Leprosy | 1 | 1 | `` |  |  |  |
| 371 | Lichen planus hypertrophic | 2 | 1 | *3 cand.* |  |  |  |
| 372 | Lichen simplex chronicus | 1 | 1 | `` |  |  |  |
| 373 | Limited-stage small cell lung cancer | 1 | 1 | *3 cand.* |  |  |  |
| 374 | Liposarcoma | 2 | 1 | `` |  | ✓ | Leiomyosarcoma or liposarcoma |
| 375 | Local intra-articular or peri-articular infiltration | 3 | 1 | *1 cand.* |  |  |  |
| 376 | Locally advanced, metastatic or recurrent biliary tract cancer | 1 | 1 | *1 cand.* |  |  |  |
| 377 | Long chain fatty acid oxidation disorders | 3 | 1 | *3 cand.* |  |  |  |
| 378 | Lupus nephritis | 3 | 1 | `` |  |  |  |
| 379 | Lymphoma | 1 | 1 | *3 cand.* |  |  |  |
| 380 | Major depression | 8 | 2 | *3 cand.* |  |  |  |
| 381 | Major depressive disorders | 6 | 1 | *3 cand.* |  |  |  |
| 382 | Malaria | 1 | 1 | `` |  |  |  |
| 383 | Malignant gastrointestinal stromal tumour | 7 | 2 | *3 cand.* |  |  |  |
| 384 | Malignant melanoma | 11 | 1 | `` |  |  |  |
| 385 | Malignant neoplasia | 2 | 1 | *2 cand.* |  |  |  |
| 386 | Mantle cell lymphoma | 3 | 2 | `` |  |  |  |
| 387 | Maple syrup urine disease | 2 | 1 | `` |  |  |  |
| 388 | Maternal hyperphenylalaninaemia due to phenylketonuria | 3 | 1 | *3 cand.* |  |  |  |
| 389 | Medullary thyroid cancer | 2 | 1 | *3 cand.* |  |  |  |
| 390 | Megacolon | 4 | 1 | `` |  |  |  |
| 391 | Megaloblastic anaemias | 2 | 1 | *3 cand.* |  |  |  |
| 392 | Melanoma | 1 | 1 | `` |  |  |  |
| 393 | Meningococcal disease | 1 | 1 | `` |  |  |  |
| 394 | Menorrhagia | 1 | 1 | `` |  |  |  |
| 395 | Merkel Cell Carcinoma | 2 | 1 | `` |  |  |  |
| 396 | Methylmalonic acidaemia | 2 | 1 | `` |  |  |  |
| 397 | Micropenis | 4 | 1 | `` |  |  |  |
| 398 | Migraine | 4 | 2 | `` | [migraine](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/migraine.md) |  |  |
| 399 | Migraine attack | 7 | 1 | *1 cand.* |  |  |  |
| 400 | Mixed episodes | 2 | 0 | *1 cand.* |  | ✓ | Acute mania or mixed episodes |
| 401 | Moderately severe Alzheimer disease | 6 | 2 | *3 cand.* |  |  |  |
| 402 | Mucositis | 2 | 1 | `` |  |  |  |
| 403 | Multiple myeloma | 42 | 3 | `` |  |  |  |
| 404 | Multiple sclerosis | 17 | 1 | `` | [multiple-sclerosis](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/multiple-sclerosis.md) |  |  |
| 405 | Mycobacterium avium complex infection | 5 | 1 | *3 cand.* |  |  |  |
| 406 | Mycobacterium ulcerans infection | 1 | 1 | *1 cand.* |  |  |  |
| 407 | Mycosis fungoides cutaneous T-cell lymphoma | 2 | 1 | *1 cand.* |  |  |  |
| 408 | Myelodysplastic | 2 | 0 | *3 cand.* |  | ✓ | Myelodysplastic or myeloproliferative disorder |
| 409 | Myelodysplastic disorder | 2 | 0 | *3 cand.* |  | ✓ | Myelodysplastic or myeloproliferative disorder |
| 410 | Myelodysplastic or myeloproliferative disorder | 2 | 1 | *3 cand.* |  |  |  |
| 411 | Myelodysplastic syndrome | 6 | 1 | `` |  |  |  |
| 412 | Myeloproliferative disorder | 2 | 0 | `` |  | ✓ | Myelodysplastic or myeloproliferative disorder |
| 413 | Myoclonic epilepsy | 1 | 1 | *3 cand.* |  |  |  |
| 414 | Myoclonic epilepsy in infancy | 3 | 1 | `` |  |  |  |
| 415 | Narcolepsy | 6 | 1 | `` |  |  |  |
| 416 | Nasopharyngeal carcinoma | 1 | 1 | `` |  |  |  |
| 417 | Nausea | 1 | 0 | `` |  | ✓ | Nausea or gastric stasis |
| 418 | Nausea and vomiting | 24 | 1 | `` |  |  |  |
| 419 | Nausea or gastric stasis | 1 | 1 | *3 cand.* |  |  |  |
| 420 | Necrobiosis lipoidica | 1 | 1 | `` |  |  |  |
| 421 | Nephrotic syndrome | 2 | 1 | `` |  |  |  |
| 422 | Neurofibromatosis type 1 | 3 | 1 | `` |  |  |  |
| 423 | Neurogenic urinary retention | 1 | 1 | *3 cand.* |  |  |  |
| 424 | Neuromyelitis optica spectrum disorder | 2 | 1 | *3 cand.* |  |  |  |
| 425 | Neuropathic pain | 2 | 2 | `` |  |  |  |
| 426 | Nicotine dependence | 7 | 1 | `` |  |  |  |
| 427 | Non-familial hypercholesterolaemia | 4 | 1 | *3 cand.* |  |  |  |
| 428 | Non-functional gastroenteropancreatic neuroendocrine tumour | 5 | 1 | *3 cand.* |  |  |  |
| 429 | Non-infectious posterior segment uveitis | 1 | 1 | *1 cand.* |  |  |  |
| 430 | Non-infectious uveitis | 5 | 1 | *3 cand.* |  |  |  |
| 431 | Non-Q-wave myocardial infarction | 1 | 1 | `` |  |  |  |
| 432 | Non-radiographic axial spondyloarthritis | 25 | 1 | `` |  |  |  |
| 433 | Non-small cell lung cancer | 44 | 7 | `` |  |  |  |
| 434 | Obesity | 3 | 1 | `` |  |  |  |
| 435 | Obsessive-compulsive disorder | 3 | 1 | `` |  |  |  |
| 436 | Obstructive hypertrophic cardiomyopathy | 3 | 1 | *3 cand.* |  |  |  |
| 437 | Oesophageal cancer | 1 | 0 | `` |  | ✓ | Oesophageal cancer or gastro-oesophageal junction cancer |
| 438 | Oesophageal cancer or gastro-oesophageal junction cancer | 1 | 1 | *1 cand.* |  |  |  |
| 439 | Oesophageal candidiasis | 3 | 1 | *3 cand.* |  |  |  |
| 440 | Oligodendroglioma | 3 | 0 | `` |  | ✓ | Adult-type IDH-mutant astrocytoma or oligodendroglioma |
| 441 | Onchocerciasis | 1 | 1 | `` |  |  |  |
| 442 | Onychomycosis | 3 | 1 | `` |  |  |  |
| 443 | Opioid dependence | 5 | 1 | `` | [opioid-dependence](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/opioid-dependence.md) |  |  |
| 444 | Opioid-induced constipation | 1 | 1 | *1 cand.* |  |  |  |
| 445 | Oral | 3 | 0 | *3 cand.* |  | ✓ | Oral or labial herpes |
| 446 | Oral herpes | 3 | 0 | *3 cand.* |  | ✓ | Oral or labial herpes |
| 447 | Oral or labial herpes | 3 | 1 | *3 cand.* |  |  |  |
| 448 | Oropharyngeal candidiasis | 5 | 1 | *1 cand.* |  |  |  |
| 449 | Osteoarthritis | 1 | 1 | `` |  |  |  |
| 450 | Osteomyelitis | 3 | 1 | `` |  |  |  |
| 451 | Osteoporosis | 11 | 1 | `` | [osteoporosis](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/osteoporosis.md) |  |  |
| 452 | Paediatric high grade glioma | 3 | 1 | *3 cand.* |  |  |  |
| 453 | Paediatric low grade glioma | 3 | 1 | *3 cand.* |  |  |  |
| 454 | Paget disease of bone | 3 | 1 | `` |  |  |  |
| 455 | Pain | 19 | 2 | `` |  |  |  |
| 456 | Painful mouth | 1 | 1 | `` |  |  |  |
| 457 | Panic disorder | 5 | 1 | `` |  |  |  |
| 458 | Parkinson disease | 39 | 2 | `` |  |  |  |
| 459 | Paroxysmal nocturnal haemoglobinuria | 26 | 1 | `` |  |  |  |
| 460 | Pathological hyperprolactinaemia | 16 | 1 | *3 cand.* |  |  |  |
| 461 | Pathological hypersecretory conditions including Zollinger-Ellison syndrome and idiopathic hypersecretion | 4 | 1 | *2 cand.* |  |  |  |
| 462 | Patients requiring administration of fluorouracil by intravenous infusion | 1 | 1 | *1 cand.* |  |  |  |
| 463 | Patients requiring administration of fluorouracil by intravenous injection | 1 | 1 | *1 cand.* |  |  |  |
| 464 | Patients requiring doses greater than 20 mg per week | 1 | 1 | *1 cand.* |  |  |  |
| 465 | Patients unable to take a solid dose form of an ACE inhibitor | 1 | 1 | *2 cand.* |  |  |  |
| 466 | Patients undergoing in-vitro fertilisation | 1 | 1 | *3 cand.* |  |  |  |
| 467 | Pelvic inflammatory disease | 1 | 1 | `` |  |  |  |
| 468 | Peptic ulcer | 1 | 1 | `` |  |  |  |
| 469 | Peri-articular infiltration | 3 | 0 | *3 cand.* |  | ✓ | Local intra-articular or peri-articular infiltration |
| 470 | Perichondritis of the pinna | 1 | 1 | *3 cand.* |  |  |  |
| 471 | Pernicious anaemia | 2 | 1 | `` |  |  |  |
| 472 | Peroxisomal biogenesis disorders | 1 | 1 | *3 cand.* |  |  |  |
| 473 | Phaeochromocytoma | 1 | 1 | `` |  |  |  |
| 474 | Phenylketonuria | 6 | 1 | `` |  |  |  |
| 475 | Phobic | 1 | 0 | *3 cand.* |  | ✓ | Phobic or anxiety states |
| 476 | Phobic disorders | 1 | 1 | *1 cand.* |  |  |  |
| 477 | Phobic or anxiety states | 1 | 1 | *3 cand.* |  |  |  |
| 478 | Phobic states | 1 | 0 |  |  | ✓ | Phobic or anxiety states |
| 479 | Pneumocystis carinii pneumonia | 1 | 1 | *1 cand.* |  |  |  |
| 480 | Pneumocystis jiroveci pneumonia | 1 | 1 | *3 cand.* |  |  |  |
| 481 | Polycythemia vera | 4 | 1 | `` |  |  |  |
| 482 | Pre-exposure prophylaxis against human immunodeficiency virus infection | 2 | 1 | *3 cand.* |  |  |  |
| 483 | Precursor B-cell acute lymphoblastic leukaemia | 2 | 1 | `` |  |  |  |
| 484 | Preservation of bone mineral density | 2 | 1 | *3 cand.* |  |  |  |
| 485 | Preterm birth | 2 | 1 | *3 cand.* |  |  |  |
| 486 | Primary and relapsing superficial urothelial carcinoma of the bladder | 2 | 1 | *2 cand.* |  |  |  |
| 487 | Primary axillary hyperhidrosis | 2 | 1 | *3 cand.* |  |  |  |
| 488 | Primary biliary cholangitis | 6 | 1 | `` |  |  |  |
| 489 | Primary hyperoxaluria type 1 | 3 | 1 | *1 cand.* |  |  |  |
| 490 | Primary nocturnal enuresis | 10 | 1 | `` |  |  |  |
| 491 | Primary peritoneal cancer | 14 | 0 | *3 cand.* |  | ✓ | Epithelial ovarian, fallopian tube or primary peritoneal cancer |
| 492 | Primary severe restless legs syndrome | 1 | 1 | *3 cand.* |  |  |  |
| 493 | Probable invasive aspergillosis | 1 | 0 | *3 cand.* |  | ✓ | Definite or probable invasive aspergillosis |
| 494 | Proctitis | 1 | 1 | `` |  |  |  |
| 495 | Progressive familial intrahepatic cholestasis | 6 | 1 | `` |  |  |  |
| 496 | Progressive fibrosing Interstitial lung disease | 2 | 1 | *3 cand.* |  |  |  |
| 497 | Proliferative diabetic retinopathy and/or Diabetic macular oedema | 2 | 1 | *3 cand.* |  |  |  |
| 498 | Propionic acidaemia | 2 | 1 | `` |  |  |  |
| 499 | Prostatitis | 2 | 1 | `` |  |  |  |
| 500 | Proven | 2 | 0 | *3 cand.* |  | ✓ | Septicaemia, proven |
| 501 | Pruritus associated with chronic kidney disease | 2 | 1 | *3 cand.* |  |  |  |
| 502 | Pseudomonas aeruginosa infection | 6 | 2 | *3 cand.* |  |  |  |
| 503 | Psoriasis | 4 | 2 | `` | [psoriasis](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/psoriasis.md) |  |  |
| 504 | Psoriatic arthritis | 76 | 2 | `` |  |  |  |
| 505 | Pubertal induction | 4 | 1 |  |  |  |  |
| 506 | Pulmonary arterial hypertension | 45 | 1 | `` | [pulmonary-arterial-hypertension](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/pulmonary-arterial-hypertension.md) |  |  |
| 507 | Pulmonary embolism | 5 | 1 | `` |  |  |  |
| 508 | Pyridoxine dependent epilepsy | 1 | 1 | `` |  |  |  |
| 509 | Pyridoxine non-responsive homocystinuria | 3 | 1 | *3 cand.* |  |  |  |
| 510 | Reduction of breast cancer risk | 2 | 1 | *3 cand.* |  |  |  |
| 511 | Rehydration in intestinal failure | 1 | 1 | *3 cand.* |  |  |  |
| 512 | Rejection in patients following organ or tissue transplantation | 2 | 1 | *3 cand.* |  |  |  |
| 513 | Relapsing remitting multiple sclerosis | 2 | 1 | `` |  |  |  |
| 514 | Renal allograft rejection | 7 | 2 | *3 cand.* |  |  |  |
| 515 | Renal cell carcinoma | 2 | 1 | `` |  |  |  |
| 516 | Resected early stage non-small cell lung cancer | 3 | 1 | *3 cand.* |  |  |  |
| 517 | Resected gastric and gastroesophageal junction adenocarcinoma | 1 | 1 | *3 cand.* |  |  |  |
| 518 | Resected non-small cell lung cancer | 1 | 1 | *3 cand.* |  |  |  |
| 519 | Resected Stage IIIB, Stage IIIC or Stage IIID malignant melanoma | 5 | 1 |  |  |  |  |
| 520 | Respiratory tract infection | 1 | 1 | `` |  |  |  |
| 521 | Rheumatoid arthritis | 66 | 2 | `` | [rheumatoid-arthritis](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/rheumatoid-arthritis.md) |  |  |
| 522 | Risk of hypoglycaemia secondary to growth hormone deficiency in neonates/infants | 7 | 1 | *3 cand.* |  |  |  |
| 523 | SARS-CoV-2 infection | 8 | 1 | *3 cand.* |  |  |  |
| 524 | Scalp psoriasis | 1 | 1 | `` |  |  |  |
| 525 | Schistosomiasis | 1 | 1 | `` |  |  |  |
| 526 | Schizophrenia | 11 | 1 | `` |  |  |  |
| 527 | Scleroderma oesophagus | 6 | 1 | *1 cand.* |  |  |  |
| 528 | Secondarily infected traumatic skin lesions | 1 | 1 | *3 cand.* |  |  |  |
| 529 | Secondary hyperparathyroidism | 4 | 1 | `` |  |  |  |
| 530 | Seizures | 6 | 1 | *3 cand.* |  |  |  |
| 531 | Seizures associated with tuberous sclerosis complex | 2 | 1 | *3 cand.* |  |  |  |
| 532 | Seizures of the Lennox-Gastaut syndrome | 1 | 1 | *3 cand.* |  |  |  |
| 533 | Septicaemia | 2 | 0 | *3 cand.* |  | ✓ | Septicaemia, proven |
| 534 | Septicaemia, proven | 2 | 1 |  |  |  |  |
| 535 | Septicaemia, suspected | 2 | 1 |  |  |  |  |
| 536 | Short stature and poor body composition due to Prader-Willi syndrome | 5 | 1 | *3 cand.* |  |  |  |
| 537 | Short stature and slow growth | 13 | 1 | *2 cand.* |  |  |  |
| 538 | Short stature associated with biochemical growth hormone deficiency | 18 | 1 | *3 cand.* |  |  |  |
| 539 | Short stature associated with chronic renal insufficiency | 11 | 1 | *3 cand.* |  |  |  |
| 540 | Short stature associated with Turner syndrome | 10 | 1 | *3 cand.* |  |  |  |
| 541 | Short stature due to short stature homeobox gene disorders | 10 | 1 | *3 cand.* |  |  |  |
| 542 | Small lymphocytic lymphoma | 26 | 0 | `` |  | ✓ | Chronic lymphocytic leukaemia or small lymphocytic lymphoma |
| 543 | Social anxiety disorder | 8 | 1 | `` |  |  |  |
| 544 | Soft tissue sarcoma | 5 | 1 | *3 cand.* |  |  |  |
| 545 | Solar keratosis | 2 | 2 | `` |  |  |  |
| 546 | Solid tumours with confirmed neurotrophic tropomyosin receptor kinase gene fusion | 4 | 2 | *2 cand.* |  |  |  |
| 547 | Solid tumours with confirmed neurotrophic tropomyosin receptor kinase gene fusion where treatment with this drug is/was initiated in a child | 1 | 1 |  |  |  |  |
| 548 | Spasmodic torticollis | 2 | 1 | `` |  |  |  |
| 549 | Spasticity of the lower limb following an acute event | 2 | 1 | *3 cand.* |  |  |  |
| 550 | Spasticity of the upper limb | 2 | 1 | *3 cand.* |  |  |  |
| 551 | Spasticity of the upper limb following an acute event | 1 | 1 | *3 cand.* |  |  |  |
| 552 | Spinal muscular atrophy | 22 | 2 | `` |  |  |  |
| 553 | Squamous cell cancer of the hypopharynx | 3 | 0 | *3 cand.* |  | ✓ | Squamous cell cancer of the larynx, oropharynx or hypopharynx |
| 554 | Squamous cell cancer of the larynx | 3 | 0 | *1 cand.* |  | ✓ | Squamous cell cancer of the larynx, oropharynx or hypopharynx |
| 555 | Squamous cell cancer of the larynx, oropharynx or hypopharynx | 3 | 1 | *3 cand.* |  |  |  |
| 556 | Squamous cell cancer of the oropharynx | 3 | 0 | *3 cand.* |  | ✓ | Squamous cell cancer of the larynx, oropharynx or hypopharynx |
| 557 | Squamous cell carcinoma of the larynx | 1 | 0 | *3 cand.* |  | ✓ | Squamous cell carcinoma of the oral cavity, pharynx or larynx |
| 558 | Squamous cell carcinoma of the oral cavity | 1 | 0 | *3 cand.* |  | ✓ | Squamous cell carcinoma of the oral cavity, pharynx or larynx |
| 559 | Squamous cell carcinoma of the oral cavity, pharynx or larynx | 1 | 1 | *3 cand.* |  |  |  |
| 560 | Squamous cell carcinoma of the pharynx | 1 | 0 | *3 cand.* |  | ✓ | Squamous cell carcinoma of the oral cavity, pharynx or larynx |
| 561 | Stage IIIB, IIIC, IIID or Stage IV malignant melanoma | 2 | 1 |  |  |  |  |
| 562 | Stage IIIB, Stage IIIC or Stage IIID malignant melanoma | 1 | 1 |  |  |  |  |
| 563 | Stage IIIB/ IIIC or Stage IV non-small cell lung cancer | 2 | 1 | *2 cand.* |  |  |  |
| 564 | Stage IV non-small cell lung cancer | 2 | 0 | *3 cand.* |  | ✓ | Stage IIIB/ IIIC or Stage IV non-small cell lung cancer |
| 565 | Stage Parkinson disease | 2 | 1 | *3 cand.* |  |  |  |
| 566 | Staphylococcal infection | 5 | 1 | `` |  |  |  |
| 567 | Staphylococcal infections | 1 | 1 | *3 cand.* |  |  |  |
| 568 | Staphylococcus aureus infection | 1 | 1 | `` |  |  |  |
| 569 | Stimulation of follicular development | 2 | 1 | *3 cand.* |  |  |  |
| 570 | Streptococcal infections | 2 | 1 | *3 cand.* |  |  |  |
| 571 | Stroke | 2 | 0 | `` | [stroke](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/stroke.md) | ✓ | Stroke or systemic embolism |
| 572 | Stroke embolism | 2 | 0 | *3 cand.* |  | ✓ | Stroke or systemic embolism |
| 573 | Stroke or systemic embolism | 2 | 1 | *3 cand.* |  |  |  |
| 574 | Strongyloidiasis | 2 | 1 | `` |  |  |  |
| 575 | Subfoveal choroidal neovascularisation | 10 | 1 | *3 cand.* |  |  |  |
| 576 | Superficial basal cell carcinoma | 2 | 1 | `` |  |  |  |
| 577 | Supra-ventricular cardiac arrhythmias | 1 | 1 | *1 cand.* |  |  |  |
| 578 | Suspected | 2 | 0 | *3 cand.* |  | ✓ | Septicaemia, suspected |
| 579 | Suspected Plasmodium falciparum malaria | 2 | 1 | *3 cand.* |  |  |  |
| 580 | Systemic aspergillosis | 1 | 1 | `` |  |  |  |
| 581 | Systemic embolism | 2 | 0 |  |  | ✓ | Stroke or systemic embolism |
| 582 | Systemic histoplasmosis | 1 | 1 |  |  |  |  |
| 583 | Systemic juvenile idiopathic arthritis | 15 | 1 | `` |  |  |  |
| 584 | Systemic light chain amyloidosis | 3 | 1 | *3 cand.* |  |  |  |
| 585 | Systemic lupus erythematosus | 2 | 1 | `` |  |  |  |
| 586 | Systemic sporotrichosis | 1 | 1 |  |  |  |  |
| 587 | Tapeworm infestation | 1 | 1 | *3 cand.* |  |  |  |
| 588 | Terminal disease | 1 | 1 | *3 cand.* |  |  |  |
| 589 | Terminal malignant neoplasia | 4 | 1 | *3 cand.* |  |  |  |
| 590 | Termination of an intra-uterine pregnancy | 1 | 1 | *3 cand.* |  |  |  |
| 591 | The onset of lactation | 1 | 1 | *3 cand.* |  |  |  |
| 592 | Thiamine deficiency | 2 | 1 | `` |  |  |  |
| 593 | Thrombocytopenia | 12 | 1 | `` |  |  |  |
| 594 | Thyroid cancer | 2 | 1 | `` |  |  |  |
| 595 | Tinea pedis | 1 | 1 | `` |  |  |  |
| 596 | Transplant rejection | 4 | 1 | `` |  |  |  |
| 597 | Transthyretin amyloid cardiomyopathy | 2 | 1 | *1 cand.* |  |  |  |
| 598 | Treatment refractory generalised myasthenia gravis | 9 | 1 | *3 cand.* |  |  |  |
| 599 | Triple negative breast cancer | 1 | 1 | `` |  |  |  |
| 600 | Triple-negative breast cancer | 2 | 1 | `` |  |  |  |
| 601 | Tuberous sclerosis complex | 2 | 1 | *3 cand.* |  |  |  |
| 602 | Tumour-induced osteomalacia | 3 | 1 | `` |  |  |  |
| 603 | Type 1 diabetes | 1 | 1 | `` |  |  |  |
| 604 | Type I, II or IIIa spinal muscular atrophy | 3 | 1 | *3 cand.* |  |  |  |
| 605 | Type III Short bowel syndrome with intestinal failure | 3 | 1 | *3 cand.* |  |  |  |
| 606 | Type IIIB/IIIC spinal muscular atrophy | 7 | 1 | *3 cand.* |  |  |  |
| 607 | Tyrosinaemia | 2 | 1 | *3 cand.* |  |  |  |
| 608 | Ulcerative colitis | 73 | 3 | `` |  |  |  |
| 609 | Ulcerative proctitis | 2 | 1 | `` |  |  |  |
| 610 | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour | 4 | 1 | *3 cand.* |  |  |  |
| 611 | Unresectable, well-differentiated malignant pancreatic neuroendocrine tumour or extra-pancreatic neuroendocrine tumour | 2 | 1 | *2 cand.* |  |  |  |
| 612 | Untreated multiple myeloma | 4 | 1 | *3 cand.* |  |  |  |
| 613 | Upper and lower respiratory tract infections | 1 | 1 | *3 cand.* |  |  |  |
| 614 | Urea cycle disorders | 6 | 1 | *3 cand.* |  |  |  |
| 615 | Urethritis | 2 | 1 | `` |  |  |  |
| 616 | Urinary incontinence | 2 | 1 | `` | [urinary-incontinence](https://github.com/Arepo-Medtech/GUIDELINES/blob/main/guidelines/urinary-incontinence.md) |  |  |
| 617 | Urinary symptoms | 1 | 1 | `` |  |  |  |
| 618 | Urinary tract infection | 1 | 1 | `` |  |  |  |
| 619 | Urothelial cancer | 5 | 1 |  |  |  |  |
| 620 | Urothelial carcinoma | 3 | 1 | *3 cand.* |  |  |  |
| 621 | Urothelial toxicity | 2 | 1 |  |  |  |  |
| 622 | Use in a hospital | 1 | 1 | *1 cand.* |  |  |  |
| 623 | Use in patients receiving palliative care | 3 | 1 | *3 cand.* |  |  |  |
| 624 | Uveal melanoma | 4 | 1 | *2 cand.* |  |  |  |
| 625 | Uveitis | 3 | 1 | `` |  |  |  |
| 626 | Vasoactive intestinal peptide secreting tumour | 5 | 1 | `` |  |  |  |
| 627 | Venous thromboembolism | 10 | 2 | *3 cand.* |  |  |  |
| 628 | Venous ulcer | 2 | 1 | *3 cand.* |  |  |  |
| 629 | Ventricular cardiac arrhythmias | 1 | 1 | *3 cand.* |  |  |  |
| 630 | Vitamin B12 deficiencies other than pernicious anaemia | 2 | 1 | *3 cand.* |  |  |  |
| 631 | Vitamin D-resistant rickets | 3 | 1 | `` |  |  |  |
| 632 | Von Hippel-Lindau disease | 2 | 1 | *1 cand.* |  |  |  |
| 633 | Waldenstrom macroglobulinaemia | 2 | 1 | `` |  |  |  |
| 634 | Whipworm infestation | 1 | 1 | *1 cand.* |  |  |  |
| 635 | WHO Class III, IV or V lupus nephritis | 2 | 1 | *3 cand.* |  |  |  |
| 636 | Wounds | 6 | 1 | *3 cand.* |  |  |  |
| 637 | X-linked hypophosphataemia | 2 | 1 | *3 cand.* |  |  |  |
| 638 | Yeast infection | 2 | 0 |  |  | ✓ | Fungal or yeast infection |
| 639 | Zollinger-Ellison syndrome | 4 | 1 | `` |  |  |  |
