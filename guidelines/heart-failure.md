# Heart failure

**Edition:** 1.0 · 2026-09-21 · **Status:** drafted and source-verified; awaiting clinical attestation
**Scope:** adults. Prevention, diagnosis, and management of heart failure with reduced ejection fraction.

> **Australian primary source, but dated.** NHFA / CSANZ *Australian clinical guidelines for the management
> of heart failure 2018* [S1]. Recommendations are graded on strength of evidence and likely **absolute
> benefit versus harm**, with additional considerations given as practice points [S1].
>
> ⚠️ **Currency warning — read before using.** This guideline is **eight years old** and I could find no
> newer Australian replacement. It **predates the trial evidence for SGLT2 inhibitors in heart failure with
> reduced ejection fraction irrespective of diabetes**. In this guideline SGLT2 inhibitors appear only for
> *preventing* HF hospitalisation in type 2 diabetes with cardiovascular disease [S1]. Subsequent evidence
> places them differently — see *The gap* below. Anything downstream must carry this caveat.

## Prevention

**Blood pressure and lipid lowering decrease the risk of developing heart failure** [S1].

**SGLT2 inhibitors decrease the risk of heart failure hospitalisation in patients with type 2 diabetes and
cardiovascular disease** [S1]. Note the framing: in 2018 this is a *prevention* recommendation scoped to
diabetes, not a treatment recommendation for established HF.

## Diagnosis

**An echocardiogram is recommended if heart failure is suspected or newly diagnosed** [S1].

**If echocardiography cannot be arranged in a timely fashion, measurement of plasma B-type natriuretic
peptides improves diagnostic accuracy** [S1]. BNP is the fallback for access, not the preferred first test.

## Treatment — reduced ejection fraction

**Angiotensin-converting enzyme inhibitors, β-blockers and mineralocorticoid receptor antagonists improve
outcomes** in HF associated with reduced left ventricular ejection fraction [S1]. These three are the
foundation.

**In selected patients with persistent HF associated with reduced LVEF**, additional options [S1]:

- switching the ACE inhibitor to an **angiotensin receptor neprilysin inhibitor**
- **ivabradine**
- **implantable cardioverter defibrillators**
- **cardiac resynchronisation therapy**
- **atrial fibrillation ablation**

## Models of care

**Multidisciplinary heart failure disease management facilitates the implementation of evidence-based HF
therapies** [S1].

**Clinicians should also consider models of care that optimise medication titration** — nurse-led titration
is named [S1]. The guideline treats *how the drugs get titrated* as a recommendation in its own right, not
an implementation detail.

It was designed to support **systematic integration into HF care, including ongoing audit and feedback** [S1].

## The gap

The 2018 guideline confines SGLT2 inhibitors to prevention in type 2 diabetes with CVD [S1]. A 2025
meta-analysis of 11 RCTs and 32,654 participants with **HFrEF** — a population defined by ejection fraction,
not by diabetes — found **SGLT2 inhibitors the most effective intervention in Asian patients for the
composite of HF hospitalisation, cardiovascular death and all-cause mortality (RR 0.61, 95% CI 0.49–0.75)**
[S2].

That is a different clinical position from the one the Australian guideline states, and the guideline has
not been updated to reflect it. **I am not writing a recommendation here** — a single meta-analysis in a
population-stratified comparison is not a substitute for guideline authorship. It is recorded so that the
staleness is visible rather than inferred.

## Australian context — PBS

PBS Schedule 4333, checked directly [S3]:

| Class | Agents | Benefit type |
|---|---|---|
| ACE inhibitors | perindopril, ramipril | **unrestricted** (also R) |
| ARB | candesartan | **unrestricted** (also R) |
| β-blockers | metoprolol | **unrestricted** (also R) |
| β-blockers | carvedilol, bisoprolol | restricted |
| MRA | spironolactone | **unrestricted** (also R) |
| MRA | eplerenone | authority required (streamlined) |
| **ARNI** | sacubitril (with valsartan) | authority required (streamlined) |
| **SGLT2 inhibitors** | dapagliflozin, empagliflozin | authority required (streamlined) |
| Ivabradine | — | authority required (streamlined) |
| Loop diuretic | furosemide | **unrestricted** (also R) |
| Digoxin | — | restricted |

The 2018 foundation therapies are the accessible ones: ACE inhibitors, an ARB, metoprolol, spironolactone
and furosemide are all unrestricted. Everything the guideline places at "selected patients" — ARNI,
ivabradine — plus the SGLT2 inhibitors the guideline never positioned for HFrEF, require authority.

## Unresolved

| Point | Kind | Detail |
|---|---|---|
| Recommendation grades | input_unavailable | S1 states recommendations are graded on evidence strength and absolute benefit vs harm; the grades themselves are not in the retrieved abstract |
| Doses and titration targets | input_unavailable | not in the retrieved abstract |
| **HF with preserved ejection fraction** | input_unavailable | not addressed in the retrieved abstract. A major omission for practice |
| Diuretic strategy | input_unavailable | not in the retrieved abstract |
| Device eligibility thresholds (ICD, CRT) | input_unavailable | named as options; criteria not retrieved |
| Current place of SGLT2 inhibitors in HFrEF | **evidence_unsettled / guideline stale** | S1 predates the evidence; S2 indicates a different position. No Australian guideline update found |
| Acute decompensated heart failure | out_of_scope | not addressed here |

**Only the structured abstract of S1 was retrieved**, not the full guideline. This is the thinnest source
base of any guideline in this set, and the content above should be read as the guideline's own summary of
its main recommendations rather than as full coverage.

## Sources

| id | citation | type |
|---|---|---|
| S1 | NHFA / CSANZ. *Australian clinical guidelines for the management of heart failure 2018.* Med J Aust 2018. PMID 30067937 | practice guideline (AU/NZ), graded |
| S2 | Comparative Efficacy of Pharmacological Interventions for HFrEF Between Asian and White Patients: A Meta-analysis of RCTs. *Am J Cardiovasc Drugs* 2025. PMID 40643788 | meta-analysis, 11 RCTs, n=32,654 |
| S3 | PBS Public API v3, Schedule 4333 | primary data (AU) |
