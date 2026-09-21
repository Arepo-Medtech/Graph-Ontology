// Build the SNOMED candidate review queue: hierarchy-enriched, triaged, sorted
// so the dangerous ones are first.
//
// Everything the queue needs is HERE. An earlier version computed only the
// hierarchy and the triage signals, quarantine and structural flags were applied
// by hand afterwards — so every rebuild silently reverted to a naive queue.
//
// Nothing is auto-bound. The signals say where to look, never what is true.
const CLIENT = process.env.NCTS_CLIENT_PATH
  || "/Users/sleekjazz/Developer/AREPO MEDTECH/reasonmed/ncts-client.mjs";
const { expandSnomed } = await import(CLIENT);
import { readFileSync, writeFileSync } from "node:fs";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- matching
// Stems, not exact tokens: comparing whole words read "infections"/"infection"
// and "anaemias"/"anaemia" as unrelated and flagged 41 correct bindings as
// rejects. Six characters is enough to join inflections without joining
// unrelated words.
const STOP = new Set(["the","and","with","for","due","other","disease","disorder",
                      "syndrome","finding","condition"]);
const stem = (w) => {
  w = w.toLowerCase();
  if (w.endsWith("ies")) w = w.slice(0, -3) + "y";
  else if (w.endsWith("es") && w.length > 4) w = w.slice(0, -2);
  else if (w.endsWith("s") && w.length > 3) w = w.slice(0, -1);
  return w.slice(0, 6);
};
const toks = (s) => new Set(s.toLowerCase().split(/[^a-z0-9]+/)
  .filter((w) => w.length > 2 && !STOP.has(w)).map(stem));
const shared = (a, b) => [...a].filter((w) => b.has(w)).length;

// ---------------------------------------------------------------- flags
// PBS wording that names an INTERVENTION has no concept under Clinical finding.
// PrEP bound to "Asymptomatic HIV infection in pregnancy" — an inversion — purely
// because the correct concept was outside the searched hierarchy.
const INTERVENTION = /prophylaxis|prevention|preventing|pre-exposure|post-exposure|vaccinat|immunis|screening|administration of|stimulation of|mobilisation|assisting|induction of|termination of|dietary management|haemodialysis/i;

// Pregnancy is quarantined regardless of signal: AMH-derived teratogen
// classifications and gestational windows attach BY CONDITION, so a wrong
// binding puts a pregnancy-safety record on the wrong clinical object. Of 16
// reviewed by hand, ALL were wrong and 6 carried no signal at all.
const PREGNANCY = /pregnan|obstetric|fetal|foetal|neonat|lactat|breast ?feed|birth|labour|partum|gestat|matern|ivf|fertilis|fertiliz|ovulat|contracep|miscarriage|abortion|eclampsia|puerper|termination/i;

export function triage(condition, hit, parents) {
  const cw = toks(condition), hw = toks(hit.display);
  const ov = shared(cw, hw);
  const scored = parents.map((p) => ({ p, score: shared(cw, toks(p.display)) }))
                        .sort((a, b) => b.score - a.score);
  const best = scored[0];
  const off_domain = ov === 0 && parents.length > 0 && (!best || best.score === 0);
  // "Wounds" -> "Damaging own wounds" shares the stem "wound", so the hit alone
  // looks related. Its parent is "Deliberate self-harm", which shares nothing.
  // A hit whose ANCESTRY is unrelated to the condition is the real signal.
  const parents_unrelated = parents.length > 0 && (!best || best.score === 0);
  const parent_better = !!best && best.score > ov;
  const adds = hit.display.split(/[^a-zA-Z0-9]+/)
    .filter((w) => w.length > 2 && !cw.has(stem(w)));
  const narrower = adds.length > 0 && ov >= Math.max(1, cw.size - 1);

  const intervention = INTERVENTION.test(condition);
  const pregnancy = PREGNANCY.test(condition) || PREGNANCY.test(hit.display)
                    || parents.some((p) => PREGNANCY.test(p.display));

  let action = "plausible — confirm";
  if (off_domain) action = "REJECT — neither hit nor any parent shares a concept with the condition";
  else if (parents_unrelated) action = "REJECT — hit looks related but its parents share nothing with the condition";
  else if (parent_better) action = `consider parent instead: ${best.p.code} ${best.p.display}`;
  else if (narrower) action = "hit is narrower — check it is not a sub-type";
  if (intervention) action = "REJECT — wrong hierarchy for this wording; re-search under <<71388002 Procedure";
  if (pregnancy) action = "QUARANTINE — manual review required regardless of signal";

  return {
    signals: { off_domain, parents_unrelated, parent_better, narrower, adds_words: adds },
    intervention, pregnancy, suggested_action: action,
    structural_note: intervention
      ? "PBS wording names an INTERVENTION, not a clinical finding. The hit shown was searched in the wrong hierarchy."
      : undefined,
    quarantine: pregnancy ? {
      reason: "pregnancy_or_reproductive", requires_manual_review: true,
      why: "AMH teratogen classifications and gestational windows attach BY CONDITION; a wrong binding attaches a pregnancy-safety record to the wrong clinical object.",
    } : undefined,
  };
}

export function demo() {
  // NB console.assert only logs; a demo that prints "ok" after a failed check is
  // worse than none. This throws.
  const ok = (cond, msg) => { if (!cond) throw new Error(`self-check FAILED: ${msg}`); };
  const t = (c, d, par = []) => triage(c, { display: d }, par.map((x) => ({ code: "1", display: x })));
  // stems must join inflections, or correct bindings read as rejects
  ok(!t("Staphylococcal infections", "Staphylococcal infection", ["Bacterial infection"]).signals.off_domain, "inflection");
  ok(!t("Megaloblastic anaemias", "Megaloblastic anaemia", ["Anaemia"]).signals.off_domain, "plural");
  // Wounds/Damaging own wounds SHARE a stem, so off_domain cannot catch it.
  // The parent is what gives it away.
  const w = t("Wounds", "Damaging own wounds", ["Deliberate self-harm"]);
  ok(!w.signals.off_domain, "wounds: hit does share a stem");
  ok(w.signals.parents_unrelated, "wounds: parents share nothing");
  ok(w.suggested_action.startsWith("REJECT"), "wounds must be rejected");
  // and a correct binding with a broad parent must NOT be rejected
  const g = t("Genital herpes", "Genital herpes simplex", ["Herpes simplex infection"]);
  ok(!g.signals.parents_unrelated, "genital herpes parent is related");
  // interventions and pregnancy override every signal
  ok(t("Pre-exposure prophylaxis against HIV", "Asymptomatic HIV infection").intervention, "intervention");
  const p = t("Complicated urinary tract infection", "Induced termination of pregnancy complicated by UTI");
  ok(p.pregnancy && p.suggested_action.startsWith("QUARANTINE"), "pregnancy overrides");
  // a pregnancy hit with no signal at all must STILL quarantine — 6 of 16 were like this
  const q = t("Diarrhoea of greater than 2 weeks duration", "Gestation greater than 20 weeks");
  ok(q.pregnancy && q.suggested_action.startsWith("QUARANTINE"), "unsignalled pregnancy");
  console.log("self-check ok");
}

if (process.argv.includes("--demo")) { demo(); process.exit(0); }

// ---------------------------------------------------------------- build
const src = JSON.parse(readFileSync("reference/snomed_bindings.json", "utf8"));
const cands = src.results.filter((r) => r.method === "candidate_unconfirmed" && r.candidates?.length);
const out = [];
for (const [i, r] of cands.entries()) {
  const top = r.candidates[0];
  // NB first arg is the FILTER TERM. Passing the code here filters the parent
  // set by a numeric string and returns nothing for every concept.
  const parents = (await expandSnomed("", { ecl: `>!${top.code}`, count: 6 })) || [];
  await sleep(110);
  out.push({ condition: r.condition, top_hit: top,
             parents: parents.map((p) => ({ code: p.code, display: p.display })),
             ...triage(r.condition, top, parents),
             other_hits: r.candidates.slice(1) });
  if ((i + 1) % 60 === 0) console.log(`  ${i + 1}/${cands.length}`);
}

const rank = (o) => [o.quarantine ? 0 : 1,
                     o.signals.off_domain || o.signals.parents_unrelated || o.intervention ? 0
                     : o.signals.parent_better ? 1 : o.signals.narrower ? 2 : 3];
out.sort((a, b) => { const x = rank(a), y = rank(b);
  return x[0] - y[0] || x[1] - y[1] || a.condition.localeCompare(b.condition); });

writeFileSync("reference/snomed_candidates_review.json", JSON.stringify({
  note: "Review queue. Hierarchy-enriched, triaged, quarantined items first. Nothing auto-bound.",
  warning: "Signals are LEXICAL triage, not verdicts. The 'plausible' tier is NOT safe: of 16 quarantined "
         + "pregnancy candidates reviewed by hand, 6 carried no flag at all and every one was wrong.",
  count: out.length,
  quarantined: out.filter((o) => o.quarantine).length,
  wrong_hierarchy: out.filter((o) => o.intervention).length,
  candidates: out,
}, null, 2));
console.log(`\nqueue ${out.length}  quarantined ${out.filter(o=>o.quarantine).length}  wrong-hierarchy ${out.filter(o=>o.intervention).length}`);
