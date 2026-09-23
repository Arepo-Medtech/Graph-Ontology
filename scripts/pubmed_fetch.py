#!/usr/bin/env python3
"""Fetch PubMed records (title, abstract, journal, year) by search or by PMID, into cache/pubmed/ -- NCBI E-utilities.

The sign -> diagnosis likelihood ratios are transcribed from published diagnostic-accuracy reviews; this is how their
abstracts are read and kept for re-verification. Abstracts are the publishers' text: they stay in cache/pubmed/
(git-ignored) and are never committed -- the repository keeps only the numbers and the PMID
(reference/diagnostic_accuracy.json), and scripts/verify_diagnostic_accuracy.py checks each number against the cache.

    scripts/pubmed_fetch.py search "appendicitis[ti] AND (meta-analysis[pt] OR systematic review[pt]) AND sensitivity"
    scripts/pubmed_fetch.py fetch 15286004 12345678
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path("cache/pubmed")
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def call(tool: str, **q) -> bytes:
    q.update({"tool": "graph-ontology", "db": "pubmed"})
    for i in range(4):
        try:
            time.sleep(0.4)                           # NCBI: at most 3 requests a second without a key
            return urllib.request.urlopen(f"{EU}/{tool}.fcgi?" + urllib.parse.urlencode(q), timeout=60).read()
        except Exception:
            time.sleep(2 + 3 * i)
    raise SystemExit(f"E-utilities did not answer ({tool})")


def fetch(pmids: list[str]) -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [p for p in pmids if not (OUT / f"{p}.json").exists()]
    for i in range(0, len(todo), 100):
        root = ET.fromstring(call("efetch", id=",".join(todo[i:i + 100]), retmode="xml"))
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//MedlineCitation/PMID")
            abstract = " ".join(("".join(a.itertext()) if a.get("Label") is None else f"{a.get('Label')}: " + "".join(a.itertext()))
                                for a in art.iter("AbstractText"))
            rec = {"pmid": pmid, "title": "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else "",
                   "journal": art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title"),
                   "year": art.findtext(".//JournalIssue/PubDate/Year") or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4],
                   "pub_types": [t.text for t in art.iter("PublicationType")], "abstract": abstract}
            json.dump(rec, open(OUT / f"{pmid}.json", "w"), ensure_ascii=False, indent=1)
    return [json.load(open(OUT / f"{p}.json")) for p in pmids if (OUT / f"{p}.json").exists()]


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ("search", "fetch"):
        print(__doc__)
        return 2
    if sys.argv[1] == "search":
        ids = json.loads(call("esearch", term=sys.argv[2], retmax=12, sort="relevance", retmode="json"))["esearchresult"]["idlist"]
    else:
        ids = sys.argv[2:]
    for r in fetch(ids):
        print(f"PMID {r['pmid']}  {r['year']}  {r['journal']}  [{', '.join(t for t in r['pub_types'] if t in ('Meta-Analysis', 'Systematic Review', 'Review'))}]\n  {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
