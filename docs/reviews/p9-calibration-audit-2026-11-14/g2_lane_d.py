"""Audit item 4: Lane D no-memory counts (B101) recomputed with the auditor's own forward and scorer."""

import json

import _common as c
from g2_check import nomem


def main():
    s = c.study()
    bb = c.backbone("b101")
    rec = {r["name"]: r["correct"] for r in json.loads((c.RUN / "calibration.json").read_text())["controls"]["g2"]["lane_d"]["results"]}
    out = {}
    for name in ("lane_d_a_A", "lane_d_a_B", "lane_d_b_A", "lane_d_b_B"):
        tok = s.streams[name].tokens
        out[name] = {"mine": nomem(bb, tok), "facts": len(tok) * 8, "recorded": rec[name]}
    print(json.dumps(out))
    (c.OUT / "g2_lane_d.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
