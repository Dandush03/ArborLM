# ruff: noqa
"""List the current R1 / M1 / C1 lineage ids with the first line of each builder's docstring (for cross-evaluation comparison).
Run from the audited worktree: PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. uv run --locked --offline python <this> > out"""
import importlib

from studies.m0.lineages_r1_clusters_v2 import registered_v2, cluster_of_v2
from studies.m0.core import lineages_of
import studies.m0.lineages_c1_clusters as c1c
import studies.m0.lineages_m1_clusters as m1c


def doc(fn):
    d = (fn.__doc__ or "").strip().splitlines()
    return d[0][:220] if d else "(no docstring)"


print("== R1 registered_v2")
for x in registered_v2():
    print(x.id, "|", cluster_of_v2(x.id), "|", doc(x.build))

print("== C1 current")
allc = {x.id: x for x in lineages_of("C1")}
from studies.m0.lineages_c1_common import load_batch1
from studies.m0.lineages_c1_rev2 import load_rev2
for x in [*load_batch1(), *load_rev2()]:
    allc[x.id] = x
for i in c1c.current_ids():
    x = allc.get(i)
    print(i, "|", c1c.current_cluster_of(i), "|", doc(x.build) if x else "?")

print("== M1 lineages and clusters")
m1 = {x.id: x for x in lineages_of("M1")}
try:
    mm = importlib.import_module("studies.m0.lineages_m1_rev2")
    for x in mm.load_rev2():
        m1[x.id] = x
except Exception as e:
    print("m1 rev2 load failed", e)
try:
    from studies.m0.lineages_m1_common import load_batch1 as m1b
    for x in m1b():
        m1.setdefault(x.id, x)
except Exception as e:
    print("m1 batch load failed", e)
for i in sorted(m1):
    try:
        cl = m1c.cluster_of(i)
    except Exception as e:
        cl = f"? {e}"
    print(i, "|", cl, "|", doc(m1[i].build))
