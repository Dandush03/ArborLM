"""Auditor feasibility estimate of one P6-Q checkpoint evaluation on a SYNTHETIC model.

Random-weight tree model with registered shapes and a random 512x65 token panel; no real
checkpoint or data. Exploratory single run.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_budget.py
"""

import time

import torch

from arborlm import p6_fidelity as fid
from arborlm.engine import configure_cpu
from arborlm.p2_config import CONTROL
from arborlm.p2_config import Cell as ParentCell
from arborlm.p2_model import FollowupModel
from arborlm.p4_model import extract
from arborlm.p5_config import FIXED, Cell
from arborlm.p5_model import Model, evaluate


def main() -> None:
    start = time.monotonic()
    configure_cpu()
    backbone = extract(FollowupModel(ParentCell(101, 201, 301, CONTROL)))
    model = Model(Cell(101, 301, 501, FIXED), backbone)
    g = torch.Generator().manual_seed(11)
    with torch.no_grad():
        model.addition.keys += torch.randn(4096, 16, generator=g) * 0.06  # type: ignore[union-attr]
    panel = torch.randint(0, 256, (512, 65), generator=torch.Generator().manual_seed(5))
    recorded = evaluate(model, panel, 32768)
    initial = (model.addition.keys.detach() + 0.01, model.addition.values.detach().clone())  # type: ignore[union-attr]
    t = time.monotonic()
    record, arrays = fid.evaluate_checkpoint(
        model, panel, recorded_nll=recorded["nll"], recorded_retrieval=recorded["retrieval"],
        initial_tensors=initial, reference=fid.load_reference(), expected_targets=32768,
    )
    print(f"evaluate_checkpoint (synthetic, full panel): {time.monotonic()-t:.1f} s")
    print("phase seconds:", {k: round(v, 1) for k, v in record["phase_seconds"].items()})
    print("array bytes:", sum(a.numel() * a.element_size() for a in arrays.values()))
    print("gate iv disagreements:", record["gates"]["iv"]["disagreement_count"],
          "sets differ:", record["gates"]["iv"]["sets_differ_count"])
    print(f"process wall incl. imports and setup: {time.monotonic()-start:.1f} s")


if __name__ == "__main__":
    main()
