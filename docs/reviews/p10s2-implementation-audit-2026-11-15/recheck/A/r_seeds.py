"""Re-check A: the seed table recomputed from the ADR text and its addenda (220911 by the combined-tasks addendum, 220912 by the
lead's ruling on A-M8, 220906 drawn in the analysis stage only), compared with studies/p10s2/core.py and the config; the predecessor's
G9 probes repeated (empty record, wrong mode label, unlisted use, +10 code seed). No registered seed is passed to a generator here:
records are built as SeedUse data; generators are made only with test seeds. Written by the re-check auditor (Claude Opus 5.5).
Run:  <python> -I <this file> <pinned tree>
"""

import re
import sys
import tomllib
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


adr = (PIN / "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read_text()
add = (PIN / "docs/decisions/ADR-0022-addendum-combined-tasks.md").read_text()
bases = [int(x) for x in re.findall(r"\d{6}", re.search(r"Seeds: replicate bases ([\d, ]+), each", adr).group(1))]
offsets = sorted(int(x) for x in re.findall(r"^  - \+(\d+) ", adr, flags=re.M))
listed_9 = {int(s) for s in re.findall(r"(2209\d\d)", adr[adr.index("## 9. Replicates"):adr.index("## 10. Measurements")])}
s911 = "220911" in add and "C1 pairing" in add
s912 = re.search(r"own listed seed \*\*220912\*\*", adr) is not None
g9list = re.search(r"G9's list is (2209\d\d)–(2209\d\d)", adr)
boot = "220906 is drawn in the analysis stage and nowhere else" in adr
say(f"ADR: bases {bases}; offsets {offsets}; 2209xx seeds named in section 9: {sorted(listed_9)}; 220911 in the addendum: {s911}; 220912 ruling: {s912}; G9 list {g9list.groups() if g9list else None}; 220906 analysis-only ruling: {boot}")
want_data = {220901, *range(220902, 220913)} - {220906}
want_reg = {b + o for b in bases for o in offsets}

from studies.p10s2 import core  # noqa: E402

cfg = tomllib.loads((PIN / "configs/p10s2_transfer.toml").read_text())["seeds"]
say(f"config partition_streams {cfg['partition_streams']} == 220902..220912: {cfg['partition_streams'] == list(range(220902, 220913))}")
say(f"stream names in order: {list(core.PARTITION_STREAMS.items())}")
say(f"registered-run set == ADR (44): {set(core.allowed_seeds('registered-run')) == want_reg}")
say(f"registered-data set == 220901-220912 minus 220906: {set(core.allowed_seeds('registered-data')) == want_data}")
say(f"registered-analysis set == {{220906}}: {set(core.allowed_seeds('registered-analysis')) == {220906}}")
say(f"planned_seeds('registered-data') == 11 data seeds: {core.planned_seeds('registered-data') == sorted(want_data)}")
say(f"planned_seeds('registered-run') covers all 4 replicates incl. +10: {set(core.planned_seeds('registered-run')) == want_reg}")
say(f"listed_registered_seeds == 44 + 220901..220912: {set(core.listed_registered_seeds()) == want_reg | set(range(220901, 220913))}")
allm = set().union(*(core.allowed_seeds(m) for m in ("registered-run", "registered-data", "registered-analysis", "calibration", "rehearsal", "test")))
say(f"S2 seeds (all modes) in a foreign range: {sorted(s for s in allm if core.foreign_seed_hit(s, core.config_seeds()))}")
say(f"220911, 220912 outside calibration/rehearsal/test ranges and in 220001-228999: {all(220001 <= s <= 228999 and not (221001 <= s <= 222999 or 229001 <= s) for s in (220911, 220912))}")
U = core.SeedUse
# --- G9 probes (predecessor's demonstrations), strict form as gates.g9 calls it ----------------------------------------------------------------
g = core.seed_gate([], [], stage_mode="registered-run")
say(f"[G9 empty] seed_gate([], [], stage_mode='registered-run') ok = {g['ok']}; problems = {g['problems']}")
g = core.seed_gate([], [])
say(f"[G9 empty, legacy call without stage_mode] ok = {g['ok']} (the weaker form is kept in core for callers without a stage)")
recs = [U(229001, "stand-in inside a registered process", "test"), U(220001, "stage-1 store", "registered-run")]
g = core.seed_gate(recs, core.planned_seeds("registered-run"), stage_mode="registered-run", allow_partial=True)
say(f"[G9 wrong mode label] a 'test' use next to a registered one, strict: ok = {g['ok']}; first problem: {g['problems'][:1]}")
g = core.seed_gate([U(220910, "equivalence injection vector", "registered-data")], core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data", allow_partial=True)
say(f"[G9 220910 for the injection vector] passes as a seed (purpose is not checked against the listed use): ok = {g['ok']}")
g = core.seed_gate([U(220906, "bootstrap", "registered-data")], core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data", allow_partial=True)
say(f"[G9 220906 in the data step] ok = {g['ok']}; {g['problems'][:2]}")
full = [U(s, n, "registered-data") for n, s in core.partition_seeds("registered-data").items()]
g = core.seed_gate(full, core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data", extra_foreign=core.config_seeds())
say(f"[G9 data step, all eleven recorded once each] ok = {g['ok']}")
g = core.seed_gate(full[:-1], core.planned_seeds("registered-data"), planned_mode="registered-data", stage_mode="registered-data")
say(f"[G9 data step, one of the eleven missing, allow_partial False as datagen calls it] ok = {g['ok']}; {g['problems'][-1:]}")
core.reset_seed_record()
p = core.SeedPlan("test", 0)
p.code_seed()
say(f"[+10 code seed] recorded uses after SeedPlan('test',0).code_seed(): {[(u.seed, u.kind) for u in core.seed_record()]}")
try:
    core.partition_gen("registered-data", "bootstrap")
    say("[refusal] bootstrap in registered-data: ACCEPTED (unexpected)")
except core.SeedRefused as e:
    say(f"[refusal] bootstrap in registered-data refused before any generator is made: {e}")
for m, s in (("registered-run", 220901), ("registered-run", 221001), ("registered-data", 220001)):
    try:
        core.seeded_generator(s, "probe", m)
        say(f"[refusal] {s} in {m}: ACCEPTED (unexpected)")
    except core.SeedRefused:
        say(f"[refusal] {s} in {m}: refused")
from studies.p10s2 import gates  # noqa: E402

sc = gates.source_check()
say(f"[G9 source check] ok = {sc['ok']}; problems = {sc['problems'][:3]}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
