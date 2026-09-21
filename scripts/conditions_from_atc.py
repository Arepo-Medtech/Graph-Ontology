#!/usr/bin/env python
"""Primary-care therapeutic-area coverage, and the few conditions ATC labels name.

The unrestricted benefit (`benefit_type_code = 'U'`) is the primary-care signal:
prescribable without authority. Those items are the population that
`conditions_from_restrictions.py` structurally misses.

Two outputs, deliberately kept apart because they carry different evidential weight:

  therapeutic_areas  ATC level-2 groups with unrestricted prescribing, with item
                     and drug counts. This is what ATC genuinely supports.
  conditions         Conditions named by an ATC level-2/3 label. An INFERENCE from
                     drug class, never a stated indication, so `therapy_evidence`
                     is `atc_class_inferred`, distinct from the restrictions set's
                     `pbs_subsidised_restricted`.

ATC classifies drugs, not diseases. Only about 20 of 411 level-2/3 labels name a
condition at all, so this does NOT fill the primary-care condition gap; see
docs/conditions.md.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

CACHE = Path("cache/pbs")
OUT = Path("out/conditions_primary_care.json")
UNRESTRICTED = "U"

# Only patterns that name a condition on real ATC labels. `X preparations` and
# `anti<X> agents` were tried and dropped: they produced "Iron" from IRON
# PREPARATIONS and "Thrombotic" from ANTITHROMBOTIC AGENTS.
PATTERNS = [
    (r"^drugs?\s+used\s+in\s+(.+)$", "drugs_used_in"),
    (r"^drugs?\s+for\s+(?:treatment\s+of\s+)?(.+)$", "drugs_for"),
    (r"^agents?\s+for\s+(?:the\s+)?treatment\s+of\s+(.+)$", "agents_for"),
]
ANTI_STEM = {
    "epileptics": "Epilepsy", "asthmatics": "Asthma", "diabetics": "Diabetes mellitus",
    "depressants": "Depression", "psychotics": "Psychosis", "emetics": "Nausea and vomiting",
    "hypertensives": "Hypertension", "parkinson": "Parkinson disease", "glaucoma": "Glaucoma",
}
NOISE = re.compile(r"^(other|various|combinations?|all other|plain)\b", re.I)


def condition_from_label(label: str) -> tuple[str | None, str]:
    """Return (condition, method) or (None, reason). Never guesses."""
    if not label:
        return None, "empty"
    text = " ".join(label.strip().split())
    low = text.lower()
    if NOISE.match(low):
        return None, "noise_class"
    stem = re.match(r"^anti(?:-)?([a-z]+)$", low)
    if stem and stem.group(1) in ANTI_STEM:
        return ANTI_STEM[stem.group(1)], "anti_stem"
    for pattern, method in PATTERNS:
        match = re.match(pattern, low)
        if match:
            condition = match.group(1).strip(" ,.;:")
            condition = re.sub(r"\s*\band\s+related\s+.*$", "", condition)
            if not condition or NOISE.match(condition) or len(condition) < 3:
                return None, "empty_capture"
            return condition[:1].upper() + condition[1:], method
    return None, "pharmacology_only"


def ancestor(atc: dict, code: str, level: int) -> dict | None:
    current = atc.get(code)
    while current and current["atc_level"] > level:
        current = atc.get(current["atc_parent_code"])
    return current if current and current["atc_level"] == level else None


def build(items: list[dict], rels: list[dict], atc_rows: list[dict]) -> dict:
    by_code = {i["pbs_code"]: i for i in items}
    atc = {a["atc_code"]: a for a in atc_rows}
    unrestricted = {c for c, i in by_code.items()
                    if i.get("benefit_type_code") == UNRESTRICTED}

    groups: dict[tuple, dict] = collections.defaultdict(
        lambda: {"items": 0, "drugs": set()})
    for rel in rels:
        if rel["pbs_code"] not in unrestricted:
            continue
        group = ancestor(atc, rel["atc_code"], 2)
        if not group:
            continue
        key = (group["atc_code"], group["atc_description"])
        groups[key]["items"] += 1
        groups[key]["drugs"].add(by_code[rel["pbs_code"]].get("drug_name"))

    areas = [{"atc_code": code, "atc_description": desc,
              "unrestricted_items": v["items"],
              "drugs": sorted(d for d in v["drugs"] if d)}
             for (code, desc), v in sorted(groups.items(), key=lambda kv: -kv[1]["items"])]

    conditions, seen = [], set()
    for row in sorted(atc_rows, key=lambda a: a["atc_code"]):
        if row["atc_level"] not in (2, 3):
            continue
        name, method = condition_from_label(row["atc_description"])
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        conditions.append({"condition": name, "atc_code": row["atc_code"],
                           "atc_description": row["atc_description"],
                           "extraction_method": method,
                           "therapy_evidence": "atc_class_inferred",
                           "snomed": None})
    return {"therapeutic_areas": areas, "conditions": conditions,
            "unrestricted_item_count": len(unrestricted)}


def demo() -> None:
    assert condition_from_label("DRUGS USED IN DIABETES") == ("Diabetes", "drugs_used_in")
    assert condition_from_label("Antiepileptics") == ("Epilepsy", "anti_stem")
    for junk in ("IRON PREPARATIONS", "ANTITHROMBOTIC AGENTS", "Beta blocking agents",
                 "Other analgesics and antipyretics", ""):
        assert condition_from_label(junk)[0] is None, junk

    atc_rows = [
        {"atc_code": "A", "atc_description": "ALIMENTARY", "atc_level": 1, "atc_parent_code": None},
        {"atc_code": "A10", "atc_description": "DRUGS USED IN DIABETES", "atc_level": 2, "atc_parent_code": "A"},
        {"atc_code": "A10B", "atc_description": "BLOOD GLUCOSE LOWERING DRUGS", "atc_level": 3, "atc_parent_code": "A10"},
        {"atc_code": "A10BA02", "atc_description": "metformin", "atc_level": 5, "atc_parent_code": "A10B"},
    ]
    items = [{"pbs_code": "1", "benefit_type_code": "U", "drug_name": "Metformin"},
             {"pbs_code": "2", "benefit_type_code": "A", "drug_name": "Secret"}]
    rels = [{"pbs_code": "1", "atc_code": "A10BA02"}, {"pbs_code": "2", "atc_code": "A10BA02"}]
    out = build(items, rels, atc_rows)
    assert out["unrestricted_item_count"] == 1
    assert len(out["therapeutic_areas"]) == 1
    area = out["therapeutic_areas"][0]
    assert area["atc_code"] == "A10" and area["unrestricted_items"] == 1
    assert area["drugs"] == ["Metformin"], "restricted items must not leak in"
    assert [c["condition"] for c in out["conditions"]] == ["Diabetes"]
    assert out["conditions"][0]["therapy_evidence"] == "atc_class_inferred"
    print("self-check ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.demo:
        demo()
        raise SystemExit(0)

    def load(name: str) -> list[dict]:
        path = CACHE / f"{name}.json"
        if not path.exists():
            raise SystemExit(f"{path} not found - run pbs_pull.py first")
        return json.loads(path.read_text())["rows"]

    payload = build(load("items"), load("item-atc-relationships"), load("atc-codes"))
    payload.update({
        "source": "PBS Public API v3 items x item-atc-relationships x atc-codes",
        "licence": "Commonwealth CC BY",
        "coverage_boundary": "unrestricted benefits only; ATC names a condition in "
                             "only ~20 of 411 level-2/3 labels",
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"{len(payload['therapeutic_areas'])} therapeutic areas, "
          f"{len(payload['conditions'])} conditions -> {args.out}")
