# Auditor toy (confirmation of ADR-0017 rev 3): how long is the usage hinge active
# purely because u_0 = first batch's u-bar, for a memory whose selections are
# perfectly spread (uniform random)? N=16384, F=8192, b=128/F, 128 answer sites per
# update, 8 hard selections per site; optional soft mass pi_out on 56 other candidates.
import math, random
N, F = 16384, 8192
b = 128 / F
lnM = math.log(min(N, 8 * F) / 2)
def batch(rng, pi_out):
    u = [0.0] * N
    for _ in range(128):
        c = rng.sample(range(N), 64)
        for s in c[:8]:
            u[s] += 1.0
        for s in c[8:]:
            u[s] += pi_out
    t = sum(u)
    return [x / t for x in u]
def H(u):
    return -sum(x * math.log(x) for x in u if x > 0)
for pi_out in (0.0, 0.1):
    for init in ("first_batch", "uniform"):
        rng = random.Random(179001)
        ub = batch(rng, pi_out)
        u = ub[:] if init == "first_batch" else [1.0 / N] * N
        first_off = None
        for t in range(1, 2049):
            ub = batch(rng, pi_out)
            u = [(1 - b) * a + b * c for a, c in zip(u, ub)]
            if first_off is None and H(u) >= lnM:
                first_off = t
            if t in (1, 32, 64, 128, 256) or (first_off == t):
                print({"pi_out": pi_out, "u0": init, "t": t, "H_u": round(H(u), 3), "lnM": round(lnM, 3), "hinge_active": H(u) < lnM})
            if first_off is not None and t >= 256:
                break
        print({"pi_out": pi_out, "u0": init, "first_update_hinge_off": first_off, "of_U_at_E32": 2048})
