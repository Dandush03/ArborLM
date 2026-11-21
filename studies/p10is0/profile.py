# ruff: noqa: E501
"""P10IS0 profiles (ADR-0023 stage 2): ``registered`` (real sizes, the registry's seeds) and ``test`` (the synthetic tiny configuration: exposures divided by 64, 128 and 256 facts for the 2,048- and 8,192-fact sets, a random synthetic
backbone, the test-range seed bases of ``core._profiled`` and the named test initialisations). A run directory holding the marker file ``TEST_PROFILE`` selects ``test``; no registered seed, real draw or real backbone is read under it, and
the registered plan builder is the same code with only the seed sets (and sizes) changed (a test diffs the two plans)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

MARKER = "TEST_PROFILE"


@dataclass(frozen=True)
class Profile:
    name: str = "registered"
    scale: int = 1
    facts: Mapping[int, int] = field(default_factory=dict)
    diag: tuple[int, int, int] | None = None
    min_timing_updates: int | None = None

    @property
    def tiny(self) -> bool:
        return self.name == "test"

    def facts_of(self, real: int) -> int:
        return self.facts.get(real, real)

    def exp(self, exposures: int) -> int:
        """Exposures per fact in this profile (registered: unchanged; test: divided by the scale, at least 1)."""
        return max(1, exposures // self.scale)


REGISTERED = Profile()
TEST = Profile("test", 64, {2048: 128, 8192: 256}, (2, 16, 64), 16)


def by_name(name: str) -> Profile:
    if name == "registered":
        return REGISTERED
    if name == "test":
        return TEST
    raise ValueError(f"unknown profile {name!r}")


def profile_of(run_dir: Path | str | None) -> Profile:
    return TEST if run_dir is not None and (Path(run_dir) / MARKER).is_file() else REGISTERED
