"""C4 - per-event movement of a parameter row that receives a gradient only every K updates (pure math).

ADR-0017 rev 1: batch = 128 fact exposures, each fact seen once per epoch of F/128 updates, so a
value/key row dedicated to one fact (rung R2, or a slot used by one fact) has a gradient on about one
update in K = F/128: K = 16 (2,048 facts), 64 (8,192), 256 (32,768). Gradient sign constant, |g| = 1.

Optimizers (lr 0.003, betas 0.9/0.999, eps 1e-8, no weight decay - rev 1 section 5.1):
  dense   : torch-style AdamW, moments decay every update, bias correction by the global step.
  lazy_row: moments and parameter change only on updates with nonzero gradient; bias correction by the
            row's own count of nonzero-gradient updates (one reading of rev 1 section 7).
  lazy_glb: as lazy_row but bias correction by the global step (torch.optim.SparseAdam-style).
Reported: movement over the first 32 events (E = 32), share of movement on updates without gradient
(the 'tail'), and movement per event after the 32nd event (late steady state).
"""

import json
import math

LR, B1, B2, EPS = 0.003, 0.9, 0.999, 1e-8


def run(kind: str, k: int, events: int = 32) -> dict[str, float]:
    m = v = 0.0
    x = 0.0
    tail = 0.0
    row_count = 0
    per_event_last = 0.0
    total_steps = events * k
    for t in range(1, total_steps + 1):
        has_grad = (t - 1) % k == 0
        g = 1.0 if has_grad else 0.0
        before = x
        if kind == "dense":
            m = B1 * m + (1 - B1) * g
            v = B2 * v + (1 - B2) * g * g
            mh, vh = m / (1 - B1**t), v / (1 - B2**t)
            x -= LR * mh / (math.sqrt(vh) + EPS)
        elif has_grad:
            row_count += 1
            m = B1 * m + (1 - B1) * g
            v = B2 * v + (1 - B2) * g * g
            n = row_count if kind == "lazy_row" else t
            mh, vh = m / (1 - B1**n), v / (1 - B2**n)
            x -= LR * mh / (math.sqrt(vh) + EPS)
        step = abs(x - before)
        if not has_grad:
            tail += step
        if t > total_steps - k:
            per_event_last += step
    return {"movement_after_32_events": round(abs(x), 4), "share_on_updates_without_gradient": round(tail / abs(x), 3),
            "movement_per_event_late": round(per_event_last, 5), "ratio_to_lr": round(per_event_last / LR, 2)}


def main() -> None:
    for k, f in ((1, None), (16, 2048), (64, 8192), (256, 32768)):
        for kind in ("dense", "lazy_row", "lazy_glb"):
            print(json.dumps({"K_updates_between_events": k, "facts": f, "optimizer": kind, **run(kind, k)}))


if __name__ == "__main__":
    main()
