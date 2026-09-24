# Completeness, measured from the source side

*Workstream 1 of the operating plan, 24 Sep 2026; gaps 1 and 2 closed the same day. `scripts/completeness.py`, output `out/completeness.json`, guard
baseline `reference/completeness_baseline.json`.*

Precision — every hand-checked tier in the graph — cannot see an edge that ought to exist and does not. This measures
that. For each group that matters in Australia and each edge its members should carry:

- **present**: the member reaches it through admissible edges (rejected and inadmissible edges are never followed).
  Identity edges are walked both ways, classification edges only forward, and once a walk has classified
  (SNOMED → ICD-10) it may only classify further (→ ICD-11): it never widens back out to the codes' other members.
- **absent**: 50 members per cell, drawn by a seeded hash so every run sees the same ones, each classed:
  - **our gap** — a source we hold states it and the graph does not carry it: SeMRA's aggregated mappings (only the
    ones a source states — its lexical predictions, its own chaining and the 2019 predicted MeSH/ICD set count as
    *predicted*, not stated), a UMLS shared concept (including pairs held back because the names differ), or an edge
    held back by a hand check. The fix is a load or a check.
  - **unknown** — a source that covers the member for this kind of edge says nothing, or declines outright (SNOMED's
    ICD-10 map: *cannot be classified with available data*; Orphanet's own alignments naming no ICD-10 code). Recorded as
    unknown, never as "no relationship".
  - **no source held** — nothing we hold covers it, with the reason: a SNOMED CT-AU extension concept (outside every
    international map), a source still to be obtained (named), or a gap-crossing for a person.
- **not applicable** members are set aside first: a procedure in the ED principal-diagnosis set is outside the ICD maps'
  source domain (findings, disorders, events, situations); dressings and devices among PBS products carry no ATC.

Class counts are scaled from the sample to the cell's absent members; the interval is the Wilson 95% interval of the
*our gap* share of the absent. Nothing here writes an edge.

## The table (graph 1,544,958 nodes / 7,939,796 edges)

| group | expectation | members | present | absent: our gap | unknown | no source held | our gap, share of absent (95%) |
|---|---|---:|---:|---:|---:|---:|---|
| Problem/Diagnosis | ICD-10 (WHO) | 133,021 (+6 n/a) | **84.3%** | 0 | 19,587 | 1,250 | 0–7% |
| Problem/Diagnosis | ICD-11 | 133,021 (+6 n/a) | **84.4%** | 0 | 20,762 | 0 | 0–7% |
| Problem/Diagnosis | ICD-10-CM | 133,021 (+6 n/a) | **93.3%** | 0 | 7,676 | 1,250 | 0–7% |
| Problem/Diagnosis disorders | MONDO | 92,797 | **13.8%** | 0 | 0 | 80,017 | 0–7% |
| Problem/Diagnosis disorders | HPO phenotype | 92,797 | **5.8%** | 0 | 6,990 | 80,389 | 0–7% |
| ED principal diagnosis | ICD-10 (WHO) | 91,551 (+1,620 n/a) | **97.4%** | 0 | 2,227 | 194 | 0–7% |
| ED principal diagnosis | ICD-11 | 91,551 (+1,620 n/a) | **97.4%** | 0 | 2,250 | 144 | 0–7% |
| ED principal diagnosis | CCSR category | 91,551 (+1,620 n/a) | **85.3%** | 0 | 13,465 | 0 | 0–7% |
| PBS-listed products | ATC | 11,244 (+665 n/a) | **98.5%** | 0 | 0 | 171 | 0–7% |
| PBS-listed products | OMOP standard drug (RxNorm / RxNorm Extension) | 11,244 (+665 n/a) | **59.0%** | 0 | 0 | 4,612 | 0–7% |
| PBS medicine ingredients | RxNorm ingredient | 1,502 | **73.4%** | 0 | 0 | 400 | 0–7% |
| PBS medicine ingredients | DrugCentral | 1,502 | **68.2%** | 0 | 0 | 477 | 0–7% |
| PBS medicine ingredients | indication | 1,502 | **64.3%** | 64 | 11 | 461 | 6–24% |
| PBS medicine ingredients | mechanism / target | 1,502 | **61.3%** | 163 | 23 | 396 | 18–42% |
| PBS medicine ingredients | drug-level laboratory test (LOINC) | 1,502 | **30.1%** | 0 | 0 | 1,050 | 0–7% |
| Common laboratory LOINC (top 2,000) | SNOMED CT | 2,000 | **87.6%** | 0 | 0 | 248 | 0–7% |
| Common laboratory LOINC (top 2,000) | AU preferred unit | 2,000 | **17.2%** | 0 | 0 | 1,657 | 0–7% |
| Common laboratory LOINC (top 2,000) | analyte code (ChEBI, RxNorm, gene ...) | 2,000 | **27.8%** | 0 | 0 | 1,444 | 0–7% |
| Common laboratory LOINC (top 2,000) | finding it is interpreted in | 2,000 | **11.1%** | 0 | 0 | 1,778 | 0–7% |
| HPO phenotypes in use | SNOMED CT | 11,560 | **31.7%** | 1,106 | 0 | 6,791 | 7–26% |
| Orphanet disorders | ICD-10 (WHO) | 10,421 | **73.6%** | 934 | 1,814 | 0 | 22–48% |
| Orphanet disorders | ICD-11 | 10,421 | **77.8%** | 0 | 2,312 | 0 | 0–7% |
| Orphanet disorders | OMIM | 10,421 | **48.7%** | 107 | 5,240 | 0 | 0–10% |
| Orphanet disorders | MONDO | 10,421 | **94.2%** | 456 | 0 | 144 | 63–86% |
| Orphanet disorders | SNOMED CT | 10,421 | **70.2%** | 124 | 0 | 2,978 | 1–14% |
| Orphanet disorders | gene | 10,421 | **40.5%** | 0 | 0 | 6,202 | 0–7% |
| Orphanet disorders | HPO phenotype | 10,421 | **41.8%** | 0 | 0 | 6,066 | 0–7% |
| MBS items | SNOMED CT procedure | 6,046 | **0.0%** | 0 | 0 | 6,046 | 0–7% |

## What it says

**Where the gap is ours — a source we hold states the edge.**

1. **HPO phenotype → SNOMED CT — fixed.** The UMLS 2026AA concepts file pairs **4,885** HPO terms with a same-named
   SNOMED CT-AU concept; the graph carried 2,754, from the earlier per-code crosswalk, because the MRCONSO loader left
   the HPO–SNOMED pair to that older route. It now loads them (`umls:shared_cui`, HP-SCT, hand check 29/30, Tier 2):
   phenotypes in use reaching SNOMED **24.3% → 31.7%**.
2. **Orphanet disorder → SNOMED CT — fixed.** Orphanet's own file links a disorder to a UMLS concept, and that concept
   held an active SNOMED CT-AU code for 19 of 21 sampled gaps — but the graph's 29,234 UMLS concept nodes were never
   joined to the codes inside them. `umls:concept_member` now joins each to its SNOMED disorders and findings (12,489
   edges, hand check 30/30, Tier 2; drugs left out, since UMLS files a substance and SNOMED's "Product containing" it
   under one concept): Orphanet disorders reaching SNOMED **51.1% → 70.2%**, and — through the UMLS concepts MONDO
   names — Problem/Diagnosis disorders reaching MONDO 11.3% → 13.8%.
3. **Orphanet disorder → ICD-10 (~900) and → MONDO (~460 of 600 absent).** SeMRA carries MONDO's own cross-references,
   which the graph loads only from MONDO's exact-match file. For MONDO, half the sampled gaps rest on xrefs MONDO
   annotates `equivalentObsolete` — to be read before anything loads.
4. **PBS ingredient → mechanism (~160) and → indication (~60).** Held back by a hand check: MED-RT's uncorroborated
   mechanism and may-treat families. A second witness (as the FDA classes did for mechanism) would lift them.

**Where a source covers the member and says nothing (unknown).** Diagnoses without ICD-10: SNOMED's own map declines
them (19,600 of 20,800 in Problem/Diagnosis). ED diagnoses without a CCSR category: the ICD-10-CM code is a subcategory
whose last character is still to be chosen, which CCSR does not classify. Orphanet disorders without ICD-10, ICD-11 or
OMIM: Orphanet's own alignments name none.

**Where nothing we hold covers it.**

- **SNOMED CT-AU extension concepts**, most of the few diagnoses no map reaches (e.g. *Crush fracture of T11*, *Injury
  due to electric or hybrid battery fire*) and a fifth of the PBS ingredients without RxNorm or DrugCentral: outside every
  international source by construction.
- **Disorders → MONDO (82,000) and → HPO phenotypes (83,000).** MONDO and the HPO annotations cover diseases — largely
  genetic and rare — not injuries, poisonings or common findings. Much of this is out of the sources' scope, which only a
  person can confirm; it is not evidence of absence.
- **Orphanet genes (6,200) and phenotypes (6,100)**: Orphadata product6 and product4, not yet held (workstream 2).
- **Laboratory LOINC**: the AU preferred unit (RCPA's sets cover a subset of analytes), the analyte code, the finding.
  Coverage rules for LOINC are not yet written, so its unknown and no-source cases are not yet told apart.
- **PBS products → OMOP (4,600)**: AMT products Athena has no mapping for (the known post-2021 gap).
- **MBS (6,046)**: no published map anywhere; candidate frames for a person.

## Limits

A 50-member sample gives wide intervals (0–7% when none of 50 is a gap). The coverage rules are stated in the script per
cell and are approximations: Orphanet's disorders include its groupings, which no ICD or OMIM code is expected for; HPO's
silence on a disease is read as unknown only when the disease is in a vocabulary HPO annotates. SeMRA's evidence
includes UMLS-derived mappings. The loader ledger (rows available / loaded / excluded, and why) exists only for the
loaders that already log their exclusions in `build_log`; completing it for every loader is the next step here.

## The guard

`scripts/completeness.py` compares each cell's present share with `reference/completeness_baseline.json` and exits 1
naming any cell that dropped by more than half a percentage point; `--set-baseline` accepts a deliberate change.
