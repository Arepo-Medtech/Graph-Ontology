#!/usr/bin/env python3
"""Write docs/attestation-queue.md: every DOSE claim from a licensed source.

These are the claims that cannot be machine re-checked from this repository --
no source_text is stored, because storing it would redistribute licensed
content -- and that carry the highest consequence if wrong. verify.py counts
them per guideline; this collects them into one worksheet a person works down
against their own subscription, grouped by the monograph that holds each dose
so a single monograph is opened once, not once per claim.

THE FILE IT WRITES IS ALSO THE RECORD. Existing ticks are preserved across
regeneration, matched on ref AND sha, so a reworded claim loses its tick and
returns to the queue rather than silently keeping a sign-off for text nobody
read. Run it after any change to the guidelines.

  python3 scripts/dose_queue.py           # rewrites docs/attestation-queue.md
  python3 scripts/dose_queue.py --stdout  # print instead, change nothing
"""
import json, glob, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attestation import QUEUE, load, sha

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

prior = load()                      # ticks already recorded, if any
by = {}
for title, url, g, i, claim in rows:
    by.setdefault((title, url), []).append((g, i, claim))

n_mono = len({(t, u) for t, u, _, _, _ in rows})
n_claim = len({(g, i) for _, _, g, i, _ in rows})
kept = rej = dropped = 0
body = []
for (title, url), items in sorted(by.items()):
    head = f"[{title}]({url})" if url else f"**{title}**"
    for n, (g, i, claim) in enumerate(items):
        ref, s = f"{g}#{i}", sha(claim)
        a = prior.get(ref)
        if a and a["sha"] == s:
            if a["status"] == "confirmed":
                tick, _ = a["by"], kept
                kept += 1
            else:
                tick = "! " + a["by"]
                rej += 1
        else:
            if a:
                dropped += 1   # claim reworded since sign-off: back in the queue
            tick = ""
        body.append(f"| {tick} | {ref} | `{s}` | {head if n == 0 else ''} | {claim} |")

out = []
out.append("# Attestation queue — licensed-source dose claims\n")
out.append("Every row is a **dose, strength, interval or course duration** paraphrased from a")
out.append("**licensed** source. **No quote is stored**, so `verify.py` cannot check these: they")
out.append("must be read against a current subscription and attested by a person.\n")
out.append("> ### This file IS the record. Tick it in place.")
out.append("> | you write | means |")
out.append("> |---|---|")
out.append("> | *(empty)* | not yet attested |")
out.append("> | `KL 2026-09-23` | **CONFIRMED** against the subscription |")
out.append("> | `! KL 2026-09-23 AMH says 400 mg` | ⚠️ **REJECTED** — the claim is wrong. **`verify.py` FAILS until the guideline is fixed.** |")
out.append(">")
out.append("> Regenerating this file preserves your ticks. ⚠️ **A tick is matched on `ref` AND `sha`**")
out.append("> — if the claim is reworded the sha changes, the tick is dropped, and the row returns to")
out.append("> the queue. **No sign-off is ever carried onto text nobody read.**\n")
out.append(f"**{n_mono} monographs/topics · {n_claim} claims · "
           f"{kept} confirmed · {rej} REJECTED · {n_claim - kept - rej} outstanding.** "
           "A claim naming more than one monograph appears under each.\n")
if dropped:
    out.append(f"⚠️ **{dropped} previously attested row(s) returned to the queue** because the "
               "claim text changed since sign-off.\n")
out.append("| ✓ | ref | sha | source | claim |")
out.append("|---|---|---|---|---|")
out += body
text = "\n".join(out) + "\n"

if "--stdout" in sys.argv:
    sys.stdout.write(text)
else:
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    open(QUEUE, "w", encoding="utf-8").write(text)
    print(f"{QUEUE}: {n_claim} claims, {kept} confirmed, {rej} rejected, "
          f"{n_claim - kept - rej} outstanding"
          + (f", {dropped} returned to queue" if dropped else ""))
