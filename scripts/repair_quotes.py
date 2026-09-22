#!/usr/bin/env python3
"""Repair source_text fragments that were stored from a damaged rendering.

Some early guidelines were quoted from a scrape whose cleaning step consumed a
letter from words containing a doubled n ("planned" -> "pla ed", "scanning" ->
"sca ing"), and which carried markdown artifacts into the stored quote ("**",
bullet joins glued on as "n- "). Those strings are therefore NOT verbatim with
respect to the source document, even though the guideline prose reads correctly.

This tool does not guess the repair. For each fragment it locates the
corresponding span in a freshly retrieved copy of the SAME page and replaces the
stored fragment with what the page actually says. A fragment is only rewritten
when the alignment is unambiguous and close; anything else is reported and left
alone for a person to look at.

  python3 scripts/repair_quotes.py guidelines/stroke.verification.json \
      --source /tmp/rc_stroke.txt --only-source S1 [--write]

Without --write it prints the diff and changes nothing.
"""
import json, re, sys, difflib

JOINER = " … "
ALT_JOINER = " ... "
PUNCT = {"‘": "'", "’": "'", "“": '"', "”": '"',
         "–": "-", "—": "-", "−": "-", " ": " "}
MIN_RATIO = 0.93        # below this we do not trust the alignment
ANCHOR = 20             # letters of clean run used to find candidate positions


def ws(s):
    for a, b in PUNCT.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    """Letters and digits only, lowercased, with a map back to source indices."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
    return "".join(out), idx


def locate(frag, hay, hn, hidx):
    """Find frag's true span in hay. Returns (text, ratio) or (None, best)."""
    fn, _ = norm(frag)
    if len(fn) < 12:
        return None, 0.0
    best, best_r = None, 0.0
    # Anchor at many offsets: a single anchor can land on a damaged spot and
    # find nothing, which is why a fragment with several damage points scored
    # 0.00 rather than merely low.
    starts = list(range(0, max(1, len(fn) - ANCHOR), 12))[:24]
    for start in starts:
        a = fn[start:start + ANCHOR]
        if len(a) < 12:
            continue
        pos = -1
        while True:
            pos = hn.find(a, pos + 1)
            if pos < 0:
                break
            lo0 = max(0, pos - start - 12)
            hi0 = min(len(hn), lo0 + len(fn) + 40)
            cand_n = hn[lo0:hi0]
            sm = difflib.SequenceMatcher(None, fn, cand_n, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size > 2]
            if not blocks:
                continue
            # trim the window to exactly the aligned region, then re-score
            lo = lo0 + blocks[0].b
            hi = lo0 + blocks[-1].b + blocks[-1].size
            r = difflib.SequenceMatcher(None, fn, hn[lo:hi], autojunk=False).ratio()
            if r > best_r and hi > lo:
                best_r = r
                a, b = hidx[lo], hidx[hi - 1] + 1
                # hidx points at alphanumeric characters, so a span can begin or
                # end in the middle of a word. Grow outwards to whole words: a
                # fragment stopping mid-word is still a substring of the page and
                # would pass a naive check while being a truncated quote.
                while a > 0 and hay[a - 1].isalnum():
                    a -= 1
                while b < len(hay) and hay[b].isalnum():
                    b += 1
                best = hay[a:b]
    return (best, best_r) if best_r >= MIN_RATIO else (None, best_r)


def main(argv):
    src = only = None
    write = "--write" in argv
    argv = [a for a in argv if a != "--write"]
    for flag in ("--source", "--only-source"):
        if flag in argv:
            i = argv.index(flag)
            val = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
            if flag == "--source":
                src = val
            else:
                only = val
    if not argv or not src:
        print(__doc__)
        return 2

    hay = ws(open(src, encoding="utf-8", errors="replace").read())
    hn, hidx = norm(hay)
    path = argv[0]
    d = json.load(open(path))
    changed = skipped = ok = 0

    for i, c in enumerate(d.get("claims", []), 1):
        if c.get("verdict") != "pass":
            continue
        if only and c.get("source") != only:
            continue
        raw = c.get("source_text", "")
        alt = ALT_JOINER in raw and JOINER not in raw
        frags = []
        for part in raw.split(JOINER):
            frags.extend(part.split(ALT_JOINER))
        new = []
        touched = False
        for f in frags:
            fw = ws(f)
            if fw and fw in hay:
                # Already a substring -- but a fragment that begins or ends in
                # the middle of a word is a truncated quote that a substring
                # check cannot catch. Grow it to whole words.
                pos = hay.find(fw)
                a, b = pos, pos + len(fw)
                while a > 0 and hay[a - 1].isalnum() and hay[a].isalnum():
                    a -= 1
                while b < len(hay) and hay[b].isalnum() and hay[b - 1].isalnum():
                    b += 1
                if (a, b) != (pos, pos + len(fw)):
                    print(f"  claim {i}: completed truncated word(s)")
                    print(f"      was: {fw[:60]} … {fw[-40:]}")
                    print(f"      now: {hay[a:b][:60]} … {hay[a:b][-40:]}")
                    new.append(hay[a:b])
                    touched = True
                    changed += 1
                else:
                    new.append(f)
                    ok += 1
                continue
            true, r = locate(fw, hay, hn, hidx)
            if true is None:
                print(f"  claim {i}: NO CONFIDENT MATCH (best {r:.2f}) {fw[:70]!r}")
                new.append(f)
                skipped += 1
                continue
            print(f"  claim {i}: repaired (ratio {r:.2f})")
            print(f"      was: {fw[:110]}")
            print(f"      now: {ws(true)[:110]}")
            new.append(ws(true))
            touched = True
            changed += 1
        if touched:
            c["source_text"] = (ALT_JOINER if alt else JOINER).join(new)

    print(f"\n{path.rsplit('/',1)[-1]}: {ok} already verbatim, "
          f"{changed} repaired, {skipped} left for review")
    if write and changed:
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
        print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
