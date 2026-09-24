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
    *predicted*, not stated; a row from an older release of MONDO, Orphanet or HPO that the current release we hold no
    longer states counts as *superseded*, which is unknown), a UMLS shared concept (including pairs held back because the names differ), or an edge
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

## The table (graph 1,545,027 nodes / 8,064,578 edges)

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
| PBS medicine ingredients | indication | 1,502 | **64.5%** | 64 | 11 | 459 | 6–24% |
| PBS medicine ingredients | mechanism / target | 1,502 | **61.4%** | 151 | 23 | 406 | 16–40% |
| PBS medicine ingredients | drug-level laboratory test (LOINC) | 1,502 | **30.1%** | 0 | 0 | 1,050 | 0–7% |
| Common laboratory LOINC (top 2,000) | SNOMED CT | 2,000 | **87.6%** | 0 | 248 | 0 | 0–7% |
| Common laboratory LOINC (top 2,000) | AU preferred unit | 1,162 (+838 n/a) | **28.4%** | 0 | 0 | 832 | 0–7% |
| Common laboratory LOINC (top 2,000) | analyte code (ChEBI, RxNorm, gene ...) | 2,000 | **27.8%** | 0 | 1,444 | 0 | 0–7% |
| Common laboratory LOINC (top 2,000) | finding it is interpreted in | 2,000 | **11.1%** | 0 | 1,422 | 356 | 0–7% |
| HPO phenotypes in use | SNOMED CT | 11,560 | **31.7%** | 1,106 | 0 | 6,791 | 7–26% |
| Orphanet disorders | ICD-10 (WHO) | 9,886 (+535 n/a) | **77.1%** | 91 | 2,174 | 0 | 1–14% |
| Orphanet disorders | ICD-11 | 9,886 (+535 n/a) | **80.9%** | 0 | 1,888 | 0 | 0–7% |
| Orphanet disorders | OMIM | 9,886 (+535 n/a) | **50.4%** | 196 | 4,708 | 0 | 1–14% |
| Orphanet disorders | MONDO | 9,886 (+535 n/a) | **97.0%** | 0 | 18 | 276 | 0–7% |
| Orphanet disorders | SNOMED CT | 9,886 (+535 n/a) | **71.4%** | 113 | 0 | 2,718 | 1–14% |
| Orphanet disorders (disorder or subtype level) | ICD-10 (WHO) | 7,751 (+372 n/a) | **96.7%** | 0 | 258 | 0 | 0–7% |
| Orphanet disorders | gene | 9,886 (+535 n/a) | **42.9%** | 0 | 5,643 | 0 | 0–7% |
| Orphanet disorders | HPO phenotype | 9,886 (+535 n/a) | **44.0%** | 0 | 5,531 | 0 | 0–7% |
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
3. **Orphanet disorder → ICD-10 — mostly not a gap.** The ~900 first counted came from SeMRA's copies of *older* MONDO
   and Orphanet releases: MONDO has since retired all but 209 of its ICD-10 cross-references, and Orphanet's current
   file dropped others. The measure now marks such rows **superseded** (the current release we hold covers the disorder
   and no longer states it: unknown, not our gap). Most of the rest are Orphanet *groups*, which Orphanet deliberately
   leaves without an ICD-10 code, and entries Orphanet has **retired** (deprecated, or non-rare in Europe), which it
   strips of codes. A chain rule carries SNOMED International's classification to the active disorders and subtypes
   left: `orpha:icd10_via_snomed` — *correction to PR #39*: of the 63 disorders it first reached, all but 5 were
   retired entries; restricted to active ones it is 5 pairs, all right, and too small a family to tier (ungraded).
   **96.7%** of Orphanet's active disorder- and subtype-level entries reach ICD-10.
4. **Orphanet disorder → MONDO — not a gap.** Of the sampled "gaps", a third were entries Orphanet has retired — MONDO's
   `equivalentObsolete` cross-references (705 of 706 point at retired Orphanet entries) say exactly that — and the rest
   already reach MONDO in two exact steps (Orphanet ≡ OMIM entry ≡ MONDO disease) that the measure did not follow.
   Retired Orphanet entries are now *not applicable* (535), and Orphanet's narrower / broader alignments end a walk
   unless they classify to an ICD code. Active Orphanet entries reaching MONDO: 97.0%, no held gap left — then **93.5%** once obsolete MONDO classes stopped counting (docs/consistency.md): the rest are MONDO's links on retired classes, now unknown.
5. **PBS ingredient → mechanism and → indication — witnesses added.** MED-RT's held-back families now have a second
   witness where DrugCentral agrees: *may treat* corroborated by DrugCentral's label indications (3,176 edges, 34/34,
   Tier 2) and *mechanism of action* corroborated by DrugCentral's MeSH pharmacological actions (249 edges, 33/34,
   Tier 2). The uncorroborated remainder stays inadmissible (23/30 each, after topping the samples back up to 30). For
   PBS ingredients the lift is small (indication 64.3% → 64.5%, mechanism 61.3% → 61.4%): DrugCentral mostly does not
   cover the drugs whose MED-RT edges are held. Physiologic effect and may-prevent have no independent witness yet.

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
- **Orphanet genes and phenotypes — now held, and the silence is Orphanet's.** Orphadata products 6 and 4 are loaded
  (24 Sep). HPO had relayed nearly all of it (99.7% of phenotype pairs, 99.4% of gene pairs), so coverage barely moves
  (genes 42.7% → 42.9%), but every disorder without a gene or phenotype is now *unknown — Orphanet's own file states
  none*, where before it was *no source held*.
- **Laboratory LOINC — the silence is the sources', not ours (coverage rules, 24 Sep).** Every LOINC cell now says which
  held source *states* the link (absent from the graph: our gap) and which *covers* the term without stating it (unknown):

  | cell | states (→ our gap) | covers, says nothing (→ unknown) | neither (→ no source) |
  |---|---|---|---|
  | → SNOMED CT | LOINC Extension identifier; Athena *Is a* / *Maps to* SNOMED | LOINC maps only the component part to SNOMED; Athena holds the term under no SNOMED concept | in neither Athena nor the Extension |
  | → AU preferred unit (quantitative terms only, `SCALE_TYP = Qn`) | RCPA SPIA states a unit | RCPA lists the term with no unit | not in the RCPA reporting sets |
  | → analyte code | LOINC's part mapping gives the component an analyte code | LOINC decomposes the term; its component carries no code | LOINC links no component |
  | → finding interpreted in | — (a derived rule) | the LOINC Extension models the term; no SNOMED finding interprets it at this specimen | not in the Extension, the rule's input |
  | PBS ingredient → drug-level test | LOINC's part mapping names the substance | — | no LOINC part names it by the codes it reaches |

  The rules read the releases themselves, not the graph, so a loader that drops rows a source states would show as our
  gap. None does: every LOINC cell has 0 of 50 our-gap. The 248 terms without SNOMED are all Athena-held and
  Extension-absent (surgical pathology studies, ova and parasites); the unit cell is now measured on the 1,162
  quantitative terms (a presence or ordinal test has no unit to find), and its 832 absent are not in RCPA's sets.
- **PBS products → OMOP (4,600)**: AMT products Athena has no mapping for (the known post-2021 gap).
- **MBS (6,046)**: no published map anywhere; candidate frames for a person.

## Limits

A 50-member sample gives wide intervals (0–7% when none of 50 is a gap). The coverage rules are stated in the script per
cell and are approximations: Orphanet's disorders include its groupings, which no ICD or OMIM code is expected for; HPO's
silence on a disease is read as unknown only when the disease is in a vocabulary HPO annotates. SeMRA's evidence
includes UMLS-derived mappings. The loader ledger (`out/loader_ledger.json`, docs/multigraph-build.md → *The loader
ledger*) says, for every one of the 84 loaders, how many source rows it saw and where each one not loaded went.

## The guard

`scripts/completeness.py` compares each cell's present share with `reference/completeness_baseline.json` and exits 1
naming any cell that dropped by more than half a percentage point; `--set-baseline` accepts a deliberate change.
