# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Structural capacity of the R1 shapes under two readings of 'a distinct item' (fix round 3; lead rulings R-5, R-10, R-11, R-16).

Reading (a): names, settings, order of presentation and the direction of symmetric phrasings are relabelled: two items are the same if one is the other under a renaming of people, towns, events, objects and invented words
(the 'entities') and a reordering of statements. Reading (b): in addition the 'labels' (colours, shapes, marks, the letters of the conditional rules, lamp numbers) are relabelled.

Method. Each item's structured form is normalised (``NORM``: parallel lists are zipped, index references become the names, symmetric pairs are sorted, construction metadata that the text does not show is dropped), then reduced
to a key that is invariant under renaming and under the reordering of unordered lists: a Weisfeiler-Lehman colour refinement (3 rounds) over the containers an entity word occurs in. The key is a function of the structure up to
isomorphism, but two non-isomorphic structures can share a key, so the number of distinct keys is a LOWER bound on the number of structures (conservative for the gate). From N draws per (shape, level):
  D = distinct keys, C = colliding pairs; the collision estimate S = N (N - 1) / (2 C) of 1 / sum(p^2) is at most the support; with no collision the 95 % lower bound is N (N - 1) / 6.
A cell PASSES when its lower bound or estimate reaches the demand. Demand (R-10, R-11): 10 x (ceil(4,000 / G) + ceil(20,000 / G) + 100) per cluster and level, G = 11: 22,830 (reserve levels carry the same demand).
Run (worktree root): PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix3_capacity <N> <seed> [substring] [levels]
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from collections.abc import Callable
from typing import Any

from studies.m0.vocab import COLOURS, EVENTS, MARKS, NAMES, OBJECTS, PETS, PSEUDO, SHAPES, TOWNS

G = 11
DEMAND = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
_HOBBIES = ("chess", "choir", "diving", "poetry", "rowing", "archery", "baking")
_WORD = re.compile(r"[A-Za-z§][A-Za-z§0-9'-]*")  # a hyphenated word ("yo-yo") is one token
ENT = set(NAMES) | set(TOWNS) | set(OBJECTS) | set(PETS) | set(PSEUDO) | {w.capitalize() for w in PSEUDO} | set(_HOBBIES) | {w for e in EVENTS for w in e.split() if w != "the"}
LAB = set(COLOURS) | set(SHAPES) | {w for m in MARKS for w in m.split() if w != "a"} | {chr(65 + i) for i in range(12)}
KW_ORDERED = {"attr", "not", "if", "do", "turn", "walk", "pay", "earn", "half", "swap", "rotate", "move", "reverse", "join", "cut", "serve", "leave", "front_to_back", "position", "champion", "runner_up", "beaten_by", "range", "dur",
              "adj", "left", "end", "pos", "between", "notnext", "owns", "either", "was", "k", "give"}


def _h(x: object) -> str:
    return hashlib.sha256(repr(x).encode()).hexdigest()[:16]


def _srt(pair: list) -> list:
    return sorted(pair)


def _lamp(i: int) -> str:
    return f"§lamp{i}"


# ---------------------------------------------------------------- normalisers: structured form -> a form whose lists are either ordered (ORDERED paths / keyword lists) or multisets


def _n_activity(s: dict) -> dict:
    return {"m": s["meetings"]}


def _n_attr(s: dict) -> dict:
    return {"rule": s["rule"], "b": [{"o": o, "a": [it["colour"], it["shape"], it["mark"]]} for o, it in zip(s["owners"], s["items"], strict=True)]}


def _n_lights(s: dict) -> dict:
    return {"init": {_lamp(i + 1): v for i, v in enumerate(s["initial"])}, "sw": {c: [_lamp(x) for x in v] for c, v in s["switches"].items()}, "pr": s["presses"], "ask": _lamp(s["ask"])}


def _n_catfollow(s: dict) -> dict:
    c = s["cats"]
    return {"all": [[c[a], c[b]] for a, b in s["all"]], "none": [_srt([c[a], c[b]]) for a, b in s["none"]], "some": [_srt([c[a], c[b]]) for a, b in s["some"]], "kind": s["kind"], "x": c[s["x"]], "y": c[s["y"]]}


def _n_chain(s: dict) -> dict:
    return {"facts": s["facts"], "rules": [{"if": a, "then": c} for a, c in s["rules"]], "query": s["query"]}


def _n_threshold(s: dict) -> dict:
    return {"members": s["members"], "votes": [[k, v] for k, v in s["votes"].items()], "margin": s["margin"]}


def _n_stack(s: dict) -> dict:
    return {"initial": [[p, v] for p, v in s["initial"].items()], "ops": s["ops"], "ask": s["ask"]}


def _n_eqclass(s: dict) -> dict:
    return {"same": [_srt(p) for p in s["same"]], "diff": [_srt(p) for p in s["different"]], "q": _srt([s["x"], s["y"]])}


def _n_event(s: dict) -> dict:
    return {"rel": s["rel"], "q": _srt([s["x"], s["y"]])}


def _n_bip(s: dict) -> dict:
    return {"r": [_srt(p) for p in s["rivals"]]}


def _n_route(s: dict) -> dict:
    return {"r": [[[a, b], w] for a, b, w in s["roads"]], "q": [s["start"], s["end"]]}


def _n_parent(s: dict, extra: dict) -> dict:
    return {"p": [[p, c] for c, p in sorted(s["parent"].items())], **extra}


def _n_knights(s: dict) -> dict:
    ppl = s["people"]
    st = []
    for i, (k, a) in enumerate(s["statements"]):
        names = [ppl[j] for j in a]
        st.append({"s": ppl[i], "k": k, "a": names} if k in ("is_knight", "is_knave") else {"s": ppl[i], "k": k, "sym": names})  # "sym": an unordered pair
    return {"st": st, "who": ppl[s["who"]]}


def _n_mst(s: dict) -> dict:
    return {"r": [[[a, b], w] for a, b, w in s["roads"]]}


def _n_culprit(s: dict) -> dict:
    ppl = s["people"]
    return {"st": [{"s": ppl[i], "k": x[0], ("sym" if x[0] == "either" else "a"): [ppl[j] for j in x[1:]]} for i, x in enumerate(s["statements"])], "t": s["true_count"]}


def _n_seating(s: dict) -> dict:
    p = s["people"]
    out: list[list] = []
    for c in s["clues"]:
        k = c[0]
        if k in ("adj", "left"):
            out.append([k, p[c[1]], p[c[2]]])
        elif k == "end":
            out.append([k, p[c[1]]])
        elif k == "pos":
            out.append([k, p[c[1]], c[2]])
        elif k == "between":
            out.append([k, p[c[2]], [p[c[1]], p[c[3]]]])  # the middle person, then an unordered pair of the two outer ones
        else:
            out.append([k, [p[c[1]], p[c[2]]]])  # an unordered pair
    return {"c": out, "seat": s["seat"]}


def _n_grid(s: dict) -> dict:
    g = [[c if c else "WALL" for c in row] for row in s["grid"]]
    return {"grid": g, "start": g[s["start"][0]][s["start"][1]], "moves": s["moves"]}


_FLIP = {"south": "north", "west": "east"}


def _n_reldir(s: dict) -> dict:
    f = []
    for a, d, k, b in s["facts"]:
        f.append([b, _FLIP[d], k, a] if d in _FLIP else [a, d, k, b])
    return {"f": f, "q": _srt([s["x"], s["y"]])}


def _n_swap(s: dict) -> dict:
    ops = []
    for o in s["ops"]:
        if o[0] == "swap":
            ops.append(["swap", [o[1], o[2]]])  # an unordered pair
        else:
            a, b, c = o[1:]
            ops.append(["rotate", [["give", a, b], ["give", b, c], ["give", c, a]]])  # an unordered set of three hand-overs
    return {"hold": [[p, i] for p, i in s["hold"].items()], "ops": ops, "who": s["who"]}


def _n_cpath(s: dict) -> dict:
    return {"jobs": [{"p": p, "d": d, "w": w} for p, d, w in s["jobs"]]}


def _n_overlap(s: dict) -> dict:
    iv = []
    for e, sp in zip(s["events"], s["spans"], strict=True):
        a, b = (sp[1], sp[2]) if sp[0] == "range" else (sp[1], sp[1] + sp[2] - 1)
        iv.append([e, a, b])
    return {"iv": iv, "q": _srt([s["x"], s["y"]])}


def _n_weekday(s: dict) -> dict:
    return {"l": [[b, a, k] for a, b, k in s["links"]], "anchor": s["anchor"], "ask": s["ask"]}


def _n_topo(s: dict) -> dict:
    # the tie-break is alphabetical, so a renaming that changes the alphabetical order changes the item: names become their alphabetical rank (a literal number), only order-preserving renamings are identified
    rank = {p: f"{i:02d}" for i, p in enumerate(sorted(p for p, _ in s["jobs"]))}
    return {"jobs": [{"p": rank[p], "w": [rank[x] for x in w]} for p, w in s["jobs"]], "day": s["day"]}


def _n_accounts(s: dict) -> dict:
    return {"start": [[p, v] for p, v in s["start"].items()], "ops": s["ops"], "ask": s["ask"]}


def _n_venn(s: dict) -> dict:
    return {"total": s["total"], "sizes": [[g, n] for g, n in s["sizes"].items()], "pairs": [[k.split("|"), n] for k, n in s["pairs"].items()], "triples": [[k.split("|"), n] for k, n in s["triples"].items()], "quad": s["quad"], "ask": s["ask"]}


def _n_exchange(s: dict) -> dict:
    return {"rates": [_srt([[p, a], [q, b]]) for p, a, q, b in s["rates"]], "q": [s["x"], s["y"], s["n"]]}


def _n_roads(s: dict) -> dict:
    t = s["towns"]
    return {"r": [[t[a], t[b]] for a, b in s["roads"]], "q": [t[s["x"]], t[s["y"]]]}


def _n_dtree(s: dict) -> dict:
    return {"tree": s["tree"], "facts": [[k, v] for k, v in s["facts"].items()], "actions": s["actions"]}


def _n_default(s: dict) -> dict:
    return {"chain": s["chain"], "rules": s["rules"], "member": s["member"], "verb": s["verb"]}


def _n_nim(s: dict) -> dict:
    return {"piles": s["piles"]}


def _n_minimax(s: dict) -> dict:
    return {"tree": s["tree"], "first": s["first"]}


def _n_bracket(s: dict) -> dict:
    return {"players": s["players"], "results": s["results"], "ask": s["ask"]}


def _n_queue(s: dict) -> dict:
    return {"line": s["line"], "ops": s["ops"], "ask": s["ask"]}


def _n_compass(s: dict) -> dict:
    return {"start": s["start"], "seq": s["seq"]}


def _n_order(s: dict) -> dict:
    return {"t": s["taller"], "q": [s["x"], s["y"]]}


# base name -> (normaliser, ordered paths)
SPEC: dict[str, tuple[Callable[[dict], dict], set[str]]] = {
    "activity_selection": (_n_activity, {"m/*"}),
    "attribute_rule": (_n_attr, {"b/*/a"}),
    "boolean_lights": (_n_lights, {"pr"}),
    "categories_default_exceptions": (_n_default, {"chain", "rules/*"}),
    "categories_follow": (_n_catfollow, {"all/*"}),
    "compass_turns": (_n_compass, {"seq"}),
    "conditional_chain": (_n_chain, {"facts/*", "rules/*/if/*", "rules/*/then"}),
    "conditional_decision_tree": (_n_dtree, set()),
    "conditional_threshold_rule": (_n_threshold, {"members/*", "votes/*"}),
    "containers_queue_line": (_n_queue, {"line", "ops", "ask"}),
    "containers_stack_piles": (_n_stack, {"initial/*/1", "ops"}),
    "elimination_bracket": (_n_bracket, {"players", "results/*"}),
    "equivalence_classes": (_n_eqclass, set()),
    "equivalence_exchange_rates": (_n_exchange, {"q", "rates/*/*"}),
    "event_timeline": (_n_event, {"rel/*"}),
    "graph_bipartite": (_n_bip, set()),
    "graph_shortest_route": (_n_route, {"r/*"}),
    "kinship_ancestor": (lambda s: _n_parent(s, {"child": s["child"], "g": s["generations"], "options": s["options"]}), {"p/*"}),
    "kinship_cousins": (lambda s: _n_parent(s, {"q": _srt([s["x"], s["y"]])}), {"p/*"}),
    "kinship_descendants": (lambda s: _n_parent(s, {"cands": s["candidates"], "root": s["root"]}), {"p/*"}),
    "knights_knaves": (_n_knights, {"st/*/a"}),  # "sym" lists are unordered pairs
    "minimax_tree": (_n_minimax, set()),
    "mst_cost": (_n_mst, {"r/*"}),
    "nim_xor": (_n_nim, set()),
    "one_culprit": (_n_culprit, {"st/*/a"}),
    "order_compare": (_n_order, {"t/*", "q"}),
    "road_reachability": (_n_roads, {"r/*", "q"}),
    "seating_row": (_n_seating, {"c/*"}),
    "spatial_grid_walk": (_n_grid, {"grid", "grid/*", "moves"}),
    "spatial_relative_directions": (_n_reldir, {"f/*"}),
    "swap_tracking": (_n_swap, {"ops", "hold/*"}),
    "temporal_critical_path": (_n_cpath, set()),
    "temporal_interval_overlap": (_n_overlap, {"iv/*"}),
    "temporal_weekday_shift": (_n_weekday, {"l/*", "anchor"}),
    "topological_order": (_n_topo, set()),
    "tracking_accounts": (_n_accounts, {"start/*", "ops"}),
    "venn_counting": (_n_venn, {"sizes/*", "pairs/*", "triples/*"}),
}


# ---------------------------------------------------------------- canonical form


def _words(s: str) -> list[str]:
    return _WORD.findall(s)


def _is_ent(w: str) -> bool:
    return w in ENT or w.startswith("§")


def _is_lab(w: str) -> bool:
    return w in LAB


class _Canon:
    def __init__(self, ordered: set[str], relabel_labels: bool) -> None:
        self.ordered = ordered
        self.rl = relabel_labels

    def tokenised(self, s: str, col: dict[str, str], star: str | None) -> str:
        def sub(m: re.Match[str]) -> str:
            w = m.group(0)
            if w == star:
                return "*"
            if w in col:
                return "<" + col[w] + ">"
            return w

        return _WORD.sub(sub, s)

    def canon(self, v: Any, col: dict[str, str], path: str, star: str | None = None, depth: int = 0) -> str:
        if isinstance(v, str):
            return self.tokenised(v, col, star)
        if isinstance(v, bool) or v is None or isinstance(v, int | float):
            return repr(v)
        if isinstance(v, dict):
            items = []
            for k, val in v.items():
                kp = k if depth == 0 else "~"
                items.append(self.tokenised(str(k), col, star) + ":" + self.canon(val, col, f"{path}/{kp}" if path else kp, star, depth + 1))
            return "{" + ",".join(sorted(items)) + "}"
        elems = [self.canon(e, col, f"{path}/*" if path else "*", star, depth + 1) for e in v]
        ordered = path in self.ordered or (bool(v) and isinstance(v[0], str) and v[0] in KW_ORDERED)
        return "[" + ",".join(elems if ordered else sorted(elems)) + "]"

    def containers(self, v: Any, path: str, depth: int = 0):  # yields (node, path, direct words)
        if isinstance(v, dict):
            words = [w for k in v for w in _words(str(k))]
            words += [w for val in v.values() if isinstance(val, str) for w in _words(val)]
            yield v, path, words
            for k, val in v.items():
                kp = k if depth == 0 else "~"
                yield from self.containers(val, f"{path}/{kp}" if path else kp, depth + 1)
        elif isinstance(v, list):
            words = [w for e in v if isinstance(e, str) for w in _words(e)]
            yield v, path, words
            for e in v:
                yield from self.containers(e, f"{path}/*" if path else "*", depth + 1)

    def key(self, st: dict) -> str:
        ws = sorted({w for _, _, words in self.containers(st, "") for w in words if _is_ent(w) or _is_lab(w)})
        col = {w: ("E" if _is_ent(w) else ("L" if self.rl else "L:" + w)) for w in ws}
        cont = list(self.containers(st, ""))
        for _ in range(3):
            ctx: dict[str, list[str]] = {w: [] for w in ws}
            for node, path, words in cont:
                for w in set(words):
                    if w in col and (_is_ent(w) or self.rl):
                        ctx[w].append(self.canon(node, col, path, star=w, depth=path.count("/") + 1 if path else 0))
            col = {w: (_h((col[w], sorted(ctx[w]))) if (_is_ent(w) or self.rl) else col[w]) for w in ws}
        return _h(self.canon(st, col, ""))


def keys_of(lid: str, structured: dict) -> tuple[str, str]:
    base = re.sub(r"_r\d+$", "", lid.split(".", 1)[1])
    norm, ordered = SPEC[base]
    st = json.loads(json.dumps(norm(structured)))
    return _Canon(ordered, False).key(st), _Canon(ordered, True).key(st)


def estimate(counter: Counter[str], n: int) -> dict[str, Any]:
    c = sum(v * (v - 1) // 2 for v in counter.values())
    singles = sum(1 for v in counter.values() if v == 1)
    doubles = sum(1 for v in counter.values() if v == 2)
    chao = len(counter) + (singles * singles / (2 * doubles) if doubles else (singles * (singles - 1) / 2 if singles else 0))
    return {"distinct": len(counter), "pairs": c, "S_collision": round(n * (n - 1) / (2 * c)) if c else None, "lower_bound_if_no_collision": round(n * (n - 1) / 6) if not c else None, "chao1": round(chao)}


def verdict(est: dict[str, Any]) -> tuple[bool, str]:
    """PASS when the distinct keys seen already reach the demand, or the collision estimate (or the no-collision bound) does."""
    if est["distinct"] >= DEMAND:
        return True, "distinct keys seen reach the demand"
    s = est["S_collision"] if est["S_collision"] is not None else est["lower_bound_if_no_collision"]
    return (s >= DEMAND, "collision estimate" if est["S_collision"] is not None else "no collision: 95 % lower bound")


def run_cell(lin: Any, level: int, n: int, seed: int) -> dict[str, Any]:
    from studies.m0.core import Retry

    rng = random.Random(seed * 1000 + level)
    ca: Counter[str] = Counter()
    cb: Counter[str] = Counter()
    got = tries = 0
    while got < n:
        tries += 1
        if tries > 40 * n + 200:
            raise RuntimeError(f"{lin.id} level {level}: too many Retry")
        try:
            b = lin.build(level, rng)
        except Retry:
            continue
        a, bb = keys_of(lin.id, b.structured)
        ca[a] += 1
        cb[bb] += 1
        got += 1
    ea, eb = estimate(ca, n), estimate(cb, n)
    return {"id": lin.id, "level": level, "N": n, "a": ea, "b": eb, "pass_a": verdict(ea)[0], "pass_b": verdict(eb)[0], "demand": DEMAND}


def _cell(args: tuple[str, int, int, int]) -> dict[str, Any]:
    lid, level, n, seed = args
    from studies.m0.lineages_r1_fix3_clusters import registered_v3

    lin = next(x for x in registered_v3() if x.id == lid)
    return run_cell(lin, level, n, seed)


def main() -> None:
    from multiprocessing import Pool

    from studies.m0.lineages_r1_fix3_clusters import registered_v3

    n, seed = int(sys.argv[1]), int(sys.argv[2])
    filt = sys.argv[3] if len(sys.argv) > 3 else ""
    levels = [int(x) for x in sys.argv[4].split(",")] if len(sys.argv) > 4 else list(range(7))
    jobs = [(x.id, lv, n, seed) for x in registered_v3() if not filt or filt in x.id for lv in levels]
    with Pool(12) as p:
        for row in p.imap_unordered(_cell, jobs):
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
