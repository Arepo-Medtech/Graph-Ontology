# Mathematical approaches to managing ambiguity

Shannon entropy compresses an entire ambiguity into one scalar — how spread out a belief is —
and in doing so discards *why* it's spread out. It cannot distinguish "three equally likely
candidates, well-supported by data" from "almost no information at all" from "two sources that
flatly disagree." A CDSS gate needs to know which of those it's facing, because they call for
different actions: auto-accept, request more data, or escalate to a human. The approaches below
each preserve that structure instead of collapsing it.

`../scripts/evidence_scorer.py` implements the first one and is the working reference for the
rest — every other framework below is presented against it, not in isolation.

---

## 1. Fellegi-Sunter weighted-evidence sum (implemented)

**Source:** Fellegi & Sunter, *A Theory for Record Linkage*, 1969. Still the basis of modern
probabilistic record linkage (Splink, US Census Bureau matching).

**Core object:** a log-odds weight per matching attribute,

```
weight(field) = log(m / u)           if the field matches
              = log((1-m) / (1-u))   if it doesn't
```

where `m = P(field agrees | true correspondence)` and `u = P(field agrees | unrelated pair)`.
Weights sum to a combined log-odds, converted to a posterior probability.

**What it's suited for:** deciding whether two coded records refer to the same real thing, when
several independent attributes can each agree or disagree. Common attributes (both say
"paracetamol") carry weight near zero — chance agreement is likely anyway. Rare attributes
(both carry the exact same AMT code, both are atovaquone/proguanil) carry a large weight —
chance agreement is almost impossible.

**What it produces:** a single point probability plus a per-field breakdown of what drove it.

**Where it falls short:** it always returns a number, even from a single lucky observation
(mitigated here with Jeffreys smoothing, but the output is still one point estimate). It has no
native way to say "I have no idea" as distinct from "I've measured 50/50," and no native way to
represent two sources that flatly contradict each other rather than merely disagreeing in
strength.

**In this repo's four use cases:** ambiguous brand→AMT resolution, duplicate-therapy detection,
coded-fact plausibility, guideline eligibility across a SNOMED edition boundary. See
`use_case_1_ambiguous_brand()` through `use_case_4_guideline_eligibility()`.

---

## 2. Dempster-Shafer evidence theory

**Source:** Dempster (1967), formalised by Shafer (1976).

**Core object:** a *mass function* `m: 2^Θ → [0,1]` assigning belief not just to single
hypotheses but to **sets** of hypotheses, over a frame of discernment `Θ` (all the candidates).
From it: `Bel(A) = Σ_{B⊆A} m(B)` (belief) and `Pl(A) = Σ_{B∩A≠∅} m(B)` (plausibility), giving an
interval `[Bel, Pl]` rather than a point. Dempster's rule combines two independent mass
functions by normalised intersection.

**What it's suited for:** "I genuinely can't tell which of these three brand concepts it is" —
that statement gets mass assigned to the *set* of three, distinct from splitting 33/33/33 across
each one individually (which claims you've actually measured them as equally likely).

**How it relates to Fellegi-Sunter:** a strict generalisation. Fellegi-Sunter is the special
case where all mass sits on singletons — no room for "don't know," only "know and it's 50/50."

**Known weakness:** Dempster's combination rule behaves badly when two sources strongly
*disagree* rather than merely lack information — the classic Zadeh counterexample. Not the
right tool for reconciling flatly contradictory sources; see §7 for that.

**Candidate use:** representing genuine multi-way ambiguity in ingredient/brand resolution
before any tie-break rule is applied, rather than after.

---

## 3. Imprecise probability / credal sets

**Source:** Peter Walley, *Statistical Reasoning with Imprecise Probabilities*, 1991.

**Core object:** a *credal set* — the set of every probability distribution consistent with the
available evidence — summarised by a lower prevision `P̲` and upper prevision `P̅`. Classical
probability is the special case where the credal set shrinks to a single point; Dempster-Shafer's
`Bel`/`Pl` are the lower/upper probabilities of a particular credal-set structure.

**What it's suited for:** situations where you don't trust any single probability model enough
to commit to it, and want the *width* of the interval to be the honest signal — evidence that
actually constrains the answer narrowly the estimate is bracketed; evidence that says nothing,
the bracket spans almost the full [0,1] range.

**How it relates to Fellegi-Sunter and Dempster-Shafer:** the most general of the three. Both of
the others are special cases of a credal set.

**Candidate use:** any place the current m/u estimates in `evidence_scorer.py` are themselves
uncertain (small samples, expert guesses) — propagate that as an interval on the output
probability rather than pretending the point estimate is exact.

---

## 4. Conformal prediction

**Source:** Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World*, 2005; widely
adopted in production ML since ~2020.

**Core object:** a *prediction set* `C(x)` such that `P(y ∈ C(x)) ≥ 1 − α`, built from the
quantiles of a nonconformity score over a held-out calibration set. Distribution-free — no m/u
estimation, no parametric assumptions, valid under exchangeability alone.

**What it's suited for:** "give me the candidates that are guaranteed, at 95% confidence, to
contain the correct answer" — a genuinely different output shape from a probability: a *set with
a coverage guarantee*, not a ranked score.

**How it relates to Fellegi-Sunter:** doesn't compete on the same axis. Fellegi-Sunter scores one
candidate pair; conformal prediction decides how many candidates the system must keep in play to
hit a stated reliability target. They compose: use Fellegi-Sunter scores as the nonconformity
measure, then calibrate the cutoff with conformal prediction.

**Why it's the most practical of the six:** it needs a calibration set (a body of resolved
cases), which is exactly what `brier_score()`/`log_loss()` in `evidence_scorer.py` were written
to accumulate evidence for. It is the natural next thing to build once such a set exists.

**Candidate use:** ambiguous brand→AMT resolution, replacing "return the top candidate with
confidence 0.94" with "return the smallest set of candidates guaranteed to contain the right one
95% of the time" — directly actionable for an auto-accept/escalate gate.

---

## 5. Possibility theory / fuzzy sets

**Source:** Zadeh, 1965 (fuzzy sets), 1978 (possibility theory); Dubois & Prade.

**Core object:** a possibility distribution `π: Θ → [0,1]`, with possibility measure
`Π(A) = sup_{θ∈A} π(θ)` and necessity `N(A) = 1 − Π(Aᶜ)`. Non-additive — built on max/min, not
addition — because it models graded *membership*, not frequency of occurrence.

**What it's suited for:** vagueness, not randomness. "Mild," "chronic," "recent onset" are not
uncertain in the probabilistic sense — there's no experiment whose repetition would resolve
them — they're inherently graded terms. Fellegi-Sunter and its relatives all assume the ambiguity
comes from limited or noisy *evidence about a crisp fact*; possibility theory is for when the
fact itself is graded.

**How it relates to Fellegi-Sunter:** a different problem category, not a competitor. Useful
upstream of it — e.g. converting a free-text severity qualifier into a possibility distribution
over coded severity levels, before any record-linkage-style matching runs.

---

## 6. Rough sets

**Source:** Zdzisław Pawlak, 1982.

**Core object:** an indiscernibility relation `R` over a set of attributes, giving a *lower
approximation* `R̲(X)` (objects definitely in concept `X`, given the attributes recorded) and an
*upper approximation* `R̄(X)` (objects possibly in `X`). The boundary region `R̄(X) − R̲(X)` is
the ambiguous zone; `accuracy = |R̲(X)| / |R̄(X)|` quantifies how sharp the concept is under the
available attributes.

**What it's suited for:** ambiguity that comes from *limited attribute granularity* — two AMT
concepts that are genuinely indistinguishable given only the fields you recorded, not from noisy
or conflicting evidence. A lattice/order-theoretic lens on the same entity-resolution problem
Fellegi-Sunter attacks probabilistically.

**How it relates to Fellegi-Sunter:** answers a different question about the same situation.
Fellegi-Sunter asks "how likely is this a match, given the evidence." Rough sets ask "could the
available attributes even distinguish a match from a non-match, in principle" — a diagnostic on
whether more data would help before spending effort on a probabilistic score at all.

---

## 7. Belnap's four-valued logic

**Source:** Nuel Belnap, *A Useful Four-Valued Logic*, 1977; formalised via bilattices.

**Core object:** four truth values — `True`, `False`, `Both`, `Neither` — forming a bilattice,
letting a system hold contradictory evidence as its own first-class state rather than blending
it.

**What it's suited for:** two sources that flatly *disagree*, not merely two sources with
different confidence levels. Averaging two contradictory Fellegi-Sunter scores into a confident-
looking 50% hides the fact that the sources actively conflict; `Both` preserves that they do.
This is exactly the failure mode Dempster's rule struggles with (§2's Zadeh counterexample) — a
genuinely different fix, from logic rather than probability.

**How it relates to Fellegi-Sunter:** a pre-processing / conflict-detection layer. Run before
combining evidence, to flag "these two sources contradict" so the combiner doesn't quietly
average away a real disagreement.

---

## Quick reference: which one, when

| Ambiguity looks like... | Reach for |
|---|---|
| Several independent attributes, each can agree or disagree | **Fellegi-Sunter** (implemented) |
| "I can't tell which of these candidates" ≠ "I measured them as equal" | **Dempster-Shafer** |
| Your own m/u estimates are themselves uncertain | **Imprecise probability** |
| You need a guaranteed-coverage shortlist, not a single score | **Conformal prediction** |
| The fact itself is graded/vague, not just poorly evidenced | **Possibility theory** |
| Available attributes may not be able to distinguish the cases at all | **Rough sets** |
| Two sources flatly contradict each other | **Belnap four-valued logic** |
