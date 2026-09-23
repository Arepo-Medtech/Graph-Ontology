# Source research for no-guideline PBS conditions

W = this directory. Input: W/amc/reference/no_guideline_triage.json. Use only entries with "kind": "gap" and a
"specialty" in your assigned group. Each entry lists the condition, its PBS drugs, and its restriction count, which is
a rough importance weight.

## Goal
For every condition in your group, find the best **current, free-to-read Australian (or Australasian) clinical guidance**
that a verified guideline could be authored from. Where no Australian guidance exists, say so; that is a finding, not
a failure.

## Method
1. Group the conditions: one source often covers many (e.g. one myeloma guideline covers every myeloma row).
2. Candidate publishers to check, among others: national bodies (Cancer Australia, the National Blood Authority,
   the Department of Health's CDNA Series of National Guidelines, NHMRC-approved guidelines), specialist colleges and
   societies (ARA, ACD, ANZAN, RANZCP, RANZCO, RANZCOG, GESA, TSANZ, CSANZ, KHA-CARI, ASID, HSANZ, ESA, APEG, ADS,
   MSAG/Myeloma Australia, ALLG, eviQ / Cancer Institute NSW), state health services, and major hospitals.
3. **Fetch each candidate page yourself** (python urllib or curl, or WebSearch/WebFetch if available; load deferred
   tools with ToolSearch). Record the URL, title, publisher, version or date, and whether it is free to read without
   login.
4. **Licence.** Find the source's actual copyright or reuse statement (footer, copyright page, terms of use, PDF
   front matter). Quote it VERBATIM, under 60 words, with the URL you read it from. Classify it:
   - `open`: CC BY, CC BY-SA or similar; verbatim quoting with attribution is fine.
   - `quote_with_attribution`: © but free to read, and no term forbids quoting (like RCH and the Immunisation Handbook).
   - `limited`: explicit caps or conditions (like Cancer Council's 200 words / no tables).
   - `non_commercial`: NC terms. Flag it; the project may be commercial.
   - `paraphrase_only` or `login_required`: e.g. eTG, AMH, UpToDate. Unusable for quoting.
   - `unknown`: no statement found. Say where you looked.
   **Never guess a licence.** If you did not read it, it is `unknown`.
5. **Currency.** Record the publication or review date. Flag anything older than 5 years, or labelled archived,
   rescinded or draft.

## Output (write both files; touch nothing else)
- `W/research/<group>.json`, a list of objects:
  `{source_title, publisher, url, date, free_to_read, licence_class, licence_quote, licence_url, conditions_covered: [...], notes}`
- `W/research/<group>.md`, a short readable summary with three parts:
  - a table of sources ranked by (conditions covered × licence usability);
  - the conditions with NO usable Australian source;
  - your recommended first 3 sources to author from.

## Hard rules
- Do not author guidelines. Do not run git. Do not edit anything outside W/research/.
- Do not send any message or submit any form. Read-only browsing of public pages only. Do not log in.
- Everything you report must come from a page you fetched this session. Do not state a licence, date or URL from
  memory.

## Report back (brief)
Sources found, conditions covered vs not, the top 3 recommendations, and any licence surprises.

## ADDED: use Consensus with the Australia filter (mandatory)
Load the signed-in Consensus tool with ToolSearch `select:mcp__851d60f0-c694-4862-875b-bbea06568cf9__search`. Do NOT use
`mcp__plugin_bio-research_consensus__search`: it is anonymous and capped at 3 results.
For each condition cluster, search `"<condition> clinical practice guideline"` (and `"<condition> position statement"`)
with **`country: "au"`** and `page_size: 10`. This surfaces Australian society statements published in journals, e.g. Myeloma
Australia MSAG position statements in Internal Medicine Journal. For each hit you want to use, open the article page and read
its actual licence (CC BY, CC BY-NC, © RACP…). Consensus's copyright line is a lead, not the licence of record.

## ADDED (owner direction): paraphrase where you can; add open-access and #FOAM sources
- **Licence now decides HOW a source is used, not WHETHER.** Any source that is **free to read** is usable: quote it where the licence
  allows (`open`, `quote_with_attribution`), otherwise paraphrase it with a citation (©, all-rights-reserved, NC, personal-use-only).
  Only `login_required` or paywalled sources are unusable. Keep recording the licence verbatim; it decides quote vs paraphrase.
  Add a field `"use": "quote" | "paraphrase" | "unusable"`.
- **Consensus:** add `open_access: true` alongside `country: "au"` (and run a second pass without `country` for international). The
  account quota is low, so spend searches on the highest-weight clusters first and fall back to Europe PMC or PubMed.
- **#FOAM (Free Open Access Medical education).** Check and record the licence of each: LITFL (Life in the Fast Lane, Australian),
  Don't Forget the Bubbles (paediatrics), Deranged Physiology (Australian ICU), WikEM, Radiopaedia, EMCrit/IBCC, RCEMLearning,
  PedsCases, and any condition-specific open resources. Label them `"source_type": "foam"`. They are education, not guidelines, so
  grade them below society guidelines and never let them outrank one.

## REVERSED (owner decision, 2026-09-23): do NOT mark sources unusable for AI-use clauses
Record any AI-use clause verbatim in `licence_quote` for information, but classify `use` by the normal rule (quote if the licence
allows, otherwise paraphrase). Do not use `ai_prohibited` as a reason to exclude.
