"""Re-check B, R8: the cost of one registered bootstrap interval (10,000 resamples) at the registered item counts, test seeds only (mode "test").
Usage: PYTHONPATH=<pin>/src python r8_bootstrap_cost.py <pin>"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import torch
from studies.p10s2 import analysis, core
g0 = torch.Generator().manual_seed(229777)
out = {}
for n in (12, 500, 1000):
    items = torch.rand(n, generator=g0).tolist()
    t0 = time.perf_counter()
    k = 5
    for i in range(k):
        analysis.bootstrap_interval(items, core.bootstrap_generator("test", f"r8 {n} {i}"), 10000)
    out[n] = (time.perf_counter() - t0) / k
out["threads"] = torch.get_num_threads()
print(json.dumps(out))
