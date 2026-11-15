"""A7 (auditor, Opus 5.5): checkpoint restoration (straight vs snapshot-restore-continue, bit for bit) for
arms the implementer's gate does not cover (it checks N and BB only), on rehearsal draw 2 at 4,096 /
16,384 slots, 2 x 24 updates, with the implementer's own job builder and check. No loss or accuracy is
read out.
"""
import argparse
import sys
from pathlib import Path

from studies.p9i import core, stages, train

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
train.configure()
args = argparse.Namespace(mode="rehearsal", draw=2, dry=False, synthetic_backbone=False, experiments_root=str(ROOT), updates=48, calibration=None)
study = stages.study_data(args)
for arm, slots in (("A4E", 4096), ("W7", 4096), ("E7", 16384), ("A4", 16384), ("D7", 16384), ("BB-D", 4096), ("BB-0", 4096), ("R1", 4096), ("R2", 4096), ("BB", 16384)):
    cell = core.make_cell(arm, slots)
    job = stages.build_job(args, cell, study, SCRATCH / f"{arm}-{slots}", 48, snapshots=(), mode="rehearsal")
    r = train.checkpoint_restoration_check(job, 24)
    print(f"{arm:5} {slots:6} identical={r['identical']} tensors={r['tensors_compared']} mismatches={r['mismatches'][:3]}")
