#!/usr/bin/env python3
"""Produce monograph tickets in batches, recording every one in the ledger.

    python3 run_batch.py            # next 42 unprocessed conditions
    python3 run_batch.py --size 10
    python3 run_batch.py --status   # ledger summary, no work

Resumable: batch membership is derived from the ledger, so an interrupted run
picks up where it stopped and a failed condition is retried rather than skipped.
"""
import argparse, json, re, sys, pathlib
from pathlib import Path
import foundry, ledger

CONDITIONS = pathlib.Path("out/conditions.json")
ATTESTATIONS = pathlib.Path("reference/attestations.json")

def load_attestations():
    if not ATTESTATIONS.exists():
        return []
    return json.loads(ATTESTATIONS.read_text())["attestations"]

def match_attestations(condition, atts):
    """Word-boundary match. A substring match on a short key is a false-positive
    generator: "uti" occurs inside "constitutional" and "therapeutic", which
    attached a nitrofurantoin renal attestation to growth delay and dietary
    management. Attestations are clinically load-bearing; they match whole words.
    """
    low = condition.lower()
    out = []
    for a in atts:
        for k in a.get("applies_to_conditions", []):
            if re.search(rf"\b{re.escape(k.lower())}\b", low):
                out.append(a["id"])
                break
    return out

def status():
    rows = ledger.read()
    total = len(json.loads(CONDITIONS.read_text())["conditions"])
    by_state = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    batches = sorted({r.get("batch") for r in rows})
    current = {c["condition"] for c in json.loads(CONDITIONS.read_text())["conditions"]}
    done_current = ledger.done_conditions() & current
    stale = ledger.done_conditions() - current
    print(f"conditions: {total}   ledger rows: {len(rows)}   "
          f"remaining: {total - len(done_current)}   stale ledger names: {len(stale)}")
    print(f"batches run: {batches or '-'}")
    for s, n in sorted(by_state.items()):
        print(f"  {n:5d}  {s}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=42)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--redo-tier", metavar="TIER",
                        help="requeue conditions whose ticket cites this query tier")
    parser.add_argument("--redo-zero", action="store_true",
                        help="requeue conditions whose latest draft drew 0 citations")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        atts = [{"id": "R1", "applies_to_conditions": ["urinary tract infection", "uti"]}]
        assert match_attestations("Urinary tract infection", atts) == ["R1"]
        assert match_attestations("Asthma", atts) == []
        # substring false positives that reached real tickets
        assert match_attestations("Constitutional delay of growth or puberty", atts) == []
        assert match_attestations("Dietary management of therapeutic diet", atts) == []
        assert match_attestations("Complicated urinary tract infection", atts) == ["R1"]
        print("self-check ok")
        return
    if args.status:
        status()
        return

    conditions = json.loads(CONDITIONS.read_text())["conditions"]
    atts = load_attestations()
    batch_no = ledger.next_batch_number()
    if args.redo_tier:
        import glob
        affected = set()
        for path in glob.glob("out/tickets/*.json"):
            tk = json.loads(Path(path).read_text())
            if any(b.get("query_tier") == args.redo_tier
                   for b in tk["body"].get("bibliography", [])):
                affected.add(tk["body"]["condition"])
        batch = [c for c in conditions if c["condition"] in affected][:args.size]
    elif args.redo_zero:
        latest = {}
        for row in ledger.read():
            latest[row["condition"]] = row
        zero = {c for c, row in latest.items()
                if row["state"] == "drafted" and row["gate"].get("admitted", 0) == 0
                and row["gate"].get("retrieval_version") != foundry.RETRIEVAL_VERSION}
        batch = [c for c in conditions if c["condition"] in zero][:args.size]
    else:
        batch = ledger.next_batch(conditions, args.size)
    if not batch:
        print("nothing left to process")
        return

    # Pre-flight: a systematic error should cost one condition, not the batch.
    try:
        foundry.build(batch[0])
    except Exception as e:
        sys.exit(f"pre-flight failed on {batch[0]['condition']!r}: {e}\n"
                 f"Nothing written to the ledger. Fix and re-run.")

    print(f"batch {batch_no}: {len(batch)} conditions", flush=True)
    ok = fail = 0
    for i, rec in enumerate(batch, 1):
        name = rec["condition"]
        matched = match_attestations(name, atts)
        try:
            _, spine = foundry.build(rec)
            gate = dict(spine["gate_summary"])
            gate["retrieval_version"] = spine.get("retrieval_version")
            gate["evidence_tiers"] = spine.get("evidence_tiers")
            ledger.record(name, batch_no, spine["spine_id"], gate, "drafted", matched)
            ok += 1
            flag = f" +{','.join(matched)}" if matched else ""
            print(f"  {i:3d}/{len(batch)}  {spine['gate_summary']['admitted']:2d} cites  {name[:52]}{flag}", flush=True)
        except Exception as e:
            ledger.record(name, batch_no, None, {}, "failed", matched, error=str(e)[:200])
            fail += 1
            print(f"  {i:3d}/{len(batch)}  FAILED  {name[:52]}: {e}", file=sys.stderr, flush=True)
    print(f"\nbatch {batch_no} complete: {ok} drafted, {fail} failed", flush=True)
    status()

if __name__ == "__main__":
    main()
