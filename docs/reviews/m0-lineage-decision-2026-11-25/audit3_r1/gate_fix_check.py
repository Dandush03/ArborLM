# ruff: noqa
"""Audit 3 (R1): do the gate-fix tests in tests/test_m0_r1_rev4_gates.py fail on the gate as it stood at 9e32b317?

Runs every test function of that file twice: once with the current studies.m0.lineages_r1_shortcuts, once with the
module text of 9e32b317 (extracted with `git show 9e32b317:studies/m0/lineages_r1_shortcuts.py` into the scratch dir)
substituted in sys.modules. Prints PASS/FAIL per test and version. Modifies no file.

Run from the implementation worktree root:
  PYTHONHASHSEED=0 uv run --locked python <this file> <path to old_shortcuts_9e32b317.py>
"""
import importlib, importlib.util, sys

sys.path.insert(0, ".")


def run(label, mod):
    sys.modules["studies.m0.lineages_r1_shortcuts"] = mod
    import studies.m0 as pkg
    setattr(pkg, "lineages_r1_shortcuts", mod)
    spec = importlib.util.spec_from_file_location("t_gates_" + label, "tests/test_m0_r1_rev4_gates.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    assert t.sc is mod, "test module did not bind the substituted gate"
    for name in sorted(n for n in dir(t) if n.startswith("test_")):
        try:
            getattr(t, name)()
            print(f"{label:8s} PASS {name}")
        except Exception as e:
            print(f"{label:8s} FAIL {name}: {type(e).__name__}: {str(e)[:160]}")


new = importlib.import_module("studies.m0.lineages_r1_shortcuts")
spec = importlib.util.spec_from_file_location("old_shortcuts", sys.argv[1])
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
run("current", new)
run("9e32b317", old)
