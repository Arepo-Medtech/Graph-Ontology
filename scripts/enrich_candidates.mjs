// Enrich the SNOMED candidate queue with hierarchy, so review is a glance.
//
// For each candidate's top hit we fetch its DIRECT PARENTS (ECL `>!code`) and
// derive three signals:
//
//   narrower      the hit adds words the condition does not have. "Major
//                 depression" -> "Mild major depression" is a sub-type, not the
//                 thing. Binding it silently narrows the condition.
//   parent_better a parent's name matches the condition more closely than the
//                 hit does. Usually means: bind the parent instead.
//   off_domain    no parent shares a word with the condition. "Wounds" ->
//                 "Damaging own wounds" sits under self-injury. Wrong outright.
//
// Nothing is auto-bound. These are review aids; a human still decides.
const CLIENT = process.env.NCTS_CLIENT_PATH
  || "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed/ncts-client.mjs";
const { expandSnomed } = await import(CLIENT);
import { readFileSync, writeFileSync } from "node:fs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const words = (s) => new Set(s.toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(w => w.length > 2));
const overlap = (a, b) => [...a].filter((w) => b.has(w)).length;

const src = JSON.parse(readFileSync("reference/snomed_bindings.json", "utf8"));
const cands = src.results.filter((r) => r.method === "candidate_unconfirmed" && r.candidates?.length);
const out = [];

for (const [i, r] of cands.entries()) {
  const top = r.candidates[0];
  const cw = words(r.condition), hw = words(top.display);
  // NB: first arg is the FILTER TERM, not the code. Passing the code here
  // filters the parent set by a numeric string and always returns nothing.
  const parents = (await expandSnomed("", { ecl: `>!${top.code}`, count: 6 })) || [];
  await sleep(110);

  const extra = [...hw].filter((w) => !cw.has(w));          // words the hit adds
  const narrower = extra.length > 0 && overlap(cw, hw) >= Math.max(1, cw.size - 1);
  const scored = parents.map((p) => ({ ...p, score: overlap(cw, words(p.display)) }))
                        .sort((a, b) => b.score - a.score);
  const bestParent = scored[0];
  const parent_better = bestParent && bestParent.score > overlap(cw, hw);
  const off_domain = parents.length > 0 && scored.every((p) => p.score === 0) && overlap(cw, hw) <= 1;

  out.push({
    condition: r.condition, top_hit: top, parents: parents.map(p => ({ code: p.code, display: p.display })),
    signals: { narrower, parent_better, off_domain, adds_words: extra },
    suggested_action: off_domain ? "REJECT — no shared domain with any parent"
      : parent_better ? `consider parent instead: ${bestParent.code} ${bestParent.display}`
      : narrower ? "hit is narrower than the condition — check it is not a sub-type"
      : "plausible — confirm",
    other_hits: r.candidates.slice(1),
  });
  if ((i + 1) % 50 === 0) console.log(`  ${i + 1}/${cands.length}`);
}

const rank = (o) => o.signals.off_domain ? 0 : o.signals.parent_better ? 1 : o.signals.narrower ? 2 : 3;
out.sort((a, b) => rank(a) - rank(b) || a.condition.localeCompare(b.condition));

writeFileSync("reference/snomed_candidates_review.json", JSON.stringify({
  note: "Review queue. Hierarchy-enriched, risky first. Nothing auto-bound.",
  legend: { off_domain: "reject", parent_better: "bind the parent instead", narrower: "hit is a sub-type", plausible: "confirm" },
  count: out.length, candidates: out,
}, null, 2));
const c = { off_domain: 0, parent_better: 0, narrower: 0, plausible: 0 };
for (const o of out) c[o.signals.off_domain ? "off_domain" : o.signals.parent_better ? "parent_better" : o.signals.narrower ? "narrower" : "plausible"]++;
console.log(`\n${JSON.stringify(c)}`);
