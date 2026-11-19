#!/usr/bin/env python3
"""Bench `send` line of bench.json: one F Prime command through YAMCS, logged as fth expects.

fth's sender assumes `fprime-cli command-send`; the ground system here is fprime-yamcs, so this
script issues the command on the YAMCS HTTP API and writes the sender log fth exports from:
`<logs>/fprime-cli-yamcs-<ns>/command.log`, one line
`<UTC sent>,(<YAMCS command id>),<dictionary name>,<opcode>,<JSON argument list>`.
The command name on the command line is the plan's short name (`cmdDisp.CMD_NO_OP`); it must match
exactly one command of the dictionary by its last dotted parts.
"""
import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path


def find_command(dictionary: dict, short: str) -> dict:
    hits = [c for c in dictionary.get("commands", []) if c["name"] == short or c["name"].endswith("." + short)]
    if len(hits) != 1:
        raise SystemExit(f"yamcs_send: {short!r} matches {len(hits)} dictionary commands (need exactly 1)")
    return hits[0]


def kind_of(type_ref: dict, dictionary: dict) -> str:
    """integer | float | bool | string | enum | other, following aliases of the dictionary."""
    kind = type_ref.get("kind")
    if kind == "qualifiedIdentifier":
        for td in dictionary.get("typeDefinitions", []):
            if td.get("qualifiedName") == type_ref.get("name"):
                if td.get("kind") == "alias":
                    return kind_of(td.get("underlyingType", td.get("type", {})), dictionary)
                return td.get("kind", "other")
        return "other"
    return kind or "other"


def convert(value: str, kind: str):
    if kind == "integer":
        return int(value, 0)
    if kind == "float":
        return float(value)
    if kind == "bool":
        low = value.strip().lower()
        if low not in ("true", "false"):
            raise SystemExit(f"yamcs_send: {value!r} is not true/false")
        return low == "true"
    return value


def yamcs_name(root: str, name: str) -> str:
    return root.rstrip("/") + "/" + name.replace(".", "/")


def log_line(sent: datetime.datetime, command_id: str, name: str, opcode: int, args: list) -> str:
    gen = str(command_id).replace(")", "_").replace(",", ";")
    # decimal integers are logged as numbers (fth finds a marker by its integer argument), all else as text
    shown = [int(a) if re.fullmatch(r"-?[0-9]+", str(a)) else str(a) for a in args]
    return f"{sent.strftime('%Y-%m-%dT%H:%M:%S.%f')},({gen}),{name},{opcode},{json.dumps(shown)}"


def write_log(logs: Path, line: str) -> Path:
    d = logs / f"fprime-cli-yamcs-{time.time_ns()}"
    d.mkdir(parents=True, exist_ok=False)
    (d / "command.log").write_text(line + "\n", encoding="utf-8")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True, help="YAMCS HTTP address, host:port")
    ap.add_argument("--instance", required=True)
    ap.add_argument("--root", required=True, help="XTCE space system of the deployment, e.g. /PiSensor_PiSensor")
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--logs", required=True, help="sender log directory (record/raw/cmd)")
    ap.add_argument("command")
    ap.add_argument("args", nargs="*")
    a = ap.parse_args(argv)

    dictionary = json.loads(Path(a.dictionary).read_text(encoding="utf-8"))
    cmd = find_command(dictionary, a.command)
    params = cmd.get("formalParams", [])
    if len(params) != len(a.args):
        raise SystemExit(f"yamcs_send: {cmd['name']} takes {len(params)} argument(s), got {len(a.args)}")
    values = {p["name"]: convert(v, kind_of(p["type"], dictionary)) for p, v in zip(params, a.args)}

    from yamcs.client import YamcsClient
    client = YamcsClient(a.url)
    try:
        processor = client.get_processor(a.instance, "realtime")
        sent = datetime.datetime.now(datetime.timezone.utc)
        issued = processor.issue_command(yamcs_name(a.root, cmd["name"]), args=values or None)
        write_log(Path(a.logs), log_line(sent, issued.id, cmd["name"], int(cmd["opcode"]), a.args))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
