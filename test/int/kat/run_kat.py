#!/usr/bin/env python3
"""Known-answer tests of the harness, offline: `python -B test/int/kat/run_kat.py` from the repository root.

1. unit answers of the bench adapters and of the record library;
2. the stimulus replayed over a synthetic record of a healthy system (sim.py): all 12 tests pass;
3. the same with one behaviour broken at a time: the named check of the named test must not pass;
4. each planted fault of the plan, applied to the command list: its `fails` checks fail, by name.
Exit status 0 when every answer is the known one.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
INT = HERE.parent
sys.path[:0] = [str(HERE), str(INT / "bench"), str(INT / "stimulus")]
import sim  # noqa: E402
import verify_stimulus  # noqa: E402
import yamcs_recorder as recorder  # noqa: E402
import pisensor_record as rec  # noqa: E402

BASE = ["-p", "fth.pytest_plugin", "-p", "no:cacheprovider", "-q", "--fth-plan", str(INT / "stimulus" / "plan.json"),
        "--fth-bench", str(INT / "bench.json"), "--fth-dry-run"]
MANIFEST = {"repos": [{"name": "fprime", "describe": "v4.1.0"}, {"name": "uut", "describe": "c7953c9"},
                      {"name": "fprime-sensors", "describe": "v0.3.0"}, {"name": "harness", "describe": "v0.1.2"}]}
# knob -> (value, test, text that must appear among that test's failed or unverified checks)
BROKEN = [
    ("capture_fails", True, "L2-3", "event piCamera.CaptureFailed count == 0"),
    ("capture_fails", True, "L2-6", "event dpWriter.FileWritten count == 3"),
    ("clock_offset", 2.0, "L0-1", "Pi clock - bench clock"),
    ("drop_frame", True, "L2-1", "no gap, modulo 256"),
    ("corrupt_file", True, "L2-3", "CRC of each ground file"),
    ("corrupt_file", True, "L2-5", "each ground file is a product container"),
    ("class1", True, "L2-4", "class 2 and finished complete"),
    ("telemetry_gap", True, "L2-1", "largest gap between ground reception times"),
    ("small_picture", True, "L2-3", "each ground file is a product container"),
    ("extra_socket", True, "L0-1", "the process holds no TCP or UDP socket"),
    ("slow_capture", True, "L2-6", "dpWriter.FileWritten"),
    ("wrong_time", True, "L2-5", "capture time record"),
    ("stale_sample", True, "L2-5", "sample time"),
    ("tcp_frames", True, "L2-7", "TM frames received <= PacketsTransmitted rise + 2"),
    ("fatal", True, "L0-2", "severity FATAL count == 0"),
    ("keep_ignored", True, "L7-1", "the directory listing names P only"),
    ("resend", True, "L7-1", "no CFDP transaction starts after the second START_XMIT_CATALOG"),
    ("fast_downlink", True, "L2-7", "CFDP transaction duration in D >= 30 s"),
    # REQ-PiSensor-005 placeholders: the wrong records
    ("stale_sample", True, "L2-3", "sample time"),  # marked valid, sample 5 s before the capture
    ("false_invalid", True, "L2-3", "each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent"),  # marked not valid while the GPS answers
    ("false_invalid", True, "L2-6", "each piCamera event that reports a sensor unavailable has no telemetry sample of that sensor in the 2 s before it"),
    ("no_warning", True, "L2-3", "each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent"),  # placeholder, GPS silent, no LocationUnavailable event
    ("bad_placeholder", True, "L2-3", "each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent"),  # marked not valid, values not NaN
    ("placeholder_time", True, "L2-3", "each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent"),  # marked not valid, sample time not zero
    ("stray_warning", True, "L2-3", "each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent"),  # LocationUnavailable event, product marked valid
    ("stray_warning", True, "L2-6", "each piCamera event that reports a sensor unavailable has no telemetry sample of that sensor in the 2 s before it"),
]
NO_FIX = ("L2-1", "L2-2", "L2-9")  # the tests that judge gpsManager.Reading (REQ-PiSensor-003, GPS item of -012)


def pytest(args, env=None):
    return subprocess.run([sys.executable, "-B", "-m", "pytest", str(INT / "stimulus"), *BASE, *args],
                          capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env or {})))


def replay(commands, knobs, tmp, tag):
    """{test id: text of its failure section, '' when it passed}."""
    from fth.export import export
    record = Path(tmp) / tag / "record"
    sim.build(commands, record / "raw", knobs)
    export(record / "raw", record)
    manifest = Path(tmp) / "manifest.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    r = pytest(["-p", "kat_position", "--fth-run-dir", str(Path(tmp) / tag / "run"), "--fth-replay-record", str(record),
                "--fth-manifest", str(manifest), "-rA"], {"PYTHONPATH": str(HERE)})
    out = {}
    for m in re.finditer(r"^(PASSED|FAILED|ERROR) \S+::test_(L\d)_(\d)", r.stdout, re.M):
        out[f"{m.group(2)}-{m.group(3)}"] = "" if m.group(1) == "PASSED" else "?"
    for m in re.finditer(r"^_{3,} test_(L\d)_(\d) _{3,}$(.*?)(?=^_{3,} test_|^=+ )", r.stdout, re.M | re.S):
        if out.get(f"{m.group(1)}-{m.group(2)}") != "":
            out[f"{m.group(1)}-{m.group(2)}"] = "\n".join(l for l in m.group(3).splitlines() if l.startswith("E "))
    if len(out) != 12:
        raise SystemExit(f"replay produced {len(out)} verdicts:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    return out


def units():
    ev = {"type": "CdhCore.cmdDisp.NoOpStringReceived", "message": "[NoOpStringReceived] Received a NO-OP string=10",
          "generationTime": "2026-11-18T00:00:01.500Z", "receptionTime": "2026-11-18T00:00:02.250Z",
          "extra": {"fprime_severity": "ACTIVITY_HI", "fprime_event_id": 7}}
    t = recorder.epoch("2026-11-18T00:00:00Z")
    yield "event_line", recorder.event_line(ev, 1.0) == (f"TB_PROC_TIME: {t + 0.5:.6f}s, context=0,(rx={t + 2.25:.6f}),"
                                                         "CdhCore.cmdDisp.NoOpStringReceived,7,EventSeverity.ACTIVITY_HI,Received a NO-OP string=10")
    s = {"name": "/PiSensor_PiSensor/Bmp/bmpManager/Reading", "generationTime": "2026-11-18T00:00:01Z",
         "receptionTime": "2026-11-18T00:00:01.3Z", "value": {"temperature": 21.5, "pressure": 101.0}}
    yield "channel_line", recorder.channel_line(s, "/PiSensor_PiSensor/", 1.0, {"Bmp.bmpManager.Reading": 9}) == (
        f"TB_PROC_TIME: {t:.6f}s, context=0,(rx={t + 1.3:.6f}),Bmp.bmpManager.Reading,9," + '{"pressure":101.0,"temperature":21.5}')
    frames = recorder.parse_bridge("100.5 down 255 0443fe07c000\n100.6 up 255 000000000000\nnoise\n100.7 down 255 0443ff08c000\n")
    yield "parse_bridge", frames == [{"rx": 100.5, "len": 255, "scid": 0x44, "vcid": 1, "mc_count": 0xfe, "vc_count": 7},
                                     {"rx": 100.7, "len": 255, "scid": 0x44, "vcid": 1, "mc_count": 0xff, "vc_count": 8}]
    yield "frame_gaps none", rec.frame_gaps([{"rx": 1.0, "vcid": 0, "vc_count": 255}, {"rx": 2.0, "vcid": 0, "vc_count": 0}])[0] is True
    yield "frame_gaps one", rec.frame_gaps([{"rx": 1.0, "vcid": 0, "vc_count": 255}, {"rx": 2.0, "vcid": 0, "vc_count": 1}])[0] is False
    yield "frame_gaps empty", rec.frame_gaps([])[0] is False
    known = recorder.merge_transfers({}, [{"id": 3, "state": "RUNNING"}], 10.0)
    known = recorder.merge_transfers(known, [{"id": 3, "state": "COMPLETED"}], 12.0)
    known = recorder.merge_transfers(known, [{"id": 3, "state": "COMPLETED"}], 14.0)
    yield "merge_transfers", (known["3"]["first_seen"], known["3"]["finished_seen"]) == (10.0, 12.0)
    yield "crc", rec.crc(b"123456789") == 0xCBF43926
    data = sim.product(1000.25, 1000.0, {"x": 0.0, "y": 0.0, "z": 1.0}, 21.5, sim.jpeg(1))
    p = rec.decode_product(data)
    yield "decode_product", (p["metrics"]["captureTime"]["t"], p["metrics"]["temperature"], p["metrics"]["roll"],
                             rec.jpeg_size(p["jpeg"])) == (1000.25, 21.5, 0.0, (640, 480))
    for name, bad in (("flipped data bit", data[:80] + bytes([data[80] ^ 1]) + data[81:]), ("truncated", data[:-5]), ("empty", b"")):
        try:
            rec.decode_product(bad)
            yield f"decode_product refuses {name}", False
        except AssertionError:
            yield f"decode_product refuses {name}", True
    yield "roll_pitch", [round(v, 3) for v in rec.roll_pitch({"x": 0.0, "y": 1.0, "z": 1.0})] == [45.0, 0.0]


def planted(commands):
    """The plan's planted faults applied to the dry-run command list, each on one test it applies to."""
    from fth.plan import load_plan
    plan = load_plan(INT / "stimulus" / "plan.json")
    window_of = {}
    for t in plan.tests:
        for w in t.windows:
            window_of[int(w["start_id"])] = t.id
    for fault in plan.registry.planted_faults.values():
        for target in fault.applies_to:
            out, current = [], None
            for name, args in commands:
                if name == "cmdDisp.CMD_NO_OP_STRING" and int(args[0]) in window_of:
                    current = window_of[int(args[0])]
                new = fault.func(target, name, list(args)) if current == target else None
                out += [(n, list(a)) for n, a in new] if new else [(name, args)]
            yield fault.name, target, out, fault.fails[target]


def main() -> int:
    bad = 0

    def answer(name, ok, detail=""):
        nonlocal bad
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f"\n       {detail}" if detail and not ok else ""))

    for name, ok in units():
        answer(f"unit: {name}", ok)
    with tempfile.TemporaryDirectory() as tmp:
        r = pytest(["--fth-run-dir", str(Path(tmp) / "dry")])
        commands = verify_stimulus.sent(Path(tmp) / "dry")
        answer("dry run of the stimulus", r.returncode == 0 and len(commands) > 0, r.stdout[-500:])
        nominal = replay(commands, {}, tmp, "nominal")
        for test_id, text in sorted(nominal.items()):
            answer(f"healthy system: {test_id} passes", text == "", text[:600])
        no_fix = replay(commands, {"gps_silent": True}, tmp, "gps_silent")
        for test_id, text in sorted(no_fix.items()):
            if test_id in NO_FIX:
                answer(f"GPS without a fix: {test_id} fails, naming `for gpsManager.Reading in`", "for gpsManager.Reading in" in text, text[:600])
            else:
                answer(f"GPS without a fix, products with placeholders and the event: {test_id} passes", text == "", text[:600])
        done = {}
        for knob, value, test_id, needle in BROKEN:
            if (knob, value) not in done:
                done[(knob, value)] = replay(commands, {knob: value}, tmp, f"{knob}")
            text = done[(knob, value)][test_id]
            answer(f"broken ({knob}): {test_id} does not pass, naming `{needle}`", needle in text, text[:600])
        for fault, test_id, cmds, fails in planted(commands):
            text = replay(cmds, {}, tmp, f"{fault}-{test_id}")[test_id]
            failed = sorted(re.findall(r"check failed: (.*?) — seen", text))
            answer(f"planted fault {fault} on {test_id}: exactly its {len(fails)} `fails` check(s) fail, nothing is unverified",
                   failed == sorted(fails) and "Incomplete" not in text, f"failed: {failed}\n{text[:800]}")
    print(f"known-answer tests: {'ok' if not bad else f'{bad} WRONG'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
