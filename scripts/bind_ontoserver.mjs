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

// Bind only concepts that have a parent. Every active concept but the root has
// one; an orphan is retired. Without this, 17 of 35 exact matches found in a
// whole-terminology search were retired concepts with IDENTICAL display text —
// Septicaemia 154313001, Coronary artery disease 8957000 — which bind silently
// and wrongly. Mirrors the concept-activeness gate this repo applies to AMT.
const hasParent = async (code) => {
  const p = await expandSnomed("", { ecl: `>!${code}`, count: 1 });
  return p === null ? null : p.length > 0;      // null = unvalidated, not absent
};

const [src, out] = process.argv.slice(2);
const doc = JSON.parse(readFileSync(src, "utf8"));
const results = [];
let exact = 0, normalised = 0, candidate = 0, unmatched = 0, unvalidated = 0, retired = 0;

for (const [i, rec] of doc.conditions.entries()) {
  const name = rec.condition;
  // A PBS indication can name a finding OR an intervention. PrEP and
  // Haemodialysis are procedures and were unreachable under findings alone.
  const ECL = "<<404684003 OR <<71388002";
  // count 20, not 5: "Major depressive disorder" ranked 6th and was truncated away.
  let hits = await expandSnomed(name, { ecl: ECL, count: 20 });
  let tier = "full";
  if (hits !== null && hits.length === 0) {
    const stem = truncate(name);
    if (stem !== name) {
      await sleep(120);
      const retry = await expandSnomed(stem, { ecl: ECL, count: 20 });
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
    const chosen = e || n;
    const live = chosen ? await hasParent(chosen.code) : null;
    if (chosen && live === false) {
      results.push({ condition: name, snomed: null, method: "rejected_retired_concept",
                     rejected: { concept_id: chosen.code, display: chosen.display },
                     why: "concept has no parent: retired, despite an exact term match" });
      retired++;
    } else if (e && live) {
      const via = stripTag(e.display).toLowerCase() === lower ? "exact_display" : "exact_synonym";
      results.push({ condition: name, snomed: { concept_id: e.code, display: e.display, method: via, query_tier: tier, parent_verified: true } }); exact++;
    } else if (n && live) {
      const via = norm(stripTag(n.display)) === norm(name) ? "normalised_display" : "normalised_synonym";
      results.push({ condition: name, snomed: { concept_id: n.code, display: n.display, method: via, query_tier: tier, parent_verified: true } }); normalised++;
    } else if (chosen) {
      results.push({ condition: name, snomed: null, method: "unvalidated_retry",
                     why: "parentage check did not return" }); unvalidated++;
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
  binding_policy_v2: "exact/normalised match on display or designation, in <<404684003 OR <<71388002, "
    + "AND the concept must have a parent (orphan = retired = rejected)",
  counts: { exact, normalised, candidate, unmatched, unvalidated, retired, total: results.length },
  results,
}, null, 2));
console.log(`\nexact ${exact}  normalised ${normalised}  candidate ${candidate}  unmatched ${unmatched}  retired ${retired}  unvalidated ${unvalidated}`);
