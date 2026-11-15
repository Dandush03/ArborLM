"""Coordinator's item: does an S1 code path called in-process change torch / RNG / environment state of the calling process? Snapshot before and after
(1) stages.main(["work", "calibrate-cell", ...]) refused (the call tests/test_p10s1_stages.py:56 makes), (2) model.build_model(seed_rng=True) as tests do.
Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r9_process_state.py <scratch>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import contextlib, io, json, os, random, sys
import torch
from studies.p10s1 import stages

def snap():
    return {"threads": torch.get_num_threads(), "interop": torch.get_num_interop_threads(), "deterministic": torch.are_deterministic_algorithms_enabled(), "dtype": str(torch.get_default_dtype()),
            "torch_rng_sha": hash(torch.get_rng_state().numpy().tobytes()) if False else int(torch.get_rng_state().sum()), "py_rng": random.getstate()[1][:2], "env_P10S1": {k: v for k, v in os.environ.items() if "P10S1" in k}}
out = {"before": snap()}
with contextlib.redirect_stderr(io.StringIO()):
    code = stages.main(["work", "calibrate-cell", "--labels", "nonsense", "--run-dir", sys.argv[1], "--mode", "calibration", "--dry"])
out["exit"] = code
out["after_work_calibrate_cell_refused"] = snap()
json.dump(out, sys.stdout, indent=1); print()
