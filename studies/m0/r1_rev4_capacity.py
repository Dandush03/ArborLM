# ruff: noqa: E501
"""Capacity on STRUCTURE for the revision-4 registered set (lead ruling R-5: names, setting and presentation order alone are not distinct items; demand computed at the G actually written).

Demand (derived from ADR-0033 section 6.2 "Capacity gate" and section 8, as ``lineage_gates.demand_at_g`` already reads them): every cluster (lineage) of a part must be able to produce at least 10
times the number of items the pools demand of it, at every level. The pools of one part hold 4,000 development + 20,000 sealed = 24,000 items spread evenly over the part's G clusters, and
tuning draws 100 per level. Worst-case reading kept from ``lineage_gates``: a core level (1 to 5) must supply ceil(24,000 / G) + 100 items (the cluster's whole share, not a fifth of it), a reserve
level (0, 6) 100. Required distinct structures = 10 x that. G is the number of strict clusters in the part, NOT 300: scenarios G = 13 (27 clusters split half and half) and G = 8 (the smallest part of
any partition reading of ``r1_rev4_parts``).

Structure key of an item (name-, setting- and order-free): the question is split into sentences; every word of the entity vocabulary (names, towns, objects, invented words, colours, actions, verbs,
group names) is erased and its occurrences become nodes of a hypergraph whose hyperedges are the sentences (sentence template with numbers kept, entity nodes in order of appearance; a list of
entities in alphabetical order is an unordered slot; alternative phrasings of one fact -- taller/shorter, 'X is the parent of Y'/'Y's parent is X', north/south and east/west, before/after -- are rewritten
to one phrasing first, because they are a surface choice). Three rounds of colour refinement (Weisfeiler-Leman 1) give each node a name-free colour; the key is the hash of the sorted multiset of
(template, node colours) over sentences. So two items that differ only by which names are used, by the order of the sentences, or by the alphabetical position of the names have the SAME key. The key
can only merge items (a refinement invariant, order of sentences erased: permuted operation lists in a simulation, for instance, merge), so the count is a LOWER bound of the true structural count.
MEASURED by exhibition (draw until the required number of distinct keys is found, at most 3 x need + 2,000 draws). Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r1_rev4_capacity [workers]``.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import re
import sys
import time
from pathlib import Path
from typing import Any

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.vocab import COLOURS, EVENTS, NAMES, OBJECTS, PETS, PSEUDO, SHAPES, TOWNS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "studies/m0/manifests"
_EXTRA_WORDS = ("swim", "glow", "hum", "jump", "float", "climb", "stop", "wait", "knock", "hide", "sing", "run", "chess", "choir", "diving", "poetry", "rowing", "archery", "baking",
                "grandparent", "great-grandparent", "great-great-grandparent", "yo-yo", "turnleft", "turnright", "sitdown")
_ENT = {w.lower().replace(" ", "") for w in (*NAMES, *TOWNS, *OBJECTS, *PSEUDO, *COLOURS, *PETS, *SHAPES, *_EXTRA_WORDS)} | {w.lower() for e in EVENTS for w in e.split() if w != "the"}
_JOIN = (("turn left", "turnleft"), ("turn right", "turnright"), ("sit down", "sitdown"))  # two-word actions are one entity
_TOK = re.compile(r"[A-Za-z][A-Za-z'-]*|\d+|[^\sA-Za-z\d]")


def _ent(tok: str) -> str | None:
    if not tok[0].isalpha():
        return None
    w = tok[:-2] if tok.endswith("'s") else tok
    w = w.lower()
    return w if w in _ENT else None


_W = r"([A-Z][A-Za-z]+)"
# alternative phrasings of one fact (a random surface choice in several shapes) are one fact: rewritten to the first phrasing before the key is taken
_PHRASES = (
    (re.compile(_W + r" is shorter than " + _W + r"\."), r"\2 is taller than \1."),
    (re.compile(_W + r"'s parent is " + _W + r"\."), r"\2 is the parent of \1."),
    (re.compile(_W + r" is (\d+) blocks? south of " + _W + r"\."), r"\3 is \2 blocks north of \1."),
    (re.compile(_W + r" is (\d+) blocks? west of " + _W + r"\."), r"\3 is \2 blocks east of \1."),
    (re.compile(_W + r" is (\d+) blocks? north of " + _W + r"\."), r"\1 is \2 blocks north of \3."),
    (re.compile(_W + r" is (\d+) blocks? east of " + _W + r"\."), r"\1 is \2 blocks east of \3."),
    (re.compile(r"(The [a-z ]+?) took place (\d+) days? before (the [a-z ]+?)\."), r"\3 took place \2 days after \1."),
    (re.compile(r"(The [a-z ]+?) took place (\d+) days? after (the [a-z ]+?)\."), r"\1 took place \2 days after \3."),
)


def structure_key(question: str) -> str:
    q = question
    for pat, rep in _PHRASES:
        q = pat.sub(rep, q)
    q = q.replace("The ", "the ")  # a capital article at a sentence start is not structure
    for a, b in _JOIN:
        q = q.replace(a, b)
    toks = _TOK.findall(q)
    n = len(toks)
    node: dict[str, int] = {}
    edges: list[tuple[str, tuple[int, ...], tuple[tuple[int, ...], ...]]] = []
    cur_t: list[str] = []
    cur_o: list[int] = []
    cur_l: list[tuple[int, ...]] = []
    i = 0
    while i < n:
        t = toks[i]
        w = _ent(t)
        if w is None:
            cur_t.append(t)
            if t in (".", "?", "!"):
                edges.append((" ".join(cur_t), tuple(cur_o), tuple(cur_l)))
                cur_t, cur_o, cur_l = [], [], []
            i += 1
            continue
        members = [w]
        j = i
        while j + 2 < n and toks[j + 1] == "," and (e2 := _ent(toks[j + 2])) is not None:
            members.append(e2)
            j += 2
        if j + 2 < n and toks[j + 1] == "and" and (e2 := _ent(toks[j + 2])) is not None:
            members.append(e2)
            j += 2
        ids = [node.setdefault(m, len(node)) for m in members]
        if len(members) >= 2 and members == sorted(members):  # a list in alphabetical order: an unordered slot
            cur_l.append(tuple(sorted(ids)))
            cur_t.append("L")
        else:
            for k, x in enumerate(ids):
                cur_o.append(x)
                cur_t.append("E")
                if k < len(ids) - 1:
                    cur_t.append(",")
        i = j + 1
    if cur_t:
        edges.append((" ".join(cur_t), tuple(cur_o), tuple(cur_l)))
    colour = [0] * len(node)
    for _ in range(3):
        sig: list[list[tuple[Any, ...]]] = [[] for _ in node]
        for t, o, ls in edges:
            oc = tuple(colour[x] for x in o)
            lc = tuple(tuple(sorted(colour[x] for x in lst)) for lst in ls)
            for k, x in enumerate(o):
                sig[x].append((t, 0, k, oc, lc))
            for jj, lst in enumerate(ls):
                for x in lst:
                    sig[x].append((t, 1, jj, oc, lc))
        keys = [(colour[k], tuple(sorted(sg))) for k, sg in enumerate(sig)]
        rank = {kk: r for r, kk in enumerate(sorted(set(keys)))}
        colour = [rank[kk] for kk in keys]
    final = sorted((t, tuple(colour[x] for x in o), tuple(tuple(sorted(colour[x] for x in lst)) for lst in ls)) for t, o, ls in edges)
    return hashlib.blake2b(repr(final).encode(), digest_size=10).hexdigest()


def demand(g: int, level: int) -> int:
    return lg.demand_at_g(g, level)


def exhibit_structure(lid: str, level: int, need: int) -> tuple[int, int]:
    lin = next(x for x in v2.registered_v2() if x.id == lid)
    keys: set[str] = set()
    rng = stream(lg.STAT_SEED, "capacity-structure", lid, str(level))
    cap = 3 * need + 2000
    att = 0
    while len(keys) < need and att < cap:
        att += 1
        keys.add(structure_key(build_item(lin, level, rng, "A", "cap").question))
    return len(keys), att


def _job(args: tuple[str, int, int]) -> dict[str, Any]:
    lid, level, need = args
    t0 = time.time()
    found, att = exhibit_structure(lid, level, need)
    return {"id": lid, "level": level, "need": need, "found": found, "attempts": att, "passed": found >= need, "seconds": round(time.time() - t0, 2)}


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    scen = {"G13": 13, "G8": 8}
    reg = v2.registered_v2()
    jobs = []
    # exhibit up to the larger demand (G = 8); a shape that reaches it also reaches the smaller one
    for lin in reg:
        for lv in ALL_LEVELS:
            jobs.append((lin.id, lv, 10 * demand(8, lv)))
    with multiprocessing.get_context("fork").Pool(workers) as pool:
        res = pool.map(_job, jobs, chunksize=1)
    by: dict[str, dict[int, dict[str, Any]]] = {}
    for r in res:
        by.setdefault(r["id"], {})[r["level"]] = r
    ct = v2.cluster_table_v2(reg)
    report: dict[str, Any] = {"scenarios": scen, "demand_rule": "10 x (ceil(24000 / G) + 100) on a core level, 10 x 100 on a reserve level", "shapes": {}, "clusters": {}, "failures": {}}
    for sid, lv in by.items():
        report["shapes"][sid] = {str(k): v for k, v in sorted(lv.items())}
    for g_name, g in scen.items():
        fails = []
        for cid, members in sorted(ct.items()):
            for level in ALL_LEVELS:
                need = 10 * demand(g, level)
                tot = sum(by[m.id][level]["found"] for m in members)  # an upper bound for the cluster: shapes' structures taken as disjoint
                best = max(by[m.id][level]["found"] for m in members)
                if tot < need:
                    fails.append({"cluster": cid, "level": level, "need": need, "cluster_sum_of_shapes": tot, "best_single_shape": best, "shapes": {m.id: by[m.id][level]["found"] for m in members}})
        report["failures"][g_name] = fails
    # shapes alone against the whole-cluster demand (least favourable: one shape carries its cluster)
    for g_name, g in scen.items():
        report["failures"][g_name + "_single_shape"] = [{"shape": sid, "level": lv, "need": 10 * demand(g, lv), "found": by[sid][lv]["found"], "attempts": by[sid][lv]["attempts"]} for sid in sorted(by) for lv in ALL_LEVELS if by[sid][lv]["found"] < 10 * demand(g, lv)]
    (OUT / "r1_rev4_capacity.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    lines = ["# R1 revision-4 capacity on structure (MEASURED by exhibition; names, setting and presentation order do not count)", "",
             "Required distinct structures = 10 x (ceil(24,000 / G) + 100) on core levels 1-5, 10 x 100 on reserve levels 0 and 6 (derivation in the module docstring of `r1_rev4_capacity.py`). G = 13 gives 19,470 on a core level; G = 8 gives 31,000.", ""]
    for g_name, g in scen.items():
        lines += [f"## Scenario {g_name}: G = {g} (core-level requirement {10 * demand(g, 3):,})", "", "### Clusters that fail (sum over their shapes' exhibited structures, an upper bound)", ""]
        f = report["failures"][g_name]
        lines += (["| cluster | level | need | cluster sum | best single shape |", "|---|---|---|---|---|"] + [f"| {x['cluster']} | {x['level']} | {x['need']:,} | {x['cluster_sum_of_shapes']:,} | {x['best_single_shape']:,} |" for x in f]) if f else ["none"]
        lines += ["", "### Single shapes below the whole-cluster requirement (least favourable: one shape carries its cluster)", ""]
        f2 = report["failures"][g_name + "_single_shape"]
        lines += (["| shape | level | need | exhibited | draws |", "|---|---|---|---|---|"] + [f"| {x['shape']} | {x['level']} | {x['need']:,} | {x['found']:,} | {x['attempts']:,} |" for x in f2]) if f2 else ["none"]
        lines.append("")
    (OUT / "r1_rev4_capacity.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
