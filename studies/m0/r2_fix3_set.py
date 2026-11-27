# ruff: noqa: E501
"""The R2 lineage sets of fix round 3: ``current_set`` (what the registries held before this round, as the audit read it) and ``fix3_set`` (after this round).

R-12: a lineage marked NOT REGISTERED is excluded everywhere (cluster map, G, fixtures, shape list, capacity). ``deferred_acceptance_partner`` is excluded in both sets; ``chip_toppling`` only in ``fix3_set``.
Nothing here touches ``core.REGISTRY``.
"""

from __future__ import annotations

from studies.m0.core import Lineage, lineages_of

NOT_REGISTERED: dict[str, str] = {
    "R2.deferred_acceptance_partner": (
        "audit 3 and the rev2 manifest: no construction frees the lineage from the tells (the responder-proposing stable partner 0.68-0.77, own first choice 0.46-0.56); NOT REGISTERED since fix round 2, "
        "excluded here everywhere (ruling R-12)."
    ),
    "R2.chip_toppling": (
        "audit 3: a closed form (the Dirichlet Green's function of the path with the final row fixed by conservation and the first moment) answers it on 0.98-1.00 of items for both remaining shapes, "
        "which is the reason fix round 2 gave for dropping `final` and `lost`. No rule variant tried in this round removes that: the topple counts solve one linear system whose right-hand side is fixed by the "
        "two conserved quantities of the rule, on a path, a ring or with cell-dependent thresholds alike. NOT REGISTERED; excluded everywhere (ruling R-12)."
    ),
}
EXCLUDED_BEFORE = {"R2.deferred_acceptance_partner"}


def current_set() -> dict[str, Lineage]:
    """Core R2 with a core shape replaced where a rev2 shape supersedes it, plus the batch-1 lineages not superseded, plus the rev2 shapes; deferred acceptance excluded."""
    from studies.m0.lineages_r2_common import load_batch1
    from studies.m0.lineages_r2_rev2 import SUPERSEDES, load_rev2

    rev2 = load_rev2()
    superseded = set(SUPERSEDES.values())
    core = [x for x in lineages_of("R2") if x.id not in superseded]
    b1 = [x for x in load_batch1() if x.id not in superseded]
    out = {x.id: x for x in [*core, *b1, *rev2] if x.id not in EXCLUDED_BEFORE}
    return dict(sorted(out.items()))


def fix3_set() -> dict[str, Lineage]:
    from studies.m0.lineages_r2_fix3 import load_fix3

    out = dict(current_set())
    for x in load_fix3():
        out[x.id] = x
    for lid in NOT_REGISTERED:
        out.pop(lid, None)
    return dict(sorted(out.items()))
