#!/usr/bin/env python3
"""Stage-4 verification harness: does a cited work actually concern this condition?

SCOPE. The primer's stage 4 asks whether a source ENTAILS A CLAIM. These tickets
carry no claims yet — every section is [NEEDS SYNTHESIS] — so the only assertion
a bibliography entry makes is "this work is evidence about treating <condition>".
That is what is checked here, and it is labelled `topical_support`, not
`claim_entailment`, so nothing later mistakes one for the other.

VERIFIER CLASS. The primer specifies a duopoly: two model families of different
lineages, so that agreement means something. This runs ONE verifier and records
no calibrated error rate, so every verdict is stamped
`single_verifier_uncalibrated` and sits BELOW the primer's bar. It is a
screening pass, not a certification.

  prepare : build a judging batch (condition + title + abstract) as JSONL
  record  : write verdicts back onto the tickets with verifier provenance
"""
import argparse, json, glob, pathlib, time, urllib.parse, urllib.request, datetime

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BATCH = pathlib.Path("out/entail_batch.jsonl")
VERDICTS = pathlib.Path("reference/entail_verdicts.jsonl")
VERIFIER_CLASS = "single_verifier_uncalibrated"

def abstracts(pmids):
    """efetch gives abstracts; esummary does not."""
    out = {}
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        url = (f"{EUTILS}/efetch.fcgi?"
               + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk),
                                         "rettype": "abstract", "retmode": "xml"}))
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "au-guidance-entail"}), timeout=120) as r:
            xml = r.read().decode("utf-8", "replace")
        import re
        for m in re.finditer(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
            block = m.group(0)
            pid = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
            texts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", block, re.S)
            if pid:
                txt = " ".join(re.sub(r"<[^>]+>", "", t) for t in texts)
                out[pid.group(1)] = " ".join(txt.split())[:1200]
        time.sleep(0.4)
    return out

def prepare(only_fallback=True, limit=None):
    items, pmids = [], []
    for f in sorted(glob.glob("out/tickets/*.json")):
        t = json.load(open(f))
        cond = t["body"]["condition"]
        for b in t["body"].get("bibliography", []):
            tier = b.get("query_tier", "strict")
            if only_fallback and tier == "strict":
                continue
            pid = b["citation"]["query_hint_pmid"]
            items.append({"ticket": f, "condition": cond, "pmid": pid, "tier": tier,
                          "title": b["citation"]["title"],
                          "journal": b["citation"]["journal"]})
            pmids.append(pid)
    if limit:
        items, pmids = items[:limit], pmids[:limit]
    abs_by_pmid = abstracts(sorted(set(pmids)))
    with BATCH.open("w") as fh:
        for it in items:
            it["abstract"] = abs_by_pmid.get(it["pmid"], "")
            fh.write(json.dumps(it) + "\n")
    print(f"{len(items)} items -> {BATCH}  ({sum(1 for i in items if i['abstract'])} with abstracts)")

def record():
    """Apply verdicts to tickets. Verdicts are appended by the verifier as JSONL:
       {"pmid": ..., "condition": ..., "verdict": "supports|unrelated|uncertain", "why": "..."}"""
    if not VERDICTS.exists():
        raise SystemExit(f"{VERDICTS} not found")
    v = {}
    for line in VERDICTS.read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            v[(d["condition"], d["pmid"])] = d
    stamped = now = 0
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for f in sorted(glob.glob("out/tickets/*.json")):
        t = json.load(open(f)); changed = False
        for b in t["body"].get("bibliography", []):
            d = v.get((t["body"]["condition"], b["citation"]["query_hint_pmid"]))
            if not d: continue
            for g in b["gate"]:
                if g["stage"] == 4:
                    g.update({"verdict": VERDICT_TO_GATE[d["verdict"]],
                              "detail": d.get("why"), "verifier_class": VERIFIER_CLASS,
                              "scope": "topical_support_not_claim_entailment",
                              "verified_utc": ts})
                    changed = True; stamped += 1
            if d["verdict"] == "unrelated":
                b["state"] = "rejected_stage4_topical"
        if changed:
            pathlib.Path(f).write_text(json.dumps(t, indent=2)); now += 1
    print(f"stamped {stamped} citations across {now} tickets")

VERDICT_TO_GATE = {"supports": "pass", "unrelated": "fail", "uncertain": "pending"}


def demo():
    """Checks abstract extraction and verdict mapping without touching the network."""
    import re
    xml = ("<PubmedArticle><PMID Version='1'>123</PMID>"
           "<AbstractText Label='BACKGROUND'>Alpha <i>beta</i>.</AbstractText>"
           "<AbstractText>Gamma.</AbstractText></PubmedArticle>"
           "<PubmedArticle><PMID Version='1'>456</PMID></PubmedArticle>")
    out = {}
    for m in re.finditer(r"<PubmedArticle>.*?</PubmedArticle>", xml, re.S):
        block = m.group(0)
        pid = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
        texts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", block, re.S)
        if pid:
            out[pid.group(1)] = " ".join(" ".join(re.sub(r"<[^>]+>", "", t) for t in texts).split())
    assert out["123"] == "Alpha beta. Gamma.", out       # tags stripped, sections joined
    assert out["456"] == "", out                          # no abstract is empty, not missing

    # a verdict must map to exactly one gate outcome, and "uncertain" must never pass
    assert VERDICT_TO_GATE["supports"] == "pass"
    assert VERDICT_TO_GATE["unrelated"] == "fail"
    assert VERDICT_TO_GATE["uncertain"] == "pending"
    assert VERIFIER_CLASS == "single_verifier_uncalibrated", \
        "verdicts must stay labelled below the primer's duopoly bar"
    print("self-check ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "record", "demo"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--all-tiers", action="store_true")
    a = ap.parse_args()
    if a.cmd == "demo":
        demo()
    elif a.cmd == "prepare":
        prepare(only_fallback=not a.all_tiers, limit=a.limit)
    else:
        record()
