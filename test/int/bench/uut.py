#!/usr/bin/env python3
"""Bench lines of bench.json that reach the unit under test (the Pi) over ssh: `flash`, `dump`, actions.

  deploy    copy the image to the Pi, stop the instance this script started before (by its recorded pid),
            start the new one; prints `Serial# = <Pi serial>` (fth's provenance line)
  readback  copy the image on the Pi back (fth compares its sha256 with the manifest image)
  stop      stop the instance started by `deploy`
  action    one named bench action; its start, end and output go to <logs>/actions/<n>-<name>.json and
            one line to <logs>/bench-actions.log

Nothing here needs sudo; only `<remote-dir>` on the Pi is written.
"""
import argparse
import datetime
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

PLATFORM = ("echo MODEL=$(tr -d '\\0' </proc/device-tree/model); echo '--- os-release'; cat /etc/os-release; "
            "echo '--- rpi-issue'; cat /etc/rpi-issue; echo '--- long-bit'; getconf LONG_BIT")
# sockets and open character devices of the deployment process (its own user: no sudo needed)
SOCKETS = ("pid=$(cat {d}/pid); echo PID=$pid; echo EXE=$(readlink /proc/$pid/exe); echo '--- sockets'; "
           "ss -H -tuanp | grep \"pid=$pid,\" || true; echo '--- devices'; "
           "for f in /proc/$pid/fd/*; do t=$(readlink $f); [ -c \"$t\" ] && echo \"$t\"; done | sort -u")
CLEAN = "rm -f {d}/DpCat/*.fdp; ls -A {d}/DpCat | wc -l"
FINAL = "cd {d} && sha256sum DpCat/*.fdp"


def ssh(host: str, command: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, command], capture_output=True, text=True, timeout=timeout)


def must(r: subprocess.CompletedProcess, what: str) -> str:
    if r.returncode != 0:
        raise SystemExit(f"uut: {what} failed (exit {r.returncode}): {r.stderr.strip()}")
    return r.stdout


def stop_cmd(d: str) -> str:
    """Stop only the process whose pid we recorded AND whose executable is still our image."""
    return (f"if [ -f {d}/pid ]; then p=$(cat {d}/pid); "
            f"if [ \"$(readlink /proc/$p/exe 2>/dev/null)\" = \"$(readlink -f {d}/PiSensor)\" ]; then kill $p; "
            f"for i in $(seq 50); do kill -0 $p 2>/dev/null || break; sleep 0.1; done; "
            f"kill -0 $p 2>/dev/null && kill -9 $p; echo stopped $p; else echo not-running; fi; rm -f {d}/pid; fi")


def deploy(a) -> int:
    d = shlex.quote(a.remote_dir)
    print(must(ssh(a.ssh, f"mkdir -p {d} && {stop_cmd(d)}"), "stop previous instance").strip())
    r = subprocess.run(["scp", "-o", "BatchMode=yes", a.image, f"{a.ssh}:{a.remote_dir}/PiSensor.new"], capture_output=True, text=True, timeout=120)
    must(r, "scp image")
    out = must(ssh(a.ssh, f"cd {d} && mv PiSensor.new PiSensor && chmod +x PiSensor && "
                          f"(nohup ./PiSensor >fsw.log 2>&1 </dev/null & echo $! >pid) && sleep {a.settle} && "
                          f"p=$(cat pid) && kill -0 $p && echo started $p && sha256sum PiSensor && "
                          "echo \"Serial# = $(awk '/^Serial/ {print $3}' /proc/cpuinfo)\""), "start")
    print(out.strip())
    return 0


def readback(a) -> int:
    r = subprocess.run(["scp", "-o", "BatchMode=yes", f"{a.ssh}:{a.remote_dir}/PiSensor", a.readback], capture_output=True, text=True, timeout=120)
    must(r, "scp read-back")
    print(must(ssh(a.ssh, "echo \"Serial# = $(awk '/^Serial/ {print $3}' /proc/cpuinfo)\""), "serial").strip())
    return 0


def stop(a) -> int:
    print(must(ssh(a.ssh, stop_cmd(shlex.quote(a.remote_dir))), "stop").strip())
    return 0


def clock(a) -> tuple:
    """Pi clock minus bench clock: `date` on the Pi against the middle of the ssh round trip."""
    best = None
    for _ in range(5):
        t0 = time.time()
        r = ssh(a.ssh, "date +%s.%N")
        t1 = time.time()
        if r.returncode != 0:
            return r.returncode, r.stderr
        sample = {"offset_s": float(r.stdout.strip()) - (t0 + t1) / 2, "uncertainty_s": (t1 - t0) / 2}
        if best is None or sample["uncertainty_s"] < best["uncertainty_s"]:
            best = sample
    return 0, json.dumps(best)


def wait_cfdp(a) -> tuple:
    """Wait until YAMCS shows no file transfer in progress, for `--quiet` seconds in a row (reads <logs>/cfdp.json)."""
    path = Path(a.logs) / "cfdp.json"
    end = time.time() + a.timeout
    quiet_since = None
    while time.time() < end:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        busy = data is None or time.time() - data["updated"] > 5 or any(
            t.get("state") not in ("COMPLETED", "FAILED", "CANCELLED") for t in data["transfers"])
        quiet_since = None if busy else (quiet_since or time.time())
        if quiet_since and time.time() - quiet_since >= a.quiet:
            return 0, json.dumps({"transfers": len(data["transfers"])})
        time.sleep(0.5)
    return 1, "timed out waiting for the CFDP transfers to finish at the ground"


def action(a) -> int:
    logs = Path(a.logs)
    (logs / "actions").mkdir(parents=True, exist_ok=True)
    d = shlex.quote(a.remote_dir)
    start = time.time()
    if a.name == "clock":
        rc, out = clock(a)
    elif a.name == "wait_cfdp":
        rc, out = wait_cfdp(a)
    else:
        cmd = {"platform": PLATFORM, "sockets": SOCKETS.format(d=d), "clean_products": CLEAN.format(d=d),
               "final_state": FINAL.format(d=d)}[a.name]
        r = ssh(a.ssh, cmd)
        rc, out = r.returncode, r.stdout + (("\n--- stderr\n" + r.stderr) if r.stderr.strip() else "")
    end = time.time()
    if a.name == "final_state" and rc == 0:
        (logs / "final-state.txt").write_text(out, encoding="utf-8")
    n = len(list((logs / "actions").glob("*.json"))) + 1
    result = {"name": a.name, "start": start, "end": end, "rc": rc, "stdout": out}
    (logs / "actions" / f"{n:04d}-{a.name}.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    with open(logs / "bench-actions.log", "a", encoding="utf-8") as fh:
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        fh.write(f"{stamp},{a.name}.result,start={start:.3f} end={end:.3f} rc={rc} output=actions/{n:04d}-{a.name}.json\n")
    return 0 if rc == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="verb", required=True)
    for verb in ("deploy", "readback", "stop", "action"):
        s = sub.add_parser(verb)
        s.add_argument("--ssh", required=True, help="ssh host alias of the Pi")
        s.add_argument("--remote-dir", required=True, help="campaign directory on the Pi (only place written)")
        if verb == "deploy":
            s.add_argument("--image", required=True)
            s.add_argument("--settle", type=float, default=5.0)
        if verb == "readback":
            s.add_argument("--readback", required=True)
        if verb == "action":
            s.add_argument("name", choices=("platform", "sockets", "clock", "clean_products", "final_state", "wait_cfdp"))
            s.add_argument("--logs", required=True)
            s.add_argument("--timeout", type=float, default=600.0)
            s.add_argument("--quiet", type=float, default=3.0)
    a = ap.parse_args(argv)
    return {"deploy": deploy, "readback": readback, "stop": stop, "action": action}[a.verb](a)


if __name__ == "__main__":
    sys.exit(main())
