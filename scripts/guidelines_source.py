"""Where the guidelines live. They moved to their own repository, Arepo-Medtech/GUIDELINES (2026-09-23).

Resolution order:
  1. $GUIDELINES_DIR, pointing at that repository's guidelines/ folder;
  2. a sibling checkout, ../GUIDELINES/guidelines, next to this repository.
Links in generated docs point at the GitHub copy, since the files are no longer in this repository.
"""
import os

REPO_URL = "https://github.com/Arepo-Medtech/GUIDELINES"


def guidelines_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.environ.get("GUIDELINES_DIR") or os.path.join(here, "..", "..", "GUIDELINES", "guidelines")
    d = os.path.normpath(d)
    if not os.path.isdir(d):
        raise SystemExit(f"guidelines not found at {d}\n"
                         f"  clone {REPO_URL} next to this repository, or set GUIDELINES_DIR to its guidelines/ folder")
    return d


def verification_dir():
    """The <slug>.verification.json files. Split into their own folder beside guidelines/ on 2026-09-25 (GitHub lists at most
    1,000 files per folder); an older checkout that still keeps them in guidelines/ works too."""
    v = os.path.join(os.path.dirname(guidelines_dir()), "verification")
    return v if os.path.isdir(v) else guidelines_dir()


def guidelines_repo():
    """Root of the GUIDELINES checkout (the parent of its guidelines/ folder)."""
    return os.path.dirname(guidelines_dir())


def guidelines_file(rel):
    """A file that moved to GUIDELINES with the guidelines (e.g. reference/attestations.json). Fails loudly if absent."""
    p = os.path.join(guidelines_repo(), rel)
    if not os.path.exists(p):
        raise SystemExit(f"{rel} not found in the GUIDELINES checkout at {guidelines_repo()}")
    return p


def guideline_url(slug):
    return f"{REPO_URL}/blob/main/guidelines/{slug}.md"


if __name__ == "__main__":
    import glob, tempfile
    t = tempfile.mkdtemp(); os.environ["GUIDELINES_DIR"] = t
    assert guidelines_dir() == os.path.normpath(t)
    os.environ["GUIDELINES_DIR"] = os.path.join(t, "missing")
    try:
        guidelines_dir(); raise AssertionError("missing dir must exit")
    except SystemExit as e:
        assert "not found" in str(e)
    assert guideline_url("croup").endswith("/blob/main/guidelines/croup.md")
    os.makedirs(os.path.join(t, "g", "guidelines")); os.makedirs(os.path.join(t, "g", "reference"))
    open(os.path.join(t, "g", "reference", "x.json"), "w").write("{}")
    os.environ["GUIDELINES_DIR"] = os.path.join(t, "g", "guidelines")
    assert guidelines_file("reference/x.json").endswith("reference/x.json")
    assert verification_dir() == guidelines_dir()                       # old layout: JSON beside the .md files
    os.makedirs(os.path.join(t, "g", "verification"))
    assert verification_dir().endswith(os.path.join("g", "verification"))  # new layout
    try:
        guidelines_file("reference/absent.json"); raise AssertionError("absent file must exit")
    except SystemExit as e:
        assert "not found" in str(e)
    print("selftest ok")
