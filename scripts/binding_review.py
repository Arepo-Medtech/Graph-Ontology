#!/usr/bin/env python3
"""The SNOMED binding review worksheet, and the harvest back into corrections.

330 candidates sit in reference/snomed_candidates_review.json at snomed: null.
Reading a 756 KB JSON in file order is the wrong job, and it is the reason the
review has not happened -- the same diagnosis Item 19 made of the 2,063-row
RxNorm queue. This does NOT make the binding judgement. It orders the rows by
what evidence already settles, puts the evidence beside each row, and gives a
person somewhere to write the decision.

⚠️ THE 'plausible - confirm' TIER IS NOT SAFE. The review file's own warning:
of 16 quarantined pregnancy candidates reviewed by hand, 6 carried no flag at
all and every one was wrong. Lexical agreement is not evidence. Nothing here is
auto-bound, ever.

  python3 scripts/binding_review.py              # rewrite the worksheet
  python3 scripts/binding_review.py --harvest    # worksheet -> binding_corrections.json
  python3 scripts/binding_review.py --demo       # self-check

Decisions are written in the first column of docs/binding-review-queue.md:

  (empty)                       not yet reviewed
  918591000168102 KL 2026-09-23 BIND this concept  -> corrected_pending_attestation
  ! KL 2026-09-23 <why>         REJECT: must NOT bind -> rejected
  ? KL 2026-09-23 <note>        deferred; stays in the queue, note kept
"""
import hashlib, json, os, re, sys

REVIEW = "reference/snomed_candidates_review.json"
CORR   = "reference/binding_corrections.json"
QUEUE  = os.path.join("docs", "binding-review-queue.md")

# Order by what evidence settles, cheapest decision first. The REJECT tiers were
# derived from the SNOMED hierarchy -- parents sharing no concept with the
# condition -- not from string similarity, so they are the rows a person can
# close fastest and most safely.
TIERS = [
    ("QUARANTINE",
     "A. ⚠️ QUARANTINED — pregnancy or reproductive, MANUAL REVIEW REGARDLESS OF SIGNAL",
     "review by hand; do not trust any signal"),
    ("REJECT — neither hit nor any parent shares a concept with the condition",
     "B. Reject on hierarchy — no shared concept", "confirm the rejection"),
    ("REJECT — hit looks related but its parents share nothing with the condition",
     "C. Reject on hierarchy — parents unrelated", "confirm the rejection"),
    ("REJECT — wrong hierarchy for this wording; re-search under <<71388002 Procedure",
     "D. Wrong hierarchy — re-search as Procedure", "re-search, do not bind"),
    ("consider parent instead", "E. Parent concept suggested instead", "judge parent vs hit"),
    ("hit is narrower — check it is not a sub-type",
     "F. Hit is narrower than the condition", "check it is not a sub-type"),
    ("plausible — confirm", "G. ⚠️ 'Plausible' — THIS TIER IS NOT SAFE", "verify against the terminology"),
]

def sha(condition, top):
    return hashlib.sha256(f"{condition}|{top}".encode("utf-8")).hexdigest()[:8]

def parse_decision(cell):
    """-> (kind, concept_id, who) ; kind in bind/reject/defer/open"""
    c = cell.strip()
    if not c:
        return ("open", None, "")
    if c.startswith("!"):
        return ("reject", None, c[1:].strip())
    if c.startswith("?"):
        return ("defer", None, c[1:].strip())
    m = re.match(r"^(\d{6,18})\s+(.*)$", c)
    if m:
        return ("bind", m.group(1), m.group(2).strip())
    return ("defer", None, c)      # unrecognised: never silently treated as a bind

def load_queue(path=QUEUE):
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("decision", "---"):
            continue
        dec, cond, s = cells[0], cells[1], cells[2].strip("`")
        if not dec or not cond:
            continue
        out[cond] = {"sha": s, **dict(zip(("kind", "concept_id", "who"), parse_decision(dec)))}
    return out

def tier_of(action):
    for key, title, todo in TIERS:
        if action.startswith(key):
            return title, todo
    return "H. Untriaged", "review"

DEV = "reference/quarantine_development.json"

def developed():
    """Alternatives found by develop_quarantined.mjs, keyed by condition."""
    if not os.path.exists(DEV):
        return {}
    return {r["condition"]: r for r in json.load(open(DEV))["results"]}

def build():
    rev = json.load(open(REVIEW))
    dev = developed()
    prior = load_queue()
    groups, kept, dropped = {}, 0, 0
    for c in rev["candidates"]:
        cond, top = c["condition"], (c.get("top_hit") or {})
        code = top.get("code", "")
        s = sha(cond, code)
        p = prior.get(cond)
        if p and p["sha"] == s:
            cell = {"bind": f"{p['concept_id']} {p['who']}", "reject": f"! {p['who']}",
                    "defer": f"? {p['who']}"}.get(p["kind"], "")
            kept += 1
        else:
            if p:
                dropped += 1          # candidate changed: decision returns to the queue
            cell = ""
        sig = c.get("signals") or {}
        flags = ", ".join(k for k in ("off_domain", "parents_unrelated", "parent_better", "narrower")
                          if sig.get(k)) or "—"
        if c.get("quarantine"):
            flags = "⚠️ QUARANTINED: " + c["quarantine"].get("reason", "") + (", " + flags if flags != "—" else "")
        d = dev.get(cond)
        if d:
            if d.get("conditionIsReproductive"):
                others = "⚠️ **STAYS QUARANTINED** — the condition itself is reproductive"
            elif d.get("clean_alternatives"):
                others = "**re-searched:** " + " · ".join(a.split("  [")[0] for a in d["clean_alternatives"][:2])
            else:
                others = "⚠️ re-searched, **no clean alternative**"
        parents = "; ".join(p.get("display", "") for p in (c.get("parents") or [])[:2]) or "—"
        others = len(c.get("other_hits") or [])
        title, todo = tier_of(c.get("suggested_action", ""))
        groups.setdefault((title, todo), []).append(
            f"| {cell} | {cond} | `{s}` | `{code}` {top.get('display','')} | {parents} | {flags} | {others} |")
    return rev, groups, kept, dropped

def write():
    rev, groups, kept, dropped = build()
    n = rev["count"]
    o = ["# SNOMED binding review queue\n",
     f"**{n} candidates at `snomed: null`.** Source `{REVIEW}`. Nothing here is bound.\n",
     "> ### ⚠️ THE 'PLAUSIBLE' TIER IS NOT SAFE",
     "> The review file's own warning: *\"Signals are LEXICAL triage, not verdicts. The 'plausible' tier",
     "> is NOT safe: of 16 quarantined pregnancy candidates reviewed by hand, **6 carried no flag at all",
     "> and every one was wrong**.\"* **Nothing is auto-bound.** Lexical agreement is not evidence — the",
     "> top hit for *Acute mania or mixed episodes* is *Progressive cavitating leukoencephalopathy*.\n",
     "> ### Write your decision in the first column",
     "> | you write | means | state written to `binding_corrections.json` |",
     "> |---|---|---|",
     "> | *(empty)* | not yet reviewed | — |",
     "> | `918591000168102 KL 2026-09-23` | **BIND** this concept | `corrected_pending_attestation` |",
     "> | `! KL 2026-09-23 <why>` | ⚠️ **REJECT** — must NOT bind | `rejected` |",
     "> | `? KL 2026-09-23 <note>` | deferred; stays in the queue | — |",
     ">",
     "> ⚠️ **Anything unrecognised is treated as DEFERRED, never as a bind.** A decision is matched on",
     "> condition **and `sha`** (condition + top-hit code) — if the candidate changes, the decision",
     "> returns to the queue rather than binding to a hit nobody saw.\n",
     "**Order is by what evidence settles, cheapest first.** Tiers A–C were derived from the SNOMED",
     "hierarchy — parents sharing no concept with the condition — **not** from string similarity.\n",
     f"**{kept} decided · {n - kept} outstanding.**"
     + (f" ⚠️ **{dropped} returned to the queue** — the candidate changed since the decision." if dropped else "") + "\n",
     "## Run order\n```bash\npython3 scripts/binding_review.py             # rewrite this file\n"
     "python3 scripts/binding_review.py --harvest  # -> reference/binding_corrections.json\n"
     "python3 scripts/apply_corrections.py         # -> reference/snomed_bindings.json\n```\n"]
    for (title, todo), rows in sorted(groups.items()):
        o += [f"\n## {title}\n", f"*{len(rows)} rows — {todo}.*\n",
              "| decision | condition | sha | top hit | its parents | flags | other hits |",
              "|---|---|---|---|---|---|---|"] + rows
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    open(QUEUE, "w", encoding="utf-8").write("\n".join(o) + "\n")
    print(f"{QUEUE}: {n} candidates, {kept} decided, {n - kept} outstanding"
          + (f", {dropped} returned" if dropped else ""))

def harvest():
    """Worksheet -> binding_corrections.json. apply_corrections.py does the rest."""
    rev = json.load(open(REVIEW))
    tops = {c["condition"]: (c.get("top_hit") or {}) for c in rev["candidates"]}
    doc = json.load(open(CORR))
    by = {c["condition"]: c for c in doc["corrections"]}
    added = 0
    for cond, d in load_queue().items():
        if d["kind"] == "bind":
            top = tops.get(cond, {})
            disp = top.get("display", "") if top.get("code") == d["concept_id"] else ""
            by[cond] = {"condition": cond, "state": "corrected_pending_attestation",
                        "concept_id": d["concept_id"], "display": disp,
                        "method": "manual_review_worksheet", "corrected_by": d["who"],
                        "corrected_utc": "2026-09-23"}
            added += 1
        elif d["kind"] == "reject":
            by[cond] = {"condition": cond, "state": "rejected", "why": d["who"],
                        "method": "manual_review_worksheet", "corrected_by": d["who"],
                        "corrected_utc": "2026-09-23"}
            added += 1
    doc["corrections"] = sorted(by.values(), key=lambda c: c["condition"])
    open(CORR, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{CORR}: {len(doc['corrections'])} correction(s) total, {added} from the worksheet")

def demo():
    assert parse_decision("") == ("open", None, "")
    assert parse_decision("918591000168102 KL 2026-09-23")[:2] == ("bind", "918591000168102")
    assert parse_decision("! KL wrong hierarchy")[0] == "reject"
    assert parse_decision("? KL unsure")[0] == "defer"
    assert parse_decision("probably 12345")[0] == "defer", "unrecognised must NEVER become a bind"
    assert parse_decision("yes")[0] == "defer"
    assert sha("A", "1") != sha("A", "2"), "changing the top hit must change the sha"
    print("binding_review.py self-check ok")

if __name__ == "__main__":
    if "--demo" in sys.argv: demo()
    elif "--harvest" in sys.argv: harvest()
    else: write()
