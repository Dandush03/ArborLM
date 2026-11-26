# ruff: noqa: E501
"""The R2 set of fix round 4: the fix-round-3 set (``r2_fix3_set.fix3_set``, 40 lineages) with the six repaired shapes of ``lineages_r2_fix4`` in place of the shapes they supersede.
Which of the 40 stay is decided in ``manifests/r2_fix4_survivors.json`` (status SURVIVES or NOT_REGISTERED); this module only builds the shapes. Nothing here touches ``core.REGISTRY``."""

from __future__ import annotations

from studies.m0.core import Lineage


def fix4_set() -> dict[str, Lineage]:
    from studies.m0.lineages_r2_fix3 import load_fix3  # noqa: F401  (registers the fix-3 shapes)
    from studies.m0.lineages_r2_fix4 import load_fix4
    from studies.m0.r2_fix3_set import fix3_set

    out = dict(fix3_set())
    for x in load_fix4():
        if x.id not in out:
            raise KeyError(x.id)
        out[x.id] = x
    return dict(sorted(out.items()))
