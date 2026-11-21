# ruff: noqa: E501
"""Known-truth test of the power simulation (ADR-0033 section 9.4, gate 1; the freeze gate).

The study's simulation (``power``) is run on synthetic data whose answer is known, in the six scenarios of Review 3
(S1 to S6) as defined by ``docs/reviews/adr-0033-m0-2026-11-20/checks/shrink_check3c.py``:

  Truth model (one stratum): G clusters, cluster effect mu_g ~ N(0, tau) clamped so probabilities stay valid, item
  D in {+1, -1, 0} with P(+1) = (d + mu_g) / 2, P(-1) = (d - mu_g) / 2. The KNOWN power is the M5 test (mean,
  cluster-robust SE over G clusters, t quantile, pass if estimate - t SE > -delta) applied to fresh clusters and fresh
  items, n / G per cluster.

The RECOVERED power is the mean, over ``draws`` independent synthetic M0 draws, of the power the study's simulation
returns from that one draw. Registered tolerance 0.03 (proposed); the number of draws and of runs is registered so
that each side's Monte Carlo standard error is at most 0.01 (Review 3 used six draws, whose single-draw spread is too
wide). The spread over draws is printed. A scenario whose Monte Carlo standard error exceeds the bound on either side
is INCONCLUSIVE and counts as a failure of the gate.

Run: ``uv run --locked python -m studies.m0.knowntruth --profile short|long``.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict, dataclass

import torch

from studies.m0 import config as cfgmod
from studies.m0.core import derive_seed
from studies.m0.power import components, simulate_power
from studies.m0.stats import t_quantile


@dataclass(frozen=True)
class Scenario:
    name: str
    d: float
    tau: float
    sizes: str
    delta: float


def scenarios_from_config(cfg: dict) -> list[Scenario]:
    k = cfg["knowntruth"]
    return [Scenario(n, d, t, s, dl) for n, d, t, s, dl in zip(k["scenario_names"], k["scenario_d"], k["scenario_tau"], k["scenario_sizes"], k["scenario_delta"], strict=True)]


def size_pattern(kind: str, g: int) -> list[int]:
    if kind == "balanced5":
        return [5] * g
    if kind == "unbalanced":  # 60 clusters each of 1, 2, 3, 5 and 16 items at G = 300 (1,620 items), in proportion otherwise
        base = [1, 2, 3, 5, 16]
        return [base[min(4, i * 5 // g)] for i in range(g)]
    raise ValueError(kind)


def _clamp(mu: float, d: float) -> float:
    return max(-d + 1e-9, min(d - 1e-9, mu))


def synthetic_m0(sc: Scenario, g: int, rng: random.Random) -> list[tuple[str, list[float]]]:
    """One synthetic M0 draw: g clusters with the scenario's cluster-size pattern, one stratum."""
    out = []
    for m in size_pattern(sc.sizes, g):
        mu = _clamp(rng.gauss(0.0, sc.tau), sc.d)
        xs = rng.choices((1.0, -1.0, 0.0), weights=((sc.d + mu) / 2, (sc.d - mu) / 2, 1 - sc.d), k=m)
        out.append(("all", xs))
    return out


def truth_power(sc: Scenario, g: int, n: int, runs: int, seed: int, chunk_cells: int = 6_000_000) -> tuple[float, float]:
    """The known power: M5's test on fresh clusters and fresh items (independent of the study's simulation code)."""
    gen = torch.Generator()
    gen.manual_seed(derive_seed(seed, f"truth/{sc.name}") % (2**63 - 1))
    m = n // g
    tq = t_quantile(0.95, g - 1)
    ok = 0
    done = 0
    chunk = max(1, chunk_cells // (g * m))
    while done < runs:
        k = min(chunk, runs - done)
        mu = torch.randn((k, g), generator=gen, dtype=torch.float64) * sc.tau
        mu = mu.clamp(-sc.d + 1e-9, sc.d - 1e-9)
        pp = ((sc.d + mu) / 2).unsqueeze(2)
        pm = ((sc.d - mu) / 2).unsqueeze(2)
        u = torch.rand((k, g, m), generator=gen, dtype=torch.float64)
        x = (u < pp).to(torch.float64) - ((u >= pp) & (u < pp + pm)).to(torch.float64)
        s = x.sum(dim=2)  # cluster sums
        tot = float(g * m)
        est = s.sum(dim=1) / tot
        ss = ((s - m * est.view(-1, 1)) ** 2).sum(dim=1)
        se = torch.sqrt(ss * g / (g - 1)) / tot
        ok += int(((est - tq * se) > -sc.delta).sum())
        done += k
    p = ok / runs
    return p, math.sqrt(p * (1 - p) / runs)


@dataclass
class ScenarioResult:
    name: str
    known: float
    known_se: float
    recovered: float
    recovered_se: float
    draw_min: float
    draw_max: float
    draw_sd: float
    mean_tau_hat: float
    difference: float
    tolerance: float
    verdict: str  # PASS | FAIL | INCONCLUSIVE (MONTE CARLO SE)


def run_scenario(sc: Scenario, g: int, n: int, draws: int, sims: int, truth_runs: int, seed: int, tolerance: float, max_se: float) -> ScenarioResult:
    known, known_se = truth_power(sc, g, n, truth_runs, seed)
    rng = random.Random(derive_seed(seed, f"m0draws/{sc.name}"))
    per_draw: list[float] = []
    taus: list[float] = []
    for i in range(draws):
        m0 = synthetic_m0(sc, g, rng)
        comp = components(m0)
        taus.append(comp.tau)
        per_draw.append(simulate_power(comp, n, [sc.delta], g, sims, seed, label=f"{sc.name}/{i}")[sc.delta][0])
    rec = sum(per_draw) / draws
    sd = math.sqrt(sum((p - rec) ** 2 for p in per_draw) / (draws - 1)) if draws > 1 else float("nan")
    rec_se = sd / math.sqrt(draws)
    diff = rec - known
    if not (rec_se <= max_se and known_se <= max_se):
        verdict = "INCONCLUSIVE (MONTE CARLO SE)"
    else:
        verdict = "PASS" if abs(diff) <= tolerance else "FAIL"
    return ScenarioResult(sc.name, known, known_se, rec, rec_se, min(per_draw), max(per_draw), sd, sum(taus) / len(taus), diff, tolerance, verdict)


PROFILES = {
    # the registered (proposed) numbers come from the config; the short profile is the default pytest version
    "short": {"scenarios": ("S1", "S3", "S6"), "draws": 40, "sims": 300, "truth_runs": 4000, "tolerance": 0.06, "max_se": 0.03},
    "long": {"scenarios": None, "draws": None, "sims": None, "truth_runs": None, "tolerance": None, "max_se": None},
}


def run_profile(profile: str, cfg: dict | None = None) -> list[ScenarioResult]:
    cfg = cfg or cfgmod.load()
    k = cfg["knowntruth"]
    p = PROFILES[profile]
    chosen = p["scenarios"]
    draws = p["draws"] or k["draws"]
    sims = p["sims"] or k["sims_per_draw"]
    truth_runs = p["truth_runs"] or k["truth_runs"]
    tol = p["tolerance"] if p["tolerance"] is not None else k["tolerance"]
    max_se = p["max_se"] if p["max_se"] is not None else k["max_monte_carlo_se"]
    out = []
    for sc in scenarios_from_config(cfg):
        if chosen and sc.name not in chosen:
            continue
        out.append(run_scenario(sc, k["clusters"], k["n_items"], draws, sims, truth_runs, k["seed"], tol, max_se))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", choices=sorted(PROFILES), required=True)
    ap.add_argument("--out", help="write the results as JSON to this path")
    ap.add_argument("--threads", type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    t0 = time.time()
    res = run_profile(a.profile)
    for r in res:
        print(f"{r.name}: known={r.known:.3f} (se {r.known_se:.4f}); recovered={r.recovered:.3f} (se {r.recovered_se:.4f}; draws {r.draw_min:.3f}-{r.draw_max:.3f}, sd {r.draw_sd:.3f}); "
              f"mean tau_hat={r.mean_tau_hat:.4f}; difference={r.difference:+.3f} vs tolerance {r.tolerance}; {r.verdict}")
    gate = all(r.verdict == "PASS" for r in res)
    print(f"profile {a.profile}: {'ALL PASS' if gate else 'NOT ALL PASS'} ({time.time() - t0:.0f} s). Self-check only: not the independent recomputation that the freeze gate also requires.")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"profile": a.profile, "results": [asdict(r) for r in res]}, fh, indent=1)


if __name__ == "__main__":
    main()
