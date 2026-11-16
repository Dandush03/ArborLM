"""C6 (auditor, Opus 5.5) -- synthetic. AdamW (lr 0.003, betas 0.9/0.999, eps 1e-8) second-moment carry-over at the
removal of the address loss in A2 (abrupt, after U_pre) and A3 (linear decay to 0 at U/2).

One scalar parameter, gradient sign random (+/-) each step so the first moment does not accumulate drift; magnitude
G_addr while the address loss is on (scaled by lambda(t) for A3) plus G_ans from the answer loss. Ratio G_addr/G_ans
from c3 (rehearsal draw 0, collapsed state, update 256): wq 0.368/0.0067 = 55, keys 4.105/0.0144 = 285 (lambda = 1);
lambda = 0.1 gives 5.5 and 28.5. Reports the mean |step| after removal relative to a fresh optimizer fed only G_ans.
"""
import math
import random


def run(schedule, g_ans, updates=8192):
    b1, b2, eps, lr = 0.9, 0.999, 1e-8, 0.003
    m = v = 0.0
    steps = []
    rng = random.Random(1)
    for t in range(1, updates + 1):
        g_addr = schedule(t)
        sign = 1 if rng.random() < 0.5 else -1
        g = sign * math.hypot(g_addr, g_ans)
        m = b1 * m + (1 - b1) * g
        v = b2 * v + (1 - b2) * g * g
        mh, vh = m / (1 - b1**t), v / (1 - b2**t)
        steps.append(abs(lr * mh / (math.sqrt(vh) + eps)))
    return steps


U = 8192
fresh = run(lambda t: 0.0, 1.0)
ref = sum(fresh[2000:]) / len(fresh[2000:])
print("fresh-optimizer mean |step| (answer loss only) =", round(ref, 6))
for ratio in (5.5, 28.5, 55, 285):
    for name, sched, start in (
        ("A2 U_pre=1024", lambda t, r=ratio: r if t <= 1024 else 0.0, 1024),
        ("A2 U_pre=2048", lambda t, r=ratio: r if t <= 2048 else 0.0, 2048),
        ("A3 linear to 0 at U/2", lambda t, r=ratio: r * max(0.0, 1 - t / (U / 2)), U // 2),
    ):
        s = run(sched, 1.0)
        after = s[start:]
        rel = [x / ref for x in after]
        # attempt 1 used the first single update with step >= 0.5 x fresh; the residual first moment of the old,
        # large, random-sign gradients makes single steps large right after removal, so it reported 0. Use the
        # 256-update moving average instead.
        win = 256
        avg = [sum(rel[i : i + win]) / win for i in range(0, len(rel) - win + 1)]
        half = next((i for i, x in enumerate(avg) if x >= 0.5), None)
        print(f"ratio {ratio:6.1f} {name:22s}: mean step after removal / fresh = {sum(rel) / len(rel):.3f}; "
              f"updates after removal until step >= 0.5 x fresh: {half if half is not None else '> ' + str(len(rel))} (of {len(rel)})")
