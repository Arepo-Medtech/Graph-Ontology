#!/usr/bin/env python3
"""A local review page for the Wave 2 hand-check sheets (cache/wave2/*_handcheck.json).

Every sampled pair with its names, the second path, and Claude's first reading; the reviewer marks each row correct,
wrong or unsure (or accepts a family's first readings in one click), notes a decision per family, and saves a
decisions file. The page embeds names from licensed sources (UMLS, SNOMED CT), so it is written to cache/wave2/
(git-ignored) and opened from disk -- never published.

    scripts/wave2_review_page.py              # writes cache/wave2/review.html; open it in a browser
    scripts/wave2_review_page.py --apply F    # take a saved decisions file into the sheets (reviewer, verdicts)
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

W2 = Path("cache/wave2")
OUT = W2 / "review.html"

# per family: title, what is asked, how to show a row (subject, target, context), and the row key
FAMILIES = {
    "umls_disease_member": {
        "title": "UMLS disease concept → OMIM / HPO / MeSH / NCIt",
        "ask": "Correct when the target code denotes the same disease as the concept MONDO or Orphanet names. HPO, MeSH and NCIt "
               "were confirmed on 27 Sep; OMIM is held (gene entries slip through: 7/30 on the first reading).",
        "key": lambda r: f"{r['cui']}|{r['target']}",
        "stratum": lambda r: r.get("v"),
        "subject": lambda r: (r.get("src", ""), r.get("src_name", "")),
        "target": lambda r: (r.get("target", ""), r.get("target_name") or r.get("target_pt") or ""),
        "context": lambda r: f"UMLS {r.get('cui', '')}; matched through {r.get('match_ttys') or '-'}; second path {r.get('second_path') or 'none'}",
    },
    "omim_title_census": {
        "title": "UMLS disease concept → OMIM, main-title matches (census of all 30)",
        "ask": "Correct when the OMIM entry is the same disease, not one inherited form of it. Proposal: accept the correct ones as "
               "individual decisions and drop the rest of UMLS → OMIM (alternative titles and phenotype atoms).",
        "key": lambda r: f"{r['cui']}|{r['target']}",
        "stratum": lambda r: None,
        "subject": lambda r: (r.get("src", ""), r.get("src_name", "")),
        "target": lambda r: (f"OMIM {r.get('target', '')}", r.get("target_pt") or ""),
        "context": lambda r: f"UMLS {r.get('cui', '')}; MONDO's own OMIM match {r.get('second_path') or 'none'}",
    },
    "unii_rxnorm": {
        "title": "UNII ↔ RxNorm ingredient",
        "ask": "Correct when the UNII substance and the RxNorm ingredient are the same substance. Family question: does an RxNorm "
               "'X extract' count as the same ingredient as the UNII for X?",
        "key": lambda r: f"{r['unii']}|{r['rxcui']}",
        "stratum": lambda r: None,
        "subject": lambda r: (r.get("unii", ""), r.get("su_name", "")),
        "target": lambda r: (f"RxCUI {r.get('rxcui', '')} ({r.get('tty', '')})", r.get("rx_name", "")),
        "context": lambda r: f"DrugCentral: RxCUIs for this UNII {r.get('dc_rxcuis_for_unii') or '-'}; UNIIs for this RxCUI {r.get('dc_uniis_for_rxcui') or '-'}",
    },
    "drug_pharma_role": {
        "title": "Drug → MeSH pharmacological action / ChEBI role",
        "ask": "Correct when the drug truly has that pharmacological action or role. Proposal: read ~60 more MeSH rows; drop the "
               "ChEBI half (ChEBI's own roles are now loaded).",
        "key": lambda r: f"{r['drug']}|{r['v']}|{r['code']}",
        "stratum": lambda r: r.get("stratum"),
        "subject": lambda r: (f"DrugCentral {r.get('drug', '')}", r.get("drug_name", "")),
        "target": lambda r: (f"{r.get('v', '')} {r.get('code', '')}", r.get("class_name", "")),
        "context": lambda r: f"FDA classes {r.get('fda_classes') or '-'}; ChEBI roles {r.get('chebi_roles') or '-'}",
    },
    "hpo_snomed_lifted": {
        "title": "HPO → SNOMED CT through a retired SNOMED code",
        "ask": "Correct when the active SNOMED concept the retired code now points to is the same phenotype. Proposal: hold.",
        "key": lambda r: f"{r['hpo_id']}|{r['sct']}",
        "stratum": lambda r: None,
        "subject": lambda r: (r.get("hpo_id", ""), r.get("hp_name", "")),
        "target": lambda r: (r.get("sct", ""), r.get("sct_fsn", "")),
        "context": lambda r: f"retired {r.get('old_code', '')} '{r.get('old_name', '')}' via {r.get('how', '')}; second path {r.get('sp_names') or r.get('sp_codes') or '-'}",
    },
    "chembl_moa_target": {
        "title": "ChEMBL mechanism: drug → protein target",
        "ask": "Correct when the drug acts on that protein as stated. Proposal: set a policy for complex and family targets first, "
               "then draw again.",
        "key": lambda r: f"{r['drug']}|{r['acc']}",
        "stratum": lambda r: None,
        "subject": lambda r: (f"DrugCentral {r.get('drug', '')}", r.get("drug_name", "")),
        "target": lambda r: (r.get("acc", ""), r.get("acc_gene", "")),
        "context": lambda r: f"{r.get('action_type') or ''} — {r.get('moa') or ''}; target of {r.get('target_size', '?')} proteins; DrugCentral genes {r.get('dc_moa_genes') or '-'}",
    },
}


def load() -> dict:
    data = {}
    for fam, spec in FAMILIES.items():
        p = W2 / f"{fam}_handcheck.json"
        if not p.exists():
            continue
        rows = []
        for r in json.load(open(p)).get("scored", []):
            s, t = spec["subject"](r), spec["target"](r)
            rows.append({"key": spec["key"](r), "sample": r.get("sample", ""), "stratum": spec["stratum"](r) or "",
                         "s_code": s[0], "s_name": s[1], "t_code": t[0], "t_name": t[1], "context": spec["context"](r),
                         "verdict": r.get("verdict", ""), "why": r.get("why", ""), "reviewer": r.get("reviewer", "")})
        data[fam] = {"title": spec["title"], "ask": spec["ask"], "rows": rows}
    return data


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wave 2 Review</title>
<style>
:root{--bg:#f4f6f6;--card:#fff;--ink:#18222b;--muted:#56636e;--rule:#d5dcdf;--soft:#e8eeef;--acc:#1f6f8b;
 --ok:#2f7d4f;--ok-s:#e0f1e6;--bad:#b3412f;--bad-s:#f7e1dc;--un:#9a6a12;--un-s:#f6ecd5;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#11171c;--card:#172027;--ink:#e3eaee;--muted:#9aa8b2;--rule:#2c3943;--soft:#1d2830;--acc:#6cb8d1;
 --ok:#7cc99a;--ok-s:#1b3326;--bad:#ee9a8a;--bad-s:#3a211c;--un:#e2b861;--un-s:#372b14;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px 80px}
.wrap{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
h1{margin:0;font-size:24px}h2{margin:0;font-size:18px}p{margin:0;max-width:80ch}.muted{color:var(--muted)}
.bar{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--rule)}
button,select{font:inherit;padding:6px 10px;border-radius:6px;border:1px solid var(--rule);background:var(--card);color:var(--ink);cursor:pointer}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}button:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
section{background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:16px;display:flex;flex-direction:column;gap:10px}
.fhead{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline}.tally{font-variant-numeric:tabular-nums;color:var(--muted)}
textarea{width:100%;min-height:52px;font:inherit;padding:8px;border-radius:6px;border:1px solid var(--rule);background:var(--bg);color:var(--ink)}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:980px}
th,td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--rule)}th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--soft)}
td.code{font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:nowrap}.ctx{color:var(--muted);font-size:12.5px}
.rd{font-size:12px;padding:2px 6px;border-radius:4px;white-space:nowrap}.rd.correct{background:var(--ok-s);color:var(--ok)}.rd.wrong{background:var(--bad-s);color:var(--bad)}.rd.unsure{background:var(--un-s);color:var(--un)}
.dec{display:flex;gap:4px}.dec label{display:flex;align-items:center;gap:3px;padding:3px 6px;border-radius:5px;border:1px solid var(--rule);cursor:pointer;font-size:12.5px}
.dec input{margin:0}.dec label.on-correct{background:var(--ok-s);border-color:var(--ok)}.dec label.on-wrong{background:var(--bad-s);border-color:var(--bad)}.dec label.on-unsure{background:var(--un-s);border-color:var(--un)}
tr.decided td{opacity:.75}
</style></head><body><div class="wrap">
<header style="display:flex;flex-direction:column;gap:6px"><h1>Wave 2 review</h1>
<p class="muted">Each row is a sampled pair with Claude's first reading. Mark each row, or accept a family's first readings in one click, and note a decision per family. Your marks are kept in this browser; <b>Save decisions</b> writes a file to hand back. Local file: it contains licensed UMLS and SNOMED names — do not share it.</p></header>
<div class="bar"><label>Show <select id="filter"><option value="all">all rows</option><option value="todo">not yet decided</option><option value="disagree">where I disagree with Claude</option></select></label>
<span id="count" class="tally"></span><span style="flex:1"></span><button id="save" class="primary">Save decisions</button><button id="clear">Clear my marks</button></div>
<div id="fams"></div></div>
<script>
const DATA = __DATA__;
const KEY = "wave2-review-v1";
let S = {};
try { S = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { S = {}; }
S.rows = S.rows || {}; S.notes = S.notes || {};
const put = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render() {
  const f = document.getElementById("filter").value, root = document.getElementById("fams"); root.innerHTML = "";
  let total = 0, done = 0;
  for (const [fam, d] of Object.entries(DATA)) {
    const sec = document.createElement("section");
    const marks = d.rows.map(r => S.rows[fam + "::" + r.key]); const n = marks.filter(Boolean).length; total += d.rows.length; done += n;
    const tally = {correct:0, wrong:0, unsure:0}; d.rows.forEach((r, i) => { const m = marks[i] || r.verdict; if (tally[m] !== undefined) tally[m]++; });
    sec.innerHTML = `<div class="fhead"><h2>${esc(d.title)}</h2><span class="tally">${n}/${d.rows.length} marked · counting your marks, else Claude's: ${tally.correct} correct, ${tally.wrong} wrong, ${tally.unsure} unsure</span>
      <button data-accept="${fam}">Accept Claude's readings for unmarked rows</button></div><p class="muted">${esc(d.ask)}</p>
      <label>Your decision for this family <textarea data-note="${fam}" placeholder="e.g. confirm / hold / 'X extract' counts as X / policy for complex targets …">${esc(S.notes[fam] || "")}</textarea></label>
      <div class="tbl"><table><thead><tr><th>#</th><th>Sample</th><th>Subject</th><th>Target</th><th>Context</th><th>Claude's reading</th><th>Your mark</th></tr></thead><tbody></tbody></table></div>`;
    const tb = sec.querySelector("tbody");
    d.rows.forEach((r, i) => {
      const k = fam + "::" + r.key, m = S.rows[k];
      if (f === "todo" && m) return; if (f === "disagree" && !(m && m !== r.verdict)) return;
      const tr = document.createElement("tr"); if (m) tr.className = "decided";
      tr.innerHTML = `<td>${i + 1}</td><td class="ctx">${esc(r.sample)}${r.stratum ? "<br>" + esc(r.stratum) : ""}</td>
        <td><span class="code">${esc(r.s_code)}</span><br>${esc(r.s_name)}</td><td><span class="code">${esc(r.t_code)}</span><br>${esc(r.t_name)}</td>
        <td class="ctx">${esc(r.context)}</td><td><span class="rd ${esc(r.verdict)}">${esc(r.verdict)}</span><div class="ctx">${esc(r.why)}</div></td>
        <td><div class="dec">${["correct","wrong","unsure"].map(v => `<label class="${m === v ? "on-" + v : ""}"><input type="radio" name="${esc(k)}" value="${v}" ${m === v ? "checked" : ""}>${v}</label>`).join("")}</div></td>`;
      tr.querySelectorAll("input").forEach(inp => inp.addEventListener("change", () => { S.rows[k] = inp.value; put(); render(); }));
      tb.appendChild(tr);
    });
    root.appendChild(sec);
  }
  document.querySelectorAll("[data-accept]").forEach(b => b.addEventListener("click", () => {
    const fam = b.dataset.accept; DATA[fam].rows.forEach(r => { const k = fam + "::" + r.key; if (!S.rows[k] && r.verdict) S.rows[k] = r.verdict; }); put(); render(); }));
  document.querySelectorAll("[data-note]").forEach(t => t.addEventListener("input", () => { S.notes[t.dataset.note] = t.value; put(); }));
  document.getElementById("count").textContent = `${done} of ${total} rows marked`;
}
document.getElementById("filter").addEventListener("change", render);
document.getElementById("clear").addEventListener("click", () => { S = {rows:{}, notes:{}}; put(); render(); });
document.getElementById("save").addEventListener("click", () => {
  const out = {reviewer: "Ken", saved: new Date().toISOString(), notes: S.notes, rows: Object.entries(S.rows).map(([k, v]) => { const [family, key] = k.split("::"); return {family, key, verdict: v}; })};
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type: "application/json"}));
  a.download = "wave2_decisions.json"; document.body.appendChild(a); a.click(); a.remove();
});
render();
</script></body></html>"""


def write_page() -> int:
    data = load()
    OUT.write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")), encoding="utf-8")
    print(f"{OUT}: {sum(len(d['rows']) for d in data.values())} rows in {len(data)} families -- open it in a browser")
    return 0


def apply(path: Path) -> int:
    dec = json.load(open(path))
    marks = {(r["family"], r["key"]): r["verdict"] for r in dec.get("rows", [])}
    who, when, changed = dec.get("reviewer", "Ken"), date.today().isoformat(), 0
    for fam, spec in FAMILIES.items():
        p = W2 / f"{fam}_handcheck.json"
        if not p.exists():
            continue
        sheet = json.load(open(p))
        for r in sheet.get("scored", []):
            v = marks.get((fam, spec["key"](r)))
            if v:
                r["verdict"], r["reviewer"], r["decision_date"] = v, who, when
                r["reading"] = "reviewed by " + who
                changed += 1
        if dec.get("notes", {}).get(fam):
            sheet["reviewer_note"] = {"by": who, "date": when, "note": dec["notes"][fam]}
        json.dump(sheet, open(p, "w"), indent=1)
    print(f"{changed} rows taken from {path} into cache/wave2/*_handcheck.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", type=Path, help="a decisions file saved from the page")
    a = ap.parse_args()
    return apply(a.apply) if a.apply else write_page()


if __name__ == "__main__":
    sys.exit(main())
