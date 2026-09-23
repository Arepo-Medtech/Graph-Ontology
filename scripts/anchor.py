#!/usr/bin/env python3
"""Hash anchors: machine re-checkable PARAPHRASE without storing the source's words.

For sources whose terms allow reading but not reproduction (e.g. (c) all rights reserved, personal
use only, NC), a claim is written as a paraphrase and backed by one or more ANCHORS instead of a
verbatim source_text. An anchor is {"h": 16 hex of sha256(span), "n": len(span), "p": first 8 chars}
over the whitespace-normalised span (verify.ws). The 8-character prefix only locates candidate
positions; the span itself is never stored. Given a fresh copy of the source, find() proves the exact
span still exists; spans() returns it, so numbers in the claim can be checked against it.

  python3 scripts/anchor.py --selftest
"""
import hashlib, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify import ws

PREFIX = 8
MAX_COPIED_RUN = 8   # a paraphrase may not reuse 8+ consecutive words of its anchored span


def make(fragment):
    s = ws(fragment)
    return {"h": hashlib.sha256(s.encode()).hexdigest()[:16], "n": len(s), "p": s[:PREFIX]}


def find(anchor, source_ws):
    """Return the span in source_ws that matches the anchor, or None."""
    p, n, h = anchor["p"], anchor["n"], anchor["h"]
    i = source_ws.find(p)
    while i >= 0:
        span = source_ws[i:i + n]
        if len(span) == n and hashlib.sha256(span.encode()).hexdigest()[:16] == h:
            return span
        i = source_ws.find(p, i + 1)
    return None


def copied_run(claim, span, limit=MAX_COPIED_RUN):
    """Longest run of consecutive words shared by claim and span (case/punct-insensitive).
    Returns the run if it is >= limit words, else None."""
    tok = lambda t: re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", t.lower())
    a, b = tok(claim), tok(span)
    grams = {tuple(b[i:i + limit]) for i in range(len(b) - limit + 1)}
    for i in range(len(a) - limit + 1):
        if tuple(a[i:i + limit]) in grams:
            return " ".join(a[i:i + limit])
    return None


def selftest():
    src = ws("Give cefalexin 20 mg/kg (max 750 mg) orally three times daily for 5 days.\n  Review at 48 hours.")
    a = make("cefalexin 20 mg/kg (max 750 mg) orally three times daily for 5 days")
    assert "cefalexin" not in str({k: v for k, v in a.items() if k != "p"}) and len(a["p"]) == PREFIX
    assert find(a, src) == "cefalexin 20 mg/kg (max 750 mg) orally three times daily for 5 days"
    assert find(a, src.replace("750", "500")) is None, "edited source must not match"
    assert copied_run("Cefalexin 20 mg/kg, max 750 mg, by mouth 3 times a day, 5 days", find(a, src)) is None
    assert copied_run("give cefalexin 20 mg kg max 750 mg orally three times daily", find(a, src))
    print("selftest ok")


if __name__ == "__main__":
    selftest()
