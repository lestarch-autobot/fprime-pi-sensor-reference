"""Stimulus and named checks of the PiCamera component bench plan (plan.json)."""
import re

import pytest

CAPTURE = "piCamera.CAPTURE"
PICTURE_MAX_SIZE = 262144
CAPTURE_MAX_S = 15.0
DISPATCH_S = 0.05
HEARTBEAT = "bmpManager.Reading"
FRESH_S = 1.5
# Warning event and telemetry channel of each reading a capture stores
SENSORS = {
    "temperature": ("piCamera.TemperatureUnavailable", "bmpManager.Reading"),
    "attitude": ("piCamera.AttitudeUnavailable", "imuManager.Reading"),
    "location": ("piCamera.LocationUnavailable", "gpsManager.Reading"),
}
RESPONSES = ("cmdDisp.OpCodeCompleted", "cmdDisp.OpCodeError")


def opcode(value):
    """Opcode of an event argument (number or hexadecimal text) as a number."""
    return value if isinstance(value, int) else int(str(value), 16)


def commands_dispatched(h):
    """Every command of the window was dispatched by the unit: no command frame was lost on the uplink.

    Marker commands are left out on both sides: the dispatch of the START marker carries the time tag
    of the marker event and may sort before it, outside the window. A lost marker tears the window,
    which is judged by the marker precondition.
    """
    commands = h.window.cmds
    if len(commands) < 2:
        return False, "no command log for the window"
    marker = commands[0].opcode
    sent = len([c for c in commands if c.opcode != marker])
    dispatched = len([e for e in h.window.events("cmdDisp.OpCodeDispatched") if opcode(e.args["opCode"]) != marker])
    return dispatched == sent, f"commands sent, markers apart: {sent}; dispatched: {dispatched}"


ROW_TIME = re.compile(r"TB_PROC_TIME: (\d+\.\d+)s")
CATCH_UP_S = 240


def row_times(lines, name=None):
    """Unit times of recorder rows, of one name when given."""
    found = (ROW_TIME.match(line) for line in lines if name is None or f".{name}," in line)
    return [float(m.group(1)) for m in found if m]


def wait_for_channels(bench):
    """Wait until the recorded channel samples reach the time of the newest recorded event.

    Channel samples reach the ground record tens of seconds after events of the same unit time
    (measured on this bench). A window closed before they arrive has no bracket samples.
    """
    def lines(log):
        return [line for f in bench._recorder_logs(log) for line in f.read_text(errors="replace").splitlines()]

    events = row_times(lines("event.log"))
    newest = max(events) if events else 0.0
    bench._wait(f"{HEARTBEAT} samples up to the newest event",
                lambda: any(t >= newest for t in row_times(lines("channel.log"), HEARTBEAT)), CATCH_UP_S)


def complete(bench, require):
    """Preconditions of a window; called after the stimulus, once the channel samples have arrived."""
    wait_for_channels(bench)
    require("STD")
    require("every command sent in the window was dispatched", commands_dispatched)


def bracket(bench):
    bench.wait_samples(HEARTBEAT, 2, 30)


def picture_sizes_ok(sizes):
    """True when there is at least one picture and each is within the limit."""
    return len(sizes) > 0 and all(0 < s <= PICTURE_MAX_SIZE for s in sizes)


def picture_within_limit(h):
    sizes = [int(e.args["bytes"]) for e in h.window.events("piCamera.CaptureCompleted")]
    return picture_sizes_ok(sizes), f"picture sizes {sizes}"


def response_times(dispatched, responses):
    """Seconds from each dispatch of an opcode to the next response of that opcode; None where there is none."""
    times = []
    for start in dispatched:
        later = [r for r in responses if r >= start]
        times.append(min(later) - start if later else None)
    return times


def responses_within_bound(h):
    """Every CAPTURE of the window is answered within CAPTURE_MAX_MS of its dispatch (unit clock)."""
    dispatched = [e for e in h.window.events("cmdDisp.OpCodeDispatched")]
    captures = [e for e in h.window.events("piCamera.CaptureStarted")]
    if not captures:
        return False, "no capture in the window"
    # The opcode of CAPTURE is the one dispatched with the first CaptureStarted (time tags within DISPATCH_S)
    codes = {opcode(e.args["opCode"]) for e in dispatched if abs(e.t - captures[0].t) <= DISPATCH_S}
    if len(codes) != 1:
        return False, f"dispatch of CAPTURE not identified: {sorted(codes)}"
    code = codes.pop()
    starts = [e.t for e in dispatched if opcode(e.args["opCode"]) == code]
    ends = [e.t for name in RESPONSES for e in h.window.events(name) if opcode(e.args["opCode"]) == code]
    times = response_times(starts, ends)
    ok = len(times) > 0 and all(t is not None and t <= CAPTURE_MAX_S for t in times)
    return ok, f"response times {times} s for opcode {code:#x}"


def warning_expected(started, completed, sample_times):
    """Whether a capture from ``started`` to ``completed`` must warn that a reading is unavailable.

    True: the window holds no sample of the sensor at all. False: a sample in the FRESH_S before the
    start and one in the FRESH_S before the end, so the reading was fresh whenever the unit judged
    it. None: anything else is not judged, because channel samples are lost on the downlink and a
    gap in the record does not show that the unit had no reading.
    """
    if not sample_times:
        return True
    fresh = all(any(0.0 <= moment - t <= FRESH_S for t in sample_times) for moment in (started, completed))
    return False if fresh else None


def warnings_agree(sensor):
    """Check: each completed capture warned of an unavailable reading as the recorded telemetry of the sensor requires."""
    event, channel = SENSORS[sensor]

    def judge(h):
        done = h.window.events("piCamera.CaptureCompleted")
        warned = [e.t for e in h.window.events(event)]
        started = [e.t for e in h.window.events("piCamera.CaptureStarted")]
        samples = [c.t for c in h.window.ch if c.short == channel]
        if not done:
            return False, "no completed capture in the window"
        seen = []
        for capture in done:
            begin = max([t for t in started if t <= capture.t], default=capture.t)
            warning = any(begin <= t <= capture.t for t in warned)
            seen.append((warning, warning_expected(begin, capture.t, samples)))
        ok = all(expected is None or warning == expected for warning, expected in seen)
        return ok, f"(warned, warning expected from {channel}) per capture: {seen}; {len(samples)} samples"

    return judge


def check_readings(check):
    """A reading is stored as valid (no warning) when its sensor answers and as a placeholder (warning) when it is silent."""
    for sensor in SENSORS:
        check(f"{sensor} warning agrees with the sensor telemetry", warnings_agree(sensor))


def first_failure_is_camera_open(h):
    failed = h.window.events("piCamera.CaptureFailed")
    if not failed:
        return False, "no CaptureFailed in the window"
    first = failed[0].args
    return first.get("reason") == "CAMERA_ERROR" and first.get("step") == "OPEN", f"first failure {dict(first)}"


def no_start_between_failure_and_success(h):
    failed = h.window.events("piCamera.CaptureFailed")
    done = h.window.events("piCamera.CaptureCompleted")
    if not failed or not done:
        return False, "failure or success missing"
    starts = [e.t for e in h.window.events("version.ProjectVersion") if failed[0].t <= e.t <= done[-1].t]
    return not starts, f"start-up events between failure and success: {len(starts)}"


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-020", "REQ-PiCamera-026")
def test_C_1(window, send, bench, check, require):
    with window(10, 11):
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        complete(bench, require)
        check("ABS")
        check("event piCamera.CaptureStarted count == 1")
        check("event piCamera.CaptureStarted precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")
        check("picture size within PICTURE_MAX_SIZE", picture_within_limit)
        check_readings(check)
        check("every CAPTURE answered within CAPTURE_MAX_MS", responses_within_bound)


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-016", "REQ-PiCamera-019", "REQ-PiCamera-026")
def test_C_2(window, send, bench, check, require):
    with window(20, 21):
        bracket(bench)
        bench.action("camera_hold")
        try:
            send(CAPTURE, [], wait_completion=False)
            bench.wait_event("cmdDisp.OpCodeError", 30)
            # The camera stays held until any CAPTURE in flight has ended
            bracket(bench)
        finally:
            bench.action("camera_release")
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        complete(bench, require)
        check("first CaptureFailed is CAMERA_ERROR at OPEN", first_failure_is_camera_open)
        check("event piCamera.CaptureFailed count == 1")
        check("event cmdDisp.OpCodeError count == 1")
        check("event piCamera.CaptureFailed precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")
        check("no start-up between the failure and the success", no_start_between_failure_and_success)
        check_readings(check)
        check("every CAPTURE answered within CAPTURE_MAX_MS", responses_within_bound)


@pytest.mark.req("REQ-PiCamera-024", "REQ-PiCamera-026")
def test_C_3(window, send, bench, check, require):
    with window(30, 31):
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bench.action("fsw_restart")
        bench.wait(20)
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bench.wait_samples("piCamera.CapturesCompleted", 2, 30)
        bracket(bench)
        complete(bench, require)
        check("ABS")
        check("event piCamera.CaptureCompleted count == 2")
        check("event dpWriter.FileWritten count == 2")
        check("last(piCamera.CapturesCompleted) == 1")
        check("event version.ProjectVersion count == 1")
        check_readings(check)
