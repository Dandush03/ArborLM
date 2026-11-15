"""Auditor: build a perturbed copy of the dry-run eval/sim records that exercises every class."""
import hashlib, json, math, shutil, sys
from pathlib import Path
src_e, src_s, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
variant = sys.argv[4] if len(sys.argv) > 4 else "main"
E, Sd = dst / "eval", dst / "sim"
for p in (E, Sd):
    if p.exists(): shutil.rmtree(p)
(E / "cells").mkdir(parents=True); (Sd / "cells").mkdir(parents=True)
shutil.copy(src_e / "manifest.json", E / "manifest.json"); shutil.copy(src_s / "manifest.json", Sd / "manifest.json")
# factor on warm capacity misses of the ACTUAL stream, per case and panel; null factor separately
act = {"C06": (0.5, 0.5), "C07": (0.6, 0.6), "C09": (0.4, 0.4), "C05": (0.5, 0.5), "C08": (1.4, 1.4), "C10": (0.5, 1.0)}
nul = {"C05": (0.5, 0.5)}
neff = {"C04": 0.4, "C07": 0.7}
for cdir in sorted((src_e / "cells").iterdir()):
    lab = cdir.name; case = lab.split("-")[-1]
    ev = json.loads((cdir / "eval.json").read_text())
    for p in ("A", "B"):
        en = ev["nll"]["step512"]["enabled"][p]
        ev["nll"]["step512"]["disabled"][p] = en + 0.02
        ev["nll"]["step512"]["values_permuted"][p] = en + 0.01
        if case in neff:
            u = ev["traces"][p]["utilization"]
            u["n_eff"] *= neff[case]; u["entropy_nats"] = math.log(u["n_eff"])
    if variant == "negbase" and case in ("C01",):
        for p in ("A", "B"):
            en = ev["nll"]["step512"]["enabled"][p]
            ev["nll"]["step512"]["disabled"][p] = en - 0.002   # baseline gain negative
    if variant == "negbase" and case in ("C06",):
        for p in ("A", "B"):
            en = ev["nll"]["step512"]["enabled"][p]
            ev["nll"]["step512"]["disabled"][p] = en - 0.004   # case gain more negative -> retention 2.0
    od = E / "cells" / lab; od.mkdir()
    (od / "eval.json").write_text(json.dumps(ev))
    sm = json.loads((src_s / "cells" / lab / "sim.json").read_text())
    sm["eval_json_sha256"] = hashlib.sha256((od / "eval.json").read_bytes()).hexdigest()
    for i, p in enumerate(("A", "B")):
        for stream, groups in sm["panels"][p]["streams"].items():
            f = act.get(case, (1, 1))[i] if stream == "actual" else (nul.get(case, (1, 1))[i] if stream.startswith("null") else 1)
            if f == 1: continue
            for g in groups.values():
                for ties in g["by_c"].values():
                    for cnt in ties.values():
                        cap = cnt["misses_warm"] - cnt["first_touch_warm"]
                        cnt["misses_warm"] = cnt["first_touch_warm"] + int(round(cap * f))
    sd = Sd / "cells" / lab; sd.mkdir()
    (sd / "sim.json").write_text(json.dumps(sm))
print("ok", dst)
