# Review queues: what waits for a person

*24 Sep 2026. Every item below crossed a gap by name, or failed a hand check as a family, so the graph holds it as a
candidate and never as an edge. Each queue says where it lives, what a reviewer decides, and whether the build can take
a decision in yet.*

| queue | size | file | the decision | intake today |
|---|---:|---|---|---|
| **Corpus conditions** not bound to SNOMED | 374 (14 newly exact-bound) | `reference/corpus_condition_candidates.json` | bind to one of the candidates, or none | ✅ `binding_review.py --harvest` → `binding_corrections.json` → `apply_corrections.py` (docs/binding-review-loop.md) |
| **PBS indication texts** not bound | 341 (295 with candidates) | `reference/pbs_indication_bindings.json` (`results`) | the SNOMED condition the listing means | ✅ sheet `pbs_indications` |
| **Likelihood ratios**: bound, family held | 130 | `reference/diagnostic_accuracy_bindings.json` | confirm the test / score / prognosis binding | ✅ automatic: the family loads once its binding earns Tier 2 (right 65 of 79 now; needs a lower bound ≥ 0.80) |
| **Likelihood ratios**: not bound exactly | 455 | same | bind the finding or test to a SNOMED concept | ⚠️ edit the bindings file, re-run `verify_diagnostic_accuracy.py` |
| **HPO → SNOMED**, names differ | 2,073 phenotypes (2,434 pairs; the rest now reached by the 2026AA same-name load) | `cache/umls/hpo_snomed_candidates.tsv` *(UMLS-derived, not committed)* | same phenotype or not (a sample was right 34 of 40; errors are narrowings) | ✅ sheet `hpo_snomed` |
| **SNOMED organism ↔ NCBI taxon**, names differ | 3,889 | `cache/umls/sct_ncbi_candidates.tsv` *(UMLS-derived)* | same organism (most are reclassifications: *Clostridium lavalense* → *Enterocloster lavalensis*) | ✅ sheet `organism_ncbi` |
| **RadLex anatomy** with no code route | 99 terms, 180 pairs | `cache/radlex/radlex_sct_candidates.tsv` *(RadLex labels, not committed)* | the SNOMED body structure for head, neck, hand, foot … | ✅ sheet `radlex_anatomy` |
| **MBS items → SNOMED procedure** | 3,878 items with candidates (572 exact head-phrase) | `reference/mbs_procedure_candidates.json` | the procedure the item funds — a billing rule is not an equivalence | ✅ sheet `mbs_procedures` (loads as `person:funds_procedure`, not an identity) |
| **Survey instruments** | 55 pairs, 53 LOINC panels | `reference/survey_instrument_candidates.json` | same instrument (a first reading is on each pair: 40 likely same) | ✅ sheet `survey_instruments` |

**Where a person's time buys most.** The survey list is short and pre-read — an hour closes the PHQ, GAD, AUDIT, EPDS, MMSE
family. The 130 held LR bindings need only enough confirmations to lift the family's lower bound past 0.80. MBS is the one
true island in the graph (`graph_report.py` → islands): confirming even a few hundred procedures joins its 6,046 items.

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
they stay in `out/review/` (git-ignored). The corpus-condition queue keeps its own loop (above); the likelihood-ratio
bindings load as a family once their binding earns its tier.
