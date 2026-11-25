# ruff: noqa
"""Audit D0 (ADR-0035, P10-I-S2-D0): the auditor's OWN recomputation library.

Reused from my audit 21 code (audit21_scripts/a21_lib.py, copied, not imported): chrF-norm, normalization, the Part Q bundle reader and prompt/read
construction, the oracle codes (splitmix64 + Box-Muller), the store read, the greedy loop. New here, written from ADR-0035 section 4's text and the
definition of SparseStore.read (cosine to unit-normalized keys; stable descending sort, top-8, lowest row index wins ties; softmax of the eight
cosines / 0.2; per-stage gate times value): the read conditions a, b(p), c, d(p), e(p), g(p) and the read statistics of section 5.2.

Imported from the frozen tree, and only this: studies.p10s2.model (Cache, StudentConfig, build_student, load_plain_state) for the student's forward pass.
The implementer's studies/p10is2d0/ code and outputs were NOT read before my numbers were written and hashed.
"""

import hashlib
import json
import math
import struct
import sys
import unicodedata
from collections import Counter
from pathlib import Path

WT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/p10-i-s2-d0-20261124")  # D0 worktree at e74cbf25 (Part T tree f6dff34d + D0 files)
if str(WT) not in sys.path:
    sys.path.insert(0, str(WT))

import torch

from studies.p10s2.model import Cache, StudentConfig, build_student, load_plain_state  # the only frozen import

RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
SNAP = RUN / "snapshots"
QDIR = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-Q-registered3-20261119")
BUNDLE = QDIR / "outputs" / "bundle"
OUT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/audits/audit_d0_out")

TOP = 8
TEMP = 0.2
KEY_WIDTH = 16
VOCAB = 2000
MARKER = 2000
TASKNUM = {"A": 0, "B": 1}
BASES = [250001, 250101, 250201]
CODE_OFF = 10
PANEL = {"A": "E_A", "B": "E_B"}
READ_LAYER = 4
CELLS = [(r, o) for r in range(3) for o in ("AB", "BA")]


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
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    with open(path, "x") as f:
        json.dump(obj, f)
    with open(str(path) + ".done", "x") as f:
        f.write("ok\n")


# --- chrF-norm (my own; ADR-0022 sections 5.2, 10.1), unchanged from audit 21 ------------------------------------------------------------------
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


# --- data (Part Q bundle), the subset of audit 21's reader needed here ------------------------------------------------------------------------
class Data:
    def __init__(self, check_hashes=True):
        man = json.loads((BUNDLE / "manifest.json").read_text())
        self.bundle_checked = {}
        if check_hashes:
            for name, spec in man["files"].items():
                d = sha256_file(BUNDLE / name)
                if d != spec["digest"]:
                    raise SystemExit(f"bundle file {name} does not hash to its manifest")
                self.bundle_checked[name] = d
        tt = json.loads((BUNDLE / "tokenizer_table.json").read_text())
        self.table = [bytes.fromhex(h) for h in tt["token_bytes_hex"]]
        self.part = json.loads((BUNDLE / "partition.json").read_text())
        self.vocab = self.part["vocab"]
        self.vindex = {w: i for i, w in enumerate(self.vocab)}
        self.extra = json.loads((BUNDLE / "extra.json").read_text())
        self.max_new = int(self.extra["max_new"])
        bank = json.loads((BUNDLE / "bank.json").read_text())
        self.bank = {r["key"]: r for r in bank}

    def rec(self, task, en, target=None):
        k = f"{task}|{hashlib.sha256(en.encode()).hexdigest()[:16]}|{hashlib.sha256((target or '').encode()).hexdigest()[:16]}"
        return self.bank[k]

    def prompt(self, task, en):
        r = self.rec(task, en)
        segs = r["segments"][: int(r["prompt_segments"])]
        ids, reads, off = [], [], 0
        for s in segs:
            for last, w in s["word_last"]:
                if w in self.vindex:
                    reads.append((off + int(last), self.vindex[w]))
            ids += [int(x) for x in s["ids"]]
            off += len(s["ids"])
        return {"ids": ids, "reads": reads, "marker": len(ids) - 1, "task": task}

    def panel(self, cap):
        items = self.part["panels"][PANEL[cap]]
        return [self.prompt(cap, it["en"]) for it in items], [list(it["refs"][cap]) for it in items]

    def answer_text(self, gen):
        return b"".join(self.table[i] for i in gen).decode("utf-8", errors="replace").split("\n", 1)[0]

    def is_stop(self, tok):
        return b"\n" in self.table[tok]


def oracle_reads(p):
    """The oracle route for a single-capability panel item: every word read and the marker read, under the item's own task."""
    t = p["task"]
    return [(pos, t, j) for pos, j in p["reads"]] + [(p["marker"], t, MARKER)]


# --- oracle codes (splitmix64 + Box-Muller), unchanged from audit 21 -----------------------------------------------------------------------------
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

    def queries(self, reads):
        return torch.stack([self.get(t, j) for _p, t, j in reads])


# --- snapshots ---------------------------------------------------------------------------------------------------------------------------------
def load_snapshot(r, arm, o, at_append=False):
    safe = f"r{r}__{arm}__{o}" + ("_at_append" if at_append else "")
    m = json.loads((SNAP / f"{safe}.manifest.json").read_text())
    d = sha256_file(SNAP / m["file"])
    if d != m["file_sha256"]:
        raise SystemExit(f"snapshot {safe} does not hash to its manifest")
    st = torch.load(SNAP / m["file"], weights_only=True)
    assert st["kind"] == "memory" and int(st["layer"]) == READ_LAYER, (safe, st["kind"], st.get("layer"))
    return st["store"], {"name": safe, "file": m["file"], "sha256": d}


# --- reads -------------------------------------------------------------------------------------------------------------------------------------
class Store:
    """My registered read (the SparseStore.read arithmetic, re-typed): cosine to unit-normalized keys, stable descending sort, top-8,
    softmax over the eight cosines / 0.2, times per-row stage gate, times value. ``stages`` selects a sub-store holding those stages' tensors alone."""

    def __init__(self, st, stages=None):
        ks = range(len(st["stage_rows"])) if stages is None else stages
        self.keys = torch.cat([st["keys"][k] for k in ks], 0)
        self.values = torch.cat([st["values"][k] for k in ks], 0)
        self.gate = torch.cat([st["gates"][k].expand(int(st["stage_rows"][k])) for k in ks])
        self.stage = torch.cat([torch.full((int(st["stage_rows"][k]),), k, dtype=torch.long) for k in ks])
        self.kn = self.keys / self.keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        self.width = int(st["width"])

    def select(self, q):
        a = q @ self.kn.t()
        order = torch.sort(a, dim=-1, descending=True, stable=True).indices[:, :TOP]
        sel = torch.gather(a, 1, order)
        w = torch.softmax(sel / TEMP, dim=-1)
        return order, sel, w

    def read(self, q):
        order, _sel, w = self.select(q)
        return ((w * self.gate[order]).unsqueeze(-1) * self.values[order]).sum(dim=1)

    def from_weights(self, order, weight):
        return (weight.unsqueeze(-1) * self.values[order]).sum(dim=1)


class Conditions:
    """All reads of ADR-0035 section 4 on a two-stage store (stage index 0 = S1, 1 = S2). For a batch of unit queries returns a dict of (M, width)
    read vectors and the selection data used by the statistics."""

    def __init__(self, st):
        assert len(st["stage_rows"]) == 2
        self.st = st
        self.full = Store(st)
        self.sub = {1: Store(st, [0]), 2: Store(st, [1])}  # b(p): the registered read on a store holding stage p's tensors alone
        self.n1 = int(st["stage_rows"][0])
        self.g = {1: st["gates"][0].reshape(-1)[0], 2: st["gates"][1].reshape(-1)[0]}

    def compute(self, q):
        F = self.full
        order, sel, w = F.select(q)
        gslot = F.gate[order]
        stage = F.stage[order]  # 0 or 1
        mask = {1: stage == 0, 2: stage == 1}
        wa = w * gslot  # the registered per-slot weight vector
        out = {"a": F.from_weights(order, wa)}
        out["a_ref"] = F.read(q)  # my Store.read on the full store (gate: torch.equal to out['a'])
        zero = torch.zeros_like(wa)
        for p in (1, 2):
            out[f"b{p}"] = self.sub[p].read(q)
            out[f"e{p}"] = F.from_weights(order, torch.where(mask[p], wa, zero))
            logits = torch.where(mask[p], sel / TEMP, torch.full_like(sel, -math.inf))
            nonempty = mask[p].any(dim=1, keepdim=True)
            wk = torch.softmax(torch.where(nonempty, logits, torch.zeros_like(logits)), dim=-1)  # rows with K empty: placeholder, zeroed below
            wd = torch.where(mask[p] & nonempty, wk * gslot, zero)
            out[f"d{p}"] = F.from_weights(order, wd)
            out[f"_K_empty{p}"] = ~nonempty.squeeze(1)
        out["c"] = out["b1"] + out["b2"]
        out["g1"] = out["b1"] + out["e2"]
        out["g2"] = out["b2"] + out["e1"]
        out["_order"], out["_w"], out["_mask"] = order, w, mask
        return out


def scatter_add(read_vectors, reads, length, width):
    add = torch.zeros(1, length, width, dtype=read_vectors.dtype)
    return add.index_put((torch.zeros(len(reads), dtype=torch.long), torch.tensor([p for p, _t, _j in reads])), read_vectors, accumulate=True)


# --- the student and the greedy loop (unchanged from audit 21) ----------------------------------------------------------------------------------
class Model:
    def __init__(self, data):
        st = torch.load(BUNDLE / "student.pt", weights_only=True)
        self.cfg = StudentConfig(**st["cfg"])
        self.student = build_student(self.cfg)
        load_plain_state(self.student, st["state"])
        self.data = data

    @torch.no_grad()
    def fwd(self, ids, add=None, cache=None, layer=None):
        self.student.read_layer = layer if add is not None else None
        return self.student(torch.tensor([list(ids)]), add=add, adapter=None, cache=cache)

    @torch.no_grad()
    def greedy(self, ids, add, layer=READ_LAYER):
        cache = Cache()
        logits = self.fwd(ids, add, cache, layer)
        out = []
        while True:
            nxt = int(torch.argmax(logits[0, -1]).item())
            out.append(nxt)
            if self.data.is_stop(nxt) or len(out) == self.data.max_new:
                break
            logits = self.fwd([nxt], None, cache, layer)
        return out


class Decoder:
    """Greedy decode with an in-process memo keyed by (prompt ids, SHA-256 of the add tensor's bytes): a bit-identical input is decoded once."""

    def __init__(self, model):
        self.m = model
        self.memo = {}
        self.calls = 0
        self.hits = 0

    def decode(self, ids, add):
        flat = add.contiguous().reshape(-1).tolist()  # float32 -> python float is exact
        key = (tuple(ids), hashlib.sha256(struct.pack(f"<{len(flat)}f", *flat)).hexdigest(), tuple(add.shape))
        if key in self.memo:
            self.hits += 1
            return self.memo[key]
        self.calls += 1
        g = self.m.greedy(ids, add)
        self.memo[key] = g
        return g
