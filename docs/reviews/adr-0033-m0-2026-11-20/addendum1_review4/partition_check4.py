# ruff: noqa
"""Independent check 4 of ADR-0033 addendum 1, draft 4 (commit 471a1edb): section 4 steps 1 to 3 (borderline groups),
written from the text of section 4 and section 13 items 17 and 20. Auditor's own code; standard library only.

Disclosure: the concrete maps of V1 to V8 are copied from the drafter's partition_vector_rev4.py (the addendum
describes V6 to V8 only in words). I read that script before writing this one; the implementation below is my own
(BFS components, explicit _randbelow shuffle, separate counting), not a copy.

Options computed (section 13 item 17 x item 20):
  nc   = 'pass'   : a cluster with no candidate lineage is a node of the group graph (item 17 a, drafted)
         'ignore' : it is not a node; a borderline pair touching it does nothing (item 17 b)
  rule = 'a'      : section 4 steps 2/3 as drafted (balance in clusters; step 3 passes over a group that does not fit)
         'b'      : as (a) but step 3 stops at the first group that does not fit
         'c'      : draft 3's item 9 literally (counted in groups; group identity = smallest cluster identity in it,
                    all clusters); 'c*' = the drafter's rendering of (c) (identity among candidate clusters only)
Part 2 runs random maps: agreement with the drafter's function (loaded read-only from its file, -B so no .pyc),
and the invariants asked about.
Run (from the agent-a0c9d741 worktree): uv run --locked python -I -B <this file> <path of partition_vector_rev4.py>
"""
from __future__ import annotations

import hashlib
import importlib.util
import random
import sys
from collections import deque

SEED = 400004
EVALS = ("R1", "R2", "M1", "C1")


def rng_for(*labels: str) -> random.Random:
    s = "|".join([str(SEED), *labels]).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(s).digest()[:8], "big"))


def shuffle_text(ids, rng: random.Random) -> list[str]:
    """Section 4: sort by code point, then for i from len-1 down to 1: j = _randbelow(i+1), swap i and j."""
    x = sorted(ids)
    for i in range(len(x) - 1, 0, -1):
        j = rng._randbelow(i + 1)
        x[i], x[j] = x[j], x[i]
    return x


def comps_bfs(nodes, edges):
    adj = {n: [] for n in nodes}
    for a, b in edges:
        if a in adj and b in adj:
            adj[a].append(b)
            adj[b].append(a)
    seen, out = set(), []
    for n in sorted(nodes):
        if n in seen:
            continue
        q, comp = deque([n]), []
        seen.add(n)
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        out.append(sorted(comp))
    return out


def run(lin: dict[str, bool], links, borderline, nc="pass", rule="a"):
    ev = lambda x: x.split(".", 1)[0]
    clusters = comps_bfs(list(lin), links)
    cid = {}
    for mem in clusters:
        for x in mem:
            cid[x] = mem[0]
    cev = {mem[0]: {ev(x) for x in mem if lin[x]} for mem in clusters}
    hascand = {c: bool(s) for c, s in cev.items()}
    cedges = {tuple(sorted((cid[a], cid[b]))) for a, b in borderline if cid[a] != cid[b]}
    nodes = list(cev) if nc == "pass" else [c for c in cev if hascand[c]]
    raw = comps_bfs(nodes, cedges)
    groups = {}
    for g in raw:
        cc = [c for c in g if hascand[c]]
        if not cc:
            continue
        ident = min(g) if rule == "c" else min(cc)
        groups[ident] = cc
    gev = {g: set().union(*(cev[c] for c in cc)) for g, cc in groups.items()}
    w = {g: len(cc) for g, cc in groups.items()}
    we = lambda g, e: sum(1 for c in groups[g] if e in cev[c])
    X = [g for g in groups if len(gev[g]) >= 2]
    part = {}
    na = nb = 0
    for i, g in enumerate(shuffle_text(X, rng_for("cluster-partition", "cross"))):
        if rule in ("c", "c*"):
            tob = i % 2 == 0
        else:
            tob = nb <= na
        part[g] = "B" if tob else "A"
        if tob:
            nb += w[g]
        else:
            na += w[g]
    step2 = (na, nb)
    diag = {}
    for e in EVALS:
        L = [g for g in groups if gev[g] == {e}]
        order = shuffle_text(L, rng_for("cluster-partition", e))
        if rule in ("c", "c*"):
            n_g = sum(1 for g in groups if e in gev[g])
            a_g = sum(1 for g in X if e in gev[g] and part[g] == "A")
            k = min(len(order), max(0, n_g // 2 - a_g))
            for i, g in enumerate(order):
                part[g] = "A" if i < k else "B"
            diag[e] = None
        else:
            n_e = sum(1 for c in cev if e in cev[c])
            a_e = sum(we(g, e) for g in X if part[g] == "A")
            p, stop = 0, False
            for g in order:
                ok = (a_e + p + we(g, e) <= n_e // 2) and not stop
                if rule == "b" and not ok:
                    stop = True
                if ok:
                    part[g] = "A"
                    p += we(g, e)
                else:
                    part[g] = "B"
            diag[e] = (n_e, a_e)
    cpart = {c: part[g] for g, cc in groups.items() for c in cc}
    rep = {}
    for e in EVALS:
        cs = [c for c in cev if e in cev[c]]
        a = sum(1 for c in cs if cpart[c] == "A")
        rep[e] = (len(cs), a, len(cs) - a)
    return dict(cpart=cpart, rep=rep, groups=groups, X=X, step2=step2, diag=diag, nopart=sorted(c for c in cev if not hascand[c]))


def M(spec):
    return {t.rstrip("!"): not t.endswith("!") for t in spec.split()}


V = {
    "V1": (M("R1.alpha R1.beta R1.gamma R1.delta! R1.epsilon R1.zeta R2.alpha R2.beta R2.gamma R2.delta R2.epsilon M1.alpha M1.beta M1.gamma M1.delta C1.alpha C1.beta C1.gamma C1.delta C1.epsilon!"),
           [("R1.alpha", "R1.beta"), ("C1.alpha", "R2.alpha"), ("C1.beta", "R2.beta"), ("M1.alpha", "R2.gamma"), ("C1.gamma", "M1.beta"), ("R1.gamma", "R1.delta"), ("C1.epsilon", "R1.epsilon")], []),
    "V2": (M("R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c C1.a C1.b C1.c C1.d C1.e C1.f! C1.g!"),
           [("C1.a", "R2.a"), ("C1.b", "R2.b"), ("C1.c", "R2.c"), ("C1.d", "M1.a"), ("C1.e", "R1.a"), ("C1.f", "C1.g")], []),
    "V3": (M("R1.e R2.e C1.e! R1.a M1.a C1.a C1.b C1.c C1.d"), [("R1.e", "R2.e"), ("C1.e", "R1.e"), ("R1.a", "M1.a")], []),
    "V4": (M("R1.p R1.q R1.r R1.s R2.p! R2.q R2.r M1.p M1.q C1.p C1.q"), [("R1.p", "R2.p"), ("R1.q", "R2.p"), ("R2.q", "C1.p"), ("M1.p", "C1.q")], []),
    "V5": (M("C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c R2.f R2.z0"),
           [("C1.a", "R2.a"), ("C1.b", "M1.b"), ("C1.c", "R2.c"), ("C1.d", "R1.d"), ("C1.e", "R1.e"), ("C1.f", "R2.f"), ("C1.g", "R1.g")], []),
    "V6": (M("R1.a R1.b R1.c R1.d R1.e R1.f R1.g R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c M1.d C1.a C1.b C1.c C1.d C1.x!"),
           [("C1.a", "R2.a"), ("M1.a", "R2.b"), ("C1.b", "R2.c")],
           [("R1.a", "C1.x"), ("C1.x", "R1.b"), ("R1.b", "C1.a"), ("R1.c", "R1.d"), ("M1.b", "R2.b")]),
    "V7": (M("R1.a R1.b R1.c R1.d C1.x!"), [], [("R1.a", "C1.x"), ("C1.x", "R1.b")]),
    "V8": (M("R1.a R1.b R1.c R1.d R1.e R1.f"), [], [("R1.a", "R1.b"), ("R1.b", "R1.c")]),
}

# Part A as printed in partition_vector_rev4.out.txt (c4fbae36...), keyed (vector, nc, rule); copied by hand
DRAFTER = {
    ("V6", "pass", "a"): ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
    ("V7", "pass", "a"): ["R1.c", "R1.d"],
    ("V8", "pass", "a"): ["R1.d", "R1.e", "R1.f"],
    ("V6", "ignore", "a"): ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.g", "R2.e"],
    ("V7", "ignore", "a"): ["R1.a", "R1.b"],
    ("V6", "pass", "c*"): ["C1.a", "C1.d", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
    ("V7", "pass", "c*"): ["R1.d"],
    ("V8", "pass", "c*"): ["R1.a", "R1.b", "R1.c", "R1.d"],
    ("V6", "pass", "b"): ["C1.a", "C1.d", "M1.c", "M1.d", "R1.a", "R1.b", "R1.e", "R2.e"],
    ("V8", "pass", "b"): ["R1.d"],
}
REV3_A = {"V1": ["C1.alpha", "C1.beta", "C1.epsilon", "M1.delta", "M1.gamma", "R1.alpha"], "V2": ["C1.a", "C1.b", "M1.c", "R1.b"],
          "V3": ["C1.c", "C1.d", "C1.e"], "V4": ["C1.p", "M1.q", "R1.s"], "V5": ["C1.a", "C1.c", "C1.f", "M1.z1", "R1.z0"]}


def part1():
    print("== 1. shuffle check: explicit _randbelow loop equals random.shuffle on 'a'..'h' for all five labels")
    for lab in ("cross", *EVALS):
        r1, r2 = rng_for("cluster-partition", lab), rng_for("cluster-partition", lab)
        x = list("abcdefgh")
        r2.shuffle(x)
        y = shuffle_text("abcdefgh", r1)
        assert x == y
        print(f"   {lab}: {''.join(y)}")
    print("== 2. vectors, every option; '=drafter' / '!=drafter' compares part A with the drafter's printed output")
    mism = 0
    for name in V:
        for nc in ("pass", "ignore"):
            for rule in ("a", "b", "c", "c*"):
                r = run(*V[name], nc=nc, rule=rule)
                A = sorted(c for c, p in r["cpart"].items() if p == "A")
                tag = ""
                if name in REV3_A:
                    tag = "=rev3" if A == REV3_A[name] else "!=rev3"
                    mism += A != REV3_A[name]
                if (name, nc, rule) in DRAFTER:
                    ok = A == DRAFTER[(name, nc, rule)]
                    tag += " =drafter" if ok else " !=drafter"
                    mism += not ok
                if name in REV3_A and (nc, rule) != ("pass", "a"):
                    continue  # V1-V5 printed once; equality checked by tag
                print(f"   {name} nc={nc:6s} rule={rule:2s} A={A} per-eval(N,A,B)={ {e: v for e, v in r['rep'].items() if v[0]} } step2(A,B)={r['step2']} {tag}")
    print(f"   mismatches against drafter / rev3: {mism}")


def rand_map(rr: random.Random):
    lin = {}
    for e in EVALS:
        for i in range(rr.randint(0, 9)):
            lin[f"{e}.l{i:02d}"] = rr.random() < 0.8
    ids = sorted(lin)
    links, bl = [], []
    if len(ids) >= 2:
        for _ in range(rr.randint(0, len(ids) // 2)):
            links.append(tuple(rr.sample(ids, 2)))
        for _ in range(rr.randint(0, len(ids) // 2)):
            bl.append(tuple(rr.sample(ids, 2)))
    return lin, links, bl


def part2(drafter_path: str):
    spec = importlib.util.spec_from_file_location("drafter_rev4", drafter_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rr = random.Random(20261126)
    n = 4000
    disagree = {k: 0 for k in ("pass/a", "ignore/a", "pass/b", "ignore/b", "pass/c*", "ignore/c*")}
    c_vs_cstar = 0
    nobl_differs = 0
    split_group = 0
    viol_a = {"evals": 0, "A>B": 0, "A>B with a_e<=floor": 0, "A>B with a_e>floor": 0, "A>floor with a_e<=floor": 0}
    viol_a_nobl = 0
    viol_c = {"A>B": 0, "A>floor": 0}
    step2_BltA = {"a": 0, "a no borderline": 0}
    total_BltA_a = 0
    ab_order = {"a_moreA_than_c": 0}
    for t in range(n):
        lin, links, bl = rand_map(rr)
        for nc in ("pass", "ignore"):
            for rule, drule in (("a", "clusters"), ("b", "prefix"), ("c*", "groups")):
                mine = run(lin, links, bl, nc, rule)
                _, dpart, drep, _, _ = mod.partition(lin, links, bl, nc, drule)
                if mine["cpart"] != dpart or mine["rep"] != drep:
                    disagree[f"{nc}/{rule}"] += 1
        ra = run(lin, links, bl, "pass", "a")
        rc = run(lin, links, bl, "pass", "c")
        rcs = run(lin, links, bl, "pass", "c*")
        if rc["cpart"] != rcs["cpart"]:
            c_vs_cstar += 1
        r0 = [run(lin, links, [], nc, rule)["cpart"] for nc in ("pass", "ignore") for rule in ("a", "b", "c", "c*")]
        if any(x != r0[0] for x in r0):
            nobl_differs += 1
        for g, cc in ra["groups"].items():
            if len({ra["cpart"][c] for c in cc}) > 1:
                split_group += 1
        for e in EVALS:
            n_e, A, B = ra["rep"][e]
            if n_e == 0:
                continue
            viol_a["evals"] += 1
            _, a_e = ra["diag"][e]
            if A > B:
                viol_a["A>B"] += 1
                viol_a["A>B with a_e<=floor" if a_e <= n_e // 2 else "A>B with a_e>floor"] += 1
            if a_e <= n_e // 2 and A > n_e // 2:
                viol_a["A>floor with a_e<=floor"] += 1
            nn, Ac, Bc = rc["rep"][e]
            if Ac > Bc:
                viol_c["A>B"] += 1
            if Ac > nn // 2:
                viol_c["A>floor"] += 1
        r_nobl = run(lin, links, [], "pass", "a")
        viol_a_nobl += sum(1 for e in EVALS if r_nobl["rep"][e][0] and r_nobl["rep"][e][1] > r_nobl["rep"][e][2])
        if ra["step2"][1] < ra["step2"][0]:
            step2_BltA["a"] += 1
        if r_nobl["step2"][1] < r_nobl["step2"][0]:
            step2_BltA["a no borderline"] += 1
        tA = sum(ra["rep"][e][1] for e in EVALS)
        tB = sum(ra["rep"][e][2] for e in EVALS)
        total_BltA_a += tB < tA
    print(f"== 3. {n} random maps (seed 20261126; 0-9 lineages per evaluation, candidate p=0.8, random links and borderline pairs)")
    print(f"   disagreements with the drafter's partition(), per option (nc/rule): {disagree}")
    print(f"   rule (c) literal (identity over all clusters) differs from the drafter's (c*) in {c_vs_cstar} maps")
    print(f"   with the borderline pairs removed, the eight option combinations differ in {nobl_differs} maps (text: identical)")
    print(f"   groups split across parts under (a)/pass: {split_group}")
    print(f"   (a)/pass, per evaluation with N_e > 0: {viol_a}")
    print(f"   (a)/pass with borderline pairs removed: evaluations with A > B: {viol_a_nobl}")
    print(f"   (c)/pass literal, per evaluation: {viol_c}")
    print(f"   step 2 ends with B < A (clusters, all evaluations together): {step2_BltA}")
    print(f"   (a)/pass, B < A in clusters summed over the four evaluations: {total_BltA_a}")


if __name__ == "__main__":
    print("python", sys.version.split()[0])
    part1()
    part2(sys.argv[1])
