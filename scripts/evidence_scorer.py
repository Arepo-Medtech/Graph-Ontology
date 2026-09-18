#!/usr/bin/env python
"""Rarity-weighted evidence combination for ambiguous CDSS matches.

Probabilistic record linkage (Fellegi & Sunter, 1969), generalised beyond patient matching
to any "are these two coded things the same real thing" decision. Each matching attribute
contributes a log-odds weight equal to how surprising the agreement is by chance:

    weight(field) = log(m / u)          [field matches]
                  = log((1-m) / (1-u))  [field does not match]

    m = P(this field agrees | the two records are a TRUE correspondence)
    u = P(this field agrees | the two records are UNRELATED)

A common field (both records say "paracetamol") has m and u close together -> weight near 0:
weak evidence, because unrelated records would probably agree anyway. A rare field (both say
"atovaquone/proguanil", or both carry the exact same AMT code) has u near 0 -> a large positive
weight: strong evidence, because chance agreement is almost impossible. Weights sum to a
combined log-odds, converted to a posterior probability given a prior.

m and u are themselves usually unknown, especially for rare fields with only 1-5 observed
instances. Estimating them from raw counts would let a single lucky match produce infinite
confidence, so every rate here is Jeffreys-smoothed (Beta(0.5, 0.5) prior) — see `weight()`.

WHAT THIS DOES NOT DO: replace ground truth, or decide anything on its own. It scores evidence.
A CDSS gate still decides what confidence threshold triggers auto-accept vs escalate-to-human,
and that threshold is a clinical-safety decision, not a statistical one.

CALIBRATION IS SEPARATE, AND COMES LATER: `brier_score()` / `log_loss()` at the bottom measure
whether the *probabilities this module produced* were honest, against a body of cases whose
true answer is now known (a pharmacist confirmed the ambiguous brand, an audit confirmed the
duplicate therapy). They cannot run until such a body of confirmed cases exists, and they never
substitute for the scorer — they are how you'd notice this module is over- or under-confident
and needs its m/u estimates revised.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    """One matching (or mismatching) attribute between two candidate records.

    n_true_match / n_true_total  — of TRUE correspondences you have observed (or estimated
        from domain knowledge), how many agreed on this field.
    n_chance_match / n_chance_total — of UNRELATED pairs, how many agreed on this field.
        For a rare code, "this ingredient occurs in 1 of 117,258 unrelated patients" is a
        perfectly good u-estimate; it doesn't need a formal record-linkage study behind it.
    matched — whether THIS specific pair agrees on the field.
    """
    name: str
    n_true_match: int
    n_true_total: int
    n_chance_match: int
    n_chance_total: int
    matched: bool
    alpha: float = 0.5  # Jeffreys prior: smooths small counts, never lets n=1 imply certainty


def weight(e: Evidence) -> float:
    m = (e.n_true_match + e.alpha) / (e.n_true_total + 2 * e.alpha)
    u = (e.n_chance_match + e.alpha) / (e.n_chance_total + 2 * e.alpha)
    return math.log(m / u) if e.matched else math.log((1 - m) / (1 - u))


def score(evidence: list[Evidence], prior_odds: float = 1.0) -> dict:
    """Combine weighted evidence into a posterior probability plus a per-field breakdown,
    so a reviewer sees WHY a score is high or low, not just the number."""
    contributions = {e.name: round(weight(e), 3) for e in evidence}
    log_odds = math.log(prior_odds) + sum(contributions.values())
    probability = 1 / (1 + math.exp(-log_odds))
    return {"probability": probability, "log_odds": round(log_odds, 3), "contributions": contributions}


# --------------------------------------------------------------------- calibration (separate)
def brier_score(predicted_probs: list[float], outcomes: list[int]) -> float:
    """Mean squared error between predicted probability and the CONFIRMED 0/1 outcome.
    Needs resolved cases. Lower is better; 0.25 is what a coin flip scores on a 50/50 base rate."""
    return sum((p - o) ** 2 for p, o in zip(predicted_probs, outcomes)) / len(predicted_probs)


def log_loss(predicted_probs: list[float], outcomes: list[int], eps: float = 1e-9) -> float:
    """Harsher than Brier score on confident-and-wrong predictions; also needs resolved cases."""
    total = 0.0
    for p, o in zip(predicted_probs, outcomes):
        p = min(max(p, eps), 1 - eps)
        total += -(o * math.log(p) + (1 - o) * math.log(1 - p))
    return total / len(predicted_probs)


# ============================================================ four CDSS use cases (illustrative)
# Every case below states its m/u source. Where a real count exists on disk (this repo's build,
# or the Data Golf rarity analysis), it's used; everywhere else the estimate is flagged
# ILLUSTRATIVE — a placeholder pending real calibration data, not a measured rate.

def use_case_1_ambiguous_brand(matched_via: str) -> dict:
    """A PBS brand string resolved to a candidate AMT brand concept by one of four methods.
    m/u for 'amt_code'/'exact_name'/'normalised_name' are near-certain by construction (chance
    of an unrelated pair sharing a listed AMT code, or being byte-identical, is negligible).
    'prefix_name' is the real ambiguous case: many unrelated brands share a manufacturer-stem
    prefix ("APO-", "GenRx", "Sandoz"), so chance agreement is meaningfully higher — ILLUSTRATIVE
    u, pending a manual audit of prefix collisions in this compendium's own brand table."""
    methods = {
        "amt_code":        Evidence("amt_code_listed",   n_true_match=985, n_true_total=1000, n_chance_match=1,  n_chance_total=100000, matched=True),
        "exact_name":      Evidence("exact_name_match",  n_true_match=970, n_true_total=1000, n_chance_match=2,  n_chance_total=100000, matched=True),
        "normalised_name": Evidence("normalised_match",  n_true_match=950, n_true_total=1000, n_chance_match=5,  n_chance_total=100000, matched=True),
        "prefix_name":     Evidence("prefix_match",      n_true_match=700, n_true_total=1000, n_chance_match=400, n_chance_total=10000, matched=True),  # ILLUSTRATIVE u
    }
    return score([methods[matched_via]])


def use_case_2_duplicate_therapy(same_substance: bool, same_strength: bool, same_route: bool,
                                  substance_rows_in_1000_scripts: int) -> dict:
    """Two prescriptions on one patient — same drug under different brands, or coincidence?
    Substance-match weight is DATA-DRIVEN: rarer substances (fewer occurrences per 1,000
    scripts, a real, measurable rate any pharmacy system already has) make an accidental
    shared-ingredient coincidence less likely, so the same 'matched' fact carries more weight
    for a rare drug than for paracetamol. Strength/route rates below are ILLUSTRATIVE."""
    u_chance_same_substance = substance_rows_in_1000_scripts / 1000
    evidence = [
        Evidence("same_active_substance", n_true_match=98, n_true_total=100,
                 n_chance_match=max(1, round(u_chance_same_substance * 1000)), n_chance_total=1000, matched=same_substance),
        Evidence("same_strength", n_true_match=70, n_true_total=100, n_chance_match=20, n_chance_total=100, matched=same_strength),
        Evidence("same_route",    n_true_match=85, n_true_total=100, n_chance_match=40, n_chance_total=100, matched=same_route),
    ]
    return score(evidence)


def use_case_3_code_plausibility(has_supporting_lab: bool, has_supporting_med: bool,
                                  condition_prevalence_per_100k: float) -> dict:
    """Is a coded diagnosis plausible, or an extraction error with nothing else corroborating
    it? A rare diagnosis (low per-100k prevalence, a real epidemiological rate) needs
    corroborating labs/meds to be believable; the same lack of corroboration is near-irrelevant
    for a common diagnosis, because most real cases of a common condition also lack any single
    specific corroborating fact on a given day. ILLUSTRATIVE m/u for the corroboration fields."""
    rarity_factor = max(1.0, 100 / max(condition_prevalence_per_100k, 0.01))
    evidence = [
        Evidence("supporting_lab_present", n_true_match=80, n_true_total=100,
                 n_chance_match=round(50 / rarity_factor) or 1, n_chance_total=100, matched=has_supporting_lab),
        Evidence("supporting_med_present", n_true_match=75, n_true_total=100,
                 n_chance_match=round(50 / rarity_factor) or 1, n_chance_total=100, matched=has_supporting_med),
    ]
    return score(evidence, prior_odds=1.0)


def use_case_4_guideline_eligibility(codes_matched: int, codes_checked: int,
                                      edition_stable: bool) -> dict:
    """Does this patient's coded history support a guideline pathway, when checked against
    several supporting codes rather than one root subsumption test? 'edition_stable' captures
    exactly the failure we measured directly: the same root concept's descendant set moved from
    431 to 181 members across two SNOMED CT-AU editions — a hard single-code test flips silently
    when that happens; requiring several codes to agree degrades gracefully instead."""
    frac = codes_matched / max(codes_checked, 1)
    evidence = [
        Evidence("majority_of_supporting_codes_present", n_true_match=90, n_true_total=100,
                 n_chance_match=20, n_chance_total=100, matched=frac >= 0.5),
        Evidence("edition_boundary_stable_for_these_codes", n_true_match=95, n_true_total=100,
                 n_chance_match=60, n_chance_total=100, matched=edition_stable),
    ]
    return score(evidence)


def demo() -> None:
    # --- weight math sanity: a matched RARE field must outweigh a matched COMMON field ---
    common = Evidence("common", n_true_match=90, n_true_total=100, n_chance_match=80, n_chance_total=100, matched=True)
    rare = Evidence("rare", n_true_match=90, n_true_total=100, n_chance_match=1, n_chance_total=1000, matched=True)
    assert weight(rare) > weight(common), "a rarer chance-rate must produce a larger weight when matched"

    # --- a single lucky observation (n=1) must not imply certainty (Jeffreys smoothing) ---
    lucky = Evidence("lucky", n_true_match=1, n_true_total=1, n_chance_match=0, n_chance_total=1, matched=True)
    assert 0 < score([lucky])["probability"] < 1.0, "n=1 evidence must not collapse to 0 or 1"

    # --- score() is monotonic in prior odds ---
    ev = [Evidence("x", 80, 100, 20, 100, matched=True)]
    assert score(ev, prior_odds=5.0)["probability"] > score(ev, prior_odds=0.2)["probability"]

    # --- brier_score / log_loss: a perfect predictor scores 0 on both ---
    assert brier_score([1.0, 0.0], [1, 0]) == 0.0
    assert log_loss([0.99, 0.01], [1, 0]) < log_loss([0.6, 0.4], [1, 0])

    print("=== Use case 1: ambiguous brand resolution ===")
    for method in ("amt_code", "exact_name", "normalised_name", "prefix_name"):
        r = use_case_1_ambiguous_brand(method)
        print(f"  {method:16s} -> p={r['probability']:.4f}  {r['contributions']}")

    print("\n=== Use case 2: duplicate therapy (paracetamol, common vs a rare drug) ===")
    common_drug = use_case_2_duplicate_therapy(True, True, True, substance_rows_in_1000_scripts=40)
    rare_drug = use_case_2_duplicate_therapy(True, True, True, substance_rows_in_1000_scripts=1)
    print(f"  common substance (paracetamol-like): p={common_drug['probability']:.4f}")
    print(f"  rare substance:                       p={rare_drug['probability']:.4f}")
    assert rare_drug["probability"] > common_drug["probability"], "same match on a rarer drug must score higher"

    print("\n=== Use case 3: coded-fact plausibility (rare diagnosis, no corroboration) ===")
    corroborated = use_case_3_code_plausibility(True, True, condition_prevalence_per_100k=2)
    bare = use_case_3_code_plausibility(False, False, condition_prevalence_per_100k=2)
    print(f"  rare diagnosis WITH supporting lab+med: p={corroborated['probability']:.4f}")
    print(f"  rare diagnosis with NEITHER:             p={bare['probability']:.4f}")
    assert corroborated["probability"] > bare["probability"]

    print("\n=== Use case 4: guideline eligibility across an edition boundary ===")
    stable = use_case_4_guideline_eligibility(codes_matched=3, codes_checked=4, edition_stable=True)
    unstable = use_case_4_guideline_eligibility(codes_matched=1, codes_checked=4, edition_stable=False)
    print(f"  3/4 supporting codes, edition-stable:    p={stable['probability']:.4f}")
    print(f"  1/4 supporting codes, edition just moved: p={unstable['probability']:.4f}")
    assert stable["probability"] > unstable["probability"]

    print("\nall checks passed.")


if __name__ == "__main__":
    demo()
