# ruff: noqa
"""Final R1 audit: temporal_weekday_shift_r6, from the text only: distribution of the number of links on the (unique if a tree) path between the
anchored event and the asked event, number of events and links (tree check), per level. usage: python weekday_hops.py <n> <B>"""
import os, re, sys
from collections import Counter, deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen
n, B = int(sys.argv[1]), int(sys.argv[2])
lin = fgen.lineages()["R1.temporal_weekday_shift_r6"]
for lv in range(7):
    hops, tree, ev = Counter(), Counter(), Counter()
    for b in fgen.items(lin, lv, n, B):
        q = b.question
        links = [m.groups() for m in (re.fullmatch(r"The (.+?) took place \d+ days? (?:before|after) the (.+?)\.", x) for x in re.split(r"(?<=[.?])\s+", q)) if m]  # FIX: per sentence (a findall over the whole text let the first name span the anchor sentence; my slip)
        adj = {}
        for a, c in links:
            adj.setdefault(a, set()).add(c); adj.setdefault(c, set()).add(a)
        anc = re.search(r"The (.+?) took place on a \w+day\.", q).group(1)
        ask = re.search(r"did the (.+?) take place\?", q).group(1)
        d = {anc: 0}; dq = deque([anc])
        while dq:
            u = dq.popleft()
            for v in adj.get(u, ()):
                if v not in d:
                    d[v] = d[u] + 1; dq.append(v)
        hops[d.get(ask)] += 1
        tree[len(links) == len(adj) - 1] += 1
        ev[len(adj)] += 1
    print(f"L{lv} hops anchor->asked {sorted(hops.items())}  is_tree {dict(tree)}  events {sorted(ev.items())}")
