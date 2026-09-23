# Oncology (solid tumours): source research

Scope: 82 gap conditions (`kind: gap`, specialty "Oncology (solid tumours)") from `amc/reference/no_guideline_triage.json`; total restriction weight 319. Retrieved 2026-09-23. Cancer Council Australia guidelines are excluded (already assessed in `amc/docs/cancer-council-sources.md`). Full records are in `oncology-solid.json`; fetched evidence is kept in `research/_onc/`.

**Use rule applied:** a source is `quote` if its licence allows it, `paraphrase` if it is free to read but ©/NC/ND, and `unusable` only if it needs a login or is paywalled. Following the owner's decision of 2026-09-23, AI-use clauses are recorded verbatim (in `licence_quote` after `|| AI CLAUSE:`, and in `ai_clause_full`) but do not exclude a source.

## 1. Sources ranked

Order: Australian guidelines first, then international, then FOAM. Within each tier, sources are ranked by covered restriction weight × usability (quote 1, paraphrase 0.5, unusable 0).

| # | Source | Origin | Type | Date | Licence | Use | Conditions (weight) | Flags |
|---|---|---|---|---|---|---|---|---|
| 1 | [eviQ Cancer Treatments Online: medical oncology treatment protocols](https://www.eviq.org.au/medical-oncology) | AU | guideline | Protocol-level; e.g. ID 4613 v2 revised  | non_commercial | paraphrase | 65 (278) |  |
| 2 | [Optimal Care Pathways (2nd edition set: lung, breast, ovarian, endometrial, prostate, panc](https://www.cancer.org.au/health-professionals/optimal-cancer-care-pathways) | AU | pathway | 2nd editions published June 2021 (lung:  | non_commercial | paraphrase | 44 (213) | >5 y |
| 3 | [Guidance for the management of early breast cancer: Recommendations and practice points](https://www.canceraustralia.gov.au/publications-and-resources/cancer-australia-publications/guidance-management-early-breast-cancer-recommendations-and-practice-points) | AU | guideline | September 2020 | non_commercial | paraphrase | 5 (52) | >5 y |
| 4 | [COSA consensus guidelines for the management of neuroendocrine neoplasms (NENs)](https://www.cosa.org.au/COSA/Guidelines/NENs-Clinical-Guidelines.aspx) | AU | guideline | COSA page: Oct 2022; Cancer Council inve | limited | quote | 5 (25) | already in corpus |
| 5 | Keratinocyte cancer guideline (Cancer Council Australia) | AU | guideline | v1.4 2024-04-19 (per inventory) | limited | quote | 3 (9) | already in corpus |
| 6 | [Australian recommendations for the management of hepatocellular carcinoma: a consensus sta](https://www.mja.com.au/journal/2021/214/10/australian-recommendations-management-hepatocellular-carcinoma-consensus) | AU | consensus | Published online 14 December 2020 (Med J | paraphrase_only | paraphrase | 1 (10) | >5 y |
| 7 | [Clinical Practice Guidelines for Management of Sarcoma (Topic 1: specialised sarcoma centr](https://sarcoma.org.au/pages/sarcoma-guidelines) | AU | guideline | Series from 2022 (web search; no date on | paraphrase_only | paraphrase | 3 (9) |  |
| 8 | [BRCA Mutation Testing in Men With Metastatic Castration-Resistant Prostate Cancer: Practic](https://pmc.ncbi.nlm.nih.gov/articles/PMC12206285/) | AU | consensus | 2025-01-18 | non_commercial | paraphrase | 1 (7) |  |
| 9 | [European-Australasian consensus on the management of advanced gastric and gastro-oesophage](https://pmc.ncbi.nlm.nih.gov/articles/PMC9425884/) | AU | consensus | 2022-08-24 | non_commercial | paraphrase | 4 (6) |  |
| 10 | [Resource Stratified Sarcoma Guidelines 2025](https://www.cosa.org.au/COSA/Guidelines/COSA-PIOA-Resource-Stratified%20Sarcoma-Guidelines.aspx) | AU | guideline | 2025-10-31 (file name); COSA list: Oct 2 | paraphrase_only | paraphrase | 1 (5) |  |
| 11 | [Management of Adult Patients With Isocitrate Dehydrogenase-Mutant Gliomas in Australia: An](https://pmc.ncbi.nlm.nih.gov/articles/PMC13053624/) | AU | position_statement | 2026-03-25 | non_commercial | paraphrase | 1 (3) |  |
| 12 | [Medications to lower the risk of breast cancer: clinician guide](https://www.cosa.org.au/COSA/Guidelines/Breast-cancer-medication-guidelines.aspx) | AU | guideline | Version 7, approved by COSA Council 22 M | paraphrase_only | paraphrase | 1 (2) |  |
| 13 | [COSA guidelines for fertility preservation for people with cancer](https://www.cosa.org.au/COSA/Guidelines/COSA-Fertility-Preservation-Guidelines.aspx) | AU | guideline | May 2022 (COSA page); v0.6 2026-07-22 pe | limited | quote | 1 (1) | already in corpus |
| 14 | [Intra-vesical therapy for Non-Muscle Invasive Bladder Cancer (NMIBC): Nursing Guidelines, ](https://anzuns.org/sites/default/files/2022-06/Intra-vesical-Therapy-for-NMIBC-Guidelines.pdf) | AU | guideline | February 2018 | unknown | paraphrase | 1 (2) | >5 y, licence unknown |
| 15 | [Australasian Consensus Statement on the Identification, Prevention, and Management of Horm](https://doi.org/10.1159/000526848) | AU | consensus | 2022-09 (Crossref) | unknown | unusable | 2 (14) | licence unknown |
| 16 | [NICE technology appraisal guidance (drug-by-indication), plus NICE guidelines where releva](https://www.nice.org.uk/guidance/published?ngt=Technology%20appraisal%20guidance) | international | guideline | Per TA (2004-2026); refs from NICE site  | paraphrase_only | paraphrase | 54 (246) | **AI clause** |
| 17 | [ESMO Clinical Practice Guidelines published in Annals of Oncology (e.g. HCC 2025, early br](https://doi.org/10.1016/j.annonc.2025.02.006) | international | guideline | 2020-2026 by tumour (PubMed esummary) | non_commercial | paraphrase | 34 (204) | >5 y, **AI clause**, free access unverified |
| 18 | [ESMO Clinical Practice Guideline updates in ESMO Open (epithelial ovarian express update 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC12947637/) | international | guideline | 2025-2026 | non_commercial | paraphrase | 6 (20) |  |
| 19 | [Management of advanced prostate cancer in the Asia-Pacific region: Summary of the Asia-Pac](https://anzup.org.au/wp-content/uploads/2024/08/Chiong-et-al-APAC-APCCC-APJCO-2024.pdf) | international | consensus | Published 16 April 2024 | non_commercial | paraphrase | 5 (15) |  |
| 20 | [Soft tissue and visceral sarcomas: ESMO-EURACAN-GENTURIS Clinical Practice Guidelines](https://doi.org/10.1016/j.annonc.2021.07.006) | international | guideline | 2021-11 | non_commercial | paraphrase | 3 (9) | **AI clause**, free access unverified |
| 21 | [Gastrointestinal stromal tumours: ESMO-EURACAN-GENTURIS Clinical Practice Guidelines](https://doi.org/10.1016/j.annonc.2021.09.005) | international | guideline | 2022-01 | non_commercial | paraphrase | 2 (9) | **AI clause**, free access unverified |
| 22 | [ESMO Clinical Practice Guideline update on the use of systemic therapy in advanced thyroid](https://doi.org/10.1016/j.annonc.2022.04.009) | international | guideline | 2022-07 (update); 2019-12 (base) | non_commercial | paraphrase | 3 (8) | >5 y, **AI clause**, free access unverified |
| 23 | [Management of Primary Retroperitoneal Sarcoma (RPS) in the Adult: An Updated Consensus App](https://pmc.ncbi.nlm.nih.gov/articles/PMC9257997/) | international | consensus | 2021-11 | limited | paraphrase | 2 (4) |  |
| 24 | [Small-cell lung cancer: ESMO Clinical Practice Guidelines](https://pmc.ncbi.nlm.nih.gov/articles/PMC9464246/) | international | guideline | 2021-07 | limited | paraphrase | 2 (4) | >5 y, **AI clause** |
| 25 | [Merkel-cell carcinoma: ESMO-EURACAN Clinical Practice Guideline for diagnosis, treatment a](https://pmc.ncbi.nlm.nih.gov/articles/PMC11145756/) | international | guideline | 2024-05 | non_commercial | paraphrase | 1 (2) |  |
| 26 | [Nasopharyngeal carcinoma: ESMO-EURACAN CPG (2021) and 2023 update on adjuvant and first-li](https://doi.org/10.1016/j.annonc.2022.11.011) | international | guideline | 2023-03 (update) | non_commercial | paraphrase | 1 (1) | **AI clause**, free access unverified |
| 27 | [NCCN Clinical Practice Guidelines in Oncology (covers nearly every listed tumour, incl. Ka](https://www.nccn.org/guidelines/category_1) | international | guideline | Continuously versioned | login_required | unusable | 72 (298) | **AI clause** |
| 28 | [ASCO Guidelines (asco.org / JCO)](https://www.asco.org/about-asco/legal/terms-use) | international | guideline | Terms last updated September 11, 2025 | paraphrase_only | paraphrase | 0 (0) | **AI clause**, free access unverified |
| 29 | [WikEM: Carcinoid syndrome](https://wikem.org/wiki/Carcinoid_syndrome) | international | foam | undated wiki page | open | quote | 1 (9) |  |
| 30 | [Life in the Fast Lane (LITFL)](https://litfl.com/) | AU | foam | site | non_commercial | paraphrase | 0 (0) |  |
| 31 | [Radiopaedia](https://radiopaedia.org/licence) | AU | foam | site | non_commercial | paraphrase | 0 (0) | **AI clause** |
| 32 | [Internet Book of Critical Care: Immune-related adverse events from checkpoint inhibitors](https://emcrit.org/ibcc/checkpoint/) | international | foam | site | quote_with_attribution | paraphrase | 0 (0) |  |
| 33 | [Don't Forget the Bubbles; Deranged Physiology; RCEMLearning; PedsCases](https://dontforgetthebubbles.com/) | international | foam | site | paraphrase_only | paraphrase | 0 (0) |  |

Key licence facts (verbatim quotes, with the URL each was read from, are in the JSON):
- **eviQ** is CC BY-NC 4.0. It also says "eviQ content should not be hosted on external sites", and commercial entities "must contact eviQ to seek permission". So it is paraphrase-only for a commercial product, and even then a permission request is prudent. No AI clause was found.
- **Cancer Australia** (early breast cancer guidance, 2020) allows unaltered reproduction for personal or internal, non-commercial use only. **COSA** website T&Cs allow personal, non-commercial use only, and "Any other use is strictly prohibited." **Cancer Council** (host of the OCPs) forbids reproduction "for use on a web page or with any online service or application without permission". The OCP PDFs carry no licence of their own.
- **AI clauses (recorded, not exclusionary, per the owner decision):** NCCN's EULA says you shall not "use NCCN Content as an input to ... any artificial intelligence (AI) software". ASCO's terms prohibit "any means of text and data mining for any use, including the training of AI Tools". NICE requires "an approval process, licensing arrangement and a fee (for international use)" for AI purposes. Radiopaedia forbids text and data mining. Elsevier (publisher of the ESMO guidelines in *Annals of Oncology*) reserves "text and data mining, AI training, and similar technologies". ESMO's own website T&Cs have no AI clause. **Legal risk:** the NCCN and ASCO clauses expressly cover input to AI tools, not just training, and paraphrasing does not change that. NCCN stays unusable anyway because it needs a login. I recommend legal sign-off before any ASCO, NICE or Elsevier-hosted content is used in an AI-assisted pipeline.
- **Open access, NC-ND:** the ESMO Open guidelines (CC BY-NC-ND 4.0), the COGNO IDH-glioma statement, the BRCA-in-mCRPC guidance, the APCCC Asia-Pacific prostate summary (CC BY-NC-ND), and the European-Australasian gastric consensus (CC BY-NC 4.0). The only `open` source is WikEM (CC BY-SA 4.0, FOAM).

## 2. Conditions with NO usable Australian source

eviQ protocols cover 65 of 82 conditions, which is 278 of 319 restriction weight. The rows below have no free-to-read Australian source. The last column says whether a usable international or FOAM source covers the row instead.

| Condition | Weight | Usable international source? | Note |
|---|---|---|---|
| Kaposi sarcoma | 4 | none (only NCCN, which is unusable) | No eviQ protocol slug for Kaposi sarcoma; no Australian guideline found. |
| Terminal malignant neoplasia | 4 | none | PBS laxative item (bisacodyl, enema) for palliative patients; not a tumour-treatment guideline topic. No oncology source; belongs with palliative care. |
| Neurofibromatosis type 1 | 3 | none (only NCCN, which is unusable) | Only eviQ 752 (NF1 genetic risk management, https://www.eviq.org.au/p/752), which is not selumetinib treatment. No Australian source for selumetinib. |
| Paediatric high grade glioma | 3 | NICE | No paediatric dabrafenib/trametinib protocol confirmed on eviQ. The high-grade glioma OCP is adult-only. |
| Paediatric low grade glioma | 3 | NICE | No Australian source found. |
| Tumour-induced osteomalacia | 3 | none | Endocrine/metabolic; no oncology source found. Burosumab. |
| Dermatofibrosarcoma protuberans | 2 | none (only NCCN, which is unusable) | No Australian source; no eviQ imatinib-DFSP slug. |
| High-risk neuroblastoma | 2 | none (only NCCN, which is unusable) | Paediatric; no Australian source. |
| Malignant neoplasia | 2 | none | PBS benzodiazepine item (oxazepam, temazepam, nitrazepam) for patients with malignancy; not a tumour-treatment topic. Belongs with palliative/psychiatry. |
| Thyroid cancer | 2 | ESMO_AO_THY | Liothyronine (TSH suppression / RAI prep). No Australian source. |
| Patients requiring administration of fluorouracil by intravenous infusion | 1 | none | Administrative PBS item (route of fluorouracil). Not a condition; covered implicitly by every eviQ fluorouracil regimen. |
| Patients requiring administration of fluorouracil by intravenous injection | 1 | none | Administrative PBS item; as above. |
| Patients requiring doses greater than 20 mg per week | 1 | none | Administrative PBS item (methotrexate dose band). Not a condition. |

Of these 13 rows, 5 are not tumour-treatment topics: laxative and benzodiazepine items for patients with malignancy, and three administrative items (fluorouracil infusion or injection, methotrexate above 20 mg/week). Recommend re-triaging them rather than sourcing them. The real gaps are **Kaposi sarcoma, DFSP, high-risk neuroblastoma, paediatric low- and high-grade glioma, NF1 (selumetinib), tumour-induced osteomalacia and thyroid cancer (liothyronine)**. For those, the only international coverage is the NICE TA for paediatric glioma and ESMO for thyroid cancer, both paraphrase-only and both carrying AI clauses. The other rows have NCCN only, which needs a login.

Other rows are covered by eviQ only as regimen protocols, with no Australian narrative guideline behind them. These include GIST, RCC, urothelial cancer, differentiated and medullary thyroid cancer, Merkel cell carcinoma, NTRK, germ cell, giant cell tumour of bone, VHL and nasopharyngeal carcinoma. In some cases no drug-specific protocol was confirmed: toripalimab for NPC, selpercatinib for MTC, cabozantinib for NET, and dabrafenib/trametinib for paediatric glioma.

Misfiled rows: aGVHD, polycythaemia vera and AL amyloidosis are haematology. OCPs exist for MPN and AL amyloidosis, and eviQ has AL-amyloidosis and aGVHD resources.

Rows that may simply need linking to guidelines already in the corpus: the NET rows (functional carcinoid, VIPoma, non-functional GEP-NET, pancreatic NET) to `neuroendocrine-neoplasms` (COSA); BCC, superficial BCC and cSCC to `keratinocyte-cancer`; anticipated premature ovarian failure to `fertility-preservation-in-cancer`. HCC BCLC B/C is not covered by `hepatocellular-carcinoma-surveillance`, which is about surveillance.

## 3. Recommended first 3 sources to author from

1. **eviQ medical oncology protocols** (Cancer Institute NSW). This is the only Australian source that reaches PBS-drug level for almost every row: 65/82 conditions, current (protocol reviews dated 2025-26), free with no login. **Paraphrase only** (CC BY-NC, plus "should not be hosted on external sites"). Send eviQ a commercial-use permission request before publishing. Start with NSCLC (42), breast (27), HER2+ breast (20), ovarian (14) and RCC (13).
2. **COSA "Medications to lower the risk of breast cancer" clinician guide** (v7, March 2024). Current, Australian, and the only source for *Reduction of breast cancer risk* (tamoxifen). Paraphrase only (COSA website T&Cs).
3. **COGNO position statement on adult IDH-mutant glioma** (APJCO 2026, CC BY-NC-ND, open access). Current and Australian; covers vorasidenib. Paraphrase with citation, since ND forbids adapted text. Runner-up: the European-Australasian gastric/GOJ consensus (2022, CC BY-NC) for the four gastric rows, though it pre-dates perioperative durvalumab.

Not recommended as primary sources: Cancer Australia's early breast cancer guidance (Sept 2020, now older than 5 years, although its page still says "Current") and the OCPs (June 2021 second editions, just over 5 years old, pathway-level only). Use both for context.

## Method notes

- **Consensus** (signed-in tool): ran 5 searches with `country: "au"`, 1 of them with `open_access: true`. The account quota was then exhausted (the tool reported negative searches remaining). **Fallback: Europe PMC** title search for Australian or Australasian consensus, guideline or position-statement papers, 2019-2026 (110 hits, screened). Licences were read from PMC OAI `<permissions>` records.
- eviQ coverage comes from the eviQ sitemap (2,760 URLs). About 100 protocol titles were confirmed by fetching `/p/ID` pages; the rest rely on sitemap slugs.
- NICE TA refs come from NICE site search (JSON), with two passes per condition. They show only that coverage exists; NICE is unusable under the AI rule.
- Not reached or not read: the article pages for ESMO in *Annals of Oncology* (HTTP 403; the licence was taken from the Crossref publisher deposit plus the Elsevier user-license page), ascopubs.org terms (403), the Karger PRRT-crisis consensus page, and the PCFA 2026 prostate early-detection guidelines (seen only through a Cancer Australia news item; they cover early detection, not the PBS treatment rows).
