#!/usr/bin/env python3
"""Bridge HPO phenotypes (signs and symptoms) to SNOMED CT through UMLS, the one source that joins them.

hp.obo carries no SNOMED or UMLS cross-references, so without this HPO's 19,894 phenotypes reach SNOMED only through
their diseases. UMLS puts an HPO term and a SNOMED CT concept under one CUI when its editors judge them synonymous; the
UTS REST crosswalk returns, for an HPO id, the SNOMEDCT_US concepts sharing its CUI. A shared CUI is synonymy by UMLS
editors -- not a map maintained by HPO or by SNOMED International -- and the graph scores it as such
(graph_report.py: does the HPO hierarchy survive the crossing?).

The API key is read from .env (UMLS_API_KEY) or the environment and is never printed. It travels in the request URL, so
no URL is ever printed either. UMLS is licensed: the output stays in cache/umls/ (git-ignored) and is not redistributed.

Resumable: HPO ids already answered (hit or miss) are skipped on a re-run.

    scripts/umls_hpo_crosswalk.py [--workers 6] [--rate 12]     # ~20-30 min for all phenotypes
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path("cache/umls")
HITS, MISSES = OUT / "hpo_snomed.tsv", OUT / "hpo_snomed_misses.txt"
API = "https://uts-ws.nlm.nih.gov/rest/crosswalk/current/source/HPO/{}"


def api_key() -> str:
    key = os.environ.get("UMLS_API_KEY", "")
    env = Path(".env")
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("UMLS_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("UMLS_API_KEY not found in .env or the environment -- nothing fetched.")
    return key


def hp_ids() -> list[str]:
    ids, cur, obsolete = [], None, False
    for line in open("cache/hpo/hp.obo", encoding="utf-8"):
        line = line.rstrip("\n")
        if line == "[Term]":
            if cur and not obsolete:
                ids.append(cur)
            cur, obsolete = None, False
        elif line.startswith("id: HP:"):
            cur = line[4:]
        elif line == "is_obsolete: true":
            obsolete = True
    if cur and not obsolete:
        ids.append(cur)
    return ids


class Limiter:
    def __init__(self, per_second: float):
        self.gap, self.next, self.lock = 1.0 / per_second, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next)
            self.next = t + self.gap
        time.sleep(max(0.0, t - now))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--rate", type=float, default=12.0, help="requests per second, below NLM's 20/s limit")
    ap.add_argument("--limit", type=int, default=0, help="only the first N ids (a test run)")
    a = ap.parse_args()
    key = api_key()
    OUT.mkdir(parents=True, exist_ok=True)
    done = set()
    if HITS.exists():
        done |= {l.split("\t", 1)[0] for l in HITS.read_text().splitlines()[1:] if l}
    else:
        HITS.write_text("hpo_id\tsnomed_code\tsnomed_name\n")
    if MISSES.exists():
        done |= set(MISSES.read_text().split())
    todo = [i for i in hp_ids() if i not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"HPO phenotypes to fetch: {len(todo):,} (already answered: {len(done):,})", flush=True)
    lim, lock, stats = Limiter(a.rate), threading.Lock(), {"hit": 0, "miss": 0, "error": 0}

    def one(hid: str):
        url = API.format(urllib.parse.quote(hid)) + "?" + urllib.parse.urlencode({"targetSource": "SNOMEDCT_US", "apiKey": key})
        for attempt in range(4):
            lim.wait()
            try:
                d = json.load(urllib.request.urlopen(url, timeout=60))
                rows = [(hid, r.get("ui", ""), (r.get("name") or "").replace("\t", " ")) for r in d.get("result", [])]
                with lock:
                    if rows:
                        with open(HITS, "a") as fh:
                            fh.writelines("\t".join(x) + "\n" for x in rows)
                        stats["hit"] += 1
                    else:                               # an empty answer is still an answer: record it, or resume re-asks
                        with open(MISSES, "a") as fh:
                            fh.write(hid + "\n")
                        stats["miss"] += 1
                return
            except urllib.error.HTTPError as e:
                if e.code == 404:                       # UTS answers "no crosswalk" with 404
                    with lock:
                        with open(MISSES, "a") as fh:
                            fh.write(hid + "\n")
                        stats["miss"] += 1
                    return
                if e.code in (401, 403):
                    with lock:
                        stats["error"] += 1
                    raise SystemExit(f"UTS refused the key (HTTP {e.code}); stopping. The key itself is not shown.")
                time.sleep(2 ** attempt)
            except Exception:
                time.sleep(2 ** attempt)
        with lock:
            stats["error"] += 1

    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as pool:
        for i, _ in enumerate(pool.map(one, todo), 1):
            if i % 1000 == 0:
                print(f"  {i:,}/{len(todo):,}  {time.time() - t0:.0f}s  {stats}", flush=True)
    print(json.dumps({"fetched": len(todo), **stats, "seconds": round(time.time() - t0)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
