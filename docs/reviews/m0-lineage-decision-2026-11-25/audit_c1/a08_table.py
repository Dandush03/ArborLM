# ruff: noqa
"""Print the shortcut table from a07_shortcuts_<sub>.json: maxima over core levels 1-5 (and the level where reached)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sub = sys.argv[1]
res = json.load(open(os.path.join(HERE, f"a07_shortcuts_{sub}.json")))
summ = json.load(open(os.path.join(HERE, sub, "summary.json")))
CORE = ["1", "2", "3", "4", "5"]
ALL = [str(i) for i in range(7)]


def mx(lid, key, levels=CORE):
    vals = [(res[lid][lv].get(key, 0) or 0, lv) for lv in levels]
    return max(vals)


print("| lineage | n/level | const (max L1-5) | O1 shape-const CV | O5 best literal rule CV | O7 best rule per shape CV | author best single rule (A.*) | oracle any literal | oracle stat | key '0' rate | best R.* rule | min distinct keys |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
for lid in summ["old"] + summ["new"]:
    r = res[lid]
    n = r["1"]["n"]
    c = mx(lid, "const_overall")
    o1 = mx(lid, "O1.shape_const_cv")
    o5 = mx(lid, "O5.best_literal_rule_cv")
    o7 = mx(lid, "O7.best_rule_per_shape_cv")
    akeys = [k for k in r["1"] if k.startswith("A.") and not k.startswith("A.oracle")]
    ab = max((mx(lid, k)[0], k, mx(lid, k)[1]) for k in akeys)
    ol = mx(lid, "A.oracle_any_literal")
    os_ = mx(lid, "A.oracle_list_or_string_stat")
    z = mx(lid, "O6.key_is_0")
    rkeys = sorted({k for lv in ALL for k in r[lv] if k.startswith("R.")})
    rb = max(((mx(lid, k)[0], k, mx(lid, k)[1]) for k in rkeys), default=(0, "-", "-"))
    dk = min(r[lv]["distinct_keys"] for lv in CORE)
    tag = "new" if lid in summ["new"] else "old"
    print(f"| {lid} ({tag}) | {n} | {c[0]:.3f} (L{c[1]}) | {o1[0]:.3f} (L{o1[1]}) | {o5[0]:.3f} (L{o5[1]}) | {o7[0]:.3f} (L{o7[1]}) | {ab[1][2:]} {ab[0]:.3f} (L{ab[2]}) | {ol[0]:.3f} | {os_[0]:.3f} | {z[0]:.3f} | {rb[1][2:]} {rb[0]:.3f} (L{rb[2]}) | {dk} |")

if "--detail" in sys.argv:
    for lid in summ["old"] + summ["new"]:
        print("\n##", lid)
        for lv in ALL:
            row = res[lid][lv]
            keep = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if (isinstance(v, float) and v >= 0.15) or k in ("n", "distinct_keys", "const_key", "n_shapes", "O5.chosen", "O7.chosen")}
            print(" L" + lv, keep)
