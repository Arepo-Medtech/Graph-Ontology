# The weighted directed multigraph: tiers, selection protocol, inventory and scorer

*Drafted 23 September 2026. Design, not yet built — except the scorer (`scripts/route_scorer.py`), which runs.*
*Companion: `reference/graph_tiers.json` (the tier schema as data).*

## Rule zero

**An edge with no trace to its source is not an edge.** It is not written, not displayed, and not used in
traversal. 100%, at every tier, including Tier 3 — where the trace names the author, date and prompt rather than a
document, so the claim is attributable even when it is not sourced. This is the contract all 145
`guidelines/*.verification.json` files already keep; the graph inherits it rather than inventing a weaker one.

Every count in this document is traced to the query or table it came from. Three assertions I made while drafting
were wrong and were caught by that rule; they are recorded in [What drafting corrected](#what-drafting-corrected).

---

## 0. Findings the design rests on

Established while designing, 23 September 2026, and measured where a number is given.

- **Five kinds of meaning, three mechanisms.** Edges carry nouns joined by verbs, and some carry adjectives
  (qualifiers), temporality or rationality (quantity). But the five are carried by three different mechanisms, and
  conflating them would sink an implementation: **graph edges**; **typed tables** for quantities (`DRUG_STRENGTH`'s
  2,966,568 rows are a join, never traversed); and **free-text fields** in sources (PBS severity on 192 of 653
  indications, "Severe" and "severe" distinct strings), which ride as edge attributes until bound. The register gives
  every edge type a `category` on this frame.
- **Signs and symptoms are nouns, not adjectives.** In SNOMED they are clinical findings — entities asserted present
  or absent. The adjective layer is the Qualifier Value hierarchy (15,747 in the Observation domain, 6,017 as
  measurement answers) that modifies them.
- **An examination finding is one concept with two value slots**: `value_as_number` + unit (rationality) or
  `value_as_concept_id` drawn from the answer qualifiers (adjective). LOINC's SCALE axis declares in advance which slot
  a term uses.
- **The edge-type funnel.** `RELATIONSHIP.csv` defines 724 relationship types; 328 carry any data in this bundle (55%
  of the catalogue is empty — every indication type among them); 62 are reachable from the compendium's own concepts;
  the compendium used one (`Maps to`). It used OMOP to arrive and never to travel onward.
- **OMOP flattens the poly-hierarchy at the domain boundary.** Every concept gets exactly one `domain_id`, and 4,875
  standard SNOMED concepts have parents in more than one domain — for those OMOP chose, and the losing parentage is
  invisible in the CDM.

## Reuse: what was taken rather than rebuilt

PrimeKG (Harvard MIMS; 129,375 nodes, 4,050,249 relationships, 30 relation types, 20 sources, December 2023) was
the reference design. Its relation names are used in the register where they match (`indication`,
`contraindication`, `off-label use`, `disease_phenotype_positive / _negative`, `disease_disease`,
`phenotype_phenotype`). Its **data** was not taken, for three reasons: it merged 22,205 MONDO concepts into 17,080 by
embedding similarity (the upper-approximation error), its edges are undirected, and it drops HPO's frequency data.
The primary sources were imported instead — MONDO, HPO and DrugCentral — at their own granularity. PrimeKG's
DrugBank (drug–drug) and SIDER (side-effect) layers are non-commercial and were not imported.

The graph-neural-network half of the reference pipeline (PyTorch Geometric, heterogeneous GAT) is downstream of
linkage: the edge table maps directly onto PyG's `HeteroData` (node type = vocabulary, edge type = subject
vocabulary × predicate × object vocabulary) when it is wanted. A learned link prediction would be a hypothesis in
this scheme — Tier 3 in kind — and would enter the look-up queue, never the edge table.

## 1. Tier schema

Full definitions: `reference/graph_tiers.json`. In brief:

| tier | source class | admission | may emit | collapse to one target? |
|---|---|---|---|---|
| **1** | lookup, clean | route Wilson lower bound **≥ 0.99**, fired ≥ 30 | exact, likelihood ratio | yes |
| **2** | lookup, ambiguous but significant | Wilson lower bound **≥ 0.80** | LR interval, belief interval, direction, ordinal | **no** — carries its frame |
| **3** | authored from memory | fixed by provenance | **ordinal only** | no |
| inadmissible | lookup, scored below Tier 2 | — | nothing — output becomes review-queue *candidates* | — |
| ignorance | no route fired, no candidate | — | recorded as ignorance, **not** as "no edge" | — |

**A tier is earned, never declared.** `route_scorer.py` assigns it from the Wilson lower bound on a held-out truth
set. A route's author states only its *source class* (lookup or authored). This was not the first draft — see
[What drafting corrected](#what-drafting-corrected).

**Tier 3 is ordinal-only by construction.** A number recalled from memory is indistinguishable in a column from a
measured one, and it will be multiplied, displayed and eventually believed. Tier 3's job is **queue generation**:
ranking which of ~10⁴ plausible edges deserve a Tier 1 or 2 lookup. It lives in a separate table
(`edge_authored`), never merges into `guidelines/`, never combines with Tier 1–2 weights, and is never displayed
clinically.

---

## 2. Selection protocol

Every candidate edge passes this procedure. It is deterministic; a person enters only at the marked points.

```
                    ┌──────────────────────────────┐
  candidate edge ──▶│ 0. Has a source trace?       │── no ──▶ REJECT (rule zero)
                    └──────────────┬───────────────┘
                                   │ yes
                    ┌──────────────▼───────────────┐
                    │ 1. How was it derived?       │
                    └──┬────────────┬───────────┬──┘
              lookup   │     gap    │  authored │
       (code to code)  │ (text or   │  (memory) │
                       │ inference) │           │
          ┌────────────▼──┐  ┌──────▼──────┐ ┌──▼──────────────┐
          │ 2. Route's    │  │ 3. Carry    │ │ 4. Tier 3:      │
          │ EARNED tier   │  │ the FRAME   │ │ edge_authored,  │
          │ (route_scorer)│  │ candidates, │ │ ordinal only,   │
          └─┬─────┬────┬──┘  │ mass,       │ │ queue-ranking   │
          T1│   T2│  inad│   │ mass_theta  │ │ only            │
            ▼     ▼     ▼    └──────┬──────┘ └─────────────────┘
      collapse  write   candidates  │
      to one    with    to review   ▼
      target    interval queue    ★ PERSON: resolve via attestation loop
            │     │                  (corrected_pending_attestation)
            └──┬──┘
               ▼
   5. Is it a clinical-safety edge? (indication, diagnosis, monitoring, contraindication)
               │ yes ──▶ default state corrected_pending_attestation ★ PERSON signs off
               ▼
   6. Stamp: source, method, pin, strength_kind, calibrated_on, population_scope
               ▼
   7. Parallel edge already exists (same subject, predicate, object; different source)?
               │ yes ──▶ KEEP BOTH. Never merge. Disagreement is written as a finding.
               ▼
            WRITE
```

Rules the diagram compresses:

1. **Lookups may collapse; gaps must carry their frame.** A code-to-code mapping with an earned Tier 1 is written
   as one target. Anything crossing a gap — free text to a concept, an inference, a name match — carries
   `candidates[]`, `mass[]` and `mass_theta` until a person resolves it.
2. **Ignorance is not absence.** A row with no candidate records all mass on θ. It must never be written as
   "no edge exists": that is how silent false negatives are manufactured.
3. **Never use Dempster's normalised combination rule.** It divides out conflict, and at the measured 20%
   legacy-vs-candidate disagreement rate it would manufacture confident nonsense. Keep conflict mass visible
   (unnormalised, or Yager's rule). Conflict is a finding.
4. **Parallel edges are never merged.** The on-label / off-label distinction *is* the provenance; merge a PBS
   indication edge with an AMH practice edge and the only thing making the bridge safe is gone.
5. **Store the transportable quantity.** Likelihood ratio or log(m/u), not precision. Precision is a positive
   predictive value; it depends on the base rate of the population it was measured in and does not transport.
6. **One LR table, many prior tables.** Evidence weights may pool across Western primary care (Australia, NZ, USA,
   Canada, Europe, UK, Ireland) because sensitivity and specificity are properties of the sign–disease
   relationship. **Priors may not pool**: ARF/RHD prevalence among Aboriginal and Torres Strait Islander people and
   among Māori and Pacific peoples is orders of magnitude above the UK baseline. Priors are keyed by population,
   using the axis `guidelines/sti-care-by-population.md` already uses. Verification bias differs between these
   systems (GP access to imaging and pathology), so every LR carries `calibrated_on` and pooling stays undoable.
7. **Combine along paths source-aware.** Post-test odds = prior × ∏LR only for independent evidence. Every OMOP
   edge inherits the same `AMT v20210630` snapshot; chaining three of them multiplies one piece of evidence three
   times. Correlated edges (same source, same pin) combine as one.
8. **Traversal must bound cycles.** ATC ancestry, `Is a` and salt↔base contain cycles. Every traversal carries a
   visited-set and a depth cap.

---

## 3. The edge record

```
edge(
  edge_id,
  subject_id, subject_vocab, subject_level,
  predicate,
  object_id,  object_vocab,  object_level,
  source,            -- the document, schedule, bundle or study.  NOT NULL (rule zero)
  source_locator,    -- URL, file:line, schedule code, DOI
  method,            -- the route that produced it
  tier,              -- earned: '1' | '2' | '3'
  strength_kind,     -- exact | likelihood_ratio | belief_interval | possibility | rough_boundary | ordinal
  strength_lo, strength_hi,
  candidates, mass, mass_theta,   -- gap-crossing edges only
  calibrated_on,     -- truth set, n, setting, study design
  population_scope,  -- default 'western_primary_care'
  pin,               -- the edition / schedule / bundle it is true under
  state,             -- asserted | corrected_pending_attestation | attested | rejected
  attrs              -- JSON: severity, episodicity, staging, dose context ...
)
prior(condition_id, population, prevalence_lo, prevalence_hi, source, source_locator, pin)
edge_authored(... same shape, tier='3', strength_kind='ordinal', author, prompt_ref ...)
```

`pin` is on the edge because an edge is not true absolutely — it is true *under a pin*. That is where
poly-pinning earns its place: not multiplying hierarchies (the union of editions scored RMS 0.161 against 0.017
for own-edition in the Data Golf pregnancy work — the upper approximation is a bound, not an answer), but **dating
the edges**, so an edition diff is edges appearing and disappearing.

---

## 4. Node inventory

Widest scope, every class traced. Counts are from the Athena bundle (`v5.0 29-AUG-26`), the compendium database,
`spine.duckdb`, or the PBS cache (schedule 4333), measured 23 September 2026.

### Drug layer

| node class | count | source |
|---|---:|---|
| AMT containered trade product pack (CTPP) | 50,748 | `product.tag` |
| AMT trade product pack (TPP) | 47,960 | `product.tag` |
| AMT trade product unit of use (TPUU) | 24,634 | `product.tag` |
| AMT medicinal product pack (MPP) | 17,008 | `product.tag` |
| AMT medicinal product unit of use (MPUU) | 16,137 | `product.tag` |
| AMT trade product (TP) | 14,683 | `product.tag` |
| AMT medicinal product (MP) — abstract | 9,858 | `product.tag` |
| AMT medicinal product form (MPF) — abstract | 7,537 | `product.tag` |
| Substance (AMT / SNOMED CT-AU) | 6,592 | `substance` |
| RxNorm / RxNorm Extension ingredient | 36,389 (3,269 reached) | `CONCEPT.csv` |
| ATC class, levels 1–5 | 2,672 ingredients reach level 1 | `CONCEPT_ANCESTOR.csv` |
| Dose form, route, unit (UCUM 1.8.2) | — | RF2 / `VOCABULARY.csv` |
| Brand / supplier | — | `brand_of`, OMOP `Has supplier` |
| PBS item | 14,964 | `cache/pbs/items.json` |
| PBS restriction | 3,581 | `cache/pbs/restrictions.json` |
| PBS clinical criterion | 2,918 | PBS API `criteria` `_meta` |

### Clinical layer

| node class | count | source |
|---|---:|---|
| SNOMED Condition domain | 114,498 | `CONCEPT.csv` |
| SNOMED Observation domain | 115,163 | `CONCEPT.csv` |
| SNOMED Procedure domain | 51,275 | `CONCEPT.csv` |
| SNOMED Measurement domain | 32,007 | `CONCEPT.csv` |
| SNOMED body structure (Spec Anatomic Site) | 38,455 | `CONCEPT.csv` |
| SNOMED Qualifier Value (adjectives) | 15,747 obs · 6,017 meas-value · 1,376 unit · 478 drug · 210 route | `CONCEPT.csv` |
| SNOMED Staging / Scales (ordinals) | 3,084 | `CONCEPT.csv` |
| PBS indication (condition + severity + episodicity) | 653 | `cache/pbs/indications.json` |
| Corpus condition | 639, of which **265 carry a SNOMED binding** | `reference/snomed_bindings.json` (`results[].snomed` non-null) |
| LOINC term | 103,225 | `spine.duckdb` `loinc_axis` |
| LOINC component (analyte) | 62,317 parts | `CONCEPT.csv` |
| LOINC answer (coded value) | 22,146 | `CONCEPT.csv` |
| LOINC method (the only verb axis) | 2,521 | `CONCEPT.csv` |
| Population | the ten in `sti-care-by-population.md`, extensible | corpus |

### Evidence and provenance layer

| node class | count | source |
|---|---:|---|
| Guideline (verified) | 145 | `guidelines/*.verification.json` |
| Clinical evidence claim (pregnancy safety etc.) | 34 | `reference/amh_clinical_evidence.json` |
| Human decision | 10 | `reference/rxnorm_substance_decisions.json` |
| Source document / schedule / bundle / study | one per trace | the `source` column |
| Pin | 7 active | RF2 `REL="20260731"` in `build_compendium.py`, `rxnorm_resolve.py`, `rxnorm_enrich.py`, `drug_strength.py`; NCTS edition `20260831` at `bind_ontoserver.mjs:116`; Athena `v5.0 29-AUG-26` in `VOCABULARY.csv`; PBS `schedule_code 4333` in `cache/pbs/*.json`; AMH `REL` in `resolve_locators.py`; foundry versions in `foundry.py`; RxNav **unpinned**. Two SNOMED CT-AU editions are live at once. To be consolidated as `reference/pins.json` |

---

## 5. Edge inventory

Grouped by subgraph. **L** = lookup (may reach Tier 1). **G** = gap (carries its frame). Counts traced as above.

### A. Drug structure — from RF2, authoritative for Australian products

| predicate | SNOMED attribute | L/G | note |
|---|---|:-:|---|
| `is_a` | 116680003 | L | the poly-hierarchy: 42% of standard SNOMED concepts have >1 parent |
| `has_active_ingredient` | 127489000 | L | |
| `has_precise_active_ingredient` | 762949000 | L | |
| `has_basis_of_strength` | 732943007 | L | |
| `has_dose_form` | 411116001 | L | |
| `has_product_name` | 774158006 | L | brand |
| `contains_clinical_drug` | 774160008 | L | pack → unit |
| strength *(typed attribute, not an edge)* | AMT OWL | L | `DRUG_STRENGTH` holds 2,966,568 rows; quantity is a join, never an edge |

### B. Standard side — OMOP, current where AMT's copy is stale

62 edge types are reachable from the compendium's 160,718 concepts; **one** (`Maps to`) is used. The compendium
uses OMOP to *arrive* and never to travel onward. The worthwhile ones:

| predicate | edges | L/G | why |
|---|---:|:-:|---|
| `Maps to` | 159,331 | L | the transcode; the only one in use |
| `Has marketed form` / `Marketed form of` | 256,692 / 36,251 | L | natively states marketed-vs-abstract — **audits the tag heuristic** the review queue now ranks by |
| `Active ing of` | 27,262 | L | parallel to RF2 `has_active_ingredient` |
| `Basis str subst of` | 11,511 | L | parallel to item 16's salt→base (406 of 497 converged) |
| `Consists of` | 14,653 | L | combination decomposition — the legitimate 1:N product edge |
| `Has tradename` / `Tradename of` | 68,165 / 25,373 | L | commercial layer |
| `Has brand name` | 27,124 | L | |
| `Has supplier` | 18,519 | L | |
| `Available as box` / `Box of` | 37,209 / 15,610 | L | pack structure on the standard side |
| `RxNorm has dose form` | 50,715 | L | third opinion beside `product_route` and PBS |
| `RxNorm is a` | 19,905 | L | |
| `RxNorm - SPL` | 91,822 | L | Structured Product Labels — labelling AMT does not carry (US, not TGA) |
| `Mapped from` | 191,022 | L | reverse transcode |

### C. Classification

| predicate | extent | L/G | note |
|---|---|:-:|---|
| `in_atc_class` (PBS) | `product_atc` | L | |
| `in_atc_class` (OMOP ancestry) | 2,961 ingredients, avg 16.1 ancestors, median 5, max 137 | L | **parallel edge** to the PBS route; disagreement already measured in `product_atc_check` |
| multi-branch ATC | **619** ingredients under >1 top-level branch | L | genuine poly-parentage across vocabularies — prednisolone 8, metronidazole 7, dexamethasone 6 |

### D. Indication — drug → condition (PBS)

The chain, corrected and measured end to end:

```
AMT concept ─amt-items─▶ PBS item ─item-restriction─▶ restriction ─restriction-prescribing-text─▶ indication
  60,335 rows           5,765 items    23,550 links       3,043 / 3,043 reach        653 / 653 reached
```

| predicate | edges | L/G | note |
|---|---:|:-:|---|
| `pbs_indicated_for` (AMT → PBS condition text) | **16,929**, from **10,024** AMT concepts | L | every hop is a code join |
| `condition_text → SNOMED condition` | 653 texts | **G** | the one gap: *"Metastatic (Stage IV)"* is a condition, a staging ordinal and a severity in one string. Carries a frame; resolved through the binder and its attestation loop |
| edge attributes | severity on 192 of 653 (29%), episodicity on 42 (6%) | — | **free text, not a controlled vocabulary** — "Severe" (33) and "severe" (7) are distinct strings |

Edges land mostly on packs (TPP 4,699, MPP 2,246, MPUU 2,125, MP 858, TPUU 96) because PBS lists items. An
indication belongs to the molecule, not the pack size, so the build **rolls up** TPP → MP through
`contains_clinical_drug` and `is_a` and asserts the edge at the lowest level at which every descendant agrees.

**Not on-label.** A PBS restriction is "what is subsidised, under what criteria" — a real, defensible Australian
indication set, but not the TGA label. The predicate is `pbs_indicated_for`, deliberately not `indicated_for`.

OMOP cannot supply this layer: `Has FDA-appr ind`, `Has off-label ind`, `Has CI` and `May be treated by` are
defined in `RELATIONSHIP.csv` and carry **zero rows** in this bundle (FDB and NDF-RT are not licensed into it).

### E. Diagnostic — sign → diagnosis

| predicate | L/G | strength_kind | note |
|---|:-:|---|---|
| `sign_suggests` (LR+) | G | likelihood_ratio | Tier 1 from JAMA RCE / Cochrane DTA with intervals; Tier 2 single studies; Tier 3 ordinal only |
| `sign_argues_against` (LR−) | G | likelihood_ratio | a separate edge: LR− is not 1/LR+ |
| `finding_site` | L | exact | SNOMED attribute, body structure |
| `has_severity` / `has_clinical_course` / `has_temporal_context` | L | exact | OMOP: 49 / 7,268 / 9,126 edges — severity is effectively empty in OMOP |
| `has_staging` | L/G | ordinal | Staging / Scales, 3,084 concepts; order without arithmetic |

Record linkage and diagnosis are the same mathematics: m = sensitivity, u = 1 − specificity, log(m/u) = log LR+.
`scripts/evidence_scorer.py` already implements it for record linkage.

### F. Measurement and monitoring

| predicate | extent | L/G | note |
|---|---|:-:|---|
| `same_substance_as_analyte` | **985** AMT substances equal a LOINC component by name | **G** | a name join — the route class the scorer rates *inadmissible* for substances. Must be scored before admission |
| `therapeutic_drug_monitoring` | — | **G** | a **clinical claim**, distinct from the above. Ibuprofen is measurable; it is not routinely monitored. Needs a Tier 1–2 source |
| LOINC axes: `has_component`, `has_property`, `has_time_aspect`, `has_system`, `has_scale`, `has_method` | 572,986 axis rows | L | the rationality (property), temporality (time) and scale axes; `SCALE` declares in advance whether a value is quantitative (Qn) or adjectival (Ord / Nom) |
| `has_answer` | 22,146 answers | L | fills `value_as_concept_id` — the axis Eos flattens (`DvCodedText extends DvText`), worked around by `spine omop coded-values` |

### G. Population and safety

| predicate | extent | L/G | note |
|---|---|:-:|---|
| `prevalence_in` | — | G | a **prior**, stored in `prior`, keyed by population — never pooled |
| `pregnancy_safety` | 34 claims | L | `amh_clinical_evidence.json`, each with route, gestational window and dose context |
| `contraindicated_in` | — | G | clinical-safety: default `corrected_pending_attestation` |

### H. Provenance — on every edge

| predicate | note |
|---|---|
| `asserted_by` → source | rule zero |
| `valid_under` → pin | the edge is true under a pin |
| `decided_by` → decision | `rxnorm_substance_decisions.json`, `binding_corrections.json` |

---

## 6. Parallel edges, cycles and loops — enumerated

The multigraph properties are not incidental; each has a known instance.

**Parallel edges** (same subject, predicate, object; independent sources — disagreement is a finding):

| fact | source 1 | source 2 |
|---|---|---|
| product → ATC class | PBS `item-atc-relationships` | OMOP ancestry |
| product → active ingredient | RF2 127489000 | OMOP `Active ing of` |
| salt → base | item 16 (AMT) | OMOP `Basis str subst of` |
| product → dose form | AMT dose form | OMOP `RxNorm has dose form` (+ PBS routes) |
| marketed vs abstract | AMT level tag (the queue's heuristic) | OMOP `Has marketed form` |
| drug → condition | PBS restriction | AMH guideline (practice, incl. off-label) |
| substance → RxNorm | RxNav | OMOP code route — already reconciled as `omop_substance.agreement` |

**Cycles**:

- salt → base → salt (`has_basis_of_strength` with its reverse)
- `Is a` + `Subsumes` (a concept and its reverse edge)
- drug → ingredient → ATC class → drugs in class → drug
- condition → indicated drug → other indications of that drug → condition

**Loops** (self-edges):

- a substance that is its own basis of strength
- an abstract MP that `is_a` grouper containing itself through AMT's `-containing product` concepts

---

## 7. The evaluation scorer

`scripts/route_scorer.py`, runnable now:

```bash
.venv/bin/python scripts/route_scorer.py            # writes out/route_scores.json
```

It scores every edge-producing route on **one common evaluation** rather than one common scale — the internal
measures (belief, likelihood ratio, ordinal) are not commensurable, and z-scoring them fails for four reasons:
moments need an additive scale, a point destroys the ignorance width, z is non-stationary (adding edges would
change existing edges' strengths), and comparable is not interchangeable.

**What it measures, per route:**

| metric | meaning |
|---|---|
| fired / coverage | how often the route answers at all |
| precision | when it answers, how often it is right — a PPV, prevalence-dependent |
| Wilson 95% | because 24/32 and 3,074/3,074 are not the same evidence |
| m, u, log(m/u) | Fellegi & Sunter weight — prevalence-*independent*, the quantity to store |
| hard-population silence | on rows no truth exists for: does the route go quiet, or guess? |
| **earned tier** | assigned from the Wilson lower bound; never declared |

**Truth set:** 3,119 substances where RxNav resolved and OMOP independently agreed — two sources, so no method
marks its own work. **Hard set:** 1,143 review-queue rows.

**Results, 23 September 2026:**

| route | fired | precision | Wilson lower | log(m/u) | hard fired | **earned** |
|---|---:|---:|---:|---:|---:|:-:|
| `code:snomed-maps-to-ingredient` | 3,074 | 1.000 | 0.9988 | 8.01 | 153 | **1** *(name kept)* · gap *(renamed)* |
| `deprecation:name-then-replaced-by` | 82 | 0.951 | 0.8812 | 4.32 | 8 | **2** |
| `name:exact-normalised` | 32 | 0.750 | 0.5789 | 3.16 | 66 | **inadmissible** |

Read with its limits:

- **u hits its floor for the code route** (1/|distinct gold values|). The true weight is higher than 8.01; the
  stored value is a lower bound, which is the safe direction.
- **m as computed includes coverage.** For the strength of a route *when it fires*, read precision and its
  interval; log(m/u) is the transportable weight across populations.
- **The code route fired on none of the 9 hand-decided rows**, and I read that as "its failure mode is silence,
  not error". **The hand check disproved it.** On the 153 hard-population answers it was right 40 of 40 where it kept
  the substance's name and **wrong 6 of 18 where it changed it** — including *tetanus antitoxin → tetanus toxoid
  vaccine*. The Tier 1 score did not transport. The route's earned tier must therefore be read **conditionally**:
  Tier 1 when the name is kept, a gap that carries its frame when the name changes. See
  `docs/rxnorm-review-queue.md` (third pass) and `reference/rxnorm_route_resolutions.json`.
- The same reading applies to everything already relying on OMOP's single answer: of the review queue's 61
  "OMOP resolves it" rows — all renamed — 16 were flagged on review.

- **Product level, the same route:** 108,727 AMT → OMOP product mappings checked against three witnesses
  independent of OMOP (ingredient via RxNav, brand, strength). 88.9% fully confirmed; 110 rejected, 36 of them from
  a single cross-wired OMOP release (`Maps to` valid from 2026-02-03, 37% wrong). The lesson generalises: **a
  witness drawn from the same source is not a witness** — OMOP's product and substance mappings agreed with each
  other on 65 wrong strength checks. See `docs/omop-drug-audit.md`.

**Next routes to add:** `Has marketed form` against the AMT tag heuristic; salt→base against OMOP
`Basis str subst of`; the 985 substance↔analyte name join (expected inadmissible for the reason the name route is);
condition-text → SNOMED against the 265 conditions that already carry a binding (of 639 in the file).

---

## What drafting corrected

The 100%-trace rule caught three errors in this design before they were published. All three are left here because the
method is only worth anything if it is seen to work.

1. **A declared tier.** The first scorer draft let each route declare its tier. I declared the deprecation route
   Tier 1. It scored 95.1% (4 wrong in 82), Wilson lower bound 0.88 — Tier 2. Tiers are now earned, and a route's
   author may state only its source class.
2. **A wrong join, on the most important bridge.** I first joined PBS restrictions to indications through
   `treatment_of_code`. It resolves for **69 of 3,043** restrictions — 2%. The key is the prescribing text: an
   indication *is* a prescribing text. Through `restriction-prescribing-text-relationships` the chain is complete —
   3,043 of 3,043, all 653 indications, 16,929 edges. Had the first join been published, the bridge the whole
   design leans on would have looked like a failure.
3. **A count I had repeated all session.** I described the corpus as "639 SNOMED-bound conditions". The bindings
   file holds 639 conditions; **265** carry a SNOMED binding. So the indication bridge's gap hop is *not* already
   done by the binder for most conditions — 374 are unbound, and PBS condition texts will add more. Caught by
   re-verifying the figure after rebasing onto a commit that restored bindings lost to the 20260831 rename.

## Build order

1. ~~Land the 153 code-route resolutions with a hand-checked sample~~ — done; see `docs/rxnorm-review-queue.md`.
2. ~~Create the `edge` table~~ — done; see `docs/multigraph-build.md`. 4,031,867 edges, all validated against the
   register.
3. Bind the 653 PBS indication texts to SNOMED (`pbs:indication_is`, registered as `needs_binding`) — the one gap in
   the indication chain.
4. `Has marketed form` — it audits a heuristic already shipped.
5. The diagnostic layer (§5E): `sign_suggests` / `sign_argues_against` stay `needs_source` until Tier 1 sources are
   retrieved. HPO frequency gives P(sign | disease) for rare diseases only; HPO → SNOMED has no lookup path.
