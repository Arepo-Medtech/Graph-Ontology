# The medical multigraph, as built

*23 September 2026. Design: `docs/weighted-graph-design.md`. Register (the contract): `reference/graph_predicates.json`.*

**1,509,033 nodes, 7,492,883 edges, 204 edge types, 53 vocabularies — every edge validated against the register.** (The family table below is the first build; the bridges are listed in *Non-pharmacological bridges*, *Lab results → findings*, *Signs → diagnoses*, *Illnesses to ICD-10-CM*, *Pathology units*, *Anatomy, organisms, non-laboratory LOINC and MBS*, *Radiology*, *Cross-references*, *Reference sets*, *Genes, rare diseases and pathways*, *ICD-10 ↔ ICD-11*, *UMLS Metathesaurus* and *How a drug works*.)
Written to `out/graph.duckdb` (287 MB, git-ignored), rebuilt from source in about seven minutes.

## What makes it a graph rather than a pile of tables

- **Edges are rows.** Subject, predicate, object, source, method, tier, state, pin, attributes. Parallel edges — the
  same fact from two sources — are two rows, and their disagreement is a query, not a bespoke `_check` table.
- **Nodes are keyed (vocabulary, code) and never merged across vocabularies.** The same substance in SNOMED and
  RxNorm is two nodes and one identity edge. Within SNOMED, one key per SCTID: an AMT substance and DrugCentral's
  SNOMED id for the same substance are *one node*, which is why DrugCentral joins the Australian products with no
  matching at all.
- **The register is a contract.** `build_edges.py` refuses an unregistered predicate, a subject or object in the wrong
  vocabulary, an edge with no source (rule zero), or any edge of a type registered as `needs_source` /
  `needs_binding` / `needs_scoring`. A refusal aborts the build. A new SNOMED attribute in a later edition therefore
  fails the build until `graph_register.py` is re-run on purpose.
- **Rejected edges are kept and never followed.** The 110 OMOP product mappings rejected in `docs/omop-drug-audit.md`
  are present with `state = rejected`, so the refused answer survives for audit; `graph_walk.py` skips them.
- **Every walk has a visited set and a depth cap**, so the graph's cycles (salt ↔ base, is-a with its reverse,
  drug → class → drugs in class → drug) cannot loop.

## What is in it

| family | source (pin) | edges |
|---|---|---:|
| SNOMED CT-AU: poly-hierarchy, AMT structure, finding site, morphology, method, laterality, occurrence, clinical course … (115 attribute types) | RF2 snapshot 20260831 | 2,175,509 |
| LOINC axes (component, property, time, system, scale, method) and answers | LOINC 2.82 via Athena | 687,434 |
| product → ATC, **PBS and OMOP as parallel edges** | PBS 4333 / Athena 29-AUG-26 | 573,569 |
| HPO disease → phenotype, present and absent, with frequency / onset / sex | HPO 2026-09-02 | 268,906 |
| AMT product → standard drug (direct 102,656 · rejected 110 · indirect 5,971) | Athena 29-AUG-26 | 108,737 |
| MONDO is-a, and exactMatch → SNOMED / ICD-10-CM / OMIM / Orphanet | MONDO 2026-09-01 | 77,570 |
| PBS: AMT → item → restriction → indication | PBS schedule 4333 | 61,237 |
| DrugCentral: indication 38,399 (all three kinds) · SNOMED 7,470 · ATC 5,148 · RxNorm 3,539 | DrugCentral 2023-11-01 | 54,556 |
| HPO is-a | HPO 2026-09-02 | 24,436 |
| substance → standard ingredient | review decisions, scored route, RxNav | 4,689 |
| ICD-10-CM → SNOMED (for MONDO's codes; exists to score MONDO — now all codes, see *Illnesses to ICD-10-CM*) | Athena 29-AUG-26 | 1,968 |
| corpus condition → SNOMED binding | `reference/snomed_bindings.json` | 265 |

By the five-kind frame (`category` in the register): relation 1,013,035 · structure 1,008,455 · classification
578,717 · rationality 418,862 · evidence 310,348 · adjective 216,128 · identity 157,656 · temporality 139,152 ·
action 131,320 · commercial 58,194.

**The SNOMED attribute categories are derived, not asserted.** `graph_register.py` classes each of the 115 attribute
types from its name for time and quantity, and otherwise from what it actually points at in the release: *Method*
(objects are "doing" qualifiers) is **action**, *Laterality* and *Has interpretation* are **adjective**, *Occurrence*
and *Clinical course* are **temporality**, units are **rationality**.

## Linkage routes, scored

Each cross-vocabulary route is scored against an independent second path; its tier is earned from the Wilson lower
bound (`reference/graph_tiers.json`) and written onto its edges by `graph_report.py`.

| route | independent path | both fire | agreement | Wilson lower | tier |
|---|---|---:|---:|---:|:-:|
| MONDO → SNOMED | MONDO → ICD-10-CM → OMOP → SNOMED | 1,769 | 92.2% same concept or on one is-a line (81.1% exact); 138 contradicted | 0.909 | **2** |
| DrugCentral → RxNorm | DrugCentral → SNOMEDCT_US → OMOP → RxNorm | 2,946 | 98.4% | 0.979 | **2** |

**A mistake of mine, caught by the score.** The first DrugCentral run scored **62.4% — inadmissible.** The fault was
my loader, not DrugCentral: 815 of its RxNorm ids are precise ingredients (salts — *amantadine hydrochloride*) and
368 are brand names (*Klonopin*), and I had loaded them as "is ingredient" and compared them to the base ingredient.
Lifted through RxNorm's own `Form of` / `Brand name of`, with the original id kept on the edge, the route scores
98.4%. The 47 remaining disagreements are mostly one substance with two RxNorm concepts, but show one systematic
DrugCentral quirk worth knowing: **prodrugs recorded as their active metabolite** — ramipril → *ramiprilat*, and
likewise perindopril, quinapril, trandolapril, fosinopril, moexipril, oseltamivir, hetacillin (→ ampicillin),
fosfestrol — plus one plain error, *loteprednol etabonate → digoxin*. Patients are prescribed the prodrug.

## Coverage

| question | answer |
|---|---|
| Compendium RxNorm ingredients present in DrugCentral | **2,480 of 4,442**, of which 1,958 have a labelled indication |
| Corpus conditions (SNOMED-bound) reached by MONDO | **179 of 265** directly; 168 through a SNOMED ancestor |
| HPO-annotated diseases joined to MONDO | **12,772 of 12,867** |
| Products with both a PBS and an OMOP ATC class | 9,040 — **8,870 agree, 170 share no class** (the parallel-edge disagreement, now a query) |
| SNOMED CT-AU concepts with more than one parent | 169,542 of 555,791 (30.5%) — the whole AU release; the 42% quoted earlier was standard concepts across Athena's SNOMED, a different population |

## What the sources could not give

- **HPO phenotypes have no SNOMED path of their own.** `hp.obo` (2026-09-02) carries no SNOMED or UMLS
  cross-references — its top xrefs are Fyler, NCIT and MedDRA (92). They are now bridged through UMLS instead; see
  *Signs and symptoms* above.
- **HPO is rare-disease evidence.** Its annotation file describes itself as "HPO annotations for rare diseases"
  (OMIM, DECIPHER, Orphanet). Its frequency classes are the nearest thing to P(sign | disease) — sensitivity — but
  give no specificity and say little about primary-care conditions. `sign_suggests` stays `needs_source`.
- **Sign → diagnosis likelihood ratios, priors, therapeutic drug monitoring** — registered, not loadable, each with
  the reason in the register.

## Non-pharmacological bridges

A vocabulary-to-vocabulary matrix of the first build showed three families that touched nothing else: **LOINC**
(183,785 nodes, 0 edges out), **HPO phenotypes** (19,894 — joined to SNOMED only through their diseases), and the
**653 PBS indications** (a dead end at free text). Each is a different kind of bridge.

**Measurements — LOINC → SNOMED (built, Tier 2).** Athena already places LOINC lab tests under SNOMED measurement
concepts: 22,003 `Is a` (21,278 terms under 3,615 concepts), 562 `Maps to`, 107 `Maps to value`. It is a lookup from a
source already on disk; it had simply not been loaded. From the SNOMED measurement, SNOMED CT-AU's own attributes
carry the chain onward — its *Component* (the analyte), the observable it measures, and *Interprets*, which joins an
observable to the findings that read it. Scored by comparing the LOINC term's COMPONENT with the SNOMED target's
*Component*: 86.5% share a significant word over 19,653 terms (Wilson lower bound 0.860) → **Tier 2**; 45% are equal
names. The check is conservative — read by hand, the "inconsistent" rows are almost all synonyms the check cannot see
(*lutropin* / *luteinizing hormone*, *thyrotropin* / *TSH*, *9-hydroxyrisperidone* / *paliperidone*, which are the same
molecule) because the compendium stores SNOMED preferred terms only. **It reaches 21,947 of 104,720 LOINC terms
(21%)**: Athena bridges lab tests; surveys, clinical observations, radiology and document codes remain an island.
SNOMED International's LOINC Ontology is not on the public Ontoserver; it is now loaded from the release itself — see *Lab results → findings*.

**Foreign SNOMED ids → the Australian release (built).** 1,088 SCTIDs reached the graph from sources that are not
Australian — DrugCentral's US conditions (177 of its 2,641 condition concepts), Athena's LOINC targets in other
extensions (482 of 3,847). `sct:au_nearest_ancestor` joins each to its nearest ancestor that SNOMED CT-AU carries;
**499 are lifted**, and the other 589 have no ancestry in Athena at all.

**Conditions — PBS indication text → SNOMED CT-AU (built, exact matches only).** Text to concept is a gap, so only an
exact match becomes an edge: the normalised text equals a SNOMED CT-AU 20260831 preferred term or synonym, found on
the live Ontoserver, after removing parentheticals and leading severity or course words — which are kept on the edge
as `stripped_qualifier`, beside PBS's own severity and episodicity. The condition is the noun; the adjective rides on
the edge. (`scripts/bind_indications.py`; the stripper first removed only one qualifier, so *Severe active rheumatoid
arthritis* failed to reach *Rheumatoid arthritis*, and was fixed to strip repeatedly.)

| | |
|---|---:|
| PBS indications bound exactly | **312 of 653** (204 preferred term, 68 synonym, 40 after stripping qualifiers) |
| AMT products whose PBS indication now reaches a SNOMED condition | **5,899** |
| PBS indications left as candidate frames for a person | 341 — `reference/pbs_indication_bindings.json` |
| unbound corpus conditions that now bind exactly | 14 of 374 — recommendations in `reference/corpus_condition_candidates.json`, not applied: `snomed_bindings.json` belongs to the binder and its review loop |
| check against the existing binder, over its 265 bound conditions | 257 bound by both, **257 on the same concept, 0 different** — agreement between two exact-match implementations, not a precision measurement |

**Signs and symptoms — HPO phenotype → SNOMED CT-AU, through UMLS (built, Tier 2).** UMLS places an HPO term and a
SNOMED concept under one CUI when its editors judge them synonymous; the UTS crosswalk (19,891 phenotypes, about an
hour at a polite rate; key in `.env`, never printed) returned SNOMED concepts for **6,029**. A shared CUI groups
near-synonyms as well as synonyms, so the links were split and hand-checked:

| links | hand check | tier | handling |
|---|---|:-:|---|
| SNOMED name **equals** the HPO label | **40 / 40** (Wilson lower bound 0.912) | **2** | **2,754 edges**, 2,614 phenotypes, all on concepts active in SNOMED CT-AU |
| SNOMED name **differs** | **34 / 40** (85%, lower bound ~0.71) | inadmissible | **4,533 candidates** for a person, in `cache/umls/` — not edges |

The errors in the second class are almost all **narrowing**: *Polycythemia → Polycythemia vera*, *Retinal hole →
Retinal round hole*, *Tardive dyskinesia → Neuroleptic-induced tardive dyskinesia*; a few are related but different
(*Anorexia → Refusing food*). The filter works **edge by edge**, because a same-named term's other co-CUI targets are
exactly those narrowings (*Supernumerary tooth* also landing on *Supplemental tooth*).

*A test that measured the wrong thing.* The first score was hierarchy preservation — where HPO says A is-a B, is A's
SNOMED concept at or below B's? It read 62%, "inadmissible". Read by hand, the failures were mostly correct mappings
where SNOMED organises the same concepts differently (*Spastic paraparesis* is not under *Paraparesis* in SNOMED): it
measures whether two ontologies agree in structure, not whether a mapping is right. It is kept as a diagnostic (71.7%
on the loaded edges) and the tier comes from the hand check. It is the third time in this build that a first score was
wrong about its own question — DrugCentral's salts, LOINC's synonyms, HPO's hierarchy — and each time reading the
failures found it.

UMLS is licensed: the crosswalk and the candidates stay in `cache/umls/` (git-ignored). **30% of HPO** is bridged by
this route; the rest has no SNOMED concept under a shared CUI.

## Three walks

```bash
# the PBS indications of an adalimumab pack: 10, through its restrictions
.venv/bin/python scripts/graph_walk.py SCT:967341000168102 --follow pbs:lists,pbs:has_restriction,pbs:restricted_to --depth 3

# myocardial infarction's poly-hierarchy: two parents (ischaemic heart disease, myocardial necrosis)
.venv/bin/python scripts/graph_walk.py SCT:22298006 --follow sct:116680003 --depth 3

# four sources, three vocabularies: Azamun (AMT) -> azathioprine (SNOMED CT-AU) -> DrugCentral 269 -> 14 labelled indications
.venv/bin/python scripts/graph_walk.py SCT:6383011000036106 --follow sct:127489000,~drugcentral:snomed,drugcentral:indication --depth 3
```

## Lab results → findings: the LOINC Ontology and *Interprets*

**The LOINC Ontology (built).** The SNOMED CT LOINC Extension 20260321 (module 11010000107, the joint SNOMED
International / Regenstrief release, read in place from `~/Documents/ONTOLOGIES`) models 46,024 LOINC terms as SNOMED
observable entities, each defined by Component, Property, Time aspect, Direct site, Scale, Technique …: **287,753
relationships**, loaded as ordinary `sct:` edges on the same predicates as SNOMED CT-AU (the register now takes its
attribute types from both releases — 116, *Process agent* from the extension only). The LOINC number ↔ SCTID link is
the release's identifier table, a lookup: **42,881 `loinc:sct_concept`** (42,239 in the Observation refset — result
codes; 787 marked *Discouraged*) and **2,133 `loinc:order_grouper_concept`** — a separate predicate on purpose, since
the release notes say order groupers must not be used as result codes. The two LOINC routes cross-check each other:
Athena's placement of a LOINC term under a SNOMED measurement has the **same analyte, by code, as the LOINC Ontology
for 94.8%** of the 17,338 terms both cover, and a consistent one (equal, or one subsumes the other) for 96.8% (Wilson
lower bound 0.966) → Tier 2 now rests on codes, not names; 549 contradict.

**Why is-a does not close the chain.** *Interprets* (363714003) joins a finding to what it reads, beside *Has
interpretation* (above / below / within reference range, detected …) in the same role group. The expectation was that
a LOINC term would reach its findings by climbing is-a from its observable. It reaches **14**. SNOMED's lab findings
interpret measurement **procedures** (*Random blood sugar low* interprets *Random blood glucose measurement*); the
LOINC Ontology places LOINC terms under **observables**. The two hierarchies meet only on the analyte.

**The analyte bridge — `loinc:interpreted_in_finding` (built, Tier 2).** A LOINC term reaches a finding when its
observable and the finding's *Interprets* target share a **Component** and the LOINC specimen is the target's or below
it; the finding's interpretation in the same role group rides on the edge (`attrs.interpretation`), with the target,
the component and both specimens. It is **definitional, not diagnostic**: diabetic ketoacidosis is *defined* partly by
a raised glucose, not diagnosed by one. **15,912 edges, 1,110 LOINC terms, 418 findings, 18 interpretation values**
(glucose 645 terms, calcium 83, protein and albumin 21 each, magnesium, *Treponema pallidum* antibody, the
catecholamines …).

The join as first written was wrong 12 times in 40, and each failure became a rule (`reference/interprets_handcheck.json`):

| failure seen in the hand check | rule |
|---|---|
| a broader LOINC specimen (*Glucose in Specimen* → ketoacidosis; *Microalbumin in Body fluid* → microalbuminuria) | the LOINC specimen equals the target's or is below it; a specimen is required on both sides |
| a refined target (*Random blood glucose measurement* for a timed or fasting term; *Urine protein electrophoresis* for a plain urine protein) | only the most general target for its component and specimen: none of its is-a ancestors carries both |
| ratios and differences (*Calcium/Albumin*; a glucose concentration difference; a urea nitrogen mass ratio) | no *Relative to* on the observable, no LOINC PROPERTY of kind ratio or difference |
| components the extension models lossily (*Protein.abnormal band* → Protein; *Other cells*, *Unidentified cells*, *Cells counted.total* → Cell) | those LOINC component heads are excluded, by name, as a reviewed list |

Scored on **two fresh samples drawn after the rules were fixed**: 40 edges at random (40/40 — dominated by glucose ×
diabetes findings, as the edges are) and one random edge from each of 40 random findings (39/40; the miss, *Unidentified
cells*, is the lossy-component class and is now excluded too). **79/80, Wilson lower bound 0.933 → Tier 2**, earned by
`graph_report.py` from the hand-check file.

**The same bridge through Athena — parallel edges, a second witness (built, Tier 2).** Athena files a LOINC term
under a SNOMED measurement procedure; where a finding interprets **that procedure itself** (never an is-a ancestor —
*Evaluation procedure* and *Measurement* reach ~20,000 terms and a few dozen generic findings, which is what inflated the
first reach figure to 20,317 terms), the term reaches the finding. These are `loinc:interpreted_in_finding` edges too,
told apart by `method`, each route with its own tier — as `in_atc_class` keeps PBS and OMOP side by side.

Unrestricted, the route failed: **53/80**. Where it agreed with the analyte join it was right 26 times in 27; on the
edges only Athena makes, **27 in 53**. Athena's procedures are often specimen-less (*Sodium measurement*, *ANA
measurement*), so sodium in breast milk reached chronic hyponatraemia, pleural-fluid pH reached ketoacidosis and urine
red cells reached haemolytic anaemia; ratios and HEDIS value-set codes came through too. What was built is restricted
by the LOINC Ontology: result codes only (Observation refset, ACTIVE, not Discouraged), the analyte join's ratio rules,
a reviewed list of **fraction analytes** (free and bioavailable testosterone, indirect bilirubin … — a fraction's level
is not the whole's) where the LOINC component differs from the target's, and the specimen:

| route (`method`) | edges | LOINC terms | findings | hand check, new edges only | tier |
|---|---:|---:|---:|---|:-:|
| same component, specimen at or below (the analyte join) | 15,912 | 1,110 | 418 | 79 / 80 (lower bound 0.933) | 2 |
| Athena placement, specimen at or below the target's | 15,724 | 969 | 390 | 39 / 40 (0.871) | 2 |
| Athena placement, **specimen-less target, blood-family LOINC specimen** | 8,402 | 1,917 | 475 | 40 / 40 (0.912) | 2 |

The third row rests on an assumption the route supplies — that a finding on a specimen-less *Cortisol measurement*
reads blood — so it is scored alone; it held on all 40. The one miss in the second was free testosterone reaching
*Serum testosterone below reference range*, which is why fractions are excluded. A rule by is-a was tried first and
dropped: SNOMED files *Sodium electrolyte* under *Sodium* (126 correct edges would have gone) and does not file *Free
testosterone* under *Testosterone*.

**Together: 3,114 LOINC terms reach 869 findings they define** (from 1,110 and 418). The two witnesses make 13,801 of
the same edges; for the 882 LOINC terms both reach, **826 (93.7%) get exactly the same findings**. The analyte join
alone makes 2,111 edges, Athena alone 10,325.

## Signs → diagnoses: likelihood ratios (Tier 2, awaiting sign-off)

The evidence layer the design was built around: how much a finding moves the odds of a diagnosis. **252 edges, 145
findings, 57 diagnoses** in the graph, from **154 published diagnostic-accuracy reviews** (837 records) — the JAMA *Rational Clinical Examination*
series (1992–2026) and meta-analyses of bedside findings in primary care, emergency, paediatric and musculoskeletal
journals, Cochrane among them. Heart failure, pneumonia (adults and children), meningitis, UTI, strep throat,
influenza and COVID-19, ACS and MI, PE and DVT, aortic dissection, AAA, PAD, ACL, meniscus, rotator cuff, hip OA and
DDH, carpal tunnel, radiculopathy, glaucoma, conjunctivitis, concussion, child abuse, pyloric stenosis …

*Where the numbers come from.* The full texts are not open; their **PubMed abstracts** are. `scripts/pubmed_fetch.py`
harvests and caches them (`cache/pubmed/`, git-ignored — publisher text); `reference/diagnostic_accuracy.json` keeps
**only numbers, PMID, population and setting** (398 records). Every abstract read is accounted for: a source that gave
nothing usable is listed in `sources_without_usable_numbers` **with the kind of thing it held instead** —
QUESTIONNAIRE, SCORE, LAB/IMAGING, PROGNOSIS, RANGE, COMPOSITE — the queue for the next passes.

*Rules for this pass:* one named bedside finding (symptom, sign, history item) with its own number; no ranges across
findings; no scores, questionnaires, lab or imaging tests, or prognosis; demographic thresholds (age, sex) left out; a
superseded version of a review (Cochrane COVID-19 2020, 2021) gives way to its update; a value the abstract prints
oddly is transcribed as published with a note (a repeated interval; a bivariate LR+ that does not equal sens/(1−spec));
a value that cannot be verified mechanically ("3. 1") is left out; an infinite LR (specificity 100%) is left out.

*Two checks, and the edge is only as good as the weaker.*

| step | how checked | result | tier |
|---|---|---|:-:|
| transcription | `scripts/verify_diagnostic_accuracy.py`: every number against its cached abstract (the Lancet's `0·62` read as 0.62) | **398/398** (after it caught 1.80 written as 1.8) | 1 (lower bound 0.990) |
| binding to SNOMED CT-AU | exact term on the live Ontoserver; then **every distinct binding read** against the source's words | 170/182 right first time | **2** (0.888) |

The 12 wrong bindings were all near-synonym fallbacks proposed by the transcriber and matched exactly: *dry mucous
membranes* → *Aptyalism*, *furrowed tongue* → *Plicated tongue* (the congenital fissured tongue), *pulse differential*
→ *Pulse deficit* (which is apex–radial), *Barlow and Ortolani* → Ortolani alone … They were removed, so those records
are candidates (166 in all, each with the Ontoserver's nearest concepts) — never a looser edge. **Parallel sources**:
19 finding–diagnosis pairs have two or more independent reviews (Lachman for ACL has four); **all 19 agree on the
direction** of the LR, and none is merged.

*Two predicates.* `finding_lr_if_present` / `finding_lr_if_absent` (a present finding can *lower* the odds — vaginal
discharge, LR 0.3–0.65 across two reviews, for UTI; LR− is its own edge). 50 edges are derived from pooled
sensitivity and specificity and marked so, with no invented interval. Every edge carries its population and setting
(the design's `calibrated_on`) — an emergency-department LR is never silently a primary-care one.

### Passes 2–4: scores, tests, prognosis and ranges

The first pass took bedside findings only; every source it read was listed with what it held instead. Passes 2–4
re-read **the whole canon** — all 318 cached abstracts, including the imaging- and laboratory-titled reviews the first
pass filtered out (which is how six bedside findings from the JAMA headache review, filtered out by "neuroimaging" in
its title, were found and added) — for everything else with a number: **837 records from 154 reviews, all 837
verified** against their abstracts (the verifier caught a cut-off written as a word, "three").

| kind | records | predicate | subject bound in |
|---|---:|---|---|
| bedside finding (incl. 38 range-only) | 471 | `finding_lr_if_present` / `_absent` | clinical finding, situation, event |
| lab / imaging / ECG test (21 range-only) | 226 | `test_result_lr` — `attrs.result` is the threshold ("BNP < 100 pg/mL") | procedure, observable, result finding |
| score, questionnaire, decision rule (5 range-only) | 120 | `score_result_lr` — `attrs.result` is the band ("HEART 7–10") | assessment scale, observable, staging and scales |
| prognosis (a later outcome) | 20 | `finding_lr_for_outcome` | finding / scale; object is the outcome |

A **range across studies** is stored as `attrs.lr_range` with no point estimate (method *LR range across studies*): it
can be shown, never multiplied. Interval LRs (synovial white count 0–25, 25–50, 50–100 × 10⁹/L) are separate edges,
one per band; an infinite band is left out. Duplicate publications (the same pooled numbers in PLoS One and HTA; in
two athletics journals) are recorded once.

**Binding decides what enters the graph.** Every distinct binding was read against the source's words, and the tier
is set **per binding family**:

| family | read | right first time | lower bound | tier | in the graph |
|---|---:|---:|---:|:-:|---|
| bedside findings | 203 | 186 | 0.870 | **2** | 252 edges |
| tests, scores, prognosis | 79 | 65 | 0.724 | **inadmissible** | **held**: 130 records bound, kept as candidates |

The test-and-score errors are specific: a combination bound to one of its parts ("fever *and* presentation within 3
days" → Fever), a composite outcome narrowed ("death *or* poor neurological outcome" → Death; "severe alcohol
withdrawal" → *delirium*), a specific test broadened (rheumatoid factor *IgA* → any RF; inhibin *B* → inhibin), a
reading turned into a diagnosis (a systolic of 140 → *Systolic hypertension*), and the wrong route (four
transcervical and point-of-care ultrasound records → *Ultrasound of oral cavity*). Because the family's first-pass
precision is below Tier 2, none of its 130 bound records is an edge yet; each carries its proposed concept for a person
(`reference/diagnostic_accuracy_bindings.json`), and the build admits the family automatically once its measured
binding earns Tier 2. The terminology is already matched: 9 of the 41 proposed test procedures reach **60 LOINC codes**
through the graph's `loinc:is_a_snomed` / `loinc:sct_concept` edges — BNP, CRP, ESR, troponin … — so an approved test
edge arrives connected to the lab codes that report it.

**Every edge is `corrected_pending_attestation`**: a clinician signs off before any of it is used. **Priors**
(`prevalence_in`) are not built, so these LRs move odds no one has stated yet.

## Illnesses to ICD-10-CM: every code (built, Tier 2)

The first build loaded OMOP's ICD-10-CM → SNOMED maps only for the 1,968 codes MONDO uses, to score MONDO. Now **all
98,290 mapped codes** load — diseases, symptoms (R), injuries (S, T: 55% of the codes), external causes (V–Y), health
factors (Z): **129,167 edges to 15,071 SNOMED concepts**, 11,555 of which had no string to any other vocabulary. A
**combination code** maps to 2–4 concepts that *together* are its meaning (type 1 diabetes with proliferative
retinopathy and retinal detachment → both), so each edge carries `targets_of_code` (26,851 codes have more than one) and
no single target is read as the whole. OMOP's "Maps to value" pairs (*history of* style) mean something else and are
not loaded.

MONDO can witness only the disease chapters, so the tier comes from a hand check on two samples — 40 edges at random
(dominated by injury and external-cause codes, as the maps are) and 40 spread evenly across the chapter letters:
**75/80, Wilson lower bound 0.862 → Tier 2** (`reference/icd10cm_handcheck.json`). OMOP often maps *uphill* —
*Metabolic syndrome* → *Metabolic disease* — which is lossy but not wrong, and was counted correct. The five errors are
OMOP's own and stay as the source asserts them: a pedal cyclist in collision with a *non*-motor vehicle mapped to *Motor
vehicle traffic accident*; non-pressure chronic ulcers (the whole L98.A class) mapped to *Open wound*; *Other renal
tubulo-interstitial diseases* narrowed to nephritis; J05 (croup *and* epiglottitis) mapped to croup alone.

**SNOMED clinical findings with a string to another vocabulary: 9.3% → 17.4%** (22,613 of 129,675); events 0.2% →
14.4%. These are **US** codes: Australia's ICD-10-AM is licensed from IHACPA and is not held, so an Australian coded
diagnosis still needs ICD-10-AM → SNOMED from its own source.

## Pathology units: US conventional against Australian SI

The likelihood-ratio thresholds were published mostly in US units (cholesterol 55 mg/dL, uric acid 5.5 mg/dL), and
LOINC keeps a US mass-unit code and an SI molar code for the same measurement. Australian laboratories report in their
own units — mostly molar for small molecules, but **g/L** for haemoglobin, albumin and protein — so the Australian unit
cannot be inferred; it has to come from the Australian authority.

**The authority: the RCPA SPIA reference sets** (NCTS release RCPA_v20260831, read in place — RCPA copyright, so what is
derived from them stays in the git-ignored `cache/rcpa/`). `scripts/rcpa_units.py` loads the chemical pathology,
haematology, immunopathology, microbiology-serology and blood-gas **reporting** sets: **2,053 rows, 1,803 LOINC codes**,
each with its Australian preferred unit (display and UCUM).

**Three layers, all by code:**

| layer | how | result |
|---|---|---|
| `loinc:au_preferred_unit` (LOINC → UCUM) | the RCPA row's unit, beside LOINC's own example unit (the US convention) | **1,207 edges**: 667 identical, 258 spelling only, **188 differ in scale** and carry the factor (Hb g/dL → g/L ×10, cells /µL → 10⁹/L ×0.001, haematocrit % → L/L ×0.01), 67 assay-specific arbitrary units, **24 differ in kind** (a review list) |
| `loinc:unit_counterpart` (LOINC mass ↔ molar) | same LOINC axes, MCnc against SCnc; the analyte's **molecular weight from PubChem by the component's LOINC-asserted PubChem / ChEBI code** — no name matching (`scripts/unit_reconcile.py`) | **2,045 pairs**, 1,042 with a factor mg/dL → mmol/L; where the RCPA lists either side, Australia reports the **molar side 170 times, the mass side 59**, both 24 |
| threshold units (`reference/threshold_units.json`) | every unit-bearing LR threshold keeps its value **as published** (the source trace) beside the **Australian value** | 35 thresholds: 23 already Australian, 8 relabels (BNP pg/mL = ng/L, procalcitonin ng/mL = µg/L, base deficit mEq/L = mmol/L), 2 molar conversions (**urate 5.5 mg/dL → 0.327 mmol/L**; pleural cholesterol 55 mg/dL → 1.42 mmol/L) |

**The local unit takes primacy only once corrected.** A threshold's Australian value becomes primary when the conversion
is by code (or a pure relabel) **and** an RCPA row for the **same analyte in the same specimen** confirms the unit
(`reference/threshold_rcpa_map.json` names the row; the check is mechanical): **13 thresholds now read Australian first**
(BNP 100 ng/L, NT-proBNP 135 ng/L, procalcitonin 2 µg/L, urate 0.327 mmol/L, CRP, calprotectin, fluid LDH …). 10 keep the
published unit first with the Australian value beside it, because no RCPA row covers that analyte and specimen —
pleural-fluid cholesterol (serum only), PlGF, quantitative FIT (the RCPA lists faecal occult blood as qualitative) and
the synovial white count, where borrowing the *blood* row (10⁹/L) would be wrong: fluid counts are commonly reported in
10⁶/L. Two BNP thresholds are flagged at source: the abstract says "100 ng/mL" where the convention is 100 pg/mL.

**Conversions are checked against the clinical factors.** The first molecular-weight pass got **phosphate wrong by a
factor of three** (0.105 instead of 0.3229): LOINC maps the analyte to the phosphate ion (95 g/mol), but laboratories
report phosphate *as phosphorus* (31 g/mol). Seven reporting conventions — phosphate as P, urea nitrogen as N₂,
triglyceride as triolein, HDL / LDL / VLDL / non-HDL cholesterol as cholesterol — are now explicit, cited to Young DS,
*Ann Intern Med* 1987 (PMID 3789557), with the molecular weight still PubChem's by CID; the choice of reference substance
is authored, so those factors carry `convention` and await sign-off, and the reconciler refuses to run if a convention is
keyed to the wrong LOINC part (two were, on the first try). Against the standard table: **13 of 14 factors match**
(glucose 0.0555, creatinine 0.0884, cholesterol 0.02586, calcium 0.2495, urea nitrogen 0.357, phosphate 0.3229 …);
direct bilirubin has no chemical code and gets no factor rather than a guess.

**What the RCPA data itself needs** (reported, not corrected): **47 unit strings in 6 forms are not valid UCUM** —
`[IU]mL` (no operator) across the coagulation-factor rows, a typographic apostrophe in `[beth’U]`, `KU/L` (K is not a
UCUM prefix), `mmHg` for `mm[Hg]` — and the 24 kind differences include clashes with the LOINC code's own property:
methaemoglobin *fraction* in g/L, mixed-venous base deficit in %, stone weight in g/L, hepatitis C core antigen in pg/mL
on an arbitrary-unit code, "Non HDL cholesterol" in nmol/L.

## Anatomy, organisms, non-laboratory LOINC and MBS

Four blank areas left after the first bridges: SNOMED body structures (0.6% reached another vocabulary) and organisms
(0%), the ~37,000 clinical and survey LOINC terms (147 bridged), and the Medicare Benefits Schedule (absent).

**Anatomy — Uberon (built, Tier 2).** Uberon v2026-06-23 (CC BY 3.0): 14,975 classes, 28,834 is-a / part-of edges, and
**4,119 links to SNOMED CT body structures** from Uberon's own SSSOM file. Uberon curates every SNOMED link as
`skos:narrowMatch` — it is species-neutral, SNOMED is human — so the edge (`uberon:sct_narrow_match`) says the SNOMED
concept is the human form of the class, not that the two are one concept. Hand check **76/80, lower bound 0.878 → Tier 2**
(`reference/uberon_handcheck.json`); the four errors are Uberon's: a metatarsal epiphysis mapped to the *metacarpal* one,
the dorsal horn mapped to SNOMED's "dorsal spinal cord" (which SNOMED files under *thoracic* cord), hemopoietic organ to
*lymphoid* organ, and a branch of the abdominal aorta to the broader "artery of abdomen". MONDO's own
**disease_has_location** (775 → Uberon) and **disease_has_infectious_agent** (691 → NCBI Taxonomy) are now loaded: 766
diseases have a location, 652 an infectious agent.

**Organisms — SNOMED CT ↔ NCBI Taxonomy (built).** No map is published. Two routes, parallel edges on
`sct:ncbitaxon_equivalent`, told apart by method: LOINC's part file asserts **both** codes for 116 organism parts (the
witness); the UMLS crosswalk SNOMEDCT_US → NCBI puts a SNOMED organism and a taxon under one CUI
(`scripts/umls_crosswalk.py`, a generalisation of the HPO crosswalk; key in `.env`, never printed) — admitted, as for HPO,
only where the NCBI name equals the SNOMED preferred term — as written (15,912), or once rank words are set aside
("Salmonella species" = *Salmonella*, "Order Strigiformes" = *Strigiformes*; 4,189). Both classes hand-checked **40/40 →
Tier 2** (`cache/umls/organism_handcheck.json` — UMLS-derived, so kept with the crosswalk and not committed). The crosswalk answered for 23,762 of 34,748 SNOMED CT-AU organisms;
**20,127 organisms now reach NCBI Taxonomy** (from 0). The truly different names (3,958) are candidates in `cache/umls/`,
not edges: a sample of them was right 37 times in 40, but the three errors are exactly the kind a shared CUI hides — the
family Anatidae mapped to the genus *Aythya*, *Magnusiomyces ingens* to a different species, *Cookeolus boops* to a
different fish — while most of the rest are real reclassifications (*Clostridium lavalense* → *Enterocloster lavalensis*)
a person can confirm quickly.

*The witness.* Where LOINC and UMLS both answer (78 organisms) they give the same taxon for 60. The other 18 are not
disagreements about the organism: for 17, NCBI keeps a genus (*Salmonella*, 590) **and** a placeholder for its
unidentified isolates ("*Salmonella* sp.", 599) — LOINC's part "Salmonella sp" points at the placeholder, UMLS at the
genus, which is SNOMED's rank; the last is the mumps virus under an older and a newer NCBI id. Both edges stay, parallel.

**Non-laboratory LOINC — through LOINC's parts (built, and thin).** The one code-to-code route LOINC offers for its
clinical and survey terms: term → its COMPONENT, SYSTEM or METHOD part (`LoincPartLink_Primary`) → the SNOMED concept
LOINC maps that part to (`PartRelatedCodeMapping`), with LOINC's own equivalence (a SYSTEM part "Heart" maps *narrower* to
both "Heart structure" and "Specimen from heart"). TIME, SCALE and PROPERTY parts and the unspecified system "XXX" are not
loaded — they name an axis value, not the thing observed. 164,022 edges (`loinc:part_maps_to_sct`):

| active LOINC terms | terms | bridged before | with the part route |
|---|---:|---:|---:|
| laboratory | 62,148 | 42,325 | 58,867 |
| clinical | 25,152 | 147 | **1,460** |
| claims attachment | 503 | 0 | 17 |
| survey | 11,934 | 0 | **13** |

That is the honest ceiling of code-to-code bridging for non-laboratory LOINC today. *(24 Sep: survey instruments now have
candidate frames — 55 pairs, 37 instruments, `reference/survey_instrument_candidates.json`, `scripts/survey_candidates.py`,
keyed by the instrument's acronym held to SNOMED's own initials; frames, never edges. All queues: `docs/review-queues.md`.)* Radiology (7,045 of the clinical terms)
maps its anatomy parts to **RadLex**, which has no published SNOMED map; survey instruments (PHQ-9, AUDIT …) have no SNOMED
map in LOINC, Athena or the LOINC Extension. Closing either is a gap-crossing, not a lookup. *(24 Sep: radiology is now
bridged by codes after all, through RadLex's own FMA and UMLS cross-references — see* Radiology *below; clinical reach
1,460 → 7,303.)*

**MBS — structure built, SNOMED only as candidates.** The MBS XML (MBS Online, release 20260801): 6,046 items → 99
groups → 9 categories (`mbs:in_group`, `mbs:group_in_category`), each item's schedule fee and benefit on its edge. **No MBS
item carries a SNOMED code and no map exists** — the RCPA requesting set codes pathology requests to SNOMED but has no MBS
numbers. An MBS item is a billing rule (a service plus eligibility conditions), so even an exact name match is not an
equivalence: for the procedural categories (diagnostic, therapeutic, imaging, pathology) `scripts/mbs_candidates.py`
proposes the nearest SNOMED procedures to each descriptor's head phrase from the live Ontoserver
(`reference/mbs_procedure_candidates.json`) — **frames for a person, never edges.** Of 4,710 procedural items, 3,878 have candidates and 572 an exact head-phrase match —
and the sample shows why exact is not enough: dozens of MRI items match only the bare word "MRI" → *Magnetic resonance
imaging*, not the scan the item funds; "amputation of 4 digits of one foot" comes back as *Amputation of left fourth toe*,
an imaging item headed "Hand" as *Hand closure*. The candidates are a work list, and MBS stays reachable only through its
own structure until a person confirms them.

## Radiology: LOINC and the RSNA playbook → RadLex → SNOMED CT (built, Tier 2)

LOINC codes the parts of its ~7,000 radiology terms (modality, region imaged, imaging focus, contrast, view, timing) to
**RadLex** — the LOINC/RSNA Radiology Playbook in LOINC's accessory files — and to nothing in SNOMED CT; RadLex has no
published SNOMED map. What RadLex *does* carry is where its anatomy came from: it was built from the Foundational Model of
Anatomy (Mejino, Rubin & Brinkley, AMIA 2008 — the lead from Overton & Romagnoli's *Radiology, Philosophy, and
Ontology*), and 33,404 of its 46,898 classes state their FMA id; 1,376 state a UMLS CUI. RadLex.owl spreads a class
over three blocks (the class axioms, the OWL pun, and an `rdf:Description` holding the annotations), so
`scripts/radlex_prepare.py` merges them — read naively, only 16 of the playbook's 431 anatomy terms appear to have an
FMA id; merged, 127 do.

Every step is a code someone else asserted, and three routes are kept apart by method on **`radlex:anatomy_sct`**:

| route | edges | RadLex terms | hand check | lower bound | tier |
|---|---:|---:|---:|---:|---:|
| RadLex → FMA → Uberon (crossSpeciesExactMatch) → SNOMED (narrowMatch) | 1,509 | 1,496 | 78/80 | 0.913 | 2 |
| RadLex → FMA → SNOMED (UMLS shared CUI) | 133 | 124 | 75/80 | 0.862 | 2 |
| RadLex's own CUI → SNOMED (UMLS atoms) | 123 | 119 | 78/80 | 0.913 | 2 |

Only active SNOMED CT-AU body structures load (95 targets not in the AU release and 12 non-body-structures are counted,
not loaded). The errors: UMLS joins "hip" (the limb region) to the hip *joint*, "pelvis" to the cavity of the true
pelvis, a gland to its whole salivary apparatus, a node to its node group, "muscle organ" to the skeletal muscle system;
Uberon broadens a segment of cerebral white matter and narrows the ventral lateral thalamic nucleus to one of its parts;
and RadLex itself gives "arm" (defined as the upper arm) the CUI of the whole upper limb and "lateral wall of orbit" the
CUI of the sella turcica. Verdicts: `reference/radlex_handcheck.json` (Uberon route; codes only — RadLex labels are
RSNA's) and `cache/umls/radlex_handcheck.json` (UMLS routes; not committed).

*The witness.* Uberon names SNOMED's "Entire kidney", UMLS its "Structure of kidney" — one structure, two SNOMED forms —
so agreement is counted through SNOMED's own is-a. Where the Uberon and UMLS-FMA routes both answer (104 terms), 98 give
the same concept or an is-a pair; the two UMLS routes agree 53/53. Of the 8 unrelated answers across all route pairs,
4 are UMLS-side mistakes (pelvis → cavity of the true pelvis, knee → bone of the knee region, bone organ → the skeletal
system, large intestine → colon) and 4 are SNOMED near-duplicates its is-a does not join ("Structure of prostate gland" /
"Entire prostate" twice, "Bone structure of sacrum" / "Entire sacrum", popliteal fossa / popliteal region).

**The LOINC side.** `loinc:radlex_part` (48,227 edges: every coded part of every active radiology term),
`loinc:rsna_rpid` (1,008 LOINC ↔ playbook-procedure pairs) and — through `radlex:anatomy_sct` — 17,713 new
`loinc:part_maps_to_sct` edges (method `RadLex anatomy: <route>`, attrs.rid, the route's tier). Of 6,717 radiology terms
with an anatomy part, **5,932 now reach a SNOMED body structure** (3,039 through every anatomy part they have). The
**RSNA Radiology Playbook** itself (`complete-playbook-dev.csv`, 4,772 orderable procedures, 3,762 never exported to
LOINC) loads as `rsna:radlex_part` (23,666 edges, ACTIVE and TRIAL only): 3,324 of its 4,403 live procedures reach
SNOMED through their body region or anatomic focus. RadLex's own is-a (46,898) and part-of (24,764), its FMA
cross-references (33,404) and Uberon's FMA matches (6,051) load as the native steps of the chain.

*What stays open.* 302 playbook anatomy terms carry neither an FMA id nor a CUI — among them the commonest regions,
**head, neck, shoulder, ankle, hand, foot, lumbar spine, whole body** — so no code route exists. For 99 of them a SNOMED
body structure has the same name ("internal jugular vein" → *Structure of internal jugular vein*); those are candidates
in `cache/radlex/radlex_sct_candidates.tsv` for a person, never edges — a name match is a gap-crossing. Modality,
contrast, view and timing parts stay RadLex-only: SNOMED models them as qualifier values, and no map joins them.

## Cross-references the sources already assert (24 Sep 2026)

Asked whether the cross-vocabulary links were maximised, the answer was no: several sources carried mappings the graph had
not loaded. Every one below is a code a publisher asserts — no matching.

| from | to | edges | predicate |
|---|---|---:|---|
| SNOMED CT-AU release (Refset/Map) | ICD-O-3 topography / morphology | 23,514 | `sct:icdo_map` |
| AMT product (Refset/Map) | ARTG entry — the TGA registration | 51,981 (50,056 products) | `sct:artg_id` |
| SNOMED "Structure of X" (Refset/Content) | "Entire X" / "Part of X" | 16,171 | `sct:anatomy_structure_entire` / `_part` |
| retired SNOMED id in the graph (Refset/Content, Map) | its active successor | 1,288 | `sct:historical_association` |
| MONDO (SSSOM exactMatch) | DOID, NCIT, MeSH, ICD-11, EFO, UMLS, MedGen, WHO ICD-10, OMIM PS | +78,635 (109,623 in all) | `mondo:exact_match` |
| DrugCentral (identifier table) | ChEMBL, UNII, PubChem, ChEBI, MeSH, UMLS, INN, KEGG, IUPHAR | 42,163 | `drugcentral:xref` |
| LOINC term's analyte part | ChEBI, RxNorm, PubChem, UNII, NCBI Taxonomy, NCBI Gene, HGNC, ClinVar | 53,683 | `loinc:part_xref` |
| Uberon (SSSOM narrowMatch) | NCI Thesaurus anatomy | 2,578 | `uberon:ncit_narrow_match` |
| HPO (hp.obo xref) | NCIT, Orphanet, WHO ICD-10 | 265 | `hp:xref` |

**Medicines meet the tests that measure them.** LOINC codes the analyte of a drug-level test to RxNorm — the vocabulary
the compendium's ingredients already use — so **964 Australian medicine ingredients now reach a LOINC test** (9,158
tests; 752 ingredients and 4,429 tests in class DRUG/TOX, i.e. drug levels). The witness is independent: LOINC's ChEBI /
UNII / PubChem code for the same analyte, carried to RxNorm by DrugCentral's identifiers, names **the same drug for 5,824
of 5,913 tests** (98.5%). A "vancomycin" component is also the drug in a *susceptibility* test (class ABXBACT: the
organism against the drug), so a query for levels filters by class.

**Retired SNOMED ids now lead somewhere.** Of 1,794 SNOMED ids that other sources use and the AU release does not
define as active, 1,034 now have the release's own successor (REPLACED BY 243, SAME AS 293, POSSIBLY EQUIVALENT TO 326,
MOVED TO 135, …) — the August "Clexane with Automatic Safety Lock System" packs → their "Eris Safety Lock System"
replacements — and with Athena's nearest ancestor **1,741 of 1,794** are reachable (775 before). POSSIBLY EQUIVALENT TO and
ALTERNATIVE are weaker than REPLACED BY and SAME AS; the edge's method says which.

**Not loaded, and why:** MedDRA (MSSO licence), DrugBank ids (excluded throughout), the US formulary ids in DrugCentral
(MMSL, NDDF, VANDF, VUID, NUI), LOINC's *Search* part links (they help people find terms, they do not say what a term
measures), the CTV3 map (UK Read codes), and the SNOMED refsets of AU clinical subsets (loaded next — see *Reference sets*).

**Islands.** `graph_report.py` now reports connected components on every run: 1,317,597 of 1,335,431 nodes (98.7%) are
one component. MBS (6,046 items, no published map) is the one true island; the rest are pairs and small clusters —
MONDO's obsoleted terms with their old xrefs, and ~930 DrugCentral drugs no Australian source uses, now carrying their
own identifiers.

## Reference sets: the AU release's curated subsets (built)

`sct:in_refset` — **1,252,680 memberships of 138 simple reference sets** in SNOMED CT-AU 20260831 (1,589 members that are
not active concepts are counted, not loaded). A reference set is a SNOMED concept, so a membership is an edge from the
member to it; `method` is the set's name. Membership is the owner's curation for a purpose — "in the emergency department
principal diagnosis set" says the concept may be coded as an ED principal diagnosis, not anything about the disease.

| family | examples |
|---|---|
| clinical subsets | Problem/Diagnosis (133,027), Australian ED (99,699) and ED principal diagnosis for funding (93,171), RACS MALT surgical procedures (16,041), Queensland allied health |
| foundation, by hierarchy | clinical finding, procedure, body structure, organism, substance, qualifier … |
| AMT structure | TP, TPUU, TPP, CTPP, MP, MPUU, MPP |
| medicines regulation | each state and territory's reportable / monitored Schedule 4 list, Schedule 8, Black Triangle Scheme, List of Medicines for Brand Consideration, List of Excluded Medicinal Items |
| requesting | RCPA SPIA requesting pathology, RCPA microbiology organisms, RANZCR radiology requesting, request / result test names |
| answer lists | smoking, vaping, alcohol, housing, food security, pregnancy assertion … |

**Regulation meets the PBS.** At the product level the PBS lists: 482 PBS-listed products are **Schedule 8**, 21 are under
the **Black Triangle Scheme** (all recently approved biologics — Rybrevant, Libtayo, Padcev, Imjudo, Vyxeos …), 942 are on
the **List of Medicines for Brand Consideration**, and 274–386 are on each state's monitored Schedule 4 list.

**What the sets show about the graph** (`graph_report.py`, share of each set's members with a link outside SNOMED): the
AMT pack sets 77–97% and the state Schedule 4 lists ~92% (the drug side is well bridged); ED diagnosis sets 57%; the
national ED sets 22%, Problem/Diagnosis 17%; foundation procedures 6%; **RACS MALT surgical procedures 0.3%** and imaging
procedures 0.8% — procedures are the least-bridged part of SNOMED, the same gap MBS sits in, and the MALT set (the
surgical audit list) is the natural target for the MBS candidate frames.

## Genes, rare diseases and pathways: HGNC, Orphanet, Reactome (built)

Three free downloads (24 Sep 2026, cache/, 115 MB), each a source's own assertions.

**HGNC** (complete set, CC0) — the authority for human gene symbols: `hgnc:xref` from each approved gene to its NCBI Gene id,
UniProt proteins and OMIM **gene** entry (37,746 edges). Only genes that share an id with something else in the graph load
(a disease gene, a drug target, a genotype test, a Reactome participant); the other 32,173 — mostly non-coding RNAs and
pseudogenes — would each be a detached cluster of their own ids, and are counted in `build_log`, not loaded. *Witness:* on the
gene ↔ protein pairs DrugCentral's target components gave (`uniprot:encoded_by`), HGNC agrees for **1,854 of 1,890**; the 2
that differ are duplicated genes (P0DMV8 is made by both HSPA1A and HSPA1B; DrugCentral puts P36544 on the CHRFAM7A fusion
gene where HGNC says CHRNA7), 34 are silent.

**Orphanet** (Orphadata product 1, 2026-06-23, CC BY 4.0) — Orphanet's *own* alignments, not MONDO's: `orpha:xref` from 11,645
rare disorders to ICD-10, ICD-11 (MMS codes, a vocabulary separate from MONDO's ICD-11 foundation ids), OMIM, UMLS, MeSH,
MONDO and GARD (49,601 edges; MedDRA left out). The relation is Orphanet's and it matters: to ICD-10 the ORPHAcode is
mostly **narrower** than the code (NTBT 7,034, exact 605) — ICD-10 has no room for most rare diseases — and to OMIM often
**broader** (BTNT 4,138, exact 3,781). Only E is an equivalence. *Witness:* of Orphanet's 8,918 ORPHA → MONDO links, MONDO
asserts the same pair back for **8,789** (98.6%). Orphanet writes MONDO ids without MONDO's leading zeros; they are padded.

**Reactome** (v97, CC0) — `reactome:participates_in` from 12,155 human proteins to their lowest-level pathways (54,699,
curated TAS or inferred IEA) and `reactome:part_of` for the pathway hierarchy (2,899; 2,344 pathways). The chain drug →
target → protein → **pathway** now closes: **2,549 DrugCentral drugs and 1,807 Australian medicine ingredients reach a
pathway through a target**, and **9,135 diseases reach one through a gene** (HPO genes_to_disease → NCBI Gene → HGNC →
UniProt → Reactome).

**Orphanet's gene and phenotype files (built, 24 Sep).** Orphadata product 6 (`cache/orphanet/en_product6.xml`, 22.6 MB)
and product 4 (`en_product4.xml`, 47.9 MB), release 2026-06-23, CC BY 4.0. HPO relays both — 99.4% of the gene pairs and
99.7% of the phenotype pairs are already in `hpo:gene_disease` / `hpo:has_phenotype` — but drops Orphanet's detail, which
is what these add. `orpha:gene_disease` (8,133, HGNC → Orphanet) carries **how** the gene is involved as its method:
disease-causing germline mutation 5,408, loss of function 1,222, gain of function 214, susceptibility factor 393, fusion
gene 261, somatic 243, role in the phenotype 277, modifier 56, biomarker 47, candidate gene tested 12 (HPO relays all as
UNKNOWN); the 367 Orphanet has not yet assessed are counted, not loaded. `orpha:has_phenotype` (115,908) carries the
frequency band as its method and marks **1,096 diagnostic criteria and 19 pathognomonic signs**; `orpha:lacks_phenotype`
(733, "Excluded (0%)") is a stated absence — HPO's NOT annotations carry 726 of them.

## ICD-10 ↔ ICD-11: WHO's mapping tables (built)

WHO's tables from the ICD-11 2026-01 release (`cache/who-icd11/`, 6.8 MB, CC BY-ND 3.0 IGO; codes only, no titles):
`who:icd10_to_icd11` (ICD-10 → ICD-11 MMS: WHO's single best category, and the other categories an ICD-10 code's content
moved to), `who:icd11_to_icd10` (the backward table, from MMS codes and from foundation entities — not the inverse: many
ICD-11 codes fold into one ICD-10 code), and `who:icd11_mms_foundation`, which **joins the graph's two ICD-11
identifiers** — the foundation ids MONDO cites and the MMS codes Orphanet cites. As with HGNC, only rows touching a code
another source already names load (30,222); the rest of the two classifications would be detached clusters.
4,155 of 4,545 ICD-10 codes in the graph reach ICD-11, and 4,558 MONDO diseases reach ICD-10 through their ICD-11 entity.

*Two witnesses, both readable only through Orphanet's relation.* Where Orphanet calls its ICD-11 link **exact**, MONDO's
foundation id is the entity that MMS code linearises for **1,216 of 1,252** diseases (97.1%); where Orphanet's ICD-11 code
is *broader* than the disease (NTBT), it agrees 20 of 1,617 times — as it should, since the code then stands for a larger
entity. Where both Orphanet ICD links are exact, WHO's backward table gives Orphanet's ICD-10 code for **346 of 388**
(89%) and the same 3-character category for 365 (94%); the NTBT/NTBT majority agrees on the category 60% of the time. The
disagreement lives where Orphanet itself says the codes are approximations.

## SNOMED CT → ICD-10 and ICD-10-CM: the publishers' own maps (built, native)

The **SNOMED CT to ICD-10 map** (extended map reference set 447562003, SNOMED International) is released with the
International Edition, which the AU release is built on but does not carry, and which otherwise comes only through MLDS.
NLM's **SNOMED CT US Edition 20260901** ships it unchanged (SNOMED International's mapping module 449080006, the July 2026
map) beside NLM's own **SNOMED CT to ICD-10-CM map** (6011000124106), and NLM gives the US Edition to UMLS licence
holders at once (661 MB, fetched with the UTS key; `scripts/snomed_us_maps.py` keeps the two refsets' active rows in
`cache/snomed-us/`). Both are loaded as their publishers' assertions — **native**, like the ICD-O map — as
`sct:icd10_map` (**129,729 edges**, 112,426 concepts → 10,692 ICD-10 codes) and `sct:icd10cm_map` (**200,311** full codes, 106,256 concepts → 16,947 ICD-10-CM codes, plus 56,263 partial — below).

**Complex maps, kept whole.** A concept can need several codes together (`attrs.group`); within a group the first rule
that holds wins (`attrs.priority`). `method` names the rule kind so a traversal that cannot evaluate a condition can leave
it out: *unconditional* (rule TRUE; ICD-10 129,583, ICD-10-CM 91,812), *conditional* (IFA the patient's sex, age or
another concept; 132 and 84,180 — ICD-10-CM's specificity is mostly context-dependent) and *default, when no condition
holds* (14 and 24,319). The rule text, advice and map category ride in `attrs`. Not edges: rows with no target
("cannot be classified with available data": 25,050 and 28,085) and US-extension concepts not in SNOMED CT-AU (46 and
10,264). ICD-10-CM targets ending `?` load against their subcategory (below).

**What it closes.** WHO ICD-10 was reached by **none** of the AU diagnosis reference sets before; now **84.3%** of the
Problem/Diagnosis set (133,027 members), **95.7%** of the ED principal-diagnosis set and **93.6%** of the ED diagnosis set
reach ICD-10, and — with the fifth-character step below — the same shares go on to ICD-11 through WHO's tables. WHO's
tables themselves now load 59,591 rows (30,222 before), since a row loads when it touches a code the graph holds and the map brought 7,118 more ICD-10 codes (4,545 → 11,663).

*Witnesses, both structural.* ICD-10-CM extends ICD-10, so a concept's two maps should share the three-character
category: they do for **55,634 of 69,420** concepts (80.1%) — the rest are where ICD-10-CM re-sorted a chapter (diabetes
E08–E13, injuries, the clinical-modification additions). OMOP's ICD-10-CM → SNOMED map, a separate source in the reverse
direction, maps each code up to one concept: NLM's concept is that concept or below it for **45,962 of 88,849** pairs;
the rest are mostly residual codes ("Other specified …"), which OMOP maps to a same-named concept beside the specific
diagnoses rather than above them — a difference of method, not an error. A read of 30 random rows from each map found
every one as published (one questionable choice is NLM's: *Patient denies drug use* → F19.90).

**Partial ICD-10-CM targets and ICD-10's fifth characters (built).** A target ending `?` names a code whose last
character — for injuries, the episode of care — the coder still has to choose; the concept certainly falls in the
subcategory the published characters spell, so it loads against that code (placeholder X's dropped: `O32.4XX?` → O32.4,
`S08.129?` → S08.129) with method *⟨rule kind⟩, partial code (subcategory)* and `attrs.target_as_published`: **56,263
edges**, every subcategory an ICD-10-CM code. WHO's ICD-11 tables list no fifth-character codes (M41.15, S36.00, T08.X0 —
WHO's optional site, open/closed and similar subdivisions), so `icd10:subdivision_of` joins each of the **1,855** the
map uses to its parent, kept only when the parent is in WHO's tables; 6 mapped codes have none there (K58.0, K58.9,
U06.9 …). With that step, ICD-11 reach equals ICD-10 reach: **84.3%** of Problem/Diagnosis, **95.6%** and **93.6%** of
the two ED diagnosis sets.

### Orphanet → ICD-10 through SNOMED CT's map: the first chain rule (built, ungraded)

`orpha:icd10_via_snomed` (derivation `chain`): an **active** Orphanet disorder- or subtype-level entry with no ICD-10 code
of its own, exactly aligned by Orphanet to a UMLS concept or MONDO disease that holds a SNOMED CT concept, gets the ICD-10
code SNOMED International's map classifies that concept to — only through maps with a single unconditional group. Three
rules came from the checks: Orphanet *groups* are left out (27 of the first 30 new chains were groups, and each of the 6
errors was one — a group handed one member's code), two-group maps are left out (*Maternally inherited diabetes and
deafness* needs both codes), and entries Orphanet has retired are left out — **most entries without an ICD-10 code of
their own are retired ones** (Orphanet strips a deprecated entry of its codes), which is what the first version (PR #39,
63 disorders) was mostly filling. What remains is 6 edges, 5 pairs, all right in the census — too few to earn a tier, so
ungraded. The rule stands for later releases; the witness is unchanged (where Orphanet has its own exact code, the chain
gives it for 424 of 474, its category for 459). Orphanet's `orpha:xref` rows for retired entries carry `attrs.entry`.

**MED-RT: two more witnesses (24 Sep).** *may treat* corroborated by DrugCentral's label indication (same drug, same
SNOMED concept, a MeSH disease through its same-name SNOMED concept): 3,176 edges, 34/34, Tier 2. *Mechanism of action*
corroborated by DrugCentral's MeSH pharmacological action (same drug, same class once wording is set aside — "Adrenergic
alpha2-Antagonists" = "Adrenergic alpha-2 Receptor Antagonists"): 249 edges, 33/34 (the error, *isosorbide* → nitric
oxide donor, is shared by both sources and rejected by name), Tier 2. The uncorroborated families stay inadmissible
(23/30 each; their samples were topped back up to 30 after the split).

## UMLS Metathesaurus: every shared concept, locally (built)

The licence holder's UMLS 2026AA concepts file (MRCONSO, 18.1 M names for 3.5 M concepts from 195 sources; 513 MB,
downloaded with the UTS key, kept as `cache/umls/2026AA/mrconso.parquet`) replaces per-code API calls: every pair of graph
codes that share a CUI, in seconds (`scripts/umls_mrconso.py`). Loaded as `umls:shared_cui`, **179,878 edges**, last of the
loaders so a pair loads only if one code is already a node.

**Rules.** Sources at UMLS restriction level 0 and SNOMED CT (level 9, under the affiliate licence Australia's
membership covers); levels 1–4 — ICD-10-CM (4), WHO ICD-10 and ICD-10-AM (3), MedDRA, CPT, MEDCIN, ICPC-2 PLUS (3),
ORPHANET (1) — need their own agreements and are not used. Suppressible atoms are out. A pair loads when the two codes
**share a name** in the CUI (case, punctuation, word order and SNOMED's semantic tag set aside); the 66,660 whose names
differ are candidates. **MeSH pairs only through its own headings** (MH, NM): UMLS files many MeSH entry terms as concepts
of their own, and the first hand check caught a broad descriptor paired with a narrow concept through them
(Leukoencephalopathies → Vanishing white matter disease, Nodaviridae → Alphanodavirus, Malus → *Malus domestica*,
terodiline → terodiline hydrochloride): 25/30 before the rule, 30/30 after.

| vocabulary pairs | edges | check | tier |
|---|---:|---|---:|
| 32 pairs — among them NCIT–SNOMED (25,807), MeSH–SNOMED (25,396), LOINC–SNOMED (12,120), MeSH–NCBI Taxonomy, FMA–SNOMED, RxNorm–SNOMED, NCIT–OMIM, LOINC–NCIT, MeSH–OMIM, HGNC–NCIT, the four ATC pairs, HP–NCIT, HP–MeSH and six small pairs as one pool | 162,000+ | 30/30 each, or 29/30, 56/60 where the first 30 sat on the boundary | 2 |
| HGNC–OMIM | 12,004 | 11,920 of 11,933 agree with HGNC's own cross-reference | 1 |
| HP–OMIM | 465 | 20/34 | inadmissible |
| LOINC–OMIM | 125 | **census, all 125: 114 right** (the 11 wrong rejected by name) | 2 |
| six pairs under 40 edges each | 63 | not sampled | ungraded |

**OMIM gene entries pair only with genes.** An OMIM *gene* entry carries its diseases' names as synonyms, so a shared name
paired a disease with a gene — Bardet-Biedl syndrome 1 → the BBS1 entry, beta-thalassaemia → HBB, Leydig cell agenesis →
LHCGR (OMIM–SNOMED 23/30 before the rule, 30/30 after). HGNC names the gene entries; they now pair only with an HGNC gene
or an NCIt "… Gene" concept. What still fails is HPO and LOINC *features* paired with a specific OMIM disease (restless
legs → RLS susceptibility 1, mandibulofacial dysostosis → Treacher Collins 1): HP–OMIM stays inadmissible. LOINC–OMIM
sat at 29/31 (lower bound 0.793) — close, but re-drawing until a sample passes is optional stopping; at 125 edges the honest
answer was a census: 114/125, lower bound 0.849, Tier 2, and the 11 it names (a condition paired with a *susceptibility* or
*quantitative trait* entry: cerebrovascular accident → ischaemic stroke susceptibility, hyponatraemia → sodium serum level
QTL 1) are rejected. **Every edge a hand check finds wrong is rejected by name** — kept, never followed — 35 UMLS and 27
MED-RT edges so far.

HPO → SNOMED and SNOMED organism → NCBI Taxonomy keep their own UMLS loaders and are not repeated. SNOMED concepts with a
link outside SNOMED: **41.9% → 45.5%**; 33,785 MeSH descriptors now sit in the graph, the index PubMed uses. UMLS-derived:
the pairs, the hand check (`cache/umls/umls_shared_cui_handcheck.json`) and the parquet stay git-ignored, and a graph built
with them is for UMLS licensees.

**Two gaps the completeness measure found (docs/completeness.md), closed 24 Sep.** *HPO → SNOMED*: the loader had left
that pair to the older per-code crosswalk (`hp:umls_snomed`, 2,754); it now loads the concepts file's **4,885** same-name
pairs as `umls:shared_cui` HP-SCT (hand check 29/30, Tier 2; the one error, *Cystic medial necrosis* → *Cystic
adventitial disease*, is a UMLS merge of two arterial diseases, rejected by name). *UMLS concept → SNOMED*: the graph's
29,234 CUI nodes — named by Orphanet's, MONDO's and DrugCentral's own cross-references — were joined to nothing;
`umls:concept_member` joins each to the SNOMED CT-AU disorders and findings inside it (**12,489 edges**, hand check
30/30, Tier 2), so 6,783 Orphanet disorders reach SNOMED that had no other route. Drugs are left out: UMLS files a
substance and SNOMED's *Product containing* it under one CUI. A SNOMED code now joins through UMLS only as an active
SNOMED CT-AU concept (227 pairs dropped that would have added US-only or retired codes).

### UMLS relationships (MRREL, Level 0 subset 2026AA)

The Level 0 subset (2.0 GB; exactly the unrestricted sources — SNOMED's own relationships already come from the AU release)
gives 23.9 M relationships (`scripts/umls_mrrel.py`). UMLS writes each as *the second atom to the first*: a row
(disease, may_treat, drug) says the drug may treat the disease; a PAR row names the parent second. Two kinds, loaded
apart because they rest on different evidence:

**Sources' own hierarchies — native** (`umls:source_parent`, 273,627 edges): the LOINC part hierarchy (158,159), NCI
Thesaurus is-a (50,927), FMA is-a (42,243) and the MeSH tree (22,298; headings only). The only UMLS step is atom → the
source's own code, so each is that source's assertion. They are **climbed upward** from nodes the graph already holds —
parents, then theirs — and never pulled downward, so a broad concept does not bring thousands of children nothing
names; nodes outside the main component fell 18,507 → 13,313.

**MED-RT** (the VA's medication reference terminology, public domain), projected onto the graph's RxNorm ingredients and
SNOMED CT / MeSH diseases through a shared CUI on each side, both ends already nodes:

| predicate | edges | hand check | tier |
|---|---:|---|---:|
| `medrt:contraindicated_with` | 21,441 | 56/60 (lower bound 0.841) | 2 |
| `medrt:may_diagnose` | 265 | 30/30 | 2 |
| `medrt:has_mechanism_of_action`, **corroborated by FDA SPL** | 1,352 | 30/30 | 2 |
| `medrt:has_physiologic_effect`, **corroborated by FDA SPL** | 279 | 30/30 | 2 |
| `medrt:has_mechanism_of_action`, MED-RT alone | 4,648 | 23/30 | inadmissible |
| `medrt:has_physiologic_effect`, MED-RT alone | 7,508 | 26/30 | inadmissible |
| `medrt:may_treat` | 26,143 | 24/30 | inadmissible |
| `medrt:may_prevent` | 4,091 | 24/30 | inadmissible |

**The FDA route — the terminology shim.** The FDA indexes every approved label to pharmacologic classes (Structured
Product Labeling: Established Pharmacologic Class, mechanism of action, physiologic effect), and its classes *are* MED-RT
concepts. DrugCentral carries that indexing (`pharma_class`, now extracted by `drugcentral_extract.py`), so
`fda:pharmacologic_class` (3,459 edges, native) reaches the same class nodes from label evidence: 1,558 drugs to 542
Established Pharmacologic Classes ("Proton Pump Inhibitor"), 996 to a mechanism, 247 to an effect. Where the FDA and
MED-RT assert the same class for a drug the MED-RT edge is marked *corroborated*, and the two halves are tiered apart:
**every MED-RT error found sits in the uncorroborated half** (dexmedetomidine carries both alpha-1 and alpha-2 in
MED-RT, the FDA only alpha-2; megestrol both progestin and oestrogen antagonist, the FDA only progestin). MED-RT classes
outside the main component fell 1,173 → 718.

MED-RT is generous where labels are strict: its "may treat" includes cannabidiol → pain and chloroquine → systemic
scleroderma, "may prevent" warfarin → atrial fibrillation (it prevents the stroke), its effects clomipramine as
*decreasing serotonin degradation* (that is MAO inhibition), its mechanisms dexmedetomidine as an *alpha-1* agonist — so
those edges stay, held inadmissible, never displayed (and never followed: MED-RT's 1,173 effect and mechanism classes now
sit outside the main component, which is the tiering working). Its contraindications are sound; the four errors in 60 are MED-RT's coarse
concepts ("Acute Disease" for acute bronchospasm). *The witness is a lower bound, not a disagreement:* for the 1,706 drugs
both carry, 42% of MED-RT's SNOMED indications match DrugCentral's exactly or through is-a, and 32% of its
contraindications — DrugCentral follows current labels, and its silence is *unknown*, not "no". Verdicts:
`cache/umls/umls_medrt_handcheck.json` (UMLS-derived, git-ignored).

### MedCAT on PBS indication texts (tried, not adopted)

The UMLS self-trained MedCAT pack (2023; `cache/medcat/`, licensed) was tried as a candidate generator for the 341
unbound PBS indication texts. Its concept database (3.9 GB) cannot be loaded on this 8 GB Mac, so
`scripts/medcat_subset.py` streams it and keeps only the names the texts can reach, their concepts and context vectors —
faithful on those texts (checked against the original) — and `scripts/medcat_pbs.py` runs MedCAT 2, carries each 2023
CUI to 2026AA (MRCUI merges only) and to active SNOMED CT-AU codes. **On the 312 texts already bound by exact name it
recovers 142 (lower bound ~0.40).** The pack has trained context vectors for 62,796 of 4.55 M concepts (1.4%) —
osteoporosis, schizophrenia and migraine have none, so their names are never linked — and a two-word indication gives it
no context to weigh. 16 of the 341 got a whole-text proposal (7 not among the Ontoserver candidates). No edges;
candidates stay in `cache/medcat/pbs_medcat_candidates.json`. The tool fits running clinical notes, which the graph has not.

### AHRQ CCSR: ICD-10-CM into clinical categories (built)

AHRQ's Clinical Classifications Software Refined for ICD-10-CM (2026, public domain), relayed verbatim in UMLS's MRMAP:
`ccsr:category`, **235,027 edges** — 74,415 of the graph's 98,366 ICD-10-CM codes into 553 categories in 23 body systems
(`CIR017` Cardiac dysrhythmias; the prefix is the body system). method is AHRQ's: *classified_as* (a code can fall in
several — 8,780 do) and the *default inpatient* / *default outpatient* category for a principal diagnosis. Native: AHRQ's
assertion, not a UMLS judgement. (MRMAP's FROMID/TOID are its own row ids; the codes are FROMEXPR/TOEXPR.)

## How a drug works: drug → target → protein → gene → disease

Until now the graph knew *what* a medicine treats (PBS, DrugCentral's labels) but not *how*. DrugCentral's activity
tables (already in the dump on disk) and HPO's gene file add the mechanism layer — the one PrimeKG, the template this
graph reused, is built around. All four hops are lookups from their sources; every edge keeps its DrugCentral `act_id`
or HPO row, and through it ChEMBL, the drug label, the paper (PMID / DOI) or NCBI.

| hop | predicate | edges | |
|---|---|---:|---|
| drug → target, **the mechanism** | `drugcentral:mechanism_target` | 2,866 | 1,933 drugs, 733 targets (606 human); the verb rides on the edge — *inhibitor*, *agonist*, *antagonist*, *blocker* … |
| drug → target, measured activity | `drugcentral:bioactivity` | 18,112 | a Ki or IC50 — binding, **not** a claim about why the drug is used; kept as a separate predicate for that reason |
| target → protein | `drugcentral:target_component` | 4,167 | a complex (a GABA-A receptor) has several; a drug on the complex is not asserted to act on each subunit |
| protein → gene | `uniprot:encoded_by` | 1,890 | target proteins only |
| gene → disease | `hpo:gene_disease` | 16,099 | OMIM (Mendelian / polygenic, via NCBI mim2gene) and Orphanet; HPO release v2026-09-01 |

Targets include bacterial, viral and fungal proteins (`attrs.organism`): that is where an antibiotic acts.

**Two witnesses.** These are native assertions, so they carry no earned tier; they were checked instead.
*ChEMBL, for mechanisms DrugCentral did not take from ChEMBL* (the label, papers, IUPHAR, KEGG — 1,187 rows;
`scripts/chembl_moa_witness.py`, ChEMBL's public API): ChEMBL records the same protein for **838**, differs for 197,
is silent for 152 — 81% where it speaks; the verdict rides on each edge as `attrs.chembl_witness`. Read by hand (40
rows), the differences are of two kinds: the same target recorded for another strain or as a coarser group (*Candida
inhibitor* for rezafungin's glucan synthase), and a **secondary target labelled as mechanism** — lorlatinib → NTRK3,
an in-vitro activity from the label, where its mechanism is ALK / ROS1; epoprostenol → EP1, where it is the IP
receptor. Treat `differs` as "check before relying on it". The 1,679 rows DrugCentral took from ChEMBL cannot be
checked against ChEMBL. *HPO, for the gene ids*: of 936 NCBI gene ids both sources use, **921 carry the same symbol**;
13 of the 15 others are HGNC renames since DrugCentral's 2023 release (GBA → GBA1, SEPT9 → SEPTIN9) and 2 are
DrugCentral naming the paralogue (HBA1 on HBA2's id).

**Reach.** Of 1,933 drugs with a mechanism, 1,686 reach a gene, **1,266 reach a genetic disease** through it and
1,001 reach SNOMED CT-AU through MONDO; **40,387 of the 59,649 SNOMED CT-AU products** with an active ingredient
(68%) now reach a mechanism. *Imatinib* inhibits ABL1, KIT and PDGFRB, whose genes lead to chronic myeloid
leukaemia, mastocytosis and hypereosinophilic syndrome — its indications, reached from its mechanism alone.

**What the chain does not say.** Drug → target gene → disease is *mechanistic proximity*, not an indication: the
disease is one a mutation in that gene causes. It is where a drug's effects and side effects can be reasoned about,
and where repurposing is looked for; the indication edges are still `drugcentral:indication` and the PBS chain.

## The loader ledger (built 24 Sep 2026)

Every loader in `scripts/build_edges.py` states what its source offered and where each row it did not load went, so a
member the graph lacks can be traced to *never in the source* or *in it, and excluded for this reason*. The build writes
`out/loader_ledger.json` and a `loader_ledger` table in the graph; the release guard fails if a loader appears with no
ledger, and warns if a loader's excluded share rises by more than 5 points.

- **source** (77 loaders): rows available → each filter in turn, with its reason and the rows it took out → loaded. The
  filters are counted in one pass over the source (`count(*) FILTER`), before the insert, so a filter that asks "is this
  code in the graph yet" never counts the loader's own edges. What remains between the rows kept and the edges loaded is
  named, not absorbed: *collapsed into fewer edges* (duplicate rows, several rows naming one edge) or *fanned out* (one
  row, several edges: a LOINC part mapped to two SNOMED concepts, an HGNC entry's several ids).
- **derived** (7): rules over edges already loaded (lab result → finding, the RadLex anatomy routes, the Orphanet chain,
  foreign SNOMED ids resolved) — each names its rule.
- **undeclared**: none.

Every source ledger balances (available − excluded + fanned out = loaded). What it shows first:

| loader | available | loaded | the largest exclusions |
|---|---:|---:|---|
| SNOMED CT → ICD-10-CM (NLM map) | 294,007 | 200,311 | 58,689 partial codes (loaded apart as subcategories: 56,263), 28,085 no target, 6,922 US-only concepts |
| HPO → SNOMED (UTS crosswalk, same name) | 14,854 | 2,756 | **7,566 SNOMED codes not active in SNOMED CT-AU**, 4,532 names differ (the review queue) |
| UMLS shared CUI, same name | 376,257 | 180,371 | 98,640 neither code a graph node, 65,379 names differ, 24,027 organism pairs (own loader), 7,330 OMIM gene entries paired with a disease |
| UMLS concept → SNOMED disorder / finding | 1,728,196 | 12,489 | 975,038 CUI not a graph node, 691,296 suppressed atoms |
| LOINC term → analyte code | 220,072 | 53,683 | 183,635 part with no analyte code, 4,036 inactive terms (21,282 fanned out) |
| Reactome protein → pathway | 324,818 | 54,699 | 270,119 not human |
| HGNC gene → NCBI Gene / UniProt / OMIM | 45,083 | 37,736 | 32,178 no id shared with the graph (24,831 fanned out) |
| Decisions by a person | 516 | 328 | 107 none, 81 rejected |

The HPO crosswalk's inactive half is the one new finding: the older per-code UTS crosswalk carries many US-only or
retired SNOMED codes. The 2026AA concepts file (`umls:shared_cui`) reaches most of those phenotypes through current codes,
so it is not a coverage loss, but it is why that loader's yield is 19%.

## Rebuild

```bash
# sources (cache/, git-ignored): mondo.obo 53.1 MB, mondo.sssom.tsv 13.1 MB, phenotype.hpoa 35.8 MB, hp.obo 10.9 MB,
# genes_to_disease.txt 1.5 MB (HPO release v2026-09-01),
# drugcentral.dump.11012023.sql.gz 1.40 GB -- URLs in scripts/build_edges.py and scripts/drugcentral_extract.py
.venv/bin/python scripts/drugcentral_extract.py   # ~10 s: streams the dump, keeps 9 tables, no Postgres needed
.venv/bin/python scripts/chembl_moa_witness.py    # ~3 min, once per DrugCentral release: ChEMBL's verdict on each mechanism
.venv/bin/python scripts/rcpa_units.py            # RCPA SPIA preferred units, read in place (RCPA_DIR); derived data to cache/rcpa/
.venv/bin/python scripts/unit_reconcile.py        # ~10-25 min first run (PubChem, cached): LOINC mass <-> molar pairs and factors
.venv/bin/python scripts/threshold_units.py       # LR thresholds: as published + Australian value, primacy once RCPA confirms
.venv/bin/python scripts/umls_crosswalk.py --source SNOMEDCT_US --target NCBI --ids cache/umls/sct_organisms.txt --out sct_ncbi   # ~1.7 h, resumable
.venv/bin/python scripts/mbs_candidates.py       # ~25 min (Ontoserver): MBS -> SNOMED procedure candidate frames
.venv/bin/python scripts/umls_mrconso.py         # UMLS 2026AA MRCONSO (key in .env; --download first time, 513 MB) -> shared-CUI pairs, ~20 s
.venv/bin/python scripts/umls_mrrel.py           # UMLS 2026AA Level 0 subset (--download first time, 2.0 GB) -> hierarchies + MED-RT edges, ~1 min
.venv/bin/python scripts/snomed_us_maps.py       # SNOMED CT US Edition 20260901 (cache/snomed-us/, 661 MB via UTS) -> the ICD-10 and ICD-10-CM maps, seconds
.venv/bin/python scripts/radlex_prepare.py       # ~20 s: RadLex.owl (RADLEX_OWL) -> cache/radlex/, and the ids UMLS needs
.venv/bin/python scripts/umls_crosswalk.py --source FMA --target SNOMEDCT_US --ids cache/radlex/anatomy_fma.txt --out fma_sct            # ~30 s
.venv/bin/python scripts/umls_crosswalk.py --source CUI --target SNOMEDCT_US --ids cache/radlex/anatomy_cui.txt --out radlex_cui_sct     # ~30 s
#   read in place: ~/Documents/ONTOLOGIES/PunRadLex_Owl4.3/RadLex.owl (RadLex 4.3) and complete-playbook-dev.csv (RSNA_PLAYBOOK)
# sources added 24 Sep: cache/orphanet/en_product6.xml 22.6 MB + en_product4.xml 47.9 MB (Orphadata genes, phenotypes), cache/who-icd11/ (WHO mapping.zip, ICD-11 2026-01, 6.8 MB), cache/hgnc/hgnc_complete_set.txt 17 MB, cache/orphanet/en_product1.xml 54 MB (Orphadata), cache/reactome/{UniProt2Reactome,ReactomePathways,ReactomePathwaysRelation}.txt 45 MB (Reactome v97)
# sources added: uberon-basic.obo 12.1 MB + uberon.sssom.tsv 3.9 MB (Uberon v2026-06-23), MBS-XML-20260801.XML 8.3 MB (MBS Online)
.venv/bin/python scripts/graph_register.py        # only when the SNOMED CT-AU pin moves
scripts/rebuild.sh                                # the build and every guard below, in order, stopping at the first failure
.venv/bin/python scripts/build_edges.py           # ~7 min: out/graph.duckdb, validated against the register
#   refuses to run if any source is missing (a deleted folder used to rebuild a smaller graph silently);
#   --allow-missing NAME builds without one on purpose and records it in build_log
#   reads in place: LOINC_EXTENSION (the LOINC Extension Snapshot dir) and LOINC_TABLE (Loinc.csv); defaults under ~/Documents/ONTOLOGIES
.venv/bin/python scripts/graph_report.py          # scores the linkage routes, sets their tiers, writes out/graph_report.json
.venv/bin/python scripts/consistency.py           # ~10 s: equivalence clusters, one-to-one conflicts, bridge edges (docs/consistency.md)
.venv/bin/python scripts/release_guard.py         # seconds: per-release limits on edge / node / conflict / island counts (Guards)
.venv/bin/python scripts/completeness.py          # ~1 min: completeness by group, absent members classed (docs/completeness.md);
#   exits 1 if a cell's present share fell against reference/completeness_baseline.json (--set-baseline to accept)
```

## Inputs, and rebuilding on another machine

`reference/graph_inputs_manifest.json` lists every input the build reads — 27 entries, with source, version, licence,
and each file's size and sha256 — and `scripts/graph_inputs.py` keeps a copy of everything outside the licensed
releases in **`~/Documents/ONTOLOGIES/graph-inputs/`** (1.5 GB: the build's `cache/` inputs including every hand-check
verdict file, `out/compendium.duckdb`, the spine database; `MANIFEST.json` and a `README.md` beside them). With the
ONTOLOGIES folder and this repository, the graph rebuilds anywhere:

```bash
.venv/bin/python scripts/graph_inputs.py restore   # link (or --copy) the stored inputs into cache/ and out/; unzip Athena's
                                                   # CONCEPT / CONCEPT_RELATIONSHIP / CONCEPT_ANCESTOR from its zip
scripts/rebuild.sh                                 # checks the inputs first, then the build and every guard
```

The licensed releases (5.4 GB: SNOMED CT-AU, LOINC, the LOINC Extension, RadLex, RCPA, the RSNA playbook, the Athena
bundle) are read in place; set `ONTOLOGIES=/path` if the folder is elsewhere. Without `~/code/spine`, the build reads the
spine database and Athena files from `out/`. Not needed to build, so not stored: the UMLS and SNOMED US zips (3.1 GB —
re-download with the UTS key), SeMRA (1 GB) and the DrugCentral SQL dump (1.4 GB), each only for re-deriving a stored
file. After an input changes (a new hand check, a new download), `graph_inputs.py export` refreshes the ONTOLOGIES copy
and the manifest; `graph_inputs.py check` (first step of `rebuild.sh`) fails if an input is missing and lists what has
changed since the manifest. Tested 24 Sep on a fresh clone with an empty home directory: restore, then a full rebuild
reproducing the graph and passing every guard.

## Guards

A rebuild can shrink the graph without failing, so four checks run after it, each against a committed baseline of counts
(`scripts/rebuild.sh` runs the build and all four, stopping at the first failure):

| guard | fails when | baseline |
|---|---|---|
| sources (`build_edges.py`) | a source file is missing, unless `--allow-missing NAME` | — |
| register (`build_edges.py`) | an edge's predicate or vocabularies are not the registered ones | `reference/graph_predicates.json` |
| completeness (`completeness.py`) | a cell's present share falls by more than half a point | `reference/completeness_baseline.json` |
| release (`release_guard.py`) | an edge family (usable edges) or a vocabulary vanishes or loses more than 1% (and ≥ 10); clusters with two codes of a one-to-one vocabulary rise more than 5% (and ≥ 5); the largest equivalence cluster more than doubles; islands grow more than 5% (and ≥ 50). An edge family growing more than 25% (and ≥ 1,000) is a warning — a new source, or a load run twice | `reference/release_guard_baseline.json` |

A deliberate change is accepted with `--set-baseline` on the guard that flagged it, and says why in the commit.

## Licences

DrugCentral is CC BY-SA 4.0; HGNC and Reactome are CC0; Orphadata is CC BY 4.0; Uberon is CC BY 3.0; the MBS XML is Commonwealth of Australia material from MBS Online; ChEMBL (the witness answers in cache/chembl/) is CC BY-SA 3.0; MONDO is CC BY 4.0; HPO is free to use with attribution under its own licence; SNOMED
CT-AU, AMT and PBS data are used under the compendium's existing terms. LOINC and the SNOMED CT LOINC Extension are
licensed releases read in place and never committed; the hand-check file carries LOINC codes and names under the LOINC
licence's notice terms. DrugBank and SIDER (non-commercial) are not
imported. The RCPA SPIA reference sets are RCPA copyright (NCTS terms of use): read in place, derived data in cache/rcpa/
only, and a graph built with them is not for redistribution. ICD-O-3, ICD-11 and WHO ICD-10 are WHO's: only codes are loaded, never labels. MeSH is NLM's (public domain). UMLS is used under the licence holder's UMLS licence: level 0 sources and SNOMED CT only, UMLS-derived data in cache/umls/ only, and a graph built with it is for UMLS licensees. ARTG ids are TGA identifiers shipped in SNOMED CT-AU. The SNOMED CT US Edition (for the ICD-10 and ICD-10-CM maps) is used under the UMLS licence and the SNOMED affiliate licence Australia's membership covers: kept in cache/snomed-us/, never committed. RadLex and the RSNA Radiology Playbook are RSNA's, used under the RadLex licence: read in place, derived data in cache/radlex/, and only RadLex codes (no labels) in committed files. *These were stated from memory while designing and should be confirmed before any commercial use.*
