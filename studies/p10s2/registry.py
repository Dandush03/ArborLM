# ruff: noqa: E501
"""The cell registry (ADR-0022 section 13.1): 18 trained cells per replicate, with their units of U, their dependencies and the scored-only and assembled items.

Group, cells, units of U per replicate: ST1 (two orders) 2 cells 2 units; M-append-frozen 2/2; M-ii (64-row batches, about twice the cost per update) 2/4; M-seq 2/2; M-joint 1/2; E-table
(each capability) 2/2; MA-gold (each capability) 2/2; LoRA-1 and L-seq 4/4; L-joint 1/2. Trained cells per replicate: 18 (16 store-type units and 6 LoRA units). Four replicates: 72 trained
cells; three: 54. Assembled without training: M-i-separate and L-sep.
"""

from dataclasses import dataclass

from . import core

STORE_GROUPS = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "ETABLE", "MAGOLD")
LORA_GROUPS = ("LORA1", "LSEQ", "LJOINT")
GROUP_NAMES = {"ST1": "ST1", "MAF": "M-append-frozen", "MII": "M-ii", "MSEQ": "M-seq", "MJOINT": "M-joint", "ETABLE": "E-table", "MAGOLD": "MA-gold", "LORA1": "LoRA-1", "LSEQ": "L-seq", "LJOINT": "L-joint"}
UNITS = {"ST1": 1, "MAF": 1, "MII": 2, "MSEQ": 1, "MJOINT": 2, "ETABLE": 1, "MAGOLD": 1, "LORA1": 1, "LSEQ": 1, "LJOINT": 2}  # units of U per cell
PER_ORDER = ("ST1", "MAF", "MII", "MSEQ", "LORA1", "LSEQ")
PER_CAPABILITY = ("ETABLE", "MAGOLD")
SINGLE = ("MJOINT", "LJOINT")
MEMORY_CELL_GROUPS = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD")  # the 11 memory cells per replicate that carry the five ablations (E-table has none)


@dataclass(frozen=True)
class Cell:
    replicate: int
    group: str
    variant: str  # order "AB"/"BA", capability "A"/"B", or "-" for the single cells

    @property
    def label(self) -> str:
        return f"r{self.replicate}/{self.group}/{self.variant}"

    @property
    def units(self) -> int:
        return UNITS[self.group]

    @property
    def is_lora(self) -> bool:
        return self.group in LORA_GROUPS

    @property
    def depends_on(self) -> str | None:
        """The cell whose snapshot this one continues (a failed parent stops its dependants; nothing is re-run with changed settings)."""
        parent = {"MAF": "ST1", "MII": "MAF", "MSEQ": "ST1", "LSEQ": "LORA1"}.get(self.group)
        return f"r{self.replicate}/{parent}/{self.variant}" if parent else None


def parse_label(label: str) -> Cell:
    r, g, v = label.split("/")
    if not r.startswith("r") or g not in UNITS:
        raise ValueError(f"not a cell label: {label!r}")
    return Cell(int(r[1:]), g, v)


def replicate_cells(replicate: int) -> list[Cell]:
    out: list[Cell] = []
    for g in (*PER_ORDER, *PER_CAPABILITY, *SINGLE):
        variants = core.ORDERS if g in PER_ORDER else (core.TASKS if g in PER_CAPABILITY else ("-",))
        out += [Cell(replicate, g, v) for v in variants]
    return out


def registry(replicates: int) -> list[Cell]:
    if replicates not in (1, 2, 3, 4):
        raise ValueError("a design has 1 to 4 replicates (3 or 4 when registered)")
    return [c for r in range(replicates) for c in replicate_cells(r)]


def units_per_replicate() -> dict[str, int]:
    store = sum(c.units for c in replicate_cells(0) if not c.is_lora)
    lora = sum(c.units for c in replicate_cells(0) if c.is_lora)
    return {"store": store, "lora": lora, "total": store + lora}


def memory_cells(replicate: int) -> list[Cell]:
    return [c for c in replicate_cells(replicate) if c.group in MEMORY_CELL_GROUPS]
