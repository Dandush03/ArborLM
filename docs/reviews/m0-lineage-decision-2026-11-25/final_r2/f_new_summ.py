# ruff: noqa
"""Final R2 audit: summary of the NEW rules (f_rules_new_4000.json, my fresh seeds only, 4,000 test items per level).
Effect as audit 4: open -> k/n ('[cond]' rules k/napp), yes/no -> |k/napp - 0.5|. Class = the tag in the rule name.
Usage: python3 -I f_new_summ.py f_rules_new_4000.json OUT.json"""
import json, math, re, sys
d = json.load(open(sys.argv[1]))["lineages"]
out = {}
for lid, lv_rows in sorted(d.items()):
    best = {}
    for lv, rows in lv_rows.items():
        for sh, e in rows.items():
            for hn, v in e["rules"].items():
                c = re.search(r"\((cue|partial|P|artifact)\)", hn).group(1)
                if e["answer_type"] == "yn":
                    eff = abs(v["k"] / v["napp"] - 0.5) if v["napp"] else 0
                    m = v["napp"]
                elif "[cond]" in hn:
                    eff = v["k"] / v["napp"] if v["napp"] else 0
                    m = v["napp"]
                else:
                    eff = v["k"] / e["n"]; m = e["n"]
                se = math.sqrt(eff * (1 - eff) / m) if m and e["answer_type"] != "yn" else 0
                b = best.setdefault(c, {})
                key = hn
                if key not in b:
                    b[key] = [0.0] * 7
                b[key][int(lv)] = max(b[key][int(lv)], round(eff, 4))
    out[lid] = best
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
for lid, best in out.items():
    for c, rules in best.items():
        for hn, vals in rules.items():
            if max(vals) > 0.10:
                flag = "ABOVE 0.15" if max(vals) > 0.15 else ""
                print(f"{lid[3:]:28s} {c:8s} L0..L6 " + " ".join(f"{x:.3f}" for x in vals) + f"  {flag}  {hn[6:90]}")
