# Which SNOMED CT-AU edition, and should the pin move?

**Checked 2026-09-23 against the live server. ✅ PIN BUMPED TO `20260831` the same day; the local RF2 release followed on 2026-09-24.**

## They are not two things

> ⚠️ **"Live Ontoserver" and "the NCTS validation" are the same server.** The NCTS *is* an Ontoserver
> deployment. Both the compendium's binder and the validation client hit
> `api.healthterminologies.gov.au`.

The real distinction is **pinned edition vs the server's default**, which is a choice this repo makes on
every call, not a difference between services.

## What the server holds

| edition | on the server | notes |
|---|---|---|
| `20260731` | ✅ | the previous pin; what the first 301-code validation used |
| `20260831` | ✅ | ✅ **the pin as of 2026-09-23**, and what an unpinned query also answers from |

Confirmed directly: `CodeSystem?url=http://snomed.info/sct` returns both, and an unpinned
`$validate-code` for `22298006` answers `Myocardial infarction` at **`.../version/20260831`**.

**So yes — a more current edition is live and available, and the repo is one monthly release behind it.**

## Does it change anything? Measured, not assumed

All **301** distinct candidate codes were re-validated against **both** editions in one pass:

| | |
|---|---:|
| codes checked | **301** |
| retired or absent in August | **0** |
| new in August | **0** |
| **display changed** | **1** |
| unvalidated in either | 0 |

The single difference:

| code | July `20260731` | August `20260831` |
|---|---|---|
| `254637007` | Non-small cell lung **cancer** | Non-small cell lung **carcinoma** |

## What was done

**The pin was bumped to `20260831` on 2026-09-23**, after the cost was measured rather than guessed.

> ### ⚠️ THE PIN HAS ONE HOME, AND IT IS MACHINE-WIDE
> `reasonmed/ncts-client.mjs` holds it: *"NCTS client path is configurable; it holds the OAuth flow and
> the release pin."* The compendium's `bind_ontoserver.mjs` **imports that client and inherits the pin** —
> it never sets one.
>
> **That client is a shared machine resource.** Bumping it changes the edition every project on this
> machine resolves against, not just this repo. Backup at `/tmp/ncts-client.mjs.bak`.

Changed:

| file | change |
|---|---|
| `reasonmed/ncts-client.mjs` | `AU_VERSION` → `.../version/20260831`, with the measurement recorded in the comment |
| `scripts/bind_ontoserver.mjs` | pin comment, and the `source` string **future runs** will write |
| `reference/binding_validation.json` | all 301 codes re-validated at the new pin |

## ⚠️ Two things deliberately NOT changed

**1. `reference/snomed_bindings.json` still records `SNOMED CT-AU 20260731 (pinned)`.**
That string describes **what was actually produced**, and the file's contents were produced at
`20260731`. Editing it without re-running the binder would make the provenance a lie.

> **It is now stale relative to the pin.** Closing that gap means the full sequence:
> ```bash
> node --env-file=<env> scripts/bind_ontoserver.mjs out/conditions.json reference/snomed_bindings.json
> python3 scripts/apply_corrections.py      # restores every human decision
> python3 scripts/validate_bindings_ncts.py
> ```
> **Not run** — it rewrites all 639 bindings over the wire, and `apply_corrections.py` exists precisely
> so that doing it later loses nothing.

**2. The local RF2 release — moved to `20260831` on 2026-09-24.**
The downloaded bundle is now SNOMED CT-AU 20260831 (`NCTS_SCT_RF2_DISTRIBUTION_32506021000036107-20260831-ALL.zip`, Snapshot
only unpacked to `~/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/`), and `REL` / the default `AU_RF2_SNAPSHOT`
in `build_compendium.py`, `rxnorm_enrich.py`, `rxnorm_resolve.py` and `drug_strength.py`, the graph's `PIN["sct"]` and
`graph_register.py` all say `20260831`. The compendium, the register and the graph were rebuilt on it; the July release
is no longer on this machine (the July build is kept in `cache/backup-20260731/`).

What moved, July → August: **+1,783 concepts, 385 retired** (278 substances, 35 disorders, 55 AMT products and
packs), 56 preferred terms renamed; +1,015 products, +7,009 SNOMED relationships; no SNOMED attribute type added or
removed; **no hand-checked route changed tier**, and **no committed reference file cites a retired code**.
343 graph edges from sources dated before the release (OMOP ancestry and maps, PBS schedule 4333, one RxNav resolution)
now point at 56 retired AMT products — the "Clexane with Automatic Safety Lock System" packs among them. They are right
for their sources and will clear as those sources move; the build names them rather than dropping them.
`rxnorm_enrich.py` / `rxnorm_resolve.py` (optional, networked) were **not** re-run: their pins moved for the next run.

## Reproduce

```bash
cd "<reasonmed>" && node --env-file=.env <script>    # credentials are read by node, never printed
```

Two probes: `CodeSystem?url=http://snomed.info/sct&_summary=true` for the editions held, and
`$validate-code` with and without `&version=` for the default.
