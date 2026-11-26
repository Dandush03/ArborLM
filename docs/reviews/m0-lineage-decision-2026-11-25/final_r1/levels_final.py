# ruff: noqa
"""Final R1 audit: levels. For each survivor and level, n items at seed base B (Random(B + level)).
(1) Distinctness: (a) audit-4 identity test (same Random(seed) for every level; identical streams = one generator), (b) cross-level text overlap
(number of normalised texts of level a that also occur among the items of level b), (c) per-level means of text-derived parameters.
(2) The difficulty parameter, measured from the TEXT with this auditor's own parsers (no structured field is read), mean / min / max per level,
and whether its mean rises strictly (or weakly) from level 0 to 6.
usage: python levels_final.py <n> <B> <out.json>"""
import json, os, random, re, statistics, sys
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen
from studies.m0.core import Retry, normalise


def sents(q):
    return [s for s in re.split(r"(?<=[.?])\s+", q) if s]


def bfs_hops(adj, s, t):
    d = {s: 0}; dq = deque([s])
    while dq:
        u = dq.popleft()
        for v in adj.get(u, ()):
            if v not in d:
                d[v] = d[u] + 1; dq.append(v)
    return d.get(t)


def p_boolean(q):
    return {"presses": len(re.search(r"pressed in this order: ([a-z, ]+)\.", q).group(1).split(", ")),
            "lamps": int(re.search(r"There are (\d+) lamps", q).group(1)), "switches": len(re.findall(r"switch toggles", q))}


def p_cde(q):
    par = dict(re.findall(r"Every (\w+) is an? (\w+)\.", q))
    g = re.search(r"\. [A-Z]\w+ is an? (\w+)\. Can", q).group(1)
    depth = 0
    while g in par:
        g = par[g]; depth += 1
    return {"groups_sentences": len(par), "chain_from_person": depth, "property_rules": len(re.findall(r"(?<![\w])An? \w+ (?:can|cannot) \w+\.", q))}


def p_compass(q):
    return {"commands": len(re.search(r"You are facing \w+\. You (.+)\. Which", q).group(1).split(", then "))}


def p_dtree(q):
    rule = re.search(r"Your rule is: (.+)\. Right now", q).group(1)
    depth = mx = 0
    for ch in rule:
        if ch == "(":
            depth += 1; mx = max(mx, depth)
        elif ch == ")":
            depth -= 1
    return {"lights_stated": len(re.findall(r"it is (?:true|false) that the", q)), "max_paren_depth": mx, "options": len(re.split(r", | and ", re.search(r"Choose from (.+)\.$", q).group(1)))}


def p_threshold(q):
    return {"members": len(re.findall(r"has weight", q))}


def p_exch(q):
    adj = {}
    for a, x, b, y in re.findall(r"(\d+) units of (.+?) are worth the same as (\d+) units of (.+?)\.(?: |$)", q):
        adj.setdefault(x, set()).add(y); adj.setdefault(y, set()).add(x)
    m = re.search(r"How many units of (.+?) are worth the same as (\d+) units of (.+?)\?$", q)
    return {"rate_sentences": q.count("are worth the same as") - 1, "hops_between_asked": bfs_hops(adj, m.group(3), m.group(1))}


def p_route(q):
    adj = {}
    roads = re.findall(r"road between (.+?) and (.+?) of length (\d+)\.", q)
    for a, b, _ in roads:
        adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
    m = re.search(r"from (.+?) to (.+?) along", q)
    return {"towns": len(adj), "roads": len(roads), "min_hops": bfs_hops(adj, m.group(1), m.group(2))}


def p_kk(q):
    return {"people": len(re.findall(r'\w+ says: "', q))}


def p_grid(q):
    m = re.search(r"A map has (\d+) rows .*? and (\d+) columns", q)
    return {"cells": int(m.group(1)) * int(m.group(2)), "moves": len(re.search(r"You move (.+?), one cell", q).group(1).split(", then ")), "walls": len(re.findall(r"\bwall\b", q)) - 1}


def p_swap(q):
    return {"operations": len(re.findall(r"swap what they are holding|all at once", q)), "people": len(re.findall(r" holds the ", q))}


def p_weekday(q):
    adj = {}
    links = [m.groups() for m in (re.fullmatch(r"The (.+?) took place \d+ days? (?:before|after) the (.+?)\.", x) for x in re.split(r"(?<=[.?])\s+", q)) if m]  # FIX: per sentence (a findall over the whole text let the first name span the anchor sentence; my slip)
    for a, b in links:
        adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
    anc = re.search(r"The (.+?) took place on a \w+day\.", q).group(1)
    ask = re.search(r"did the (.+?) take place\?", q).group(1)
    return {"links": len(links), "hops_anchor_to_asked": bfs_hops(adj, anc, ask)}


def p_venn(q):
    ask = re.search(r"How many of the people are in (.+?)\?", q).group(1)
    return {"groups": len(re.findall(r"people are in the \w+ group", q)), "total": int(re.search(r"Among (\d+) people", q).group(1)),
            "ask_" + ask.replace(" ", "_"): 1}


P = {"R1.boolean_lights_r4": p_boolean, "R1.categories_default_exceptions_r4": p_cde, "R1.compass_turns": p_compass, "R1.conditional_decision_tree_r6": p_dtree,
     "R1.conditional_threshold_rule_r4": p_threshold, "R1.equivalence_exchange_rates_r6": p_exch, "R1.graph_shortest_route_r6": p_route, "R1.knights_knaves_r6": p_kk,
     "R1.spatial_grid_walk_r5": p_grid, "R1.swap_tracking_r5": p_swap, "R1.temporal_weekday_shift_r6": p_weekday, "R1.venn_counting_r5": p_venn}


def stream(lin, lv, seed, n):
    r = random.Random(seed); out = []
    while len(out) < n:
        try:
            b = lin.build(lv, r); out.append((b.question, b.answer))
        except Retry:
            pass
    return out


n, B, outp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
L = fgen.lineages()
res = {}
for lid in sorted(L):
    lin = L[lid]
    its = {lv: fgen.items(lin, lv, n, B) for lv in range(7)}
    texts = {lv: {normalise(b.question) for b in its[lv]} for lv in range(7)}
    overlap = {f"{a}-{b}": len(texts[a] & texts[b]) for a in range(7) for b in range(a + 1, 7)}
    ident = []
    for lv in range(7):
        s = stream(lin, lv, 4243, 100)
        for c in ident:
            if c[1] == s:
                c[0].append(lv); break
        else:
            ident.append([[lv], s])
    params = {}
    for lv in range(7):
        rows = [P[lid](b.question) for b in its[lv]]
        keys = sorted({k for r in rows for k in r})
        params[lv] = {k: {"mean": round(statistics.mean(r.get(k, 0) or 0 for r in rows), 3), "min": min(r.get(k, 0) or 0 for r in rows), "max": max(r.get(k, 0) or 0 for r in rows)} for k in keys}
        params[lv]["chars"] = {"mean": round(statistics.mean(len(b.question) for b in its[lv]), 1)}
    allk = sorted({k for lv in params for k in params[lv]})
    trend = {}
    for k in allk:
        ms = [params[lv].get(k, {"mean": 0})["mean"] for lv in range(7)]
        trend[k] = {"means": ms, "strictly_rising": all(ms[i] < ms[i + 1] for i in range(6)), "weakly_rising": all(ms[i] <= ms[i + 1] for i in range(6))}
    res[lid] = {"identity_classes": [c[0] for c in ident], "n_identity_classes": len(ident), "cross_level_text_overlap_max": max(overlap.values()), "distinct_texts_per_level": [len(texts[lv]) for lv in range(7)], "trend": trend}
    print(f"{lid:38s} identity classes {len(ident)}  max cross-level overlap {max(overlap.values())}  distinct/level {[len(texts[lv]) for lv in range(7)]}")
    for k in allk:
        t = trend[k]
        print(f"    {k:28s} {' '.join(f'{x:8.2f}' for x in t['means'])}  strict={t['strictly_rising']} weak={t['weakly_rising']}")
json.dump(res, open(outp, "w"), indent=1, sort_keys=True)
