# ruff: noqa: E501
"""Installs the tiny Part T world in every child process of the launch tests (a no-op unless the launch test's environment is set). Test support only."""

import os
import sys

if os.environ.get("E2E_ROOT") and os.path.isdir(os.path.join(os.getcwd(), "studies", "p10is2")):
    sys.path.insert(0, os.getcwd())
    sys.path.append(os.environ["E2E_SRC"])
    sys.path.append(os.environ["E2E_TESTS"])
    import studies

    studies.__path__.append(os.path.join(os.environ["E2E_ROOT"], "studies"))  # P10-S2's code (immutable, not copied) resolves from the main checkout; studies.p10is2 comes from the repository first
    import p10is2_partt_e2e_world

    p10is2_partt_e2e_world.install()
