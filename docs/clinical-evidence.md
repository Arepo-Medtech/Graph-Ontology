# AMH clinical evidence

**Status:** curated, source-linked clinical evidence metadata

**Bulk tables:** `clinical_evidence`, `pregnancy_safety_evidence`, `supplement_role_evidence`, `therapeutic_role_evidence`

**Source edition:** AMH Medicines July 2026

**Coverage boundary:** selected pregnancy-safety and supplement-role distinctions; not a complete AMH extract

## Why this layer exists

Medicine identity alone cannot answer every clinical classification question. Pregnancy guidance can
change with gestational age, route, dose, formulation and indication. The same element or vitamin can
be used as dietary supplementation, deficiency treatment, an antidote or an acute hospital medicine.

The compendium therefore stores these findings as evidence records instead of adding unconditional
flags to AMT substances. Every record includes:

- the subject and whether it represents a substance, class or formulation;
- route, pregnancy window and dose or role context;
- an evidence category and a concise recommendation;
- a paraphrased summary, AMH edition, access date and direct source URL.

The records contain concise metadata derived from the licensed source. They do not reproduce AMH
monographs and are not a substitute for checking the current source before clinical use.

## Pregnancy-safety distinctions

| Evidence category | Representative subjects | Rule consequence |
|---|---|---|
| `known_human_teratogen` | acitretin, isotretinoin, thalidomide, valproate, mycophenolate | Strong positive evidence; still retain route and indication context |
| `congenital_malformation_risk` | methotrexate, warfarin, phenytoin, carbamazepine, antithyroid drugs | Do not silently promote every risk statement to the same certainty or recommendation |
| `animal_or_uncertain_human` | lenalidomide, leflunomide | Preserve the difference between animal evidence, class inference and demonstrated human risk |
| `fetal_toxicity` | sartans, later-pregnancy tetracyclines, danazol | Match the gestational window; these are not interchangeable with first-trimester teratogenicity |
| `pregnancy_avoidance` | lithium, statins | Avoidance guidance can reflect theoretical, maternal or neonatal risk rather than proven malformations |
| `safe_at_physiological_dose` / `local_use_appears_safe` | colecalciferol, topical calcipotriol with betamethasone | Dose and route can reverse the result of a substance-only rule |

The general AMH pregnancy guide explains the central distinction: first-trimester exposure is the
principal concern for structural malformations, while later exposure can produce fetal toxicity or
perinatal effects. It also notes that only a small number of medicines have conclusively demonstrated
human teratogenicity and that missing information is not proof of safety.

Primary guide: [Drugs in pregnancy](https://amhonline.amh.net.au/guides/guide-pregnancy)

## Supplement-role distinctions

| Subject | AMH-supported distinction | Rule consequence |
|---|---|---|
| Calcium | Supplementation and therapeutic indications coexist | Require product formulation and intended role |
| Iron | Prevention, deficiency treatment, oral products, parenteral products and iron–folate combinations coexist | Keep route and formulation; include iron even though PBS places it outside ATC A12 |
| Iodine | Dietary-dose supplementation differs from high-dose thyroid treatment | Use dose and indication, not elemental ancestry alone |
| Magnesium sulfate | Obstetric and other acute therapeutic uses | A magnesium-containing medicine is not automatically a supplement |
| Thiamine | Nutritional replacement and antidote use coexist | Vitamin identity does not uniquely determine role |
| Carbimazole, probenecid and sulfasalazine | Therapeutic medicines that can be caught by broad name, element or chemical-fragment logic | Use as negative controls for rule development |

This layer complements `supplement_listing`. The PBS table answers whether an item is listed in the
A11, A12 or B03A therapeutic branches. The AMH evidence answers why chemical identity is not enough
to expand that set safely.

## Rule contract for Makoha

A deterministic classifier should evaluate a record in this order:

1. Resolve the medicine or product identity and retain its formulation.
2. Match a specific substance, class or formulation evidence record.
3. Apply route, pregnancy window, dose and indication constraints.
4. Return the sourced category and recommendation with the evidence ID and URL.
5. Return `unknown` when a required dimension is absent or the record is outside this curated scope.

For supplement-role decisions, keep three separate facts: nutrient or chemical identity, product
classification, and use in context. For pregnancy decisions, keep congenital-malformation risk,
later fetal toxicity, neonatal effects and precautionary avoidance as separate categories.

## Condition-to-treatment evidence

The `therapeutic_role_evidence` table records when AMH links a medicine family to a condition and
also records nearby class boundaries. The initial records cover oral NSAIDs for osteoarthritis,
adjunctive NSAID use in rheumatoid arthritis, renal-risk context, the separation of
5-aminosalicylates from NSAIDs, and oral iron for confirmed deficiency.

This evidence supports a possible treatment relationship; it does not prove why a particular
patient received a medicine. Makoha should retain `supported`, `contradicted`, and `unknown` rather
than converting condition–medicine co-occurrence into a causal assertion.

## Source references

The complete machine-readable reference list is in
[`reference/amh_clinical_evidence.json`](../reference/amh_clinical_evidence.json). Representative
primary entries include:

- [Acitretin](https://amhonline.amh.net.au/chapters/dermatological-drugs/drugs-acne/retinoids-oral/acitretin)
- [Methotrexate](https://amhonline.amh.net.au/chapters/immunomodulators-anti-inflammatories/other-immunomodulators/methotrexate-immunomodulator)
- [Valproate](https://amhonline.amh.net.au/chapters/neurological-drugs/antiseizure-drugs/other-antiseizure-drugs/valproate)
- [Doxycycline](https://amhonline.amh.net.au/chapters/anti-infectives/antibacterials/tetracyclines/doxycycline)
- [Colecalciferol](https://amhonline.amh.net.au/chapters/endocrine-drugs/drugs-affecting-bone/vitamin-d/colecalciferol)
- [Calcium](https://amhonline.amh.net.au/chapters/endocrine-drugs/drugs-affecting-bone/other-drugs-affecting-bone/calcium)
- [Iron](https://amhonline.amh.net.au/chapters/blood-electrolytes/drugs-anaemias/other-drugs-anaemias/iron)
- [Iodine](https://amhonline.amh.net.au/chapters/endocrine-drugs/drugs-thyroid-disorders/other-drugs-thyroid-disorders/iodine)
- [Magnesium sulfate](https://amhonline.amh.net.au/chapters/obstetric-gynaecological-drugs/drugs-obstetrics/drugs-pre-eclampsia/magnesium-sulfate)
