#!/usr/bin/env python3
"""Bench actions of bench.json that read the unit under test (the Pi) over ssh.

  action    one named bench action; its start, end and output go to <logs>/actions/<n>-<name>.json and
            one line to <logs>/bench-actions.log

The image is copied, started and stopped by yamcs_bench.py (`<remote-dir>/PiSensor`, `fsw.pid`, working
directory `run/`). Nothing here needs sudo; only `<remote-dir>` on the Pi is written.
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
SOCKETS = ("pid=$(cat {d}/fsw.pid); echo PID=$pid; echo EXE=$(readlink /proc/$pid/exe); echo '--- sockets'; "
           "ss -H -tuanp | grep \"pid=$pid,\" || true; echo '--- devices'; "
           "for f in /proc/$pid/fd/*; do t=$(readlink $f); [ -c \"$t\" ] && echo \"$t\"; done | sort -u")
CLEAN = "rm -f {d}/run/dp/*.fdp; ls -A {d}/run/dp | wc -l"
FINAL = "cd {d}/run && ls -A dp && for f in dp/*.fdp; do [ -e \"$f\" ] && sha256sum \"$f\"; done; true"


def ssh(host: str, command: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, command], capture_output=True, text=True, timeout=timeout)


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
    s = sub.add_parser("action")
    s.add_argument("--ssh", required=True, help="ssh host alias of the Pi")
    s.add_argument("--remote-dir", default="pisensor-campaign/sys-run",
                   help="directory on the Pi owned by yamcs_bench.py (its --pi-dir default)")
    s.add_argument("name", choices=("platform", "sockets", "clock", "clean_products", "final_state", "wait_cfdp"))
    s.add_argument("--logs", required=True)
    s.add_argument("--timeout", type=float, default=600.0)
    s.add_argument("--quiet", type=float, default=3.0)
    a = ap.parse_args(argv)
    return action(a)


if __name__ == "__main__":
    sys.exit(main())
