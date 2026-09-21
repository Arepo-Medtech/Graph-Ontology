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

## Binding over the wire (NCTS Ontoserver)

`bind_conditions.py` above needs `sct2_Description` and `sct2_Relationship` from
an RF2 release. **Both SNOMED releases available at time of writing ship
neither** — the AU 20260731 and International 20260701 bundles both contain
Concept, Identifier, RelationshipConcreteValues and TextDefinition only, and the
AU `Full/Refset/Language` directory is empty. With no Description file there are
no terms to match against, so the offline binder cannot run. It is kept for when
a complete release is available.

`bind_ontoserver.mjs` binds over the wire instead, against the same pinned AU
edition (20260731) via the NCTS terminology server:

```bash
NCTS_CLIENT_PATH=/path/to/ncts-client.mjs \
node --env-file=/path/to/.env scripts/bind_ontoserver.mjs \
     out/conditions.json out/snomed_bindings.json
```

Credentials come from the client's `.env` via `node --env-file`; nothing reads
or stores them.

### Method discipline

Unchanged from the offline binder — nothing is fuzzy-matched:

| Method | Binding? |
|---|---|
| `exact_display` / `exact_synonym` | yes |
| `normalised_display` / `normalised_synonym` | yes |
| `candidate_unconfirmed` | **no** — top 3 hits recorded for human confirmation |
| `unmatched` | no concept found |
| `unvalidated_retry` | server/auth failure. **Never** recorded as absence |

A ranked search hit is not a binding. `$expand` orders by text relevance and
will return a near-miss for a term with no concept, so *Bone metastases* →
*Metastatic malignant neoplasm to bone* is a candidate for a human, not a link.

The `unvalidated_retry` row follows the NCTS client's fail-safe contract: a null
response means UNVALIDATED, never "no such concept".

### Results, 639 conditions

| | n | % |
|---|---|---|
| Bound | 259 | 40.5 |
| Candidate (confirmation queue) | 349 | 54.6 |
| Unmatched | 31 | 4.9 |
| Unvalidated | 0 | 0 |

By method: 189 `exact_display`, 64 `exact_synonym`, 3 + 3 normalised.

Three matcher defects were found and fixed by checking a bad number, and are
worth knowing before changing this code:

1. **Synonyms carry the match.** SNOMED records "Breast cancer" only as a
   synonym of 254837009 *Malignant neoplasm of breast*. Matching preferred
   display alone missed 67 bindings (30.0% → 40.5%).
2. **Possessives.** "Crohn's disease" normalised to `crohn s disease`, which
   never equals `crohn disease`. Stripped before punctuation.
3. **`filter` is a conjunctive word-PREFIX search.** Inflections miss —
   "metastases" does not prefix "metastatic". A stemmed retry tier recovers
   them (unmatched 46 → 31).
