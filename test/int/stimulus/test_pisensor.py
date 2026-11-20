"""Stimulus and named checks of the PiSensor system test plan (plan.json beside this file), one function per test.

Each body sends exactly the commands of the plan procedure, paces itself on the record, and declares its
checks inside `with window(...)`; fth judges them over the record when the window closes and replays this
same file over the record at audit. Check names are constants: they are the identity of a verdict.
"""
import json
import math
import re
import time

import pytest

import pisensor_record as rec

R = lambda *n: [f"REQ-PiSensor-{i:03d}" for i in n]
DP_DIR = "dp"  # DataProductsConfig.Paths.dpDir
DEVICES = re.compile(r"^/dev/(spidev\d+\.\d+|i2c-\d+|ttyACM\d+|ttyAMA\d+|video\d+|media\d+|dma_heap/\S+|null|urandom)$")
BENCH_POSITION = (34.130442, -118.058840)  # surveyed bench position (latitude, longitude), degrees: docs/ledger.md 2026-11-19
DISPATCH = "commands sent, marker commands apart, == count of cmdDisp.OpCodeDispatched events of other opcodes (resends logged by the bench allowed for)"


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
    require(DISPATCH, every_command_dispatched)


def absent(check):
    """The plan's ABS block."""
    check("event piCamera.CaptureFailed count == 0")
    check("severity FATAL count == 0", lambda h: (not [e for e in h.window.ev if e.severity == "FATAL"], "FATAL events in the window"))
    check("each piCamera event that reports a sensor unavailable has no telemetry sample of that sensor in the 2 s before its capture", unavailable_silent)


def metrics(w, plan, test_id, check, require):
    """The plan's metrics of this window, by their plan text. fth 0.1.2 evaluates a plan metric only through
    its grammar, so the helper predicates the plan names are declared here instead (see README, fth gaps)."""
    names = [x["name"] for x in plan.test(test_id).windows]
    w.metrics.clear()
    for c in (c for c in plan.test(test_id).checks if c.kind == "metrics"):
        said = re.search(r" in ([A-Z])\b", c.text)  # fth files every metric under the first window; the text names its own
        if (said.group(1) if said and said.group(1) in names else c.window) != w.name:
            continue
        declare = require if "(require)" in c.text or "(require)" in c.rationale else check
        declare(c.text, lambda h, c=c: plan.registry.helpers[c.helper](h, **c.helper_args))


def every_command_dispatched(h):
    """Commands of the window against their dispatch events, marker commands left out on both sides: the
    dispatch event of the START marker carries the time of the marker event and can sort before it, outside
    the window; a lost marker tears the window. The uplink has no retransmission, so the bench sends a
    command again (at most twice) when no dispatch is reported; each resend is in cmd/resend.log, and with r
    resends in the window the count may be up to r higher."""
    w = h.window
    marker = w.cmds[0].opcode
    sent = len([c for c in w.cmds if c.opcode != marker])
    count = len([e for e in w.events("cmdDisp.OpCodeDispatched") if w.start_marker.idx < e.idx < w.end_marker.idx
                 and int(rec.OPCODE.search(e.text).group(1), 16) != marker])
    again = rec.resends(w, marker)
    return sent <= count <= sent + again, f"sent {sent}, dispatched {count}, resends logged {again}"


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
    """Every product whose CRC the UUT reported arrived, and the CRC of its ground file is that value (whole
    test). How many files arrived is a check of its own."""
    onboard = {}
    for w in h.windows.values():
        for e in w.events("fileManager.CalculateCrcSucceeded"):
            m = re.match(r"(\S+) has CRC value (0x[0-9a-fA-F]+)$", e.text)
            if m:
                onboard[m.group(1).rsplit("/", 1)[-1]] = int(m.group(2), 16)
    files = {k: v for w in h.windows.values() for k, v in rec.arrived(w).items()}
    same = [n for n in onboard if n in files and rec.crc(files[n]) == onboard[n]]
    return bool(onboard) and len(same) == len(onboard), \
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


def bmp_plausible(h):
    """BMP280 temperature of the window."""
    temps = [rec.value(r)["temperature"] for r in h.window.channel("bmpManager.Reading")]
    assert temps, "no bmpManager.Reading sample in the window"
    return all(-20 <= t <= 60 for t in temps), f"temperature {min(temps):.2f}..{max(temps):.2f} degC"


def gps_plausible(h):
    """GPS position of the window against the bench position in the manifest."""
    gps = [rec.value(r) for r in h.window.channel("gpsManager.Reading")]
    assert gps, "no gpsManager.Reading sample in the window"
    far = max(_distance_km(s["latitude"], s["longitude"], *BENCH_POSITION) for s in gps)
    return far <= 1.0, f"GPS within {far:.3f} km of the bench position"


def imu_plausible(h):
    """MPU6050 acceleration and rate of the window, bench at rest; the channel is in g and deg/s."""
    imu = [rec.value(r) for r in h.window.channel("imuManager.Reading")]
    assert imu, "no imuManager.Reading sample in the window"
    norm = lambda v: math.sqrt(v["x"] ** 2 + v["y"] ** 2 + v["z"] ** 2)
    acc, rate = [norm(s["acceleration"]) for s in imu], [norm(s["rotation"]) for s in imu]
    return all(0.82 <= a <= 1.22 for a in acc) and all(r <= 28.6 for r in rate), \
        f"acceleration {min(acc):.3f}..{max(acc):.3f} g, rate <= {max(rate):.2f} deg/s"


SILENT_S = 2.0  # REQ-PiSensor-014: a reading older than this is not stored
SAMPLE_MATCH_S = 0.1  # a metric marked valid has a telemetry sample this close to its sample time (sensors sample once a second)


def metrics_valid_or_silent(h):
    """REQ-PiSensor-005, for every ground file of the window and each metric group (temperature; latitude and
    longitude; roll and pitch). Marked valid: the values are finite and the record holds a telemetry sample of
    that sensor within 0.1 s of the stated sample time. Marked not valid: the values are NaN, the
    sample time is zero, and the record holds no telemetry sample of that sensor with a unit time in the 2 s up
    to the capture time record. In the window, the events piCamera sends for a group stored as placeholders are
    as many as the ground files with that group not valid."""
    files = rec.arrived(h.window)
    assert files, "no file arrived"
    bad, lacking = [], {g[0]: 0 for g in rec.GROUPS}
    for n, d in sorted(files.items()):
        m = rec.decode_product(d)["metrics"]
        for group, flag, keys, tkey, channel, _ in rec.GROUPS:
            values = [m[k] for k in keys]
            if m[flag]:
                if not all(math.isfinite(v) for v in values):
                    bad.append(f"{n}: {group} marked valid, values {values}")
                if not rec.sampled(channel, m[tkey]["t"], SAMPLE_MATCH_S, SAMPLE_MATCH_S):
                    bad.append(f"{n}: {group} marked valid, no {channel} sample within {SAMPLE_MATCH_S:g} s of its sample time {m[tkey]['t']:.3f}")
                continue
            lacking[group] += 1
            if not all(math.isnan(v) for v in values):
                bad.append(f"{n}: {group} marked not valid, values {values} are not NaN")
            if m[tkey]["t"] != 0:
                bad.append(f"{n}: {group} marked not valid, sample time {m[tkey]['t']:.3f} is not zero")
            fresh = rec.sampled(channel, m["captureTime"]["t"], SILENT_S)
            if fresh:
                bad.append(f"{n}: {group} marked not valid, {len(fresh)} {channel} sample(s) in the {SILENT_S:g} s before the capture")
    for group, _, _, _, _, event in rec.GROUPS:
        seen = len([e for e in h.window.ev if e.short == event])
        if seen != lacking[group]:
            bad.append(f"{event}: {seen} event(s), {lacking[group]} product(s) with {group} not valid")
    return not bad, f"{len(files)} product(s), not valid: {lacking}; wrong: {bad or 'none'}"


def unavailable_silent(h):
    """Each piCamera event that reports a sensor unavailable: no telemetry sample of that sensor in the record
    with a unit time in the 2 s up to the capture time, which is the time in the name of the product written
    next in the window (the event itself follows the capture); the event time where no product follows."""
    bad, n = [], 0
    written = [(e.fsw, rec.name_time(e.text)) for e in h.window.ev if e.short == "dpWriter.FileWritten"]
    for _, _, _, _, channel, event in rec.GROUPS:
        for e in (e for e in h.window.ev if e.short == event):
            n += 1
            at = next((t for fsw, t in written if fsw >= e.fsw and t is not None and t <= e.fsw), e.fsw)
            fresh = rec.sampled(channel, at, SILENT_S)
            if fresh:
                bad.append(f"{event} at {e.fsw:.3f} (capture {at:.3f}): {len(fresh)} {channel} sample(s) in the {SILENT_S:g} s before the capture")
    return not bad, f"{n} event(s); sensor answering at: {bad or 'none'}"


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


def metrics_match_telemetry(h, which):
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
    flag = {c: f for _, f, _, _, c, _ in rec.GROUPS}
    skipped = []
    for name, tkey, channel, get, widen, exact in (i for i in items if (i[2] == "imuManager.Reading") == (which == "attitude")):
        if not m[flag[channel]]:  # a placeholder: judged by the validity check of this window
            skipped.append(name)
            continue
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
    return not bad, f"metrics not matching the telemetry: {bad or 'none'}; marked not valid, not compared: {skipped or 'none'}"


def settle(bench, limit_s=60):
    """Last step of every window: wait until the telemetry sampled up to now has reached the ground. The
    radio downlink carries telemetry later than events, and later the longer the unit runs; fth judges a
    window right after its END marker over the samples whose unit time lies in it."""
    if not rec.live():
        return
    now = time.time()
    for _ in range(limit_s):
        if rec.caught_up("bmpManager.Reading", now):
            return
        bench.wait(1)


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


# Limit for one product on the link: 128 file bytes a second, pictures seen up to 90 kB (about 710 s), a
# 127 kB product measured at 938 s; lost PDUs are sent again at one a second. A test waits this long for each
# product it stores, and one more where a planted capture can add one.
PRODUCT_DOWNLINK_S = 1200


def downlinked(bench, products=1):
    bench.wait_event("dpCat.CatalogXmitCompleted", PRODUCT_DOWNLINK_S * products)
    bench.action("wait_cfdp")


# ---------------------------------------------------------------- the tests, in plan order
@pytest.mark.req(*R(13, 10))
def test_L0_1(window, send, bench, check, require, fth_plan):
    with window(10, 11) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L0-1", check, require)
        bench.action("clock")
        send("version.VERSION", ["ALL"])
        bench.action("platform")
        bench.wait_samples("bmpManager.Reading", 2)
        bench.action("sockets")
        absent(check)
        check("Version events equal the manifest describe strings", versions)
        check("platform is a Raspberry Pi 5 under 64-bit Raspberry Pi OS 13 (trixie)", platform)
        check("the process holds no TCP or UDP socket", lambda h: (not _sockets(h)[0], f"sockets: {_sockets(h)[0]}"))
        check("character devices held by the process are a subset of the list in Scope",
              lambda h: (all(DEVICES.match(d) for d in _sockets(h)[1]), f"devices: {_sockets(h)[1]}"))
        check("LibraryVersions names fprime-sensors only",
              lambda h: ([e.text.split("[")[1].split("@")[0] for e in h.window.events("version.LibraryVersions")] == ["fprime-sensors"],
                         "; ".join(e.text for e in h.window.events("version.LibraryVersions"))))
        check("the dictionary of the image holds no command of a test component", no_test_command)
        settle(bench)


def no_test_command(h):
    names = [c["name"] for c in json.loads((rec.raw_dir() / "dictionary.json").read_text(encoding="utf-8"))["commands"]]
    extra = [n for n in names if re.search(r"(?i)test|harness", n.rsplit(".", 1)[0])]
    return bool(names) and not extra, f"{len(names)} commands, of test components: {extra}"


@pytest.mark.req(*R(13))
def test_L0_2(window, send, bench, check, require, fth_plan):
    with window(20, 21):
        std(require, fth_plan)
        bench.wait_samples("bmpManager.Reading", 2)
        send("cmdDisp.CMD_NO_OP_STRING", [42405])
        bench.action("platform")
        absent(check)
        check("three NoOpStringReceived events in order, strings byte-exact",
              lambda h: ([e.raw_args.get("arg1") for e in h.window.events("cmdDisp.NoOpStringReceived")] == ["20", "42405", "21"],
                         str([e.text for e in h.window.events("cmdDisp.NoOpStringReceived")])))
        check("platform is a Raspberry Pi 5 under 64-bit Raspberry Pi OS 13 (trixie)", platform)
        settle(bench)


@pytest.mark.req(*R(1, 2, 3, 11))
def test_L2_1(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(30, 31) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-1", check, require)
        bench.wait(60)
        absent(check)
        check("BMP280 readings plausible for a bench at rest", bmp_plausible)
        check("GPS readings plausible for a bench at rest", gps_plausible)
        check("MPU6050 readings plausible for a bench at rest", imu_plausible)
        settle(bench)


@pytest.mark.req(*R(1, 2, 3, 11))
def test_L2_2(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(32, 33) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-2", check, require)
        for _ in range(3):
            send("cmdDisp.CMD_NO_OP", [])
            bench.wait(10)
        absent(check)
        check("BMP280 readings plausible for a bench at rest", bmp_plausible)
        check("GPS readings plausible for a bench at rest", gps_plausible)
        check("MPU6050 readings plausible for a bench at rest", imu_plausible)
        check("event cmdDisp.NoOpReceived count == 3")
        settle(bench)


@pytest.mark.req(*R(4, 5, 6, 7, 8, 9, 11, 14))
def test_L2_3(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(40, 41) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-3", check, require)
        absent(check)
        check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1", completed(1))
        check("event dpWriter.FileWritten count == 1")
        check("exactly one file arrived", files_arrived(1))
        check("CRC of each ground file == value in the fileManager.CalculateCrcSucceeded event of its product", crc_matches)
        check("every CFDP transaction in the window is class 2 and finished complete at the ground", class2_complete)
        check("each ground file is a product container with one Metrics and one Picture record; the JPEG decodes, >= 640x480", product_content)
        check("each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent", metrics_valid_or_silent)
        p = capture(send, bench, 40, 1)
        send("fileManager.CalculateCrc", [p])
        downlink(send, bench)
        downlinked(bench, 2)
        settle(bench)


@pytest.mark.req(*R(4, 5, 6, 7, 8, 9, 14))
def test_L2_4(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(42, 43) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-4", check, require)
        absent(check)
        check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2", completed(2))
        check("event dpWriter.FileWritten count == 2 with different names", two_names)
        check("capture time of P2 later than that of P1; picture records of P1 and P2 differ", two_differ)
        check("exactly two files arrived", files_arrived(2))
        check("CRC of each ground file == value in the fileManager.CalculateCrcSucceeded event of its product", crc_matches)
        check("every CFDP transaction in the window is class 2 and finished complete at the ground", class2_complete)
        check("each ground file is a product container with one Metrics and one Picture record; the JPEG decodes, >= 640x480", product_content)
        check("each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent", metrics_valid_or_silent)
        p1 = capture(send, bench, 42, 1)
        bench.wait(5)
        p2 = capture(send, bench, 42, 2)
        send("fileManager.CalculateCrc", [p1])
        send("fileManager.CalculateCrc", [p2])
        downlink(send, bench)
        downlinked(bench, 3)
        settle(bench)


def two_names(h):
    names = [e.text.rsplit(" ", 1)[-1] for w in h.windows.values() for e in w.events("dpWriter.FileWritten")]
    return len(names) == 2 and len(set(names)) == 2, f"FileWritten: {names}"


def two_differ(h):
    """P1 and P2 are the first two products the window wrote, by their FileWritten events."""
    names = [e.text.rsplit("/", 1)[-1] for e in h.window.events("dpWriter.FileWritten")][:2]
    files = rec.arrived(h.window)
    assert len(names) == 2 and all(n in files for n in names), f"written {names}, arrived {sorted(files)}"
    p1, p2 = (rec.decode_product(files[n]) for n in names)
    t1, t2 = p1["metrics"]["captureTime"]["t"], p2["metrics"]["captureTime"]["t"]
    return t1 < t2 and p1["jpeg"] != p2["jpeg"], f"capture times {t1:.3f}, {t2:.3f}"


@pytest.mark.req(*R(5, 6, 14, 8))
def test_L2_5(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(44, 45) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-5", check, require)
        absent(check)
        check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1", completed(1))
        check("every CFDP transaction in the window is class 2 and finished complete at the ground", class2_complete)
        check("exactly one file arrived", files_arrived(1))
        check("each ground file is a product container with one Metrics and one Picture record; the JPEG decodes, >= 640x480", product_content)
        check("each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent", metrics_valid_or_silent)
        check("temperature, latitude and longitude of the product equal, or lie between, the telemetry samples around their sample times",
              lambda h: metrics_match_telemetry(h, "other"))
        check("roll and pitch of the product equal, or lie between, the telemetry samples around their sample time",
              lambda h: metrics_match_telemetry(h, "attitude"))
        bench.wait(10)
        capture(send, bench, 44, 1)
        bench.wait(10)
        downlink(send, bench)
        downlinked(bench, 1)
        settle(bench)


@pytest.mark.req(*R(4, 7))
def test_L2_6(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(46, 47) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-6", check, require)
        absent(check)
        check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 3", completed(3))
        check("event dpWriter.FileWritten count == 3")
        for k in (1, 2, 3):
            capture(send, bench, 46, k)
        settle(bench)


@pytest.mark.req(*R(12, 8, 9, 10, 11))
def test_L2_7(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(50, 51) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-7", check, require)
        absent(check)
        check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2", completed(2))
        p1 = capture(send, bench, 50, 1)
        p2 = capture(send, bench, 50, 2)
        send("fileManager.CalculateCrc", [p1])
        send("fileManager.CalculateCrc", [p2])
        settle(bench)
    with window(51, 52) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-7", check, require)
        absent(check)
        check("event dpWriter.FileWritten count == 2 over the whole test (Q and D)", two_names)
        check("exactly two files arrived", files_arrived(2))
        check("rfm69Manager.PacketsTransmitted and PacketsReceived rise in D; TM frames received <= PacketsTransmitted rise + 2", radio_only)
        check("CRC of each ground file == value in the fileManager.CalculateCrcSucceeded event of its product", crc_matches)
        check("every CFDP transaction in the window is class 2 and finished complete at the ground", class2_complete)
        downlink(send, bench)
        downlinked(bench, 3)
        settle(bench)


@pytest.mark.req(*R(12, 10))
def test_L2_8(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(53, 54) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-8", check, require)
        absent(check)
        check("event dpWriter.FileWritten count == 2")
        capture(send, bench, 53, 1)
        capture(send, bench, 53, 2)
        settle(bench)
    with window(54, 55) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-8", check, require)
        absent(check)
        check("event cmdDisp.NoOpReceived count == 1 between dpCat.CatalogXmitStarted and dpCat.CatalogXmitCompleted", noop_during_downlink)
        check("exactly two files arrived", files_arrived(2))
        check("rfm69Manager.PacketsTransmitted and PacketsReceived rise in D; TM frames received <= PacketsTransmitted rise + 2", radio_only)
        check("every CFDP transaction in the window is class 2 and finished complete at the ground", class2_complete)
        downlink(send, bench, wait_s=0)
        bench.wait(15)
        send("cmdDisp.CMD_NO_OP", [])
        downlinked(bench, 2)
        settle(bench)


def noop_during_downlink(h):
    ev = h.window.ev
    a = [i for i, e in enumerate(ev) if e.short == "dpCat.CatalogXmitStarted"]
    b = [i for i, e in enumerate(ev) if e.short == "dpCat.CatalogXmitCompleted"]
    assert a and b, f"CatalogXmitStarted {len(a)}, CatalogXmitCompleted {len(b)}"
    n = len([e for e in ev[a[0]:b[0]] if e.short == "cmdDisp.NoOpReceived"])
    return n == 1, f"{n} NoOpReceived between them"


@pytest.mark.req(*R(12))
def test_L2_9(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    with window(56, 57) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-9", check, require)
        absent(check)
        check("event dpWriter.FileWritten count == 1")
        capture(send, bench, 56, 1)
        settle(bench)
    with window(57, 58) as w:
        std(require, fth_plan)
        metrics(w, fth_plan, "L2-9", check, require)
        absent(check)
        check("exactly one file arrived", files_arrived(1))
        downlink(send, bench)
        downlinked(bench, 1)
        settle(bench)


@pytest.mark.req(*R(9, 5, 8))
def test_L7_1(window, send, bench, check, require, fth_plan):
    bench.action("clean_products")
    try:
        with window(60, 61):
            std(require, fth_plan)
            absent(check)
            check("event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1", completed(1))
            check("CRC of each ground file == value in the fileManager.CalculateCrcSucceeded event of its product", crc_matches)
            check("each ground file is a product container with one Metrics and one Picture record; the JPEG decodes, >= 640x480", product_content)
            check("each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose sensor was silent", metrics_valid_or_silent)
            check("the directory listing names P only", listing_names_product)
            check("no CFDP transaction starts after the second START_XMIT_CATALOG", no_second_downlink)
            send("cfdpManager.FileInDefaultKeep_PRM_SET", ["KEEP"])
            p = capture(send, bench, 60, 1)
            send("fileManager.CalculateCrc", [p])
            downlink(send, bench)
            downlinked(bench, 1)
            send("fileManager.ListDirectory", [DP_DIR])
            downlink(send, bench, wait_s=0)
            bench.wait(30)
            settle(bench)
    finally:
        bench.action("final_state")


def listing_names_product(h):
    listed = [m.group(1) for e in h.window.events("fileManager.DirectoryListing")
              for m in [re.match(r"Directory \S+: (\S+) \(\d+ bytes\)$", e.text)] if m]
    written = [e.text.rsplit("/", 1)[-1] for e in h.window.events("dpWriter.FileWritten")]
    return len(written) == 1 and listed == written, f"listed {listed}, written {written}"


def no_second_downlink(h):
    ops = {c.opcode for c in h.window.cmds if c.short == "dpCat.START_XMIT_CATALOG"}
    disp = [e for e in h.window.events("cmdDisp.OpCodeDispatched") if int(rec.OPCODE.search(e.text).group(1), 16) in ops]
    assert len(disp) == 2, f"{len(disp)} START_XMIT_CATALOG dispatched"
    late = [t["id"] for t in rec.transfers(h.window) if rec.epoch(t["startTime"]) > rec.rx(disp[1])]
    return not late, f"transactions started after the second START_XMIT_CATALOG: {late}"
