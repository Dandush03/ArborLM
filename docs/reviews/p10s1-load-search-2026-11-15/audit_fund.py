"""Cap needed under the twofold rule for row combinations (numbers transcribed from audit_costs.out). Usage: python3 -I audit_fund.py"""
sets = {"MAN": dict(rem=7.21, L={196608: 2.06, 262144: 2.68, 393216: 3.92, 524288: 5.17}, Y={(16384, 262144): 6.96, (32768, 262144): 9.15}),
        "TRN": dict(rem=6.65, L={196608: 1.82, 262144: 2.35, 393216: 3.43, 524288: 4.51}, Y={(16384, 262144): 5.92, (32768, 262144): 7.83})}
for name, s in sets.items():
    for ext in (2.3, 3.8):
        fixed = 1.57 + ext + 0.45
        print(f"{name} ext={ext}: unchanged study only {fixed + 2 * s['rem']:.1f} h")
        for ul, a in s["L"].items():
            print(f"   4K row U_L={ul}: {fixed + 2 * (s['rem'] + a):.1f}")
        for k, b in s["Y"].items():
            print(f"   16K row U_P'={k[0]} U_L={k[1]}: {fixed + 2 * (s['rem'] + b):.1f};  with 4K row U_L=196608/393216: {fixed + 2 * (s['rem'] + b + s['L'][196608]):.1f} / {fixed + 2 * (s['rem'] + b + s['L'][393216]):.1f}")
