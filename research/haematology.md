# Source research: Haematological malignancy and Haematology

**Scope.** The scope is the `kind: "gap"` rows of `amc/reference/no_guideline_triage.json`: 35 Haematological malignancy rows and 14 Haematology rows. The brief said 15 Haematology rows, but the file changed during the session (mtime 16:50). "A patient identifying as Aboriginal or Torres Strait Islander" is now `kind: "admin"`, so it is out of scope. CARPA still covers it if it is ever reinstated.

**Method.** I fetched every licence quote, date and URL in `haematology.json` this session. International sources carry `"origin": "international"`, as the coordinator requested. The signed-in Consensus tool (`country: "au"`) was used for myeloma, CML, PNH, aHUS and ALL. It then reported its monthly quota exhausted ("-5 searches left this month"). The remaining clusters were searched with Europe PMC and PubMed E-utilities and checked on PMC article pages. Wiley, T&F and Elsevier article pages returned 403. For those articles the copyright line comes from the PubMed record, which is marked in each entry.

**Usability weights** used for ranking:

| Licence class | Weight |
|---|---|
| `open` | 3 |
| `quote_with_attribution` | 3 |
| `non_commercial` | 2 (flagged: the project may be commercial) |
| `limited` | 1 |
| `paraphrase_only`, `login_required`, `unknown` | 0 |

Score = number of conditions covered × weight. Australian sources rank first.

## 1. Sources ranked

| Origin | Source | Publisher | Date | Licence | Conds | Score |
|---|---|---|---|---|---|---|
| AU | eviQ haematology protocols (regimen-level) | Cancer Institute NSW | per protocol, versioned | non_commercial (CC BY-NC 4.0) | 28 | 56 |
| AU | Optimal care pathways, haematology set (11 OCPs; pathways, not drug guidance) | Leukaemia Foundation / DoH, hosted by Cancer Council | Jun 2021 to Jul 2024 | limited | 27 | 27 |
| AU | **Australian treatment guidelines for adults with AML v1.0** | Blood Cancer Taskforce / Leukaemia Foundation / HSANZ | Feb 2025 | quote_with_attribution | 3 | 9 |
| AU | **MSAG clinical practice guidelines** (RRMM, transplant-eligible, transplant-ineligible, bone disease v3) | MSAG / Myeloma Australia | 2026 | quote_with_attribution | 2 | 6 |
| AU | Services Australia PBS authority pages, PNH and aHUS (**administrative only**) | Services Australia | Dec 2025 / Apr 2026 | open (CC BY 4.0) | 2 | 6 |
| AU | Australasian CLL consensus statement: 2026 update (IMJ) | ALA / ALLG / HSANZ | Jul 2026 | non_commercial | 2 | 4 |
| AU | ANZ consensus: cardiovascular management of CLL on BTKi (IMJ) | IMJ, via HSANZ | Jul 2025 | non_commercial (ND) | 2 | 4 |
| AU | ALLG frailty assessment in older AML patients (IMJ) | ALLG | May 2025 | non_commercial (ND) | 2 | 4 |
| AU | MSAG transplant-eligible myeloma (IMJ version) | MSAG | Aug 2025 | non_commercial | 2 | 4 |
| AU | NHFA/CSANZ ACS guideline 2025 | Heart Foundation / CSANZ | Apr 2025 | non_commercial (ND) | 2 | 4 |
| AU | CARPA Standard Treatment Manual, 8th edn | CAAC / CARPA / CRANAplus / Flinders | 2022, reprinted 2026 | non_commercial | 2 | 4 |
| AU | MSAG Waldenström macroglobulinaemia guideline | MSAG | Jun 2022 | quote_with_attribution | 1 | 3 |
| AU | eviQ neutropenic fever resource (ID 123 v7) | Cancer Institute NSW | 11 Jul 2026 | non_commercial | 1 | 2 |
| AU | NHFA/CSANZ AF guideline 2018 ⚠ >5 y | Heart Foundation / CSANZ | 2018 | non_commercial (ND) | 1 | 2 |
| AU | THANZ VTE guideline ⚠ >5 y | THANZ | 2019 | limited (reproduction prohibited) | 1 | 1 |
| AU | ALA lymphoma statements: DLBCL, HL, PTCL (2021 ⚠); FL, MCL, MZL (2024) | ALA (IMJ) | 2021 to 2024 | login_required (© RACP) | 12 | 0 |
| AU | MSAG transplant-ineligible (IMJ 2026); MSAG infection prevention (IMJ 2023) | MSAG (IMJ) | 2026 / 2023 | login_required | 2 | 0 |
| AU | MSAG myeloma bone disease (Expert Rev Hematol) | MSAG | 2025/26 | unknown | 2 | 0 |
| AU | ANZ TMA consensus (Fox et al.) ⚠ >5 y | Nephrology / IMJ | 2018 | login_required | 1 | 0 |
| AU | NBA Ig Criteria v3; PBM Module 3 (archived 2012); AHCDO haemophilia; ANZSBT | NBA / AHCDO / ANZSBT | various | unknown or quote_with_attribution | 0 | 0 |
| intl | EHA endorsement of ESMO follicular lymphoma CPG ⚠ ESMO CPG 2020 | EHA / ESMO | 2021 | non_commercial (ND) | 4 | 8 |
| intl | German ONKOPEDIA myelofibrosis guideline 2025 | DGHO | Jun 2026 | **open (CC BY)** | 2 | 6 |
| intl | French eosinophilia / hypereosinophilic syndrome guidelines | French reference centre | 2023 | **open (CC BY)** | 2 | 6 |
| intl | ASH 2026 ALL guidelines, frontline AYA/adult and relapsed/refractory | ASH | Jul 2026 | non_commercial (ND) | 2 | 4 |
| intl | EHA Hodgkin lymphoma CPG | EHA | Jun 2026 | non_commercial (ND) | 2 | 4 |
| intl | **ELN 2025 CML recommendations** | European LeukemiaNet | Jul 2025 | **open (CC BY)** | 1 | 3 |
| intl | EHA endorsement of ESMO MDS CPG (CC BY covers the endorsement only) ⚠ 2021 | EHA / ESMO | 2022 | open | 1 | 3 |
| intl | ELN APL recommendations ⚠ 2019 | ELN (Blood) | 2019 | quote_with_attribution | 1 | 3 |
| intl | French non-advanced mastocytosis guideline (poor fit for aggressive SM) | CEREMAST | 2025 | open | 1 | 3 |
| intl | EHA large B-cell lymphoma CPG | EHA | Sep 2025 | non_commercial (ND) | 1 | 2 |
| intl | EHA-EU MCL network guideline | EHA | Oct 2025 | non_commercial (ND) | 1 | 2 |
| intl | Asia-Pacific aHUS-with-triggers algorithms | Nephrology (APSN) | Sep 2025 | non_commercial | 1 | 2 |
| intl | NCCN (all haematology panels) | NCCN | versioned | paraphrase_only | 11 | 0 |
| intl | EORTC MF/Sézary 2023; ASCO G-CSF 2015 ⚠; ELN AML 2022; EHA-EMN myeloma 2025; BSH CLL 2025; NICE NG239 (B12, paraphrase_only); KDIGO aHUS 2017 ⚠; Taiwan PNH 2025 (lead only); ASH VTE 2020 ⚠; BSH hairy cell 2020 ⚠; ESC AF 2024 (lead only) | various | 2015 to 2025 | unknown, login_required or paraphrase_only | 1 to 4 | 0 |

## 2. Conditions with no usable Australian source

A source counts as usable here if it is `open` or `quote_with_attribution` and is actual clinical guidance. By that test, only these rows have a usable Australian source:

- **Multiple myeloma** and **Untreated multiple myeloma**: MSAG 2026.
- **Acute Myeloid Leukaemia**, **Acute myelogenous leukaemia** and **Acute promyelocytic leukaemia**: HSANZ/LF AML guideline 2025.
- **Waldenstrom macroglobulinaemia**: MSAG 2022.

**Tier A: no Australian source at all.**

| Condition | Restrictions | International option |
|---|---|---|
| Chronic Myelomonocytic Leukaemia | 4 | Only NCCN (paraphrase_only). No major EU guideline found. |
| Chronic stable atherosclerotic disease (rivaroxaban) | 3 | None verified. The ESC chronic coronary syndromes guideline was not checked. The Australian ACS 2025 guideline has no rivaroxaban content. |
| Aggressive systemic mastocytosis with eosinophilia | 2 | NCCN (paraphrase_only). The French 2025 guideline (CC BY) covers only non-advanced SM. |
| Chronic eosinophilic leukaemia or hypereosinophilic syndrome | 2 | French 2023 guideline, CC BY. |
| Myelodysplastic or myeloproliferative disorder (imatinib, PDGFR) | 2 | French 2023 guideline, CC BY (partial). |
| Congenital, chronic and chronic cyclical neutropenia | 2 each | Only ASCO 2015 (unknown licence, >5 y, touches severe chronic neutropenia briefly). |
| Chronic granulomatous disease | 2 | None found anywhere. |

**Tier B: an Australian source exists, but only under non-commercial, limited or subscription terms.** Each row names the best international source where one exists.

| Condition | Australian source(s) | Best international |
|---|---|---|
| Chronic Myeloid Leukaemia | eviQ (NC), OCP | ELN 2025, CC BY |
| CLL or SLL; CLL | CLL 2026 update (NC) | BSH 2025 (unknown) |
| Paroxysmal nocturnal haemoglobinuria | Services Australia only (admin, no clinical guidance) | None usable (Taiwan and EJH leads only) |
| Atypical haemolytic uraemic syndrome | 2018 ANZ TMA consensus (paywalled, old); Services Australia (admin) | Asia-Pacific 2025 (NC) |
| ALL; Precursor B-cell ALL | eviQ, OCP | ASH 2026 (NC-ND) |
| Chemotherapy-induced neutropenia | eviQ G-CSF lines and FN resource (NC) | ASCO 2015 (unknown, old) |
| DLBCL | ALA 2021 (paywalled) | EHA 2025 (NC-ND) |
| Follicular lymphoma, all 4 rows | ALA 2024 (paywalled) | ESMO/EHA 2020-21 (NC-ND, old) |
| Myelodysplastic syndrome | OCP 2021 | EHA/ESMO 2021-22 (partly CC BY) |
| Deep vein thrombosis | THANZ 2019 (limited, old) | ASH 2020 (unknown) |
| CTCL, all 4 rows | OCP (limited) | EORTC 2023 (unknown) |
| Hodgkin lymphoma; CD30+ Hodgkin lymphoma | ALA 2021 (paywalled) | EHA 2026 (NC-ND) |
| PTCL, all 3 rows | ALA 2021 (paywalled) | NCCN only |
| Myelofibrosis, both rows | OCP, eviQ | ONKOPEDIA 2025, CC BY |
| Mantle cell lymphoma | ALA 2024 (paywalled) | EHA-EU MCL 2025 (NC-ND) |
| Vitamin B12 anaemia; megaloblastic anaemias | CARPA (NC, partial) | NICE NG239 (paraphrase_only outside the UK) |
| Hairy cell leukaemia | eviQ (NC) | BSH 2020 (unknown) |
| Lymphoma | OCPs, eviQ, ALA | None |
| ACS; coronary artery disease | ACS 2025 (NC-ND) | None needed |
| Systemic embolism | AF 2018 (NC-ND, old) | ESC 2024 (lead only) |

## 3. Recommended first 3 sources to author from

1. **MSAG clinical practice guidelines, 2026** (myeloma.org.au). They cover the top-weighted row in the group (Multiple myeloma, 42 restrictions) plus Untreated multiple myeloma. They are current, cleared for review until Jan 2028, free, and written around PBS access for exactly the listed drugs. The licence is © with nothing found forbidding quotation. Consider asking Myeloma Australia for explicit reuse permission.
2. **Australian treatment guidelines for adults with AML v1.0, Feb 2025** (HSANZ / Leukaemia Foundation / Blood Cancer Taskforce). It covers AML (19), APL (3) and the idarubicin AML row (1). Recommendations are GRADE-graded and include every PBS AML drug. The licence is © HSANZ, with no quotation bar found. Access needs a health-professional click-through, but no login.
3. **ELN 2025 CML recommendations** (Leukemia, CC BY 4.0). This is international, but CML carries 26 restrictions, no Australian CML treatment guideline exists, and it is the only fully open major guideline in the set. If non-commercial terms turn out to be acceptable, the Australasian CLL 2026 update (CC BY-NC, 26 + 3 restrictions) is the next pick, and eviQ gives the widest regimen-level coverage.

## Licence surprises

- **eviQ is CC BY-NC 4.0.** The live copyright page says so, although search snippets claim CC BY 4.0. Every eviQ protocol is therefore non-commercial.
- **Most ALA lymphoma statements are paywalled** (© RACP, IMJ, no PMC copy). They are the only Australasian DLBCL, HL, PTCL, FL and MCL guidance.
- **The same MSAG guideline has two licences.** The journal version of transplant-ineligible myeloma (IMJ 2026) is paywalled, while the 2026 website PDF is free.
- **The PDFs carry no licence statements.** Neither the HSANZ AML guideline nor the MSAG PDFs has a copyright or reuse statement inside, so the recorded licences are the site footers.
- **Restrictive host terms.** THANZ strictly prohibits reproduction beyond personal non-commercial use. Cancer Council's host terms bar OCP use in any online service without permission. NICE bars reuse outside the UK without agreement. NCCN forbids any use without written permission.
- **NBA.** The blood.gov.au site default is CC BY 4.0, but every PBM module except critical bleeding is archived. The Ig Criteria site states it is not a clinical practice guideline.
- **PNH is the largest true gap.** It carries 26 restrictions, and the only Australian material is Services Australia authority text (CC BY 4.0, administrative).
