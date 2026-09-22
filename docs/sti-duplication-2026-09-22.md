# A guideline was written over work the compendium already had

**Date:** 2026-09-22 · **Author:** claude-opus-5 · **Status:** corrected in the same session

## What happened

On 2026-09-22 I retrieved ASHM's *Australian STI Management Guidelines for Use in Primary Care* and
published `guidelines/sexually-transmissible-infections.md` (commit `bce8bf9`), reporting that it
**"closes the gonorrhoea gap"** and added **28 quoted doses**.

**Every ASHM organism page was already covered.** On 2026-09-21 the compendium had written, from the same
source, guidelines for: `chlamydia-and-gonorrhoea` · `syphilis` · `genital-herpes` ·
`mycoplasma-genitalium` · `trichomoniasis` · `bacterial-vaginosis` · `candidiasis` · `anogenital-warts` ·
`donovanosis` · `lymphogranuloma-venereum` · `mpox` · `ectoparasites-scabies-and-pubic-lice` ·
`hepatitis-a` · `hepatitis-b` · `hepatitis-c` · `hiv`.

**So three specific statements I made were wrong:**

| Stated | Actually |
|---|---|
| "Closes the gonorrhoea gap" | `chlamydia-and-gonorrhoea` already held the regimen, written 2026-09-21 |
| "28 quoted doses" added | 12 were new. The rest re-quoted doses already in the corpus |
| Quoted doses 164 → 192 | The real increase was 164 → 176 |

## The second error: a currency claim I did not check

The same guideline said that gonorrhoea, genital herpes, cervicitis, epididymo-orchitis and urethritis
**"were last revised in the 2020–2022 major review"**, inferring this from the *What's New* page's
review lists.

**Every ASHM page carries its own `dateModified` in JSON-LD structured data**, which I did not read. The
values, checked 2026-09-22, are **2026-06-29 or 2026-06-30** for all thirteen syndrome and screening
pages, and **2026-09-07** for syphilis. The compendium's own 2026-09-21 guidelines had already recorded
these dates on their face — the information was in the repository when I wrote the claim.

**The corrected position:** a `dateModified` is an *edit* date and the *What's New* list is a *content
review* list. **Neither tells a reader when a given regimen last changed.** The currency question is open,
but it is open for a different and weaker reason than I gave.

## How both were found

Not by review. By starting the next instruction — "do syphilis and the remaining STI pages" — and
checking the coverage map before writing, which is the check that should have run the first time.

## What was done

- `sexually-transmissible-infections.{md,verification.json}` **deleted**.
- Replaced by **`sti-syndromes-and-screening`**, scoped to the eleven ASHM *syndrome* pages plus
  *Standard Asymptomatic Check-up* and *Contact Tracing* — **none of which any guideline covered** — and
  retaining the two genuinely new analytical sections: the **AMH concordance comparison** and the
  **C. difficile access check**. Three organism quotes are kept solely as evidence for the comparison.
- The currency claim is replaced by a **quoted** claim citing the `dateModified` table, saved to
  `src/sti-datemodified.txt` with the extraction expression so it is re-checkable.
- The four earlier ASHM guidelines were **re-verified against today's live pages: zero content drift.**
  Their apparent failures were entirely artifacts of a different HTML-to-text extractor (spaces inserted
  around inline tags; a `-` list-item joiner). No existing guideline was wrong.

## The rule this should have followed

**Check `reference/amh-topic-coverage.json` and grep the corpus for the source URL before retrieving
anything.** A one-command audit —

```
grep -l "sti.guidelines.org.au" guidelines/*.verification.json
```

— would have shown sixteen existing guidelines before a line was written.

## Still open

The three existing guidelines built on ASHM carry mg figures but **never set `dose: true`**, so
`dose_queue.py` and `corpus_stats.py` under-count quoted doses across the corpus. These are *open-source*
doses, so nothing is missing from the attestation queue — only the statistic is wrong. **Left for the
user's decision rather than retagged unilaterally.**
