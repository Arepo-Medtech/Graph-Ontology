#!/usr/bin/env python3
"""Ticket foundry — Engine of Engines, Play 3 slice.

Manufactures one Australian guideline into Tier A / Tier B with its
bibliography on the spine, as a content-addressed ticket.

Implements the mechanisable part of the four-stage citation gate:
  1 exists     - record retrievable from PubMed
  2 resolves   - citation RE-DERIVED from bibliographic fields, never trusted
                 from an input PMID (primer: identifier is the weakest field)
  3 retracted  - PubMed publication-type sync
  4 entails    - NOT implemented; needs the class-2 duopoly. Emitted as
                 state "pending_entailment" so nothing claims a pass it lacks.

Never writes a disposition or a rendering. Tier A numeric bounds are left
for rule extraction; they never enter the schema.

Usage: python3 foundry.py [condition substring ...]
"""
import hashlib, json, re, sys, time, urllib.parse, urllib.request, datetime, pathlib

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OUT = pathlib.Path("out/tickets")
SCHEMA_VERSION = "S:au-guidance/0.1"
# Bump when retrieval changes; --redo-zero requeues anything stamped older.
RETRIEVAL_VERSION = "v3-no-trimmed"

# Licence class per publishing body. Primer: licence class on every spine, day one.
LICENCE = {
    "National Asthma Council": "all-rights-reserved/free-to-read",
    "Lung Foundation Australia": "all-rights-reserved/free-to-read",
    "RACGP / Diabetes Australia": "all-rights-reserved/free-to-read",
    "Kidney Health Australia": "all-rights-reserved/free-to-read",
    "Heart Foundation": "all-rights-reserved/free-to-read",
    "NHFA / CSANZ": "all-rights-reserved/free-to-read",
    "RANZCP": "all-rights-reserved/free-to-read",
    "Dept of Health": "CC-BY-4.0",
    "Cancer Institute NSW": "registration-required",
    "Stroke Foundation": "all-rights-reserved/free-to-read",
    "ASHM": "all-rights-reserved/free-to-read",
}
# Nothing here is redistributable-by-default. Free-to-read != re-publishable.
REDISTRIBUTABLE = {"CC-BY-4.0", "CC0", "Apache-2.0", "MIT"}

def eutils(path, **p):
    p.setdefault("retmode", "json")
    req = urllib.request.Request(f"{EUTILS}/{path}?{urllib.parse.urlencode(p)}",
                                 headers={"User-Agent": "au-guidance-foundry"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def cid(obj):
    """Content-addressed spine ID over canonical JSON."""
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def gate(pmid, summ):
    """Citation gate stages 1-3. Returns a re-derived citation + verdicts."""
    d = summ.get("result", {}).get(pmid)
    verdicts = []
    if not d:
        return None, [{"stage": 1, "name": "exists", "verdict": "fail",
                       "class": 1, "detail": "no PubMed record"}]
    verdicts.append({"stage": 1, "name": "exists", "verdict": "pass", "class": 1})

    # Stage 2: rebuild the citation from bibliographic fields. The input PMID is
    # only ever the query hint that got us here.
    authors = [a.get("name") for a in d.get("authors", []) if a.get("name")]
    citation = {
        "title": (d.get("title") or "").rstrip("."),
        "journal": d.get("source"),
        "year": (d.get("pubdate") or "")[:4],
        "volume": d.get("volume") or None,
        "pages": d.get("pages") or None,
        "first_author": authors[0] if authors else None,
        "author_count": len(authors),
        "doi": d.get("elocationid", "").replace("doi: ", "") or None,
        "publication_types": d.get("pubtype", []),
        "derived_from": "pubmed_esummary_bibliographic_fields",
        "query_hint_pmid": pmid,
    }
    ok = bool(citation["title"] and citation["journal"] and citation["year"])
    verdicts.append({"stage": 2, "name": "resolves", "class": 1,
                     "verdict": "pass" if ok else "fail",
                     "detail": "citation re-derived from bibliographic fields"})

    # Stage 3: retraction.
    pt = set(citation["publication_types"])
    retracted = bool(pt & {"Retracted Publication", "Retraction of Publication"})
    verdicts.append({"stage": 3, "name": "not_retracted", "class": 1,
                     "verdict": "fail" if retracted else "pass",
                     "detail": sorted(pt & {"Retracted Publication",
                                            "Retraction of Publication"}) or None})

    # Stage 4 is a class-2 instrument. Not run here; never claimed as passed.
    verdicts.append({"stage": 4, "name": "entails", "class": 2,
                     "verdict": "pending", "detail": "requires duopoly verifier"})
    return citation, verdicts

def evidence(condition, n=8):
    """Strict query first, then a looser one. 43% of a 604-condition run returned
    zero citations under the strict query alone: it demands a guideline/SR/MA
    publication type AND a therapy MeSH subheading, which the long tail of rare
    conditions simply does not carry. The fallback keeps the condition term and
    drops the design filter, so a rare disease yields primary literature rather
    than nothing. `query_tier` records which one produced the result.
    """
    strict = (f'("{condition}"[Title/Abstract]) AND '
              f'(practice guideline[pt] OR systematic review[pt] OR meta-analysis[pt]) AND '
              f'(therapy[sh] OR drug therapy[sh])')
    loose = f'("{condition}"[Title/Abstract]) AND (therapy[sh] OR drug therapy[sh])'
    bare = f'"{condition}"[Title/Abstract]'
    # A `trimmed` tier once queried the head of long PBS names. Verification of 40
    # fallback citations found 8 of 16 trimmed hits (50%) topically unrelated:
    # "Adjuvant management of breast cancer" trimmed to "Adjuvant management" and
    # returned endometrial, ovarian, pancreatic and rectal cancer. Retrieval
    # improved, precision collapsed. Removed: a condition with no citations is
    # visible to a reviewer, a plausible wrong citation is not.
    tiers = [("strict", strict), ("loose", loose), ("bare", bare)]
    for tier, term in tiers:
        ids = eutils("esearch.fcgi", db="pubmed", term=term, retmax=n,
                     sort="relevance").get("esearchresult", {}).get("idlist", [])
        if not ids:
            continue
        time.sleep(0.4)
        summ = eutils("esummary.fcgi", db="pubmed", id=",".join(ids))
        out = []
        for pid in ids:
            c, v = gate(pid, summ)
            if c is None:
                continue
            admitted = all(x["verdict"] == "pass" for x in v if x["class"] == 1)
            out.append({"citation": c, "gate": v, "query_tier": tier,
                        "state": "admitted_pending_entailment" if admitted else "rejected"})
        if out:
            return out
        time.sleep(0.4)
    return []

def slug(s, n=60):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n].rstrip("-") or "untitled"

def coverage_status(rec):
    """Tolerates both condition schemas; unknown is explicit, never a crash."""
    return rec.get("status") or rec.get("open_au_guidance") or "unassessed"

def build(rec):
    cond = rec["condition"]
    refs = evidence(cond)
    now = datetime.datetime.now(datetime.timezone.utc)
    lic = LICENCE.get(rec.get("body"), "unknown")

    body = {
        "condition": cond,
        "coverage_status": coverage_status(rec),
        "tier_a": {
            "state": "not_extracted",
            "note": "Executable rules (dose, renal adjustment, thresholds). "
                    "Numeric bounds live here, never in the schema.",
            "rules": [],
        },
        "tier_b": {
            "state": "source_identified" if rec.get("url") else "no_open_source",
            "source": rec.get("source"),
            "source_url": rec.get("url"),
            "publisher": rec.get("body"),
            "note": "Reformat and chunk at topic boundaries before use.",
            "chunks": [],
        },
        "bibliography": refs,
        "caveat": rec.get("caveat"),
    }

    spine = {
        "spine_id": cid(body),
        "created_utc": now.isoformat(),
        "licence_class": lic,
        "redistributable": lic in REDISTRIBUTABLE,
        "version_tuple": {
            "S": SCHEMA_VERSION,
            "R": None, "K": None, "W": None, "F": None,
            "M": "none/deterministic-extraction",
            "P": "none", "U": None,
        },
        "prov": {
            "wasGeneratedBy": "au-guidance-foundry/foundry.py",
            "wasDerivedFrom": [u for u in [rec.get("url")] if u] +
                              ["https://pubmed.ncbi.nlm.nih.gov/"],
            "generatedAtTime": now.isoformat(),
        },
        "expires": (now + datetime.timedelta(days=365)).date().isoformat(),
        "expiry_basis": "annual re-verification; re-key to living guideline when available",
        "evidence_tiers": sorted({r.get("query_tier") for r in refs}) or None,
        "retrieval_version": RETRIEVAL_VERSION,
        "gate_summary": {
            "admitted": sum(1 for r in refs if r["state"].startswith("admitted")),
            "rejected": sum(1 for r in refs if r["state"] == "rejected"),
            "entailment": "pending — no class-2 verifier run",
        },
    }

    ticket = {"spine": spine, "body": body}
    OUT.mkdir(exist_ok=True)
    (OUT / f"{slug(cond)}.json").write_text(json.dumps(ticket, indent=2))
    return cond, spine

def demo():
    summ = {"result": {"1": {
        "title": "A trial.", "source": "BMJ", "pubdate": "2020 Jan",
        "authors": [{"name": "Smith J"}], "pubtype": ["Journal Article"],
        "elocationid": "doi: 10.1/x"}}}
    c, v = gate("1", summ)
    assert c["query_hint_pmid"] == "1" and "pmid" not in c, "PMID must not be a citation fact"
    assert c["derived_from"] == "pubmed_esummary_bibliographic_fields"
    assert [x["verdict"] for x in v] == ["pass", "pass", "pass", "pending"]

    summ["result"]["1"]["pubtype"] = ["Retracted Publication"]
    _, v2 = gate("1", summ)
    assert v2[2]["verdict"] == "fail", "retraction must fail stage 3"

    _, v3 = gate("9", {"result": {}})
    assert v3[0]["verdict"] == "fail"
    assert cid({"a": 1}) == cid({"a": 1}) and cid({"a": 1}) != cid({"a": 2})
    assert "CC-BY-4.0" in REDISTRIBUTABLE and "registration-required" not in REDISTRIBUTABLE
    assert coverage_status({"status": "open"}) == "open"
    assert coverage_status({"open_au_guidance": "gap"}) == "gap"
    assert coverage_status({}) == "unassessed", "missing coverage must not raise"
    print("self-check ok")

if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo(); sys.exit(0)
    args = sys.argv[1:]
    recs = json.load(open("conditions.json"))["conditions"]
    if args:
        recs = [r for r in recs if any(a.lower() in r["condition"].lower() for a in args)]
    for r in recs:
        try:
            cond, sp = build(r)
            flag = "REDIST" if sp["redistributable"] else "no-redist"
            print(f"{sp['gate_summary']['admitted']:2d} admitted  "
                  f"{sp['gate_summary']['rejected']:2d} rejected  "
                  f"{flag:10s} {cond}")
        except Exception as e:
            print(f"FAIL {r['condition']}: {e}", file=sys.stderr)
