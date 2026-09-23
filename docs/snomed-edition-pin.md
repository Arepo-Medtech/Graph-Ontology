# Which SNOMED CT-AU edition, and should the pin move?

**Checked 2026-09-23 against the live server.**

## They are not two things

> ⚠️ **"Live Ontoserver" and "the NCTS validation" are the same server.** The NCTS *is* an Ontoserver
> deployment. Both the compendium's binder and the validation client hit
> `api.healthterminologies.gov.au`.

The real distinction is **pinned edition vs the server's default**, which is a choice this repo makes on
every call, not a difference between services.

## What the server holds

| edition | on the server | notes |
|---|---|---|
| `20260731` | ✅ | **what this repo pins**, and what the 301-code validation used |
| `20260831` | ✅ | ⚠️ **newer, and what an UNPINNED query answers from today** |

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

## What follows

**The pin is not doing harm — but it is not free either.** The exposure is precise: anyone querying the
server *without* the pin gets a display for `254637007` that differs from the one this repo records.
That is one row of 301.

**Keep pinning.** The client's own reasoning stands: *"Pinning makes answers reproducible; unpinned
queries answer from whatever the server's default edition is that day."* An unpinned corpus would drift
silently every month.

**But move the pin deliberately, and record the move.** The cost of a bump to `20260831` is now measured
rather than guessed: **one display string, no retirements**. That is the cheapest a bump is ever likely
to be.

⚠️ **A bump is not a code change alone.** `reference/snomed_bindings.json` carries
`SNOMED CT-AU 20260731 (pinned)` in its `source`, and `reference/binding_validation.json` records the
version every code was checked at. Moving the pin means re-running the binder, re-applying corrections
through `apply_corrections.py`, and re-validating — **which is exactly the sequence `apply_corrections.py`
exists to survive.**

**Not done.** Moving a terminology pin changes what every binding in the repo means, and that is the
user's call, not a cleanup.

## Reproduce

```bash
cd "<reasonmed>" && node --env-file=.env <script>    # credentials are read by node, never printed
```

Two probes: `CodeSystem?url=http://snomed.info/sct&_summary=true` for the editions held, and
`$validate-code` with and without `&version=` for the default.
