# Consistency: equivalence clusters and their conflicts

*Workstream 3 of the operating plan, 24 Sep 2026: the part that raises precision rather than volume.
`scripts/consistency.py`, output `out/consistency.json` (licensed codes and names: not committed).*

Every edge that claims two codes are the same thing — an exact match, a shared UMLS concept, Orphanet's exact alignment,
a gene's own cross-reference — is followed transitively into **equivalence clusters**. In the vocabularies that are
one-to-one by design (a MONDO disease, an Orphanet entry, an OMIM entry, an HGNC or NCBI gene, an HPO phenotype, a DOID
disease), a cluster holding two codes of one vocabulary says two different things were declared the same: the source has
a duplicate, or an edge on the path between them is wrong. For each such pair the shortest path is traced (up to 20
pairs a cluster, seeded), and the edges on the most paths — the **bridges** — form a precision queue. Gene → protein
(many genes encode one histone), uphill product maps and classifications are not equivalence and are not followed.

## What the first pass found, and what was fixed

| | first pass | now |
|---|---:|---:|
| largest cluster (codes) | 820 | 86 |
| clusters with two MONDO diseases | 1,223 | 1,207 |
| … two OMIM entries | 125 | 90 |
| … two HGNC genes | 66 | 40 |
| … two NCBI genes | 31 | 3 |
| … two HPO phenotypes | 126 | 122 |
| … two DOID diseases | 490 | 481 |
| … two Orphanet entries | 331 | 331 |

1. **HPO's own cross-references are classifications, not equivalences** (`hp:xref`, 221 NCIt links): *Testicular
   teratoma* → *Teratoma*, *Cutaneous melanoma* → *Melanoma*, *Neoplasm of the lung* → *Neoplasm*. Walked as identity
   they chained distinct phenotypes and cancers into one 820-code cluster; the register now files them as classification
   (walked forward only). This alone took the largest cluster to 93.
2. **NCIt fusion genes paired with both partner genes** — *ETV6/PDGFRB Fusion Gene* ↔ OMIM's PDGFRB *and* ETV6
   entries, because OMIM gene entries list fusion names as synonyms. Rule in the UMLS loader: a fusion gene does not pair
   with an OMIM gene entry (268 pairs dropped). NCBI-gene conflicts 31 → 3.
3. **OMIM susceptibility entries list the phenotypes they predispose to as synonyms** (*Multiple system atrophy 1,
   susceptibility to* → *Orthostatic hypotension*). Rule: such an entry pairs only with a concept that is itself a
   susceptibility (16 pairs dropped).
4. **Obsolete MONDO classes still carried exact matches** (1,790 classes, 2,170 rows of MONDO's SSSOM file). Only active
   classes load now. This lowered *Orphanet → MONDO* completeness from 97.0% to 93.5%: that reach had come through
   retired classes, and those entries are now *unknown* (MONDO's only link to them is on an obsolete class).
5. **60 bridges hand-checked** (`cache/consistency/bridge_handcheck.json`): the 30 on the most conflict paths (12
   correct — UMLS same-name 2/13, UMLS concept membership 0/3, Orphanet exact 3/6, MONDO exact 7/8) and 30 at random
   among UMLS-derived bridges (22 correct). The 26 wrong are rejected by name — *Glioma susceptibility 1* ↔
   *Glioblastoma*, *Aortic valve disease 1/2* ↔ *Bicuspid aortic valve*, *AL amyloidosis* ↔ *Multiple myeloma*, an
   annexin pseudogene ↔ the gene, a pre-eclampsia locus ↔ pregnancy-induced hypertension — which took the largest
   cluster from 93 to 86.

## What the 30 sampled MONDO conflicts are

About 12 are UMLS lumping a specific entry with the general one (an OMIM numbered type with the disease, a subtype with
its parent); 6 are MONDO holding two classes for one disease (typically one built from OMIM and one from Orphanet —
*olfactory neuroblastoma* / *esthesioneuroblastoma*); 6 are MONDO's own looser mappings; 3 are Orphanet "exact"
alignments that are broader or narrower; 2 were obsolete MONDO classes (now fixed). The MONDO duplicates are MONDO's to
resolve; the rest are the precision queue.

## Next

**Bridge position predicts error.** Among random UMLS bridges, those on one conflict path were right 13 of 13, those on
two or more 9 of 17. With a full 30-edge sample of the second group, "a UMLS pair on two or more conflict paths" can be
tiered as its own family and, if it fails, held back (about 1,460 UMLS edges are bridges today). Then the chain rules
(exact ∘ exact, exact ∘ narrower) with their own hand checks.
