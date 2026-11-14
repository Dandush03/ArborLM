"""R3 (re-check of rev 2) - section 7 objectives: EMA gradient scale, coefficient magnitudes, soft-usage
gaming, Adam on gradient-free rows, row-lazy learning rate. Pure math / toy autograd, no ArborLM code.

1. u_t = (1-b) u_{t-1}.detach() + b * ubar(theta), b = 128/F ('EMA over the last F/128 updates').
   Autograd shows dR/dtheta carries the factor b; compared with the 'gradient at u_t, full weight' reading.
2. lambda_u, lambda_c values (rev 2 formulas) and the penalty at typical states vs the answer loss.
3. Soft-usage gaming: H(u) when the hard top-8 use K slots and the 56 other candidates carry pi = x.
4. AdamW on a row whose only gradient is a tiny regularizer gradient g: movement per update.
5. Row-lazy Adam (row-count bias correction) per-exposure movement vs dense AdamW, and the lr that
   matches dense AdamW at 4,096 slots (K = 16).
"""

import json
import math

import torch

LN32 = math.log(32)


def part1() -> None:
    for n, f in ((4096, 2048), (16384, 8192), (65536, 32768)):
        b = 128 / f
        m = min(n, 8 * f) / 2
        g = torch.Generator().manual_seed(n)
        logits = torch.randn(n, generator=g, dtype=torch.float64) * 3.0  # a concentrated usage state
        theta = logits.clone().requires_grad_(True)
        prev = torch.softmax(logits + 0.1 * torch.randn(n, generator=g, dtype=torch.float64), 0)
        ubar = torch.softmax(theta, 0)
        u = (1 - b) * prev + b * ubar
        h = -(u * u.log()).sum()
        r = torch.clamp(math.log(m) - h, min=0) / math.log(n)
        (grad_ema,) = torch.autograd.grad(r, theta, retain_graph=True)
        # 'full weight' reading: dR/du evaluated at u_t, applied to ubar
        u_det = u.detach().requires_grad_(True)
        h2 = -(u_det * u_det.log()).sum()
        r2 = torch.clamp(math.log(m) - h2, min=0) / math.log(n)
        (dr_du,) = torch.autograd.grad(r2, u_det)
        (grad_full,) = torch.autograd.grad(ubar, theta, grad_outputs=dr_du)
        print(json.dumps({"part": 1, "N": n, "F": f, "ema_weight_b": b, "M": m, "H_u": round(float(h), 3),
                          "ln_M": round(math.log(m), 3), "R_glob": round(float(r), 4),
                          "grad_norm_ema_autograd": float(grad_ema.norm()),
                          "grad_norm_full_weight": float(grad_full.norm()),
                          "ratio": round(float(grad_ema.norm() / grad_full.norm()), 5)}))


def part2() -> None:
    for n, f in ((4096, 2048), (16384, 8192), (65536, 32768)):
        m = min(n, 8 * f) / 2
        lam_u1 = LN32 / (math.log(m) / math.log(n))
        # usage one nat below the floor
        pen_1nat = lam_u1 * 1.0 / math.log(n)
        print(json.dumps({"part": 2, "N": n, "M": m, "M_over_N": m / n, "lambda_u(alpha=1)": round(lam_u1, 4),
                          "penalty_alpha1_H_one_nat_below_floor": round(pen_1nat, 4),
                          "penalty_alpha1_P8_like_127_effective": round(lam_u1 * max(0, math.log(m) - math.log(127)) / math.log(n), 3)}))
    lam_c1 = LN32 / (1 - 1 / 8)
    for r_co in (1.0, 0.75, 0.5, 0.25, 0.125):
        print(json.dumps({"part": 2, "R_co": r_co, "penalty_alpha_c=1": round(lam_c1 * r_co, 3),
                          "penalty_alpha_c=0.25": round(0.25 * lam_c1 * r_co, 3),
                          "penalty_if_shifted_by_1/8_alpha_c=1": round(lam_c1 * (r_co - 1 / 8), 3)}))
    for acc_loss in (("chance", LN32), ("acc~0.5 (p_true~0.4)", -math.log(0.4)), ("acc~0.9 (p_true~0.8)", -math.log(0.8))):
        print(json.dumps({"part": 2, "answer_loss_state": acc_loss[0], "nats": round(acc_loss[1], 3)}))
    # random 8-of-N selection: expected distinct 8-slot groups among 8 random slots
    for n in (16384,):
        groups = n // 8
        exp_groups = groups * (1 - (1 - 1 / groups) ** 8)
        print(json.dumps({"part": 2, "N": n, "expected_groups_touched_by_8_random_slots": round(exp_groups, 4),
                          "R_co_random": round(exp_groups / 8, 4)}))


def part3() -> None:
    for n in (16384,):
        m = n / 2
        for k_hard, pool in ((1000, 8192), (1000, 16384), (2000, 8192), (500, 4096)):
            for x in (0.0, 0.1, 0.3, 0.5):
                s = 56 * x / (8 + 56 * x)
                hs = 0.0 if s in (0.0, 1.0) else -s * math.log(s) - (1 - s) * math.log(1 - s)
                h = hs + (1 - s) * math.log(k_hard) + s * math.log(pool)
                print(json.dumps({"part": 3, "N": n, "hard_effective_slots": k_hard, "candidate_pool": pool,
                                  "pi_outside_top8": x, "soft_share_outside_top8": round(s, 3),
                                  "H_u_upper_disjoint": round(h, 3), "floor_ln_M": round(math.log(m), 3),
                                  "hinge_satisfied": h >= math.log(m)}))


def adam_move(g: float, steps: int = 50, lr: float = 0.003) -> float:
    m = v = 0.0
    x = 0.0
    for t in range(1, steps + 1):
        m = 0.9 * m + 0.1 * g
        v = 0.999 * v + 0.001 * g * g
        x -= lr * (m / (1 - 0.9**t)) / (math.sqrt(v / (1 - 0.999**t)) + 1e-8)
    return abs(x) / steps


def part4() -> None:
    for g in (1.0, 1e-3, 1e-6, 1e-7, 1e-8, 1e-9):
        print(json.dumps({"part": 4, "constant_gradient": g, "movement_per_update_in_lr": round(adam_move(g) / 0.003, 4)}))


def lazy_move(k: int, events: int, lr: float) -> float:
    m = v = 0.0
    x = 0.0
    c = 0
    for _ in range(events):
        c += 1
        m = 0.9 * m + 0.1
        v = 0.999 * v + 0.001
        x -= lr * (m / (1 - 0.9**c)) / (math.sqrt(v / (1 - 0.999**c)) + 1e-8)
    return abs(x) / events


def dense_move(k: int, events: int, lr: float) -> float:
    m = v = 0.0
    x = 0.0
    for t in range(1, events * k + 1):
        g = 1.0 if (t - 1) % k == 0 else 0.0
        m = 0.9 * m + 0.1 * g
        v = 0.999 * v + 0.001 * g * g
        x -= lr * (m / (1 - 0.9**t)) / (math.sqrt(v / (1 - 0.999**t)) + 1e-8)
    return abs(x) / events


def part5() -> None:
    for k, f in ((16, 2048), (64, 8192), (256, 32768)):
        d = dense_move(k, 32, 0.003)
        lz = lazy_move(k, 32, 0.003)
        lz4 = lazy_move(k, 32, 0.012)
        print(json.dumps({"part": 5, "facts": f, "K": k, "dense_adamw_per_exposure_lr": round(d / 0.003, 2),
                          "row_lazy_lr0.003_per_exposure_lr": round(lz / 0.003, 2),
                          "row_lazy_lr0.012_per_exposure_lr": round(lz4 / 0.003, 2)}))


if __name__ == "__main__":
    part1()
    part2()
    part3()
    part4()
    part5()
