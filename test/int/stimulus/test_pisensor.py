"""Stimulus and named checks of the PiSensor system test plan (test/int/plan.json), one function per test.

Each body sends exactly the commands of the plan procedure, paces itself on the record, and declares its
checks inside `with window(...)`; fth judges them over the record when the window closes and replays this
same file over the record at audit. Check names are constants: they are the identity of a verdict.
"""
import json
import math
import re

import pytest

import pisensor_record as rec

R = lambda *n: [f"REQ-PiSensor-{i:03d}" for i in n]
DP_DIR = "./DpCat"  # DataProductsConfig.Paths.dpDir
DEVICES = re.compile(r"^/dev/(spidev\d+\.\d+|i2c-\d+|ttyACM\d+|ttyAMA\d+|video\d+|media\d+|dma_heap/\S+|null|urandom)$")
G, DEG = 9.80665, math.pi / 180  # imuManager.Reading is in g and deg/s; the plan bounds are m/s^2 and rad/s
BENCH_POSITION = None  # (latitude, longitude) of the surveyed bench position, degrees: set at bench entry


# ---------------------------------------------------------------- declarations shared by the tests
def std(require, plan):
    """The plan's STD block, every item by its plan text; the two items outside fth's grammar get a function."""
    for text in plan.raw["std_complete"]:
        if "OpCodeError" in text:
            require(text, no_error_but_capture)
        elif "frame count" in text:
            require(text, lambda h: rec.frame_gaps(rec.frames(h.window)))
        else:
            require(text)


def absent(check):
    """The plan's ABS block."""
    check("event piCamera.CaptureFailed count == 0")
    check("severity FATAL count == 0", lambda h: (not [e for e in h.window.ev if e.severity == "FATAL"], "FATAL events in the window"))


def metrics(w, plan, test_id, check, require):
    """The plan's metrics of this window, by their plan text. fth 0.1.2 evaluates a plan metric only through
    its grammar, so the helper predicates the plan names are declared here instead (see README, fth gaps)."""
    specs = [c for c in plan.test(test_id).checks if c.kind == "metrics" and c.window == w.name]
    w.metrics.clear()
    for c in specs:
        declare = require if "(require)" in c.text or "(require)" in c.rationale else check
        declare(c.text, lambda h, c=c: plan.registry.helpers[c.helper](h, **c.helper_args))


def no_error_but_capture(h):
    ops = {c.opcode for c in h.window.cmds if c.short == "piCamera.CAPTURE"}
    bad = [e for e in h.window.events("cmdDisp.OpCodeError") if int(rec.OPCODE.search(e.text).group(1), 16) not in ops]
    return not bad, f"{len(bad)} OpCodeError of other commands"


def completed(n):
    """event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == n"""
    def fn(h):
        ops = {c.opcode for c in h.window.cmds if c.short == "piCamera.CAPTURE"}
        got = [e for e in h.window.events("cmdDisp.OpCodeCompleted") if int(rec.OPCODE.search(e.text).group(1), 16) in ops]
        return len(got) == n, f"{len(got)} completed"
    return fn


def files_arrived(n, *names):
    return lambda h: (len(rec.arrived(h.windows[names[-1] if names else h.window.label])) == n,
                      f"{len(rec.arrived(h.windows[names[-1] if names else h.window.label]))} file(s) arrived")


def crc_matches(h):
    """CRC of each ground file == the value in the CalculateCrcSucceeded event of that product (whole test)."""
    onboard = {}
    for w in h.windows.values():
        for e in w.events("fileManager.CalculateCrcSucceeded"):
            m = re.match(r"(\S+) has CRC value (0x[0-9a-fA-F]+)$", e.text)
            if m:
                onboard[m.group(1).rsplit("/", 1)[-1]] = int(m.group(2), 16)
    files = {k: v for w in h.windows.values() for k, v in rec.arrived(w).items()}
    same = [n for n in onboard if n in files and rec.crc(files[n]) == onboard[n]]
    return bool(onboard) and len(same) == len(onboard) and set(files) <= set(onboard), \
        f"{len(onboard)} on-board CRC, {len(files)} ground file(s), {len(same)} equal"


def class2_complete(h):
    ts = rec.transfers(h.window)
    bad = [t["id"] for t in ts if not t.get("reliable") or t.get("state") != "COMPLETED"]
    return bool(ts) and not bad, f"{len(ts)} transaction(s), not class 2 or not complete: {bad}"


def product_content(h):
    """Each ground file parses as a container with one Metrics and one Picture record; the JPEG decodes >= 640x480."""
    files = rec.arrived(h.window)
    assert files, "no file arrived"
    sizes = []
    for name, data in sorted(files.items()):
        size = rec.jpeg_size(rec.decode_product(data)["jpeg"])
        assert size[0] >= 640 and size[1] >= 480, f"{name}: picture {size[0]}x{size[1]}"
        sizes.append(f"{size[0]}x{size[1]}")
    return True, f"{len(files)} product(s), pictures {', '.join(sizes)}"


def platform(h):
    """Platform identity read over ssh (REQ-PiSensor-013)."""
    got = [a for a in rec.actions(h.window, "platform") if a["rc"] == 0]
    assert got, "no platform action in the window"
    out = got[-1]["stdout"]
    head, _, rest = out.partition("--- os-release")
    os_release, _, rest = rest.partition("--- rpi-issue")
    issue, _, bits = rest.partition("--- long-bit")
    kv = dict(l.split("=", 1) for l in os_release.splitlines() if "=" in l)
    facts = {"model": head.strip().startswith("MODEL=Raspberry Pi 5"), "VERSION_ID": kv.get("VERSION_ID", "").strip('"') == "13",
             "VERSION_CODENAME": kv.get("VERSION_CODENAME", "").strip('"') == "trixie",
             "rpi-issue": "Raspberry Pi" in issue, "LONG_BIT": bits.strip() == "64"}
    return all(facts.values()), ", ".join(f"{k} {'ok' if v else 'WRONG'}" for k, v in facts.items())


def _sockets(h):
    got = [a for a in rec.actions(h.window, "sockets") if a["rc"] == 0]
    assert got, "no sockets action in the window"
    _, _, rest = got[-1]["stdout"].partition("--- sockets")
    socks, _, devs = rest.partition("--- devices")
    return [l for l in socks.splitlines() if l.strip()], [l.strip() for l in devs.splitlines() if l.strip()]


def versions(h):
    """Version events equal the manifest describe strings (manifest named on the fth command line)."""
    path = rec._arg("--fth-manifest")
    if not path:
        return None, "no manifest on the command line", [], True
    want = {r["name"]: r["describe"] for r in json.loads(rec.Path(path).read_text(encoding="utf-8"))["repos"]}
    text = " ".join(e.text for e in h.window.ev if e.short.startswith("version."))
    missing = [n for n, d in want.items() if n != "harness" and f"[{d}]" not in text and f"@{d}]" not in text]
    return not missing, f"describe strings absent from the version events: {missing or 'none'}"


def sensors_plausible(h):
    w, seen = h.window, []
    temps = [rec.value(r)["temperature"] for r in w.channel("bmpManager.Reading")]
    imu = [rec.value(r) for r in w.channel("imuManager.Reading")]
    gps = [rec.value(r) for r in w.channel("gpsManager.Reading")]
    assert temps and imu and gps, f"samples: bmp {len(temps)}, imu {len(imu)}, gps {len(gps)}"
    norm = lambda v: math.sqrt(v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2)
    ok = all(-20 <= t <= 60 for t in temps)
    seen.append(f"temperature {min(temps):.2f}..{max(temps):.2f} degC")
    acc, rate = [norm(s["acceleration"]) * G for s in imu], [norm(s["rotation"]) * DEG for s in imu]
    ok = ok and all(8 <= a <= 12 for a in acc) and all(r <= 0.5 for r in rate)
    seen.append(f"acceleration {min(acc):.2f}..{max(acc):.2f} m/s^2, rate <= {max(rate):.3f} rad/s")
    assert BENCH_POSITION is not None, "; ".join(seen) + "; bench position not set"
    far = max(_distance_km(s["latitude"], s["longitude"], *BENCH_POSITION) for s in gps)
    return ok and far <= 1.0, "; ".join(seen) + f"; GPS within {far:.3f} km"


def _distance_km(lat1, lon1, lat2, lon2):
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def radio_only(h):
    """PacketsTransmitted and PacketsReceived rise in D; TM frames received between the first and last
    PacketsTransmitted sample <= (last - first) + 2."""
    w = h.window
    tx, rxs = w.channel("rfm69Manager.PacketsTransmitted"), w.channel("rfm69Manager.PacketsReceived")
    assert len(tx) >= 2 and len(rxs) >= 2, f"samples: PacketsTransmitted {len(tx)}, PacketsReceived {len(rxs)}"
    t0, t1 = rec.rx(tx[0]), rec.rx(tx[-1])
    n = len([f for f in rec.frames(w) if t0 < f["rx"] <= t1])
    rise = tx[-1].value - tx[0].value
    return rise > 0 and rxs[-1].value > rxs[0].value and n <= rise + 2, \
        f"PacketsTransmitted +{rise}, PacketsReceived +{rxs[-1].value - rxs[0].value}, {n} TM frames"


def metrics_match_telemetry(h):
    """Each metric of the product against the telemetry samples of its channel around its sample time."""
    files = rec.arrived(h.window)
    assert len(files) == 1, f"{len(files)} file(s) arrived"
    m = rec.decode_product(next(iter(files.values())))["metrics"]
    rp = lambda s: rec.roll_pitch(s["acceleration"])
    items = (("temperature", "temperatureTime", "bmpManager.Reading", lambda s: s["temperature"], 0.5, 0.0),
             ("roll", "attitudeTime", "imuManager.Reading", lambda s: rp(s)[0], 2.0, 0.1),
             ("pitch", "attitudeTime", "imuManager.Reading", lambda s: rp(s)[1], 2.0, 0.1),
             ("latitude", "locationTime", "gpsManager.Reading", lambda s: s["latitude"], 0.0001, 0.0),
             ("longitude", "locationTime", "gpsManager.Reading", lambda s: s["longitude"], 0.0001, 0.0))
    bad = []
    for name, tkey, channel, get, widen, exact in items:
        rows, t = h.window.channel(channel), m[tkey]["t"]
        same = [r for r in rows if abs(r.fsw - t) < 0.001]  # the record keeps FSW time to the millisecond
        before, after = [r for r in rows if r.fsw <= t], [r for r in rows if r.fsw >= t]
        if same:
            good = any(abs(get(rec.value(r)) - m[name]) <= exact + 1e-6 * max(1.0, abs(m[name])) for r in same)
        elif before and after:
            lo, hi = sorted((get(rec.value(before[-1])), get(rec.value(after[0]))))
            good = lo - widen <= m[name] <= hi + widen
        else:
            good = False
        if not good:
            bad.append(name)
    return not bad, f"metrics not matching the telemetry: {bad or 'none'}"


def capture(send, bench, start_id, k):
    """piCamera.CAPTURE(), wait for its dpWriter.FileWritten; returns the name of the k-th product of the window."""
    send("piCamera.CAPTURE", [])
    bench.wait_event("dpWriter.FileWritten", 60)
    return rec.products(start_id, k)[k - 1]


def downlink(send, bench, wait_s=30):
    if wait_s:
        bench.wait(wait_s)
    send("dpCat.BUILD_CATALOG", [])
    send("dpCat.START_XMIT_CATALOG", ["NO_WAIT", "false"])


def downlinked(bench):
    bench.wait_event("dpCat.CatalogXmitCompleted", 900)
    bench.action("wait_cfdp")
