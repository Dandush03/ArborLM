# Auditor's own arithmetic for the C1/C2 addendum cost (projection only).
import math
n = 500
rate = (0.8, 2.6)          # min per 1,000 single answers (ADR 13.3: 1.6-5.2 min / 2,000 answers)
second = (1.0, 1.5)        # second-answer weight
def equiv(w):  # C1 2n + C2 2n + S_B^C n
    return n + n*w + n + n*w + n
eq = (equiv(second[0]), equiv(second[1]))
cell = (eq[0]*rate[0]/1000, eq[1]*rate[1]/1000)
print("equivalents", eq, "min per arm-cell", cell)
cells = 10
rep_router = (1.8, 7.5)
for router in (True, False):
    rep = (cells*cell[0] + (rep_router[0] if router else 0), cells*cell[1] + (rep_router[1] if router else 0))
    s0 = (cell[0]/60, cell[1]/60)
    print("router" if router else "no router", "per replicate h", [round(x/60,4) for x in rep], "stage0 h", [round(x,4) for x in s0])
    for nrep in (4, 3):
        run = (nrep*rep[0]/60 + s0[0], nrep*rep[1]/60 + s0[1])
        add = (2*run[0], 2*run[1])
        print(f"  {nrep} reps: run {run[0]:.3f}-{run[1]:.3f}  added to R {add[0]:.3f}-{add[1]:.3f}")
    base = {1:(4,20.28,54.74),2:(3,15.39,41.46),3:(4,16.01,46.41),4:(3,12.19,35.21)}
    for rung,(nr,lo,hi) in base.items():
        run = (nr*rep[0]/60 + s0[0], nr*rep[1]/60 + s0[1])
        lo2, hi2 = lo+2*run[0], hi+2*run[1]
        out=[]
        for cap,P in ((36,3.5),(36,7.0),(72,3.5),(72,7.0)):
            lim=(cap-P)/2
            x=(lim-lo2)/(hi2-lo2)
            xs = "no" if x<0 else ("all" if x>=1 else f"{math.floor(x*100)/100:.2f}")
            xo=(lim-lo)/(hi-lo); xos="no" if xo<0 else f"{math.floor(xo*100)/100:.2f}"
            out.append(f"{cap}h/P{P}: x<={xs} (was {xos})")
        print(f"  rung {rung}: R {lo2:.2f}-{hi2:.2f}  ", "; ".join(out))
