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
    r"""^(severe|moderate|mild|chronic|acute|active|uncontrolled|refractory|relapsed|
    advanced|metastatic|unresectable|recurrent|persistent|complex|symptomatic|
    pre-?symptomatic|moderate\s+to\s+severe|mild\s+to\s+moderate|locally\s+advanced|
    newly\s+diagnosed|treatment[-\s]resistant|early|late|stage\s+[0-9ivx]+[ab]?)\s+""",
    re.I | re.X,
)
# Administrative eligibility criteria are not conditions.
ADMIN = re.compile(
    r"""^(for\s|prescribing|patients?\s+(who|with\s+no)|assisted\s+reproductive|
    ketogenic\s+diet|continuing\s+therapy|grandfather|transitional|aboriginal|
    torres\s+strait|certain\s+health)""",
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
    assert family("Severe chronic plaque psoriasis") == "Plaque psoriasis"
    assert family("Stage IV malignant melanoma (unresectable)") == "Malignant melanoma"
    assert family("For prescribing by certain health practitioners") is None
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
