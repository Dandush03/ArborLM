# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 20: compare the independent recomputation (recompute_labels.py, run as a module-free re-execution)
with analysis.json's per-cell numbers. Stdlib only; read-only. Usage: python3 -I compare_with_analysis.py <run_dir>"""
import json
import runpy
import sys
import io
import contextlib

RUN = sys.argv[1]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ns = runpy.run_path(__file__.replace("compare_with_analysis.py", "recompute_labels.py"), run_name="audit20")
rows = ns["rows"]
a = json.load(open(f"{RUN}/analysis.json"))["lines"]
worst = {}


def cmp(name, mine, theirs):
    d = abs(mine - theirs)
    worst[name] = max(worst.get(name, 0.0), d)


t = a["RETENTION"]["table"]
for k, c in rows.items():
    cmp("G_first(M1)", c["G_first_M1"], t["G_first(M1)"][k])
    cmp("G_second(M-append)", c["G_second_Mapp"], t["G_second(M-append)"][k])
    cmp("F", c["F"], t["F"][k])
    cmp("rho", c["rho"], t["rho"][k])
for i, (k, c) in enumerate(rows.items()):
    cmp("delta_G M-append/D-append", c["dG"], a["AGAINST-DENSE"]["delta_G"][i])
    cmp("delta_G M-seq/D-seq", c["dG_seq"], a["AGAINST-DENSE (M-seq vs D-seq)"]["delta_G"][i])
    cmp("delta_rho M-seq/D-seq", c["drho_seq"], a["AGAINST-DENSE (M-seq vs D-seq)"]["delta_rho"][i])
look = ns["look"]
for rd in a["AGAINST-LOOKUP"]["readings"]:
    v = look[f"{rd['cell']}/{rd['capability']}"]
    assert v[0] == rd["best"], (rd, v)
    cmp("lookup b", v[1], rd["b"])
    cmp("lookup s(M-append)", v[2], rd["s"])
acq = a["ACQUISITION"]["table"]
flags_ok = all(acq["ACQ1"][k] == c["ACQ1"] and acq["ACQ2"][k] == c["ACQ2"] for k, c in rows.items())
print("worst |mine - analysis.json| per quantity:")
for k, v in worst.items():
    print(f"  {k}: {v:.3e}")
print("ACQ1/ACQ2 flags identical:", flags_ok)
print("labels mine vs analysis:")
for name, mine, theirs in [
    ("ACQUISITION", ns["acq"], a["ACQUISITION"]["label"]),
    ("RETENTION", ns["ret"], a["RETENTION"]["label"]),
    ("GENERAL-QUALITY", ns["gen"], a["GENERAL-QUALITY"]["label"]),
    ("AGAINST-DENSE acq", ns["ad_acq"], a["AGAINST-DENSE"]["acquisition"]),
    ("AGAINST-DENSE ret", ns["ad_ret"], a["AGAINST-DENSE"]["retention"]),
    ("M-seq/D-seq acq", ns["seq_acq"], a["AGAINST-DENSE (M-seq vs D-seq)"]["acquisition"]),
    ("M-seq/D-seq ret", ns["seq_ret"], a["AGAINST-DENSE (M-seq vs D-seq)"]["retention"]),
    ("AGAINST-LOOKUP", ns["lookup"], a["AGAINST-LOOKUP"]["label"]),
    ("MODIFICATION", ns["mod"], a["MODIFICATION"]["label"]),
    ("MILESTONE", ns["milestone"], a["MILESTONE"]["label"] + a["MILESTONE"]["line_tail"]),
]:
    print(f"  {name}: {'SAME' if mine == theirs else 'DIFFERENT'} | mine={mine} | analysis={theirs}")
