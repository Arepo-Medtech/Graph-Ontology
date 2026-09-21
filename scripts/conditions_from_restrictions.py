#!/usr/bin/env python
"""Derive condition families from cached PBS restrictions.

The indication is the first paragraph of `li_html_text`, after the schedule <h1>.
Severity, stage and line-of-therapy qualifiers are stripped to get the family;
the raw strings are kept as variants so nothing is lost.

Coverage boundary: restricted and authority items only. Unrestricted benefits
carry no restriction text, so conditions treated mainly with unrestricted drugs
do not appear here. This is not a complete list of treatable conditions and is
not derived from any subscriber source.
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import re
from pathlib import Path

CACHE = Path("cache/pbs")
OUT = Path("out/conditions.json")

INDICATION = re.compile(r"</h1>\s*<p>(.*?)</p>", re.S)
TAGS = re.compile(r"<[^>]+>")
PAREN = re.compile(r"\s*\([^)]*\)")
QUALIFIER = re.compile(
    r"""^(
    # Multi-word forms FIRST: Python alternation is leftmost-first, so a bare
    # `moderate` would otherwise match "Moderate to severe X" and leave "To severe X".
    moderate\s+to\s+severe|mild\s+to\s+moderate|locally\s+advanced|newly\s+diagnosed|
    treatment[-\s]resistant|relapsed\s+and/?or\s+refractory|
    stage\s+[0-9ivx]+(/[0-9ivx]+)*[ab]?(\s*,?\s*(or\s+)?(stage\s+)?[0-9ivx]+[ab]?)*|
    severe|moderate|mild|active|uncontrolled|refractory|relapsed|advanced|metastatic|
    unresectable|recurrent|persistent|complex|symptomatic|pre-?symptomatic|early|late
    )\s+""",
    re.I | re.X,
)
# `chronic` and `acute` are deliberately NOT qualifiers: they are part of the
# disease name far more often than they are severity (chronic myeloid leukaemia,
# chronic kidney disease, acute coronary syndrome). Stripping them renamed
# "Chronic Myeloid Leukaemia" to "Myeloid Leukaemia".

# Stripping a leading qualifier can strand a connective: "Moderate to severe X"
# -> "To severe X", "Stage IIIB or Stage IV X" -> "Or Stage IV X".
CONNECTIVE = re.compile(r"^(to|or|and|and/or|with|for)\s+", re.I)

# PBS restriction scaffolding wrapped around the condition. Derived from the
# 246 zero-citation names in the first full run, not guessed: these prefixes
# are listing language, not part of any disease name.
SCAFFOLD = re.compile(
    r"""^(
    management\s+of|treatment\s+of|adjuvant\s+treatment\s+of|prevention\s+of|
    prophylaxis\s+(of|against)|maintenance\s+treatment\s+of|
    proven|confirmed|documented|serious|severe\s+complications\s+of|
    high\s+grade|previously\s+untreated|resectable|vision\s+threatening|
    first\s+line\s+treatment\s+of|second\s+line\s+treatment\s+of
    )\s+""",
    re.I | re.X,
)

# Administrative eligibility criteria are not conditions.
ADMIN = re.compile(
    r"""^(for\s|prescribing|patients?\s+(who|with\s+no)|assisted\s+reproductive|
    ketogenic\s+diet|continuing\s+therapy|grandfather|transitional|aboriginal|
    torres\s+strait|certain\s+health|the\s+condition\s+must|transfer\s+to|
    a\s+patient\s+who|patients?\s+receiving|this\s+drug|the\s+treatment|
    where\s+the|mobilisation\s+of)""",
    re.I | re.X,
)


def indication(li_html_text: str | None) -> str | None:
    if not li_html_text:
        return None
    match = INDICATION.search(li_html_text)
    if not match:
        return None
    text = html.unescape(TAGS.sub(" ", match.group(1)))
    text = " ".join(text.split())
    return text or None


def family(text: str) -> str | None:
    text = PAREN.sub("", text)
    previous = None
    while previous != text:
        previous = text
        text = QUALIFIER.sub("", text).strip()
        text = SCAFFOLD.sub("", text).strip()
        text = CONNECTIVE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text).strip(" ,.;:")
    if not text or len(text) < 3 or ADMIN.match(text):
        return None
    return text[:1].upper() + text[1:]


def build(rows: list[dict]) -> list[dict]:
    families: dict[str, dict] = collections.defaultdict(
        lambda: {"variants": set(), "restriction_count": 0})
    for row in rows:
        text = indication(row.get("li_html_text"))
        if not text or len(text) > 200:
            continue
        name = family(text)
        if not name:
            continue
        families[name]["variants"].add(text)
        families[name]["restriction_count"] += 1
    return [
        {
            "condition": name,
            "restriction_count": data["restriction_count"],
            "pbs_variants": sorted(data["variants"]),
            "therapy_evidence": "pbs_subsidised_restricted",
            # Filled by bind_conditions.py; body system is derived from the
            # SNOMED hierarchy, never from keywords.
            "snomed": None,
        }
        for name, data in sorted(families.items(), key=lambda kv: -kv[1]["restriction_count"])
    ]


def demo() -> None:
    li = ("<h1>Listing of Pharmaceutical Benefits (NHL) - Schedule 4 part 1</h1>"
          "<p>Severe chronic plaque psoriasis</p><br/><p>ignored</p>")
    assert indication(li) == "Severe chronic plaque psoriasis"
    # "chronic plaque psoriasis" is the established disease name; keeping `chronic`
    # is more precise than the earlier expectation of "Plaque psoriasis".
    assert family("Severe chronic plaque psoriasis") == "Chronic plaque psoriasis"
    assert family("Stage IV malignant melanoma (unresectable)") == "Malignant melanoma"
    assert family("For prescribing by certain health practitioners") is None
    # regressions from batch 2
    assert family("Moderate to severe ulcerative colitis") == "Ulcerative colitis"
    assert family("Stage IIIB or Stage IV non-small cell lung cancer") == "Non-small cell lung cancer"
    assert family("Moderate to severe hidradenitis suppurativa") == "Hidradenitis suppurativa"
    assert family("Relapsed and/or refractory multiple myeloma") == "Multiple myeloma"
    assert family("Chronic Myeloid Leukaemia") == "Chronic Myeloid Leukaemia", "chronic is part of the name"
    assert family("Chronic lymphocytic leukaemia") == "Chronic lymphocytic leukaemia"
    assert family("Acute coronary syndrome") == "Acute coronary syndrome"
    # scaffolding stripped (patterns taken from the first full run's residue)
    assert family("Management of renal allograft rejection") == "Renal allograft rejection"
    assert family("Vision threatening non-infectious uveitis") == "Non-infectious uveitis"
    assert family("Prevention of nausea and vomiting") == "Nausea and vomiting"
    assert family("Adjuvant treatment of stage II colon cancer") == "Colon cancer"
    assert family("Proven invasive aspergillosis") == "Invasive aspergillosis"
    assert family("Serious staphylococcal infection") == "Staphylococcal infection"
    # listing policy is not a condition
    for junk in ("The condition must be stable for the prescriber to consider",
                 "Transfer to a base-priced drug would cause patient confusion",
                 "A patient who is unable to take a solid dose form of atenolol",
                 "Patients receiving this drug as a pharmaceutical benefit prior to 1 August 2002",
                 "Mobilisation of haematopoietic stem cells"):
        assert family(junk) is None, junk
    assert family("Assisted Reproductive Technology") is None
    assert indication("<p>no h1</p>") is None
    rows = [{"li_html_text": li}, {"li_html_text": li.replace("Severe chronic", "Chronic")}]
    out = build(rows)
    assert len(out) == 1 and out[0]["restriction_count"] == 2, out
    assert len(out[0]["pbs_variants"]) == 2
    print("self-check ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.demo:
        demo()
        raise SystemExit(0)

    source = CACHE / "restrictions.json"
    if not source.exists():
        raise SystemExit(f"{source} not found - run pbs_pull.py --tables restrictions first")
    payload = json.loads(source.read_text())
    rows = payload.get("data") or payload
    conditions = build(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "source": "PBS Public API v3 restrictions",
        "licence": "Commonwealth CC BY",
        "coverage_boundary": "restricted/authority items only; unrestricted benefits absent",
        "count": len(conditions),
        "conditions": conditions,
    }, indent=2))
    print(f"{len(conditions)} condition families -> {args.out}")
