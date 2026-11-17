"""Read-only analysis of the P10-S1 load calibration curves (ADR-0021 section 10.1 item 0), for the draft of section 24.
Reads eval.json / train.json / manifest.json of the calibration run directory; trains nothing, writes nothing there.
Calibration draws only (p10s1-cal-1, -2; init seed 2191). Calibration numbers are never results.
Usage: python3 load_curve_analysis.py > load_curve_analysis.out
"""
import json, math
from pathlib import Path

R = Path('/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1C-20261115T172402822940Z-5e33fb08d1104815a21110f1f308c27c')
PLATEAU, LOADED, CEIL = 0.10, 4.0, 4.5
CELLS = ((4096, (8192, 16384, 32768, 65536)), (16384, (8192, 32768, 65536, 131072)))
REG_RUN = {4096: 49152, 16384: 32768}
DOUBLING = (512, 1024, 2048, 4096, 8192, 16384, 32768, 65536)

def h2(e): return 0.0 if e <= 0 or e >= 1 else -e * math.log2(e) - (1 - e) * math.log2(1 - e)
def fano(a):  # i = 5 - h2(e) - e log2 31 (ADR section 7.1)
    e = 1 - a; return 5 - h2(e) - e * math.log2(31)
def chance_hi(n):  # exact binomial upper end of the G2 interval, level 1 - 0.001/40 around 1/32 (two-sided)
    p, alpha = 1 / 32, 0.001 / 40
    # normal approximation is not used: exact tail by summation in log space
    from math import lgamma, log, exp
    def logpmf(k): return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) + k * log(p) + (n - k) * log(1 - p)
    k = int(n * p); tail = 0.0
    ks = range(n, k, -1); acc = 0.0; hi = n
    for kk in ks:
        acc += exp(logpmf(kk))
        if acc > alpha / 2: hi = kk; break
    return hi
_ch = {}
def bits(useful, n):
    if n not in _ch: _ch[n] = chance_hi(n)
    return 0.0 if useful <= _ch[n] else fano(useful / n)

def curve(slots, facts, d):
    lab = f'CAL_F-OQ_f{facts}_n{slots}_d{d}_i2191_y65536'
    out = {}
    for p in sorted((R / 'cells' / lab / 'eval').iterdir()):
        u = int(p.name[1:]); e = json.load(open(p / 'eval.json'))['reads']['main']['panels']
        out[u] = {q: (bits(e[q]['useful'], e[q]['n']), e[q]['useful'] / e[q]['n']) for q in 'AB'}
    return lab, out

def istar(c, q, u): return max(v[q][0] for uu, v in c.items() if uu <= u)

print('=' * 118)
print('1. LEARNING CURVES i(u), bits per fact (a_use in brackets); F-OQ; calibration draws d1, d2; panels A, B')
print('=' * 118)
curves = {}
for slots, fl in CELLS:
    for facts in fl:
        print(f'\n{slots} slots, {facts} facts (load {facts / slots:g}); registered U_run {REG_RUN[slots]}')
        print(f'{"updates":>8} | {"d1A":>14} {"d1B":>14} {"d2A":>14} {"d2B":>14}')
        cs = {d: curve(slots, facts, d)[1] for d in (1, 2)}
        curves[(slots, facts)] = cs
        for u in sorted(cs[1]):
            print(f'{u:8d} | ' + ' '.join(f'{cs[d][u][q][0]:6.3f} ({cs[d][u][q][1]:.3f})' for d in (1, 2) for q in 'AB'))

print('\n' + '=' * 118)
print('2. INCREMENTS PER DOUBLING  d(U) = i*(U) - i*(U/2)  (the quantity of the plateau rule, section 8.2: plateaued iff d <= 0.10)')
print('   and the ratio of successive increments r = d(U) / d(U/2)')
print('=' * 118)
for (slots, facts), cs in curves.items():
    print(f'\n{slots} slots, {facts} facts (load {facts / slots:g})')
    print(f'{"U":>8} | ' + ' '.join(f'{k:>7}' for k in ('d1A', 'd1B', 'd2A', 'd2B')) + ' | ' + ' '.join(f'{"r " + k:>7}' for k in ('d1A', 'd1B', 'd2A', 'd2B')))
    prev = None
    for u in DOUBLING[1:]:
        ds = [istar(cs[d], q, u) - istar(cs[d], q, u // 2) for d in (1, 2) for q in 'AB']
        rs = ['   -   ' if prev is None or min(prev) < 0.05 else f'{a / b:7.2f}' for a, b in zip(ds, prev or ds)] if prev else ['   -   '] * 4
        print(f'{u:8d} | ' + ' '.join(f'{x:7.3f}' for x in ds) + ' | ' + ' '.join(rs))
        prev = ds

print('\n' + '=' * 118)
print('3. THE RULE OF SECTION 8.2 READ AT EVERY RUN LENGTH U FOR WHICH BOTH U AND U/2 ARE SNAPSHOTS (information; only the registered U_run enters section 10.1)')
print('=' * 118)
for (slots, facts), cs in curves.items():
    us = [u for u in sorted(cs[1]) if u // 2 in cs[1] and u >= 8192]
    for u in us:
        rows = [(istar(cs[d], q, u), istar(cs[d], q, u) - istar(cs[d], q, u // 2)) for d in (1, 2) for q in 'AB']
        plat = all(x[1] <= PLATEAU + 1e-12 for x in rows); below = all(x[0] <= LOADED + 1e-12 for x in rows)
        print(f'{slots:6d} slots {facts:7d} facts  U={u:6d}: i* {min(x[0] for x in rows):.3f}-{max(x[0] for x in rows):.3f}  d(U) {min(x[1] for x in rows):.3f}-{max(x[1] for x in rows):.3f}  plateaued {str(plat):5}  i*<=4.0 {str(below):5}  LOADED {plat and below}')

print('\n' + '=' * 118)
print('4. EXTRAPOLATION (NOT A MEASUREMENT). Assumption G: from 65,536 updates on, each further doubling adds r times the previous doubling\'s increment,')
print('   r = d(65,536)/d(32,768) of that curve (constant). Assumption S (slower decay): r_S = sqrt(r) (the decay itself relaxes). Assumption C: constant increment (no decay).')
print('   Shown per draw (mean of panels A and B): projected i at 131,072 / 262,144 / 524,288 / 1,048,576; the first doubling U at which d(U) <= 0.10; i there; the asymptote under G.')
print('   Three post-onset doublings carry these fits. A learning curve can decay faster (a hard storage limit) or slower (a long tail) than either assumption.')
print('=' * 118)
proj = {}
for (slots, facts), cs in curves.items():
    for d in (1, 2):
        i65 = sum(cs[d][65536][q][0] for q in 'AB') / 2
        d65 = sum(istar(cs[d], q, 65536) - istar(cs[d], q, 32768) for q in 'AB') / 2
        d32 = sum(istar(cs[d], q, 32768) - istar(cs[d], q, 16384) for q in 'AB') / 2
        if d65 <= PLATEAU:
            print(f'{slots:6d} slots {facts:7d} facts d{d}: already plateaued at 65,536 (d = {d65:.3f}); i = {i65:.3f}')
            continue
        r = d65 / d32
        line = f'{slots:6d} slots {facts:7d} facts d{d}: i(65,536) {i65:.3f}  d(65,536) {d65:.3f}  d(32,768) {d32:.3f}  r {r:.2f}'
        if r >= 1:
            print(line + '  increments are not yet shrinking: no decay fit; the curve is still in its rise'); proj[(slots, facts, d)] = None; continue
        res = {}
        for name, rr in (('G', r), ('S', math.sqrt(r)), ('C', 1.0)):
            i, inc, u, hit, path = i65, d65, 65536, None, []
            for _ in range(6):
                inc *= rr; i = min(5.0, i + inc); u *= 2; path.append((u, i, inc))
                if hit is None and inc <= PLATEAU: hit = (u, i)
            res[name] = (path, hit)
        asym = min(5.0, i65 + d65 * r / (1 - r))
        proj[(slots, facts, d)] = (res, asym)
        print(line)
        for name in 'GSC':
            path, hit = res[name]
            print(f'        {name}: ' + '  '.join(f'{u // 1024}k {i:.2f} (+{inc:.2f})' for u, i, inc in path[:4]) + (f'  -> plateau rule first met at U = {hit[0]:,} with i = {hit[1]:.2f} ({"<= 4.0: LOADED" if hit[1] <= LOADED else "> 4.0: NOT LOADED"})' if hit else '  -> plateau rule not met by 4,194,304'))
        print(f'        asymptote under G: {asym:.2f} bits per fact = {asym * facts / 1000:.0f}k bits in the store')

print('\n' + '=' * 118)
print('5. INFORMATION BUDGET. F-OQ trainable parameters: slots x 48 (16 key + 32 value) + 1,025 (output projection 32x32 + gate).')
print('   demand = facts x 5 bits. retained = facts x i at 65,536 updates (mean of draws and panels). FP32 parameters hold 32 bits each, so the counting budget never binds;')
print('   the comparison of interest is against ~2 bits per parameter (a common empirical figure for memorization in trained networks; stated as a heuristic, not a law).')
print('=' * 118)
print(f'{"slots":>6} {"facts":>7} {"load":>5} {"params":>8} {"demand bits":>11} {"demand/param":>12} {"demand/value-param":>18} {"retained@65k":>12} {"ret/param":>9} {"ret/slot":>8} {"asym G bits":>11} {"asym/slot":>9}')
for (slots, facts), cs in curves.items():
    params = slots * 48 + 1025
    i65 = sum(cs[d][65536][q][0] for d in (1, 2) for q in 'AB') / 4
    asy = [proj.get((slots, facts, d)) for d in (1, 2)]
    a = sum(x[1] for x in asy) / 2 * facts if all(asy) else float('nan')
    print(f'{slots:6d} {facts:7d} {facts / slots:5g} {params:8d} {facts * 5:11d} {facts * 5 / params:12.2f} {facts * 5 / (slots * 32):18.2f} {i65 * facts:12.0f} {i65 * facts / params:9.3f} {i65 * facts / slots:8.1f} {a:11.0f} {a / slots:9.1f}')

print('\n' + '=' * 118)
print('6. MEASURED COST (calibrate/manifest.json task seconds = wall of one run including its snapshot evaluations; six workers; the machine was shared)')
print('=' * 118)
man = json.load(open(R / 'calibrate' / 'manifest.json'))
rate = {}
for t in man['tasks']:
    lab = t['label']; tr = json.load(open(R / 'cells' / lab / 'train.json'))
    key = (tr['arm'], tr['slots'], tr['facts'], tr['learning_rate'])
    rate.setdefault(key, []).append((t['seconds'], tr['run_updates'], tr['wall_seconds'], tr['cpu_seconds']))
print(f'{"arm":>5} {"slots":>6} {"facts":>7} {"lr":>6} {"updates":>7} {"task s (d1,d2)":>16} {"train wall s":>12} {"s/update (task)":>15} {"s/update (train)":>16}')
RATE = {}
for (arm, slots, facts, lr), v in sorted(rate.items()):
    ts = [x[0] for x in v]; u = v[0][1]; tw = sum(x[2] for x in v) / len(v)
    RATE[(arm, slots, facts, lr)] = max(ts) / u
    print(f'{arm:>5} {slots:6d} {facts:7d} {lr:6g} {u:7d} {ts[0]:8.0f},{ts[1]:7.0f} {tw:12.0f} {max(ts) / u:15.5f} {tw / u:16.5f}')

print('\n' + '=' * 118)
print('7. DENSE CONTROL (D-OQ) BY LEARNING RATE: Panel A accuracy (minimum over the two draws) at each snapshot')
print('=' * 118)
for facts, slots in ((8192, 16384), (32768, 65536)):
    for lr, suf in ((0.001, '_lr0.001'), (0.003, ''), (0.01, '_lr0.01')):
        acc = {}
        for d in (1, 2):
            lab = f'CAL_D-OQ_f{facts}_n{slots}_d{d}_i2191{suf}'
            for p in sorted((R / 'cells' / lab / 'eval').iterdir()):
                u = int(p.name[1:]); e = json.load(open(p / 'eval.json'))['reads']['main']['panels']['A']
                acc[u] = min(acc.get(u, 1.0), e['correct'] / e['n'])
        print(f'{slots:6d} slots {facts:6d} facts lr {lr:<6g}: ' + '  '.join(f'{u}: {a:.3f}' for u, a in sorted(acc.items())))

print('\n' + '=' * 118)
print('8. COST OF THE PROPOSED EXTENSION AND OF THE REGISTERED ROWS IT CAN CREATE (projections from the rates of part 6; T-OQ is unmeasured and taken at 2 x F-OQ as in section 10.3)')
print('=' * 118)
f4_32, f4_16, f16_65, f16_32 = RATE[('F-OQ', 4096, 32768, 0.003)], RATE[('F-OQ', 4096, 16384, 0.003)], RATE[('F-OQ', 16384, 65536, 0.003)], RATE[('F-OQ', 16384, 32768, 0.003)]
f4_24 = (f4_32 + f4_16) / 2  # 24,576 facts: interpolated
f64 = RATE[('F-OQ', 65536, 32768, 0.003)]; r64 = RATE[('R2', 65536, 32768, 0.003)]
h4, h16, h64 = RATE[('H8', 4096, 2048, 0.003)], RATE[('H8', 16384, 8192, 0.003)], RATE[('H8', 65536, 32768, 0.003)]
d16, d64 = RATE[('D-OQ', 16384, 8192, 0.01)], RATE[('D-OQ', 65536, 32768, 0.01)]
print(f'rates used, s per update: F-OQ 4K/32,768 {f4_32:.5f}; 4K/24,576 {f4_24:.5f} (interpolated); 16K/65,536 {f16_65:.5f}; 16K/32,768 {f16_32:.5f}; 64K {f64:.5f}; H8 {h4:.5f}/{h16:.5f}/{h64:.5f}; D-OQ {d16:.5f}/{d64:.5f}; R2 64K {r64:.5f}')
print('\n8a. Extension stages (each run on its own worker, six workers; charged = wall of the slowest run of the stage)')
cands = (131072, 196608, 262144, 393216, 524288); prevu = 65536; tot = 0.0
for k, u in enumerate(cands, 1):
    a = (u - prevu) * f4_32; b = (u - (0 if k == 1 else prevu)) * f4_24; c = (u - prevu) * f16_65 if u <= 262144 else 0.0
    w = max(a, b, c); tot += w
    print(f'  stage E{k} -> {u:7,}: 4K/32,768 {a:6.0f} s; 4K/24,576 {b:6.0f} s; 16K/65,536 {c:6.0f} s; stage wall {w:6.0f} s; cumulative {tot:6.0f} s = {tot / 3600:.2f} h')
    prevu = u
print(f'  CPU-seconds of the six runs to the ceilings: {2 * ((524288 - 65536) * f4_32 + 524288 * f4_24 + (262144 - 65536) * f16_65):.0f} s')
print(f'  if the continuation from the stored 65,536-update checkpoints is refused (restore check fails): 4K/32,768 and 16K/65,536 start from zero: + {65536 * f16_65:.0f} s on the first stage')
print('\n8b. Registered 4K->16K loaded row, added training CPU-seconds per replicate over the registered design, as a function of U_L')
print('     F* = 32,768 (cells are the registered 32K/4K and 32K/16K): smaller cell F-OQ + T-OQ + H8 from 49,152 to U_L; larger cell from 32,768 to 4 U_P\' for F-OQ, T-OQ, H8, D-OQ; R2 at 32K/64K from 8,192 to U_P\'')
print('     F* = 24,576 (a new row): smaller cell from zero to U_L; larger cell 24K/16K for F-OQ, T-OQ, H8, D-OQ to 4 U_P\'; R2 at 24K/64K to U_P\'')
base_charged_now, rehearsal, remaining = 5664 / 3600, 0.45, 5.6
print(f'     baseline for the headroom rule (section 10.3; the registered projection is itself unmeasured until the rehearsal): charged so far {base_charged_now:.2f} h; rehearsal about {rehearsal} h; remaining {remaining} h (both seed blocks)')
for upp in (16384, 32768):
    print(f'   row U_P\' = {upp}:')
    for u in cands:
        small32 = (f4_32 * 3 + h4) * (u - 49152)
        large32 = (f16_32 * 3 + h16 + d16) * (4 * upp - 32768) + r64 * (upp - 8192)
        small24 = (f4_24 * 3 + h4) * u
        large24 = (f16_32 * 3 + h16 + d16) * 4 * upp + r64 * upp
        for name, s in (('F*=32,768', small32 + large32), ('F*=24,576', small24 + large24)):
            ch = 5 * s / 6 / 3600
            print(f'     U_L {u:7,} {name}: {s:7.0f} s per replicate; x5 = {5 * s / 3600:5.1f} CPU-h = {ch:4.2f} charged h; cap needed by the twofold rule about {base_charged_now + rehearsal + 2.3 + 2 * (remaining + ch):.1f} h (taking 2.3 h for the whole extension)')
print('\n8c. Registered 16K->64K overload row (65,536 facts; section 10.1 row 4 with the smaller cell run to U_L): smaller cell F-OQ + T-OQ + H8 to U_L; larger cell F-OQ, T-OQ, H8, D-OQ to 2 U_P\'; R2 to U_P\'')
for upp in (16384, 32768):
    for u in (131072, 196608, 262144):
        s = (f16_65 * 3 + h16) * u + (f64 * 3 + h64 + d64) * 2 * upp + r64 * upp
        ch = 5 * s / 6 / 3600
        print(f'     U_P\' {upp} U_L {u:7,}: {s:7.0f} s per replicate; x5 = {5 * s / 3600:5.1f} CPU-h = {ch:4.2f} charged h; twofold: + {2 * ch:.1f} h of cap')
print('\n8d. Dense learning-rate grid: one further rate = D-OQ at 8K/16K (to 32,768) and 32K/64K (to 16,384) on two draws = 4 runs')
print(f'     wall {max(32768 * d16, 16384 * d64):.0f} s per rate = {max(32768 * d16, 16384 * d64) / 3600:.2f} charged h; three rates {3 * max(32768 * d16, 16384 * d64) / 3600:.2f} h; CPU-seconds per rate {2 * (32768 * d16 + 16384 * d64):.0f}')
