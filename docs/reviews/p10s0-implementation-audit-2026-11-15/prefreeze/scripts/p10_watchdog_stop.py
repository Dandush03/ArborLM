# arborlm.watchdog._stop on a child that has already exited (zombie, not reaped) with graceful=False: does killpg raise PermissionError?
# Also studies.p9.pool._kill (S0's pool) on the same state.
import subprocess, sys, time, os, signal, psutil
from arborlm import watchdog
from studies.p9 import pool
def zombie():
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    w = psutil.Process(p.pid); time.sleep(0.3); os.kill(p.pid, signal.SIGKILL); time.sleep(0.2); return p, w
out = {}
p, w = zombie()
try:
    watchdog._stop(p, w, graceful=False); out["watchdog._stop"] = "no error"
except Exception as e:
    out["watchdog._stop"] = f"{type(e).__name__}: {e}"; p.wait()
p, w = zombie()
try:
    pool._kill(p); out["p9.pool._kill (S0)"] = "no error"
except Exception as e:
    out["p9.pool._kill (S0)"] = f"{type(e).__name__}: {e}"; p.wait()
print(out)
