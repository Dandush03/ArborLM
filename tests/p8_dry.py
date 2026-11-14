"""One full-size synthetic dry-run cell (evaluation, then simulation), built once per process."""

import tempfile
from functools import cache
from pathlib import Path

from arborlm import p8_core as core
from arborlm import p8_eval, p8_sim
from arborlm.io import read_json, write_json
from arborlm.p7a_trace import configure_deterministic_cpu


@cache
def dry_cell(label: str = "b101-o301-s601-C03") -> tuple[Path, Path]:
    """(eval cell dir, sim cell dir); a registered tree cell with random-init checkpoints."""
    configure_deterministic_cpu()
    root = Path(tempfile.mkdtemp(prefix="p8dry-"))
    eval_dir, sim_dir = root / "eval", root / "sim"
    eval_dir.mkdir()
    sim_dir.mkdir()
    write_json(
        root / "job.json",
        {"label": label, "cell_dir": str(eval_dir), "dry_run": True},
    )
    assert p8_eval.worker_main(root / "job.json") == 0
    cell = core.parse_label(label)
    record = p8_sim.simulate_cell(cell, eval_dir, sim_dir)
    write_json(sim_dir / "sim.json", record)
    assert read_json(eval_dir / "eval.json")["outcome"] == "completed"
    return eval_dir, sim_dir
