# AMH therapeutic topic index

**Retrieved 2026-09-22** from `https://amhonline.amh.net.au/therapeutics` — *Browse by therapeutic topic* —
using the subscriber account on this machine. **235 topics listed**, which matches the DOM link count
exactly (255 links = 20 chapter links + 235 topic links), so the transcription is complete.

Files:

- [`amh-therapeutic-topics.txt`](amh-therapeutic-topics.txt) — all 235, in AMH's own A–Z order and wording
- [`amh-topics-not-yet-written.txt`](amh-topics-not-yet-written.txt) — the 162 with no guideline here
- [`amh-topic-coverage.json`](amh-topic-coverage.json) — the 40 that map, topic → guideline

## What this list is

**Condition names only.** Nothing from AMH's monograph text is reproduced — the names are facts, and that is
all that has been taken. Every topic also carries an AMH chapter and URL in the live site; the chapter
assignment is recoverable from the same page if needed.

⚠️ **It is 235, not 600–700.** The page states its own limit: *"This is a list of the main therapeutic
topics. The search function can be used to find other conditions included in the AMH."* The 639-item figure
elsewhere in this repo is [`out/conditions.json`](../out/conditions.json), derived from **PBS restriction
text** — a different instrument with a different shape, and not comparable.

**202 distinct after collapsing synonyms.** AMH lists 33 pairs twice, either as an inversion
(*Anaemia, iron deficiency* / *Iron deficiency anaemia*) or as an abbreviation (*BPH*, *COPD*, *GORD*,
*PUD*, *TIA*, *STEMI*, *NSTEACS*, *PMS*, *Impotence*, *Convulsions*).

**No oncology skew.** The entire anticancer chapter contributes a single topic —
*Anticancer drugs, general principles*. AMH indexes by therapeutic management, so the list sits where
everyday prescribing sits: 13 dermatology topics, 13 obstetric/gynaecological, 11 psychotropic,
9 cardiovascular, 9 gastrointestinal.

## Coverage against this compendium

| | Count |
|---|---|
| Distinct AMH topics | **202** |
| With a guideline in this compendium | **40** |
| ⚠️ **With no guideline** | **162** |

The compendium also holds **~35 guidelines with no AMH topic at all** — sepsis, delirium, hip fracture,
emergency laparotomy, stillbirth, colonoscopy, the paediatric set, the STI set beyond the four AMH lists.
Those come from the ACSQHC and ASHM instruments, which index care processes rather than drug therapy.
**The two indexes answer different questions and neither contains the other.**

## Source

| id | citation |
|---|---|
| A1 | Australian Medicines Handbook. *Browse by therapeutic topic.* AMH Medicines, July 2026 release. https://amhonline.amh.net.au/therapeutics (retrieved 2026-09-22, subscriber access) |
