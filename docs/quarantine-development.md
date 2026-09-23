# Developing the quarantined conditions

**Can a quarantined row be moved out of quarantine?** For some, yes — and the reason is that **most of
them were never really quarantine cases.**

> ### ⚠️ THE RULE IS NOT WEAKENED. NOTHING IS BOUND.
> The pregnancy quarantine rule is untouched. What this fixes is **the input that tripped it.**

## The 15 split two ways

| | rows | what it means |
|---|---:|---|
| ⚠️ **the CONDITION is reproductive** | **7** | Quarantine is protecting exactly the right thing. **It stays, whatever we find.** |
| ✅ **only the CANDIDATE was** | **8** | The condition is ordinary; the top hit was a lexical accident |

The clearest case: ***"Diarrhoea of greater than 2 weeks duration"*** was offered ***"Gestation greater
than 20 weeks"***. The condition has nothing to do with pregnancy — **the duration clause matched.**

`scripts/develop_quarantined.mjs` re-searches each row on a **simplified term** that strips the PBS
qualifier wrapping a plain clinical noun, then filters anything reproductive.

## Result on the 8

| condition | was offered | re-searched to |
|---|---|---|
| Diarrhoea of greater than 2 weeks duration | *Gestation greater than 20 weeks* | ✅ **`62315008` Diarrhoea** |
| Septicaemia | *Antepartum septicaemia* | ✅ **`10001005` Bacterial sepsis** |
| Complicated urinary tract infection | *Induced termination of pregnancy complicated by UTI* | ✅ **`68566005` Urinary tract infection** |
| Anaemia associated with intrinsic renal disease | *Fetal hypertrophic cardiomyopathy…* | ⚠️ `271737000` Anaemia — **broader than the condition** |
| Secondarily infected traumatic skin lesions | *Fetal varicella syndrome* | ⚠️ `95324001` Skin lesion — **broader** |
| Upper and lower respiratory tract infections | *Familial nasal acilia* | ⚠️ immunodeficiency syndromes — **still wrong** |
| Facial lipoatrophy | *Nestor Guillermo progeria syndrome* | ❌ **no clean alternative** |
| Mixed episodes | *Neonatal antiphospholipid syndrome* | ❌ **no clean alternative** |

**3 clean · 3 arguable or still wrong · 2 with nothing.** Not 8.

## ⚠️ Two defects in the first cut of this script, and why they mattered

**1. It searched the full condition before the simplified term.** Results came back ranked by the
accident, not the noun. *Diarrhoea* returned *"Premature baby less than 26 weeks"* until the order was
flipped.

**2. It called a candidate "clean" on display and synonyms alone, without checking parents.**

> That is the exact hole the quarantine exists to cover — **6 of the 16 reviewed by hand carried the
> pregnancy signal only on a parent.** Uncorrected, *Facial lipoatrophy* would have been released from
> quarantine onto *Nestor Guillermo progeria syndrome*, whose parent is **"Fetal and/or neonatal
> disorder"**. Adding the parent check is what turned that row from a false success into an honest
> ❌.

## What a person still has to decide

- ⚠️ **Three of the alternatives are broader than the condition** — binding *"Anaemia associated with
  intrinsic renal disease"* to plain **Anaemia** loses the qualifier. The worksheet has a whole tier
  (**F**) for hits that are *narrower*; this is the same problem inverted, and it is a judgement.
- **The 7 reproductive conditions stay quarantined.** Contraception, preterm birth, lactation, IVF,
  termination of pregnancy, maternal hyperphenylalaninaemia, neonatal hypoglycaemia risk. **Those need
  a person regardless of what any search returns.**
- **Two have nothing**, and no amount of re-searching produced a candidate.

**Nothing here is bound.** The alternatives are now shown inline on the quarantine tier of
`docs/binding-review-queue.md` so the decision can be made in one place.
