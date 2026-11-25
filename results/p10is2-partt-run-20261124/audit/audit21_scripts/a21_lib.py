# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21 (P10-I-S2 Part T): the auditor's OWN recomputation code (ADR-0025 section 8.6).

Written by the auditor from ADR-0025 sections 5, 8; ADR-0022 sections 3, 5.2, 5.4, 6.4, 7, 10.1; the combined-tasks addendum sections 2-7.

Imported from the frozen tree, and only this (needed to run a forward pass of the student):
  studies.p10s2.model: Cache, StudentConfig, build_student, load_plain_state
    (the Llama-style student, its key-value cache and the strict weight loader).
Everything else here is the auditor's: bundle reading and hash check, prompt and read construction from the stored segment
records, oracle codes (splitmix64 + Box-Muller, re-implemented), the store read, the LoRA / E-table application, the ablations,
the greedy loop, routing of which snapshot scores which item, the router decision, GEN NLLs, chrF-norm, the retrieval baselines,
the combined tasks C1/C2, and all means.
"""

import hashlib
import json
import math
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

WT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-acd0bce1f7811562f")
if str(WT) not in sys.path:
    sys.path.insert(0, str(WT))

import torch
import torch.nn.functional as F

from studies.p10s2.model import Cache, StudentConfig, build_student, load_plain_state  # the only frozen import

RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
SNAP = RUN / "snapshots"
QDIR = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-Q-registered3-20261119")
BUNDLE = QDIR / "outputs" / "bundle"
OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit21_out")

# --- constants typed from the ADRs -------------------------------------------------------------------------------------------------
TOP = 8  # ADR-0022 section 3: top-8
TEMP = 0.2  # softmax temperature 0.2
KEY_WIDTH = 16
VOCAB = 2000  # closed vocabulary; the task marker is j = 2000
MARKER = 2000
TASKNUM = {"A": 0, "B": 1}
BASES = [250001, 250101, 250201]  # ADR-0025 section 6
PERM_OFF, CODE_OFF = 4, 10
PANEL = {"A": "E_A", "B": "E_B"}
TWO = ("A", "B")
DECISION_INDEX = 63  # token 64
FIRST_NLL = 64
READ_LAYER = 4  # the calibrated read layer (plan: calibration.read_layer = 4); also the router layer


# --- small utilities ---------------------------------------------------------------------------------------------------------------------
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else float("nan")


def write_json_once(path, obj):
    """Write a result file in my own output directory (never overwritten); a .done marker follows the complete file."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    with open(path, "w") as f:
        json.dump(obj, f)
    with open(str(path) + ".done", "w") as f:
        f.write("ok\n")


# --- normalization and chrF-norm (ADR-0022 sections 5.2 and 10.1), my own ---------------------------------------------------------------------
def norm(text):
    t = unicodedata.normalize("NFC", text).lower()
    t = "".join(ch for ch in t if not unicodedata.category(ch).startswith("P"))
    return " ".join(t.split())


def _grams(s, n):
    return Counter(s[i : i + n] for i in range(len(s) - n + 1))


def chrf_one(hyp, ref):
    h = "".join(norm(hyp).split())
    r = "".join(norm(ref).split())
    ps, rs, eff = [], [], 0
    for n in range(1, 7):
        gh, gr = _grams(h, n), _grams(r, n)
        th, tr = sum(gh.values()), sum(gr.values())
        if th == 0 or tr == 0:
            continue
        m = sum(min(c, gr[g]) for g, c in gh.items() if g in gr)
        ps.append(m / th)
        rs.append(m / tr)
        eff += 1
    if eff == 0:
        return 0.0
    p, rc = math.fsum(ps) / eff, math.fsum(rs) / eff
    b2 = 4.0
    if p + rc == 0:
        return 0.0
    return (1 + b2) * p * rc / (b2 * p + rc)


def chrf(hyp, refs):
    return max((chrf_one(hyp, r) for r in refs), default=0.0)


def exact(hyp, refs):
    return norm(hyp) in {norm(r) for r in refs}


# --- data from the Part Q bundle ---------------------------------------------------------------------------------------------------------
class Data:
    def __init__(self, check_hashes=True):
        man = json.loads((BUNDLE / "manifest.json").read_text())
        if check_hashes:
            for name, spec in man["files"].items():
                if sha256_file(BUNDLE / name) != spec["digest"]:
                    raise SystemExit(f"bundle file {name} does not hash to its manifest")
        tt = json.loads((BUNDLE / "tokenizer_table.json").read_text())
        self.table = [bytes.fromhex(h) for h in tt["token_bytes_hex"]]
        self.newline_ids = [int(x) for x in tt["newline_ids"]]
        self.part = json.loads((BUNDLE / "partition.json").read_text())
        self.vocab = self.part["vocab"]
        self.vindex = {w: i for i, w in enumerate(self.vocab)}
        self.extra = json.loads((BUNDLE / "extra.json").read_text())
        self.max_new = int(self.extra["max_new"])
        bank = json.loads((BUNDLE / "bank.json").read_text())
        self.bank = {r["key"]: r for r in bank}
        self.teacher = json.loads((BUNDLE / "teacher_outputs.json").read_text())
        self.accepted = json.loads((BUNDLE / "accepted.json").read_text())
        res = json.loads((QDIR / "generation" / "result.json").read_text())
        assert res["draws_label"] == "DISJOINT DRAWS"
        idx = res["draws"]["indices"]
        self.draws = [{c: [self.accepted[c][i] for i in idx[c][r]] for c in TWO} for r in range(3)]
        self.gloss = json.loads((QDIR / "outputs" / "gloss_bank.json").read_text())
        self._windows = None

    @property
    def windows(self):
        if self._windows is None:
            self._windows = json.loads((BUNDLE / "windows.json").read_text())["windows"]
        return self._windows

    def rec(self, task, en, target=None):
        """The bank record of (task, source, target), keyed task|sha256(source)[:16]|sha256(target or '')[:16]."""
        k = f"{task}|{hashlib.sha256(en.encode()).hexdigest()[:16]}|{hashlib.sha256((target or '').encode()).hexdigest()[:16]}"
        return self.bank[k]

    def prompt(self, task, en):
        """Prompt ids, word reads [(pos, j)] at the stored last subword of every in-vocabulary word, the marker position (last prompt token)."""
        r = self.rec(task, en)
        segs = r["segments"][: int(r["prompt_segments"])]
        ids, reads, off = [], [], 0
        for s in segs:
            for last, w in s["word_last"]:
                if w in self.vindex:
                    reads.append((off + int(last), self.vindex[w]))
            ids += [int(x) for x in s["ids"]]
            off += len(s["ids"])
        return {"ids": ids, "reads": reads, "marker": len(ids) - 1, "task": task, "segs": segs}

    def train_ids(self, task, item):
        r = self.rec(task, item["en"], item["target"])
        return [int(x) for s in r["segments"] for x in s["ids"]]

    def panel(self, name, cap):
        items = self.part["panels"][name]
        return [self.prompt(cap, it["en"]) for it in items], [list(it["refs"][cap]) for it in items]

    def subsample(self, cap):
        keys = set(self.part["ablation_keys"][PANEL[cap]])
        return [k for k, it in enumerate(self.part["panels"][PANEL[cap]]) if it["key"] in keys]

    def open_panel(self, cap):
        items = self.part["panels"]["E_open"]
        idx = [i for i, it in enumerate(items) if it["refs"].get(cap)]
        return idx, [self.prompt(cap, items[i]["en"]) for i in idx], [list(items[i]["refs"][cap]) for i in idx]

    def dcon(self, cap):
        items = self.part["panels"]["D_con"]
        return [self.prompt(cap, it["en"]) for it in items], [list(it["refs"][cap]) for it in items]

    def seen(self, r, cap):
        in_draw = {x["key"]: x for x in self.draws[r][cap]}
        items = [in_draw[k] for k in self.part["seen_order"][cap] if k in in_draw][:300]
        return [self.prompt(cap, x["en"]) for x in items], [[x["target"]] for x in items]

    def answer_text(self, gen):
        return b"".join(self.table[i] for i in gen).decode("utf-8", errors="replace").split("\n", 1)[0]

    def is_stop(self, tok):
        return b"\n" in self.table[tok]


# --- oracle codes: splitmix64 + Box-Muller, re-implemented (fixed random unit vector from a seeded hash, ADR-0025 section 5.4) -----------------
M64 = (1 << 64) - 1
GOLD = 0x9E3779B97F4A7C15


def mix64(x):
    x = (x + GOLD) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


def unit_vec(seed, ident, width=KEY_WIDTH):
    st = mix64(mix64(seed & M64) + ident)
    vals = []
    for j in range((width + 1) // 2):
        a = mix64((st + (2 * j + 1) * GOLD) & M64)
        b = mix64((st + (2 * j + 2) * GOLD) & M64)
        u1 = ((a >> 11) + 1) / float(1 << 53)
        u2 = (b >> 11) / float(1 << 53)
        rad = math.sqrt(-2.0 * math.log(u1))
        vals += [rad * math.cos(2.0 * math.pi * u2), rad * math.sin(2.0 * math.pi * u2)]
    vals = vals[:width]
    nn_ = math.sqrt(sum(v * v for v in vals))
    return [v / nn_ for v in vals]


class Codes:
    def __init__(self, seed):
        self.seed, self.cache = seed, {}

    def get(self, task, j):
        k = (task, j)
        if k not in self.cache:
            self.cache[k] = torch.tensor(unit_vec(self.seed, (VOCAB + 1) * TASKNUM[task] + j), dtype=torch.float32)
        return self.cache[k]


# --- arms (my own application of a snapshot) -----------------------------------------------------------------------------------------------
class Store:
    """One sparse store from a snapshot: the read of ADR-0022 section 3 (cosine to unit-normalized keys, top-8 with lowest index on ties, softmax/0.2,
    per-stage gate times value)."""

    def __init__(self, st, value_perms=None):
        keys = torch.cat(list(st["keys"]), 0)
        vals = list(st["values"])
        if value_perms:
            vals = [v[value_perms[k]] if k in value_perms else v for k, v in enumerate(vals)]
        self.values = torch.cat(vals, 0)
        self.gate = torch.cat([g.expand(int(r)) for g, r in zip(st["gates"], st["stage_rows"])])
        self.kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        self.width = int(st["width"])

    def read(self, q):
        a = q @ self.kn.t()
        order = torch.sort(a, dim=-1, descending=True, stable=True).indices[:, :TOP]
        w = torch.softmax(torch.gather(a, 1, order) / TEMP, dim=-1)
        return ((w * self.gate[order]).unsqueeze(-1) * self.values[order]).sum(dim=1)


def store_add(store, codes, reads, length):
    if not reads:
        return None
    q = torch.stack([codes.get(t, j) for _p, t, j in reads])
    r = store.read(q)
    add = torch.zeros(1, length, store.width, dtype=r.dtype)
    return add.index_put((torch.zeros(len(reads), dtype=torch.long), torch.tensor([p for p, _t, _j in reads])), r, accumulate=True)


class Lora:
    def __init__(self, sd):
        n = len([k for k in sd if k.startswith("a.")])
        self.a = [sd[f"a.{i}"] for i in range(n)]
        self.b = [sd[f"b.{i}"] for i in range(n)]

    def delta(self, block, which, h):
        k = 2 * block + (0 if which == "q" else 1)
        return (h @ self.a[k].t()) @ self.b[k].t() * 1.0


class SumLora:
    def __init__(self, first, second):
        self.first, self.second = first, second

    def delta(self, block, which, h):
        return self.first.delta(block, which, h) + self.second.delta(block, which, h)


class PosLora:
    """The LoRA update at a position is that of the task owning it (combined addendum section 7). ``Model.fwd`` sets the span of each call."""

    def __init__(self, adapters, owner):
        self.adapters, self.owner = adapters, owner
        self.start, self.length = 0, 0

    def delta(self, block, which, h):
        owners = [self.owner(self.start + i) for i in range(self.length)]
        res = None
        for task, ad in self.adapters.items():
            d = ad.delta(block, which, h)
            m = torch.tensor([o == task for o in owners])[None, :, None]
            piece = torch.where(m, d, torch.zeros_like(d))
            res = piece if res is None else res + piece
        return res


def load_snapshot(name):
    safe = name.replace("/", "__").replace("@", "_at_")
    m = json.loads((SNAP / f"{safe}.manifest.json").read_text())
    if sha256_file(SNAP / m["file"]) != m["file_sha256"]:
        raise SystemExit(f"snapshot {name} does not hash to its manifest")
    return torch.load(SNAP / m["file"], weights_only=True), m


class Arm:
    """kind: null | mem | lora | lora2 | table | msep | lsep."""

    def __init__(self, kind, **kw):
        self.kind = kind
        self.layer = None
        self.__dict__.update(kw)

    def prepare(self, reads, length, ablation=None):
        k = self.kind
        if k == "null":
            return None, None
        if k == "mem":
            use = apply_ablation(reads, ablation)
            if not use:
                return None, None
            store = ablation[2] if ablation is not None and ablation[0] == "value" else self.store
            return store_add(store, self.codes, use, length), None
        if k == "msep":
            total = None
            for t, st in self.stores.items():
                sub = [x for x in reads if x[1] == t]
                if sub:
                    a = store_add(st, self.codes, sub, length)
                    total = a if total is None else total + a
            return total, None
        if k == "table":
            sel = [(p, j) for p, t, j in reads if t == self.task]
            if not sel:
                return None, None
            vec = self.gate * self.tab[torch.tensor([j for _p, j in sel])]
            add = torch.zeros(1, length, self.tab.shape[1], dtype=vec.dtype)
            return add.index_put((torch.zeros(len(sel), dtype=torch.long), torch.tensor([p for p, _j in sel])), vec, accumulate=True), None
        if k in ("lora", "lora2"):
            if not reads:
                return None, None
            return None, self.adapter
        if k == "lsep":
            tasks = {x[1] for x in reads}
            if len(tasks) != 1:
                return None, None
            return None, self.adapters[next(iter(tasks))]
        raise ValueError(k)


def apply_ablation(reads, ab):
    if ab is None:
        return list(reads)
    kind = ab[0]
    if kind == "marker":
        return [r for r in reads if r[2] == MARKER]
    if kind == "words":
        return [r for r in reads if r[2] != MARKER]
    if kind == "code":
        perm, tasks = ab[1], ab[2]
        return [(p, t, int(perm[j]) if (j != MARKER and t in tasks) else j) for p, t, j in reads]
    if kind == "value":
        return list(reads)
    raise ValueError(kind)


def arm_from(name, r):
    st, _m = load_snapshot(name)
    if st["kind"] == "memory":
        assert int(st["layer"]) == READ_LAYER
        return Arm("mem", store=Store(st["store"]), raw=st["store"], codes=Codes(BASES[r] + CODE_OFF), layer=int(st["layer"]))
    if st["kind"] == "lora":
        return Arm("lora", adapter=Lora(st["state"]))
    if st["kind"] == "lora2":
        return Arm("lora2", adapter=SumLora(Lora(st["first"]), Lora(st["second"])))
    if st["kind"] == "table":
        assert int(st["layer"]) == READ_LAYER
        return Arm("table", task=st["task"], tab=st["table"], gate=st["gate"], layer=int(st["layer"]))
    raise ValueError(st["kind"])


# --- the student and the greedy loop ------------------------------------------------------------------------------------------------------
class Model:
    def __init__(self, data):
        st = torch.load(BUNDLE / "student.pt", weights_only=True)
        self.cfg = StudentConfig(**st["cfg"])
        self.student = build_student(self.cfg)
        load_plain_state(self.student, st["state"])
        self.data = data

    @torch.no_grad()
    def fwd(self, ids, add=None, adapter=None, cache=None, layer=None):
        if isinstance(adapter, PosLora):
            adapter.start, adapter.length = (cache.length if cache is not None else 0), len(ids)
        self.student.read_layer = layer if add is not None else None
        return self.student(torch.tensor([list(ids)]), add=add, adapter=adapter, cache=cache)

    @torch.no_grad()
    def greedy(self, ids, add=None, adapter=None, layer=None, cache=None):
        """Greedy decoding: the chunk ``ids`` is read with ``add``; generated positions are never read; stop at the first token whose bytes contain 0x0A
        (kept), or after max_new tokens; the last generated token is not fed. Returns (generated ids, cache)."""
        cache = cache if cache is not None else Cache()
        logits = self.fwd(ids, add, adapter, cache, layer)
        out = []
        while True:
            nxt = int(torch.argmax(logits[0, -1]).item())
            out.append(nxt)
            if self.data.is_stop(nxt) or len(out) == self.data.max_new:
                break
            logits = self.fwd([nxt], None, adapter, cache, layer)
        return out, cache

    @torch.no_grad()
    def hidden(self, ids, layer, pos):
        self.student.read_layer = None
        h = self.student(torch.tensor([list(ids)]), hidden_at=layer)
        return h[0, pos]


def oracle_reads(p, tasks):
    out = []
    for t in tasks:
        out += [(pos, t, j) for pos, j in p["reads"]]
        out.append((p["marker"], t, MARKER))
    return out


class Scorer:
    """Decodes with a memo keyed by the exact inputs (arm id, ablation id, prompt ids, reads): an identical computation is done once."""

    def __init__(self, model):
        self.m, self.d = model, model.data
        self.memo = {}
        self.calls = 0
        self.hits = 0

    def decode(self, arm_id, arm, p, tasks, ab=None, ab_id=None):
        reads = oracle_reads(p, tasks)
        key = (arm_id, ab_id, tuple(p["ids"]), tuple(reads))
        if key in self.memo:
            self.hits += 1
            return self.memo[key]
        add, adapter = arm.prepare(reads, len(p["ids"]), ab)
        self.calls += 1
        g, _ = self.m.greedy(p["ids"], add, adapter, arm.layer)
        self.memo[key] = g
        return g

    def panel(self, arm_id, arm, prompts, refs, tasks_of=None, ab=None, ab_id=None, indices=None):
        idx = range(len(prompts)) if indices is None else indices
        rec = {"items": [], "exact": [], "sequences": [], "texts": []}
        for i in idx:
            p = prompts[i]
            tasks = [p["task"]] if tasks_of is None else tasks_of(i, p)
            g = self.decode(arm_id, arm, p, tasks, ab, ab_id)
            txt = self.d.answer_text(g)
            rec["items"].append(chrf(txt, refs[i]))
            rec["exact"].append(exact(txt, refs[i]))
            rec["sequences"].append(g)
            rec["texts"].append(txt)
        return rec


# --- ablations (ADR-0025 section 5.2; ADR-0022 section 7) ---------------------------------------------------------------------------------------
def ablations(arm, r, stages, tasks):
    """value / code / marker / words on the 300-item subsample. Reading taken from the frozen code where the ADR is silent: the permutation controls
    use the replicate's +4 seed with a fresh generator per control; ``value`` permutes each listed stage's value rows among themselves, in stage order,
    from one generator; ``code`` permutes the 2,000 word indices (marker kept) for the listed tasks."""
    seed = BASES[r] + PERM_OFF
    g = torch.Generator()
    g.manual_seed(seed)
    perms = {k: torch.randperm(int(arm.raw["stage_rows"][k]), generator=g) for k in stages}
    vstore = Store(arm.raw, value_perms=perms)
    g2 = torch.Generator()
    g2.manual_seed(seed)
    cperm = torch.randperm(VOCAB, generator=g2)
    return {"value": ("value", None, vstore), "code": ("code", cperm, tuple(tasks)), "marker": ("marker",), "words": ("words",)}


# --- the router (my own decision from the stored projection and keys) --------------------------------------------------------------------------
def load_router(r, tasks):
    name = "_".join(tasks)
    d = SNAP / "routers" / f"r{r}"
    m = json.loads((d / f"{name}.manifest.json").read_text())
    if sha256_file(d / m["file"]) != m["file_sha256"]:
        raise SystemExit("router file hash differs")
    st = torch.load(d / m["file"], weights_only=True)
    return {"tasks": tuple(st["tasks"]), "proj": st["state"]["proj"], "keys": st["state"]["keys"]}


def route(router, h):
    z = F.normalize(h @ router["proj"].t(), dim=-1)
    s = z @ F.normalize(router["keys"], dim=-1).t()
    return (*router["tasks"], "none")[int(torch.argmax(s).item())]


# --- GEN (ADR-0022 section 6.4 with rulings C-M6 and the 2026-11-16 addendum; ADR-0025 section 5.5) ------------------------------------------
def window_nll(model, arm, w, tasks):
    reads = [(p, t, j) for t in tasks for p, j in w["reads"]]
    add, adapter = arm.prepare(reads, len(w["ids"]))
    logits = model.fwd(w["ids"], add, adapter, None, arm.layer)[0]
    tgt = torch.tensor(w["ids"][FIRST_NLL:])
    x = logits[FIRST_NLL - 1 : -1]
    f32 = float(-torch.log_softmax(x, dim=-1).gather(1, tgt[:, None]).mean())  # the model's own precision (float32)
    f64 = float(-torch.log_softmax(x.double(), dim=-1).gather(1, tgt[:, None]).mean())  # the same logits, log-softmax in float64
    return f32, f64


def gen_records(model, arm, router, base_cache, hidden_cache):
    win = model.data.windows
    out = {k: {"nll_base": [], "nll_arm": [], "nll_base_f64": [], "nll_arm_f64": [], "strata": [], "preds": []} for k in ("token64", "first_marker")}
    null = Arm("null")
    for k, w in enumerate(win):
        if k not in base_cache:
            base_cache[k] = window_nll(model, null, w, [])
        base = base_cache[k]
        pos2 = w["marker_end"] if w["stratum"] == "marker" and w["marker_end"] >= 0 else DECISION_INDEX
        for name, pos in (("token64", DECISION_INDEX), ("first_marker", pos2)):
            hk = (k, pos)
            if hk not in hidden_cache:
                hidden_cache[hk] = model.hidden(w["ids"][: pos + 1], READ_LAYER, pos)
            pred = route(router, hidden_cache[hk])
            nll = base if pred == "none" else window_nll(model, arm, w, [pred])
            o = out[name]
            o["nll_base"].append(base[0])
            o["nll_arm"].append(nll[0])
            o["nll_base_f64"].append(base[1])
            o["nll_arm_f64"].append(nll[1])
            o["strata"].append(w["stratum"])
            o["preds"].append(pred)
    return out


def gen_value(rec, suffix=""):
    def pm(vals, strata):
        ms = [fmean([v for v, s in zip(vals, strata) if s == n]) for n in ("marker", "ordinary") if n in strata]
        return math.fsum(ms) / len(ms)

    return pm(rec["nll_arm" + suffix], rec["strata"]) - pm(rec["nll_base" + suffix], rec["strata"])


# --- retrieval baselines (ADR-0022 section 7), my own ------------------------------------------------------------------------------------------
def trigrams(s):
    t = f"  {norm(s)}  "
    return Counter(t[i : i + 3] for i in range(len(t) - 2))


class Tfidf:
    def __init__(self, train):
        grams = [trigrams(x["en"]) for x in train]
        df = Counter()
        for g in grams:
            df.update(g.keys())
        n = max(1, len(grams))
        self.idf = {k: math.log((1 + n) / (1 + v)) + 1.0 for k, v in df.items()}
        self.vecs = [self.vec(g) for g in grams]

    def vec(self, g):
        v = {k: c * self.idf.get(k, 1.0) for k, c in g.items()}
        nn_ = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {k: x / nn_ for k, x in v.items()}

    def nearest(self, src, k):
        q = self.vec(trigrams(src))
        sims = [(-sum(w * v.get(t, 0.0) for t, w in q.items()), i) for i, v in enumerate(self.vecs)]
        return [i for _s, i in sorted(sims)[:k]]


def dice_lexicon(train):
    cs, ct, co = Counter(), Counter(), defaultdict(Counter)
    for x in train:
        sw, tw = set(norm(x["en"]).split()), set(norm(x["target"]).split())
        cs.update(sw)
        ct.update(tw)
        for a in sw:
            co[a].update(tw)
    return {a: min(row, key=lambda b: (-2 * row[b] / (cs[a] + ct[b]), b)) for a, row in co.items()}


def edit1(a, b):
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    s, lo = (a, b) if len(a) < len(b) else (b, a)
    return any(lo[:i] + lo[i + 1 :] == s for i in range(len(lo)))


# --- combined tasks (addendum sections 4-7), my own ---------------------------------------------------------------------------------------------
def combined_cell(model, arm, data, limit=None):
    """``limit`` (timing and validation runs only): the first ``limit`` C1 items and C2 items, and the separate single answers of sentences < limit."""
    d, m = data, model
    ec = d.part["panels"]["E_C"]
    n = len(ec)
    nl_ = n if limit is None else limit
    sigma = d.extra["c1_pairing"]["sigma"]
    pairs = []
    for j in range(nl_):
        t1 = "A" if j % 2 == 0 else "B"
        pairs.append((j, sigma[j], sigma[(j + 1) % n], t1, "B" if t1 == "A" else "A"))
    P = {(i, c): d.prompt(c, ec[i]["en"]) for i in range(n) for c in TWO}
    refs = {(i, c): list(ec[i]["refs"][c]) for i in range(n) for c in TWO}
    nl = list(d.newline_ids)
    single, c1 = {}, []

    def split(g):
        for k, t in enumerate(g):
            if d.is_stop(t):
                return list(g[:k]), False
        return list(g), True

    def step(ids, reads, cache=None):
        add, adapter = arm.prepare(reads, len(ids))
        return m.greedy(ids, add, adapter, arm.layer, cache)

    for j, i1, i2, t1, t2 in pairs:
        p1, p2 = P[(i1, t1)], P[(i2, t2)]
        if arm.kind == "lsep":
            bound = [math.inf]
            pa = PosLora({t1: arm.adapters[t1], t2: arm.adapters[t2]}, lambda i, b=bound, a=t1, c=t2: a if i < b[0] else c)
            g1, cache = m.greedy(p1["ids"], None, pa, None)
            a1, hit = split(g1)
            pre = [a1[-1]] if hit and a1 else []
            bound[0] = len(p1["ids"]) + len(a1)
            g2, _ = m.greedy(pre + nl + p2["ids"], None, pa, None, cache)
        else:
            g1, cache = step(p1["ids"], oracle_reads(p1, [t1]))
            a1, hit = split(g1)
            pre = [a1[-1]] if hit and a1 else []
            base = len(pre) + len(nl)
            reads2 = [(pos + base, t, jj) for pos, t, jj in oracle_reads(p2, [t2])]
            g2, _ = step(pre + nl + p2["ids"], reads2, cache)
        single[(i1, t1)] = g1
        c1.append((j, i1, i2, t1, t2, g1, g2))
    separate = 0
    for i in range(nl_):
        for c in TWO:
            if (i, c) not in single:
                p = P[(i, c)]
                if arm.kind == "lsep":
                    g, _ = m.greedy(p["ids"], None, arm.adapters[c], None)
                else:
                    g, _ = step(p["ids"], oracle_reads(p, [c]))
                single[(i, c)] = g
                separate += 1
    c2 = []
    for i in range(nl_):
        pa_, pb_ = P[(i, "A")], P[(i, "B")]
        marker_b = [int(x) for x in pb_["segs"][-1]["ids"]]
        if arm.kind == "lsep":
            g1, _ = m.greedy(pa_["ids"], None, arm.adapters["A"], None)
            a1, _hit = split(g1)
            full = pa_["ids"] + a1 + nl + marker_b
            mlen = len(pa_["segs"][-1]["ids"])
            prefix, end_a = len(pa_["ids"]) - mlen, len(pa_["ids"]) + len(a1)
            pl = PosLora({"A": arm.adapters["A"], "B": arm.adapters["B"]}, lambda q, pr=prefix, ea=end_a: "A" if pr <= q < ea else "B")
            g2, _ = m.greedy(full, None, pl, None)
        else:
            reads1 = oracle_reads(pa_, ["A"]) + [(pos, "B", jj) for pos, jj in pa_["reads"]]
            g1, cache = step(pa_["ids"], reads1)
            a1, hit = split(g1)
            pre = [a1[-1]] if hit and a1 else []
            suffix = pre + nl + marker_b
            g2, _ = step(suffix, [(len(suffix) - 1, "B", MARKER)], cache)
        c2.append((i, g1, g2))

    def sc(g, rf):
        t = d.answer_text(g)
        return chrf(t, rf), exact(t, rf)

    rec = {}
    for kind, rows in (("C1", c1), ("C2", [(i, i, i, "A", "B", g1, g2) for i, g1, g2 in c2])):
        items, tested = [], {"A": [], "B": []}
        for j, i1, i2, l1, l2, g1, g2 in rows:
            x1, p1 = sc(g1, refs[(i1, l1)])
            x2, p2 = sc(g2, refs[(i2, l2)])
            items.append({"j": j, "i": [i1, i2], "langs": [l1, l2], "ids": [g1, g2], "scores": [x1, x2], "pass": bool(p1 and p2)})
            tested[l2].append(x2)
            if kind == "C2":
                tested[l1].append(x1)
        rec[kind] = {"items": items, "mean": fmean([(it["scores"][0] + it["scores"][1]) / 2 for it in items]), "tested_by_language": {a: (fmean(v) if v else None) for a, v in tested.items()}}
    keep = range(n) if limit is None else [i for i in range(n) if all((i, c) in single for c in TWO)]
    rec["single"] = {"index": list(keep), "sequences": {c: [single[(i, c)] for i in keep] for c in TWO}, "scores": {c: [sc(single[(i, c)], refs[(i, c)])[0] for i in keep] for c in TWO}, "separate_answers": separate}
    return rec


def ensemble_record(data):
    d = data
    ec = d.part["panels"]["E_C"]
    n = len(ec)
    sigma = d.extra["c1_pairing"]["sigma"]
    single = {c: [chrf(d.teacher[c]["E_C"][i], list(ec[i]["refs"][c])) for i in range(n)] for c in TWO}
    rows1 = []
    for j in range(n):
        t1 = "A" if j % 2 == 0 else "B"
        rows1.append((sigma[j], sigma[(j + 1) % n], t1, "B" if t1 == "A" else "A"))
    rec = {}
    for kind, rows in (("C1", rows1), ("C2", [(i, i, "A", "B") for i in range(n)])):
        tested, its = {"A": [], "B": []}, []
        for i1, i2, l1, l2 in rows:
            x1, x2 = single[l1][i1], single[l2][i2]
            its.append((x1 + x2) / 2)
            tested[l2].append(x2)
            if kind == "C2":
                tested[l1].append(x1)
        rec[kind] = {"mean": fmean(its), "tested_by_language": {a: (fmean(v) if v else None) for a, v in tested.items()}}
    rec["single"] = {"scores": single}
    return rec
