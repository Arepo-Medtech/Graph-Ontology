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
| **MBS items → SNOMED procedure** | 3,950 items, 28,914 candidates (first search + a second search inside the category's reference set) — **first reading 24 Sep: 1,649 items with a likely procedure**, 885 more with only a general form; 465 anaesthesia items out of scope | `reference/mbs_procedure_candidates.json`, `reference/mbs_procedure_candidates_malt.json`; reading in `reference/mbs_procedure_first_reading.json`; out of scope in `reference/mbs_out_of_scope.json` | the procedure the item funds — a billing rule is not an equivalence | ✅ sheet `mbs_procedures` (loads as `person:funds_procedure`, not an identity) |
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

  465 anaesthesia items fund anaesthesia time, its initiation or a modifier, not a procedure. They are listed with the
  reason in `reference/mbs_out_of_scope.json` and are kept out of the search and the sheet.
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
