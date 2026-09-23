# Newly diagnosed multiple myeloma — transplant-ineligible patients

**Edition:** 1.0 · 2026-09-23 · **Status:** drafted and source-anchored; awaiting clinical attestation
**Scope:** frailty assessment, induction and maintenance for adults with newly diagnosed myeloma who are not candidates for autologous transplant. Transplant-eligible patients are covered in `myeloma-transplant-eligible`; relapsed disease in `myeloma-relapsed-refractory`. PBS access for each drug is in `docs/no-guideline-pbs-listings.md`.

> ✅ **PARAPHRASED, HASH-ANCHORED.** 16 claims paraphrased from **Medical and Scientific Advisory Group (MSAG) to Myeloma Australia (Sim S, Quach H) — *Clinical practice guideline: Treatment of patients with newly diagnosed multiple myeloma who are ineligible for autologous stem cell transplantation*** (2026 (evidence current to January 2026; due for review after January 2028; file dated March 2026); origin: AU). **29 anchors re-checkable by machine; 2 doses.** The source's words are not reproduced: its licence is *Copyright © 2026 Myeloma Foundation of Australia Inc. All Rights Reserved. (site-wide footer; the PDF itself carries no reuse statement)*.

> ⚠️ **Australia differs from the international standard here, because of PBS funding.** CD38-antibody quadruplets (daratumumab or isatuximab with VRd) now have phase III support, but they are **not PBS-funded**. Dara-Rd, PBS-listed since 2025, is the Australian standard.

---

## Who is transplant-ineligible

- **Transplant-ineligible patients are mostly older (usually over 70) or at higher risk of toxicity from comorbidity and frailty,** so gentler regimens suit them. A fixed age cut-off of 65 is no longer thought appropriate. [S1]
- **Consider 'rainy day' stem-cell collection in patients aged 70 or under who are judged transplant-ineligible,** especially those 65 or under. Renal impairment alone does not rule out a transplant. [S1]
- **Every transplant-ineligible patient should have a frailty assessment at diagnosis,** and MSAG's preferred tool is the IMWG Frailty Index. It sorts patients into three groups (fit, intermediate-fit, frail) and independently predicts adverse events, early drug discontinuation and survival. [S1]
- **Match intensity to frailty:** fit patients get treatment chosen for efficacy; intermediate-fit and frail patients get dose-reduced treatment weighing benefit against toxicity. Offer a clinical trial wherever one is available. [S1]

## Induction

- ⚠️ **Dara-Rd (daratumumab, lenalidomide, dexamethasone) is the standard induction for all transplant-ineligible patients, frail ones included** (Grade A, Level 1A). In MAIA it lengthened PFS (61.9 v 34.4 months) and overall survival compared with Rd. PBAC recommended it and it was on the PBS as of March 2025. [S1]
- **IMWG-fit patients: a CD38-antibody triplet aimed at deep remission** (Grade A, Level 1A). Quadruplets now have supporting evidence in this group but cannot be accessed through the PBS. [S1]
- **Quadruplet caveat:** IMROZ, CEPHEUS and BENEFIT all left out patients aged 80 or more, and 72% of IMROZ patients were non-frail, so how well quadruplets apply to truly frail older people is uncertain. [S1]
- **Intermediate-fit and frail patients: a CD38-antibody triplet, or a doublet built on an IMiD or proteasome inhibitor,** with doses reduced and avoiding toxicity as the priority. [S1]
- **VRd-lite is the other main triplet:** bortezomib is given subcutaneously once a week (1.3mg/m2 on days 1,8,15,22 of a 35-day cycle), to keep patients on treatment and limit neuropathy (Grade B, Level 2A). It has not been compared head-to-head with Rd. VCD with weekly subcutaneous bortezomib is a further option. [S1]
- **Twice-weekly intravenous bortezomib causes a lot of neuropathy:** in SWOG S0777, 80% had some neuropathy and 33% grade 3 or worse, and truly transplant-ineligible patients would fare worse. Prefer subcutaneous over intravenous, and weekly over twice-weekly. [S1]
- **Doublets:** Rd, planning to stop dexamethasone after 9 cycles (Grade A, Level 1A); or, with renal impairment, Vd (Grade B, Level 1B). Frail older patients often do better on a doublet than a triplet, Dara-Rd excepted. [S1]
- **Do not add an alkylating agent to Rd.** In EMN01, melphalan-based and cyclophosphamide-based triplets gave no PFS or survival gain over Rd in intermediate-fit and frail patients. [S1]

## Maintenance

- **After lenalidomide-based induction, continue lenalidomide alone as maintenance:** it is well tolerated and prolongs PFS (Grade A, Level 1A). In the Rd-R study, dropping dexamethasone after 9 cycles of Rd and continuing lenalidomide 10mg on days 1 to 21 of each 28 days matched continuous Rd. [S1]
- **Proteasome-inhibitor maintenance is not PBS-funded.** The benefit of bortezomib maintenance is unclear; ixazomib improves PFS but not overall survival. [S1]
- **Maintenance must never cost the patient unacceptable toxicity or quality of life.** [S1]

## Supportive care

- **Care should be multidisciplinary from the start,** with early allied health input and early palliative care for symptom control where it fits. [S1]

---

## PBS listings (Australian access, schedule 4333)

Derived from PBS Public API data: counts of current restrictions, access type and listed drugs. The restriction criteria themselves are not reproduced (see `docs/no-guideline-action-agenda.md`, Decision 1).

| PBS condition | restrictions | authority / streamlined / restricted | drugs | PBS items |
|---|---:|---|---|---:|
| Multiple myeloma | 42 | 28 / 13 / 1 | Lenalidomide, Pomalidomide, Daratumumab, Carfilzomib, Selinexor, Elranatamab, Thalidomide, Bortezomib +3 | 132 |
| Untreated multiple myeloma | 4 | 4 / 0 / 0 | Daratumumab, Lenalidomide | 22 |

---

## Unresolved

| # | Item | Class |
|---|---|---|
| 1 | **Regimen doses and schedules** (Table 3: Dara-Rd, Rd, VRd-lite, VCD, Vd, Dara-VRd, Isa-VRd) and the **frailty-based starting-dose reductions** (Table 4) are in tables, garbled by PDF extraction, and are not stated here. The lenalidomide start-dose reduction for CrCl ≤60 mL/min is a table footnote. | `input_unavailable` |
| 2 | **The frailty scoring tools** (IMWG-FI, Mayo, simplified frailty scale; Table 2) and the treatment algorithm (Figure 1) are in a table and figure, not anchored. | `input_unavailable` |
| 3 | **Journal version:** Intern Med J 2026 (doi 10.1111/imj.70329) is paywalled; this guideline uses the free myeloma.org.au PDF. | `observation` |
| 4 | **Supportive care** points to Myeloma Australia's separate supportive-care guidelines, not authored here. | `out_of_scope` |
| 5 | **Licence:** site-wide 'All Rights Reserved' footer. The claims are paraphrased and hash-anchored; the source's words are not reproduced. | `observation` |

## Sources

| id | Source | Licence | Treatment |
|---|---|---|---|
| **S1** | Medical and Scientific Advisory Group (MSAG) to Myeloma Australia (Sim S, Quach H). *Clinical practice guideline: Treatment of patients with newly diagnosed multiple myeloma who are ineligible for autologous stem cell transplantation*. 2026 (evidence current to January 2026; due for review after January 2028; file dated March 2026). https://myeloma.org.au/wp-content/uploads/2026/04/Newly-Diagnosed-Transplant-Ineligible-Guidelines-MAR2026.pdf — retrieved 2026-09-23. | Copyright © 2026 Myeloma Foundation of Australia Inc. All Rights Reserved. (site-wide footer; the PDF itself carries no reuse statement) | **paraphrased, hash-anchored** |

⚠️ **`verifier_class: single_verifier_uncalibrated` — written and checked by one model, reviewed by nobody.**
