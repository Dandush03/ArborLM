# ruff: noqa: E501
"""R2 cluster map (lead ruling R-2): the AUDITOR's strict map is the working map (AUDIT_M0_R2_1.md section 2). Disagreements are written beside it and do NOT un-merge.

The map covers the 16 existing R2 lineages, the 26 batch-1 lineages (ids unchanged by the rev2 shapes) and the two new shape ids of existing lineages. Borderline groups
("strictest") are listed, not merged. Nothing here registers anything. Self-checked, not independent review.
"""

from __future__ import annotations

# (auditor, strict reading) merged groups of lineage ids; every other lineage is its own cluster
STRICT_MERGES: list[tuple[str, ...]] = [
    ("R2.sort_list", "R2.kth_smallest"),  # same procedure (sort); only the final question differs (merged under both readings)
    ("R2.count_letter", "R2.count_divisible"),  # a linear scan with a predicate counter
    ("R2.to_base", "R2.from_base"),  # inverse directions of positional conversion
    ("R2.permutation_power", "R2.modular_power"),  # iterate a map t times from a start; both fastest by reducing t
]

# shape ids that are not lineages: they belong to the cluster of the lineage they revise
SHAPE_OF: dict[str, str] = {
    "R2.string_rewrite_nonidentity": "R2.string_rewrite",
    "R2.to_base_wide": "R2.to_base",
}

# the two further merges implied by the BATCH AUTHOR's own rejection log (auditor section 8): reported as the strictest count, NOT applied to the working map
STRICTEST_EXTRA: list[tuple[str, ...]] = [
    ("R2.subtraction_game", "R2.coin_change_min"),  # log: 'subset sum / ways / stair paths = coin_change_min (capacity table)'; a win/lose cell rule over the same table of amounts
    ("R2.dictionary_rank", "R2.to_base"),  # log: 'factorial base conversion = a shape of the base-conversion lineages'
]

# the author's own earlier 'strictest' reading of the existing list, kept for the record (the auditor keeps them apart; not applied)
AUTHOR_EARLIER_BORDERLINE: list[tuple[str, ...]] = [("R2.list_ops", "R2.stack_machine")]

# renamed family names (the existing files are not edited; the clash is resolved by this mapping only)
FAMILY_RENAME_BATCH1 = {"numtheory": "numtheory_b1"}

DISAGREEMENTS = """\
Author's notes beside the auditor's strict map (they do not un-merge anything):
1. to_base + from_base. Division gives digits right to left and Horner evaluates left to right, so on the lenient reading they are two procedures; the auditor's strict reading (number system and final question
   are parameters) and the batch's own dictionary_rank (one lineage for rank and unrank) point the same way. No objection to the merge.
2. permutation_power + modular_power. The batch-1 note kept them apart because square-and-multiply applies only to modular_power. The batch's own rejection log ('iterate a stated rule until a condition: the same strict
   procedure as permutation_power and digit_root') is inconsistent with that note, as the auditor says; under that rule digit_root would also join this cluster. digit_root is NOT merged in the working map (the auditor
   keeps it apart); the inconsistency is the author's, to be settled by the lead.
3. count_letter + count_divisible and sort_list + kth_smallest: agreed.
4. list_ops + stack_machine: the author's earlier note merged them on the strictest reading; the auditor keeps them apart (op sets and data structure differ). Not merged here.
5. subtraction_game / coin_change_min and dictionary_rank / base conversion: the author's log implies these merges ('strictest'); the auditor lists them as near misses. They stay apart in the working map and are counted in 'strictest'.
6. Cross-evaluation duplicates (audit section 3) are not clusters of this map (ruling R-7).
"""


def working_ids() -> list[str]:
    """Every R2 lineage id the map covers: the 16 existing, the 26 batch-1 (their rev2 shapes keep the id) and no shape ids."""
    from studies.m0.core import lineages_of
    from studies.m0.lineages_r2_common import load_batch1

    return sorted({x.id for x in lineages_of("R2")} | {x.id for x in load_batch1()})


def _clusters(merges: list[tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    ids = working_ids()
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            x = parent[x]
        return x

    for grp in merges:
        for other in grp[1:]:
            ra, rb = find(grp[0]), find(other)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    out: dict[str, list[str]] = {}
    for i in ids:
        out.setdefault(find(i), []).append(i)
    return {k: tuple(v) for k, v in sorted(out.items())}


def strict_clusters() -> dict[str, tuple[str, ...]]:
    return _clusters(STRICT_MERGES)


def strictest_clusters() -> dict[str, tuple[str, ...]]:
    return _clusters([*STRICT_MERGES, *STRICTEST_EXTRA])


def cluster_of(lineage_id: str) -> str:
    base = SHAPE_OF.get(lineage_id, lineage_id)
    for k, v in strict_clusters().items():
        if base in v:
            return k
    raise KeyError(lineage_id)


def reporting_family(lineage_id: str, family: str, batch1: bool) -> str:
    return FAMILY_RENAME_BATCH1.get(family, family) if batch1 else family
