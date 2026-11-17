"""Recheck script r6 (Claude Opus 5.5 auditor; not Astra review). M5: in a source-only copy of f1e8ebb (git archive), rewrite
configs/p10s1_capacity.toml as `set-cap` and `set-generation-cap` would (the code's own render_config_toml, cap 23 h, a
measured generation cap), so the config-dependent tests can be run against a post-freeze-like config.
  <worktree venv python> -I r6_m5_postfreeze_config.py <copy root>
"""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from studies.p10s1 import core  # noqa: E402
p = Path(sys.argv[1]) / core.DEFAULT_CONFIG
gen = {"cap_seconds": 420.0, "provisional": False, "table_facts": 32768, "source": "measured", "measured_seconds": 200.0, "manifest_sha256": "a" * 64}
p.write_text(core.render_config_toml(23.0, gen), encoding="utf-8")
core.load_config(p)
print("config rewritten: cap_hours 23.0, generation measured", core.generation_settings(p))
