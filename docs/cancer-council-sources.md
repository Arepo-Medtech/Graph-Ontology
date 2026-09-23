# Cancer Council Australia guideline sources: inventory and decisions

**Retrieved:** 2026-09-23, from the 20 guidelines listed at cancer.org.au/health-professionals/clinical-practice-guidelines.

**Terms:** fair dealing with citation is allowed. Reproducing "more than 200 words or figures/tables" needs permission,
so every guideline here quotes at most 200 words and nothing from a table. See
`docs/cancer-council-permission-request.md` (drafted, **not sent**).

**Retrieval:** current guidelines are on MAGICapp. `cc_fetch.py` pulls each one's published JSON and strips every HTML
table before any quote is taken.

## Current, on MAGICapp — authored under the 200-word budget

| source | version · published | corpus guideline |
|---|---|---|
| Cancer pain management in adults | v2.4 · 2026-05-13 | `cancer-pain-adults` (practice points only: every recommendation and dose is in a table) |
| National Cervical Screening Program Guidelines | v2.28 · 2026-09-23 | `cervical-cancer-screening` · 12 claims · 200/200 words |
| Colorectal cancer: population screening | v1.5 · 2026-04-30 | `colorectal-cancer-population-screening` · 9 claims · 197/200 words |
| Colorectal cancer: risk and screening based on family history | v1.2 · 2026-05-25 | `colorectal-cancer-family-history-screening` · 8 claims · 196/200 words |
| Colorectal cancer (parent guideline) | v2.4 · 2026-04-23 | `colorectal-cancer-prevention-and-management` · 12 claims · 199/200 words |
| Keratinocyte cancer | v1.4 · 2024-04-19 | `keratinocyte-cancer` · 13 claims · 199/200 words |
| Melanoma | v1.1 · 2024-04-05 | `melanoma` · 12 claims · 199/200 words |
| Hepatocellular carcinoma surveillance | v0.20 · 2023-09-25 | `hepatocellular-carcinoma-surveillance` · 11 claims · 195/200 words |
| COSA neuroendocrine neoplasms | v1.0 · 2023-10-31 | `neuroendocrine-neoplasms` · 12 claims · 198/200 words |
| COSA early detection of cancer in AYAs | v1.0 · 2024-01-26 | `early-detection-of-cancer-in-young-people` · 14 claims · 196/200 words |
| COSA nutritional management, head and neck cancer | v1.3 · 2025-08-22 | `head-and-neck-cancer-nutrition` · 9 claims · 197/200 words |
| COSA fertility preservation | v0.6 · 2026-07-22 | `fertility-preservation-in-cancer` · 11 claims · 199/200 words |

## Not authored

| source | why |
|---|---|
| Cancer therapy medication safety (MAGICapp `n3QAOj`) | the API returns **401**: not publicly readable |
| COSA teleoncology | a service-delivery model, not treatment guidance |
| Lung cancer prevention and diagnosis | **draft** screening guidelines only |
| Management of cervical cancer | **in public consultation** (closed 19/05/2026); not yet published |
| Barrett's oesophagus (2014) | ⚠️ **archived** PDF |
| Endometrial cancer (2012) | ⚠️ **archived** PDF |
| PSA testing (2015) | ⚠️ **archived** PDF |
| Lung cancer treatment | ⚠️ **archived** PDF |
| Surveillance colonoscopy | ⚠️ **archived** PDF |
| Communication and swallowing in childhood brain tumour/leukaemia | ⚠️ **archived** PDF (2021) |

**Why the archived ones were skipped:** Cancer Council labels each one "developed, reviewed or revised more than five
years ago. It may no longer reflect current evidence or best practice." A verbatim quote proves only that the words
exist; it cannot make a withdrawn recommendation current. **PSA testing is the largest gap this leaves**: no current
Australian PSA guideline was found in this source.
