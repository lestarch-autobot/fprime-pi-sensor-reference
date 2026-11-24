#!/usr/bin/env python3
"""Bench adapter between fth (fprime-testing-harness) and the PiSensor bench.

fth drives a bench through the command lines of ``bench.json`` and reads the
recorder and sender logs in the fprime-cli log format. This bench has no
fprime-gds: the ground system is fprime-yamcs behind a bench bridge (TCP since
2026-11-23, tcp_bridge.py; before that the RFM69 ground radio) and the
unit under test is a Linux process on the Raspberry Pi. Each subcommand below is
one ``bench.json`` line:

  flash     copy the image to the Pi, stop the image this adapter started
            before, start the new one, print the Pi serial number
  dump      copy the image file back from the Pi (read-back)
  gds       run the bench bridge and fprime-yamcs until terminated
  recorder  write the events and channels YAMCS receives as event.log and
            channel.log
  send      send one command through YAMCS and write command.log; a command the
            unit does not report as dispatched is sent again (resend.log)
  action    bench actions on the Pi: fsw-restart, camera-hold, camera-release
  stop      stop the image on the Pi (bench release)
  collect-gcda  copy the coverage counts of a stopped image built for coverage

Names: the dictionary qualifies instances with their subtopology
(``CdhCore.cmdDisp.OpCodeCompleted``); plans use ``cmdDisp.OpCodeCompleted`` and
fth prefixes the deployment. The logs carry ``<deployment>.<instance>.<name>``
and ``send`` resolves such a name back through the dictionary.

Processes are stopped by recorded process id only, never by name pattern.
"""
import argparse
import datetime
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PI_PID = "fsw.pid"
GCDA_DIR = "gcda"
HOLD_PID = "camera-hold.pid"


def ssh(host: str, command: str, timeout: float = 120, check: bool = True) -> str:
    done = subprocess.run(["ssh", "-o", "BatchMode=yes", host, command], capture_output=True, text=True,
                          timeout=timeout)
    if check and done.returncode != 0:
        raise SystemExit(f"ssh {host}: {command!r} failed ({done.returncode}): {done.stderr.strip()}")
    return done.stdout


def short_name(deployment: str, qualified: str) -> str:
    """``CdhCore.cmdDisp.OpCodeCompleted`` -> ``<deployment>.cmdDisp.OpCodeCompleted``."""
    return ".".join([deployment] + qualified.split(".")[-2:])


def load_dictionary(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve(entries: list, deployment: str, name: str) -> dict:
    found = [e for e in entries if short_name(deployment, e["name"]) == name or e["name"] == name]
    if not found:  # the dictionary writes a parameter command in upper case: FILEINDEFAULTKEEP_PRM_SET
        found = [e for e in entries if short_name(deployment, e["name"]).lower() == name.lower()]
    if len(found) != 1:
        raise SystemExit(f"{name}: {len(found)} dictionary entries match")
    return found[0]


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")


def fsw_time(iso: str) -> tuple:
    """YAMCS generation time (the FSW time tag) -> (seconds, microseconds)."""
    when = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(when.timestamp()), when.microsecond


def time_fields(iso: str) -> str:
    seconds, micros = fsw_time(iso)
    # The literal TB_PROC_TIME is the fprime-cli log layout fth parses; the time is the FSW time tag
    return f"TB_PROC_TIME: {seconds}.{micros:06d}s, context=0,(2(0)-{seconds}:{micros})"


# ----------------------------------------------------------------------
# Unit under test on the Pi
# ----------------------------------------------------------------------

def stop_recorded(args, pid_file: str, executable: str) -> None:
    """Stop the process a pid file of this adapter names, only while it still runs ``executable``.

    A pid file can outlive its process, and the number can be reused by another user of the Pi.
    """
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} 2>/dev/null || exit 0; [ -f {pid_file} ] || exit 0; "
                 f"pid=$(cat {pid_file}); want=$(readlink -f {shlex.quote(executable)}); "
                 f"if [ -n \"$want\" ] && [ \"$(readlink /proc/$pid/exe 2>/dev/null)\" = \"$want\" ]; then "
                 f"kill $pid; for i in $(seq 20); do kill -0 $pid 2>/dev/null || break; sleep 0.5; done; "
                 f"if kill -0 $pid 2>/dev/null && [ \"$(readlink /proc/$pid/exe 2>/dev/null)\" = \"$want\" ]; "
                 f"then kill -9 $pid; fi; fi; rm -f {pid_file}")


def confirm_running(args, pid_file: str, what: str) -> None:
    alive = ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && kill -0 $(cat {pid_file}) 2>/dev/null && echo alive; true")
    if "alive" not in alive:
        raise SystemExit(f"{what} is not running on {args.pi}")


def pi_stop(args) -> None:
    stop_recorded(args, PI_PID, "PiSensor")


def pi_start(args) -> None:
    # Arguments of the image (the ground address and port of the TCP variant), a comma separated list
    image_args = " ".join(shlex.quote(part) for part in args.image_args.split(",") if part)
    # An image built for coverage writes its counts under gcda/ when it ends (flash --gcov)
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && mkdir -p run && "
                 f"if [ -d {GCDA_DIR} ]; then export GCOV_PREFIX=$PWD/{GCDA_DIR}; fi; cd run && "
                 f"(nohup ../PiSensor {image_args} >> fsw.log 2>&1 < /dev/null & echo $! > ../{PI_PID}); sleep 1")
    confirm_running(args, PI_PID, "the image")


def cmd_flash(args) -> None:
    ssh(args.pi, f"mkdir -p {shlex.quote(args.pi_dir)}")
    pi_stop(args)
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && rm -rf run PiSensor {GCDA_DIR}" + (f" && mkdir {GCDA_DIR}" if args.gcov else ""))
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", args.image, f"{args.pi}:{args.pi_dir}/PiSensor"], check=True,
                   timeout=300)
    ssh(args.pi, f"chmod +x {shlex.quote(args.pi_dir)}/PiSensor")
    if args.prm:  # the parameter file is read from the working directory when the image starts
        ssh(args.pi, f"mkdir -p {shlex.quote(args.pi_dir)}/run")
        subprocess.run(["scp", "-q", "-o", "BatchMode=yes", args.prm, f"{args.pi}:{args.pi_dir}/run/PrmDb.dat"],
                       check=True, timeout=60)
    pi_start(args)
    serial = ssh(args.pi, "awk '/^Serial/ {print $3}' /proc/cpuinfo").strip()
    # The target has no debugger: the serial number of the Pi identifies the unit
    print(f"Serial# = {serial}")


def cmd_dump(args) -> None:
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", f"{args.pi}:{args.pi_dir}/PiSensor", args.readback],
                   check=True, timeout=300)
    serial = ssh(args.pi, "awk '/^Serial/ {print $3}' /proc/cpuinfo").strip()
    print(f"Serial# = {serial}")


def cmd_collect_gcda(args) -> None:
    """Copy the coverage counts of a stopped image off the Pi, paths kept."""
    alive = ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && [ -f {PI_PID} ] && echo alive; true")
    if "alive" in alive:
        raise SystemExit("collect-gcda: stop the image first (the counts are written when it ends)")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pack = subprocess.run(["ssh", "-o", "BatchMode=yes", args.pi, f"cd {shlex.quote(args.pi_dir)}/{GCDA_DIR} && tar cf - ."],
                          check=True, capture_output=True, timeout=300)
    subprocess.run(["tar", "xf", "-", "-C", str(out)], input=pack.stdout, check=True)
    print(f"{len(list(out.rglob('*.gcda')))} .gcda files -> {out}")


def cmd_stop(args) -> None:
    pi_stop(args)
    cmd_action_release(args)


def cmd_action(args) -> None:
    if args.name == "fsw-restart":
        pi_stop(args)
        pi_start(args)
    elif args.name == "camera-hold":
        # Another process opens the camera, as a second user of the Pi would
        ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && "
                     f"(nohup rpicam-hello -n -t {int(args.seconds) * 1000} > camera-hold.log 2>&1 < /dev/null & "
                     f"echo $! > {HOLD_PID}); sleep 3")
        confirm_running(args, HOLD_PID, "the process that holds the camera")
    elif args.name == "camera-release":
        cmd_action_release(args)
    else:
        raise SystemExit(f"unknown action {args.name}")


def cmd_action_release(args) -> None:
    program = ssh(args.pi, "command -v rpicam-hello", check=False).strip()
    if program:
        stop_recorded(args, HOLD_PID, program)
    ssh(args.pi, "sleep 2")


# ----------------------------------------------------------------------
# Ground system
# ----------------------------------------------------------------------

def cmd_gds(args) -> None:
    logs = Path(args.logs)
    logs.mkdir(parents=True, exist_ok=True)
    data = logs / "yamcs-data"
    children = []

    def stop(_signum=None, _frame=None):
        for child in children:
            if child.poll() is None:
                child.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # fprime-yamcs starts its tools by name: they are beside it
    environment = dict(os.environ)
    if os.sep in args.fprime_yamcs:
        environment["PATH"] = str(Path(args.fprime_yamcs).resolve().parent) + os.pathsep + environment.get("PATH", "")
    if (args.uart is None) == (args.tcp_port is None):
        raise SystemExit("gds: give --uart (ground/feather_bridge.py) or --tcp-port (tcp_bridge.py), not both")
    link = ["--uart-device", args.uart] if args.uart else ["--tcp-port", str(args.tcp_port)]
    # Same process group as this process: fth stops the group
    children.append(subprocess.Popen(
        [args.bridge_python, args.bridge] + link + ["--tm-port", str(args.tm_port), "--tc-port", str(args.tc_port),
                                                    "--log", str(logs / "bridge.log")],
        stdout=open(logs / "bridge.out", "wb"), stderr=subprocess.STDOUT))
    children.append(subprocess.Popen(
        [args.fprime_yamcs, "-n", "--dictionary", str(Path(args.dictionary).resolve()), "--communication-selection",
         "udp", "--yamcs-config-dir", str(Path(args.yamcs_config).resolve()), "--yamcs-data-dir", str(data.resolve()),
         "--udp-downlink-port", str(args.tm_port), "--udp-uplink-port", str(args.tc_port), "--udp-tm-inject-port",
         str(args.inject_port), "--skip-browser-open", "--logs", str((logs / "yamcs-logs").resolve())],
        stdout=open(logs / "ground.log", "wb"), stderr=subprocess.STDOUT, env=environment))
    while all(child.poll() is None for child in children):
        time.sleep(1)
    stop()


def cmd_recorder(args) -> None:
    from yamcs.client import YamcsClient  # of the fprime-yamcs environment

    dictionary = load_dictionary(args.dictionary)
    ids = {c["name"]: c["id"] for c in dictionary.get("telemetryChannels", [])}
    for kind in ("telemetryChannels", "events"):
        short = [short_name(args.deployment, e["name"]) for e in dictionary.get(kind, [])]
        twice = sorted({n for n in short if short.count(n) > 1})
        if twice:
            # Reported, not refused: the deployment has such instances; a plan must not judge these names
            Path(args.logs).mkdir(parents=True, exist_ok=True)
            with open(Path(args.logs) / "name-clash.log", "a", encoding="utf-8") as log:
                log.write(f"{kind} that share a name once the subtopology is dropped: {twice}\n")
    out = Path(args.logs) / f"fprime-cli-{stamp()}"
    out.mkdir(parents=True, exist_ok=True)
    events = open(out / "event.log", "a", encoding="utf-8", buffering=1)
    channels = open(out / "channel.log", "a", encoding="utf-8", buffering=1)
    ground = open(Path(args.logs) / "ground-events.log", "a", encoding="utf-8", buffering=1)

    def on_event(event) -> None:
        extra = getattr(event, "extra", None) or {}
        name = extra.get("fprime_event_name")
        if name is None:
            # Not an event of the unit under test: a ground event (link, packet sequence) kept beside the record
            ground.write(f"{event.generation_time.isoformat()},{event.source},{event.event_type},"
                         f"{getattr(event, 'severity', '')},{event.message}\n")
            return
        text = event.message or ""
        prefix = f"[{name.split('.')[-1]}] "
        text = text[len(prefix):] if text.startswith(prefix) else text
        when = event.generation_time.isoformat()
        events.write(f"{time_fields(when)},{short_name(args.deployment, name)},{extra.get('fprime_event_id', 0)},"
                     f"EventSeverity.{extra.get('fprime_severity', 'UNKNOWN')},{text}\n")

    def on_values(data) -> None:
        for value in data.parameters:
            name = value.name.split("/", 2)[-1].replace("/", ".")
            eng = value.eng_value
            shown = json.dumps(eng, default=str) if isinstance(eng, (dict, list)) else str(eng)
            channels.write(f"{time_fields(value.generation_time.isoformat())},{short_name(args.deployment, name)},"
                           f"{ids.get(name, 0)},{shown}\n")

    names = [f"/{args.space_system}/" + name.replace(".", "/") for name in ids]
    client = None
    limit = time.time() + args.connect_s
    while True:
        try:
            client = YamcsClient(args.yamcs)
            processor = client.get_processor(args.instance, "realtime")
            client.create_event_subscription(args.instance, on_event)
            processor.create_parameter_subscription(names, on_data=on_values, abort_on_invalid=False,
                                                    send_from_cache=False)
            break
        except Exception as error:  # YAMCS is still starting
            if time.time() > limit:
                raise SystemExit(f"recorder: YAMCS at {args.yamcs} not reachable: {error}")
            time.sleep(2)
    (out / "recorder.ready").write_text("ready\n", encoding="utf-8")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        time.sleep(1)


def post_command(url: str, body: dict, name: str) -> None:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
                                     method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            reply.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"send {name}: HTTP {error.code}: {error.read().decode(errors='replace')[:300]}")


def watch_dispatch(args, opcode: int):
    """Event set when the unit reports the dispatch of ``opcode``; None when resending is off."""
    if args.resend <= 0:
        return None
    import threading

    from yamcs.client import YamcsClient

    seen = threading.Event()
    text = f"Opcode 0x{opcode:x} dispatched"

    def on_event(event) -> None:
        name = (getattr(event, "extra", None) or {}).get("fprime_event_name", "")
        if name.endswith("cmdDisp.OpCodeDispatched") and text in (event.message or ""):
            seen.set()

    client = YamcsClient(args.yamcs)
    subscription = client.create_event_subscription(args.instance, on_event)
    seen.close = lambda: (subscription.cancel(), client.close())
    return seen


def cmd_send(args) -> None:
    dictionary = load_dictionary(args.dictionary)
    entry = resolve(dictionary.get("commands", []), args.deployment, args.command)
    params = entry.get("formalParams", [])
    if len(params) != len(args.args):
        raise SystemExit(f"{args.command}: {len(params)} arguments expected, {len(args.args)} given")
    # YAMCS takes a bool as the label of its enumeration, True or False
    body = {"args": {p["name"]: (a.strip().capitalize() if p["type"].get("kind") == "bool" else a)
                     for p, a in zip(params, args.args)}}
    url = (f"http://{args.yamcs}/api/processors/{args.instance}/realtime/commands/{args.space_system}/"
           + entry["name"].replace(".", "/"))
    seen = watch_dispatch(args, entry["opcode"])
    sent = datetime.datetime.now()
    resent = 0
    while True:
        post_command(url, body, args.command)
        if seen is None or seen.wait(args.dispatch_s) or resent >= args.resend:
            break
        # The uplink has no retransmission: a command frame the unit did not report as dispatched is sent again
        resent += 1
        Path(args.logs).mkdir(parents=True, exist_ok=True)
        with open(Path(args.logs) / "resend.log", "a", encoding="utf-8") as log:
            log.write(f"{datetime.datetime.now().isoformat()},{args.command},{entry['opcode']},resend {resent}\n")
    if seen is not None:
        seen.close()
    out = Path(args.logs) / f"fprime-cli-{stamp()}"
    out.mkdir(parents=True, exist_ok=True)
    epoch = int(sent.timestamp())
    # fth compares a marker argument as a number: a decimal argument is logged as one
    logged = [int(a) if re.fullmatch(r"-?\d+", a) else a for a in args.args]
    # the name as the caller wrote it when only the case differs (parameter commands)
    logged_name = short_name(args.deployment, entry["name"])
    if logged_name != args.command and logged_name.lower() == args.command.lower():
        logged_name = args.command
    (out / "command.log").write_text(
        f"{sent.isoformat()},(2(0)-{epoch}:{sent.microsecond}),{logged_name},"
        f"{entry['opcode']},{json.dumps(logged)}\n", encoding="utf-8")


PI_ROOT = "pisensor-campaign"  # in the home directory of the ssh user on the Pi


def pi_directory(run: str, directory: str | None = None) -> str:
    """Directory on the Pi owned by the adapter: `--pi-dir` when given, else PI_ROOT/<--pi-run>."""
    if directory:
        return directory
    if not run or "/" in run or run in (".", ".."):
        raise SystemExit(f"--pi-run {run!r}: a directory name without `/` (it is put under {PI_ROOT}/)")
    return f"{PI_ROOT}/{run}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pi", default="pi", help="ssh host of the Raspberry Pi")
    parser.add_argument("--pi-run", default="sys-run", metavar="NAME",
                        help=f"the adapter owns the directory {PI_ROOT}/NAME on the Pi; no `/` in NAME, so that a bench "
                             "recipe can name it (fth rfr refuses a path outside its checkouts). The default is the "
                             "default of --remote-dir of uut.py")
    parser.add_argument("--pi-dir", help="directory on the Pi instead of the one of --pi-run, for use by hand")
    parser.add_argument("--image-args", default="", help="arguments of the image on the Pi, comma separated")
    parser.add_argument("--deployment", default="PiSensor")
    parser.add_argument("--yamcs", default="localhost:8190")
    parser.add_argument("--instance", default="fprime-project")
    parser.add_argument("--space-system", default="PiSensor_PiSensor")
    sub = parser.add_subparsers(dest="sub", required=True)
    p = sub.add_parser("flash"); p.add_argument("image"); p.add_argument("--prm"); p.set_defaults(fn=cmd_flash)
    p.add_argument("--gcov", action="store_true", help="image built for coverage: keep its counts on the Pi")
    p = sub.add_parser("collect-gcda"); p.add_argument("out"); p.set_defaults(fn=cmd_collect_gcda)
    p = sub.add_parser("dump"); p.add_argument("readback"); p.set_defaults(fn=cmd_dump)
    p = sub.add_parser("stop"); p.set_defaults(fn=cmd_stop)
    p = sub.add_parser("action"); p.add_argument("name"); p.add_argument("--seconds", default=120)
    p.set_defaults(fn=cmd_action)
    p = sub.add_parser("gds")
    p.add_argument("--dictionary", required=True); p.add_argument("--logs", required=True)
    p.add_argument("--bridge", required=True)
    p.add_argument("--uart", help="serial device of the ground radio (ground/feather_bridge.py)")
    p.add_argument("--tcp-port", type=int, help="TCP port the image connects to (tcp_bridge.py)")
    p.add_argument("--bridge-python", default=sys.executable, help="interpreter with pyserial")
    p.add_argument("--fprime-yamcs", default="fprime-yamcs"); p.add_argument("--yamcs-config", required=True)
    p.add_argument("--tm-port", type=int, default=51000); p.add_argument("--tc-port", type=int, default=51001)
    p.add_argument("--inject-port", type=int, default=51002)
    p.set_defaults(fn=cmd_gds)
    p = sub.add_parser("recorder")
    p.add_argument("--dictionary", required=True); p.add_argument("--logs", required=True)
    p.add_argument("--connect-s", type=float, default=180)
    p.set_defaults(fn=cmd_recorder)
    p = sub.add_parser("send")
    p.add_argument("--dictionary", required=True); p.add_argument("--logs", required=True)
    p.add_argument("--resend", type=int, default=2, help="times a command not reported as dispatched is sent again")
    # not a whole number of seconds: the unit sends a frame every second and hears nothing meanwhile
    p.add_argument("--dispatch-s", type=float, default=6.4, help="wait for the dispatch report before a resend")
    p.add_argument("command"); p.add_argument("args", nargs="*")
    p.set_defaults(fn=cmd_send)
    args = parser.parse_args()
    args.pi_dir = pi_directory(args.pi_run, args.pi_dir)
    args.fn(args)


if __name__ == "__main__":
    main()
