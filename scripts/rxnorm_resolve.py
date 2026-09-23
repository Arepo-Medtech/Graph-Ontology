#!/usr/bin/env python
"""Second-pass, auditable RxNorm resolution for every SNOMED CT-AU substance used as an AMT ingredient.

Methods, applied in order; the first that yields an IN/PIN/MIN wins and is recorded as `method`:

  1. rxnav-snomedct-id        RxNav id map (RxNorm's own SNOMEDCT_US atoms) - authoritative, corrects
                              the by-name pass (e.g. Morphine sulfate had landed on morphine hydrochloride).
  2. snomed-ancestor          AU-only salts/hydrates: nearest |is a| ancestor (<=3 hops) resolved by
                              method 1 whose preferred term is a prefix of the child's (records via/hops).
  3. rxnav-by-name-verified   legacy by-name hit whose RxNorm name (or RxNorm synonym) equals one of the
                              concept's descriptions after British->American normalisation.
  4. rxnav-approximate-verified  RxNav approximateTerm candidate that passes the same equality test.
  5. rxnav-name-preparation   RxNorm '<name> preparation' / '<name> extract' forms for botanicals (low tier).
  Otherwise: not-applicable:<bucket> (vaccine antigen, allergen, excipient, medical food) or unresolved,
  with the top approximate candidates kept in `candidates` for human review.

Legacy by-name hits that fail verification are demoted (rxcui=None, method rxnav-by-name-unverified) and
listed in out/rxnorm_review.tsv. Output: cache/rxnorm_substances.json (schema v2, one record per substance)
and out/rxnorm_resolution_report.md. Re-runnable: RxNav responses are cached in cache/rxnav_*.json.
Run with AU_RF2_SNAPSHOT set, then rebuild with build_compendium.py."""
from __future__ import annotations

import base64
import collections
import http.client
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb

RF2 = os.environ.get("AU_RF2_SNAPSHOT",
                     "/Users/ken-lee-arepo/Documents/ONTOLOGIES/SnomedCT_Release_AU1000036_20260831/Snapshot")
REL = "20260831"
CACHE = Path("cache")
OUT = Path("out")
SUBS_OUT = CACHE / "rxnorm_substances.json"
LEGACY_BACKUP = CACHE / "rxnorm_substances.v1-by-name.json"
INGREDIENTS_CACHE = CACHE / "rxnav_ingredients.json"  # allconcepts?tty=IN+PIN+MIN, one bulk call
IDMAP_CACHE = CACHE / "rxnav_snomedct_idmap.json"
NAMES_CACHE = CACHE / "rxnav_rxcui_names.json"
APPROX_CACHE = CACHE / "rxnav_approximate.json"
RXNAV = "https://rxnav.nlm.nih.gov/REST"
ING_TYPES = ("127489000", "762949000")
ISA = "116680003"
FSN, PREFERRED = "900000000000003001", "900000000000548007"
ING_TTY = ("IN", "PIN", "MIN")
WORKERS = 8
# generic hierarchy roots that must never act as a salt/hydrate parent
GENERIC_ROOTS = {"105590001", "410942007", "312413006", "259094000", "418743003", "373873005"}

_session_calls = 0
_statuses = collections.Counter()  # HTTP statuses / exceptions seen, printed after each fill
_local = threading.local()


def _conn() -> http.client.HTTPSConnection:
    """One keep-alive HTTPS connection per worker thread (the TLS handshake dominates per-call latency)."""
    c = getattr(_local, "conn", None)
    if c is None:
        proxy = urllib.request.getproxies().get("https")  # honour https_proxy (sandboxed sessions route through one)
        if proxy:
            u = urllib.parse.urlsplit(proxy)
            c = http.client.HTTPSConnection(u.hostname, u.port or 8080, timeout=60)
            hdrs = {}
            if u.username:
                cred = f"{urllib.parse.unquote(u.username)}:{urllib.parse.unquote(u.password or '')}"
                hdrs["Proxy-Authorization"] = "Basic " + base64.b64encode(cred.encode()).decode()
            c.set_tunnel("rxnav.nlm.nih.gov", 443, headers=hdrs)
        else:
            c = http.client.HTTPSConnection("rxnav.nlm.nih.gov", timeout=60)
        _local.conn = c
    return c


def rxnav(path: str, **params) -> dict:
    global _session_calls
    _session_calls += 1
    q = f"?{urllib.parse.urlencode(params)}" if params else ""
    for attempt in range(5):
        try:
            c = _conn()
            c.request("GET", f"/REST/{path}{q}", headers={"Accept": "application/json",
                      "User-Agent": "arepo-au-medicines-compendium/0.2 (rxnorm_resolve)"})
            resp = c.getresponse()
            body = resp.read().decode("utf-8")
            _statuses[resp.status] += 1
            if resp.status == 404:
                return {}
            if resp.status != 200:
                raise OSError(f"HTTP {resp.status}")
            return json.loads(body) if body.strip().startswith("{") else {}
        except Exception as e:  # noqa: BLE001
            _statuses[type(e).__name__] += 1
            _local.conn = None
            time.sleep(1.5 ** attempt)
    _statuses["gave-up"] += 1
    return {}


class JsonCache:
    def __init__(self, path: Path):
        self.path, self.d = path, (json.load(open(path)) if path.exists() else {})

    def save(self):
        self.path.write_text(json.dumps(self.d))

    def fill(self, keys, fn, label):
        todo = [k for k in dict.fromkeys(keys) if k not in self.d]
        print(f"  {label}: {len(todo):,} RxNav calls ({len(keys) - len(todo):,} cached)", flush=True)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for i, (k, v) in enumerate(zip(todo, ex.map(fn, todo)), 1):
                self.d[k] = v
                if i % 500 == 0:
                    self.save()
                    print(f"    {i:,}/{len(todo):,}", flush=True)
        self.save()
        print(f"    statuses so far: {dict(_statuses)}", flush=True)


class IngredientTable:
    """rxcui -> {name, tty} for every RxNorm IN/PIN/MIN, from one bulk allconcepts call (cached)."""

    def __init__(self):
        if INGREDIENTS_CACHE.exists():
            self.d = json.load(open(INGREDIENTS_CACHE))
        else:
            g = rxnav("allconcepts.json", tty="IN PIN MIN").get("minConceptGroup") or {}
            self.d = {c["rxcui"]: {"name": c["name"], "tty": c["tty"]} for c in g.get("minConcept") or []}
            if len(self.d) < 10000:
                raise SystemExit(f"allconcepts returned only {len(self.d)} ingredients; refusing to continue")
            INGREDIENTS_CACHE.write_text(json.dumps(self.d))
        print(f"RxNorm ingredient table: {len(self.d):,} IN/PIN/MIN", flush=True)


# --- name normalisation --------------------------------------------------------------------------
_BRIT = [(r"sulph", "sulf"), (r"aluminium", "aluminum"), (r"oestr", "estr"), (r"haem", "hem"), (r"anaes", "anes"),
         (r"paed", "ped"), (r"oedema", "edema"), (r"\bhcl\b", "hydrochloride"), (r"\bvit\b", "vitamin"),
         (r"caesium", "cesium"), (r"\bcolour", "color"), (r"tiot", "thiot"), (r"guaiph", "guaif"),
         (r"beclometasone", "beclomethasone"), (r"\bl-", "levo"), (r"\bdl-", "")]


SALT_TOKENS = {"hydrochloride", "dihydrochloride", "hydrobromide", "sulfate", "bisulfate", "hemisulfate", "citrate", "nitrate",
               "acetate", "diacetate", "phosphate", "diphosphate", "hydrogen", "sodium", "disodium", "potassium", "dipotassium",
               "calcium", "magnesium", "zinc", "lithium", "ammonium", "mesylate", "mesilate", "maleate", "malate", "tartrate",
               "bitartrate", "bromide", "chloride", "iodide", "fluoride", "succinate", "fumarate", "besylate", "besilate",
               "tosylate", "tosilate", "lactate", "gluconate", "stearate", "palmitate", "propionate", "valerate", "benzoate",
               "salicylate", "pamoate", "embonate", "oxalate", "carbonate", "bicarbonate", "oxide", "hydroxide", "monohydrate",
               "dihydrate", "trihydrate", "tetrahydrate", "pentahydrate", "hexahydrate", "heptahydrate", "hemihydrate",
               "sesquihydrate", "hydrate", "anhydrous", "dihydrogen", "trisodium", "tromethamine", "meglumine", "edetate",
               "aspartate", "glutamate", "orotate", "picolinate", "nicotinate", "ascorbate", "pidolate", "glycinate",
               "chelate", "ester", "esters", "decanoate", "enantate", "enanthate", "undecanoate", "cypionate", "caproate",
               "dipropionate", "furoate", "butyrate", "pivalate", "trifluoroacetate", "xinafoate", "napsylate", "napsilate",
               "hyclate", "monosodium", "hemicalcium", "hemifumarate", "hemitartrate", "sesquihydrate", "monobasic", "dibasic",
               "tribasic", "acid", "base", "salt"}


def norm_tokens(s: str) -> list[str]:
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s.lower().strip())
    for a, b in _BRIT:
        s = re.sub(a, b, s)
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def norm(s: str) -> str:
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s.lower().strip())  # trailing (tag) / (source)
    for a, b in _BRIT:
        s = re.sub(a, b, s)
    return re.sub(r"[^a-z0-9]+", "", s)


# --- not-applicable buckets ---------------------------------------------------------------------
NA_SKIP = r"immunoglobulin|immune globulin|antiserum|antivenom|antivenin|antitoxin"  # real RxNorm ingredients may exist
NA_RULES = [
    ("substance grouper / pharmacological class", r"and/or|\bagonist\b|\bantagonist\b|\binhibitor\b|\bblocker\b|"
     r"\bderivatives?\b|\bcompounds?\b|\banalogues?\b|\bmodulator\b|\bstimulant\b|\bmimetic\b|\bproducts?\b|"
     r"\bsubstance\b$|\bagent\b$|\bpreparation\b$"),
    ("vaccine antigen / strain", r"like (virus|strain)|\bvirus\b|\bantigen\b|toxoid|serotype|serogroup|\bstrain\b|"
     r"conjugate|polysaccharide|pertussis|diphtheriae|tetani|haemophilus|poliovirus|hepatitis|influenza|pneumoniae|"
     r"meningitidis|papillomavirus|rotavirus|varicella|measles|mumps|rubella|zoster|rabies|typhi|cholera|encephalitis|"
     r"yellow fever|bacillus calmette|\bbcg\b|virus-like|inactivated|attenuated"),
    ("allergen extract", r"\ballergen\b|pollen|venom|dust mite|dander|mixed grass|\bmite\b|\bmould\b|\bmold\b|"
     r"feathers?|epitheli|salivary|\bhair\b|\bfur\b|\bwool\b|\bserum protein"),
    ("excipient / vehicle", r"inert substance|water for injection|purified water|aqueous cream|excipient|vehicle|"
     r"diluent|placebo|\bemollient\b|\bbase\b$"),
    ("medical food / formula", r"amino acid formula|formula with|glycomacropeptide|medical food|infant formula|"
     r"protein supplement|carbohydrate supplement|\bfeed\b|nutritional|\bformula\b"),
    ("cell / gene / tissue therapy", r"\bcells?\b|autologous|allogeneic|\bgene\b|tissue|\bplasma\b|\bplatelet"),
]


def na_bucket(names: list[str]) -> str | None:
    text = " | ".join(names).lower()  # preferred term + FSN only; synonyms mislead ("T-cell growth factor")
    if re.search(NA_SKIP, text):
        return None
    for label, rx in NA_RULES:
        if re.search(rx, text):
            return label
    return None


# --- main -------------------------------------------------------------------------------------------
def main() -> int:
    OUT.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute(f"""
    CREATE VIEW dsc AS SELECT * FROM read_csv('{RF2}/Terminology/sct2_Description_Snapshot-en-au_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
    CREATE VIEW rel AS SELECT * FROM read_csv('{RF2}/Terminology/sct2_Relationship_Snapshot_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
    CREATE VIEW lang AS SELECT * FROM read_csv('{RF2}/Refset/Language/der2_cRefset_LanguageSnapshot-en-au_AU1000036_{REL}.txt', delim='\t', header=true, quote='', all_varchar=true);
    CREATE TABLE used AS SELECT DISTINCT destinationId AS id FROM rel WHERE active='1' AND typeId IN {ING_TYPES};
    CREATE TABLE names AS
      SELECT d.conceptId AS id,
             CASE WHEN d.typeId='{FSN}' THEN regexp_replace(d.term, ' \\([^()]+\\)$', '') ELSE d.term END AS term,
             d.typeId='{FSN}' AS is_fsn,
             bool_or(l.acceptabilityId='{PREFERRED}') AS preferred
      FROM dsc d LEFT JOIN lang l ON l.referencedComponentId=d.id AND l.active='1'
      WHERE d.active='1' AND d.conceptId IN (SELECT id FROM used)
      GROUP BY 1,2,3;
    """)
    subs: dict[str, dict] = {}
    for sid, term, is_fsn, pref in con.execute("SELECT id, term, is_fsn, preferred FROM names ORDER BY 1, is_fsn DESC, preferred DESC, term").fetchall():
        rec = subs.setdefault(sid, {"pt": None, "fsn": None, "names": []})
        if is_fsn:
            rec["fsn"] = term
        elif pref and not rec["pt"]:
            rec["pt"] = term
        rec["names"].append(term)
    for rec in subs.values():
        rec["pt"] = rec["pt"] or rec["fsn"] or rec["names"][0]
        rec["norms"] = {norm(n) for n in rec["names"]} - {""}
    print(f"substances used as ingredients: {len(subs):,}", flush=True)

    # parents among ALL concepts (ancestors may not themselves be ingredients) - walk up to 3 hops
    parents = collections.defaultdict(set)
    for c, p in con.execute(f"SELECT sourceId, destinationId FROM rel WHERE active='1' AND typeId='{ISA}'").fetchall():
        parents[c].add(p)
    anc_names = {}

    def name_of(sid: str) -> str:
        if sid in subs:
            return subs[sid]["pt"]
        if sid not in anc_names:
            r = con.execute(f"""SELECT d.term FROM dsc d JOIN lang l ON l.referencedComponentId=d.id AND l.active='1' AND l.acceptabilityId='{PREFERRED}'
                                WHERE d.conceptId=? AND d.active='1' AND d.typeId<>'{FSN}' LIMIT 1""", [sid]).fetchone()
            anc_names[sid] = r[0] if r else ""
        return anc_names[sid]

    # legacy (v1 by-name) results
    legacy = {}
    if SUBS_OUT.exists():
        raw = json.load(open(SUBS_OUT))
        if raw and "method" not in next(iter(raw.values())):
            if not LEGACY_BACKUP.exists():
                LEGACY_BACKUP.write_text(json.dumps(raw))
            legacy = raw
        elif LEGACY_BACKUP.exists():
            legacy = json.load(open(LEGACY_BACKUP))
    print(f"legacy by-name hits: {sum(1 for v in legacy.values() if v.get('rxcui')):,}", flush=True)

    # --- phase 1: SNOMED CT id map -----------------------------------------------------------------
    idmap = JsonCache(IDMAP_CACHE)
    idmap.fill(list(subs), lambda sid: ((rxnav("rxcui.json", idtype="SNOMEDCT", id=sid).get("idGroup") or {}).get("rxnormId") or []),
               "phase 1 idtype=SNOMEDCT")
    props = IngredientTable()  # any rxcui absent from it is not an ingredient

    result: dict[str, dict] = {}

    def ingredient_of(ids: list[str]) -> dict | None:
        for r in ids:
            p = props.d.get(r) or {}
            if p.get("tty") in ING_TTY:
                return {"rxcui": r, "name": p["name"], "tty": p["tty"]}
        return None

    for sid, rec in subs.items():
        hit = ingredient_of(idmap.d.get(sid, []))
        if hit:
            result[sid] = {**hit, "method": "rxnav-snomedct-id"}
        elif idmap.d.get(sid):
            rec["mapped_non_ingredient"] = idmap.d[sid]
    print(f"phase 1: {len(result):,} resolved by SNOMED CT id map", flush=True)

    # --- phase 2: ancestor walk (AU salts/hydrates) ----------------------------------------------
    n2 = 0
    for sid, rec in subs.items():
        if sid in result:
            continue
        child = norm(rec["pt"])
        frontier, seen, hops, found = {sid}, {sid}, 0, None
        while frontier and hops < 3 and not found:
            hops += 1
            nxt = set()
            for c in frontier:
                nxt |= parents.get(c, set())
            nxt -= seen
            seen |= nxt
            cands = []
            for a in nxt:
                if a in GENERIC_ROOTS or a not in result or result[a]["method"] != "rxnav-snomedct-id":
                    continue
                an = norm(name_of(a))
                if an and len(an) >= 4 and child.startswith(an):
                    cands.append((-len(an), a))
            if cands:
                found = sorted(cands)[0][1]
            frontier = nxt
        if found:
            n2 += 1
            result[sid] = {**{k: result[found][k] for k in ("rxcui", "name", "tty")}, "method": "snomed-ancestor",
                           "via_sctid": found, "via_name": name_of(found), "hops": hops}
    print(f"phase 2: {n2:,} resolved via SNOMED ancestor", flush=True)

    # --- phase 3: verify legacy by-name hits -----------------------------------------------------
    names_c = JsonCache(NAMES_CACHE)

    def fetch_names(rxcui: str) -> list[str]:
        g = rxnav(f"rxcui/{rxcui}/allProperties.json", prop="names").get("propConceptGroup") or {}
        return sorted({p["propValue"] for p in (g.get("propConcept") or []) if p.get("propValue")})

    def verified(sid: str, rxcui: str) -> bool:
        p = props.d.get(rxcui) or {}
        if p.get("tty") not in ING_TTY:
            return False
        if norm(p.get("name") or "") in subs[sid]["norms"]:
            return True
        return any(norm(n) in subs[sid]["norms"] for n in names_c.d.get(rxcui, []))

    pending3 = {sid: legacy[sid]["rxcui"] for sid in subs if sid not in result and legacy.get(sid, {}).get("rxcui")}
    names_c.fill([r for sid, r in pending3.items() if norm((props.d.get(r) or {}).get("name") or "") not in subs[sid]["norms"]],
                 fetch_names, "phase 3 RxNorm synonyms")
    n3 = n3u = 0
    for sid, r in pending3.items():
        p = props.d.get(r) or {}
        if verified(sid, r):
            n3 += 1
            result[sid] = {"rxcui": r, "name": p.get("name"), "tty": p.get("tty"), "method": "rxnav-by-name-verified"}
        else:
            n3u += 1
            subs[sid]["legacy_unverified"] = {"rxcui": r, "name": p.get("name"), "tty": p.get("tty")}
    print(f"phase 3: {n3:,} legacy by-name hits verified, {n3u:,} demoted to review", flush=True)

    # --- phase 4: approximate match with the same verification ------------------------------------
    approx = JsonCache(APPROX_CACHE)
    remaining = [sid for sid in subs if sid not in result]

    def fetch_approx(term: str) -> list[dict]:
        g = rxnav("approximateTerm.json", term=term, maxEntries=8).get("approximateGroup") or {}
        out, seen = [], set()
        for c in g.get("candidate") or []:
            if c.get("rxcui") and c["rxcui"] not in seen:
                seen.add(c["rxcui"])
                out.append({"rxcui": c["rxcui"], "score": float(c.get("score") or 0), "name": c.get("name")})
        return out

    approx.fill([subs[sid]["pt"] for sid in remaining], fetch_approx, "phase 4 approximateTerm")
    names_c.fill([c["rxcui"] for sid in remaining for c in approx.d.get(subs[sid]["pt"], [])
                  if (props.d.get(c["rxcui"]) or {}).get("tty") in ING_TTY], fetch_names, "phase 4 RxNorm synonyms")
    n4 = n5 = n6 = 0
    for sid in remaining:
        cands = approx.d.get(subs[sid]["pt"], [])
        chosen = None
        for c in cands:
            if verified(sid, c["rxcui"]):
                chosen = ("rxnav-approximate-verified", c)
                break
        if not chosen:  # botanical preparation / extract forms
            for c in cands:
                p = props.d.get(c["rxcui"]) or {}
                if p.get("tty") not in ING_TTY:
                    continue
                pn = norm(p.get("name") or "")
                for sfx in ("preparation", "wholeextract", "extract"):
                    if pn.endswith(sfx) and pn[:-len(sfx)] in subs[sid]["norms"]:
                        chosen = ("rxnav-name-preparation", c)
                        break
                if chosen:
                    break
        if not chosen:  # salt/ester/hydrate with no RxNorm entry of its own -> base ingredient (precision loss recorded)
            for c in cands:
                p = props.d.get(c["rxcui"]) or {}
                if p.get("tty") != "IN":
                    continue
                base = norm(p.get("name") or "")
                if len(base) < 5:
                    continue
                for n in subs[sid]["names"]:
                    toks = norm_tokens(n)
                    if toks and toks[0] == base and 1 <= len(toks) - 1 <= 3 and all(t in SALT_TOKENS for t in toks[1:]):
                        chosen = ("rxnav-base-of-salt", c)
                        break
                if chosen:
                    break
        if chosen:
            m, c = chosen
            p = props.d[c["rxcui"]]
            result[sid] = {"rxcui": c["rxcui"], "name": p["name"], "tty": p["tty"], "method": m, "score": c["score"]}
            n4 += m == "rxnav-approximate-verified"
            n5 += m == "rxnav-name-preparation"
            n6 += m == "rxnav-base-of-salt"
        else:
            subs[sid]["candidates"] = [{**c, **(props.d.get(c["rxcui"]) or {})} for c in cands[:3]
                                       if (props.d.get(c["rxcui"]) or {}).get("tty") in ING_TTY]
    print(f"phase 4: {n4:,} approximate-verified, {n5:,} preparation/extract forms, {n6:,} base-of-salt", flush=True)

    # --- unresolved: bucket ---------------------------------------------------------------------
    for sid, rec in subs.items():
        if sid in result:
            continue
        b = na_bucket([rec["pt"], rec["fsn"] or ""])
        result[sid] = {"rxcui": None, "name": None, "tty": None,
                       "method": f"not-applicable:{b}" if b else ("rxnav-by-name-unverified" if rec.get("legacy_unverified") else "unresolved")}

    # --- assemble + write -------------------------------------------------------------------------
    final = {}
    for sid, rec in subs.items():
        r = dict(result[sid])
        r["pt"] = rec["pt"]
        lg = legacy.get(sid, {})
        if lg.get("rxcui"):
            r["legacy_rxcui"], r["legacy_name"] = lg["rxcui"], lg.get("name")
        for k in ("candidates", "mapped_non_ingredient", "legacy_unverified"):
            if rec.get(k):
                r[k] = rec[k]
        final[sid] = r
    SUBS_OUT.write_text(json.dumps(final, indent=0))

    by_method = collections.Counter(r["method"] for r in final.values())
    resolved = sum(1 for r in final.values() if r["rxcui"])
    changed = [(sid, r) for sid, r in final.items() if r.get("legacy_rxcui") and r["rxcui"] and r["rxcui"] != r["legacy_rxcui"]]
    lines = ["# RxNorm resolution report", "",
             f"Substances used as AMT ingredients: {len(final):,}. Resolved to an RxNorm IN/PIN/MIN: {resolved:,} "
             f"(legacy by-name pass: {sum(1 for v in legacy.values() if v.get('rxcui')):,}). RxNav calls this run: {_session_calls:,}.", "",
             "| method | substances |", "|---|---|"]
    lines += [f"| {m} | {n:,} |" for m, n in by_method.most_common()]
    lines += ["", f"## Legacy hits corrected by a stronger method ({len(changed):,})", "",
              "| sctid | AU preferred term | was (v1 by-name) | now | method |", "|---|---|---|---|---|"]
    lines += [f"| {sid} | {r['pt']} | {r['legacy_rxcui']} {r['legacy_name']} | {r['rxcui']} {r['name']} ({r['tty']}) | {r['method']} |"
              for sid, r in sorted(changed, key=lambda x: x[1]["pt"])[:400]]
    (OUT / "rxnorm_resolution_report.md").write_text("\n".join(lines) + "\n")

    with open(OUT / "rxnorm_review.tsv", "w") as fh:
        fh.write("sctid\tpt\tstatus\tlegacy_rxcui\tlegacy_name\tcand1\tcand2\tcand3\n")
        for sid, r in sorted(final.items(), key=lambda x: x[1]["pt"]):
            if r["rxcui"]:
                continue
            lu = r.get("legacy_unverified") or {}
            cands = [f"{c['rxcui']} {c.get('name')} ({c.get('tty')}, {c['score']:.0f})" for c in r.get("candidates", [])] + ["", "", ""]
            fh.write("\t".join([sid, r["pt"], r["method"], lu.get("rxcui") or "", lu.get("name") or "", *cands[:3]]) + "\n")
    print("\n".join(lines[:6 + len(by_method)]), flush=True)
    print(f"wrote {SUBS_OUT}, {OUT/'rxnorm_resolution_report.md'}, {OUT/'rxnorm_review.tsv'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
