# The medical multigraph, as built

*23 September 2026. Design: `docs/weighted-graph-design.md`. Register (the contract): `reference/graph_predicates.json`.*

**893,831 nodes, 4,031,867 edges, 142 edge types, 16 vocabularies — every edge validated against the register.**
Written to `out/graph.duckdb` (144 MB, git-ignored), rebuilt from source in about two minutes.

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

- **HPO phenotypes cannot be linked to SNOMED findings by lookup.** `hp.obo` (2026-09-02) carries no SNOMED or UMLS
  cross-references — its top xrefs are Fyler, NCIT and MedDRA (92). HPO therefore joins the graph on the *disease*
  side (OMIM / Orphanet ↔ MONDO, 12,772 of 12,867) but not the *phenotype* side. `hp:maps_to_snomed` is registered as
  `needs_source`.
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
SNOMED International's LOINC Ontology (module 11010000107) would bridge more, but is not on the public Ontoserver.

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

## Three walks

```bash
# the PBS indications of an adalimumab pack: 10, through its restrictions
.venv/bin/python scripts/graph_walk.py SCT:967341000168102 --follow pbs:lists,pbs:has_restriction,pbs:restricted_to --depth 3

# myocardial infarction's poly-hierarchy: two parents (ischaemic heart disease, myocardial necrosis)
.venv/bin/python scripts/graph_walk.py SCT:22298006 --follow sct:116680003 --depth 3

# four sources, three vocabularies: Azamun (AMT) -> azathioprine (SNOMED CT-AU) -> DrugCentral 269 -> 14 labelled indications
.venv/bin/python scripts/graph_walk.py SCT:6383011000036106 --follow sct:127489000,~drugcentral:snomed,drugcentral:indication --depth 3
```

## Rebuild

```bash
# sources (cache/, git-ignored): mondo.obo 53.1 MB, mondo.sssom.tsv 13.1 MB, phenotype.hpoa 35.8 MB, hp.obo 10.9 MB,
# drugcentral.dump.11012023.sql.gz 1.40 GB -- URLs in scripts/build_edges.py and scripts/drugcentral_extract.py
.venv/bin/python scripts/drugcentral_extract.py   # ~10 s: streams the dump, keeps 4 tables, no Postgres needed
.venv/bin/python scripts/graph_register.py        # only when the SNOMED CT-AU pin moves
.venv/bin/python scripts/build_edges.py           # ~2 min: out/graph.duckdb, validated against the register
.venv/bin/python scripts/graph_report.py          # scores the linkage routes, sets their tiers, writes out/graph_report.json
```

## Licences

DrugCentral is CC BY-SA 4.0; MONDO is CC BY 4.0; HPO is free to use with attribution under its own licence; SNOMED
CT-AU, AMT and PBS data are used under the compendium's existing terms. DrugBank and SIDER (non-commercial) are not
imported. *These were stated from memory while designing and should be confirmed before any commercial use.*
