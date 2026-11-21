# ruff: noqa: E501
"""Paired statistics on the M0 draw (ADR-0033 section 9.1 and 9.2). Standard library and the locked torch only.

Cluster bootstrap stratified by family (or task): clusters are resampled with replacement within each stratum, 10,000
resamples, a registered seed, percentile bounds. Derived statistics (such as the union gain, whose better teacher is
re-chosen in every resample) are recomputed inside every resample. With fewer than 30 clusters the cluster-robust
standard error with a t quantile on (clusters - 1) degrees of freedom replaces the percentile bootstrap.

Readings chosen for the least favourable result (listed as rulings needed in studies/m0/NOTES.md): percentile bounds are
the more extreme order statistic (index floor(p (B + 1)) from each end); the t branch uses the unstratified cluster-robust
standard error (which is not smaller than the stratified one); a linearisation with the better teacher fixed at the
point estimate stands in for the union gain on that branch.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from statistics import NormalDist

import torch

from studies.m0.core import derive_seed

_N = NormalDist()


def t_quantile(p: float, df: int) -> float:
    """Student t quantile by the Cornish-Fisher series in 1/df (accurate for df >= 5; conservative below)."""
    z = _N.inv_cdf(p)
    g1 = (z**3 + z) / 4
    g2 = (5 * z**5 + 16 * z**3 + 3 * z) / 96
    g3 = (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / 384
    return z + g1 / df + g2 / df**2 + g3 / df**3


@dataclass(frozen=True)
class Rec:
    item_id: str
    cluster: str
    stratum: str
    correct: dict[str, int]  # system name -> 0 or 1


@dataclass
class Table:
    """Per-item numeric columns with a cluster and stratum for every item."""

    clusters: list[str]
    strata: list[str]
    cols: dict[str, list[float]]
    _cl: dict[str, torch.Tensor] = field(default_factory=dict, repr=False)

    @classmethod
    def from_recs(cls, recs: Sequence[Rec], systems: Sequence[str]) -> Table:
        cols = {f"c_{s}": [float(r.correct[s]) for r in recs] for s in systems}
        return cls([r.cluster for r in recs], [r.stratum for r in recs], cols)

    def add(self, name: str, values: Sequence[float]) -> None:
        if len(values) != len(self.clusters):
            raise ValueError("column length")
        self.cols[name] = [float(v) for v in values]

    @property
    def n(self) -> int:
        return len(self.clusters)

    def cluster_ids(self) -> list[str]:
        return sorted(set(self.clusters))

    def n_clusters(self) -> int:
        return len(self.cluster_ids())

    def cluster_table(self, names: Sequence[str]) -> tuple[torch.Tensor, list[tuple[str, int, int]]]:
        """Rows = clusters (sorted by stratum, cluster id); columns = [n_items, sum of each named column].
        Also returns [(stratum, first row, last row + 1)] for each stratum."""
        key = {c: s for c, s in zip(self.clusters, self.strata, strict=True)}
        order = sorted(key, key=lambda c: (key[c], c))
        pos = {c: i for i, c in enumerate(order)}
        m = torch.zeros((len(order), 1 + len(names)), dtype=torch.float64)
        for i, c in enumerate(self.clusters):
            row = pos[c]
            m[row, 0] += 1.0
            for j, nm in enumerate(names):
                m[row, 1 + j] += self.cols[nm][i]
        spans: list[tuple[str, int, int]] = []
        start = 0
        for i in range(1, len(order) + 1):
            if i == len(order) or key[order[i]] != key[order[start]]:
                spans.append((key[order[start]], start, i))
                start = i
        return m, spans


def _gen(seed: int, label: str) -> torch.Generator:
    g = torch.Generator()
    g.manual_seed(derive_seed(seed, label) % (2**63 - 1))
    return g


def bootstrap_totals(cl: torch.Tensor, spans: list[tuple[str, int, int]], b: int, seed: int, label: str, chunk_cells: int = 4_000_000) -> torch.Tensor:
    """Stratified cluster bootstrap: returns tensor (b, K) of resampled column totals (column 0 is the item count)."""
    g = _gen(seed, label)
    k = cl.shape[1]
    out = torch.zeros((b, k), dtype=torch.float64)
    chunk = max(1, chunk_cells // max(1, cl.shape[0] * k))
    for lo in range(0, b, chunk):
        hi = min(b, lo + chunk)
        for _, s0, s1 in spans:
            idx = torch.randint(s0, s1, (hi - lo, s1 - s0), generator=g)
            out[lo:hi] += cl[idx].sum(dim=1)
    return out


def lower_bound(samples: torch.Tensor, p: float = 0.05) -> float:
    """The floor(p (B + 1))-th smallest value (1-indexed): the more extreme order statistic (reading: ruling needed)."""
    b = samples.numel()
    k = max(1, math.floor(p * (b + 1)))
    return float(torch.sort(samples).values[k - 1])


def upper_bound(samples: torch.Tensor, p: float = 0.05) -> float:
    b = samples.numel()
    k = max(1, math.floor(p * (b + 1)))
    return float(torch.sort(samples, descending=True).values[k - 1])


def cluster_robust(cl: torch.Tensor, col: int) -> tuple[float, float, int]:
    """Mean of an item-level variable, its cluster-robust standard error (unstratified) and the cluster count."""
    n = float(cl[:, 0].sum())
    s = float(cl[:, col].sum())
    mean = s / n
    g = cl.shape[0]
    ss = float(((cl[:, col] - cl[:, 0] * mean) ** 2).sum())
    se = math.sqrt(ss * g / (g - 1)) / n if g > 1 else float("nan")
    return mean, se, g


@dataclass(frozen=True)
class Interval:
    estimate: float
    lo: float  # two-sided 95 % lower bound, or the one-sided lower bound when ``one_sided``
    hi: float  # two-sided 95 % upper bound (nan when one-sided)
    method: str  # "bootstrap" or "t"
    one_sided: bool = False


# A statistic maps the means of the named columns (tensors of shape (R,)) to a tensor of shape (R,).
Stat = Callable[[dict[str, torch.Tensor]], torch.Tensor]


def interval(
    table: Table,
    names: Sequence[str],
    stat: Stat,
    *,
    linear: str | None,
    one_sided: bool,
    b: int,
    seed: int,
    label: str,
    min_clusters_bootstrap: int = 30,
) -> Interval:
    """Interval of ``stat`` of the column means. ``linear`` names an item-level column whose mean equals the statistic
    when the statistic is linear (used for the t branch); a derived statistic passes a linearisation."""
    cl, spans = table.cluster_table(list(names) + ([linear] if linear and linear not in names else []))
    cols = list(names) + ([linear] if linear and linear not in names else [])

    def means(tot: torch.Tensor) -> dict[str, torch.Tensor]:
        return {nm: tot[:, 1 + j] / tot[:, 0] for j, nm in enumerate(cols)}

    point = float(stat(means(cl.sum(dim=0, keepdim=True)))[0])
    g = cl.shape[0]
    if g < min_clusters_bootstrap:
        if linear is None:
            raise ValueError("t branch needs a linear column")
        _, se, _ = cluster_robust(cl, 1 + cols.index(linear))
        if one_sided:
            return Interval(point, point - t_quantile(0.95, g - 1) * se, float("nan"), "t", True)
        q = t_quantile(0.975, g - 1)
        return Interval(point, point - q * se, point + q * se, "t", False)
    tot = bootstrap_totals(cl, spans, b, seed, label)
    s = stat(means(tot))
    if one_sided:
        return Interval(point, lower_bound(s, 0.05), float("nan"), "bootstrap", True)
    return Interval(point, lower_bound(s, 0.025), upper_bound(s, 0.025), "bootstrap", False)


def _col(name: str) -> str:
    return f"c_{name}"


def score_interval(table: Table, system: str, b: int, seed: int, label: str = "") -> Interval:
    c = _col(system)
    return interval(table, [c], lambda m: m[c], linear=c, one_sided=False, b=b, seed=seed, label=f"score/{system}/{label}")


def paired_difference(table: Table, a: str, bsys: str, b: int, seed: int, one_sided: bool, label: str = "") -> Interval:
    """Score of a minus score of b on identical items (one-sided: the lower 95 % bound L)."""
    ca, cb = _col(a), _col(bsys)
    name = f"d_{a}_{bsys}"
    if name not in table.cols:
        table.add(name, [x - y for x, y in zip(table.cols[ca], table.cols[cb], strict=True)])
    return interval(table, [name], lambda m: m[name], linear=name, one_sided=one_sided, b=b, seed=seed, label=f"diff/{a}/{bsys}/{label}")


@dataclass(frozen=True)
class Discordance:
    share: float  # items on which exactly one of the two is right
    a_only: float
    b_only: float


def discordance(table: Table, a: str, bsys: str) -> Discordance:
    xa, xb = table.cols[_col(a)], table.cols[_col(bsys)]
    n = len(xa)
    ao = sum(1 for x, y in zip(xa, xb, strict=True) if x == 1 and y == 0) / n
    bo = sum(1 for x, y in zip(xa, xb, strict=True) if x == 0 and y == 1) / n
    return Discordance(ao + bo, ao, bo)


@dataclass(frozen=True)
class UnionGain:
    union: float
    better: float
    gain: float
    better_system: str
    lower: Interval


def union_gain(table: Table, t1: str, t2: str, b: int, seed: int, label: str = "") -> UnionGain:
    """U = share of items at least one teacher gets right, B = the better teacher's score, G_U = U - B.
    G_U is recomputed in every resample, including which teacher is the better one."""
    c1, c2 = _col(t1), _col(t2)
    u = f"u_{t1}_{t2}"
    if u not in table.cols:
        table.add(u, [max(x, y) for x, y in zip(table.cols[c1], table.cols[c2], strict=True)])
    s1 = sum(table.cols[c1]) / table.n
    s2 = sum(table.cols[c2]) / table.n
    best = t1 if s1 >= s2 else t2  # ties go to the first teacher named
    cbest = _col(best)
    lin = f"g_{t1}_{t2}"
    if lin not in table.cols:  # linearisation with the better teacher fixed at the point estimate
        table.add(lin, [x - y for x, y in zip(table.cols[u], table.cols[cbest], strict=True)])
    iv = interval(
        table,
        [u, c1, c2],
        lambda m: m[u] - torch.maximum(m[c1], m[c2]),
        linear=lin,
        one_sided=True,
        b=b,
        seed=seed,
        label=f"union/{t1}/{t2}/{label}",
    )
    uu = sum(table.cols[u]) / table.n
    return UnionGain(uu, max(s1, s2), uu - max(s1, s2), best, iv)
