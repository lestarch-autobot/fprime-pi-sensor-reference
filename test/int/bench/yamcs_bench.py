#!/usr/bin/env python3
"""Bench adapter between fth (fprime-testing-harness) and the PiSensor bench.

fth drives a bench through the command lines of ``bench.json`` and reads the
recorder and sender logs in the fprime-cli log format. This bench has no
fprime-gds: the ground system is fprime-yamcs behind the RFM69 bridge and the
unit under test is a Linux process on the Raspberry Pi. Each subcommand below is
one ``bench.json`` line:

  flash     copy the image to the Pi, stop the image this adapter started
            before, start the new one, print the Pi serial number
  dump      copy the image file back from the Pi (read-back)
  gds       run the RFM69 bridge and fprime-yamcs until terminated
  recorder  write the events and channels YAMCS receives as event.log and
            channel.log
  send      send one command through YAMCS and write command.log
  action    bench actions on the Pi: fsw-restart, camera-hold, camera-release
  stop      stop the image on the Pi (bench release)

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
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PI_PID = "fsw.pid"
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

def pi_stop(args) -> None:
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} 2>/dev/null || exit 0; "
                 f"if [ -f {PI_PID} ]; then kill $(cat {PI_PID}) 2>/dev/null; sleep 2; "
                 f"kill -9 $(cat {PI_PID}) 2>/dev/null; rm -f {PI_PID}; fi; true")


def pi_start(args) -> None:
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && mkdir -p run && cd run && "
                 f"(nohup ../PiSensor >> fsw.log 2>&1 < /dev/null & echo $! > ../{PI_PID})")


def cmd_flash(args) -> None:
    ssh(args.pi, f"mkdir -p {shlex.quote(args.pi_dir)}")
    pi_stop(args)
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} && rm -rf run PiSensor")
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", args.image, f"{args.pi}:{args.pi_dir}/PiSensor"], check=True,
                   timeout=300)
    ssh(args.pi, f"chmod +x {shlex.quote(args.pi_dir)}/PiSensor")
    pi_start(args)
    serial = ssh(args.pi, "awk '/^Serial/ {print $3}' /proc/cpuinfo").strip()
    # The target has no debugger: the serial number of the Pi identifies the unit
    print(f"Serial# = {serial}")


def cmd_dump(args) -> None:
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes", f"{args.pi}:{args.pi_dir}/PiSensor", args.readback],
                   check=True, timeout=300)
    serial = ssh(args.pi, "awk '/^Serial/ {print $3}' /proc/cpuinfo").strip()
    print(f"Serial# = {serial}")


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
    elif args.name == "camera-release":
        cmd_action_release(args)
    else:
        raise SystemExit(f"unknown action {args.name}")


def cmd_action_release(args) -> None:
    ssh(args.pi, f"cd {shlex.quote(args.pi_dir)} 2>/dev/null || exit 0; "
                 f"if [ -f {HOLD_PID} ]; then kill $(cat {HOLD_PID}) 2>/dev/null; rm -f {HOLD_PID}; sleep 2; fi; true")


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
    environment["PATH"] = str(Path(args.fprime_yamcs).resolve().parent) + os.pathsep + environment.get("PATH", "")
    # Same process group as this process: fth stops the group
    children.append(subprocess.Popen(
        [args.bridge_python, args.bridge, "--uart-device", args.uart, "--tm-port", str(args.tm_port), "--tc-port",
         str(args.tc_port), "--log", str(logs / "bridge.log")],
        stdout=open(logs / "bridge.out", "wb"), stderr=subprocess.STDOUT))
    children.append(subprocess.Popen(
        [args.fprime_yamcs, "-n", "--dictionary", str(Path(args.dictionary).resolve()), "--communication-selection",
         "udp", "--yamcs-config-dir", args.yamcs_config, "--yamcs-data-dir", str(data.resolve()),
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
    out = Path(args.logs) / f"fprime-cli-{stamp()}"
    out.mkdir(parents=True, exist_ok=True)
    events = open(out / "event.log", "a", encoding="utf-8", buffering=1)
    channels = open(out / "channel.log", "a", encoding="utf-8", buffering=1)

    def on_event(event) -> None:
        extra = getattr(event, "extra", None) or {}
        name = extra.get("fprime_event_name")
        if name is None:
            return  # not an event of the unit under test
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


def cmd_send(args) -> None:
    dictionary = load_dictionary(args.dictionary)
    entry = resolve(dictionary.get("commands", []), args.deployment, args.command)
    params = entry.get("formalParams", [])
    if len(params) != len(args.args):
        raise SystemExit(f"{args.command}: {len(params)} arguments expected, {len(args.args)} given")
    body = {"args": {p["name"]: a for p, a in zip(params, args.args)}}
    url = (f"http://{args.yamcs}/api/processors/{args.instance}/realtime/commands/{args.space_system}/"
           + entry["name"].replace(".", "/"))
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
                                     method="POST")
    sent = datetime.datetime.now()
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            reply.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f"send {args.command}: HTTP {error.code}: {error.read().decode(errors='replace')[:300]}")
    out = Path(args.logs) / f"fprime-cli-{stamp()}"
    out.mkdir(parents=True, exist_ok=True)
    epoch = int(sent.timestamp())
    (out / "command.log").write_text(
        f"{sent.isoformat()},(2(0)-{epoch}:{sent.microsecond}),{short_name(args.deployment, entry['name'])},"
        f"{entry['opcode']},{json.dumps(list(args.args))}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pi", default="pi", help="ssh host of the Raspberry Pi")
    parser.add_argument("--pi-dir", default="pisensor-campaign/fth-uut", help="directory on the Pi, owned by the adapter")
    parser.add_argument("--deployment", default="PiSensor")
    parser.add_argument("--yamcs", default="localhost:8190")
    parser.add_argument("--instance", default="fprime-project")
    parser.add_argument("--space-system", default="PiSensor_PiSensor")
    sub = parser.add_subparsers(dest="sub", required=True)
    p = sub.add_parser("flash"); p.add_argument("image"); p.set_defaults(fn=cmd_flash)
    p = sub.add_parser("dump"); p.add_argument("readback"); p.set_defaults(fn=cmd_dump)
    p = sub.add_parser("stop"); p.set_defaults(fn=cmd_stop)
    p = sub.add_parser("action"); p.add_argument("name"); p.add_argument("--seconds", default=120)
    p.set_defaults(fn=cmd_action)
    p = sub.add_parser("gds")
    p.add_argument("--dictionary", required=True); p.add_argument("--logs", required=True)
    p.add_argument("--bridge", required=True); p.add_argument("--uart", required=True)
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
    p.add_argument("command"); p.add_argument("args", nargs="*")
    p.set_defaults(fn=cmd_send)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
