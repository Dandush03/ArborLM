"""Render ONE item at level 2 for each of a handful of lineage ids, for reading only (no rate, no rule).
Seed: random.Random(20261126 + index of the id in the list below). Builders are retried on core.Retry up to 50 times with the same stream."""
import importlib, pkgutil, sys, random
sys.path.insert(0, '.')
import studies.m0 as pkg
from studies.m0 import core
IDS = ["C1.fast_power_f4", "C1.fast_power", "C1.counter_list_f3", "C1.counter_list", "C1.bfs_queue", "C1.union_find_links_f3",
       "R1.containers_queue_line_r5", "R2.list_ops", "C1.grid_path_table", "M1.mode_tally_r3", "C1.loop_sum", "R1.equivalence_classes_r5"]
mods = sorted(m.name for m in pkgutil.iter_modules(pkg.__path__) if m.name.startswith('lineages_'))
for name in mods: importlib.import_module(f'studies.m0.{name}')
byid = {}
for name in mods:
    for val in vars(sys.modules[f'studies.m0.{name}']).values():
        items = val if isinstance(val, list) else (list(val.values()) if isinstance(val, dict) else [])
        for x in items:
            if isinstance(x, core.Lineage): byid.setdefault(x.id, x)
for lst in core.REGISTRY.values():
    for x in lst: byid.setdefault(x.id, x)
for i, lid in enumerate(IDS):
    r = random.Random(20261126 + i)
    for _ in range(50):
        try:
            b = byid[lid].build(2, r); break
        except core.Retry:
            continue
    print(f"===== {lid} (module {byid[lid].build.__module__})\n{b.question}\nANSWER: {b.answer}\n")
