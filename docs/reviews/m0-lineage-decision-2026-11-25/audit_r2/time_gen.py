# ruff: noqa
import time
from studies.m0.core import build_item, stream, lineages_of
from studies.m0.lineages_r2_common import load_batch1
for lin in [*lineages_of("R2"), *load_batch1()]:
    t = time.time()
    for lv in (0, 3, 6):
        r = stream(1, "t", lin.id, str(lv))
        for i in range(200):
            build_item(lin, lv, r, "A", "x")
    print(f"{lin.id} {time.time()-t:.2f}s per 600")
