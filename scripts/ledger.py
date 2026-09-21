#!/usr/bin/env python3
"""Append-only production ledger for the monograph foundry.

One JSONL line per ticket produced. Never rewritten, never reordered: the file
is the record of what was made, when, from what, and in which batch. Resumption
and batch selection both read from it, so the ledger is the only state.
"""
import json, datetime, pathlib

LEDGER = pathlib.Path("out/ledger.jsonl")

def read():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]

def done_conditions():
    return {r["condition"] for r in read() if r.get("state") != "failed"}

def next_batch(conditions, size):
    """Conditions not yet in the ledger, in source order, capped at size."""
    done = done_conditions()
    return [c for c in conditions if c["condition"] not in done][:size]

def next_batch_number():
    rows = read()
    return (max((r.get("batch", 0) for r in rows), default=0)) + 1

def append(record):
    with LEDGER.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

def record(condition, batch, spine_id, gate, state, attestations, error=None):
    append({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "batch": batch, "condition": condition, "spine_id": spine_id,
        "gate": gate, "state": state, "attestations": attestations,
        "error": error,
    })

def demo():
    global LEDGER
    import tempfile
    LEDGER = pathlib.Path(tempfile.mkdtemp()) / "l.jsonl"
    conds = [{"condition": f"C{i}"} for i in range(100)]
    assert next_batch_number() == 1
    b = next_batch(conds, 42)
    assert len(b) == 42 and b[0]["condition"] == "C0"
    for c in b:
        record(c["condition"], 1, "sha256:x", {"admitted": 1}, "drafted", [])
    assert len(read()) == 42
    assert next_batch_number() == 2
    b2 = next_batch(conds, 42)
    assert len(b2) == 42 and b2[0]["condition"] == "C42", "must not repeat done work"
    # a failure must be retried, not skipped
    record("C99", 2, None, {}, "failed", [], error="boom")
    assert "C99" not in done_conditions()
    assert any(x["condition"] == "C99" for x in next_batch(conds, 100))
    # tail of the list must not over-run
    for c in conds[42:]:
        record(c["condition"], 3, "sha256:y", {}, "drafted", [])
    assert next_batch(conds, 42) == []
    print("self-check ok")

if __name__ == "__main__":
    demo()
