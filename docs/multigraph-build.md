# The medical multigraph, as built

*23 September 2026. Design: `docs/weighted-graph-design.md`. Register (the contract): `reference/graph_predicates.json`.*

**954,396 nodes, 4,474,223 edges, 156 edge types, 19 vocabularies — every edge validated against the register.** (The family table below is the first build; the bridges are listed in *Non-pharmacological bridges*, *Lab results → findings* and *How a drug works*.)
Written to `out/graph.duckdb` (147 MB, git-ignored), rebuilt from source in under three minutes.

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
| SNOMED CT-AU: poly-hierarchy, AMT structure, finding site, morphology, method, laterality, occurrence, clinical course … (115 attribute types) | RF2 snapshot 20260731 | 2,168,500 |
| LOINC axes (component, property, time, system, scale, method) and answers | LOINC 2.82 via Athena | 687,434 |
| product → ATC, **PBS and OMOP as parallel edges** | PBS 4333 / Athena 29-AUG-26 | 573,569 |
| HPO disease → phenotype, present and absent, with frequency / onset / sex | HPO 2026-09-02 | 268,906 |
| AMT product → standard drug (direct 102,656 · rejected 110 · indirect 5,971) | Athena 29-AUG-26 | 108,737 |
| MONDO is-a, and exactMatch → SNOMED / ICD-10-CM / OMIM / Orphanet | MONDO 2026-09-01 | 77,570 |
| PBS: AMT → item → restriction → indication | PBS schedule 4333 | 61,237 |
| DrugCentral: indication 38,399 (all three kinds) · SNOMED 7,470 · ATC 5,148 · RxNorm 3,539 | DrugCentral 2023-11-01 | 54,556 |
| HPO is-a | HPO 2026-09-02 | 24,436 |
| substance → standard ingredient | review decisions, scored route, RxNav | 4,689 |
| ICD-10-CM → SNOMED (for MONDO's codes; exists to score MONDO) | Athena 29-AUG-26 | 1,968 |
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

## Rebuild

```bash
# sources (cache/, git-ignored): mondo.obo 53.1 MB, mondo.sssom.tsv 13.1 MB, phenotype.hpoa 35.8 MB, hp.obo 10.9 MB,
# genes_to_disease.txt 1.5 MB (HPO release v2026-09-01),
# drugcentral.dump.11012023.sql.gz 1.40 GB -- URLs in scripts/build_edges.py and scripts/drugcentral_extract.py
.venv/bin/python scripts/drugcentral_extract.py   # ~10 s: streams the dump, keeps 9 tables, no Postgres needed
.venv/bin/python scripts/chembl_moa_witness.py    # ~3 min, once per DrugCentral release: ChEMBL's verdict on each mechanism
.venv/bin/python scripts/graph_register.py        # only when the SNOMED CT-AU pin moves
.venv/bin/python scripts/build_edges.py           # ~2.5 min: out/graph.duckdb, validated against the register
#   reads in place: LOINC_EXTENSION (the LOINC Extension Snapshot dir) and LOINC_TABLE (Loinc.csv); defaults under ~/Documents/ONTOLOGIES
.venv/bin/python scripts/graph_report.py          # scores the linkage routes, sets their tiers, writes out/graph_report.json
```

## Licences

DrugCentral is CC BY-SA 4.0; ChEMBL (the witness answers in cache/chembl/) is CC BY-SA 3.0; MONDO is CC BY 4.0; HPO is free to use with attribution under its own licence; SNOMED
CT-AU, AMT and PBS data are used under the compendium's existing terms. LOINC and the SNOMED CT LOINC Extension are
licensed releases read in place and never committed; the hand-check file carries LOINC codes and names under the LOINC
licence's notice terms. DrugBank and SIDER (non-commercial) are not
imported. *These were stated from memory while designing and should be confirmed before any commercial use.*
