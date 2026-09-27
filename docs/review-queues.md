# Review queues: what waits for a person

*24 Sep 2026. Every item below crossed a gap by name, or failed a hand check as a family, so the graph holds it as a
candidate and never as an edge. Each queue says where it lives, what a reviewer decides, and whether the build can take
a decision in yet.*

| queue | size | file | the decision | intake today |
|---|---:|---|---|---|
| **Corpus conditions** not bound to SNOMED | 374 (14 newly exact-bound) | `reference/corpus_condition_candidates.json` | bind to one of the candidates, or none | ✅ `binding_review.py --harvest` → `binding_corrections.json` → `apply_corrections.py` (docs/binding-review-loop.md) |
| **PBS indication texts** not bound | 341 (295 with candidates) — **decided 24 Sep by Ken on Claude's first reading, after a second search: 200 accepted (169 likely matches, 19 closest), 107 none; credited "Ken (on Claude's first reading)"** | `reference/pbs_indication_bindings.json` (`results`) | the SNOMED condition the listing means | ✅ sheet `pbs_indications` |
| **Likelihood ratios**: bound, family held | 130 | `reference/diagnostic_accuracy_bindings.json` | confirm the test / score / prognosis binding | ✅ automatic: the family loads once its binding earns Tier 2 (right 65 of 79 now; needs a lower bound ≥ 0.80) |
| **Likelihood ratios**: not bound exactly | 455 | same | bind the finding or test to a SNOMED concept | ⚠️ edit the bindings file, re-run `verify_diagnostic_accuracy.py` |
| **HPO → SNOMED**, names differ | 2,071 phenotypes, 2,430 pairs — **first reading 24 Sep: 1,550 phenotypes with a likely match**; the rest read as narrower (289 pairs), broader (174), related (272) or different (41) | `cache/umls/hpo_snomed_candidates.tsv` *(UMLS-derived, not committed)*; reading in `cache/review/hpo_snomed_first_reading.json` | same phenotype or not (a sample was right 34 of 40; errors are narrowings) | ✅ sheet `hpo_snomed` |
| **SNOMED organism ↔ NCBI taxon**, names differ | 3,889 — **first reading 24 Sep: 3,689 with a likely match** (3,484 pairs the same organism, 235 renamed or moved genus); 124 another rank, 107 another organism | `cache/umls/sct_ncbi_candidates.tsv` *(UMLS-derived)*; reading in `cache/review/organism_ncbi_first_reading.json` | same organism (most are reclassifications: *Clostridium lavalense* → *Enterocloster lavalensis*) | ✅ sheet `organism_ncbi` |
| **RadLex anatomy** with no code route | 99 terms, 180 pairs — **reviewed 24 Sep by Ken: 84 terms matched (one SNOMED structure each), 70 pairs rejected, 15 terms left** | `cache/radlex/radlex_sct_candidates.tsv` *(RadLex labels, not committed)* | the SNOMED body structure for head, neck, hand, foot … | ✅ sheet `radlex_anatomy` |
| **MBS items → SNOMED procedure** | 3,937 items, 28,790 candidates (first search + a second search inside the category's reference set) — **first reading 24 Sep: 1,676 items with a likely procedure**; 478 items out of scope (anaesthesia, bulk-billing incentives); 55 receiving-laboratory items inherit the test they render | `reference/mbs_procedure_candidates.json`, `reference/mbs_procedure_candidates_malt.json`; reading in `reference/mbs_procedure_first_reading.json`; out of scope in `reference/mbs_out_of_scope.json` | the procedure the item funds — a billing rule is not an equivalence | ✅ sheet `mbs_procedures` (loads as `person:funds_procedure`, not an identity) |
| **Survey instruments** | 55 pairs, 53 LOINC panels — **reviewed 24 Sep by Ken: 44 accepted, 11 rejected; 9 panels left with no match** | `reference/survey_instrument_candidates.json` | same instrument (a first reading is on each pair: 40 likely same) | ✅ sheet `survey_instruments` |

**Where a person's time buys most.** The survey list is short and pre-read — an hour closes the PHQ, GAD, AUDIT, EPDS, MMSE
family. The 130 held LR bindings need only enough confirmations to lift the family's lower bound past 0.80. MBS is the one
true island in the graph (`graph_report.py` → islands): confirming even a few hundred procedures joins its 6,046 items.

## First readings of the three large queues (24 Sep)

`scripts/review_first_reading.py` puts a first reading on every row of the HPO, organism and MBS sheets, so a reviewer
can accept the likely rows and read only the doubtful ones. It is a reading, not a decision.

- **Rule pass.** A pair whose names agree once synonyms, word order, plurals and *of / the* are set aside is read as
  likely by rule: 795 HPO pairs and 3,077 organism pairs (NCBI's own synonyms and former names, or the same species
  epithet in another genus). HPO's *exact* synonyms can be loose, so the 401 HPO pairs that agree only through a synonym
  were read afterwards and 68 overridden. Two examples: "Neoplasm of the liver" matched to *malignant* neoplasm of liver
  is narrower; "Hyperactivity" matched to ADHD is related, not the same.
- **Read.** Every other row was read from its names and synonyms (MBS: the item descriptor) and given one code:
  HPO S/N/B/R/D (same, narrower, broader, related, different), organisms S/M/K/D (same, renamed or moved, another
  rank, another organism), MBS P/G/N/A/D (the procedure, a more general form, narrower, part of or related, different).
  A subject where no candidate reads as likely is marked *no candidate fits* (answer `none`).
- **MBS: a second search, and what is out of scope.** The first search took the descriptor's head phrase across all
  procedures and often found only a neighbour. A second search (`scripts/mbs_candidates_malt.py`, Ken's pointer) looks
  inside the SNOMED CT-AU reference set suited to the item's category:
  - diagnostic and therapeutic procedures: the **RACS MALT surgical procedure set** (1061861000168107, the procedures surgeons log);
  - imaging: the **Imaging procedure set**;
  - pathology: the **RCPA requesting set**.

  Each item is searched with its head phrase, its first clause, and each part of an "A or B" clause cut to its content
  words. This gave 15,451 new candidates and raised the items with a likely procedure from 1,098 to 1,649.

  478 items fund no procedure of their own: 465 anaesthesia items (anaesthesia time, its initiation or a modifier) and
  13 bulk-billing incentives. They are listed with the reason in `reference/mbs_out_of_scope.json` and kept out of the
  search and the sheet (Ken, 24 Sep).
- **MBS: receiving laboratories inherit.** 55 pathology items fund "a test described in item X, if rendered by a
  receiving APP". Their descriptor names no test, so each takes the candidates and first reading of the item it names
  (`reference/mbs_inherits_from.json`), marked *inherited from item X*.
- **Conventions the MBS readers shared.** Fee tiers and eligibility are set aside. A left/right concept is narrower
  unless the item names one side. A sibling item's variant is *related*. A surgeon's share of a combined operation reads
  as the whole operation.

## How to review (built 24 Sep)

```bash
.venv/bin/python scripts/review_sheets.py make        # out/review/<queue>.csv: one row per candidate, names and my first reading
#   fill the 'decision' column in a spreadsheet:  y = this candidate is right   n = it is not   none = no candidate is
#   (leave it blank to skip; the 'note' column is kept)
.venv/bin/python scripts/review_sheets.py harvest --reviewer "Your name"
.venv/bin/python scripts/review_sheets.py status      # what each queue has left
scripts/rebuild.sh                                    # accepted decisions become edges
```

Decisions go into one file, `reference/candidate_decisions.json` — codes and verdicts only, committed — and
`build_edges.py` loads every accepted one as an edge: `person:same_as` (or `person:funds_procedure` for MBS), method
*confirmed by ⟨reviewer⟩ ⟨date⟩*, tier `decision`. A rejection or *none* is recorded but not loaded; it keeps the subject
out of the next sheet, as does any pair the graph has since found by another route. The sheets carry licensed names, so
they stay in `out/review/` (git-ignored). **Spreadsheets reformat long numbers** (a SNOMED CT id becomes `3.361E+12`), so every row
carries an `id` column with its codes as text, and the harvest reads the codes from there. The corpus-condition queue keeps its own loop (above); the likelihood-ratio
bindings load as a family once their binding earns its tier.

## Wave 2 families (27 Sep)

Five families of cross-vocabulary links that come from sources we hold but rest on UMLS synonymy or a derived step.
**Prepared, not loaded**: nothing below is an edge, `build_edges.py` and `reference/graph_predicates.json` are unchanged.
`scripts/wave2_candidates.py` (read-only on a copy of `out/graph.duckdb`, seed `wave2-27sep`) writes the candidates,
the second-path score and a hand-check sheet per family to `cache/wave2/` (git-ignored: the sheets carry UMLS, SNOMED CT,
DrugCentral and ChEMBL names). *New* means the graph does not already reach the pair. Each sheet has 30 new pairs drawn at
random per stratum, then every new pair the second path contradicts. Every verdict on it is a **first reading (Claude),
awaiting reviewer**. It is not a decision. Wilson lower bounds and tiers follow `reference/graph_tiers.json`
(≥ 0.99 → 1, ≥ 0.80 → 2, fired ≥ 30). Scored against the graph as rebuilt after Wave 3 (1,573,887 nodes).

**1. UMLS concept → OMIM / NCIt / MeSH / HPO members** (`umls_disease_member`). The 24,210 CUI nodes named by MONDO
(exact_match) or Orphanet (xref E), and their non-suppressed MRCONSO 2026AA atoms. MeSH counts headings (MH/NM) only.
Gate: the shared-name rule from `umls_mrconso.py` (the target shares a name with the MONDO / Orphanet label). OMIM gene
entries (HGNC's list) and non-matching susceptibility entries are excluded. `umls:concept_member` for SNOMED has no name
gate, so this rule is stricter than that loader's. Second path: the same MONDO / Orphanet node's own xref in that
vocabulary. Exact is the same code. One line means an Orphanet NTBT/BTNT link, or an ancestor in the MeSH tree, NCIt
is-a or HPO is-a.

| target | candidates | pass gate | already reached | new | both fire | exact / one line | Wilson lower (line) | tier it would earn | sample | first reading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| HPO | 2,273 | 1,518 | 0 | 1,518 | — | no second path | — | hand check | 30 | 30 / 30 (lower 0.886 → 2) |
| MeSH | 8,189 | 4,760 | 4,572 | 188 | 4,589 | 4,572 / 4,576 | 0.995 | 1 | 30 + 13 contradicting | 30 / 30; contradicting 13 / 13 correct |
| NCIt | 7,973 | 6,252 | 5,494 | 758 | 5,539 | 5,494 / 5,513 | 0.993 | 1 | 30 + 26 | 29 / 30 (lower 0.833); contradicting 22 correct, 4 unsure |
| OMIM | 17,012 | 7,498 | 7,120 | 378 | 7,262 | 7,120 / 7,244 | 0.996 | 1 | 30 + 18 | **7 / 30** (18 wrong, 5 unsure); contradicting 0 / 18 |

- **The research estimate (~47,600) was the raw atom count.** Counting MeSH headings only and dropping `MTH*` codes leaves
  35,447 candidates. 20,028 pass the gate and 17,186 of those are already reached through the CUI's own MONDO / Orphanet
  node. The family adds **2,842 new pairs**, and 96 targets would get their first link to another vocabulary (71 of
  them are not yet nodes).
- **The second-path score speaks only for pairs MONDO also maps, and those are exactly the pairs already reached.** It
  does not carry over to the new ones. OMIM shows why: the route scores 0.996 where MONDO agrees, but the new OMIM
  pairs read 7 / 30. They are OMIM *alternative titles*: a numbered type for a group, a variant for the disease, or a
  susceptibility entry reached through an alias. **All 18 OMIM contradictions are wrong.** 14 are gene or locus entries
  whose preferred title names a gene, an imprinting region, an enhancer or a repeat. Each carries the disorder as a
  PHENO atom, which HGNC's list does not catch. The other 4 are neighbouring disease entries. A proposed rule, not applied: an OMIM target must match through its
  PT / ET atoms, not a PHENO atom alone (18 new pairs).
- MeSH and NCIt contradictions are mostly the second path out of date: MeSH's newer disease headings, and NCIt's
  renamed concepts.

**2. UNII ↔ RxNorm ingredient** (`unii_rxnorm`). MTHSPL substance atoms (SU, code = UNII) and RxNorm IN / PIN / MIN
atoms under one CUI: 13,870 pairs. Gate (the `umls:shared_cui` rule): one end is already a node. **5,172 pass**. 2,194
are already carried by DrugCentral on one struct, so **2,978 are new**. 2,282 of the new pairs have neither id in
DrugCentral. 2,169 UNIIs and 427 RxCUIs would be new nodes. Second path: DrugCentral's identifier table. For a UNII
DrugCentral holds, it gives the same RxCUI on the same struct (exact), or RxNorm's own form_of / has_form (line).

| candidates | pass gate | already reached | new | both fire | exact / line | Wilson lower (line) | tier it would earn | sample | first reading |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 13,870 | 5,172 | 2,194 | 2,978 | 2,369 | 2,194 / 2,294 | 0.961 | 2 | 30 + 75 contradicting | 23 / 30, 7 unsure, 0 wrong (lower 0.591); contradicting 72 correct, 3 unsure |

The 75 contradictions read as **DrugCentral's** errors: uridine for uridine triacetate, the prodrug for ceftaroline.
UMLS was right in 72. Six of the 7 unsure pairs in the random 30 are one class: RxNorm names a botanical or
allergenic *extract*, while the UNII identifies the material itself. The seventh is a purified grade paired with the
parent substance. Ken's decision on the extract convention settles most of the family. 451 new pairs where DrugCentral puts the RxCUI on a struct with another UNII (mostly a salt PIN on
the parent's struct) are not counted as contradictions.

**3. Drug → MeSH pharmacological action / ChEBI role** (`drug_pharma_role`). DrugCentral `pharma_class`: 14,274 MeSH PA
rows (470 classes) and 7,385 ChEBI *has role* rows (705 roles).

- **MeSH PA.** None of these rows is in the graph yet, so all 14,274 are new. They would give 427 descriptors their
  first link, 381 of them not yet nodes. **No second path can contradict.** A drug holds many true classes, so the
  check is confirmation only: the drug's FDA EPC / MoA / PE and MED-RT classes, plus its ChEBI roles, compared by
  class name. That confirms 2,271 of 11,376 rows, a floor on corroboration, not a precision.
- **ChEBI roles.** Wave 3 (`chebi:has_role`, ChEBI 255) loaded ChEBI's own roles. Through DrugCentral's ChEBI xref,
  **6,755 of the 7,385 rows are already reached**, so only **630 are new** (194 roles would get a first link). ChEBI
  255 is the same source in a newer release, so this is a check of DrugCentral's copy, not an independent path. It
  agrees on 6,801 of 7,162 rows (exact or on one `chebi:is_a` line: lower 0.944). The new rows are exactly where it
  does not: of 407 that fire, 361 disagree.

| source | candidates | already reached | new | second path (new) | sample | first reading |
|---|---:|---:|---:|---|---:|---|
| MeSH PA | 14,274 | 0 | 14,274 | name agrees 2,271 / 11,376, confirmation only | 30 | 26 / 30, 3 unsure, 1 wrong (lower 0.703) |
| ChEBI role | 7,385 | 6,755 | 630 | ChEBI 255 agrees 46 / 407 (lower 0.086) → inadmissible | 30 + 361 contradicting | 21 / 30, 8 unsure, 1 wrong (lower 0.521); contradicting 225 correct, 86 unsure, 50 wrong |

Many correct rows are true but uninformative: a broad MeSH parent (*Neurotransmitter Agents*), or ChEBI's *xenobiotic*,
*environmental contaminant* and organism-metabolite roles. The new ChEBI rows are those ChEBI has since dropped or
moved. Most of them still hold, as endogenous-metabolite and nutrient roles. The wrong ones are:

- amino acids filed as *trace elements*;
- nicotinamide's cofactor, PARP and sirtuin roles on nialamide and nicotinic acid;
- roles of another compound (an anticoagulant filed as anti-asthmatic);
- a nucleoside analogue filed as a PBP3 inhibitor.

The unsure ones are mostly ChEBI's *geroprotector* and in-vitro *anticoronaviral* roles. On MeSH, the one wrong row is
a sulfonylurea filed as a radioprotector.

**4. HPO → SNOMED through retired SNOMED codes** (`hpo_snomed_lifted`). 7,566 crosswalk rows have a code retired in
SNOMED CT-AU. 3,526 of them lift through SAME AS or REPLACED BY (up to 3 steps) to 2,115 distinct (HPO, active concept)
pairs. The same-name rule leaves 976, and 864 of those are already in the graph. **112 pairs are new, for 106 HPO
terms, and 70 of those terms have no SNOMED link yet.** The research's ~714 / 385 is the 737 new pairs *before* the
same-name rule. 107 of the 112 pass only through the retired code's own name. Second path: the HPO term's current
active SNOMED atoms in MRCONSO 2026AA (exact, or one SNOMED is-a line). Both paths are UMLS-based: only the lift step
is independent.

| candidates | pass gate | already reached | new | both fire (new) | exact / line | Wilson lower (line) | tier it would earn | sample | first reading |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2,115 | 976 | 864 | 112 | 78 | 43 / 58 | 0.637 | inadmissible | 30 + 20 contradicting | **18 / 30**, 9 wrong, 3 unsure (lower 0.423); contradicting 5 / 20 |

The errors have one cause. The retired code is a duplicate that SNOMED points at a **morphologic abnormality** (10 of the
23 wrong: the disorder with the same meaning exists and is the second path's answer), or it is REPLACED BY a
**narrower** concept (a malignant or subtype form of the phenotype). The same-name rule passes these because it
compares the HPO label with the *retired* code's name.

**5. ChEMBL mechanism drug → UniProt target** (`chembl_moa_target`). `cache/chembl/moa_chembl_raw.json` holds ChEMBL's
answers only for the 1,265 molecules `chembl_moa_witness.py` asked about. Those are drugs whose DrugCentral mechanism
came from another source, so this is not all of ChEMBL. It gives 1,869 (drug, accession) pairs. 1,129 are already
reached through DrugCentral's mechanism rows, so **740 are new** (210 drugs, 23 new UniProt nodes). Second path:
DrugCentral's act_table_full for the drug. Exact is the same accession. Consistent is the same gene symbol, or another
component of the same ChEMBL target.

| candidates | already reached | new | both fire (new) | exact / consistent | Wilson lower | tier it would earn | sample | first reading |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1,869 | 1,129 | 740 | 739 | 144 / 583 | 0.758 | inadmissible | 30 + 156 contradicting | 23 / 30, 6 unsure, 1 wrong (lower 0.591); contradicting 92 correct, 27 wrong, 37 unsure |

**381 of the 740 are ChEMBL expanding a complex or family target of ten or more proteins to every component**: the 38
proteasome subunits, 15 tubulins, 10 sodium-channel α subunits. Nearly every *unsure* reading is a family member the
drug is not shown to act on. The wrong ones include 12 **Ensembl gene ids for siRNA / antisense targets**, which are not
UniProt accessions. They also include *exogenous protein* rows (alteplase → PLAT: the drug *is* the protein) and plain
ChEMBL errors (eptinezumab → integrins).

### What Ken needs to decide

1. **Family 1 by target.** HPO, MeSH and NCIt read 30 / 30, 30 / 30 and 29 / 30 on first reading. If a reviewer
   confirms them, they earn Tier 2 on the hand check. That is 2,464 new pairs. The one NCIt error is two different
   skin conditions joined through a shared eponymous synonym. **OMIM is inadmissible (7 / 30).** Hold it back, or add the PT / ET rule
   and draw a fresh sample.
2. **Family 2: the extract convention.** Is RxNorm's *X extract* the same ingredient as the UNII for *X*? If yes, the
   first reading is 29 / 30 with 1 unsure (lower bound ≥ 0.83) and the family can take Tier 2. If no, add a rule for
   extracts and draw again.
3. **Family 3, MeSH PA:** the second path is confirmation-only, so the tier rests on the hand check (26 / 30, lower
   0.703). It needs about 60 more read to test Tier 2. **ChEBI roles: drop the family.** `chebi:has_role` already
   carries 6,755 of the 7,385 rows. The 630 left are DrugCentral's older copy of ChEBI, and ChEBI 255 disagrees with
   361 of them. Also decide whether uninformative roles (*xenobiotic*, *environmental contaminant*, organism
   metabolites, broad MeSH parents) belong in the graph at all.
4. **Family 4: hold back.** Or lift only through SAME AS to a disorder or finding (never a morphologic abnormality),
   and require the HPO label to match the *active* concept (5 pairs).
5. **Family 5: target policy.** Load only single-protein targets and protein complexes, drop family expansions and
   `exogenous protein` rows, and accept UniProt-pattern accessions only. Then re-draw.

Re-run: `cp -c out/graph.duckdb $TMPDIR/graph.duckdb; .venv/bin/python scripts/wave2_candidates.py --graph $TMPDIR/graph.duckdb`.
A re-run keeps the verdicts already written on a sheet.
