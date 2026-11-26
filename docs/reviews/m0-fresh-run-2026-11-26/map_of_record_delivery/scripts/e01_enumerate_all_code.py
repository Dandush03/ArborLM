"""Enumerate every Lineage object defined anywhere in studies/m0/lineages_*.py (all rounds), standard library only.
Imports each module, then collects Lineage instances from every module-level list/dict and core.REGISTRY.
Builds no item, runs no rule. Output: one line per (id, module-list) pair, sorted."""
import importlib, pkgutil, sys, json
sys.path.insert(0, '.')
import studies.m0 as pkg
from studies.m0 import core
mods = sorted(m.name for m in pkgutil.iter_modules(pkg.__path__) if m.name.startswith('lineages_'))
seen = {}
errors = []
for name in mods:
    try:
        importlib.import_module(f'studies.m0.{name}')
    except Exception as e:  # record, do not hide
        errors.append((name, repr(e)))
for name in mods:
    m = sys.modules.get(f'studies.m0.{name}')
    if m is None: continue
    for attr, val in vars(m).items():
        items = []
        if isinstance(val, list): items = val
        elif isinstance(val, dict): items = list(val.values())
        for x in items:
            if isinstance(x, core.Lineage):
                origin = f'{x.build.__module__}'
                seen.setdefault(x.id, set()).add(f'{origin}:{x.build.__name__}:{x.build.__code__.co_firstlineno}|{x.family}')
for ev, lst in core.REGISTRY.items():
    for x in lst:
        seen.setdefault(x.id, set()).add(f'{x.build.__module__}:{x.build.__name__}:{x.build.__code__.co_firstlineno}|{x.family}')
print('modules', len(mods)); print('import_errors', json.dumps(errors))
print('ids', len(seen))
for k in sorted(seen):
    print(k, ' ; '.join(sorted(seen[k])))
