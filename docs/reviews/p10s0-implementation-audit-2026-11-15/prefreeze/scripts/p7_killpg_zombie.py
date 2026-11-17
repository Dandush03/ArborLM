# Does os.killpg on a process group whose only member is an unreaped (zombie) child raise PermissionError on this macOS?
import os, signal, subprocess, sys, time, platform
res = []
for trial in range(5):
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    time.sleep(0.3)
    os.kill(p.pid, signal.SIGKILL)   # like psutil child.kill()
    time.sleep(0.2)                  # let it become a zombie; do NOT wait()
    try:
        os.killpg(p.pid, signal.SIGKILL); r = "no error"
    except Exception as e:
        r = f"{type(e).__name__}: {e}"
    p.wait(); res.append(r)
# and the race variant: killpg immediately after kill (no sleep)
race = []
for trial in range(20):
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    time.sleep(0.2)
    os.kill(p.pid, signal.SIGKILL)
    try:
        os.killpg(p.pid, signal.SIGKILL); r = "no error"
    except Exception as e:
        r = type(e).__name__
    p.wait(); race.append(r)
print(platform.platform(), {"after_zombie": res, "immediate": {k: race.count(k) for k in set(race)}})
