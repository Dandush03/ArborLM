"""Auditor's arithmetic for ADR-0022 rev 5 (stdlib only; no project import). python3 -I arith.py"""
from fractions import Fraction as Fr
# ---- §13.3 per-unit ranges (lo, hi)
store_min=(5,10); lora_min=(8,15); score_min=(1.6,5.2); other_h=(0.9,3.0); fixed_h=(0.3,0.6)
STORE_U, LORA_U, CELLS = 16, 6, 18
def R_train_score(n, U):
    f = 1.0 if U == 2000 else 0.5
    return tuple(n*STORE_U*store_min[i]/60*f + n*LORA_U*lora_min[i]/60*f + n*CELLS*score_min[i]/60 + n*other_h[i] + fixed_h[i] for i in (0,1))
def recompute(n):
    return tuple(n*CELLS*score_min[i]/60 + n*other_h[i] + fixed_h[i] for i in (0,1))
gates = (4*1.6/60, 4*5.2/60 + 0.05)
print("second gates stage h: %.3f-%.3f" % gates)
rungs = {1:(4,2000),2:(3,2000),3:(4,1000),4:(3,1000)}
Rtab = {}
for k,(n,U) in rungs.items():
    ts = R_train_score(n,U); R=(ts[0]+gates[0], ts[1]+gates[1]); Rtab[k]=R; rc=recompute(n)
    print(f"rung {k} {n}x{U}: train+score {ts[0]:.2f}-{ts[1]:.2f}; R {R[0]:.2f}-{R[1]:.2f}; recompute {rc[0]:.2f}-{rc[1]:.2f}; R+recompute {R[0]+rc[0]:.2f}-{R[1]+rc[1]:.2f}")
for P in (3.5, 7.0):
    Rmax=(36-P)/2; print(f"P={P}: R_max={Rmax}")
# reachability under one common speed factor x in [0,1] (x=0 fastest end of every range, x=1 slowest)
def Rx(k,x): lo,hi=Rtab[k]; return lo + x*(hi-lo)
for P in (3.5, 5.0, 7.0):
    Rmax=(36-P)/2
    print(f"P={P}: rung holds for x <= ", {k: round((Rmax-Rtab[k][0])/(Rtab[k][1]-Rtab[k][0]),3) for k in Rtab})
    # first rung chosen as x varies
    seg=[]; prev=None
    for i in range(0,1001):
        x=i/1000; ch=next((k for k in (1,2,3,4) if P + 2*Rx(k,x) <= 36), 'NOT STARTED')
        if ch!=prev: seg.append((x,ch)); prev=ch
    print("   chosen by x:", seg)
# max P at which rung k's fastest R fits
for k in Rtab: print(f"rung {k}: fits at fastest R only if P <= {36-2*Rtab[k][0]:.2f}")
# counterfactual (first draft): recompute inside R
for k,(n,U) in rungs.items():
    lo = Rtab[k][0]+recompute(n)[0]; print(f"[if charged] rung {k}: R_lo {lo:.2f}; fits at fastest only if P <= {36-2*lo:.2f}")
# ---- seeds
bases=[220001,220101,220201,220301]
reg={b+o for b in bases for o in range(11)} | set(range(220901,220906))
cal={221001+100*i+o for i in range(10) for o in range(11)}
reh={222001+100*i+o for i in range(10) for o in range(11)}
tests=set(range(229001,230000))
print("registered seeds:", len(reg), min(reg), max(reg))
assert len(reg)==49
assert all(220001<=s<=228999 for s in reg)
for name,st in (("cal",cal),("reh",reh)):
    assert st.isdisjoint(reg), name
assert not any(221001<=s<=221999 or 222001<=s<=222999 or 229001<=s<=229999 for s in reg)
assert all(221001<=s<=221999 for s in cal) and all(222001<=s<=222999 for s in reh)
assert cal.isdisjoint(reh)
others = {"S0":[(200001,209999),(2001,2002),(2091,2092),(920001,920999)],
          "S1":[(210001,219999),(2101,2105),(2111,2112),(2121,2122),(2191,2192),(921001,921999)],
          "P9":[(170001,171343),(179001,179933),(1701,1702)],
          "P9-I":[(182001,182020),(180101,181900),(1791,1792),(1801,1802),(900001,900233),(500001,500004),(941001,941001)],
          "P9-II":[(190001,191599),(1891,1892),(1901,1902),(910001,919999)]}
allS2 = reg|cal|reh|tests
for k,rs in others.items():
    hit=[s for s in allS2 if any(a<=s<=b for a,b in rs)]
    print(k, "overlap with S2 sets:", hit[:5])
# derived-seed hazard: other studies' declared init seeds + 1000k (k<=9) into S2 sets
for k,rs in others.items():
    small=[s for a,b in rs if b<10000 for s in range(a,b+1)]
    print(k, "seed+1000k (k<=9) landing in S2 sets:", [s+1000*j for s in small for j in range(1,10) if s+1000*j in allS2])
# what P9's +1000k would do to S2's own seeds (why direct seeding is needed)
print("P9 convention hazard: reg+1000 in cal:", sum((s+1000) in range(221001,222000) for s in reg), "reg+2000 in reh:", sum((s+2000) in range(222001,223000) for s in reg))
