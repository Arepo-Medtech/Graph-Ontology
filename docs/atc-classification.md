# ATC classification — from the PBS listing, and from OMOP for everything else

*Item 14 of the SPINE backlog, 22 September 2026. `scripts/atc_bridge.py`, offline, writes only into
`out/compendium.duckdb`.*

## The gap

The compendium knew the ATC class of a **PBS-listed item** and nothing else: 6,844 item-to-ATC rows from the
schedule, reaching 15,757 AMT concepts once a pack's class is carried down to the units inside it. Everything the
PBS does not list — private, over-the-counter, hospital-only, unlisted brands — had no class at all, so a question
as ordinary as "every ACE inhibitor in the compendium" could only be answered for subsidised products.

## The second route

OMOP's vocabulary carries the whole ATC classification rolled up over RxNorm and RxNorm Extension in
`CONCEPT_ANCESTOR` — 10,229,527 ATC-over-drug rows. A product that reaches a standard drug concept through
`omop_drug` can therefore be classified without the PBS at all. Both routes are written into one table, each row
tagged with its source:

| | products classified |
|---|---:|
| PBS schedule | 15,757 |
| OMOP ancestry | 95,236 |
| **either** | **101,732** |
| only OMOP can classify | 85,975 |

Coverage by level, where a class is meaningful:

| level | with an ATC | of |
|---|---:|---:|
| TPUU (branded unit) | 18,796 | 24,634 |
| TPP / CTPP (packs) | 36,458 / 37,404 | 47,960 / 50,748 |
| MPUU (generic unit) | 5,594 | 16,137 |
| MP | 988 | 9,858 |

Brand concepts (14,683) and MPF (7,537) get none, correctly: neither is a product with ingredients.

## Where both routes speak, do they agree?

9,056 products carry an ATC 5th level from both sources:

| | products |
|---|---:|
| same ATC 5th code | 8,870 (97.9 %) |
| agree only at the 4th level | 48 |
| agree only at the 3rd level | 11 |
| different branch | 127 |

The 127 are not errors in either source. They are substances with more than one legitimate ATC, where the PBS
classifies **the listed product by the indication it is subsidised for** and OMOP classifies **the substance**:

| product | PBS | OMOP |
|---|---|---|
| Buvidal (buprenorphine, modified release injection) | N07BC01 drugs used in opioid dependence | N02AE01 opioid analgesic |
| Flagyl (metronidazole) | J01XD01 antibacterial | P01AB01 antiprotozoal |
| Selsun (selenium sulfide shampoo) | D11AC03 medicated shampoo | D01AE13 topical antifungal |
| Fentora (fentanyl, orally disintegrating) | N02AB03 opioid analgesic | N01AH01 opioid anaesthetic |

Both codes are true of the molecule; they answer different questions. The table keeps both, and a query that needs
one meaning should filter on `source`. See also [ambiguity management](ambiguity-management.md).

## Reproduce

```bash
.venv/bin/python scripts/atc_bridge.py      # ~5 s; needs CONCEPT_ANCESTOR in the installed Athena bundle
```

```sql
-- every ACE inhibitor in the compendium, however it was classified
SELECT DISTINCT p.pt, pa.atc_code, pa.source
FROM product_atc pa JOIN product p ON p.id = pa.product_id
WHERE pa.atc_code LIKE 'C09A%' AND p.level = 'TPUU' ORDER BY p.pt;

-- the products the two sources classify differently
SELECT p.pt, ch.pbs_atc, ch.omop_atc
FROM product_atc_check ch JOIN product p ON p.id = ch.product_id
WHERE NOT ch.same_third ORDER BY p.pt;
```
