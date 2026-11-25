# ruff: noqa
# ruff: noqa
"""Auditor's surface-shortcut probes on the 20 pilot fixtures (140 items each).

For each lineage: answer-class balance, and the hit rate of one or more cheap
heuristics a solver could use without executing the intended procedure. A
heuristic counts only when it fires; reported as fired/correct-when-fired and
overall accuracy if a fallback guess (majority class or first option) is used.
Reads question text (and the `structured` form only to locate fields quickly
where noted); never imports generator code.
Usage: python shortcuts.py <fixtures dir>
"""
import collections
import json
import os
import re
import sys

fx = sys.argv[1]
rows = {}
for f in sorted(os.listdir(fx)):
    rows[f[3:-6]] = [json.loads(x) for x in open(os.path.join(fx, f))]


def report(lid, name, fired, correct, n):
    print(f"  {name}: fires {fired}/{n}, correct when fired {correct}/{fired}")


for lid, rs in rows.items():
    n = len(rs)
    dist = collections.Counter(r["answer"] for r in rs)
    k = collections.Counter(r["k"] for r in rs)
    print(f"{lid}: answers {dict(dist.most_common(4)) if len(dist) <= 4 else str(len(dist)) + ' distinct'}; k values {dict(sorted(k.items()))}")
    if lid == "equivalence_classes":
        direct = cor = unm = ucor = 0
        for r in rs:
            q = r["question"]; x, y = r["structured"]["x"], r["structured"]["y"]
            body = q.split(" Is ")[0]
            pats = [f"{x} is the same thing as {y}.", f"{y} is the same thing as {x}.", f"{x} is a different thing from {y}.", f"{y} is a different thing from {x}."]
            hit = [p for p in pats if p in body]
            if hit:
                direct += 1; cor += ("yes" if "same" in hit[0] else "no") == r["answer"]
            if not re.search(rf"\b{x}\b", body) or not re.search(rf"\b{y}\b", body):
                unm += 1; ucor += r["answer"] == "cannot be determined"
        report(lid, "query pair stated verbatim -> that answer", direct, cor, n)
        report(lid, "a queried entity never mentioned -> cbd", unm, ucor, n)
    if lid == "kinship_descendants":
        for ask in ("grandchildren", "descendants"):
            sub = [r for r in rs if r["structured"]["ask"] == ask]
            fired = cor = 0
            for r in sub:
                par = r["structured"]["parent"]
                roots = [p for p in r["structured"]["people"] if p not in par]
                fired += 1; cor += roots[0] == r["answer"]
            report(lid, f"[{ask}] answer = the only person with no recorded parent", fired, cor, len(sub))
    if lid == "boolean_lights":
        fired = cor = 0
        for r in rs:
            st = r["structured"]; a = st["ask"]
            cnt = sum(a in st["switches"][c] for c in st["presses"])
            if cnt == 0:
                fired += 1; cor += ("yes" if st["initial"][a - 1] else "no") == r["answer"]
        report(lid, "asked lamp never toggled -> initial state", fired, cor, n)
    if lid == "categories_default_exceptions":
        fired = cor = 0
        for r in rs:
            st = r["structured"]
            vals = {ok for g, v, ok in st["rules"] if v == st["verb"]}
            if len(vals) == 1:
                fired += 1; cor += ("yes" if vals.pop() else "no") == r["answer"]
        report(lid, "all rules about the asked verb agree -> that value (no priority reasoning)", fired, cor, n)
        fired = cor = 0
        for r in rs:
            st = r["structured"]
            own = [ok for g, v, ok in st["rules"] if v == st["verb"] and g == st["chain"][0]]
            if own:
                fired += 1; cor += ("yes" if own[0] else "no") == r["answer"]
        report(lid, "member's own group has a rule -> that value (one lookup)", fired, cor, n)
    if lid == "containers_queue_line":
        fired = cor = 0
        for r in rs:
            q = r["question"]; ask = r["structured"]["ask"]
            if ask == "back":
                js = re.findall(r"(\w+) joins at the back\.", q)
                if js:
                    fired += 1; cor += js[-1] == r["answer"]
            else:
                js = re.findall(r"(\w+) is let in at the very front\.", q)
                if js:
                    fired += 1; cor += js[-1] == r["answer"]
        report(lid, "back->last joiner / front->last cutter", fired, cor, n)
    if lid == "containers_stack_piles":
        fired = cor = 0
        for r in rs:
            st = r["structured"]; ask = st["ask"]
            if not any(o[0] == "move" and o[2] == ask for o in st["ops"]):
                fired += 1; cor += (st["initial"][ask] or [None])[-1] == r["answer"]
        report(lid, "nothing moved onto asked pile -> its initial top", fired, cor, n)
    if lid == "elimination_bracket":
        fired = cor = 0
        for r in rs:
            pl = r["structured"]["players"]
            if r["structured"]["ask"][0] == "runner_up":
                half = len(pl) // 2
                top = max(pl, key=lambda x: x[1])
                idx = pl.index(top)
                other = pl[half:] if idx < half else pl[:half]
                fired += 1; cor += max(other, key=lambda x: x[1])[0] == r["answer"]
        report(lid, "[runner_up] = top rating in the other half (one max, no simulation)", fired, cor, n)
        fired = cor = 0
        for r in rs:
            pl = r["structured"]["players"]
            if r["structured"]["ask"][0] == "beaten_by":
                fired += 1; cor += max(pl, key=lambda x: x[1])[0] == r["answer"]
        report(lid, "[beaten_by] = champion (top rating)", fired, cor, n)
    if lid == "temporal_critical_path":
        fired = cor = 0
        for r in rs:
            jobs = r["structured"]["jobs"]
            fired += 1; cor += max(jobs, key=lambda j: j[1])[0] == r["answer"]
        report(lid, "longest single job", fired, cor, n)
    if lid == "spatial_grid_walk":
        fired = cor = 0
        for r in rs:
            g = r["structured"]["grid"]; s = r["structured"]["start"]
            fired += 1; cor += g[s[0]][s[1]] == r["answer"]
        report(lid, "answer = start cell", fired, cor, n)
    if lid == "graph_shortest_route":
        fired = cor = 0
        for r in rs:
            s = r["structured"]["start"]
            nb = [(w, b if a == s else a) for a, b, w in r["structured"]["roads"] if s in (a, b)]
            fired += 1; cor += min(nb)[1] == r["answer"]
        report(lid, "greedy: nearest neighbour of start", fired, cor, n)
        fired = cor = 0
        for r in rs:
            s, t = r["structured"]["start"], r["structured"]["end"]
            direct = any({a, b} == {s, t} for a, b, w in r["structured"]["roads"])
            if direct:
                fired += 1
        print(f"  start-end directly connected (answer is then never the end town): {fired}/{n}")
    if lid == "tracking_accounts":
        fired = cor = 0
        for r in rs:
            st = r["structured"]["start"]
            f = max if r["structured"]["ask"] == "most" else min
            fired += 1; cor += f(st, key=lambda p: st[p]) == r["answer"]
        report(lid, "same person as at the start", fired, cor, n)
    if lid == "conditional_threshold_rule":
        fired = cor = 0
        for r in rs:
            st = r["structured"]
            if any(st["votes"][v] == "no" for v in st["vetoes"]):
                fired += 1; cor += r["answer"] == "no"
        report(lid, "a veto holder voted no -> no (no arithmetic)", fired, cor, n)
    if lid == "spatial_relative_directions":
        fired = cor = 0
        for r in rs:
            facts = r["structured"]["facts"]; anc = r["structured"]["anchor"]
            # pick the place mentioned in the fact with the largest k not touching anchor
            fired += 1
            best = max(facts, key=lambda f: f[2])
            cor += r["answer"] in (best[0], best[3])
        report(lid, "answer is an endpoint of the largest single offset", fired, cor, n)
    if lid == "order_tournament_wins":
        pass
    if lid == "elimination_josephus":
        pass
