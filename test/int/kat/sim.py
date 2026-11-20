"""A synthetic raw record of the PiSensor plan, for the known-answer tests (no bench, no flight code).

`build(commands, raw_dir, knobs)` plays the command list of a dry run of the stimulus against a model of
the deployment, as the SSDD and the piCamera SDD describe it, and writes record/raw exactly as the bench
adapters would: sender logs (the layout of yamcs_bench.py send), recorder logs (yamcs_recorder.event_line /
channel_line), cfdp.json, frames.json, files/, actions/, dictionary.json. Knobs break one behaviour each.
"""
import datetime
import hashlib
import io
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "bench"))
import yamcs_recorder as recorder  # noqa: E402

ROOT = "/PiSensor_PiSensor/"
DEPLOYMENT = "PiSensor"
T0 = 1_800_000_000.0
LAT, LON = 34.2000, -118.1700
COMMANDS = {"cmdDisp.CMD_NO_OP": 0x1000, "cmdDisp.CMD_NO_OP_STRING": 0x1001, "version.VERSION": 0x2000,
            "piCamera.CAPTURE": 0x10008000, "fileManager.CalculateCrc": 0x3000, "fileManager.ListDirectory": 0x3001,
            "dpCat.BUILD_CATALOG": 0x4000, "dpCat.START_XMIT_CATALOG": 0x4001, "cfdpManager.FileInDefaultKeep_PRM_SET": 0x5000}
PLATFORM = ("MODEL=Raspberry Pi 5 Model B Rev 1.0\n--- os-release\nVERSION_ID=\"13\"\nVERSION_CODENAME=trixie\n"
            "--- rpi-issue\nRaspberry Pi reference 2025-10-01\n--- long-bit\n64\n")
SOCKETS = "PID=4242\nEXE=/home/fprime/pisensor-campaign/sys/PiSensor\n--- sockets\n--- devices\n/dev/spidev0.0\n/dev/i2c-1\n/dev/ttyAMA0\n"
DEFAULTS = {"capture_fails": False, "clock_offset": 0.1, "drop_frame": False, "corrupt_file": False, "class1": False,
            "telemetry_gap": False, "small_picture": False, "extra_socket": False, "slow_capture": False,
            "stale_sample": False, "tcp_frames": False, "fatal": False, "keep_ignored": False, "fast_downlink": False, "resend": False, "wrong_time": False,
            # GPS without a fix (REQ-PiSensor-005 placeholders) and the wrong records around it
            # each of the others names a metric group (temperature, location, attitude) or is False
            "gps_silent": False, "false_invalid": False, "no_warning": False, "bad_placeholder": False,
            "placeholder_time": False, "stray_warning": False, "valid_absent": False, "flag_one": False}
GROUP = {"temperature": ("Bmp/", "Temperature unavailable: SENSOR_NO_DATA code 0; temperature stored as NaN"),
         "location": ("Gps/", "Location unavailable: SENSOR_NO_DATA code 0; latitude and longitude stored as NaN"),
         "attitude": ("MpuImu/", "Attitude unavailable: SENSOR_NO_DATA code 0; roll and pitch stored as NaN")}


def jpeg(seed: int, size=(640, 480)) -> bytes:
    from PIL import Image
    img = Image.new("RGB", size, (seed * 37 % 256, seed * 91 % 256, seed * 53 % 256))
    out = io.BytesIO()
    img.save(out, "JPEG")
    return out.getvalue()


def _time(t: float) -> bytes:
    return struct.pack(">HBII", 2, 0, int(t), int(round((t - int(t)) * 1e6)))


def product(t: float, sample_t: float, acc: dict, temperature: float, picture: bytes, lacking=None, true=0xFF) -> bytes:
    """A `Capture` container as Fw::DpContainer writes it (see stimulus/pisensor_record.decode_product)."""
    import math
    roll = math.degrees(math.atan2(acc["y"], acc["z"]))
    pitch = math.degrees(math.atan2(-acc["x"], math.sqrt(acc["y"] ** 2 + acc["z"] ** 2)))
    # lacking: {group: (values kept finite, sample time)} for the groups stored as marked not valid
    lacking, nan = lacking or {}, float("nan")
    val = lambda g, v: v if g not in lacking or lacking[g][0] else nan
    tail = lambda g: _time(lacking[g][1] if g in lacking else sample_t) + bytes([0 if g in lacking else true])
    metrics = (_time(t) + struct.pack(">dd", val("location", LAT), val("location", LON)) + tail("location")
               + struct.pack(">ff", val("attitude", roll), val("attitude", pitch)) + tail("attitude")
               + struct.pack(">f", val("temperature", temperature)) + tail("temperature"))
    body = struct.pack(">I", 0x10008000) + metrics + struct.pack(">IQ", 0x10008001, len(picture)) + picture
    head = struct.pack(">HII", 5, 0x10008000, 0) + _time(t) + bytes([0]) + bytes(32) + bytes([0]) + struct.pack(">Q", len(body))
    crc = lambda b: struct.pack(">I", zlib.crc32(b) & 0xFFFFFFFF)
    return head + crc(head) + body + crc(body)


def iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat()


def build(commands: list, raw_dir, knobs: dict | None = None) -> None:
    k = dict(DEFAULTS, **(knobs or {}))
    # groups whose sensor gives no sample: the GPS over the whole run (no fix), the others in the 3 s up to each capture
    quiet = {k[x] for x in ("no_warning", "bad_placeholder", "placeholder_time") if k[x]} | ({"location"} if k["gps_silent"] else set())
    captured = []
    raw = Path(raw_dir)
    for d in ("cmd", "fprime-cli-yamcs", "files", "actions"):
        (raw / d).mkdir(parents=True, exist_ok=True)
    dictionary = {"commands": [{"name": n, "opcode": o, "formalParams": []} for n, o in COMMANDS.items()], "telemetryChannels": []}
    (raw / "dictionary.json").write_text(json.dumps(dictionary), encoding="utf-8")
    events, cmd_lines, transfers, actions, stored, made, downlinked = [], [], [], [], {}, [], set()
    state = {"t": T0, "keep": False, "n": 0, "busy_until": 0.0, "window_start": T0}
    acc = lambda t: {"x": 0.01, "y": 0.02 + 0.001 * (int(t) % 3), "z": 1.0}
    temp = lambda t: 21.0 + 0.01 * (int(t) % 5)

    def ev(t, name, severity, text):
        events.append((t, {"type": name, "message": f"[{name.rsplit('.', 1)[-1]}] {text}", "generationTime": iso(t + 1.0),
                           "receptionTime": iso(t + 0.3), "extra": {"fprime_severity": severity, "fprime_event_id": 1}}))

    def act(t, name, out):
        actions.append({"name": name, "start": t, "end": t + 0.5, "rc": 0, "stdout": out})

    prev, skip = None, False
    for name, args in commands:
        if skip and name != "cmdDisp.CMD_NO_OP_STRING":
            continue  # the stimulus stops a window at a capture that wrote no product
        skip = False
        if name == "cmdDisp.CMD_NO_OP" and prev == "dpCat.START_XMIT_CATALOG":
            state["t"] += 15  # the one command the plan sends during a downlink (L2-8)
        elif name == "cmdDisp.CMD_NO_OP" and prev == name and state["busy_until"] > state["t"]:
            state["t"] += 1  # a second copy sent at once (planted fault)
        elif state["busy_until"] > state["t"]:
            state["t"] = max(state["t"] + 30, state["busy_until"] + 5)  # the stimulus waits for the downlink
        elif name == "dpCat.BUILD_CATALOG":
            state["t"] += 30
        elif name == "cmdDisp.CMD_NO_OP":
            state["t"] += 10
        else:
            state["t"] += 3
        if name == "fileManager.CalculateCrc" and str(args[0]).startswith("<P"):  # dry-run placeholder of a UUT-chosen name
            args = [made[int(str(args[0])[2:-1]) - 1]] if len(made) >= int(str(args[0])[2:-1]) else args
        if name == "cmdDisp.CMD_NO_OP_STRING" and str(args[0]) == "31":
            state["t"] += 60
        t = state["t"]
        op = COMMANDS[name]
        shown = [int(a) if re.fullmatch(r"-?\d+", str(a)) else str(a) for a in args]
        sent = datetime.datetime.fromtimestamp(t)  # local time without a zone, as the bench sender logs it
        cmd_lines.append(f"{sent.isoformat()},(2(0)-{int(t)}:{sent.microsecond}),{DEPLOYMENT}.{name},{op},{json.dumps(shown)}")
        ev(t + 0.10, "CdhCore.cmdDisp.OpCodeDispatched", "COMMAND", f"Opcode 0x{op:x} dispatched to port 1")
        done = t + 0.2
        ok = True
        if name == "cmdDisp.CMD_NO_OP":
            ev(t + 0.15, "CdhCore.cmdDisp.NoOpReceived", "ACTIVITY_HI", "Received a NO-OP command")
        elif name == "cmdDisp.CMD_NO_OP_STRING":
            ev(t + 0.15, "CdhCore.cmdDisp.NoOpStringReceived", "ACTIVITY_HI", f"Received a NO-OP string={args[0]}")
            if str(args[0]) == "10":
                act(t + 0.5, "clock", json.dumps({"offset_s": k["clock_offset"], "uncertainty_s": 0.02}))
                act(t + 1.2, "platform", PLATFORM)
                act(t + 2.0, "sockets", SOCKETS.replace("--- sockets\n", "--- sockets\nudp UNCONN 0 0 0.0.0.0:50000 users:((\"PiSensor\",pid=4242,fd=9))\n") if k["extra_socket"] else SOCKETS)
            if str(args[0]) == "20":
                act(t + 1.2, "platform", PLATFORM)
            if str(args[0]) == "42405" and k["fatal"]:
                ev(t + 0.17, "CdhCore.fatalHandler.Fatal", "FATAL", "Assert")
        elif name == "version.VERSION":
            ev(t + 0.15, "CdhCore.version.FrameworkVersion", "ACTIVITY_LO", "Framework Version: [v4.1.0]")
            ev(t + 0.16, "CdhCore.version.ProjectVersion", "ACTIVITY_LO", "Project Version: [c7953c9]")
            ev(t + 0.17, "CdhCore.version.LibraryVersions", "ACTIVITY_LO", "Library Versions: [fprime-sensors@v0.3.0]")
        elif name == "piCamera.CAPTURE":
            ev(t + 0.15, "PiSensor.piCamera.CaptureStarted", "ACTIVITY_LO", "Capture started")
            if k["capture_fails"]:
                ev(t + 0.5, "PiSensor.piCamera.CaptureFailed", "WARNING_HI", "Capture failed: SENSOR_STALE at step 1 code 0")
                ok = False
                done = t + 0.6
                skip = True
            else:
                state["n"] += 1
                took = 35.0 if k["slow_capture"] else 1.5
                tc = t + 0.4 - (10.0 if k["wrong_time"] else 0.0)
                sample_t = tc - (5.0 if k["stale_sample"] else 0.0) - (tc % 1.0)
                captured.append(tc)
                lacking = {g: (g == k["bad_placeholder"], sample_t if g == k["placeholder_time"] else 0.0)
                           for g in GROUP if g in quiet or g == k["false_invalid"]}  # stored as placeholders
                for g in GROUP:  # the order piCamera sends them in
                    if (g in lacking and g != k["no_warning"]) or g == k["stray_warning"]:
                        ev(t + 0.45, f"PiSensor.piCamera.{g.capitalize()}Unavailable", "WARNING_LO", GROUP[g][1])
                data = product(tc, sample_t, acc(tc), temp(tc), jpeg(state["n"], (320, 240) if k["small_picture"] else (640, 480)),
                               lacking, 0x01 if k["flag_one"] else 0xFF)
                fname = f"dp/Dp_{0x10008000:08d}_{int(tc):08d}_{int((tc % 1) * 1e6):08d}.fdp"
                stored[fname] = data
                made.append(fname)
                ev(t + took, "DataProducts.dpWriter.FileWritten", "ACTIVITY_LO", f"Wrote {len(data)} bytes to file {fname}")
                ev(t + took + 0.05, "PiSensor.piCamera.CaptureCompleted", "ACTIVITY_HI", f"Capture completed: {len(data)} bytes")
                done = t + took + 0.1
                state["t"] = done
        elif name == "fileManager.CalculateCrc":
            data = stored.get(str(args[0]))
            if data is None:
                ok = False
            else:
                ev(t + 0.15, "FileHandling.fileManager.CalculateCrcSucceeded", "ACTIVITY_HI", f"{args[0]} has CRC value 0x{~zlib.crc32(data) & 0xFFFFFFFF:x}")
        elif name == "fileManager.ListDirectory":
            ev(t + 0.15, "FileHandling.fileManager.ListDirectoryStarted", "ACTIVITY_HI", f"Listing contents of directory {args[0]}")
            for i, (fname, data) in enumerate([("dp/DpState.dat", b"\0" * 31)] + sorted(stored.items())):
                ev(t + 0.16 + i * 0.01, "FileHandling.fileManager.DirectoryListing", "ACTIVITY_HI", f"Directory {args[0]}: {fname.rsplit('/', 1)[-1]} ({len(data)} bytes)")
            ev(t + 0.19, "FileHandling.fileManager.ListDirectorySucceeded", "ACTIVITY_HI", f"Directory {args[0]} contains {len(stored) + 1} files")
        elif name == "cfdpManager.FileInDefaultKeep_PRM_SET":
            state["keep"] = not k["keep_ignored"]
        elif name == "dpCat.START_XMIT_CATALOG":
            ev(t + 0.15, "DataProducts.dpCat.CatalogXmitRangeStarted", "ACTIVITY_HI", "Catalog transmission started for priorities 0 through 4294967295")
            at, each = t + 1.0, (2.0 if k["fast_downlink"] else 35.0)
            for fname, data in sorted(stored.items()):
                if fname in downlinked and not k["resend"]:
                    continue  # the catalog holds each product until it was transmitted once
                downlinked.add(fname)
                tid = len(transfers) + 1
                sent = data[:-1] + bytes([data[-1] ^ 1]) if k["corrupt_file"] else data
                (raw / "files" / f"{tid}-{Path(fname).name}").write_bytes(sent)
                transfers.append({"id": tid, "startTime": iso(at), "state": "COMPLETED", "bucket": "cfdpDown", "objectName": Path(fname).name,
                                  "remotePath": fname, "direction": "DOWNLOAD", "totalSize": len(data), "sizeTransferred": len(data),
                                  "reliable": not k["class1"], "first_seen": at + 0.5, "finished_seen": at + each,
                                  "file": f"files/{tid}-{Path(fname).name}", "file_sha256": hashlib.sha256(sent).hexdigest()})
                at += each
            ev(at + 0.5, "DataProducts.dpCat.CatalogXmitCompleted", "ACTIVITY_LO", f"Catalog transmission completed.  {sum(map(len, stored.values()))} bytes transmitted.")
            state["busy_until"] = at + 1.0
            if not state["keep"]:
                stored.clear()
        if name == "cmdDisp.CMD_NO_OP_STRING" and int(args[0]) in (30, 32, 40, 42, 44, 46, 50, 53, 60):
            stored.clear()  # the clean_products bench action before the window
            made.clear()
        if ok:
            ev(done, "CdhCore.cmdDisp.OpCodeCompleted", "COMMAND", f"Opcode 0x{op:x} completed")
        else:
            ev(done, "CdhCore.cmdDisp.OpCodeError", "COMMAND", f"Opcode 0x{op:x} completed with error EXECUTION_ERROR")
        prev = name
    end = state["t"] + 5

    # telemetry at 1 Hz and frames at 4 Hz over the whole run
    ch, frames, sent_frames, tsec = [], [], 0, T0
    while tsec < end:
        gap = k["telemetry_gap"] and T0 + 20 <= tsec < T0 + 28
        for q in range(4):
            tf = tsec + q * 0.25
            sent_frames += 1
            if not (k["drop_frame"] and sent_frames % 97 == 0):
                frames.append({"rx": tf + 0.3, "len": 255, "scid": 68, "vcid": 0, "mc_count": sent_frames % 256, "vc_count": sent_frames % 256})
            if k["tcp_frames"]:
                frames.append({"rx": tf + 0.31, "len": 255, "scid": 68, "vcid": 1, "mc_count": 0, "vc_count": sent_frames % 256})
        if not gap:
            for nm, val in (("MpuImu/imuManager/Reading", {"acceleration": acc(tsec), "rotation": {"x": 0.1, "y": 0.0, "z": 0.2}, "temperature": 25.0}),
                            ("Bmp/bmpManager/Reading", {"pressure": 101.3, "temperature": temp(tsec), "altitude": 350.0}),
                            ("Gps/gpsManager/Reading", {"latitude": LAT, "longitude": LON, "altitude": 350.0}),
                            ("Radio/rfm69Manager/PacketsTransmitted", sent_frames), ("Radio/rfm69Manager/PacketsReceived", int(tsec - T0))):
                if k["gps_silent"] and nm.startswith("Gps/"):
                    continue
                if any(nm.startswith(GROUP[g][0]) and any(tc - 3.0 <= tsec <= tc + 1.0 for tc in captured) for g in quiet - ({"location"} if k["gps_silent"] else set()) | ({k["valid_absent"]} if k["valid_absent"] else set())):
                    continue
                ch.append({"name": ROOT + nm, "generationTime": iso(tsec + 1.0), "receptionTime": iso(tsec + 0.3), "value": val})
        tsec += 1.0

    events.sort(key=lambda e: e[0])
    (raw / "fprime-cli-yamcs" / "event.log").write_text("".join(recorder.event_line(e, 1.0, DEPLOYMENT) + "\n" for _, e in events), encoding="utf-8")
    (raw / "fprime-cli-yamcs" / "channel.log").write_text("".join(recorder.channel_line(s, ROOT, 1.0, {}, DEPLOYMENT) + "\n" for s in ch), encoding="utf-8")
    for i, line in enumerate(cmd_lines):
        d = raw / "cmd" / f"fprime-cli-yamcs-{i:06d}"
        d.mkdir()
        (d / "command.log").write_text(line + "\n", encoding="utf-8")
    (raw / "cfdp.json").write_text(json.dumps({"updated": end, "transfers": transfers}), encoding="utf-8")
    (raw / "frames.json").write_text(json.dumps({"updated": end, "frames": frames}), encoding="utf-8")
    for i, a in enumerate(actions):
        (raw / "actions" / f"{i + 1:04d}-{a['name']}.json").write_text(json.dumps(a), encoding="utf-8")
