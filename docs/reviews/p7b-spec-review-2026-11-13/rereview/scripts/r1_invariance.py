"""Calibration-only: is 'at R = 1 every layout gives identical results' (ADR-0014 section 4 and 10)
true under the page-number eviction tie rule? L-ID vs L-FREQ vs L-COAX at R = 1, all C, both ties."""
import json, sys
sys.dont_write_bytecode = True
HERE = __file__.rsplit("/", 1)[0]
sys.path.insert(0, HERE); sys.path.insert(0, HERE.rsplit("/rereview", 1)[0] + "/scripts")
import calib_coaccess as old  # noqa: E402
import rev3_layouts as L  # noqa: E402
for label in ("b101-o301-flat-s501", "b101-o301-fixed_tree-s501", "b101-o301-learned_tree-s501"):
    rec = json.load(open(f"{old.TREC}/{label}.json"))
    cs = rec["files"]["calibration"]["selected"]
    path = f"{old.RAW}/{rec['trace_dir']}/{cs['file']}"
    assert "eval_" not in path and old.sha256(path) == cs["sha256"]
    sel = old.read_i16(path)
    f = L.counts_of(sel)
    lays = {"ID": [[s] for s in range(4096)], "FREQ": [[s] for s in L.layout_freq(f)]}
    for C in (8, 16, 32, 64, 128):
        row = []
        for tie in (False, True):
            ms = {n: old.lru(old.query_pages(sel, L.positions(p), 1, range(32768)), C, 16384, descending=tie) for n, p in lays.items()}
            row.append(f"{'desc' if tie else 'asc'}: ID {ms['ID']:.5f} FREQ {ms['FREQ']:.5f}")
        print(label, f"R1 C{C}", " | ".join(row))
