"""Hand-worked cases (values computed by hand in the comments) against studies/p10s1/classes.py.
Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c9_hand_cases.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json, math, sys
from studies.p10s1 import classes as C, core

N = 8192
def a_for_i(i):  # bisection on the Fano bound, own code
    lo, hi = 0.0, 1.0
    for _ in range(80):
        m = (lo + hi) / 2
        e = 1 - m
        h = 0 if e in (0, 1) else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
        lo, hi = (m, hi) if 5 - h - e * math.log2(31) < i else (lo, m)
    return (lo + hi) / 2
def obs(i):
    u = math.ceil(a_for_i(i) * N)
    return C.PanelObs(n=N, correct=u, useful=u, disabled=256, shuffled=256)
out = {}
# u_T: s_prev=2048 with min i 2.5, s_hit=4096 with min i 3.5 -> fraction (3.0-2.5)/(3.5-2.5) ~ 0.5 -> log2 u = 11 + 0.5 = 11.5 -> u ~ 2896.3
va = C.View({1024: obs(1.0), 2048: obs(2.5), 4096: obs(3.5), 8192: obs(4.0)}, 16384, 8192)
vb = C.View({1024: obs(1.2), 2048: obs(2.6), 4096: obs(3.6), 8192: obs(4.1)}, 16384, 8192)
r = C.u_t([va, vb])
m_prev, m_hit = min(va.i(2048), vb.i(2048)), min(va.i(4096), vb.i(4096))
hand = 2 ** (11 + (3.0 - m_prev) / (m_hit - m_prev))
out["u_t"] = {"impl": r.ut._asdict(), "hand": hand, "m_prev": m_prev, "m_hit": m_hit, "equal": abs(r.ut.lo - hand) < 1e-9}
# left censoring: first snapshot already >= 3.0 on both panels -> (0, 1024]
vl = C.View({1024: obs(3.2), 2048: obs(3.5)}, 2048, 8192)
out["left"] = C.u_t([vl, vl]).ut._asdict()
# right censoring: never >= 3.0 -> above U_run
vr = C.View({1024: obs(1.0), 2048: obs(2.9)}, 2048, 8192)
out["right"] = C.u_t([vr, vr]).ut._asdict()
# plateau/loaded: U_run = 49152; i*(24576) = 3.80, i*(49152) = 3.88 -> slope 0.08 <= 0.10 plateaued; i* 3.88 <= 4.0 loaded
vp = C.View({8192: obs(3.5), 24576: obs(3.80), 49152: obs(3.88)}, 49152, 8192)
out["plateau"] = {"i_star_run": vp.i_star(49152)[0], "i_star_half": vp.i_star(24576)[0], "plateaued": vp.plateaued(), "loaded": vp.loaded(), "hand": "plateaued True, loaded True"}
vq = C.View({8192: obs(3.5), 24576: obs(3.80), 49152: obs(3.95)}, 49152, 8192)
out["not_plateaued"] = {"plateaued": vq.plateaued(), "hand": "0.15 > 0.10 -> False"}
# MC: cpu 0.010 -> 0.035 (x3.5), madds x3.94 -> larger multiplier 3.94 -> grid 4.0 -> smaller read at 4 x 8192 = 32768 <= 49152
e = C.mc_pair({"cpu": 0.010, "madds": 1.0}, {"cpu": 0.035, "madds": 3.94}, 8192, 49152, 32768)
out["mc"] = {"impl": e._asdict(), "hand": "OK, small at 32768, large at 8192, multiplier 3.94"}
e2 = C.mc_pair({"cpu": 0.014, "madds": 1.0}, {"cpu": 0.06, "madds": 3.99}, 8192, 32768, 16384)
out["mc_short"] = {"impl": e2._asdict(), "hand": "ratio 4.29 -> grid 6.0 -> 49152 > 32768 -> MC-SHORT"}
# CAPACITY by hand: small loaded at i*=3.88 (plateau 0.08); large at U_P 4.75: d_mu = 4.75 - i_s(UP)=3.5 -> 1.25; d_sat = 4.75 - 3.88 = 0.87; d_sat - 2*0.08 = 0.71 >= 0.5;
# d_mc with small at 32768 (i=3.84) = 0.91 -> CAPACITY
small = C.View({8192: obs(3.5), 24576: obs(3.80), 32768: obs(3.84), 49152: obs(3.88)}, 49152, 8192)
large = C.View({8192: obs(4.75), 16384: obs(4.8), 32768: obs(4.85)}, 32768, 8192)
res = C.capacity_panel(small, large, C.McEntry("OK", 32768, 8192, 3.94, "small"), ref_ok=True)
out["capacity_by_hand"] = {"verdict": res.verdict, "delta_mu": res.detail["delta_mu"], "delta_sat": res.detail["delta_sat"], "delta_mc": res.detail["delta_mc"], "hand": "CAPACITY (1.25, 0.87, 0.91)"}
json.dump(out, sys.stdout, indent=1, default=str); print()
