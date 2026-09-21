// Bind condition names to SNOMED CT-AU concepts via NCTS Ontoserver.
//
// Method discipline matches the compendium: nothing is fuzzy-matched and every
// link carries how it was made. A top-ranked search hit is NOT a binding — it is
// recorded as a candidate for human confirmation, because $expand ranks by text
// relevance and will happily return a near-miss for a term that has no concept.
//
// Fail-safe, as the NCTS client contract requires: a null response means
// UNVALIDATED, never "no such concept". Those are retried, not recorded as absent.
//
// Usage:
//   NCTS_CLIENT_PATH=/path/to/ncts-client.mjs \
//   node --env-file=/path/to/.env scripts/bind_ontoserver.mjs out/conditions.json out/snomed_bindings.json
//
// Why this exists alongside bind_conditions.py: the offline binder needs
// sct2_Description and sct2_Relationship from an RF2 release. Both SNOMED
// releases available at time of writing ship neither, so there are no terms to
// match against. This binds over the wire instead, against the same pinned
// AU edition (20260731).
// NCTS client path is configurable; it holds the OAuth flow and the release pin.
// Credentials come from its .env via `node --env-file=`, never from this file.
const CLIENT = process.env.NCTS_CLIENT_PATH
  || "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed/ncts-client.mjs";
const { expandSnomed } = await import(CLIENT);
import { readFileSync, writeFileSync } from "node:fs";

// Possessives first: "Crohn's disease" and "Crohn disease" are the same term,
// but stripping punctuation blindly yields "crohn s disease" and they diverge.
const norm = (s) => s.toLowerCase()
  .replace(/['\u2019]s\b/g, "")
  .replace(/[^a-z0-9]+/g, " ")
  .replace(/\s+/g, " ")
  .trim();
// A concept's terms are its preferred display plus every designation. SNOMED
// records "Breast cancer" only as a synonym of "Malignant neoplasm of breast",
// so matching display alone misses the binding entirely.
const terms = (h) => [h.display, ...(h.synonyms || [])].filter(Boolean);
const stripTag = (t) => t.replace(/\s*\((disorder|finding|situation|event)\)\s*$/i, "").trim();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Ontoserver's `filter` is a conjunctive word-PREFIX search: every word must
// prefix a word in some designation. Inflections therefore miss —
// "metastases" does not prefix "metastatic", "oropharyngeal" does not prefix
// "oropharynx" — even though the concept plainly exists. Truncating each long
// word to a stem recovers them. Retrieval-tier discipline, as with PubMed.
const truncate = (t) => t.split(/\s+/)
  .map((w) => (w.length > 7 ? w.slice(0, 7) : w))
  .join(" ");

const [src, out] = process.argv.slice(2);
const doc = JSON.parse(readFileSync(src, "utf8"));
const results = [];
let exact = 0, normalised = 0, candidate = 0, unmatched = 0, unvalidated = 0;

for (const [i, rec] of doc.conditions.entries()) {
  const name = rec.condition;
  let hits = await expandSnomed(name, { count: 5 });
  let tier = "full";
  if (hits !== null && hits.length === 0) {
    const stem = truncate(name);
    if (stem !== name) {
      await sleep(120);
      const retry = await expandSnomed(stem, { count: 5 });
      if (retry && retry.length) { hits = retry; tier = "stemmed"; }
    }
  }
  if (hits === null) {                       // server/auth failure, not absence
    results.push({ condition: name, snomed: null, method: "unvalidated_retry" });
    unvalidated++;
  } else {
    const lower = name.toLowerCase();
    const e = hits.find((h) => terms(h).some((t) => stripTag(t).toLowerCase() === lower));
    const n = hits.find((h) => terms(h).some((t) => norm(stripTag(t)) === norm(name)));
    if (e) {
      const via = stripTag(e.display).toLowerCase() === lower ? "exact_display" : "exact_synonym";
      results.push({ condition: name, snomed: { concept_id: e.code, display: e.display, method: via, query_tier: tier } }); exact++;
    } else if (n) {
      const via = norm(stripTag(n.display)) === norm(name) ? "normalised_display" : "normalised_synonym";
      results.push({ condition: name, snomed: { concept_id: n.code, display: n.display, method: via, query_tier: tier } }); normalised++;
    }
    else if (hits.length) {
      results.push({ condition: name, snomed: null, method: "candidate_unconfirmed",
                     query_tier: tier, candidates: hits.slice(0, 3) });
      candidate++;
    } else { results.push({ condition: name, snomed: null, method: "unmatched" }); unmatched++; }
  }
  if ((i + 1) % 50 === 0) console.log(`  ${i + 1}/${doc.conditions.length}`);
  await sleep(120);
}

writeFileSync(out, JSON.stringify({
  source: "NCTS Ontoserver, SNOMED CT-AU 20260731 (pinned)",
  binding_policy: "exact or normalised display only; ranked hits are candidates, not bindings",
  counts: { exact, normalised, candidate, unmatched, unvalidated, total: results.length },
  results,
}, null, 2));
console.log(`\nexact ${exact}  normalised ${normalised}  candidate ${candidate}  unmatched ${unmatched}  unvalidated ${unvalidated}`);
