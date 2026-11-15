"""Numbers present on removed diff lines but absent from added lines (rev3 -> rev4). Usage: python3 -I numbers_check.py <unified diff>"""
import re, sys
from collections import Counter
rm, ad = Counter(), Counter()
for ln in open(sys.argv[1]):
    if ln.startswith('---') or ln.startswith('+++'): continue
    nums = re.findall(r'\d[\d,.]*\d|\d', ln[1:])
    if ln.startswith('-'): rm.update(nums)
    elif ln.startswith('+'): ad.update(nums)
lost = {k: v - ad.get(k, 0) for k, v in rm.items() if v > ad.get(k, 0)}
print("numbers removed and not re-added (value: net count):", lost or "none")
