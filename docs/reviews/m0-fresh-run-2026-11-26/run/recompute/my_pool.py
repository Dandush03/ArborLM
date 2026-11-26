"""Auditor's independent pooling of the M0 fresh run (ADR-0033 addendum 1, section 4A stage 1S points 2, 6, 7, 8;
lead rulings R-46, R-56, R-57). Written from the text; pool_fresh.py was not imported, copied or read before this was written.
Standard library only. Exact fractions throughout. Output: rows.jsonl, per_lineage.json, notes.json in OUT_DIR.
Usage: python my_pool.py OUT_DIR
"""
import json, os, re, sys, gzip
from fractions import Fraction as F
from collections import defaultdict

IMPL = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SPEC = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126"
OUT = sys.argv[1]
SEEDS = ("1", "2", "3")
BOUND = F(3, 20)
LEVELS = range(7)
os.makedirs(OUT, exist_ok=True)

plan = json.load(open(f"{IMPL}/studies/m0/fresh_run/run_plan.json"))
surv_doc = json.load(open(f"{IMPL}/studies/m0/manifests/survivor_list_of_record.json"))
ct = json.load(open(f"{SPEC}/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"))
amend = json.load(open(f"{IMPL}/docs/reviews/m0-fresh-run-2026-11-26/amendment_audit/amendment_list.json"))
assert amend["entries"] == [], "amendment list not empty: handle"

# survivor ids, whatever the manifest's layout
def all_ids(o):
    if isinstance(o, str):
        return {o} if re.match(r"^(R1|R2|M1|C1)\.", o) else set()
    if isinstance(o, dict):
        s = set()
        for k, v in o.items():
            s |= all_ids(k) | all_ids(v)
        return s
    if isinstance(o, list):
        s = set()
        for v in o:
            s |= all_ids(v)
        return s
    return set()
SURV = all_ids(surv_doc)
notes = {"survivors_by_eval": {e: len([x for x in SURV if x.startswith(e + ".")]) for e in ("R1", "R2", "M1", "C1")}}

def fr(x):
    return F(repr(x)) if isinstance(x, float) else F(x)

def dec_unc(d):
    return F(1, 2 * 10 ** d)

ROWS = []  # every pooled row
def add(unit, src, lid, lv, rule, reading, excess, items, unc, counted, entry, extra=None):
    r = {"unit": unit, "src": src, "lineage": lid, "level": lv, "rule": rule, "reading": reading,
         "excess": excess, "items": items, "unc": unc, "counted": counted, "entry": entry}
    if extra:
        r.update(extra)
    r["over"] = counted and (abs(excess) + unc > BOUND)
    ROWS.append(r)

def outspec(unit):
    return plan["units"][unit]["outputs"]

missing = []
def need(unit, kind, lids, have):
    for lid in lids:
        for s in SEEDS:
            for lv in LEVELS:
                if (lid, s, lv) not in have:
                    missing.append((unit, kind, lid, s, lv))

# ---------------- R1 ----------------
R1E = ct["R1"]["entries"]
def r1_stem(lid):
    return re.sub(r"_r\d+$", "", lid[3:])
def r1_bare(name):
    for p in ("a3:", "a4:"):
        if name.startswith(p):
            return name[len(p):]
    return name
def r1_entry(unit, lid, rule):
    if unit not in ct["R1"]["units"]:
        return None
    b = r1_bare(rule)
    for e in R1E:
        if e["rule"] == b and (e["lineage_stems"] == "every R1 lineage" or r1_stem(lid) in e["lineage_stems"]):
            return f"R1 {e['label']} {e['rule']}"
    return None

exact_rows = []
for unit in ("R1a", "R1b"):
    o = outspec(unit)[0]
    idmap = o["id_map"]
    for kind, kd in o["kinds"].items():
        data = defaultdict(dict)  # (lid, lv, rule) -> seed -> row
        have = set()
        for s in SEEDS:
            d = f"{RUN}/{unit}/seed{s}"
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(f".{kind}.jsonl"):
                    continue
                for line in open(f"{d}/{fn}"):
                    if not line.strip():
                        continue
                    x = json.loads(line)
                    if x["lineage"] not in idmap:
                        continue
                    lid = idmap[x["lineage"]]
                    key = (lid, x["level"], x["heuristic"])
                    assert s not in data[key], ("dup", unit, kind, key, s)
                    data[key][s] = x
                    have.add((lid, s, x["level"]))
        need(unit, kind, kd["must_contain"], have)
        # exactness per (lid, rule) over all levels and seeds
        exact = defaultdict(lambda: True)
        for (lid, lv, h), by in data.items():
            ok = len(by) == 3 and all(r.get("fired") == r["n"] and r.get("acc_fired") is not None and fr(r["acc_fired"]) == 1 for r in by.values())
            exact[(lid, h)] = exact[(lid, h)] and ok
        lvcount = defaultdict(set)
        for (lid, lv, h) in data:
            lvcount[(lid, h)].add(lv)
        for (lid, h), ok in exact.items():
            if ok and len(lvcount[(lid, h)]) == 7:
                exact_rows.append({"unit": unit, "kind": kind, "lineage": lid, "rule": h, "entry": r1_entry(unit, lid, h)})
        for (lid, lv, h), by in data.items():
            ent = r1_entry(unit, lid, h)
            for reading in ("eff", "anti"):
                vals = [(s, by[s]) for s in SEEDS if s in by]
                if all(r[reading] is None for _, r in vals):
                    continue
                if any(r[reading] is None for _, r in vals):
                    notes.setdefault("r1_partial_none", []).append([unit, kind, lid, lv, h, reading])
                num = F(0); den = 0
                for s in SEEDS:
                    if s in by and by[s][reading] is not None:
                        num += by[s]["n"] * fr(by[s][reading]); den += by[s]["n"]
                    elif s not in by:
                        notes.setdefault("r1_rule_missing_in_seed", []).append([unit, kind, lid, lv, h, s])
                add(unit, kind, lid, lv, h, reading, num / den, den, dec_unc(4), ent is None, ent,
                    {"seeds": [s for s in SEEDS if s in by]})

# R1c stdout
o = outspec("R1c")[0]
data = defaultdict(dict)
pat = re.compile(r"^(\S+)\s+(.*?)\s+eff((?:\s+[+-]\d+\.\d+){7})\s+anti((?:\s+[+-]\d+\.\d+){7})\s*$")
for s in SEEDS:
    for line in open(f"{RUN}/R1c/seed{s}/stdout.txt"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        m = pat.match(line)
        if not m:
            notes.setdefault("r1c_unparsed", []).append(line[:120]); continue
        lid, name = m.group(1), m.group(2).rstrip()
        if lid not in o["id_map"]:
            continue
        lid = o["id_map"][lid]
        assert s not in data[(lid, name)]
        data[(lid, name)][s] = ([F(v) for v in m.group(3).split()], [F(v) for v in m.group(4).split()])
n_r1c = plan["units"]["R1c"]["items_per_level"]["run"]
have = {(lid, s, lv) for (lid, _), by in data.items() for s in by for lv in LEVELS}
need("R1c", "stdout", o["must_contain"], have)
for (lid, name), by in data.items():
    for i, reading in enumerate(("eff", "anti")):
        for lv in LEVELS:
            vals = [by[s][i][lv] for s in SEEDS if s in by]
            den = n_r1c * len(vals)
            add("R1c", "new", lid, lv, name, reading, sum(vals) * n_r1c / den, den, F(55, 100000), True, None,
                {"seeds": [s for s in SEEDS if s in by]})

# ---------------- R2 ----------------
R2E = ct["R2"]["entries"]
R2NEW_E = ct["R2"]["new_rules"]["entries"]
def r2_stem(lid):
    return lid[3:]
def r2_class(lid, name, shape, lv):
    """returns (uncounted_label or None, entry text)"""
    if name.startswith("[NEW] "):
        for e in R2NEW_E:
            if e["rule"] == name and e["lineage_stem"] == r2_stem(lid):
                return e["label"], e["rule"]
        return None, None
    for e in sorted(R2E, key=lambda e: e["order"]):
        m = e["match"]; t = e["text"]
        if m == "name contains":
            hit = t in name
        elif m == "name equal":
            hit = name == t
        elif m == "name starts with":
            hit = name.startswith(t)
        elif m == "name equal, and shape equal":
            hit = name == t and shape == e["shape"]
        elif m == "name equal, and level 0":
            hit = name == t and lv == 0
        else:
            raise ValueError(m)
        if hit:
            return e["label"], f"{e['order']}:{t}"
    return None, None

SHAPE_DEP = [e for e in R2E if e["match"] == "name equal, and shape equal"]
SHAPE_DEP_NAMES = {e["text"] for e in SHAPE_DEP}
for unit in ("R2a", "R2b"):
    for o in outspec(unit):
        fn = o["file"]; idmap = o["id_map"]
        # per seed: lid -> lv -> shape -> entry
        seeds = {}
        for s in SEEDS:
            d = json.load(open(f"{RUN}/{unit}/seed{s}/{fn}"))
            seeds[s] = {idmap[l]: v for l, v in d["lineages"].items() if l in idmap}
            for l in d["lineages"]:
                if l not in idmap:
                    notes.setdefault("r2_unmapped", []).append([unit, fn, l])
        have = {(lid, s, int(lv)) for s in SEEDS for lid, L in seeds[s].items() for lv in L}
        need(unit, fn, o["must_contain"], have)
        lids = sorted(set().union(*(seeds[s].keys() for s in SEEDS)))
        for lid in lids:
            for lv in LEVELS:
                # answer-type groups
                groups = defaultdict(lambda: {"n": 0, "nseed": defaultdict(int), "shapes": set()})
                shape_at = {}
                for s in SEEDS:
                    for sh, e in seeds[s].get(lid, {}).get(str(lv), {}).items():
                        at = e["answer_type"]
                        assert shape_at.setdefault(sh, at) == at, (lid, lv, sh)
                        g = groups[at]; g["n"] += e["n"]; g["nseed"][s] += e["n"]; g["shapes"].add(sh)
                if len(groups) > 1:
                    notes.setdefault("r2_mixed_answer_types", []).append([unit, fn, lid, lv, sorted(groups)])
                for at, g in groups.items():
                    names = set()
                    for s in SEEDS:
                        for sh, e in seeds[s].get(lid, {}).get(str(lv), {}).items():
                            if e["answer_type"] == at:
                                names |= set(e["rules"])
                    for name in sorted(names):
                        k = 0; napp = 0; named = set()
                        per_shape = defaultdict(lambda: [0, 0, 0])  # shape -> k, napp, n
                        for s in SEEDS:
                            for sh, e in seeds[s].get(lid, {}).get(str(lv), {}).items():
                                if e["answer_type"] != at:
                                    continue
                                per_shape[sh][2] += e["n"]
                                if name in e["rules"]:
                                    v = e["rules"][name]; named.add(s)
                                    k += v["k"]; napp += v["napp"]
                                    per_shape[sh][0] += v["k"]; per_shape[sh][1] += v["napp"]
                        if name in SHAPE_DEP_NAMES:
                            # read per shape on the shapes where it counts; the uncounted shape is left out
                            for sh, (ks, nas, ns) in sorted(per_shape.items()):
                                lab, ent = r2_class(lid, name, sh, lv)
                                if at == "yn":
                                    if nas:
                                        add(unit, fn, lid, lv, name, "k_over_napp-0.5", F(ks, nas) - F(1, 2), nas, F(0), lab is None, ent, {"shape": sh, "answer_type": at})
                                else:
                                    add(unit, fn, lid, lv, name, "k_over_n", F(ks, ns), ns, F(0), lab is None, ent, {"shape": sh, "answer_type": at})
                                    if "[cond]" in name and nas:
                                        add(unit, fn, lid, lv, name, "k_over_napp", F(ks, nas), nas, F(0), lab is None, ent, {"shape": sh, "answer_type": at})
                            continue
                        lab, ent = r2_class(lid, name, None, lv)
                        ex = {"answer_type": at, "named_in": sorted(named)}
                        if at == "yn":
                            if napp:
                                add(unit, fn, lid, lv, name, "k_over_napp-0.5", F(k, napp) - F(1, 2), napp, F(0), lab is None, ent, ex)
                        else:
                            add(unit, fn, lid, lv, name, "k_over_n", F(k, g["n"]), g["n"], F(0), lab is None, ent, ex)
                            if "[cond]" in name and napp:
                                add(unit, fn, lid, lv, name, "k_over_napp", F(k, napp), napp, F(0), lab is None, ent, ex)

# ---------------- M1 ----------------
M1E = ct["M1"]["entries"]
def m1_stem(lid):
    return re.sub(r"_r[234]$", "", lid[3:])
def m1_entry(lid, key):
    for e in M1E:
        if e["lineage_stem"] == m1_stem(lid) and e["rule"] == key:
            return f"M1 {e['label']} {e['rule']}"
    return None
def is_rule_key(k):
    return not k.endswith("__within_applicable")

def m1_pool(unit, src, lid, lv, rows_by_seed, prefix, dec, bracket=False):
    """rows_by_seed: seed -> row {N, base, rates}"""
    Ns = {s: r["N"] for s, r in rows_by_seed.items()}
    Ntot = sum(Ns.values())
    if len(rows_by_seed) != 3:
        notes.setdefault("m1_level_missing_seed", []).append([unit, src, lid, lv, sorted(rows_by_seed)])
    base = sum(Ns[s] * fr(r["base"]) for s, r in rows_by_seed.items()) / Ntot
    u = dec_unc(dec)
    # base as the rule "most frequent answer", against chance 0
    add(unit, src, lid, lv, f"{src}:base(most frequent answer)", "vs_chance", base, Ntot, u, True, None)
    keys = set()
    for r in rows_by_seed.values():
        keys |= {k for k in r["rates"] if is_rule_key(k)}
    def emit(name, rate, tag):
        ent = m1_entry(lid, name)
        add(unit, src, lid, lv, name, "vs_chance", rate, Ntot, u, ent is None, ent, tag)
        add(unit, src, lid, lv, name, "vs_base", rate - base, Ntot, 2 * u, ent is None, ent, tag)
    for k in sorted(keys):
        name = prefix + k
        rate = sum(Ns[s] * fr(r["rates"].get(k, 0)) for s, r in rows_by_seed.items()) / Ntot
        emit(name, rate, {"named_in": sorted(s for s, r in rows_by_seed.items() if k in r["rates"])})
    if bracket:
        groups = defaultdict(set)
        for k in keys:
            m = re.match(r"^(.*?)\[.*\]$", k)
            if m:
                groups[m.group(1)].add(k)
        for base_name, ks in sorted(groups.items()):
            rate = sum(Ns[s] * sum(fr(r["rates"].get(k, 0)) for k in ks) for s, r in rows_by_seed.items()) / Ntot
            emit(prefix + base_name, rate, {"bracket_stripped": True, "keys": sorted(ks)})

o = outspec("M1a")[0]
secs = {}
for s in SEEDS:
    d = json.load(open(f"{RUN}/M1a/seed{s}/battery.json"))
    secs[s] = d["raw"]
have = set()
for sec, prefix in (("own", "im:"), ("a4", ""), ("a3", "a3:")):
    lids = set()
    for s in SEEDS:
        lids |= {l for l in secs[s][sec]}
    for l in sorted(lids):
        if l not in o["id_map"]:
            continue
        lid = o["id_map"][l]
        for lv in LEVELS:
            rb = {s: secs[s][sec][l][str(lv)] for s in SEEDS if str(lv) in secs[s][sec].get(l, {})}
            for s in rb:
                have.add((lid, s, lv))
            if rb:
                m1_pool("M1a", sec, lid, lv, rb, prefix, 4, bracket=True)
need("M1a", "battery", o["must_contain"], have)
for unit in ("M1b", "M1c"):
    o = outspec(unit)[0]
    res = {s: json.load(open(f"{RUN}/{unit}/seed{s}/out.json"))["results"] for s in SEEDS}
    have = set()
    lids = set().union(*(res[s].keys() for s in SEEDS))
    for l in sorted(lids):
        if l not in o["id_map"]:
            continue
        lid = o["id_map"][l]
        for lv in LEVELS:
            rb = {s: res[s][l][str(lv)] for s in SEEDS if str(lv) in res[s].get(l, {})}
            for s in rb:
                have.add((lid, s, lv))
            if rb:
                m1_pool(unit, "results", lid, lv, rb, "", 5)
    need(unit, "out.json", o["must_contain"], have)

# ---------------- C1 ----------------
C1E = ct["C1"]["entries"]
def c1_entry(src, name):
    for e in C1E:
        if e["source"].split(" ")[0] == {"s5": "a4", "a3": "a3", "battery": "battery", "f5": "closed", "f5b": "closed"}[src] and e["text"] == name:
            return f"C1 {e['label']} {e['text']}"
    return None

def scalar_rows(unit, src, lid, by_seed_level, fields):
    for lv in LEVELS:
        rb = {s: by_seed_level[s][str(lv)] for s in SEEDS if str(lv) in by_seed_level.get(s, {})}
        if not rb:
            continue
        Ntot = sum(r["n"] for r in rb.values())
        for f in fields:
            if not any(f in r for r in rb.values()):
                continue
            if any(isinstance(r.get(f), dict) for r in rb.values()):
                continue
            rate = sum(r["n"] * fr(r.get(f, 0)) for r in rb.values()) / Ntot
            ent = c1_entry(src, f)
            add(unit, src, lid, lv, f, "rate", rate, Ntot, dec_unc(3), ent is None, ent, {"named_in": sorted(s for s, r in rb.items() if f in r)})

alt_s5 = []
shape_rates = []
for unit in ("C1a", "C1c"):
    for o in outspec(unit):
        form = o["form"]
        if form == "c1_s5":
            idmap = o["id_map"]
            d = {s: json.load(open(f"{RUN}/{unit}/seed{s}/s5.json")) for s in SEEDS}
            have = set()
            for l in sorted(set().union(*(d[s].keys() for s in SEEDS))):
                if l not in idmap:
                    notes.setdefault("s5_unmapped", []).append([unit, l]); continue
                lid = idmap[l]
                byl = {s: d[s][l] for s in SEEDS if l in d[s]}
                for s in byl:
                    for lv in byl[s]:
                        have.add((lid, s, int(lv)))
                scalar_rows(unit, "s5", lid, byl, ["MF", "MFsh", "EFF_S", "EFF_SM", "EFF_F"])
                for lv in LEVELS:
                    rb = {s: byl[s][str(lv)] for s in SEEDS if str(lv) in byl.get(s, {})}
                    Ntot = sum(r["n"] for r in rb.values())
                    names = set()
                    for r in rb.values():
                        for key in r["rules"]:
                            sh, rule = key.split("|", 1)
                            if rule == "MF_in_shape_cv":
                                shape_rates.append([unit, lid, lv, key]); continue
                            names.add(rule)
                    for rule in sorted(names):
                        hits = 0; hits_alt = 0
                        for s, r in rb.items():
                            for key, v in r["rules"].items():
                                sh, rr = key.split("|", 1)
                                if rr == rule:
                                    hits += round(v["rate_in_shape"] * v["n_shape"])
                                    hits_alt += round(v["share_of_level"] * r["n"])
                        ent = c1_entry("s5", rule)
                        add(unit, "s5", lid, lv, rule, "rate", F(hits, Ntot), Ntot, F(0), ent is None, ent, {"recovered": "round(rate_in_shape*n_shape)"})
                        alt_s5.append([unit, lid, lv, rule, str(F(hits, Ntot)), str(F(hits_alt, Ntot)), ent is None])
            need(unit, "s5.json", o["must_contain"], have)
        elif form == "c1_a3":
            have = set()
            for lid, ps in o["per_survivor"].items():
                byl = {}
                for s in SEEDS:
                    rl = json.load(open(f"{RUN}/{unit}/seed{s}/a3/run_log.json"))
                    rec = rl.get(ps["run_log_key"], {})
                    if ps["fallback_file"] and rec.get("alias_rc", 0) != 0:
                        f, k = ps["fallback_file"], ps["fallback_key"]
                        notes.setdefault("a3_fallbacks", []).append([unit, lid, s])
                    else:
                        f, k = ps["primary_file"], ps["primary_key"]
                    dd = json.load(open(f"{RUN}/{unit}/seed{s}/{f}"))
                    byl[s] = dd[k]
                    for lv in dd[k]:
                        have.add((lid, s, int(lv)))
                scalar_rows(unit, "a3", lid, byl, ["MF_cv", "MF_printform_cv", "MF_shape_cv", "BEST_generic_cv"])
                for lv in LEVELS:
                    rb = {s: byl[s][str(lv)] for s in SEEDS if str(lv) in byl.get(s, {})}
                    Ntot = sum(r["n"] for r in rb.values())
                    names = {key.split("|", 1)[1] for r in rb.values() for key in r["S"]}
                    for rule in sorted(names):
                        hits = sum(v["hit"] for r in rb.values() for key, v in r["S"].items() if key.split("|", 1)[1] == rule)
                        ent = c1_entry("a3", rule)
                        add(unit, "a3", lid, lv, rule, "rate", F(hits, Ntot), Ntot, F(0), ent is None, ent)
            need(unit, "a3", o["must_contain"], have)
        elif form == "c1_closed":
            fn = o["file"]; src = fn.split(".")[0]
            d = {s: json.load(open(f"{RUN}/{unit}/seed{s}/{fn}")) for s in SEEDS}
            have = set()
            for l in sorted(set().union(*(d[s].keys() for s in SEEDS))):
                if l not in o["id_map"]:
                    continue
                lid = o["id_map"][l]
                for lv in LEVELS:
                    rb = {s: (d[s][l]["n_per_level"][str(lv)], d[s][l]["per_level"].get(str(lv), {})) for s in SEEDS if l in d[s] and str(lv) in d[s][l]["n_per_level"]}
                    for s in rb:
                        have.add((lid, s, lv))
                    Ntot = sum(n for n, _ in rb.values())
                    names = set().union(*(set(p) for _, p in rb.values()))
                    for rule in sorted(names):
                        rate = sum(n * fr(p.get(rule, 0)) for n, p in rb.values()) / Ntot
                        ent = c1_entry(src, rule)
                        add(unit, src, lid, lv, rule, "rate", rate, Ntot, dec_unc(4), ent is None, ent)
            need(unit, fn, o["must_contain"], have)

# C1b battery
o = outspec("C1b")[0]
d = {s: json.load(open(f"{RUN}/C1b/seed{s}/battery.json")) for s in SEEDS}
have = set()
for l in sorted(set().union(*(d[s].keys() for s in SEEDS))):
    if l not in o["id_map"]:
        continue
    lid = o["id_map"][l]
    byl = {s: d[s][l] for s in SEEDS if l in d[s]}
    for s in byl:
        for lv in byl[s]:
            have.add((lid, s, int(lv)))
    scalar_rows("C1b", "battery", lid, byl, ["MF_cv", "BEST_generic_cv", "MF_shape_cv"])
    for lv in LEVELS:
        rb = {s: byl[s][str(lv)] for s in SEEDS if str(lv) in byl.get(s, {})}
        Ntot = sum(r["n"] for r in rb.values())
        # MF_shape_cv as a per-shape dict: hits recovered per shape and summed
        if any(isinstance(r.get("MF_shape_cv"), dict) for r in rb.values()):
            hits = 0
            for r in rb.values():
                m = r.get("MF_shape_cv")
                if isinstance(m, dict):
                    for sh, rate in m.items():
                        hits += round(rate * r["shapes"][sh])
                        shape_rates.append(["C1b", lid, lv, f"MF_shape_cv|{sh}"])
                else:
                    hits += round(fr(m) * r["n"]) if m is not None else 0
            add("C1b", "battery", lid, lv, "MF_shape_cv", "rate", F(hits, Ntot), Ntot, F(0), True, None, {"recovered": "round(rate*shapes[shape])"})
        names = {key.split("|", 1)[1] for r in rb.values() for key in r["S"]}
        for rule in sorted(names):
            hits = sum(v["hit"] for r in rb.values() for key, v in r["S"].items() if key.split("|", 1)[1] == rule)
            ent = c1_entry("battery", rule)
            add("C1b", "battery", lid, lv, rule, "rate", F(hits, Ntot), Ntot, F(0), ent is None, ent)
need("C1b", "battery", o["must_contain"], have)

# ---------------- decide ----------------
notes["missing"] = missing
notes["exact_rows_R1"] = exact_rows
notes["n_rows"] = len(ROWS)
notes["n_shape_rates_reported_only"] = len(shape_rates)
survivors_seen = sorted({r["lineage"] for r in ROWS})
notes["survivors_without_rows"] = sorted(SURV - set(survivors_seen))
notes["rows_for_non_survivors"] = sorted(set(survivors_seen) - SURV)

def ser(x):
    return {"fraction": f"{x.numerator}/{x.denominator}", "decimal": f"{float(x):.12f}"}
per = {}
for lid in sorted(SURV):
    rs = [r for r in ROWS if r["lineage"] == lid]
    levels = {}
    for lv in LEVELS:
        c = [r for r in rs if r["level"] == lv and r["counted"]]
        if not c:
            levels[str(lv)] = None; continue
        b = max(c, key=lambda r: abs(r["excess"]) + r["unc"])
        levels[str(lv)] = {"unit": b["unit"], "src": b["src"], "rule": b["rule"], "reading": b["reading"], "shape": b.get("shape"),
                           "excess": ser(b["excess"]), "unc": ser(b["unc"]), "abs_plus_unc": ser(abs(b["excess"]) + b["unc"]), "items": b["items"]}
    over = [r for r in rs if r["over"]]
    per[lid] = {"dropped": bool(over), "n_rows_over": len(over), "levels": levels,
                "over_rows": [{"unit": r["unit"], "src": r["src"], "rule": r["rule"], "reading": r["reading"], "level": r["level"], "shape": r.get("shape"),
                               "excess": ser(r["excess"]), "unc": ser(r["unc"]), "items": r["items"]} for r in over]}
json.dump(per, open(f"{OUT}/per_lineage.json", "w"), indent=1, sort_keys=True)
with open(f"{OUT}/rows.jsonl", "w") as f:
    for r in ROWS:
        rr = dict(r); rr["excess"] = ser(r["excess"]); rr["unc"] = ser(r["unc"])
        f.write(json.dumps(rr, sort_keys=True) + "\n")
json.dump({"alt_s5": alt_s5}, open(f"{OUT}/s5_alt_recovery.json", "w"))
json.dump(notes, open(f"{OUT}/notes.json", "w"), indent=1, sort_keys=True, default=str)
dropped = sorted(l for l, v in per.items() if v["dropped"])
print("rows", len(ROWS), "survivors", len(SURV), notes["survivors_by_eval"])
print("missing (unit, kind, lineage, seed, level):", len(missing), missing[:10])
print("dropped", len(dropped))
for l in dropped:
    print("  ", l, per[l]["n_rows_over"])
for e in ("R1", "R2", "M1", "C1"):
    tot = [l for l in SURV if l.startswith(e + ".")]
    print(e, "before", len(tot), "dropped", len([l for l in dropped if l.startswith(e + ".")]), "left", len(tot) - len([l for l in dropped if l.startswith(e + ".")]))
for k in ("r1_partial_none", "r1_rule_missing_in_seed", "r1c_unparsed", "r2_unmapped", "r2_mixed_answer_types", "m1_level_missing_seed", "a3_fallbacks", "s5_unmapped", "exact_rows_R1", "survivors_without_rows", "rows_for_non_survivors"):
    v = notes.get(k)
    print(k, (len(v) if isinstance(v, list) else v), (v[:8] if isinstance(v, list) else ""))
