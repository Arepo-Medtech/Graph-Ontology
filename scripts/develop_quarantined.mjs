// Develop the quarantined rows: re-search each, and report whether a candidate
// exists that does NOT trip the pregnancy rule.
//
// ⚠️ THIS DOES NOT WEAKEN THE QUARANTINE RULE, AND DOES NOT BIND ANYTHING.
// The rule is sound and was validated by hand. What this fixes is the INPUT
// that tripped it. The 15 split two ways:
//
//   the CONDITION is reproductive (7)  -> quarantine is protecting the right
//                                         thing. It STAYS, whatever we find.
//   only the CANDIDATE is (8)          -> the condition is ordinary and the
//                                         top hit was a lexical accident, eg
//                                         "Diarrhoea of greater than 2 weeks
//                                         duration" -> "Gestation greater than
//                                         20 weeks". Replace the candidate and
//                                         the quarantine falls away by itself.
//
// A candidate is only reported as clean once ITS PARENTS are checked too.
// Display alone is not enough: 6 of the 16 reviewed by hand carried the
// pregnancy signal only on a parent.
//
// Output is a REPORT of better candidates for a person to choose from.
//
//   node --env-file=<env> scripts/develop_quarantined.mjs [--demo]
const CLIENT = process.env.NCTS_CLIENT_PATH
  || "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed/ncts-client.mjs";
import { readFileSync, writeFileSync } from "node:fs";

const PREG = /pregnan|obstetric|fetal|foetal|neonat|lactat|breast ?feed|birth|labour|partum|gestat|matern|ivf|fertilis|fertiliz|ovulat|contracep|miscarriage|abortion|eclampsia|puerper|termination/i;
// Search terms that strip the PBS qualifier wrapping a plain clinical noun.
// "Diarrhoea of greater than 2 weeks duration" searches as "Diarrhoea": the
// duration clause is what matched "Gestation greater than 20 weeks".
const simplify = (c) => c
  .replace(/\s+of greater than .*$/i, "")
  .replace(/\s+associated with .*$/i, "")
  .replace(/^(risk of|patients? (undergoing|with|unable to).*?)\s+/i, "")
  .replace(/\s+secondary to .*$/i, "")
  .replace(/\s+due to .*$/i, "")
  .replace(/^(secondarily |complicated |upper and lower )/i, "")
  .trim();

export function plan(condition) {
  const conditionIsReproductive = PREG.test(condition);
  return { conditionIsReproductive,
           terms: [...new Set([simplify(condition), condition])].filter(Boolean),
           verdict: conditionIsReproductive ? "STAYS QUARANTINED" : "candidate may be replaceable" };
}

function demo() {
  const a = plan("Diarrhoea of greater than 2 weeks duration");
  if (a.conditionIsReproductive) throw new Error("plain diarrhoea must not be reproductive");
  if (!a.terms.includes("Diarrhoea")) throw new Error("must strip the duration clause: " + a.terms);
  const b = plan("Termination of an intra-uterine pregnancy");
  if (!b.conditionIsReproductive) throw new Error("a real pregnancy condition must stay quarantined");
  if (b.verdict !== "STAYS QUARANTINED") throw new Error("verdict");
  const c = plan("Anaemia associated with intrinsic renal disease");
  if (!c.terms.includes("Anaemia")) throw new Error("must strip 'associated with': " + c.terms);
  console.log("develop_quarantined.mjs self-check ok");
}
if (process.argv.includes("--demo")) { demo(); process.exit(0); }

const { expandSnomed } = await import(CLIENT);
const rev = JSON.parse(readFileSync("reference/snomed_candidates_review.json", "utf8"));
const q = rev.candidates.filter((c) => c.quarantine);
const out = [];
for (const c of q) {
  const p = plan(c.condition);
  const seen = new Map();
  for (const t of p.terms) {
    const hits = await expandSnomed(t, { count: 10 });
    if (hits === null) { out.push({ condition: c.condition, ...p, error: "UNVALIDATED - lookup did not return" }); seen.clear(); break; }
    for (const h of hits) if (!seen.has(h.code)) seen.set(h.code, { ...h, via: t });
    await new Promise((r) => setTimeout(r, 120));
  }
  const all = [...seen.values()];
  const shortlist = all.filter((h) => !PREG.test(h.display) && !(h.synonyms || []).some((s) => PREG.test(s)));
  const clean = [];
  for (const h of shortlist.slice(0, 6)) {
    const par = (await expandSnomed("", { ecl: `>!${h.code}`, count: 6 })) || [];
    await new Promise((r) => setTimeout(r, 120));
    if (par.some((p) => PREG.test(p.display))) continue;   // parent carries it: NOT clean
    clean.push({ ...h, parents: par.map((p) => p.display).slice(0, 2) });
  }
  out.push({ condition: c.condition, ...p,
             current_hit: `${c.top_hit.code} ${c.top_hit.display}`,
             searched: p.terms, total_hits: all.length,
             clean_alternatives: clean.slice(0, 4).map((h) => `${h.code} ${h.display}  [via "${h.via}"; parents: ${h.parents.join(' / ')}]`) });
}
writeFileSync("reference/quarantine_development.json", JSON.stringify({
  _note: "Re-search of the quarantined rows. Reports better candidates; binds NOTHING.",
  _rule_unchanged: "The pregnancy quarantine rule is not weakened. Rows whose CONDITION is reproductive stay quarantined whatever is found.",
  checked_utc: "2026-09-23", count: out.length, results: out }, null, 2) + "\n");
const stays = out.filter((o) => o.conditionIsReproductive).length;
const fixable = out.filter((o) => !o.conditionIsReproductive && (o.clean_alternatives || []).length).length;
const stuck = out.filter((o) => !o.conditionIsReproductive && !(o.clean_alternatives || []).length).length;
console.log(`quarantined ${out.length} | stays (condition reproductive) ${stays} | clean alternative found ${fixable} | none found ${stuck}`);
