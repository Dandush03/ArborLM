"""Audit A, check 1: the seed table of ADR-0022 section 9 recomputed from the ADR text and compared with studies/p10s2/core.py;
probes of gate G9 (vacuity, mode confusion, unlisted uses). Written by the auditor (Claude Opus 5.5); imports only core/gates (not analysis modules).
Run from the pinned tree:  <python> <this file>
"""

import re
import sys
from pathlib import Path

PIN = Path.cwd()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
adr = (PIN / "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md").read_text()

out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


# --- 1. the seed table from the ADR text ---------------------------------------------------------------------------------------------------
m = re.search(r"Seeds: replicate bases ([\d, ]+), each with these offsets:", adr)
bases = [int(x.replace(",", "")) for x in re.findall(r"\d{3},?\d{3}", m.group(1))] if m else []
# the ADR writes 220001, 220101, ... without thousands separators
bases = [int(x) for x in re.findall(r"\d{6}", m.group(1))] if m else []
offsets = sorted(int(x) for x in re.findall(r"^  - \+(\d+) ", adr, flags=re.M))
partition = int(re.search(r"Partition seed (\d{6})", adr).group(1))
streams = {int(s): name for s, name in re.findall(r"(2209\d\d) (the [^,;]+)", adr)}
further = {int(s) for s in re.findall(r"^  - (2209\d\d),", adr, flags=re.M)}
say(f"ADR replicate bases: {bases}")
say(f"ADR offsets: {offsets}")
say(f"ADR partition seed: {partition}; streams named in the text: {sorted(streams)}; further listed: {sorted(further)}")
adr_registered = {b + o for b in bases for o in offsets}
adr_data = {partition, *range(220902, 220911)}
adr_cal = {221001 + 100 * i + o for i in range(10) for o in offsets}
adr_reh = {222001 + 100 * i + o for i in range(10) for o in offsets}

from studies.p10s2 import core  # noqa: E402

code_registered = set(core.allowed_seeds("registered-run"))
code_data = set(core.allowed_seeds("registered-data"))
code_cal = set(core.allowed_seeds("calibration"))
code_reh = set(core.allowed_seeds("rehearsal"))
code_test = set(core.allowed_seeds("test"))
say(f"registered-run set equal to ADR: {code_registered == adr_registered} ({len(code_registered)} seeds)")
say(f"registered-data set equal to ADR 220901-220910: {code_data == adr_data}")
say(f"calibration set equal to 221001+100i+offset: {code_cal == adr_cal}; inside 221001-221999: {all(221001 <= s <= 221999 for s in code_cal)}")
say(f"rehearsal set equal to 222001+100i+offset: {code_reh == adr_reh}; inside 222001-222999: {all(222001 <= s <= 222999 for s in code_reh)}")
say(f"test set is 229001-229999: {code_test == set(range(229001, 230000))}")
names = core.partition_seeds("registered-data")
want_names = {220901: "partition", 220902: "q_split", 220903: "source_sample", 220904: "ablation_subsample", 220905: "gen_windows", 220906: "bootstrap", 220907: "seen_items", 220908: "timing_items", 220909: "tokenizer_record", 220910: "random_id_sequences"}
say(f"partition-side names match the ADR uses: {all(names[n] == s for s, n in want_names.items())}")
listed = adr_registered | adr_data
say(f"every listed registered seed in 220001-228999: {all(220001 <= s <= 228999 for s in listed)}")
say(f"no listed registered seed in calibration/rehearsal/test ranges: {not any(221001 <= s <= 221999 or 222001 <= s <= 222999 or 229001 <= s <= 229999 for s in listed)}")
say(f"modes disjoint: reg&cal={bool(code_registered & code_cal)} reg&reh={bool(code_registered & code_reh)} reg&test={bool(code_registered & code_test)} cal&reh={bool(code_cal & code_reh)} data&reg={bool(code_data & code_registered)}")
tp = set(core.partition_seeds("test").values())
say(f"test-mode stand-ins for partition seeds {sorted(tp)} inside test range: {tp <= code_test}")

# foreign ranges against ADR-0021 6.3 and ADR-0022 9 (by eye in the audit; here recomputed membership)
fr = core.foreign_ranges()
allmine = code_registered | code_data | code_cal | code_reh | code_test
hits = sorted(s for s in allmine if core.foreign_seed_hit(s) is not None)
say(f"S2 seeds (all modes) inside a listed foreign range: {hits}")
cfg = core.config_seeds()
say(f"P1-P8 (and S0/S1/P9) config seeds read: {len(cfg)}; intersect S2 sets: {sorted(cfg & allmine)}")
# derived +1000k collisions of foreign initialization seeds with S2 listed seeds (informational)
small_foreign = [s for spans in fr.values() for lo, hi in spans for s in range(lo, hi + 1) if hi < 10000]
coll = sorted({(f, (s - f) // 1000) for f in small_foreign for s in allmine if s > f and (s - f) % 1000 == 0})
say(f"foreign small seeds f with f + 1000k equal to an S2 seed (k shown; informational): {coll[:12]} ... total {len(coll)}; min k = {min((k for _, k in coll), default=None)}")

# --- 2. gate G9 probes ---------------------------------------------------------------------------------------------------------------------
core.reset_seed_record()
g = core.seed_gate(core.seed_record(), [])
say(f"G9 probe vacuity: seed_gate(no records, no planned) ok = {g['ok']}  (expected by the ADR: cannot pass vacuously)")
core.reset_seed_record()
core.seeded_generator(229001, "stand-in drawn inside a registered process", "test")
core.seeded_generator(220001, "stage-1 store", "registered-run")
g = core.seed_gate(core.seed_record(), core.SeedPlan("registered-run", 0).planned())
say(f"G9 probe mode confusion: a 'test' use recorded in a registered process passes: ok = {g['ok']}")
core.reset_seed_record()
core.seeded_generator(220910, "equivalence injection vector (unlisted use)", "registered-data")
g = core.seed_gate(core.seed_record(), [])
say(f"G9 probe unlisted use of 220910 for the injection vector: ok = {g['ok']}")
core.reset_seed_record()
try:
    core.seeded_generator(220901, "partition seed in registered-run", "registered-run")
    say("partition seed accepted in registered-run mode: UNEXPECTED")
except core.SeedRefused:
    say("partition seed refused in registered-run mode: as required")
try:
    core.seeded_generator(221001, "calibration seed in registered-run", "registered-run")
    say("calibration seed accepted in registered-run mode: UNEXPECTED")
except core.SeedRefused:
    say("calibration seed refused in registered-run mode: as required")
core.reset_seed_record()
g = core.seed_gate([core.SeedUse(220311, "oracle hash", "registered-run")], [])
say(f"the +10 oracle-code seed is never recorded (the hash seeds no generator); G9 cannot see it; a manual record of 220311 passes: {g['ok']}")

# the source check (G9's second half)
from studies.p10s2 import gates  # noqa: E402

sc = gates.source_check()
say(f"G9 source check on the pinned package: ok = {sc['ok']}; problems = {sc['problems'][:5]}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
