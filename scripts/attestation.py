#!/usr/bin/env python3
"""Read the human attestation record out of docs/attestation-queue.md.

ONE file is the record. A person ticks the markdown table; this parses it.
There is no second JSON to keep in sync, because two copies drift.

A row is identified by ref = "<guideline>#<claim index>" and sha = the first 8
hex of sha256 over the claim text. The sha is what makes this safe: if a claim
is reworded after it was attested, the sha changes, the old tick no longer
matches, and the row returns to the queue instead of silently carrying a
sign-off for text nobody read.

Tick conventions, documented in the file's own header:
    (empty)                      not yet attested
    KL 2026-09-23                CONFIRMED against the subscription
    ! KL 2026-09-23 <reason>     REJECTED - the claim is wrong; verify.py fails
"""
import hashlib, os, re

QUEUE = os.path.join("docs", "attestation-queue.md")

def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]

def load(path=QUEUE):
    """-> {ref: {"sha":..., "status":"confirmed"|"rejected", "by":...}}"""
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("✓", "---"):
            continue
        tick, ref, s = cells[0], cells[1], cells[2]
        if not tick or "#" not in ref:
            continue
        rejected = tick.startswith("!")
        out[ref] = {"sha": s.strip("`"),
                    "status": "rejected" if rejected else "confirmed",
                    "by": tick.lstrip("!").strip()}
    return out

def status_for(ref, claim_text, record):
    """confirmed / rejected / stale / open, for one claim."""
    a = record.get(ref)
    if not a:
        return "open"
    if a["sha"] != sha(claim_text):
        return "stale"          # claim reworded since sign-off
    return a["status"]

def demo():
    assert sha("abc") == sha("abc") and len(sha("abc")) == 8
    rec = {"x#1": {"sha": sha("dose is 500 mg"), "status": "confirmed", "by": "KL"}}
    assert status_for("x#1", "dose is 500 mg", rec) == "confirmed"
    assert status_for("x#1", "dose is 400 mg", rec) == "stale"   # reworded -> not carried
    assert status_for("x#2", "anything", rec) == "open"
    print("attestation.py self-check ok")

if __name__ == "__main__":
    demo()
