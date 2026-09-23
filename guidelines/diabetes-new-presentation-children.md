# New presentation of diabetes mellitus in children (not in DKA)

**Edition:** 1.0 · 2026-09-23 · **Status:** drafted and source-verified; awaiting clinical attestation
**Scope:** diagnosis, work-up and subcutaneous insulin initiation for children newly diagnosed with diabetes who are **not** in DKA. A child in DKA goes to `diabetic-ketoacidosis-children`; the adult counterpart for type 2 disease is `type-2-diabetes` (non-pregnant adults). Sick days at home: `diabetes-sick-day-management-children`.

> ✅ **OPEN AND QUOTED.** 20 of 20 claims quoted verbatim from the **RCH Melbourne Clinical Practice Guideline *Diabetes Mellitus: new presentation*** (Last updated July 2025); **32 fragments re-checked by machine. 7 quoted doses.**

> ⚠️ **Check the venous gas first: pH under 7.3 or bicarbonate under 18 mmol/L is DKA** — use `diabetic-ketoacidosis-children`, not this page.

---

## Recognise and diagnose

- **Check a BGL in most acutely unwell children** — diabetes can present non-specifically. [S1]
- **Diagnostic: random BGL 11.1 mmol/L or more, or fasting BGL 7.0 mmol/L or more, together with symptoms of hyperglycaemia.** [S1]
- **Classic symptoms:** polydipsia, polyuria, new nocturnal enuresis in a previously dry child, unexplained weight loss or fatigue. Vomiting, respiratory distress, dehydration, abdominal pain or altered consciousness may indicate ketosis/ketoacidosis. [S1]
- **Do not diagnose on a single BGL without symptoms**; if in doubt, HbA1c, OGTT or continued BGL monitoring with a paediatric specialist. [S1]
- **Most childhood diabetes is type 1.** If autoantibodies are negative, consider **type 2** (obesity, acanthosis nigricans, strong family history) or **monogenic** diabetes (presentation under 6 months, or autosomal dominant family history). [S1]

## Investigate

- **Formal serum glucose; point-of-care blood ketones if random BGL is 11.1 mmol/L or more** (urine ketones if blood ketones are unavailable); venous blood gas. [S1]
- ⚠️ **pH under 7.3 or bicarbonate under 18 mmol/L: manage as DKA.** [S1]
- **Also send:** UEC, diabetes autoantibodies (anti-GAD, IAA, anti-IA2, ZnT8), coeliac serology, TSH and FT4. [S1]

## Start subcutaneous insulin

- **A child not in DKA can be managed with subcutaneous insulin.** ⚠️ **If ketones are 0.6 or more, start insulin as soon as possible to prevent DKA.** [S1]
- **Initial total daily dose (TDD):** under 1 year — consult a paediatric endocrinologist · 1–5 years 0.5 units/kg/day · 5–10 years 0.7 units/kg/day · over 10 years 0.7–1.0 units/kg/day. [S1]
- **MDI (basal-bolus): 40% of TDD as long-acting insulin in the evening; the other 60% as rapid-acting split across breakfast, lunch and dinner** (~0.1–0.2 units/kg before each main meal). [S1]
- **First rapid-acting dose more than 2 hours before a meal: consider a stat 0.2 units/kg.** Daytime presenters may need slightly higher pre-meal doses (e.g. 0.25 units/kg) until the evening basal dose. **Round doses down to the nearest 0.5 unit.** [S1]
- **Pre-meal target 4–8 mmol/L.** Above 8, use the correction factor to bring BGL back to 6 mmol/L, unless insulin was given in the preceding 2 hours. **Give pre-meal rapid-acting insulin 15 minutes before the meal** (Fiasp at the time of the meal). [S1]
- **Flexible dosing: rapid-acting dose = (BGL − 6) ÷ correction factor, plus carbohydrate grams ÷ insulin:carbohydrate ratio.** Also give with snacks over 15 g carbohydrate. [S1]
- **Worked example:** pre-lunch BGL 16, eating 20 g carbohydrate, CF 2, ICR 5 → (16 − 6) = 10 ÷ 2 = 5 units, plus 20 ÷ 5 = 4 units → **9 units**. Not eating or under 15 g carbohydrate: correction only. BGL 4–8 with food: carbohydrate dose only. [S1]
- **Twice-daily injections are rarely used** as a standard regimen. Individualise doses and discuss ongoing dosing with a paediatric endocrinologist or experienced paediatrician. [S1]

## Monitor

- **MDI finger-prick BGLs:** pre-meals, 2 am during initial stabilisation, and whenever hypoglycaemia is suspected; more often initially (e.g. 2 hours after the first dose and 4-hourly overnight), especially if ketotic. [S1]
- **Ketones present at diagnosis: measure with each BGL every 2 hours until under 0.6.** Thereafter check ketones whenever BGL is 15 or more or the child is unwell. [S1]

## Admission and discharge

- **Discuss every new presentation with the local paediatric team; most are admitted** for insulin initiation and education. HITH/ambulatory programs only after discussion with paediatric endocrinology. [S1]
- **Discharge when** tolerating oral intake, linked with the local diabetes team, initial education done, and the family is competent with BGL monitoring, insulin and hypoglycaemia treatment. [S1]

---

## Unresolved

| # | Item | Class |
|---|---|---|
| 1 | **Weight-banded initial ICR, correction factor and long-acting doses (Appendices 1 and 2)** were not quoted: each flattens to a long run of bare numbers across 4–7 columns, too easy to misalign in a verbatim quote. | `input_unavailable` |
| 2 | ⚠️ **The two appendices disagree on the long-acting starting dose** at the same weight — e.g. at 10 kg Appendix 1 gives 2 units and Appendix 2 gives 2.5; at around 60 kg Appendix 1 gives 18–24 units and Appendix 2 (56–60 kg) gives 14. RCH offers no reconciliation. | `observation` |
| 3 | **The page says some centres use different management guidelines**; the regimen here is RCH's. | `observation` |
| 4 | **Type 2 diabetes in children** is only flagged here (autoantibody-negative, obesity, acanthosis); `type-2-diabetes` covers adults only, so paediatric type 2 management is not in this corpus. | `out_of_scope` |
| 5 | **Licence:** RCH guidelines are free to read but **© The Royal Children's Hospital**, not openly licensed; quoted with attribution. | `observation` |

## Sources

| id | Source | Treatment |
|---|---|---|
| **S1** | The Royal Children's Hospital Melbourne. *Clinical Practice Guidelines: Diabetes Mellitus: new presentation*. Last updated July 2025. https://www.rch.org.au/clinicalguide/guideline_index/Diabetes_Mellitus__new_presentation/ — retrieved 2026-09-23. | **quoted, re-checkable** |

⚠️ **`verifier_class: single_verifier_uncalibrated` — written and checked by one model, reviewed by nobody.**
