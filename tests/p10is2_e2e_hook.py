# ruff: noqa: E501
"""The child side of the end-to-end launch tests: what the fake ``uv`` executes instead of ``uv run ... python -m <module> <args>``. It imports the study from the repository the launch script ran in (the current
directory), installs the download and teacher fakes of ``p10is2_e2e_world`` and then runs the module exactly as ``python -m`` would."""

import os
import runpy
import sys

repo = os.getcwd()
sys.path.insert(0, repo)
sys.path.append(os.environ["E2E_SRC"])
import studies  # noqa: E402

studies.__path__.append(os.path.join(os.environ["E2E_ROOT"], "studies"))  # P10-S2 and the other earlier studies' code (immutable, not copied) resolve from the main checkout; studies.p10is2 comes from the repository first
import studies.p10is2.partq.real_stages  # noqa: E402, F401  (the study's modules come from the repository, before anything else puts another checkout on the path)

sys.path.append(os.environ["E2E_TESTS"])
import p10is2_e2e_world  # noqa: E402

p10is2_e2e_world.install()
module = sys.argv[1]
sys.argv = [module, *sys.argv[2:]]
runpy.run_module(module, run_name="__main__", alter_sys=True)
