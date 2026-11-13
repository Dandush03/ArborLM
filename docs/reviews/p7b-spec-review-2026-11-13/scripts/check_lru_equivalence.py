"""Check that the LRU in calib_coaccess.py equals the LRU of the P7-A results audit (recompute_p7a.py),
which matched the P7-A records exactly on all 81 checkpoints. Calibration traces only.
Usage (repo root): .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/check_lru_equivalence.py"""
import importlib.util, sys
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
new = load("cc", "docs/reviews/p7b-spec-review-2026-11-13/scripts/calib_coaccess.py")
old = load("rp", "docs/reviews/p7a-results-audit-2026-11-13/recompute_p7a.py")
n = 0
for lb, kind, idx in new.registered()[:9]:
    rec = __import__("json").load(open(f"{new.TREC}/{lb}.json"))
    sel = new.read_i16(f"{new.RAW}/{rec['trace_dir']}/calib_selected.int16.bin")
    f = new.counts_of(sel)
    A = new.affinity(sel, 8, range(512))
    for R, C in ((2, 32), (8, 8), (1, 16)):
        for name, pages in (("FREQ", new.order_to_pages(new.layout_freq(f), R)), ("COAX", new.l_coax(R, f, A))):
            pos = new.pages_to_pos(pages)
            pq = new.query_pages(sel, pos, R, range(new.Q))
            a = new.lru(pq, C, new.Q // 2)
            b = old.lru(pq, C)
            b = (b["misses_warm"] - b["first_touch_warm"]) / 16384
            for desc in (False, True):
                a = new.lru(pq, C, new.Q // 2, descending=desc)
                b = old.lru(pq, C, descending=desc)
                b = (b["misses_warm"] - b["first_touch_warm"]) / 16384
                assert a == b, (lb, R, C, name, desc, a, b)
                n += 1
print("LRU equivalence: OK on", n, "configurations (9 checkpoints, calibration stream)")
