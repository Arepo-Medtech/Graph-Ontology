#!/usr/bin/env python3
"""Turn `out/rxnorm_review.tsv` into a queue a person can actually work through.

`scripts/rxnorm_resolve.py` left 2,063 substances for review. Reading them in order is the wrong job: 920 are
already classified as not-applicable (vaccine antigens, allergen extracts, pharmacological groupers, medical
foods), and of the rest most are salts and hydrates whose **products are already reachable** through their basis of
strength, so nothing downstream is blocked by them.

This script attaches to every row the evidence the compendium has gained since — OMOP's own resolution of the same
substance, the salt-to-base pair from item 16, and how many of the substance's products reach a standard drug
concept either directly or through item 15's indirect routes — and sorts by what is actually blocked. It decides
nothing clinical: it says which rows a person still has to read, and why.

    scripts/rxnorm_review_queue.py [--review out/rxnorm_review.tsv] [--out out/rxnorm_review_queue.tsv]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
from pathlib import Path

import duckdb

DB = Path("out/compendium.duckdb")
DECISIONS = Path("reference/rxnorm_substance_decisions.json")


def load_decisions(path: Path = DECISIONS) -> dict:
    """Human choices already made, keyed by substance id. Rejections map to None."""
    if not path.exists():
        return {}
    doc = json.load(open(path))
    return {d["substance_id"]: d for d in doc.get("decisions", []) if d.get("state") != "rejected"}


def build(review_path: str, out_path: str, log=print) -> dict:
    rows = list(csv.DictReader(open(review_path), delimiter="\t"))
    decisions = load_decisions()
    con = duckdb.connect(str(DB))
    ids = sorted({r["sctid"] for r in rows})
    con.execute("CREATE OR REPLACE TEMP TABLE q AS SELECT * FROM (VALUES " + ",".join(f"('{i}')" for i in ids) + ") t(id)")

    # how many of this substance's products reach OMOP, directly or through the indirect routes
    con.execute("""CREATE OR REPLACE TEMP TABLE reach AS
        WITH used AS (
            SELECT q.id AS substance_id, i.product_id
            FROM q JOIN ingredient i ON q.id IN (i.active_substance_id, i.precise_substance_id, i.boss_substance_id))
        SELECT u.substance_id, count(DISTINCT u.product_id) AS products,
               count(DISTINCT CASE WHEN EXISTS (SELECT 1 FROM omop_drug d WHERE d.product_id=u.product_id AND d.standard_concept_id IS NOT NULL)
                                     OR EXISTS (SELECT 1 FROM omop_drug_indirect x WHERE x.product_id=u.product_id)
                              THEN u.product_id END) AS products_reaching_omop
        FROM used u GROUP BY 1""")
    # is this substance a salt whose base is the one carrying the strength?
    con.execute("""CREATE OR REPLACE TEMP TABLE as_salt AS
        SELECT b.salt_id, any_value(b.base) AS base_name, any_value(b.base_id) AS base_id,
               any_value(ob.omop_rxcui) AS base_rxcui, any_value(ob.omop_rxnorm_name) AS base_rxnorm
        FROM substance_salt_base b LEFT JOIN omop_substance ob ON ob.substance_id=b.base_id GROUP BY b.salt_id""")
    evidence = {r[0]: r for r in con.execute("""
        SELECT q.id, s.substance, coalesce(r.products,0), coalesce(r.products_reaching_omop,0),
               o.omop_rxcui, o.omop_rxnorm_name, o.agreement, a.base_name, a.base_rxcui, a.base_rxnorm
        FROM q LEFT JOIN substance s ON s.substance_id=q.id
        LEFT JOIN reach r ON r.substance_id=q.id
        LEFT JOIN omop_substance o ON o.substance_id=q.id
        LEFT JOIN as_salt a ON a.salt_id=q.id""").fetchall()}
    con.close()

    out = []
    for r in rows:
        e = evidence.get(r["sctid"], (None,) * 10)
        products, reaching = e[2] or 0, e[3] or 0
        blocked = products - reaching
        decision = decisions.get(r["sctid"])
        if decision:
            # a person has already chosen; the resolver's opinion no longer matters
            verdict = "decided by review"
        elif r["status"].startswith("not-applicable"):
            verdict = "already classified: " + r["status"].split(":", 1)[1].strip()
        elif e[4]:
            verdict = "OMOP resolves it"
        elif e[8]:
            verdict = "a salt; its base resolves and carries the strength"
        elif products == 0:
            verdict = "no product uses it"
        elif blocked == 0:
            verdict = "every product using it already reaches OMOP"
        elif r["cand1"]:
            verdict = "choose among candidates"     # a person picks one of the names the resolver found
        else:
            verdict = "no candidate found"          # nothing to choose between: needs a fresh lookup, not a judgement
        out.append({
            "sctid": r["sctid"], "substance": r["pt"], "status": r["status"], "verdict": verdict,
            "products": products, "products_reaching_omop": reaching, "products_blocked": blocked,
            "decided_rxcui": (decision or {}).get("rxcui", ""),
            "decided_name": (decision or {}).get("rxnorm_name", ""),
            "decided_state": (decision or {}).get("state", ""),
            "omop_rxcui": e[4] or "", "omop_rxnorm_name": e[5] or "", "omop_vs_rxnav": e[6] or "",
            "base_substance": e[7] or "", "base_rxcui": e[8] or "", "base_rxnorm_name": e[9] or "",
            "legacy_rxcui": r["legacy_rxcui"], "legacy_name": r["legacy_name"],
            "candidate_1": r["cand1"], "candidate_2": r["cand2"], "candidate_3": r["cand3"],
        })
    HUMAN = ("choose among candidates", "no candidate found")
    out.sort(key=lambda x: (x["verdict"] not in HUMAN, -x["products_blocked"], -x["products"]))
    with open(out_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]), delimiter="\t")
        w.writeheader()
        w.writerows(out)
    by_verdict = collections.Counter(x["verdict"] for x in out)
    needs = [x for x in out if x["verdict"] in HUMAN]
    blocked_total = sum(x["products_blocked"] for x in needs)
    running, half, eighty = 0, None, None
    for i, x in enumerate(needs, 1):
        running += x["products_blocked"]
        if half is None and running >= blocked_total * 0.5:
            half = i
        if eighty is None and running >= blocked_total * 0.8:
            eighty = i
            break
    return {
        "rows": len(out),
        "by_verdict": dict(by_verdict.most_common()),
        "decided_by_review": len(decisions),
        "products_unblocked_by_decisions": sum(
            x["products_blocked"] for x in out if x["verdict"] == "decided by review"),
        "needs_a_person": len(needs),
        "products_blocked_by_them": blocked_total,
        "rows_covering_half_the_blocked_products": half,
        "rows_covering_eighty_per_cent": eighty,
        "the_first_ten": [{"substance": x["substance"], "products_blocked": x["products_blocked"],
                           "action": x["verdict"], "candidate_1": x["candidate_1"][:52]} for x in needs[:10]],
        "written": out_path,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--review", default="out/rxnorm_review.tsv")
    ap.add_argument("--out", default="out/rxnorm_review_queue.tsv")
    a = ap.parse_args()
    print(json.dumps(build(a.review, a.out), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
