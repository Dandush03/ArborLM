"""Auditor check: is the study's chunked frequency-matched generator (2048 rows per batched
torch.multinomial call) identical, at FULL size (32,768 queries x 4,096 slots), to the literal reading
of clarification 2 (one torch.multinomial(counts, 8, replacement=False) call per query on one
generator)? The implementer's test only checks 600 queries, 300 nonzero weights, chunk 256.

Uses published P5 histograms as weights; computes no page or cache metric. Does not import arborlm.
Run: uv run --locked --extra pilot python docs/reviews/p7a-preflight-2026-11-13/check_fm_chunking.py
"""

import json
import sys
import time
from pathlib import Path

import torch

P5 = Path("results/p5-2026-11-13")
Q, TOP, SLOTS = 32768, 8, 4096
CELLS = (("b101-o301-flat-s501", 0), ("b102-o302-learned_tree-s503", (9 + 3 + 2) * 3 + 2))


def main() -> int:
    torch.set_num_threads(1)
    ok = True
    for label, index in CELLS:
        counts = json.loads((P5 / label / "result.json").read_text())["final"]["retrieval"][
            "selected_slot_counts"
        ]
        w = torch.tensor(counts, dtype=torch.float32)
        for s in (91301, 91303):
            seed = s * 1000 + index
            t0 = time.time()
            g = torch.Generator().manual_seed(seed)
            chunked = torch.cat([
                torch.multinomial(w.expand(2048, SLOTS), TOP, replacement=False, generator=g)
                for _ in range(Q // 2048)
            ])
            g = torch.Generator().manual_seed(seed)
            literal = torch.stack([
                torch.multinomial(w, TOP, replacement=False, generator=g) for _ in range(Q)
            ])
            same = bool(torch.equal(chunked, literal))
            ok &= same
            print(f"{label} seed {seed}: chunked == per-query: {same} ({time.time() - t0:.1f}s)")
    print("torch", torch.__version__, "ALL EQUAL" if ok else "DIFFERENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
