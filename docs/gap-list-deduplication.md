# The gap list was counting aliases, not topics

**2026-09-22.** `reference/amh-topics-not-yet-written.txt` is the file
`scripts/corpus_stats.py` counts to produce the "AMH gap" number in every commit
message. Until today it held **one line per LABEL**. AMH's own *Browse by
therapeutic topic* index lists many topics **twice, under different labels,
pointing at a single page** — *Hyperkalaemia*, *Hypokalaemia* and *Potassium
disturbances* are all `.../potassium-disturbances`; *Immunisation* and
*Vaccination* are one page; *Mania* is *Bipolar disorder*.

⚠️ **So the gap number has been overstated for the whole march.** At the moment
of correction the file held **35 labels** covering **25 distinct pages**.

It also held **one stale entry**. *Otitis externa* points at
`.../drugs-ear-infections/otitis-externa`, which the `otitis-externa-and-ear-wax`
guideline closed under AMH's other label for the same page, *Ear infection
(external)*. It had been sitting on the gap list since, counted as outstanding
work that was already done.

## What changed

- The file now holds **one line per PAGE**, with AMH's alias labels joined by
  ` / ` on that line, so the count `corpus_stats.py` prints is a count of pages.
- `reference/amh-gap-topic-urls.json` records the label → page mapping, read off
  AMH's index on 2026-09-22, so this can be re-derived rather than re-judged.
- *Otitis externa* removed as already closed.

## What this does NOT change

**No guideline changed. No claim changed. No count of claims, passes or queued
doses changed.** The corpus is the same size it was; the statement about *how
much AMH remains* was wrong, and is now right.

⚠️ **Earlier commit messages in this repository contain the inflated figure.**
They are not being rewritten — the history says what it said. This document is
the correction.
