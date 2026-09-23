# Community-acquired pneumonia in children

**Edition:** 1.0 · 2026-09-23 · **Status:** drafted and source-verified; awaiting clinical attestation
**Scope:** clinical diagnosis, severity, investigation, antibiotic choice and disposition for community-acquired pneumonia in children. The adult counterpart is the pneumonia row of `drug-choice-for-selected-infections`; see also `sepsis-children` and `influenza`.

> ✅ **OPEN AND QUOTED.** 24 of 24 claims quoted verbatim from the **RCH Melbourne Clinical Practice Guideline *Community acquired pneumonia*** (Last updated October 2023); **32 fragments re-checked by machine. 3 quoted doses.**

> ⚠️ **Non-severe pneumonia: high-dose oral amoxicillin, even for inpatients.** Routine chest X-ray, bloods and microbiology are not recommended. **The amoxicillin dose is not on the retrieved page** (it sits in an algorithm image) — see Unresolved.

---

## Recognise it

- **CAP is a clinical diagnosis and is most often viral.** [S1]
- **Clinical definition:** fever, cough and tachypnoea at rest, plus retractions in younger children. [S1]
- **Complicated pneumonia** means a complication such as parapneumonic effusion, empyema, lung abscess or necrotising pneumonia. [S1]
- **Absent breath sounds with a dull percussion note suggest a pleural effusion.** [S1]
- ⚠️ **Consider severe pneumonia** when pneumonia features come with any of: severe respiratory distress · marked tachycardia · altered mental state · SpO2 <80% or needing respiratory support (e.g. CPAP, HFNP) · complicated pneumonia. [S1]
- ⚠️ **Consider sepsis in severe pneumonia.** Infants under 1 month: use the seriously unwell neonate and sepsis guidelines instead. [S1]

## Investigate

- **No routine chest X-ray, blood tests or microbiology** — especially in mild disease managed as an outpatient. [S1]
- **CXR when severe or complicated pneumonia is suspected.** Consider repeating it if the child deteriorates or fails to improve after 48–72 hours of appropriate antibiotics. [S1]
- **No follow-up CXR** after uncomplicated pneumonia or a small effusion with uneventful recovery. **Follow-up CXR at 6 weeks** for complicated pneumonia, recurrent pneumonia in the same lobe, or initial suspicion of a chest mass, anatomical abnormality or foreign body. [S1]
- **Severe or complicated pneumonia:** UEC if on IV fluids · FBE and blood film · blood culture · influenza PCR · COVID-19 testing per local criteria. [S1]
- **Do not test for other viruses or atypical pathogens**: it will not change management, and atypical testing cannot separate infection from carriage. [S1]
- **CRP and procalcitonin cannot distinguish viral from bacterial cause, nor indicate severity.** [S1]

## Treat

- **Admit** children needing supplemental oxygen, NG or IV hydration, or with moderate to severe work of breathing. [S1]
- **Give oxygen if saturations are below 90%.** [S1]
- ⚠️ **Limit NG or IV maintenance fluids to 2/3 of calculated requirement** to avoid fluid overload, with regular review of fluid status. [S1]
- **Non-severe pneumonia: high-dose oral amoxicillin, even for inpatients** — as effective as IV benzylpenicillin. Most children, including hospitalised children, can be managed orally. [S1]
- **Follow local susceptibility guidance** where it differs. [S1]
- **Reported penicillin allergy:** assess severity using Therapeutic Guidelines and the RCH allergy prescribing guidance. [S1]
- **Immediate or severe penicillin hypersensitivity, oral:** doxycycline 50 mg (<26 kg), 75 mg (26–35 kg) or 100 mg (>35 kg) twice daily, **or** azithromycin 10 mg/kg (max 500 mg) once daily. [S1]
- **Immediate or severe penicillin hypersensitivity, IV:** ciprofloxacin 10 mg/kg (max 400 mg) IV 12-hourly **plus** vancomycin IV per local protocol. [S1]
- **Mycoplasma:** no proven benefit from treatment; it may be considered in severe pneumonia not responding to treatment. [S1]

## Disposition and follow-up

- **Discuss with the paediatric team** when the child meets admission criteria or outpatient therapy fails. [S1]
- ⚠️ **Consider transfer** for severe or complicated pneumonia, comorbidities (cardiac, chronic respiratory, immune deficiency or suppression), or care beyond the local hospital's comfort. [S1]
- **Discharge when oxygenation and oral intake are adequate.** **Outpatients need medical review in 24–48 hours.** [S1]

---

## Unresolved

| # | Item | Class |
|---|---|---|
| 1 | ⚠️ **No amoxicillin dose, severe-pneumonia IV regimen or treatment duration is on the retrieved page** — they sit in the antibiotic algorithm image ('summarised in the algorithm below'), which was not retrieved. | `input_unavailable` |
| 2 | **Vancomycin dose** is deferred to local hospital protocol. | `input_unavailable` |
| 3 | **SpO2 threshold for severe pneumonia reads '<80%'** in the extracted text, while oxygen is started below 90%. Quoted as retrieved; confirm against the live page before relying on it. | `observation` |
| 4 | **Adult counterpart differs by population, not contradiction:** `drug-choice-for-selected-infections` (AMH, adults) gives doxycycline or **clarithromycin** as penicillin-allergy alternatives and 5 days' duration; RCH gives doxycycline or **azithromycin** and states no duration. | `observation` |
| 5 | **Parapneumonic effusion/empyema management** is in a separate RCH guideline, not retrieved. | `out_of_scope` |
| 6 | **Licence:** RCH guidelines are free to read but **© The Royal Children's Hospital**, not openly licensed; quoted with attribution. | `observation` |

## Sources

| id | Source | Treatment |
|---|---|---|
| **S1** | The Royal Children's Hospital Melbourne. *Clinical Practice Guidelines: Community acquired pneumonia*. Last updated October 2023. https://www.rch.org.au/clinicalguide/guideline_index/Community_acquired_pneumonia/ — retrieved 2026-09-23. | **quoted, re-checkable** |

⚠️ **`verifier_class: single_verifier_uncalibrated` — written and checked by one model, reviewed by nobody.**
