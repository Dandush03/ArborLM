"""For every lineage id (all rounds), print each defining builder (module:function:line, body length) and its docstring, whitespace-collapsed.
Reading aid only; builds no item. Usage: e03_docstrings.py EVAL"""
import importlib, pkgutil, sys, inspect
sys.path.insert(0, '.')
import studies.m0 as pkg
from studies.m0 import core
ev = sys.argv[1]
mods = sorted(m.name for m in pkgutil.iter_modules(pkg.__path__) if m.name.startswith('lineages_'))
for name in mods: importlib.import_module(f'studies.m0.{name}')
seen = {}
def add(x):
    f = x.build
    key = (f.__module__, f.__name__, f.__code__.co_firstlineno)
    seen.setdefault(x.id, {})[key] = x
for name in mods:
    m = sys.modules[f'studies.m0.{name}']
    for attr, val in vars(m).items():
        items = val if isinstance(val, list) else (list(val.values()) if isinstance(val, dict) else [])
        for x in items:
            if isinstance(x, core.Lineage): add(x)
for e, lst in core.REGISTRY.items():
    for x in lst: add(x)
for lid in sorted(seen):
    if not lid.startswith(ev + '.'): continue
    for key, x in sorted(seen[lid].items()):
        src = inspect.getsource(x.build)
        doc = ' '.join((inspect.getdoc(x.build) or '').split())
        print(f'### {lid} [{key[0].split(".")[-1]}:{key[2]}, {len(src.splitlines())} lines, family={x.family}]')
        print('   ', doc[:900])
