# ruff: noqa
"""Check the numbers and verdicts printed in REPORT_SUPPLEMENT.md against recompute.py's independent output (capacity tables, saturation tables,
dense counts, labels). Usage: python3 -I report_vs_recompute.py <REPORT_SUPPLEMENT.md> <recompute.json>"""
import json, re, sys
rep = open(sys.argv[1], encoding="utf-8").read().splitlines()
m = json.load(open(sys.argv[2]))
arm = None; sec = None; n = bad = 0
for ln in rep:
    if ln.startswith("## "): sec = ln[3:]
    h = re.match(r"### (F-OQ-IVF|F-OQ|T-OQ|H8):", ln)
    if h: arm = h.group(1)
    cells = [c.strip() for c in ln.strip("|").split("|")] if ln.startswith("| ") else None
    if sec == "C-CAPACITY" and cells and len(cells) == 9 and cells[1].isdigit():
        st, r, v, a, b = cells[0], int(cells[1]), cells[2], float(cells[3]), float(cells[4])
        rr = m["capacity"]["arms"][arm]["steps_detail"][st]["replicates"][r - 1]
        ok = rr["verdict"] == v and abs(rr["detail"]["A"]["d_mu"] - a) < 6e-4 and abs(rr["detail"]["B"]["d_mu"] - b) < 6e-4
        n += 1; bad += not ok
        if not ok: print("CAP DIFF", arm, st, r, v, a, b, rr["verdict"], rr["detail"]["A"]["d_mu"], rr["detail"]["B"]["d_mu"])
    if sec == "C-SATURATION" and cells and len(cells) == 10 and cells[1].isdigit():
        pair, r, p, v, rho = cells[0].replace("1K", "1K"), int(cells[1]), cells[2], cells[3], float(cells[4])
        rr = m["saturation"]["arms"][arm]["pairs"][pair]["replicates"][r - 1]
        ok = rr["verdict"] == v and abs(rr["rho"][p] - rho) < 6e-4
        n += 1; bad += not ok
        if not ok: print("SAT DIFF", arm, pair, r, p, v, rho, rr["verdict"], rr["rho"][p])
    d = re.match(r"- dense, larger cell (\S+): (.+?)(?: \[.*?\])?; replicates holding a dense lead.*?: (MU: .*)$", ln)
    if d:
        cell, lab, counts = d.group(1), d.group(2), dict((k.strip(), int(v)) for k, v in (x.split(":") for x in d.group(3).split(",")))
        mm = m["capacity"]["arms"][arm]["dense_cells"][cell]
        ok = mm["label"] == lab and all(mm["counts"][k] == v for k, v in counts.items())
        n += 1; bad += not ok
        if not ok: print("DENSE DIFF", arm, cell, lab, counts, mm["label"], mm["counts"])
    s = re.match(r"- dense at saturation, loaded cell (\S+): (DENSE HOLDS MORE AT SATURATION|STORE HOLDS MORE AT SATURATION|SAME AT SATURATION)", ln)
    if s:
        ok = m["capacity"]["arms"][arm]["dense_at_saturation"][s.group(1)]["label"] == s.group(2)
        n += 1; bad += not ok
print(f"report rows/labels checked: {n}; differences: {bad}")
