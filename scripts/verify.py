#!/usr/bin/env python3
"""Check a guideline's verification.json.

Structural checks always run. With --source, every source_text fragment must
appear verbatim in the retrieved source file.

  python3 scripts/verify.py guidelines/stroke.verification.json --source /tmp/st.txt
  python3 scripts/verify.py guidelines/*.verification.json

Most guidelines cite several sources, and one retrieved file is only ever one
of them. --only-source limits the verbatim check to the claims attributed to
that source id, so a re-check against a single fetched page does not report
the other sources' claims as failures. Claims from the other sources are left
unchecked, and the count of skipped claims is printed rather than hidden.

  python3 scripts/verify.py guidelines/sepsis.verification.json \
      --source /tmp/sepsis.txt --only-source S1

Whitespace is collapsed on both sides before comparison, so line-wrapping
differences pass but paraphrase does not. This does NOT check that a claim
follows from its source_text -- that stays a human judgement, which is what
verifier_class: single_verifier_uncalibrated records.
"""
import json, re, sys

JOINER = " … "          # multi-fragment source_text separator
# The earliest guidelines wrote the same elision as three ASCII dots. Both mark
# "these passages are not contiguous in the source", so both must split, or a
# fragment either side of one gets compared as though it were continuous text.
ALT_JOINER = " ... "


def split_frags(s):
    out = []
    for part in s.split(JOINER):
        out.extend(part.split(ALT_JOINER))
    return out

# "pass" requires a verbatim quote. The rest record why no quote exists; they
# count toward total but not toward pass, which is the 6-claim gap in the totals.
VERDICTS = {"pass", "fail", "not_quoted", "not_asserted", "searched_not_found",
            "attested_not_sourced", "pass_image_transcription",
            "licensed_source_not_quoted"}

# "pass" means the quote was checked against RETRIEVED TEXT and can be re-checked
# here. "pass_image_transcription" means a human-or-model read it off a diagram:
# genuinely checked against the source, but NOT machine re-checkable, and subject
# to transcription error in a way text quotes are not. Doses read this way should
# be re-checked against the image by a person before use.
#
# "licensed_source_not_quoted" means the claim was read in a SUBSCRIBER source
# (AMH, Therapeutic Guidelines) and paraphrased. No source_text is stored, because
# storing the passage would redistribute licensed content. The claim therefore
# CANNOT be machine re-checked from this repository: it carries a locator (which
# topic, retrieved when) and must be verified by a person against their own
# subscription. It counts toward total and NOT toward pass.
#
# Do NOT attach a citation to one of these claims that was found afterwards to fit
# it. A claim read in AMH and cited to a PubMed paper located later records a
# provenance that did not happen, and the verbatim check would PASS while the
# attribution is false -- the one error this tool cannot see.

# Unicode punctuation the scrape and the JSON render differently. Folding these
# is an ENCODING normalisation: the words are identical either way.
PUNCT = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
         "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u00a0": " "}


def ws(s):
    for a, b in PUNCT.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def check(path, source=None, only_source=None):
    errs, notes = [], []
    d = json.load(open(path))

    for k in ("guideline", "verified_utc", "verifier", "verifier_class", "method",
              "claims", "summary"):
        if not d.get(k):
            errs.append(f"missing or empty top-level key: {k}")
    # Provenance is a note, not an error: the older files predate the field.
    # Without it a guideline cannot be re-verified, because nothing records
    # WHICH page was retrieved -- a citation names the work, not the fetch.
    if not d.get("retrieved_from"):
        notes.append("no retrieved_from: source cannot be re-fetched for "
                     "verification from this file alone")
    claims = d.get("claims") or []
    if not claims:
        return errs + ["no claims"], notes, 0

    seen = set()
    for i, c in enumerate(claims, 1):
        v = c.get("verdict")
        # A claim may legitimately carry no quote: the early guidelines record
        # WHY in the verdict itself. Only "pass" obliges a verbatim source_text.
        need = ("claim", "source", "verdict", "source_text") \
               if v in ("pass", "pass_image_transcription") \
               else ("claim", "source", "verdict")
        if v == "licensed_source_not_quoted":
            if (c.get("source_text") or "").strip():
                errs.append(f"claim {i}: licensed_source_not_quoted must NOT carry "
                            f"source_text (storing it redistributes licensed content)")
            if not (c.get("locator") or "").strip():
                errs.append(f"claim {i}: licensed_source_not_quoted requires a "
                            f"locator (which topic, retrieved when)")
        for k in need:
            if not (c.get(k) or "").strip():
                errs.append(f"claim {i}: missing or empty {k}")
        if v not in VERDICTS:
            errs.append(f"claim {i}: unknown verdict {v!r}")
        t = c.get("claim", "")
        if t in seen:
            errs.append(f"claim {i}: duplicate claim text")
        seen.add(t)

    s = d.get("summary") or {}
    npass = sum(1 for c in claims if c.get("verdict") == "pass")
    nfail = sum(1 for c in claims if c.get("verdict") == "fail")
    nimg = sum(1 for c in claims if c.get("verdict") == "pass_image_transcription")
    if nimg:
        notes.append(f"{nimg} claim(s) transcribed from a DIAGRAM - not machine "
                     f"re-checkable; verify doses against the image by eye")
    nlic = sum(1 for c in claims if c.get("verdict") == "licensed_source_not_quoted")
    if nlic:
        notes.append(f"{nlic} claim(s) read in a LICENSED source and paraphrased: "
                     f"not machine re-checkable here, verify against a subscription")
    # Doses are the highest-consequence claims. "dose" marks that a claim IS a dose;
    # it does NOT by itself mean unverifiable. Only the licensed ones need a person,
    # so only those go to the attestation queue -- the rest carry a verbatim quote
    # and are re-checkable here like any other claim. Reporting both counts keeps
    # the difference visible: until an open source supplied one, every dose in this
    # corpus was licensed, and "dose" and "unverifiable" were the same set by
    # accident rather than by definition.
    ndose = sum(1 for c in claims
                if c.get("dose") and c.get("verdict") == "licensed_source_not_quoted")
    if ndose:
        notes.append(f"ATTESTATION QUEUE: {ndose} DOSE claim(s) from a licensed source, "
                     f"unquoted - check each against the subscription before use")
    nqdose = sum(1 for c in claims if c.get("dose") and c.get("verdict") == "pass")
    if nqdose:
        notes.append(f"{nqdose} DOSE claim(s) QUOTED from an open source: re-checkable "
                     f"here, not in the attestation queue")
    nunq = sum(1 for c in claims
               if c.get("verdict") not in ("pass", "fail", "pass_image_transcription"))
    if nunq:
        notes.append(f"{nunq} claim(s) carry no quote by design: "
                     + ", ".join(sorted({c["verdict"] for c in claims
                                         if c.get("verdict") not in
                                         ("pass", "fail", "pass_image_transcription")})))
    if s.get("total") != len(claims):
        errs.append(f"summary.total {s.get('total')} != {len(claims)} claims")
    if s.get("pass") != npass:
        errs.append(f"summary.pass {s.get('pass')} != {npass}")
    if s.get("fail") != nfail:
        errs.append(f"summary.fail {s.get('fail')} != {nfail}")

    checked = skipped = 0
    if source:
        hay = ws(open(source, encoding="utf-8", errors="replace").read())
        for i, c in enumerate(claims, 1):
            if c.get("verdict") != "pass":
                continue
            if only_source and c.get("source") != only_source:
                skipped += 1
                continue
            for frag in split_frags(c.get("source_text", "")):
                frag = ws(frag)
                if not frag:
                    continue
                checked += 1
                pos = hay.find(frag)
                if pos < 0:
                    errs.append(f"claim {i}: source_text NOT VERBATIM: {frag[:90]!r}")
                    continue
                # A fragment that stops mid-word is still a substring, so the
                # plain check passes it. "the clinical concer" matched "...concern"
                # that way, hiding a lost letter. Require whole words at both ends.
                end = pos + len(frag)
                if frag[-1].isalnum() and end < len(hay) and hay[end].isalnum():
                    errs.append(f"claim {i}: fragment ENDS MID-WORD "
                                f"({frag[-24:]!r} + {hay[end:end+12]!r})")
                if frag[0].isalnum() and pos > 0 and hay[pos - 1].isalnum():
                    errs.append(f"claim {i}: fragment STARTS MID-WORD "
                                f"({hay[max(0,pos-12):pos]!r} + {frag[:24]!r})")
        if skipped:
            notes.append(f"{skipped} claim(s) NOT re-checked: they cite a source "
                         f"other than {only_source}")
    return errs, notes, checked


def main(argv):
    src = only = None
    if "--source" in argv:
        i = argv.index("--source")
        src = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if "--only-source" in argv:
        i = argv.index("--only-source")
        only = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__)
        return 2

    bad = 0
    for p in argv:
        errs, notes, n = check(p, src, only)
        name = p.rsplit("/", 1)[-1].replace(".verification.json", "")
        if errs:
            bad += 1
            print(f"FAIL  {name}")
            for e in errs[:20]:
                print(f"        {e}")
            if len(errs) > 20:
                print(f"        ... and {len(errs) - 20} more")
        else:
            tail = f"  ({n} fragments verbatim)" if src else ""
            print(f"ok    {name}{tail}")
        for nt in notes:
            print(f"        note: {nt}")
    print(f"\n{len(argv) - bad}/{len(argv)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
