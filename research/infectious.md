# Source research: Infectious diseases (33) and Other/parasitic (8), 41 PBS gap conditions

This covers the 41 conditions in `no_guideline_triage.json` with `kind: gap` and specialty "Infectious diseases" or "Other". Every URL,
date and licence below comes from a page or PDF fetched on 2026-09-23. The full records, with each licence quoted verbatim, are in
`infectious.json`: 48 sources. There are 40 guidelines (19 AU, 21 international) and 8 #FOAM, and each record carries `origin`,
`source_type` and `use`.

**`use`** follows the owner rule:
- **quote** when the licence is open or quote_with_attribution.
- **paraphrase** when the source is free to read but the licence is ©, NC, ND or personal-use only, or the licence is unknown.
- **unusable** when the source is paywalled or login-only. I also marked the retired NCET COVID guidelines unusable.

**Score** = conditions covered × weight. The weights are quote 1.0, paraphrase 0.5 and unusable 0. Within the guidelines, AU sources are
ranked first. FOAM is listed separately and never outranks a guideline.

**Already authored (triage looks stale):** Urethritis, Cervicitis, PID and Epididymo-orchitis are quoted from ASHM in
`amc/guidelines/sti-syndromes-and-screening.md`. Septicaemia has `sepsis.md` (ACSQHC, which names no drug).

## 1. Sources ranked

### Guidelines

| # | Origin | Source | Date | Licence | Use | Conds | Score |
|---|---|---|---|---|---|---|---|
| 1 | AU | [CARPA Standard Treatment Manual 8th ed V1.03](https://remotephcmanuals.com.au/document/35499.html) | 2022, corrected May 2026 | non_commercial (CC BY-NC 4.0) | paraphrase (quote if project is NC) | 16 | 8.0 |
| 2 | AU | [ASHM STI Guidelines, syndrome pages](https://sti.guidelines.org.au/syndromes/) | modified Jun 2026 | quote_with_attribution | quote | 4 | 4.0 |
| 3 | AU | [RCH Immigrant Health: Strongyloides / Schisto / Intestinal parasites](https://www.rch.org.au/immigranthealth/clinical/Strongyloidiasis/) | 2020; reviewed Jan 2024 | limited (site T&C 5.2) | paraphrase | 6 | 3.0 |
| 4 | AU | [ASID/RHeaNA refugee screening recs 2nd ed](https://asid.net.au/wp-content/uploads/2026/07/ASID-RHeaNA-screening-guidelines-2nd-Edition-2016.pdf) | 2016 ⚠ >5y | paraphrase_only | paraphrase | 6 | 3.0 |
| 5 | AU | [Australasian antifungal consensus 2021, IMJ 51 S7](https://onlinelibrary.wiley.com/doi/10.1111/imj.15591) (ASID ANZMIG) | 22 Dec 2021 | limited (Wiley Free Access, not OA) | paraphrase | 5 | 2.5 |
| 6 | AU | [Australian Refugee Health Practice Guide](https://refugeehealthguide.org.au/strongyloidiasis/) | Nov 2018 ⚠ | non_commercial | paraphrase | 5 | 2.5 |
| 7 | AU | [National Healthy Skin Guideline 2nd ed](https://infectiousdiseases.thekids.org.au/resources/skin-guidelines/) | 2023 | non_commercial | paraphrase | 4 | 2.0 |
| 8 | AU | [CDNA COVID-19 SoNG v8.0](https://www.cdc.gov.au/resources/publications/cdna-national-guidelines-covid-19) | 19 Jun 2024 | **open (CC BY 4.0)** | quote | 1 | 1.0 |
| 9 | AU | [ASHM ARV guidelines (DHHS + Australian commentary)](https://hiv.guidelines.org.au/arv-adult/introduction/) | Apr 2025 | quote_with_attribution | quote | 1 | 1.0 |
| 10 | AU | [ASHM National PrEP Guidelines 2025](https://hiv.guidelines.org.au/prep-guidelines/introduction/) | Aug 2025 | quote_with_attribution | quote | 1 | 1.0 |
| 11 | AU | [CF Australia Standards of Care](https://www.cysticfibrosis.org.au/wp-content/uploads/2024/07/TD_CFA_Standard-of-Care_Design_Refresh_2024.07.25.pdf) (TSANZ-endorsed) | 2023 | quote_with_attribution (© only) | quote | 1 | 1.0 (weak, no regimen) |
| 12 | AU | [NT NTM guidelines](https://hdl.handle.net/10137/701) | Aug 2014 ⚠ | non_commercial | paraphrase | 2 | 1.0 |
| 13 | AU | [ACSQHC Sepsis Clinical Care Standard](https://www.safetyandquality.gov.au/clinical-care-standards/sepsis) | 2022 | non_commercial (CC BY-NC-ND) | paraphrase | 2 | 1.0 |
| 14 | AU | [MJA 2025 Buruli ulcer consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC12167611/) | Feb 2025 | non_commercial (CC BY-NC-ND) | paraphrase | 1 | 0.5 |
| 15 | AU | [NT leprosy guidelines v3.0](https://hdl.handle.net/10137/526) | May 2018 ⚠ | non_commercial | paraphrase | 1 | 0.5 |
| 16 | AU | [TSANZ CSLD/bronchiectasis position statement](https://europepmc.org/article/PMC/PMC10947421) | 2023 | non_commercial (CC BY-NC 4.0) | paraphrase | 1 | 0.5 |
| 17 | AU | [ASID Management of Perinatal Infections 3rd ed](https://asid.net.au/wp-content/uploads/2026/07/ASID-Management-of-Perinatal-Infections-3rd-Edition.pdf) | Nov 2022 | paraphrase_only | paraphrase | 1 | 0.5 |
| 18 | AU | [CDNA HIV SoNG](https://www.cdc.gov.au/resources/publications/human-immunodeficiency-virus-hiv-cdna-national-guidelines-public-health-units) | 2014 ⚠ outdated | non_commercial | paraphrase | 1 | 0.5 |
| 19 | AU | [NCET COVID-19 living guidelines](https://livingevidence.org.au/living-guidelines/covid-19/) | ⚠ **retired 2026** | © all rights reserved | unusable (retired) | 1 | 0 |
| 20 | Intl | [WHO AWaRe antibiotic book](https://iris.who.int/handle/10665/365237) | Dec 2022 | non_commercial (CC BY-NC-SA 3.0 IGO) | paraphrase | 11 | 5.5 |
| 21 | Intl | [IDSA aspergillosis 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4967602/) | 2016 ⚠ | quote_with_attribution (US public domain) | quote | 3 | 3.0 |
| 22 | Intl | [ECMM endemic mycoses global guideline 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC9450022/) | 2021 | unknown (PMC author MS) | paraphrase | 2 | 1.0 |
| 23 | Intl | [Surviving Sepsis Campaign 2021](https://europepmc.org/article/PMC/PMC8486643) | 2021 | limited (COVID-era permission only) | paraphrase | 2 | 1.0 |
| 24 | Intl | [WHO STH preventive chemotherapy](https://iris.who.int/handle/10665/258983) | 2017 ⚠ | non_commercial | paraphrase | 2 | 1.0 |
| 25–35 | Intl | WHO: [COVID therapeutics Aug 2025](https://iris.who.int/handle/10665/382888) · [cryptococcal 2022](https://iris.who.int/handle/10665/357088) · [leprosy 2018](https://iris.who.int/handle/10665/274127) · [strongyloidiasis 2024](https://iris.who.int/handle/10665/378257) · [schistosomiasis 2022](https://iris.who.int/handle/10665/351856) · [cystic echinococcosis 2025](https://iris.who.int/handle/10665/381674) · [SSI 2018 (mupirocin)](https://iris.who.int/handle/10665/277399) (all CC BY-NC-SA 3.0 IGO) · [Buruli 2012](https://iris.who.int/handle/10665/77771) · [onchocerciasis MDA 2016](https://iris.who.int/handle/10665/204180) (both ©) · [4th Intl CMV-SOT consensus 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12180710/) (CC BY-NC-ND) · [ATS/ERS/ESCMID/IDSA NTM 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7768745/) (©) · [ECMM cryptococcosis 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11526416/) (unknown) · [IDSA COVID 2025](https://www.idsociety.org/practice-guideline/covid-19-guideline-treatment-and-management/) (©) · [ESC endocarditis 2023](https://academic.oup.com/eurheartj/article/44/39/3948/7243107) (©) | 2012–2025 | mixed, all free to read | paraphrase | 1 each | 0.5 each |
| — | Intl | [ECIL-7 CMV](https://www.thelancet.com/journals/laninf/article/PIIS1473-3099(19)30107-0/abstract) · [ECIL PJP](https://academic.oup.com/jac/article-abstract/71/9/2386/2237807) | 2019 / 2016 | login_required (paywalled) | **unusable** | — | 0 |

### #FOAM (education, not guidelines; ranked below every guideline)

| # | Origin | Source | Licence | Use | Conds | Note |
|---|---|---|---|---|---|---|
| F1 | Intl | [WikEM](https://wikem.org/wiki/Main_Page) (32 condition pages, by API) | **open (CC BY-SA 4.0)** | quote | 36 | Only open near-complete source; US EM; pages 2016–2026; content not read |
| F2 | Intl | [IBCC](https://emcrit.org/ibcc/toc/) (PJP, Cryptococcus, Mold, Endocarditis, NTM, Septic shock) | © Farkas Medical LLC, no reuse terms | quote | 10 | Very current (Cryptococcus modified 2026-09-12) |
| F3 | AU | [Don't Forget the Bubbles](https://dontforgetthebubbles.com/congenital-cytomegalovirus-infection/) (cCMV, IE, Leprosy) | © only | quote | 3 | Paediatric |
| F4 | AU | [LITFL Infective Endocarditis](https://litfl.com/infective-endocarditis/) | CC BY-NC-SA 4.0 | paraphrase | 1 | Other LITFL slugs and the API returned 403 |
| F5–F8 | — | [Deranged Physiology](https://derangedphysiology.com/main/about) (© Alex Yartsev) · [Radiopaedia](https://radiopaedia.org/licence) (CC BY-NC-SA 3.0) · [RCEMLearning](https://www.rcemlearning.co.uk/license/) (CC BY-NC 3.0 UK) · [PedsCases](http://www.pedscases.com/terms-and-conditions-use) (all rights reserved) | as shown | quote / paraphrase | 0 | Licence recorded only; no condition pages checked |

**Checked and found empty or out of scope:**
- ASID's `/resources/clinical-guidelines` returns 404.
- NTAC (CDI journal) is TB-only, and no condition in this group is TB.
- The other CDNA SoNGs are public-health-unit documents only.
- Strongyloides Australia publishes research, not a guideline. There is no national Australian Strongyloides guideline.
- **Blocked** by bot checks that I did not bypass: NIH/HHS adult OI guidelines (clinicalinfo.hiv.gov), NCBI Bookshelf, PMC (late in the session), the Springer SSC page, and the LITFL/IBCC search APIs.

**Consensus searches:**
- 4 searches ran with `country: "au"`: Buruli (found the MJA 2025 statement), strongyloidiasis (no guideline), CMV (congenital-education papers only), and SARS-CoV-2 with `open_access: true` (no guideline).
- The account reported **"-10 searches left this month"**, meaning it is over quota. I stopped there rather than push it further negative, so the international pass without `country` was not run.
- Fallback: a Europe PMC search (Australasian affiliation, open access, 2019–2026) across 11 clusters. It added only the TSANZ bronchiectasis statement.

## 2. Conditions with NO usable Australian source

With paraphrase now allowed, most AU sources count as usable. What remains is below. The first four groups have **no free-to-read AU
guideline at all**. The last group has AU coverage only, with no international fallback recorded.

| Condition | AU | International fallback (use) | FOAM |
|---|---|---|---|
| Pneumocystis jiroveci pneumonia; Pneumocystis carinii pneumonia | none | ECIL paywalled; NIH OI blocked → **none** | IBCC PJP, WikEM PJP |
| Systemic histoplasmosis; Systemic sporotrichosis | none | ECMM endemic mycoses 2021 (paraphrase) | WikEM |
| Endophthalmitis | none | WHO AWaRe (paraphrase) | WikEM |
| Onchocerciasis | none | WHO 2016 MDA-stopping only (paraphrase) → effectively none | WikEM |
| Perichondritis of the pinna | none | **none** | WikEM only |
| 3 generic PBS antibiotic rows (amoxicillin resistance / bacteriological evidence / susceptible organism) | none (eligibility phrases, not diseases) | WHO AWaRe (paraphrase) | none |
| Fungal infection; Fungal or yeast infection; Dermatophyte; Oral or labial herpes; Tapeworm | AU paraphrase only (IMJ 2021, Healthy Skin, CARPA, RCH) | none recorded | WikEM (not for "Fungal infection") |

Every other condition has at least an AU paraphrase source. AU **quotable** sources exist only for HIV, PrEP, SARS-CoV-2 (public-health
scope), Pseudomonas (weak) and the 4 STI syndromes.

## 3. Recommended first 3 sources

1. **CARPA STM 8th ed (V1.03, May 2026).** It covers 16 conditions in one free, current Australian document: all four worms, cold sores,
   tinea and fungal skin, skin sores, sepsis, PrEP and the STI syndromes. Paraphrase it with citation, or quote it if the project is
   non-commercial (CC BY-NC 4.0).
2. **ASHM PrEP Guidelines 2025 plus ASHM ARV guidelines.** These are the only current AU sources in the group that can be quoted
   verbatim, and they close PrEP and HIV (darunavir and abacavir). The corpus `hiv.md` states no ARV regimen. Caveat: ASHM's
   copyright page returns 404.
3. **Australasian antifungal consensus 2021 (IMJ S7).** Paraphrase it. It closes 5 fungal rows (invasive aspergillosis ×2, systemic
   aspergillosis, fungal infection, cryptococcal meningitis), which carry 10 restrictions between them, and it is the Australasian
   standard. Pair it with WHO cryptococcal 2022 for HIV-associated disease. It reaches the 5-year mark in Dec 2026. ⚠ Wiley
   reserves AI-training and TDM rights (see the AI-use section). If the owner wants to avoid that, the fallback is WHO cryptococcal 2022
   plus IDSA aspergillosis 2016, which is public domain in the US.

Next in line: SARS-CoV-2 (8 restrictions), from the CDNA SoNG (quote, CC BY) plus WHO COVID Aug 2025 (paraphrase) for antivirals. CMV
(8 restrictions), from the 4th Intl CMV-SOT consensus 2025 (paraphrase), because there is no AU transplant CMV guideline.

## Licence surprises

- **The IMJ 2021 antifungal guidelines are not open access.** Wiley shows "Free Access" only and reserves "all rights, including rights
  for text and data mining and training of artificial intelligence".
- **RCH's site T&C (clause 5.2) grant a personal-use licence only.** That is stricter than RESEARCH_RULES' RCH = quote_with_attribution example.
- **The Surviving Sepsis Campaign 2021 PMC copy carries only a COVID-era permission** "for the duration of the WHO declaration".
- **The CDNA site terms ban commercial use,** but the COVID SoNG PDF itself is CC BY 4.0. It is the only open AU guideline found.
- **ASHM's quotable status rests on a © footer alone:** the copyright page 404s and the PrEP PDF has no terms.
- **WikEM is CC BY-SA 4.0,** so anything adapted from it must be ShareAlike.
- All current WHO guidelines are CC BY-NC-SA 3.0 IGO. The older WHO Buruli (2012) and onchocerciasis (2016) documents are © All rights reserved.

## AI-use clauses (recorded per owner decision, not used to exclude)

Following the REVERSED rule, `use` still follows the normal licence rule. Each clause is appended to `licence_quote` after
`[AI CLAUSE]`, and those 7 records carry `ai_clause: true`. **These sources explicitly reserve or forbid AI use, and our authoring is
AI-assisted.** Proceeding with them is the owner's call. I am only recording the risk.

| Source | Clause (short) | Read at |
|---|---|---|
| Australasian antifungal IMJ 2021 (Wiley) | "All rights reserved, including rights for text and data mining and training of artificial intelligence technologies" | onlinelibrary.wiley.com/doi/10.1111/imj.15591 |
| ESC endocarditis 2023 | ESC "reserves all rights to license uses of ESC Guidelines to train or develop generative artificial intelligence (AI) models" | academic.oup.com (EHJ article) |
| IDSA COVID 2025 | "...used for text and data mining, or used for training artificial intelligence ... without the prior permission" | idsociety.org guideline page |
| ECMM cryptococcosis 2024 and endemic mycoses 2021 (Lancet ID) | Elsevier: "All rights are reserved, including those for text and data mining, AI training" | thelancet.com (site-wide footer) |
| IBCC / EMCrit | "Commercial AI Use Prohibited: Content ... may not be used in the training or development of AI systems" | emcrit.org/disclaimer/ |
| Radiopaedia | must not "use any content ... to train, fine-tune, evaluate, validate or otherwise develop any ... artificial intelligence model" | radiopaedia.org/terms (via WebFetch) |

**Checked, no AI clause found:**
- WHO copyright and terms-of-use pages.
- CARPA front matter and document page. Its terms page is 404.
- WikEM copyrights and disclaimer.
- DFTB footer and legal disclaimer.
- Deranged Physiology.
- RCEM licence page.
- RCH T&C, ACSQHC, cdc.gov.au copyright, ASHM.

**Unverified:** LITFL. Its homepage has no clause, but /terms-of-use/ and /copyright/ returned 403.

**Not AI-specific:** PedsCases bans automated "data mining" and scraping.

**Not checked:** the Springer page for the Surviving Sepsis Campaign 2021 (bot challenge).
