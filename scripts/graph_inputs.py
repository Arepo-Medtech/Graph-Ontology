#!/usr/bin/env python3
"""Every input the graph build needs, in one manifest -- and a copy of each in ~/Documents/ONTOLOGIES/graph-inputs, so that
the ONTOLOGIES folder plus this repository are enough to rebuild the graph on another machine.

Three kinds of input:
  in place   licensed releases read where they sit in ONTOLOGIES (SNOMED CT-AU, LOINC, the LOINC Extension, RadLex,
             RCPA, the RSNA playbook, the Athena bundle)
  stored     everything the build reads from this repo's git-ignored cache/ and out/, and from the spine project: copied
             into ONTOLOGIES/graph-inputs/ under the same relative path. It includes the hand-check verdict files the
             tiers are earned from, which are irreplaceable.
  unzipped   Athena's CONCEPT / CONCEPT_RELATIONSHIP / CONCEPT_ANCESTOR, identical to the Athena zip in ONTOLOGIES
             (byte for byte), so they are unzipped on restore rather than stored twice.

    .venv/bin/python scripts/graph_inputs.py export    # copy the stored inputs into ONTOLOGIES/graph-inputs, hash everything,
                                                       # write the manifest there and to reference/graph_inputs_manifest.json
    .venv/bin/python scripts/graph_inputs.py restore   # on a fresh checkout: link every missing stored input from
                                                       # ONTOLOGIES/graph-inputs (--copy to copy), unzip the Athena files
    .venv/bin/python scripts/graph_inputs.py check     # every input present where the build reads it? exits 1 if not
                                                       # (--full: also sha256 against the manifest; --store: check the
                                                       # ONTOLOGIES copy instead)

ONTOLOGIES defaults to ~/Documents/ONTOLOGIES (env ONTOLOGIES). Licensed content in graph-inputs stays under its licences:
it is for the licence holder's own machines, not for redistribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ONT = Path(os.environ.get("ONTOLOGIES", os.path.expanduser("~/Documents/ONTOLOGIES")))
STORE = ONT / "graph-inputs"
SPINE_HOME = Path(os.path.expanduser("~/code/spine/out"))
MANIFEST_REPO = REPO / "reference" / "graph_inputs_manifest.json"
ATHENA_ZIP = "vocabulary_download_v5_{484ac870-6e27-4b26-9d34-58594255a4f1}_1790035954856.zip"
ATHENA_FILES = ("CONCEPT.csv", "CONCEPT_RELATIONSHIP.csv", "CONCEPT_ANCESTOR.csv")

# id, kind, path (repo-relative for stored; ONTOLOGIES-relative for in place), source, version, licence, keep (glob for dirs)
IN_PLACE = [
    ("snomed_ct_au", "SnomedCT_Release_AU1000036_20260831/Snapshot", "NCTS (healthterminologies.gov.au): NCTS_SCT_RF2_DISTRIBUTION_32506021000036107-20260831-ALL.zip",
     "SNOMED CT-AU 20260831", "SNOMED CT Affiliate + Australian National Terminology licence"),
    ("snomed_ct_au_zip", "NCTS_SCT_RF2_DISTRIBUTION_32506021000036107-20260831-ALL.zip", "NCTS", "20260831", "as above"),
    ("loinc", "Loinc_2.83", "https://loinc.org/downloads/ (account)", "LOINC 2.83", "LOINC licence"),
    ("loinc_extension", "SnomedCT_LOINCExtension_PRODUCTION_LO1010000_20260321T120000Z/Snapshot", "SNOMED International / NCTS",
     "LOINC Extension 20260321", "SNOMED CT + LOINC licences"),
    ("radlex", "PunRadLex_Owl4.3/RadLex.owl", "https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon", "RadLex 4.3", "RadLex licence (RSNA)"),
    ("rsna_playbook", "complete-playbook-dev.csv", "RSNA Radiology Playbook", "downloaded 24 Sep 2026", "RSNA"),
    ("rcpa_spia", "RCPA_v20260831", "NCTS: RCPA SPIA reference sets", "v20260831", "RCPA copyright (NCTS terms)"),
    ("athena_zip", ATHENA_ZIP, "https://athena.ohdsi.org (bundle requested 22 Sep 2026)", "Athena v5.0 29-AUG-26", "per vocabulary (OHDSI Athena)"),
]
STORED = [
    ("compendium", "out/compendium.duckdb", "scripts/build_compendium.py (SNOMED CT-AU, AMT, PBS, RxNav, OMOPHub)", "built 24 Sep 2026", "derived"),
    ("spine", "spine/spine.duckdb", "~/code/spine (spine ingest; Athena)", "spine main", "derived"),
    ("pbs", "cache/pbs", "https://data-api.health.gov.au/pbs/api/v3", "PBS schedule 4333", "Commonwealth of Australia"),
    ("mondo", "cache/mondo", "https://github.com/monarch-initiative/mondo/releases (mondo.obo, mondo.sssom.tsv)", "v2026-09-01", "CC BY 4.0"),
    ("hpo", "cache/hpo", "https://github.com/obophenotype/human-phenotype-ontology/releases (hp.obo, phenotype.hpoa, genes_to_disease.txt)",
     "v2026-09-01 / 2026-09-02", "HPO licence (free with attribution)"),
    ("mbs", "cache/mbs", "https://www.mbsonline.gov.au (MBS-XML-20260801.XML)", "20260801", "Commonwealth of Australia"),
    ("uberon", "cache/uberon", "https://github.com/obophenotype/uberon/releases (uberon-basic.obo, uberon.sssom.tsv)", "v2026-06-23", "CC BY 3.0"),
    ("drugcentral", "cache/drugcentral", "https://drugcentral.org/download (drugcentral.dump.11012023.sql.gz, 1.40 GB -- not stored; "
     "scripts/drugcentral_extract.py makes the .tsv tables)", "2023-11-01", "CC BY-SA 4.0", "*.tsv"),
    ("chembl_witness", "cache/chembl", "scripts/chembl_moa_witness.py (ChEMBL API)", "ChEMBL, 23 Sep 2026", "CC BY-SA 3.0"),
    ("radlex_derived", "cache/radlex", "scripts/radlex_prepare.py from RadLex.owl", "RadLex 4.3", "RadLex licence: labels only"),
    ("rcpa_derived", "cache/rcpa", "scripts/rcpa_units.py from RCPA_v20260831", "v20260831", "RCPA copyright: derived data"),
    ("umls_derived", "cache/umls", "UMLS 2026AA via UTS with the licence holder's key (.env UMLS_API_KEY): scripts/umls_mrconso.py, "
     "umls_mrrel.py, umls_crosswalk.py; the raw zips (2.4 GB) are not stored -- re-download with the key", "UMLS 2026AA",
     "UMLS licence: the licence holder's own use", "!2026AA/*.zip"),
    ("hgnc", "cache/hgnc", "https://www.genenames.org/download/archive/ (hgnc_complete_set.txt)", "2026-09-24", "CC0"),
    ("orphanet", "cache/orphanet", "https://www.orphadata.com/data/xml/ (en_product1.xml, en_product4.xml, en_product6.xml)", "2026-06-23", "CC BY 4.0"),
    ("reactome", "cache/reactome", "https://reactome.org/download-data (UniProt2Reactome, ReactomePathways, ReactomePathwaysRelation)", "v97", "CC0"),
    ("who_icd11", "cache/who-icd11", "WHO ICD-11 2026-01 release: mapping tables (mapping.zip)", "2026-01", "CC BY-ND 3.0 IGO"),
    ("snomed_us_maps", "cache/snomed-us", "https://download.nlm.nih.gov/mlb/utsauth/USExt/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20260901T120000Z.zip "
     "(661 MB, UTS key; not stored) -> scripts/snomed_us_maps.py", "US Edition 20260901", "UMLS + SNOMED affiliate licence", "*.parquet"),
    ("completeness_evidence", "cache/completeness", "scripts/completeness.py --refresh-evidence (from SeMRA Zenodo 15208251 + UMLS pairs)",
     "24 Sep 2026", "derived (UMLS licence)"),
    ("consistency_handcheck", "cache/consistency", "hand checks, 24 Sep 2026", "-", "derived"),
]


def build_path(eid: str, rel: str) -> Path:
    """Where the build reads a stored input on this machine."""
    if eid == "spine":
        return SPINE_HOME / "spine.duckdb" if (SPINE_HOME / "spine.duckdb").exists() else REPO / "out" / "spine.duckdb"
    return REPO / rel


def files(path: Path, keep: str | None) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    out = [p for p in sorted(path.rglob("*")) if p.is_file() and p.name != ".DS_Store"]
    if keep and keep.startswith("!"):
        out = [p for p in out if not p.match(keep[1:]) and not p.relative_to(path).match(keep[1:])]
    elif keep:
        out = [p for p in out if p.match(keep)]
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def export(a) -> int:
    t0 = time.time()
    STORE.mkdir(parents=True, exist_ok=True)
    entries = []
    for eid, rel, src, ver, lic, *keep in STORED:
        keep = keep[0] if keep else None
        base = build_path(eid, rel)
        dest_root = STORE / rel
        fl = files(base, keep)
        if not fl:
            print(f"  MISSING at source: {eid} {base}", file=sys.stderr)
        rows = []
        for p in fl:
            rp = p.relative_to(base) if base.is_dir() else Path(p.name)
            d = dest_root / rp if base.is_dir() else dest_root
            d.parent.mkdir(parents=True, exist_ok=True)
            if not d.exists() or d.stat().st_size != p.stat().st_size or d.stat().st_mtime < p.stat().st_mtime:
                shutil.copy2(p, d)
            rows.append({"file": str(rp), "bytes": p.stat().st_size, "sha256": sha256(p)})
        entries.append({"id": eid, "kind": "stored", "path": rel, "is_dir": base.is_dir(), "keep": keep, "source": src, "version": ver,
                        "licence": lic, "files": rows, "bytes": sum(r["bytes"] for r in rows)})
        print(f"  stored   {eid:<24} {len(rows):>4} files {sum(r['bytes'] for r in rows) / 1e6:>9.1f} MB", flush=True)
    for eid, rel, src, ver, lic in IN_PLACE:
        base = ONT / rel
        fl = files(base, None)
        rows = [{"file": str(p.relative_to(base)) if base.is_dir() else p.name, "bytes": p.stat().st_size,
                 "sha256": sha256(p) if not a.quick else None} for p in fl]
        entries.append({"id": eid, "kind": "in place", "path": rel, "is_dir": base.is_dir(), "source": src, "version": ver, "licence": lic,
                        "files": rows, "bytes": sum(r["bytes"] for r in rows)})
        print(f"  in place {eid:<24} {len(rows):>4} files {sum(r['bytes'] for r in rows) / 1e6:>9.1f} MB", flush=True)
    with zipfile.ZipFile(ONT / ATHENA_ZIP) as z:
        info = {i.filename: i.file_size for i in z.infolist()}
    entries.append({"id": "athena_vocabulary", "kind": "unzipped", "path": "~/code/spine/out/omop-vocab (or out/omop-vocab)",
                    "from": ATHENA_ZIP, "files": [{"file": f, "bytes": info.get(f)} for f in ATHENA_FILES],
                    "source": "the Athena zip above", "version": "Athena v5.0 29-AUG-26", "licence": "per vocabulary"})
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    man = {"_note": "Every input the graph build reads (scripts/graph_inputs.py). With ~/Documents/ONTOLOGIES (including graph-inputs/) "
                    "and the repository, the graph rebuilds: graph_inputs.py restore, then scripts/rebuild.sh.",
           "written": time.strftime("%Y-%m-%d %H:%M"), "repo_commit": commit, "ontologies": str(ONT),
           "not_needed_to_build": {".env UMLS_API_KEY": "only to re-download UMLS or the SNOMED US Edition",
                                   "cache/semra (1 GB)": "only to rebuild cache/completeness/evidence.parquet (Zenodo 15208251)",
                                   "DrugCentral SQL dump (1.4 GB)": "only to re-extract cache/drugcentral/*.tsv",
                                   "UMLS and SNOMED US zips (3.1 GB)": "only to re-derive cache/umls and cache/snomed-us"},
           "totals": {k: sum(e.get("bytes") or 0 for e in entries if e["kind"] == k) for k in ("stored", "in place")},
           "entries": entries}
    for dest in (STORE / "MANIFEST.json", MANIFEST_REPO):
        dest.write_text(json.dumps(man, indent=1) + "\n")
    (STORE / "README.md").write_text(README.format(commit=commit, written=man["written"],
                                                   stored=man["totals"]["stored"] / 1e9, inplace=man["totals"]["in place"] / 1e9))
    print(f"manifest: {MANIFEST_REPO} and {STORE / 'MANIFEST.json'} ({round(time.time() - t0)} s); "
          f"stored {man['totals']['stored'] / 1e9:.2f} GB, in place {man['totals']['in place'] / 1e9:.2f} GB")
    return 0


def restore(a) -> int:
    man = json.load(open(STORE / "MANIFEST.json"))
    n = 0
    for e in man["entries"]:
        if e["kind"] != "stored":
            continue
        target = build_path(e["id"], e["path"]) if e["id"] != "spine" else (SPINE_HOME / "spine.duckdb" if (SPINE_HOME / "spine.duckdb").exists()
                                                                           else REPO / "out" / "spine.duckdb")
        for r in e["files"]:
            src = STORE / e["path"] / r["file"] if e["is_dir"] else STORE / e["path"]
            dst = target / r["file"] if e["is_dir"] else target
            if dst.exists() or dst.is_symlink():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if a.copy:
                shutil.copy2(src, dst)
            else:
                dst.symlink_to(src)
            n += 1
    vocab = SPINE_HOME / "omop-vocab" if (SPINE_HOME / "omop-vocab" / "CONCEPT.csv").exists() else REPO / "out" / "omop-vocab"
    with zipfile.ZipFile(ONT / ATHENA_ZIP) as z:
        for f in ATHENA_FILES:
            if not (vocab / f).exists():
                vocab.mkdir(parents=True, exist_ok=True)
                print(f"  unzipping {f} -> {vocab}", flush=True)
                z.extract(f, vocab)
    print(f"restore: {n} file(s) {'copied' if a.copy else 'linked'} from {STORE}; Athena vocabulary at {vocab}")
    return check(argparse.Namespace(full=False, store=False))


def check(a) -> int:
    man = json.load(open(MANIFEST_REPO if MANIFEST_REPO.exists() else STORE / "MANIFEST.json"))
    missing, differ = [], []
    for e in man["entries"]:
        if e["kind"] == "unzipped":
            vocab = SPINE_HOME / "omop-vocab" if (SPINE_HOME / "omop-vocab" / "CONCEPT.csv").exists() else REPO / "out" / "omop-vocab"
            for r in e["files"]:
                p = vocab / r["file"]
                if not p.exists():
                    missing.append(f"athena_vocabulary: {p} (graph_inputs.py restore unzips it from ONTOLOGIES)")
                elif r["bytes"] and p.stat().st_size != r["bytes"]:
                    differ.append(f"athena_vocabulary: {p} size differs from the Athena zip")
            continue
        if a.store and e["kind"] == "stored":
            root = STORE / e["path"]
        elif e["kind"] == "stored":
            root = build_path(e["id"], e["path"])
        else:
            root = ONT / e["path"]
        for r in e["files"]:
            p = root / r["file"] if e["is_dir"] else root
            if not p.exists():
                missing.append(f"{e['id']}: {p}")
            elif p.stat().st_size != r["bytes"]:
                differ.append(f"{e['id']}: {p} ({r['bytes']:,} -> {p.stat().st_size:,} bytes)")
            elif a.full and r.get("sha256") and sha256(p) != r["sha256"]:
                differ.append(f"{e['id']}: {p} (content differs)")
    where = "ONTOLOGIES/graph-inputs" if a.store else "where the build reads them"
    for m in missing:
        print("  MISSING " + m, file=sys.stderr)
    for d in differ:
        print("  CHANGED " + d)
    n = sum(len(e["files"]) for e in man["entries"])
    if missing:
        print(f"inputs: {len(missing)} of {n} missing {where} -- run scripts/graph_inputs.py restore (or re-export)", file=sys.stderr)
        return 1
    print(f"inputs: all {n} present {where}" + (f"; {len(differ)} changed since the manifest (run export to refresh the copy)" if differ else ""))
    return 0


README = """# graph-inputs: what the medical multigraph build needs, beyond the licensed releases in this folder

Written {written} by `scripts/graph_inputs.py export` (repository commit {commit}). `MANIFEST.json` lists every input,
its source, version, licence, size and sha256.

This folder (~{stored:.1f} GB) holds the inputs the build reads from the repository's git-ignored `cache/` and `out/`, and
from the spine project, under the same relative paths -- including the hand-check verdict files the tiers are earned
from. The licensed releases the build reads in place (~{inplace:.1f} GB: SNOMED CT-AU, LOINC, the LOINC Extension, RadLex,
RCPA, the RSNA playbook, the Athena bundle) sit beside it in the ONTOLOGIES folder.

## Rebuilding on another machine

    git clone https://github.com/Arepo-Medtech/Graph-Ontology.git && cd Graph-Ontology
    python3 -m venv .venv && .venv/bin/pip install duckdb
    # unzip the ONTOLOGIES archive to ~/Documents/ONTOLOGIES (or set ONTOLOGIES=/path)
    .venv/bin/python scripts/graph_inputs.py restore     # links cache/, out/compendium.duckdb, the spine db; unzips Athena
    scripts/rebuild.sh                                   # build + every guard (~10 min)

`restore --copy` copies instead of linking. The UMLS key (`.env UMLS_API_KEY`) is not needed to build -- only to
re-download UMLS or the SNOMED US Edition. Licensed content here is for the licence holder's own machines, not for
redistribution.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--quick", action="store_true", help="skip hashing the in-place releases")
    r = sub.add_parser("restore")
    r.add_argument("--copy", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--full", action="store_true")
    c.add_argument("--store", action="store_true")
    a = ap.parse_args()
    return {"export": export, "restore": restore, "check": check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
