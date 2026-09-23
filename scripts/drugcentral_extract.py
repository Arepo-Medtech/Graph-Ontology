#!/usr/bin/env python3
"""Pull the few DrugCentral tables the graph needs out of its PostgreSQL dump, without Postgres.

DrugCentral publishes only a full plain-SQL dump (drugcentral.dump.11012023.sql.gz, 1.40 GB). Its indications and its
RxNorm identifiers are in no separate file. A plain dump stores each table as `COPY <table> (<columns>) FROM stdin;`
followed by one tab-separated row per line and a `\\.` terminator, so the needed tables can be read by streaming the
gzip once -- nothing is decompressed to disk and no database server is needed. The disk this runs on was 91% full.

Kept, as TSV under cache/drugcentral/ (git-ignored):

    identifier         struct_id -> external id (RXNORM, SNOMEDCT_US, UNII, ...)
    struct2atc         struct_id -> ATC code
    omop_relationship  struct_id -> condition: indication / contraindication / off-label use, with SNOMED and UMLS ids
    structures         id and name only (the molfile column is dropped -- it is most of the table's size)
    act_table_full     struct_id -> target: activity (Ki, IC50 ...), mechanism-of-action flag, action type, organism, sources
    target_dictionary  target id, name, class (a target may be a complex of several proteins)
    target_component   protein: UniProt accession, gene symbol, NCBI gene id, organism
    td2tc              target -> its protein components
    reference          id, PMID, DOI, URL, title -- what act_ref_id / moa_ref_id point at, for the source trace

    scripts/drugcentral_extract.py [--dump cache/drugcentral/drugcentral.dump.11012023.sql.gz]
"""
from __future__ import annotations

import argparse
import gzip
import re
import sys
from pathlib import Path

OUT = Path("cache/drugcentral")
KEEP = {"identifier": None, "struct2atc": None, "omop_relationship": None, "structures": ["id", "name"],
        "act_table_full": None, "target_dictionary": None, "target_component": None, "td2tc": None,
        "reference": ["id", "pmid", "doi", "url", "title"]}
COPY = re.compile(r"^COPY (?:public\.)?(\w+) \(([^)]*)\) FROM stdin;$")


def unescape(v: str) -> str:
    """COPY text format: \\N is NULL; \\t \\n \\\\ are escapes. Write NULL as empty and keep one line per row."""
    if v == r"\N":
        return ""
    return v.replace("\\t", " ").replace("\\n", " ").replace("\\r", " ").replace("\\\\", "\\")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", default=str(OUT / "drugcentral.dump.11012023.sql.gz"))
    a = ap.parse_args()
    table = writer = idx = None
    counts = {}
    with gzip.open(a.dump, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if table is None:
                m = COPY.match(line.rstrip("\n"))
                if m and m.group(1) in KEEP:
                    table = m.group(1)
                    cols = [c.strip().strip('"') for c in m.group(2).split(",")]
                    want = KEEP[table] or cols
                    idx = [cols.index(c) for c in want]
                    writer = open(OUT / f"{table}.tsv", "w", encoding="utf-8")
                    writer.write("\t".join(want) + "\n")
                    counts[table] = 0
                continue
            if line.startswith("\\."):
                writer.close()
                print(f"  {table:<20} {counts[table]:>9,} rows", flush=True)
                table = writer = None
                if len(counts) == len(KEEP):
                    break
                continue
            parts = line.rstrip("\n").split("\t")
            writer.write("\t".join(unescape(parts[i]) if i < len(parts) else "" for i in idx) + "\n")
            counts[table] += 1
    missing = set(KEEP) - set(counts)
    if missing:
        print(f"NOT FOUND in the dump: {sorted(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
