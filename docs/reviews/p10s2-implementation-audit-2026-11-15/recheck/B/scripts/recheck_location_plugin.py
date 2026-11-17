"""pytest plugin for re-check B (R5b): makes the location-based test guard behave as it would in the real repository (outside every temporary root) while the clone itself lives under /private/tmp.
Only the pytest base temporary directory and $RECHECK_TMP count as temporary. Nothing else is changed."""
import os
from pathlib import Path


def pytest_configure(config):  # noqa: ANN001, ANN201
    from studies.p10s2 import core

    roots = [Path(str(config.option.basetemp)).resolve(), Path(os.environ["RECHECK_TMP"]).resolve()]
    core.is_temporary = lambda p: any(Path(p).resolve().is_relative_to(r) for r in roots)
