# Review queues: what waits for a person

*24 Sep 2026. Every item below crossed a gap by name, or failed a hand check as a family, so the graph holds it as a
candidate and never as an edge. Each queue says where it lives, what a reviewer decides, and whether the build can take
a decision in yet.*

| queue | size | file | the decision | intake today |
|---|---:|---|---|---|
| **Corpus conditions** not bound to SNOMED | 374 (14 newly exact-bound) | `reference/corpus_condition_candidates.json` | bind to one of the candidates, or none | ✅ `binding_review.py --harvest` → `binding_corrections.json` → `apply_corrections.py` (docs/binding-review-loop.md) |
| **PBS indication texts** not bound | 341 | `reference/pbs_indication_bindings.json` (`results`) | the SNOMED condition the listing means | ⚠️ none yet — a corrections file like the corpus one is the natural shape |
| **Likelihood ratios**: bound, family held | 130 | `reference/diagnostic_accuracy_bindings.json` | confirm the test / score / prognosis binding | ✅ automatic: the family loads once its binding earns Tier 2 (right 65 of 79 now; needs a lower bound ≥ 0.80) |
| **Likelihood ratios**: not bound exactly | 455 | same | bind the finding or test to a SNOMED concept | ⚠️ edit the bindings file, re-run `verify_diagnostic_accuracy.py` |
| **HPO → SNOMED**, names differ | 4,532 | `cache/umls/hpo_snomed_candidates.tsv` *(UMLS-derived, not committed)* | same phenotype or not (a sample was right 34 of 40; errors are narrowings) | ⚠️ none yet |
| **SNOMED organism ↔ NCBI taxon**, names differ | 3,956 | `cache/umls/sct_ncbi_candidates.tsv` *(UMLS-derived)* | same organism (most are reclassifications: *Clostridium lavalense* → *Enterocloster lavalensis*) | ⚠️ none yet |
| **RadLex anatomy** with no code route | 100 terms, 180 pairs | `cache/radlex/radlex_sct_candidates.tsv` *(RadLex labels, not committed)* | the SNOMED body structure for head, neck, hand, foot … | ⚠️ none yet |
| **MBS items → SNOMED procedure** | 3,878 items with candidates (572 exact head-phrase) | `reference/mbs_procedure_candidates.json` | the procedure the item funds — a billing rule is not an equivalence | ⚠️ none yet; RACS MALT (the surgical audit set, 0.3% bridged) is the natural target |
| **Survey instruments** | 55 pairs, 37 instruments | `reference/survey_instrument_candidates.json` | same instrument (a first reading is on each pair: 40 likely same) | ⚠️ none yet |

**Where a person's time buys most.** The survey list is short and pre-read — an hour closes the PHQ, GAD, AUDIT, EPDS, MMSE
family. The 130 held LR bindings need only enough confirmations to lift the family's lower bound past 0.80. MBS is the one
true island in the graph (`graph_report.py` → islands): confirming even a few hundred procedures joins its 6,046 items.

**An intake the queues without one could share:** one `reference/candidate_decisions.json` — rows of
`{queue, subject, object, decision: accept | reject, reviewer, date}` — that `build_edges.py` loads as edges with method
`confirmed by a person`, tier from the confirmations themselves. Not built: it needs a reviewer first.
