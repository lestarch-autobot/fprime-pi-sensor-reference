"""Record access shared by the PiSensor stimulus tests and the plan's helper predicates.

Everything here reads the run's record (record/raw and its export); nothing talks to the bench.
Ground reception times come from the `rx=` field the YAMCS recorder writes on every row; the product
decoder follows Components/PiCamera/docs/sdd.md section 4 and Fw/Dp/DpContainer.hpp.
"""
import datetime
import json
import math
import re
import struct
import sys
import tempfile
import time
import zlib
from pathlib import Path

RX = re.compile(r"rx=([0-9.]+)")
MARK = re.compile(r"cmdDisp\.NoOpStringReceived,\d+,EventSeverity\.\w+,Received a NO-OP string=(\d+)$")
WRITTEN = re.compile(r"dpWriter\.FileWritten,\d+,EventSeverity\.\w+,Wrote \d+ bytes to file (\S+)$")
OPCODE = re.compile(r"Opcode (0x[0-9a-fA-F]+)")
TIME_SIZE = 11  # Fw.TimeValue: time base U16, context U8, seconds U32, microseconds U32
METRICS_SIZE = 4 * TIME_SIZE + 8 + 8 + 1 + 4 + 4 + 1 + 4 + 1
# Metric groups of a product (REQ-PiSensor-005): flag, values, sample time, telemetry channel of the sensor,
# event piCamera sends when it stores the group as placeholders.
GROUPS = (("temperature", "temperatureValid", ("temperature",), "temperatureTime", "bmpManager.Reading", "piCamera.TemperatureUnavailable"),
          ("location", "locationValid", ("latitude", "longitude"), "locationTime", "gpsManager.Reading", "piCamera.LocationUnavailable"),
          ("attitude", "attitudeValid", ("roll", "pitch"), "attitudeTime", "imuManager.Reading", "piCamera.AttitudeUnavailable"))
_cache = {}


def _arg(name):
    for i, a in enumerate(sys.argv):
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def raw_dir():
    """record/raw of this pytest session: the replayed record's, else the live run's; None in a dry run."""
    replay = _arg("--fth-replay-record")
    if replay:
        return Path(replay) / "raw"
    live = _arg("--fth-run-dir")
    if live and "--fth-dry-run" not in sys.argv:
        return Path(live) / "record" / "raw"
    return None


def live():
    return _arg("--fth-replay-record") is None and raw_dir() is not None


def caught_up(channel, since):
    """True when a sample of `channel` with a unit time of `since` (UTC epoch seconds) or later is on the ground."""
    log = raw_dir() / "fprime-cli-yamcs" / "channel.log"
    if not log.is_file():
        return False
    for line in reversed(log.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]):
        if f".{channel}," in line:
            return float(line.split("TB_PROC_TIME: ", 1)[1].split("s,", 1)[0]) >= since
    return False


def exported():
    """events/channels rows of the export with their ground reception time (`rx`), indexed like fth's rows."""
    raw = raw_dir()
    logs = sorted(raw.glob("fprime-cli-*/*.log"))
    key = tuple((str(p), p.stat().st_size) for p in logs)
    if _cache.get("key") != key:
        from fth.export import export
        with tempfile.TemporaryDirectory() as tmp:
            export(raw, tmp)
            out = {}
            for kind in ("events", "channels"):
                rows = [json.loads(l) for l in (Path(tmp) / f"{kind}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
                for r in rows:
                    m = RX.search(r.get("gen", ""))
                    r["rx"] = float(m.group(1)) if m else None
                out[kind] = rows
        _cache.update(key=key, rows=out)
    return _cache["rows"]


def epoch(value):
    """UTC epoch seconds of an ISO-8601 time. YAMCS writes the zone; the bench program that sends commands (yamcs_bench.py send)
    and its resend log write the local time of the workstation without one, so a time without a zone is
    local time: judge a record in the time zone of the bench that made it."""
    value = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.astimezone()
    return value.timestamp()


def rx(row):
    """Ground reception time (UTC epoch seconds) of an fth event or channel row."""
    return exported()["events" if row.kind == "event" else "channels"][row.idx - 1]["rx"]


def bounds(w):
    """Ground reception times of the window's START and END marker events."""
    return rx(w.start_marker), rx(w.end_marker)


def resends(w, marker_opcode):
    """Resends the bench logged (cmd/resend.log) between the two markers, marker commands apart."""
    t0, t1 = epoch(w.cmds[0].sent), epoch(w.cmds[-1].sent)
    rows = [l.split(",") for f in raw_dir().glob("**/resend.log") for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return len([r for r in rows if int(r[2]) != marker_opcode and t0 <= epoch(r[0]) <= t1])


def snapshot(name, after):
    """record/raw/<name> (cfdp.json, frames.json) as the recorder last wrote it; it must have been written
    after `after` (the window's END marker), else the recorder stopped and the file cannot judge the window."""
    path = raw_dir() / name
    end = time.monotonic() + (15 if live() else 0)
    while True:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        if data is not None and data.get("updated", 0) > after:
            return data
        assert time.monotonic() < end, f"record/raw/{name} was not written after the window closed"
        time.sleep(0.2)


def actions(w, name):
    """Results of bench action `name` that ran between the window's markers (ground time)."""
    t0, t1 = bounds(w)
    out = []
    for p in sorted((raw_dir() / "actions").glob(f"*-{name}.json")):
        a = json.loads(p.read_text(encoding="utf-8"))
        if t0 <= a["start"] and a["end"] <= t1:
            out.append(a)
    return out


def value(row):
    """A channel sample's value as the recorder wrote it (JSON)."""
    return json.loads(row.raw) if isinstance(row.raw, str) else row.raw


# ---------------------------------------------------------------- stimulus: names the UUT chose
def sampled(channel, t, span_s, after_s=0.0):
    """Unit times of the samples of `channel` in the whole record from span_s before unit time t to after_s after it."""
    return [r["fsw"] for r in exported()["channels"] if r["name"].endswith("." + channel) and t - span_s <= r["fsw"] <= t + after_s]


def name_time(name):
    """Time tag in a product file name (`Dp_<id>_<seconds>_<microseconds>.fdp`): the capture time."""
    m = re.search(r"_(\d+)_(\d+)\.fdp", name)
    return int(m.group(1)) + int(m.group(2)) / 1e6 if m else None


def products(start_id, count):
    """File names of the first `count` dpWriter.FileWritten events after the last marker `start_id`.

    Dry run: placeholders. Fewer events than asked raises LookupError (live after a timed-out wait, and
    in replay of that same record, so both stop sending at the same step)."""
    raw = raw_dir()
    if raw is None:
        return [f"<P{k + 1}>" for k in range(count)]
    names = None
    for log in sorted(raw.glob("fprime-cli-*/event.log")):
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = MARK.search(line)
            if m and int(m.group(1)) == int(start_id):
                names = []
            m = WRITTEN.search(line)
            if m and names is not None:
                names.append(m.group(1))
    if names is None or len(names) < count:
        raise LookupError(f"{0 if names is None else len(names)} product(s) written after marker {start_id}, {count} expected")
    return names[:count]


# ---------------------------------------------------------------- transfers, files, frames
def transfers(w):
    """YAMCS downlink transfer records that started between the window's markers (ground time)."""
    t0, t1 = bounds(w)
    data = snapshot("cfdp.json", t1)
    return [t for t in data["transfers"] if t.get("direction") == "DOWNLOAD" and t0 <= epoch(t["startTime"]) <= t1]


def arrived(w):
    """{product file name: bytes} of the files received in the window and copied to record/raw/files."""
    out = {}
    for t in transfers(w):
        if t.get("state") == "COMPLETED" and t.get("file"):
            name = Path(t.get("remotePath") or t["objectName"]).name
            out[name] = (raw_dir() / t["file"]).read_bytes()
    return out


def frames(w):
    t0, t1 = bounds(w)
    data = snapshot("frames.json", t1)
    return [f for f in data["frames"] if t0 <= f["rx"] <= t1]


LOST_FRAME_NOTE = "THIS TEST'S REPORT MAY BE ERRONEOUS: lost frames"


def frame_gaps(rows):
    """(holds, seen): frames arrived; the frames lost, modulo 256, in the frame counts of the virtual channels are
    counted, never refused (human ruling of 2026-11-23). With one or more lost, `seen` carries the count and
    LOST_FRAME_NOTE, so both are in the check outcomes of the test (junit.xml, quick-look page)."""
    last, gaps, lost = {}, [], 0
    for f in rows:
        prev = last.get(f["vcid"])
        if prev is not None and (f["vc_count"] - prev) % 256 != 1:
            gaps.append(f"vc {f['vcid']}: {prev} -> {f['vc_count']} at {f['rx']:.3f}")
            lost += (f["vc_count"] - prev - 1) % 256
        last[f["vcid"]] = f["vc_count"]
    return (
        bool(rows),
        f"{len(rows)} frames, {lost} lost in {len(gaps)} gap(s)"
        + (f". {LOST_FRAME_NOTE} (" + "; ".join(gaps[:3]) + ")" if gaps else ""),
    )


# ---------------------------------------------------------------- the product container
def crc(data):
    """CRC-32 as zlib computes it: the header and data hashes of a product container."""
    return zlib.crc32(data) & 0xFFFFFFFF


def file_crc(data):
    """F Prime file CRC as fileManager.CalculateCrc reports it: the CRC-32 that zlib computes, without the
    final inversion (seen on the first live product: 0x67b852b1 on board, 0x9847ad4e from zlib)."""
    return ~zlib.crc32(data) & 0xFFFFFFFF


def _time(buf, off):
    base, _ctx, sec, usec = struct.unpack_from(">HBII", buf, off)
    return {"base": base, "t": sec + usec / 1e6}


def _flag(byte, name):
    """F Prime writes a bool as one byte: FW_SERIALIZE_TRUE_VALUE 0xFF, FW_SERIALIZE_FALSE_VALUE 0x00."""
    assert byte in (0x00, 0xFF), f"{name} is 0x{byte:02X}, neither 0xFF (true) nor 0x00 (false)"
    return byte == 0xFF


def decode_product(data, size_len=8):
    """Parse one `Capture` container; AssertionError (with the reason) when it is not one.

    Layout: header (descriptor U16, id U32, priority U32, time tag, processing U8, user data 32, state U8,
    data size FwSizeStoreType) + CRC-32, records, CRC-32. Records: Metrics (id U32 + CaptureMetrics),
    Picture (id U32 + size FwSizeStoreType + JPEG bytes)."""
    head = 2 + 4 + 4 + TIME_SIZE + 1 + 32 + 1 + size_len
    assert len(data) >= head + 8, f"{len(data)} bytes: shorter than a container header"
    descriptor, dp_id, priority = struct.unpack_from(">HII", data, 0)
    assert descriptor == 5, f"packet descriptor {descriptor}, expected 5 (data product)"
    tag = _time(data, 10)
    size = int.from_bytes(data[head - size_len:head], "big")
    assert struct.unpack_from(">I", data, head)[0] == crc(data[:head]), "header hash mismatch"
    assert len(data) == head + 4 + size + 4, f"file is {len(data)} bytes, header says {head + 8 + size}"
    body = data[head + 4:head + 4 + size]
    assert struct.unpack_from(">I", data, head + 4 + size)[0] == crc(body), "data hash mismatch"
    assert len(body) >= 4 + METRICS_SIZE + 4 + size_len, "data too short for a Metrics and a Picture record"
    off = 4
    m = {"captureTime": _time(body, off)}
    off += TIME_SIZE
    m["latitude"], m["longitude"] = struct.unpack_from(">dd", body, off)
    off += 16
    m["locationTime"] = _time(body, off)
    off += TIME_SIZE
    m["locationValid"] = _flag(body[off], "locationValid")
    off += 1
    m["roll"], m["pitch"] = struct.unpack_from(">ff", body, off)
    off += 8
    m["attitudeTime"] = _time(body, off)
    off += TIME_SIZE
    m["attitudeValid"] = _flag(body[off], "attitudeValid")
    off += 1
    m["temperature"] = struct.unpack_from(">f", body, off)[0]
    off += 4
    m["temperatureTime"] = _time(body, off)
    off += TIME_SIZE
    m["temperatureValid"] = _flag(body[off], "temperatureValid")
    off += 1
    ids = [struct.unpack_from(">I", body, 0)[0], struct.unpack_from(">I", body, off)[0]]
    n = int.from_bytes(body[off + 4:off + 4 + size_len], "big")
    jpeg = body[off + 4 + size_len:]
    assert n == len(jpeg), f"Picture record says {n} bytes, {len(jpeg)} remain (exactly one Metrics and one Picture record expected)"
    assert ids[0] != ids[1], "both records carry the same id"
    return {"id": dp_id, "priority": priority, "time": tag, "record_ids": ids, "metrics": m, "jpeg": jpeg}


def jpeg_size(jpeg):
    """(width, height) after a full decode with the bench JPEG decoder (Pillow)."""
    from PIL import ImageFile
    assert jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9", "picture is not SOI..EOI"
    parser = ImageFile.Parser()
    parser.feed(jpeg)
    image = parser.close()
    image.load()
    return image.size


def roll_pitch(acc):
    """Bench computation of roll and pitch (degrees) from an acceleration sample, as the SDD defines them."""
    ax, ay, az = acc["x"], acc["y"], acc["z"]
    return math.degrees(math.atan2(ay, az)), math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
