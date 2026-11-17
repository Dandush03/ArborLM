"""Re-check auditor C: bootstrap intervals (ruling: 220906 drawn in the analysis stage only, a fresh generator per printed
interval in a fixed order; descriptive; identical on a re-run). Test-mode stand-in seed. Seeds 229501.. for the data.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval. Usage: <python> check_bootstrap.py <pin>"""

import copy
import random
import sys
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

import torch  # noqa: E402

from studies.p10s2 import analysis, core  # noqa: E402

import check_edges_v2_lib as E  # noqa: E402

rng = random.Random(229501)
st = E.build()
for rep in st["replicates"]:
    for c in rep["cells"].values():
        for sn in c["scores"].values():
            for node in sn.get("panels", {}).values():
                node["items"] = [min(1.0, max(0.0, float(node["mean"]) + rng.uniform(-0.2, 0.2))) for _ in range(30)]
for kind in ("student",):
    for p, v in st["baseline"]["student"].items():
        v["panel"]["items"] = [rng.random() for _ in range(30)]

core.reset_seed_record()
a = analysis.analyze(copy.deepcopy(st), bootstrap_mode="test", bootstrap_resamples=2000)
uses1 = list(core.seed_record())
core.reset_seed_record()
b = analysis.analyze(copy.deepcopy(st), bootstrap_mode="test", bootstrap_resamples=2000)
uses2 = list(core.seed_record())
core.reset_seed_record()
c = analysis.analyze(copy.deepcopy(st))
uses3 = list(core.seed_record())
print("intervals printed:", len(a["intervals"]), "| with values:", sum(x["lo"] is not None for x in a["intervals"]))
print("identical on a re-run:", a["intervals"] == b["intervals"])
print("seed uses in run 1:", len(uses1), "distinct seeds:", sorted({u.seed for u in uses1}), "== test stand-in of 220906:", {u.seed for u in uses1} == {core.partition_seeds("test")["bootstrap"]})
print("one fresh generator per interval WITH items (uses == intervals with values):", len(uses1) == sum(x["lo"] is not None for x in a["intervals"]))
print("purposes in the fixed order (first 4):", [u.purpose for u in uses1[:4]])
print("no seed drawn without bootstrap_mode:", len(uses3) == 0, "| verdicts identical with and without intervals:", analysis.verdicts_of_outcome(a) == analysis.verdicts_of_outcome(c))
# fresh generator per interval: two targets with the same items get the same interval; my own percentile bootstrap agrees
x = [i / 29 for i in range(30)]
seed = core.partition_seeds("test")["bootstrap"]
from studies.p10s2.text import bootstrap_interval  # noqa: E402

core.reset_seed_record()
i1 = bootstrap_interval(x, core.bootstrap_generator("test", "one"), 2000)
i2 = bootstrap_interval(x, core.bootstrap_generator("test", "two"), 2000)
gm = torch.Generator().manual_seed(seed)
xs = torch.tensor(x, dtype=torch.float64)
means = sorted(xs[torch.randint(0, 30, (2000, 30), generator=gm)].mean(dim=1).tolist())
print("same items, two names -> same interval:", i1 == i2, i1, "| my percentile bootstrap (one 2000x30 draw):", (means[int(0.025 * 1999)], means[int(0.975 * 1999)]))
core.reset_seed_record()
try:
    core.bootstrap_generator("registered-data", "x")
    print("registered-data mode may draw 220906: True (DEFECT)")
except Exception as e:  # noqa: BLE001
    print("registered-data mode refuses 220906:", type(e).__name__)
try:
    core.bootstrap_generator("registered-run", "x")
    print("registered-run mode may draw 220906: True (DEFECT)")
except Exception as e:  # noqa: BLE001
    print("registered-run mode refuses 220906:", type(e).__name__)
print("registered-analysis holds exactly:", core.partition_seeds("registered-analysis"))
