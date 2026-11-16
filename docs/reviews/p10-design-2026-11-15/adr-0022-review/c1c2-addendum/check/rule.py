# Illustrative (invented) per-answer means on E_C; not data. Old rule vs proposed rule on C1.
S0 = dict(de_single=0.20, de_comb=0.20, fr_single=0.18, fr_comb=0.15)  # Stage 0; C1 first answer == single
T = dict(de=0.62, fr=0.65)
def old(de_s, fr_s, de_c, fr_c):
    return (de_c+fr_c)/2 >= 0.8*(de_s+fr_s)/2
def H(a_c, a_s, s0c, s0s): return (a_c - s0c)/(a_s - s0s)
def new(de_s, fr_s, de_c, fr_c):
    out = {}
    for a,(c,s) in {"de":(de_c,de_s),"fr":(fr_c,fr_s)}.items():
        G = (s - S0[a+"_single"])/(T[a]-S0[a+"_single"])
        if G < 0.5: out[a] = "NOT_EVALUATED (G=%.2f)" % G; continue
        out[a] = round(H(c, s, S0[a+"_comb"], S0[a+"_single"]), 3)
    return out
cases = {
 "do-nothing (=Stage 0)": (0.20, 0.18, 0.20, 0.15),
 "Stage-0-like but old rule": (0.20, 0.18, 0.20, 0.15),
 "first answer only, 2nd empty (strong DE, weak FR)": (0.60, 0.20, 0.60, 0.00),
 "first answer only, 2nd = Stage 0 behaviour": (0.55, 0.45, 0.55, 0.15),
 "copies German into French slot (chrF de-vs-fr refs ~0.25)": (0.55, 0.50, 0.55, 0.25),
 "composes well": (0.55, 0.50, 0.55, 0.46),
}
for k,v in cases.items(): print(f"{k:58s} old={old(*v)!s:5s} new={new(*v)}")
# ensemble C1: per-answer combined == single == teacher
print("ensemble", {"de": H(T['de'],T['de'],S0['de_comb'],S0['de_single']), "fr": round(H(T['fr'],T['fr'],S0['fr_comb'],S0['fr_single']),3)})
print("ensemble if Stage0 French gains from context (fr_comb=0.25):", round(H(T['fr'],T['fr'],0.25,0.18),3))
