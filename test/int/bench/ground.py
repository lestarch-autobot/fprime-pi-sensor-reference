#!/usr/bin/env python3
"""Bench `gds` line of bench.json: the ground side of the RFM69 link for one run.

Starts fprime-yamcs (project configuration, HTTP 8190, UDP frame links) and the Feather ground radio
bridge, both logging under `<logs>` (= record/raw: yamcs.out, bridge.out, bridge.log, yamcs-data/).
fth stops this process group with SIGTERM; fprime-yamcs does not stop its children on a signal, so
this script kills every descendant it started (found by parent pid, never by name) and then exits.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def descendants(root: int) -> list:
    """Pids of every live descendant of `root`, children before parents reversed (leaves first)."""
    parent = {}
    for d in Path("/proc").glob("[0-9]*"):
        try:
            parent[int(d.name)] = int((d / "stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
    out, frontier = [], [root]
    while frontier:
        kids = [p for p, pp in parent.items() if pp in frontier]
        out += kids
        frontier = kids
    return list(reversed(out))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--yamcs-config-dir", required=True)
    ap.add_argument("--bridge", required=True, help="ground/feather_bridge.py")
    ap.add_argument("--uart", required=True)
    ap.add_argument("--tm-port", type=int, default=51000)
    ap.add_argument("--tc-port", type=int, default=51001)
    ap.add_argument("--inject-port", type=int, default=51002)
    a = ap.parse_args(argv)
    logs = Path(a.logs).resolve()
    logs.mkdir(parents=True, exist_ok=True)
    bindir = Path(sys.executable).parent
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    yamcs = subprocess.Popen(
        [str(bindir / "fprime-yamcs"), "-n", "--dictionary", str(Path(a.dictionary).resolve()),
         "--communication-selection", "udp", "--yamcs-config-dir", str(Path(a.yamcs_config_dir).resolve()),
         "--yamcs-data-dir", str(logs / "yamcs-data"), "--udp-downlink-port", str(a.tm_port),
         "--udp-uplink-port", str(a.tc_port), "--udp-tm-inject-port", str(a.inject_port),
         "--skip-browser-open", "--logs", str(logs / "yamcs-logs")],
        cwd=str(Path(a.yamcs_config_dir).resolve().parent), env=env,
        stdout=open(logs / "yamcs.out", "w"), stderr=subprocess.STDOUT)
    bridge = subprocess.Popen(
        [sys.executable, str(Path(a.bridge).resolve()), "--uart-device", a.uart, "--tm-port", str(a.tm_port),
         "--tc-port", str(a.tc_port), "--log", str(logs / "bridge.log")],
        stdout=open(logs / "bridge.out", "w"), stderr=subprocess.STDOUT)
    print(f"ground: fprime-yamcs pid {yamcs.pid}, bridge pid {bridge.pid}", flush=True)
    stop = []
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda s, _f: stop.append(s))
    while not stop and yamcs.poll() is None and bridge.poll() is None:
        time.sleep(0.5)
    print(f"ground: stopping (signal {stop}, yamcs {yamcs.poll()}, bridge {bridge.poll()})", flush=True)
    victims = descendants(os.getpid())
    for sig, grace in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 2.0)):
        for pid in victims:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        end = time.monotonic() + grace
        while time.monotonic() < end and any(Path(f"/proc/{p}").exists() for p in victims):
            for child in (yamcs, bridge):
                child.poll()
            time.sleep(0.1)
    left = [p for p in victims if Path(f"/proc/{p}").exists() and p not in (yamcs.pid, bridge.pid)]
    print(f"ground: stopped {len(victims)} process(es); still alive: {left}", flush=True)
    return 0 if stop else 1


if __name__ == "__main__":
    sys.exit(main())
