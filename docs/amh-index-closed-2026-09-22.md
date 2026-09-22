# The AMH therapeutic topic index is covered. What that does and does not mean.

**Date:** 2026-09-22 · **Author:** claude-opus-5

## The claim

**All 235 topics in AMH's therapeutic topic index now map to a guideline in this compendium.**
`reference/amh-topics-not-yet-written.txt` is empty and the audit below returns nothing:

```
235 AMH therapeutic topics; 0 unmapped
```

The last ten were written today: potassium disturbances · hypoglycaemia · snakebite antivenoms · worm
infections · kidney stones · urinary alkalinisation and acidification · infertility · preterm labour ·
lactation suppression and stimulation · immunisation.

## ⚠️ What "covered" does NOT mean

**It does not mean the compendium is usable for prescribing.** Read the counts:

| | |
|---|---|
| **Guidelines** | **145** |
| **Claims** | **6,276** |
| **Quoted, machine re-checkable** | **4,248** |
| **Licensed, paraphrased, NOT re-checkable** | **1,905** |
| **Doses awaiting human attestation** | ⚠️ **621** |
| **Doses quoted from open sources** | **177** |
| **Reviewed by a person** | ⚠️ **0** |

**Every guideline carries `verifier_class: single_verifier_uncalibrated`.** One model wrote them and the
same model checked them. **Nothing has been read by a clinician.**

**621 dose claims cannot be machine-checked at all**, because they come from a licensed source that may
not be reproduced. They are listed in the attestation queue and each must be read against a current AMH
subscription by a person before use.

## ⚠️ Whole topics are covered by a page that gives no dose

The final ten make this unusually stark. **Of the ten, only two give a usable dose:**

- **hypoglycaemia** — glucose volumes for adults *(but no glucagon dose)*
- **urinary alkalinisation** — sachets, capsules, tablets

**The other eight give drug names, thresholds or course lengths and no milligram figure.** Notably:

- **potassium disturbances** — AMH says *"check local protocols to guide dosage"* for calcium, and gives
  no IV potassium rate or concentration limit at all
- **snakebite antivenoms** — no antivenom named, no dose; the page's most actionable content is the
  Poisons Information Centre number, 13 11 26
- **preterm labour** — no dose for any of five drugs, including no magnesium sulfate regimen
- **infertility** — product strengths only, which are not doses
- **immunisation** — no vaccine dose anywhere; the only drug quantity on the page is tetanus
  immunoglobulin 250/500 units

## The largest remaining improvable gap

⚠️ **The Australian Immunisation Handbook is OPEN, at `immunisationhandbook.health.gov.au`, and was not
retrieved.** AMH states its immunisation chapter *draws extensively* from it and defers to it in at least
twelve places, **including for all COVID-19 vaccine recommendations, for which AMH gives none of its
own**. Retrieving it would convert the compendium's largest licensed, unquoted, undosed guideline into a
quoted and dosed one.

Other named authorities behind quoted recommendations that were **not** retrieved: CDNA National
Guidelines (antenatal syphilis schedule) · the SAHMRI magnesium sulfate document · ASHM's national PEP
guidelines · the RACGP preventive activities guideline · the ASID *C. difficile* guidelines
(**closed access** — checked, `is_oa: false`, publisher HTTP 403).

## The audit that should run before any future retrieval

Both of today's earlier errors — a duplicated guideline and an alias miscount — would have been caught by
running these two before writing anything:

```bash
grep -l "<source domain>" guidelines/*.verification.json
```

```bash
python3 - <<'PY'
import json,re
d=json.load(open('reference/amh-topic-coverage.json')); keys={k.strip().lower() for k in d}
for k in list(d):
    for p in re.split(r' = | / ', k): keys.add(p.strip().lower())
t=[l.strip() for l in open('reference/amh-therapeutic-topics.txt') if l.strip()]
print([x for x in t if x.lower() not in keys] or "0 unmapped")
PY
```

**The second one found 15 apparent gaps today that were all alias spellings of covered topics** — for
example *"Hypotension, orthostatic"* against *"Orthostatic hypotension"*, and *"Eclampsia and
pre-eclampsia"* against *"Pre-eclampsia and eclampsia"*. **All 15 have been added to the coverage map so
the audit runs clean.** That is the sixth counting error of this kind in this project, and the reason the
audit is now written down.

## What the next unit of work is

**Not more topics. Attestation.** 621 doses, and 145 guidelines that nobody has read.
