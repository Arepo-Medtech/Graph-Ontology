#!/usr/bin/env python3
"""Cut a MedCAT v1 concept database (cdb.dat) down to the names that can occur in a set of texts, without loading it.

The UMLS self-trained MedCAT pack (cdb.dat 3.9 GB, a dill pickle) needs several times its size in memory to load; this
Mac has 8 GB. MedCAT's recognition and linking on a text touch only the names whose every token occurs in that text,
the candidate concepts of those names, and those concepts' context vectors -- so a database holding just those behaves
the same on those texts. This streams the pickle once with the pure-Python unpickler, keeps what the texts can reach,
drops the rest as it goes (including from the unpickler's memo, which would otherwise hold everything), and writes a
small cdb.dat that MedCAT's own legacy converter loads.

    cache/medcat/venv/bin/python scripts/medcat_subset.py --texts T.txt --out cache/medcat/subset_pbs   # ~10 min

UMLS-derived: everything stays in cache/medcat/ (git-ignored), not redistributed.
"""
from __future__ import annotations

import argparse
import dill
import json
import pickle
import re
import shutil
import sys
import time
from pathlib import Path

PACK = Path("cache/medcat/umls_self_train_model_pt2ch_3760d588371755d0")
CUI = re.compile(r"^C\d{7}$")
IDENT = re.compile(r"^[A-Za-z_][\w.]{0,60}$")          # module and class names the pickle refers back to
NAME_SECTIONS = {"name2cuis", "name2cuis2status", "name2count_train", "name_isupper"}


class Dropped:
    """Stands in for anything the texts cannot reach; counted if a kept structure ever refers to it."""
    hits = 0


DROPPED = Dropped()
import numpy as np


def bulky(x) -> bool:
    """Built per entry and never referred to again: safe to forget once its batch is filtered. Small constants the
    pickler shares across entries (a shape (0,), a dtype code b'b', the dtype itself) are kept."""
    if isinstance(x, (np.ndarray, dict, list, set)):
        return True
    if isinstance(x, (bytes, bytearray)):
        return len(x) > 64
    return isinstance(x, tuple) and len(x) >= 4


def variants(tok: str) -> set[str]:
    out = {tok}
    for suf, rep in (("ies", "y"), ("es", ""), ("s", ""), ("ae", "a"), ("ing", ""), ("ed", ""), ("ic", "")):
        if tok.endswith(suf) and len(tok) > len(suf) + 2:
            out.add(tok[: -len(suf)] + rep)
    return out


class Subsetter(pickle._Unpickler):
    def __init__(self, f, tokens: set[str], sep: str = "~"):
        super().__init__(f)
        self.tokens, self.sep = tokens, sep
        self.n = 0                      # memo index counter (entries not stored still take an index)
        self.batch_from: dict[int, int] = {}   # id(section dict) -> first memo index of its current batch
        self.cuis: set[str] = set()
        self.kept: dict[str, int] = {}
        self.seen: dict[str, int] = {}
        self.dispatch = dict(pickle._Unpickler.dispatch)
        for op, fn in ((pickle.MEMOIZE, Subsetter.load_memoize), (pickle.BINPUT, Subsetter.load_binput),
                       (pickle.LONG_BINPUT, Subsetter.load_long_binput), (pickle.BINGET, Subsetter.load_binget),
                       (pickle.LONG_BINGET, Subsetter.load_long_binget), (pickle.SETITEMS, Subsetter.load_setitems),
                       (pickle.SETITEM, Subsetter.load_setitem), (pickle.ADDITEMS, Subsetter.load_additems)):
            self.dispatch[op[0]] = fn

    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except (AttributeError, ModuleNotFoundError, ImportError):
            return type(name, (), {"__setstate__": lambda s, st: s.__dict__.update(st=st),
                                   "__init__": lambda s, *a, **k: None})

    # --- relevance -------------------------------------------------------------------------------------------------
    def relevant_name(self, s: str) -> bool:
        return all(t in self.tokens for t in s.split(self.sep) if t)

    # --- memo: a string is remembered only if something kept can refer to it (a concept id, a reachable name, or a
    #     short value such as a type id or status); containers are forgotten once their batch has been filtered -------
    def _put(self, idx: int, obj) -> None:
        if not isinstance(obj, str) or len(obj) <= 12 or CUI.match(obj) or IDENT.match(obj) or self.relevant_name(obj):
            self.memo[idx] = obj
        if isinstance(obj, (dict, set)) and self.filtered(self.section()):
            self.batch_from[id(obj)] = idx + 1          # a section starts: its first batch begins after it

    def load_memoize(self):
        self._put(self.n, self.stack[-1])
        self.n += 1

    def load_binput(self):
        i = self.read(1)[0]
        self._put(i, self.stack[-1])
        self.n = max(self.n, i + 1)

    def load_long_binput(self):
        i, = pickle.unpack("<I", self.read(4))
        self._put(i, self.stack[-1])
        self.n = max(self.n, i + 1)

    def load_binget(self):
        self.append(self.memo.get(self.read(1)[0], DROPPED))

    def load_long_binget(self):
        i, = pickle.unpack("<I", self.read(4))
        self.append(self.memo.get(i, DROPPED))

    def forget_batch(self, d) -> None:
        lo = self.batch_from.get(id(d), self.n)
        for i in range(lo, self.n):
            if bulky(self.memo.get(i)):
                del self.memo[i]
        self.batch_from[id(d)] = self.n

    # --- the filter, applied as each batch of up to 1,000 items is added to a section --------------------------------
    def section(self):
        return self.stack[-2] if len(self.stack) >= 2 and isinstance(self.stack[-2], str) else None

    def filtered(self, sec) -> bool:
        return sec is not None and (sec in NAME_SECTIONS or sec.startswith("cui2"))

    def add(self, d, sec, k, v) -> None:
        if self.filtered(sec):
            self.seen[sec] = self.seen.get(sec, 0) + 1
            if sec in NAME_SECTIONS:
                ok = isinstance(k, str) and self.relevant_name(k)
            else:
                ok = k in self.cuis
            if not ok:
                return
            self.kept[sec] = self.kept.get(sec, 0) + 1
            if sec == "name2cuis":
                self.cuis.update(c for c in v if isinstance(c, str))
            if v is DROPPED:
                Dropped.hits += 1
        d[k] = v

    def load_setitems(self):
        items = self.pop_mark()
        d, sec = self.stack[-1], self.section()
        for i in range(0, len(items), 2):
            self.add(d, sec, items[i], items[i + 1])
        if self.filtered(sec):
            self.forget_batch(d)

    def load_setitem(self):
        v = self.stack.pop()
        k = self.stack.pop()
        d, sec = self.stack[-1], self.section()
        self.add(d, sec, k, v)

    def load_additems(self):
        items = self.pop_mark()
        s, sec = self.stack[-1], self.section()
        if sec == "snames":
            self.seen[sec] = self.seen.get(sec, 0) + len(items)
            items = [x for x in items if isinstance(x, str) and self.relevant_name(x)]
            self.kept[sec] = self.kept.get(sec, 0) + len(items)
        items = [x for x in items if x is not DROPPED]
        if isinstance(s, set):
            s.update(items)
        else:
            for x in items:
                s.add(x)


def clean(x):
    """Drop stand-ins left inside kept sets and lists (names of a kept concept that no text can reach)."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items() if k is not DROPPED}
    if isinstance(x, set):
        return {v for v in x if v is not DROPPED}
    if isinstance(x, list):
        return [clean(v) for v in x if v is not DROPPED]
    return x


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--texts", required=True, help="one text per line")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    toks = set()
    for line in open(a.texts, encoding="utf-8"):
        for t in re.findall(r"[a-z0-9]+|[^a-z0-9\s]", line.lower()):
            toks |= variants(t)
    t0 = time.time()
    with open(PACK / "cdb.dat", "rb") as f:
        u = Subsetter(f, toks)
        data = u.load()
    data = {"config": data["config"], "cdb": clean(data["cdb"])}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "cdb.dat", "wb") as f:
        dill.dump(data, f, protocol=4)         # dill: the config holds a pickled function and stand-in classes
    shutil.copy(PACK / "vocab.dat", out / "vocab.dat")
    rep = {"text_tokens": len(toks), "seconds": round(time.time() - t0), "concepts_kept": len(u.cuis),
           "entries_seen": u.seen, "entries_kept": u.kept, "dangling_refs_in_kept": Dropped.hits,
           "subset_bytes": (out / "cdb.dat").stat().st_size}
    json.dump(rep, open(out / "subset_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
