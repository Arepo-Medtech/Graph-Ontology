# SNOMED CT-AU where OMOP cannot see it

*Item 17 of the SPINE backlog, 22 September 2026. `scripts/au_snomed_omop.py`, offline, writes only into
`out/compendium.duckdb`.*

## How invisible the Australian edition is

OMOP's SNOMED vocabulary is the international release with the US and UK editions. There is no Australian one, and
the numbers are absolute rather than approximate:

| | concepts | present in OMOP by code |
|---|---:|---:|
| Australian-authored clinical concepts (procedures, findings, substances, qualifiers, assessment scales, devices) | 6,849 | **6** |
| Australian-authored medicine concepts (AMT, every level) | 165,628 | **0** |

The medicines are not a problem — they live in OMOP's separate `AMT` vocabulary, which
[the indirect bridge](amt-indirect-bridge.md) already handles. The clinical concepts are: an Australian procedure in
a patient record reaches no standard concept, so it disappears from every OMOP query, and the spine's
`binding_omop` can only shrug at it.

## The nearest standard ancestor

The script walks up `is a` from each Australian concept until it meets an ancestor OMOP holds as a **standard**
concept, and records it with the number of hops. The claim is the weaker one the data supports — *this Australian
concept is subsumed by that standard one*, not that they are the same thing — and where a concept has two parents
and neither is more right than the other, both are kept (1,566 concepts).

**5,615 of the 5,938 Australian clinical concepts that need one (94.6 %) reach a standard ancestor.**

| hops to the nearest standard ancestor | concepts |
|---:|---:|
| 1 | 4,002 |
| 2 | 846 |
| 3 | 165 |
| 4 | 476 |
| 5 or more | 126 |

86 % land within two hops, so the ancestor is usually close and still specific: *Parenting skills assessment* →
*Functional assessment*, *Revision of central venous cannula* → *Operation on superior vena cava*, *Dynamic Visual
Acuity Test — Instrumented* → *Visual acuity testing*.

Every clinical tag is fully reached: procedure 2,357 of 2,357, substance 548 of 548, qualifier value 518 of 518,
finding 428 of 428, physical object 409 of 409, assessment scale 146 of 146. The 323 that reach nothing are not
clinical content at all — 211 foundation metadata concepts, 78 administrative concepts, 9 record artifacts.

## How good is a mapping nobody can check?

There is no set of known answers here: six Australian concepts exist in OMOP, which is not a test set. So quality is
measured by the two signals the data does offer — how far the walk went, above, and whether the standard concept's
OMOP **domain** is a sane home for the Australian concept's **semantic tag**:

| | concepts |
|---|---:|
| the domain suits the tag | 7,237 |
| no rule written for that tag | 717 |
| **the domain does not suit the tag** | **98** |

All 98 are substances landing on a Device-domain concept — chlorhexidine digluconate under *biguanide antiseptic
and disinfectant*, amino acid formula under *nutritional supplement*, sorbitan monostearate under *nonionic
surfactant*. The walk is right; OMOP simply files wound-care and nutritional substances in the Device domain. They
are reported rather than hidden so a reviewer can decide whether a Device-domain target is acceptable for their
question.

## Reproduce

```bash
.venv/bin/python scripts/au_snomed_omop.py     # ~2 s
```

```sql
-- what an Australian procedure becomes in an OMOP cohort
SELECT au_name, hops, omop_name, omop_domain
FROM au_omop_ancestor WHERE au_tag = 'procedure' ORDER BY hops DESC, au_name;

-- the concepts whose target domain a reviewer should look at
SELECT au_name, au_tag, omop_name, omop_domain FROM au_omop_ancestor WHERE domain_suits_tag = 'no';
```
