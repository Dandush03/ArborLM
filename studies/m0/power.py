# ruff: noqa: E501
"""Power simulation of M5's own design from measured paired outcomes (ADR-0033 section 9.4, revision 4 wording).

Implements, exactly as worded there:
  * the shrunk deviation of a drawn cluster, lambda_g (xbar_g - xbar_h), lambda_g = sqrt(tau2 / (tau2 + s_w2 / m_g)),
    tau2 = max(0, V - s_w2 * mean(1/m_g)), so that the simulated population's mean difference is exactly zero and its
    between-cluster variance is tau2;
  * n / G_e item deviations per cluster drawn with replacement from the stratum's pooled within-cluster residuals,
    each residual (x - xbar_g) multiplied by sqrt(m_g / (m_g - 1)); clusters with one item contribute no residual;
  * the sample's own mean is never subtracted; its mean difference and cluster-robust standard error over the G_e
    drawn clusters are scaled by sqrt(d_e / (d_e - mu^2)); the test passes if estimate - t_{0.95, G_e - 1} SE > -delta;
  * the floor from the clusters, Phi(delta sqrt(G_e) / tau_e - z_0.95), with the bootstrap 90 % interval of tau_e;
  * the conjunction by Boole's inequality over the ladder, and the confirmation with the percentile bootstrap inside.

Standard library and the locked torch only. Readings that the wording leaves open, each chosen for the least favourable
result and listed in studies/m0/NOTES.md: V is pooled over strata (strata with one cluster contribute nothing);
n is spread over the G_e drawn clusters as evenly as integers allow; a stratum with no residual uses the residuals pooled over strata (zero noise only if there are none anywhere).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

import torch

from studies.m0.core import derive_seed
from studies.m0.stats import t_quantile

_N = NormalDist()
Z95 = _N.inv_cdf(0.95)
LADDER = (500, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 12000, 16000, 20000)


@dataclass(frozen=True)
class Components:
    """What the simulation reads from one measured pair (item-level paired differences x in {-1, 0, +1})."""

    strata: tuple[str, ...]  # sorted
    stratum_clusters: dict[str, tuple[int, ...]]  # stratum -> cluster indices
    mean_g: tuple[float, ...]
    m_g: tuple[int, ...]
    ssw_g: tuple[float, ...]  # within-cluster sum of squares
    mu: float  # measured mean difference of the pair
    d: float  # measured discordance (share of items with x != 0)
    s_w2: float
    v_between: float
    tau2: float
    lam: tuple[float, ...]
    dev: tuple[float, ...]  # lambda_g (xbar_g - xbar_h)
    residuals: dict[str, tuple[float, ...]]  # stratum -> pooled corrected residuals

    @property
    def tau(self) -> float:
        return math.sqrt(self.tau2)

    @property
    def scale(self) -> float:
        den = self.d - self.mu**2
        return math.sqrt(self.d / den) if den > 1e-12 else 1.0


def estimate_tau2(v: float, s_w2: float, inv_m_mean: float) -> float:
    """tau2 = max(0, V - s_w2 * mean(1/m_g))  (revision 4 wording)."""
    return max(0.0, v - s_w2 * inv_m_mean)


def components(clusters: Sequence[tuple[str, Sequence[float]]]) -> Components:
    """``clusters``: (stratum, paired differences of the M0-draw items of that cluster) for every cluster."""
    g = len(clusters)
    m_g = tuple(len(x) for _, x in clusters)
    mean_g = tuple(sum(x) / len(x) for _, x in clusters)
    ssw = tuple(sum((v - mean_g[i]) ** 2 for v in clusters[i][1]) for i in range(g))
    items = [v for _, x in clusters for v in x]
    n0 = len(items)
    mu = sum(items) / n0
    d = sum(1 for v in items if v != 0) / n0
    strata = tuple(sorted({s for s, _ in clusters}))
    sc = {h: tuple(i for i in range(g) if clusters[i][0] == h) for h in strata}
    denom_w = sum(m - 1 for m in m_g if m > 1)
    s_w2 = sum(ssw[i] for i in range(g) if m_g[i] > 1) / denom_w if denom_w else 0.0
    num_v = 0.0
    den_v = 0
    xbar_h: dict[str, float] = {}
    for h in strata:
        ms = [mean_g[i] for i in sc[h]]
        xbar_h[h] = sum(ms) / len(ms)
        if len(ms) >= 2:
            num_v += sum((v - xbar_h[h]) ** 2 for v in ms)
            den_v += len(ms) - 1
    v_between = num_v / den_v if den_v else 0.0
    inv_m = sum(1.0 / m for m in m_g) / g
    tau2 = estimate_tau2(v_between, s_w2, inv_m)
    lam = tuple(math.sqrt(tau2 / (tau2 + s_w2 / m_g[i])) if tau2 > 0 else 0.0 for i in range(g))
    dev = tuple(lam[i] * (mean_g[i] - xbar_h[clusters[i][0]]) for i in range(g))
    res: dict[str, tuple[float, ...]] = {}
    for h in strata:
        pool: list[float] = []
        for i in sc[h]:
            if m_g[i] > 1:
                k = math.sqrt(m_g[i] / (m_g[i] - 1))
                pool.extend((v - mean_g[i]) * k for v in clusters[i][1])
        res[h] = tuple(pool)
    pooled_all = tuple(v for h in strata for v in res[h])
    for h in strata:  # a stratum with no residual of its own uses the residuals pooled over strata (audit C2)
        if not res[h]:
            res[h] = pooled_all
    return Components(strata, sc, mean_g, m_g, ssw, mu, d, s_w2, v_between, tau2, lam, dev, res)


def _gen(seed: int, label: str) -> torch.Generator:
    g = torch.Generator()
    g.manual_seed(derive_seed(seed, label) % (2**63 - 1))
    return g


def allocate_strata(comp: Components, g_e: int) -> dict[str, int]:
    """Clusters per stratum in the simulated sealed split: in proportion to the stratum's clusters (the sealed pool is
    spread evenly over the clusters), largest remainder, ties to the earlier stratum."""
    sizes = [len(comp.stratum_clusters[h]) for h in comp.strata]
    tot = sum(sizes)
    raw = [g_e * s / tot for s in sizes]
    base = [int(x) for x in raw]
    for i in sorted(range(len(sizes)), key=lambda i: (-(raw[i] - base[i]), i))[: g_e - sum(base)]:
        base[i] += 1
    return dict(zip(comp.strata, base, strict=True))


def _counts(n: int, g_e: int) -> torch.Tensor:
    """n items spread over g_e clusters as evenly as integers allow."""
    i = torch.arange(g_e + 1, dtype=torch.int64)
    c = (i * n) // g_e
    return (c[1:] - c[:-1]).to(torch.float64)


def sample_cluster_sums(comp: Components, n: int, g_e: int, sims: int, gen: torch.Generator) -> tuple[torch.Tensor, torch.Tensor, list[tuple[str, int, int]]]:
    """For ``sims`` simulated sealed samples: cluster sums S (sims, g_e) and item counts m (g_e,), plus the stratum spans."""
    alloc = allocate_strata(comp, g_e)
    counts = _counts(n, g_e)
    sums = torch.zeros((sims, g_e), dtype=torch.float64)
    spans: list[tuple[str, int, int]] = []
    pos = 0
    dev_t = torch.tensor(comp.dev, dtype=torch.float64)
    for h in comp.strata:
        gh = alloc[h]
        if gh == 0:
            continue
        cl = torch.tensor(comp.stratum_clusters[h], dtype=torch.int64)
        pick = cl[torch.randint(0, len(cl), (sims, gh), generator=gen)]  # drawn clusters (with replacement)
        m = counts[pos : pos + gh]
        s = dev_t[pick] * m  # shrunk deviation of every item of the cluster
        pool = torch.tensor(comp.residuals[h], dtype=torch.float64)
        if pool.numel() > 0:
            mmax = int(m.max())
            r = pool[torch.randint(0, pool.numel(), (sims, gh, mmax), generator=gen)]
            mask = torch.arange(mmax).view(1, 1, mmax) < m.view(1, gh, 1)
            s = s + (r * mask).sum(dim=2)
        sums[:, pos : pos + gh] = s
        spans.append((h, pos, pos + gh))
        pos += gh
    return sums, counts, spans


def simulate_power(comp: Components, n: int, deltas: Sequence[float], g_e: int, sims: int, seed: int, label: str = "", chunk: int | None = None) -> dict[float, tuple[float, float]]:
    """Per-test power of M5's test at size n for each margin: {delta: (share that pass, Monte Carlo standard error)}."""
    gen = _gen(seed, f"power/{label}/{n}")
    if chunk is None:
        chunk = max(1, 3_000_000 // max(1, n))
    passes = {dl: 0 for dl in deltas}
    done = 0
    tq = t_quantile(0.95, g_e - 1)
    while done < sims:
        k = min(chunk, sims - done)
        sums, counts, _ = sample_cluster_sums(comp, n, g_e, k, gen)
        tot = float(counts.sum())
        est = sums.sum(dim=1) / tot
        ss = ((sums - counts.view(1, -1) * est.view(-1, 1)) ** 2).sum(dim=1)
        se = torch.sqrt(ss * g_e / (g_e - 1)) / tot
        lower = comp.scale * est - tq * comp.scale * se
        for dl in deltas:
            passes[dl] += int((lower > -dl).sum())
        done += k
    return {dl: (passes[dl] / sims, math.sqrt(max(passes[dl] / sims * (1 - passes[dl] / sims), 0.0) / sims)) for dl in deltas}


def cluster_floor(comp: Components, delta: float, g_e: int, tau: float | None = None) -> float:
    """Largest per-test power reachable at any n: Phi(delta sqrt(G_e) / tau - z_0.95); 1 when tau is 0."""
    t = comp.tau if tau is None else tau
    if t <= 0:
        return 1.0
    return _N.cdf(delta * math.sqrt(g_e) / t - Z95)


def tau_interval(clusters: Sequence[tuple[str, Sequence[float]]], b: int, seed: int, label: str = "") -> tuple[float, float, float]:
    """tau_e and the cluster-bootstrap 90 % interval (5th and 95th percentile of tau-hat over resamples of clusters
    within strata). Returns (point, lo, hi)."""
    point = components(clusters).tau
    comp0 = components(clusters)
    g = len(clusters)
    m = torch.tensor(comp0.m_g, dtype=torch.float64)
    mean = torch.tensor(comp0.mean_g, dtype=torch.float64)
    ssw = torch.tensor(comp0.ssw_g, dtype=torch.float64)
    gen = _gen(seed, f"tau/{label}")
    num_v = torch.zeros(b, dtype=torch.float64)
    den_v = 0
    num_w = torch.zeros(b, dtype=torch.float64)
    den_w = torch.zeros(b, dtype=torch.float64)
    inv_m = torch.zeros(b, dtype=torch.float64)
    for h in comp0.strata:
        cl = torch.tensor(comp0.stratum_clusters[h], dtype=torch.int64)
        idx = cl[torch.randint(0, len(cl), (b, len(cl)), generator=gen)]
        mm, mu, ss = m[idx], mean[idx], ssw[idx]
        if len(cl) >= 2:
            num_v += ((mu - mu.mean(dim=1, keepdim=True)) ** 2).sum(dim=1)
            den_v += len(cl) - 1
        num_w += torch.where(mm > 1, ss, torch.zeros_like(ss)).sum(dim=1)
        den_w += torch.where(mm > 1, mm - 1, torch.zeros_like(mm)).sum(dim=1)
        inv_m += (1.0 / mm).sum(dim=1)
    v = num_v / den_v if den_v else torch.zeros(b, dtype=torch.float64)
    sw2 = torch.where(den_w > 0, num_w / den_w.clamp(min=1), torch.zeros_like(num_w))
    tau2 = torch.clamp(v - sw2 * inv_m / g, min=0.0)
    taus = torch.sqrt(tau2)
    srt = torch.sort(taus).values
    lo = float(srt[max(0, math.floor(0.05 * (b + 1)) - 1)])
    hi = float(srt[min(b - 1, b - math.floor(0.05 * (b + 1)))])
    return point, lo, hi


def required_size(comp: Components, delta: float, g_e: int, m_tests: int, sims: int, seed: int, power: float = 0.8, ladder: Sequence[int] = LADDER, label: str = "") -> tuple[int | None, list[tuple[int, float, float]]]:
    """Smallest n on the ladder with per-test power >= 1 - (1 - power) / M_e (Boole), M_e = ``m_tests``.
    Returns (n or None, [(n, pi, mc_se)] for every size tried)."""
    target = 1.0 - (1.0 - power) / m_tests
    tried: list[tuple[int, float, float]] = []
    for n in ladder:
        pi, se = simulate_power(comp, n, [delta], g_e, sims, seed, label=f"{label}/{delta}")[delta]
        tried.append((n, pi, se))
        if pi >= target:
            return n, tried
    return None, tried


def confirm_power(comp: Components, n: int, delta: float, g_e: int, sims: int, boot: int, seed: int, label: str = "", chunk_cells: int = 2_000_000) -> tuple[float, float]:
    """Confirmation: ``sims`` simulated samples, each tested with the full stratified percentile bootstrap (``boot``
    resamples of the drawn clusters within strata); passes if the one-sided 5 % percentile bound of the scaled mean
    difference is above -delta. Returns (share that pass, Monte Carlo standard error)."""
    gen = _gen(seed, f"confirm/{label}/{n}/{delta}")
    passes = 0
    done = 0
    per_sim = max(1, boot * g_e)
    chunk = max(1, chunk_cells // per_sim)
    k_idx = max(1, math.floor(0.05 * (boot + 1)))
    while done < sims:
        k = min(chunk, sims - done)
        sums, counts, spans = sample_cluster_sums(comp, n, g_e, k, gen)
        num = torch.zeros((k, boot), dtype=torch.float64)
        den = torch.zeros((k, boot), dtype=torch.float64)
        for _, s0, s1 in spans:
            idx = torch.randint(s0, s1, (k, boot, s1 - s0), generator=gen)
            num += torch.gather(sums.unsqueeze(1).expand(k, boot, g_e), 2, idx).sum(dim=2)
            den += counts[idx].sum(dim=2)
        vals = comp.scale * num / den
        low = torch.sort(vals, dim=1).values[:, k_idx - 1]
        passes += int((low > -delta).sum())
        done += k
    p = passes / sims
    return p, math.sqrt(p * (1 - p) / sims)
