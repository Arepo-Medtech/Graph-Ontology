// Re-search unresolved conditions across the WHOLE terminology, not just
// clinical findings, and surface Australian extension concepts.
//
// Why: the binder constrained every query to <<404684003 Clinical finding.
// That is right for conditions and wrong for everything else a PBS indication
// can name — a procedure, a prophylaxis regimen, an administration act, a
// situation. The PrEP correction found 918591000168102 "Antiretroviral
// pre-exposure prophylaxis for HIV infection", an AU extension concept that was
// unreachable by construction. This looks for the rest of that class.
//
// A SNOMED identifier carries its namespace: for an extension concept the seven
// digits before the final partition+check digits are the namespace id.
// Australian namespaces seen in this release are reported as found, not assumed.
const CLIENT = process.env.NCTS_CLIENT_PATH
  || "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed/ncts-client.mjs";
const { expandSnomed } = await import(CLIENT);
import { readFileSync, writeFileSync } from "node:fs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const norm = (s) => s.toLowerCase().replace(/['’]s\b/g, "").replace(/[^a-z0-9]+/g, " ").trim();
const stripTag = (t) => t.replace(/\s*\((.*?)\)\s*$/, "").trim();
const semTag = (t) => (t.match(/\(([^)]+)\)\s*$/) || [, null])[1];
// Core international ids are short. Extension ids embed a 7-digit namespace.
const namespaceOf = (id) => (id.length >= 11 ? id.slice(-10, -3) : null);

const review = JSON.parse(readFileSync("reference/snomed_candidates_review.json", "utf8"));
const bindings = JSON.parse(readFileSync("reference/snomed_bindings.json", "utf8"));
const unmatched = bindings.results.filter((r) => r.method === "unmatched").map((r) => r.condition);
const targets = [...review.candidates.map((c) => c.condition), ...unmatched];

const out = [];
for (const [i, cond] of targets.entries()) {
  const hits = await expandSnomed(cond, { ecl: "*", count: 8 });
  await sleep(110);
  if (!hits || !hits.length) { continue; }
  const n = norm(cond);
  const exact = hits.filter((h) => [h.display, ...(h.synonyms || [])]
    .some((t) => norm(stripTag(t)) === n));
  const au = hits.filter((h) => namespaceOf(h.code));
  if (!exact.length && !au.length) continue;
  out.push({
    condition: cond,
    exact_match_found: exact.map((h) => ({ code: h.code, display: h.display,
      semantic_tag: semTag(h.display), namespace: namespaceOf(h.code) })),
    extension_concepts: au.map((h) => ({ code: h.code, display: h.display,
      semantic_tag: semTag(h.display), namespace: namespaceOf(h.code) })),
  });
  if ((i + 1) % 60 === 0) console.log(`  ${i + 1}/${targets.length}`);
}

const ns = {};
for (const o of out) for (const h of [...o.exact_match_found, ...o.extension_concepts])
  if (h.namespace) ns[h.namespace] = (ns[h.namespace] || 0) + 1;

writeFileSync("reference/au_concept_search.json", JSON.stringify({
  note: "Unresolved conditions re-searched across the whole terminology (ecl '*') "
      + "rather than <<404684003 Clinical finding only.",
  searched: targets.length,
  with_findings: out.length,
  exact_matches_missed: out.filter((o) => o.exact_match_found.length).length,
  namespaces_seen: ns,
  results: out,
}, null, 2));
console.log(`\nsearched ${targets.length}   with something to report ${out.length}`);
console.log(`exact matches the constrained search missed: ${out.filter(o=>o.exact_match_found.length).length}`);
console.log(`namespaces: ${JSON.stringify(ns)}`);
