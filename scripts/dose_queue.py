#!/usr/bin/env python3
"""Export the attestation queue: every DOSE claim from a licensed source.

These are the claims that cannot be machine re-checked from this repository --
no source_text is stored, because storing it would redistribute licensed
content -- and that carry the highest consequence if wrong. verify.py counts
them per guideline; this collects them into one worksheet a person can work
down against their own subscription, grouped by the monograph that holds each
dose so a single monograph is opened once, not once per claim.

  python3 scripts/dose_queue.py            > out/attestation-queue.md
"""
import json, glob, re, sys

def mono_of(loc):
    """Monograph title(s) and url(s) out of a resolved locator."""
    pairs = re.findall(r"'([^']+)' at (\S+?)(?:,|;|$)", loc)
    if pairs:
        return pairs
    m = re.search(r"therapeutic topics? '([^']+)'", loc)
    return [(m.group(1) + " (therapeutic topic)", "")] if m else [(loc[:60], "")]

rows = []
for f in sorted(glob.glob("guidelines/*.verification.json")):
    d = json.load(open(f))
    g = f.split("/")[-1].replace(".verification.json", "")
    for i, c in enumerate(d["claims"], 1):
        if c.get("dose") and c["verdict"] == "licensed_source_not_quoted":
            for title, url in mono_of(c.get("locator", "")):
                rows.append((title, url, g, i, c["claim"]))

by = {}
for title, url, g, i, claim in rows:
    by.setdefault((title, url), []).append((g, i, claim))

out = sys.stdout
out.write("# Attestation queue — licensed-source dose claims\n\n")
out.write("Every row is a **dose, strength, interval or course duration** paraphrased from a\n"
          "**licensed** source. **No quote is stored**, so `verify.py` cannot check these: they\n"
          "must be read against a current subscription and attested by a person.\n\n")
out.write(f"**{len({(t,u) for t,u,_,_,_ in rows})} monographs/topics · "
          f"{len({(g,i) for _,_,g,i,_ in rows})} claims.** "
          "A claim naming more than one monograph appears under each.\n\n")
out.write("| ✓ | source | guideline | # | claim |\n|---|---|---|---|---|\n")
for (title, url), items in sorted(by.items()):
    head = f"[{title}]({url})" if url else f"**{title}**"
    for n, (g, i, claim) in enumerate(items):
        out.write(f"|  | {head if n == 0 else ''} | {g} | {i} | {claim} |\n")
