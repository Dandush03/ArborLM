# ruff: noqa
# Capacity summary from gen1/summary.json: draws needed for 2,000 distinct programs after renaming every identifier,
# and a uniform-sampling estimate of the population N from (draws n, distinct D): D = N(1 - exp(-n/N)) (an underestimate
# when the generator's distribution over programs is uneven; misleading when one shape is unbounded and others saturate).
# (Saved copy of the code that was run inline as a heredoc with `python3 -`; output in a10_capacity_out.txt.)
import json, math
s=json.load(open('gen1/summary.json'))
def solveN(n,D):
    lo,hi=D,10**9
    for _ in range(200):
        mid=(lo+hi)/2
        if mid*(1-math.exp(-n/mid))<D: lo=mid
        else: hi=mid
    return hi
rows=[]
for c in s['cells']:
    grp='new' if c['lineage'] in s['new'] else 'old'
    est = solveN(c['draws'], c['canon_distinct']) if c['new_rate_last_2000_draws']<0.9 else None
    rows.append((grp,c['lineage'],c['level'],c['draws_to_2000_canon'],c['canon_distinct'],c['draws'],c['new_rate_last_2000_draws'],est))
print('new 25 x 7 cells reaching 2000 distinct programs after renaming:', sum(1 for r in rows if r[0]=='new' and r[3] is not None), 'of', sum(1 for r in rows if r[0]=='new'))
print('max draws needed among new:', max(r[3] for r in rows if r[0]=='new'))
print('cells with late new-rate < 0.9 (population estimate, uniform model):')
for r in sorted(rows, key=lambda r: (r[7] or 1e18)):
    if r[7] is not None:
        print(f'  {r[0]} {r[1]:28s} L{r[2]} draws {r[5]:6d} distinct {r[4]:5d} new-rate {r[6]:.2f} N_est {r[7]:8.0f}')
print('old cells failing 2000:', [(r[1],r[2],r[4]) for r in rows if r[3] is None])
