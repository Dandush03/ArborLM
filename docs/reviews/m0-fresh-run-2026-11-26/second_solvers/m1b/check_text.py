"""Independent text parse: re-derive the inputs from the question text and compare with `structured`;
also report data-range facts relevant to ambiguity (dims of 1, region non-negativity, etc.)."""
import json, re
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1"
def items(l):
    for line in open(f"{F}/M1.{l}/fixtures.jsonl"):
        yield json.loads(line)
def ints(s): return [int(x) for x in re.findall(r"-?\d+", s)]
mism = {}
def bad(l, d, why):
    mism.setdefault(l, []).append((d["level"], d["index"], why))

for d in items("gcd_lcm_r4"):
    q, s = d["question"], d["structured"]
    ask = "lcm" if "flash" in q else "gcd" if "ribbons" in q else None
    if "flash" in q:
        body = q[q.index("lights flash"):]
        vals = [int(x) for x in re.findall(r"every (\d+) seconds", body)]
        cnt = int(re.search(r"(\d+) lights flash", q).group(1))
    else:
        vals = [int(x) for x in re.split(r", | and ", re.search(r"lengths ([\d, and]+) centimetres", q).group(1))]
        cnt = int(re.search(r"has (\d+) ribbons", q).group(1))
    if ask != s["ask"] or vals != s["values"] or cnt != len(vals): bad("gcd_lcm_r4", d, (ask, vals, cnt))

for d in items("grid_perimeter_r3"):
    q, s = d["question"], d["structured"]
    rows = []
    for m in re.finditer(r"Row (\d+) \(counting from the top\): ([^.]*)\.", q):
        if m.group(2) == "no squares": rows.append([]); continue
        runs = []
        for part in m.group(2).split(", "):
            mm = re.fullmatch(r"columns (\d+) to (\d+)", part)
            if mm: runs.append([int(mm.group(1)), int(mm.group(2))])
            else:
                mm = re.fullmatch(r"column (\d+)", part); runs.append([int(mm.group(1))] * 2)
        rows.append(runs)
    if rows != s["rows"]: bad("grid_perimeter_r3", d, rows)

for d in items("inclusion_exclusion_r3"):
    q, s = d["question"], d["structured"]
    ask = ("none" if "do none" in q else "any" if "at least one" in q else "exactly_one" if "exactly one" in q
           else "exactly_two" if "exactly two" in q else None)
    n = ints(q)
    if s["triple"] is None:
        exp = [s["total"], s["sizes"][0], s["sizes"][1], s["pairs"][0], s["total"]]
    else:
        exp = [s["total"]] + s["sizes"] + s["pairs"] + [s["triple"], s["total"]]
    if ask != s["ask"] or n != exp: bad("inclusion_exclusion_r3", d, (ask, n))
    # region sanity
    if s["triple"] is None:
        a, b = s["sizes"]; ab = s["pairs"][0]; regs = [a - ab, b - ab, ab, s["total"] - a - b + ab]
    else:
        A, B, C = s["sizes"]; ab, ac, bc = s["pairs"]; t = s["triple"]
        regs = [t, ab - t, ac - t, bc - t, A - ab - ac + t, B - ab - bc + t, C - ac - bc + t,
                s["total"] - (A + B + C - ab - ac - bc + t)]
    if min(regs) < 0: bad("inclusion_exclusion_r3", d, ("negative region", regs))

for d in items("last_digit_power_r3"):
    q, s = d["question"], d["structured"]
    if "the sum of" in q:
        op = "sum"; terms = [[int(b), int(e)] for e, b in re.findall(r"product of (\d+) factors, each equal to (\d+)", q)]
    elif "all the following factors" in q:
        op = "product"; terms = [[int(b), int(e)] for e, b in re.findall(r"(\d+) factors equal to (\d+)", q)]
    else:
        op = "single"; terms = [[int(b), int(e)] for e, b in re.findall(r"product of (\d+) factors, each equal to (\d+)", q)]
    m = re.search(r"divided by (\d+) \(a whole number from 0 to (\d+)\)", q)
    mod = int(m.group(1))
    ok = terms == s["terms"] and mod == s["modulus"] and int(m.group(2)) == mod - 1
    ok = ok and (s["op"] == op or (op == "single" and len(terms) == 1))
    if not ok: bad("last_digit_power_r3", d, (op, terms, mod, s))
    if op == "single" and s["op"] != "sum": bad("last_digit_power_r3", d, ("single op", s["op"]))

for d in items("linear_equation_r3"):
    q, s = d["question"], d["structured"]
    parts = re.findall(r"multiplying it by (\d+) and then (adding|subtracting) (\d+)", q, re.I)
    k, m = int(parts[0][0]), int(parts[0][2]) * (1 if parts[0][1] == "adding" else -1)
    if len(parts) == 2:
        j, n = int(parts[1][0]), int(parts[1][2]) * (1 if parts[1][1] == "adding" else -1)
    else:
        j, n = 0, int(re.search(r"gives (-?\d+)\.", q).group(1))
    if (k, m, j, n) != (s["k"], s["m"], s["j"], s["n"]): bad("linear_equation_r3", d, (k, m, j, n))
    if len(parts) == 2 and j == 0: bad("linear_equation_r3", d, "two-sided with j=0")
    if s["m"] == 0 or (s["j"] and s["n"] == 0): bad("linear_equation_r3", d, "zero constant wording")

for d in items("median_list_r3"):
    q, s = d["question"], d["structured"]
    vals = [int(x) for x in re.split(r", | and ", re.search(r"The values are ([\d, and]+)\. ", q).group(1))]
    if vals != s["values"]: bad("median_list_r3", d, vals)

for d in items("mixture_r4"):
    q, s = d["question"], d["structured"]
    m = re.search(r"mixes (\d+) kilograms of nuts costing (\d+) dollars per kilogram with (\d+) kilograms of raisins costing (\d+) dollars per kilogram", q)
    x, a, y, b = map(int, m.groups())
    p = re.search(r"flat packing cost of (\d+) dollars? per kilogram", q)
    p = int(p.group(1)) if p else 0
    if (x, a, y, b, p) != (s["x"], s["a"], s["y"], s["b"], s["packing"]): bad("mixture_r4", d, (x, a, y, b, p))

for d in items("painted_cube_r3"):
    q, s = d["question"], d["structured"]
    m = re.search(r"box (\d+) cubes long, (\d+) cubes wide and (\d+) cubes high", q)
    dims = list(map(int, m.groups()))
    bu = "except the bottom face" in q
    f = int(re.search(r"exactly (\d+) painted face", q).group(1))
    if dims != s["dims"] or bu != s["bottom_unpainted"] or f != s["faces"]: bad("painted_cube_r3", d, (dims, bu, f))
    if min(dims) < 3: bad("painted_cube_r3", d, ("small dim", dims))

for d in items("percent_change_r3"):
    q, s = d["question"], d["structured"]
    price = int(re.search(r"costs (\d+) dollars", q).group(1))
    steps = [["up" if w == "rises" else "down", int(p)] for w, p in re.findall(r"(rises|falls) by (\d+) percent", q)]
    if price != s["price"] or steps != s["steps"]: bad("percent_change_r3", d, (price, steps))

for d in items("pipes_work_r3"):
    q, s = d["question"], d["structured"]
    a = int(re.search(r"One pipe adds (\d+) litres", q).group(1))
    b = int(re.search(r"second pipe adds (\d+) litres", q).group(1))
    dr = re.search(r"drain removes (\d+) litres", q); dr = int(dr.group(1)) if dr else 0
    v = int(re.search(r"hold (\d+) litres", q).group(1))
    if (a, b, dr, v) != (s["a"], s["b"], s["drain"], s["volume"]): bad("pipes_work_r3", d, (a, b, dr, v))
    r = a + b - dr
    if r <= 0 or v % r: bad("pipes_work_r3", d, ("rate/divisibility", r, v))

for l in ["gcd_lcm_r4","grid_perimeter_r3","inclusion_exclusion_r3","last_digit_power_r3","linear_equation_r3",
          "median_list_r3","mixture_r4","painted_cube_r3","percent_change_r3","pipes_work_r3"]:
    print(l, "flags:", len(mism.get(l, [])))
    for x in mism.get(l, [])[:20]: print("   ", x)
