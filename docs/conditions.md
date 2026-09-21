# Condition families

**Status:** derived, licence-clean, SNOMED binding implemented but not yet run

**Tables / files:** `out/conditions.json`

**Source:** PBS Public API v3 `restrictions`, latest schedule. Commonwealth CC BY.

## What this is

Condition families with evidence of subsidised drug therapy, derived from the
indication text of PBS restrictions. The indication is the first paragraph of
`li_html_text`; severity, stage and line-of-therapy qualifiers are stripped to
get the family, and the raw strings are kept as `pbs_variants`.

A sample run over the current schedule gave 3,581 restrictions carrying 647
distinct indications, reducing to ~597 condition families.

## What this is not

**Not derived from any subscriber source.** AMH and Therapeutic Guidelines are
paywalled, and the selection and arrangement of a contents list is the part of a
compilation that attracts copyright. Nothing here was taken from either.

**Not a complete list of treatable conditions.** PBS restrictions cover
restricted and authority items only. Unrestricted benefits carry no restriction
text, so conditions treated mainly with unrestricted drugs are absent — the set
skews to oncology, biologics and high-cost specialist therapy. Filling the
primary-care side means deriving conditions from `items` x `atc-codes`, which
this repo already pulls.

## SNOMED binding

`bind_conditions.py` binds each family to a SNOMED CT-AU disorder or finding
concept. Consistent with the rest of the compendium, nothing is fuzzy-matched
and every link carries its method:

| Method | Meaning |
|---|---|
| `exact_fsn` | condition equals the FSN with its semantic tag removed |
| `exact_synonym` | condition equals an active synonym |
| `normalised_name` | punctuation- and case-insensitive match |
| `unmatched` | no binding; `snomed` stays null |

Body system is derived from the is-a ancestor closure intersected with
`reference/body_systems.json`, never from keywords. A keyword heuristic was
tried first and left 181 of 597 families unclassified, which is why it was
dropped rather than tuned.

## Running it

```bash
python scripts/pbs_pull.py --tables restrictions
python scripts/conditions_from_restrictions.py
export AU_RF2_SNAPSHOT=/path/to/SnomedCT_Release_AU1000036_<release>/Snapshot
python scripts/bind_conditions.py --list-ancestor-roots   # populate body_systems.json
python scripts/bind_conditions.py
```

Both scripts carry `--demo` self-checks. `bind_conditions.py --demo` verifies the
match methods and the transitive closure against RF2-shaped fixtures and needs no
snapshot; the binding has **not** been run against a real AU release yet.
