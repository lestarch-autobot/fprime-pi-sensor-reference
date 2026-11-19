"""Stimulus and named checks of the PiCamera component bench plan (plan.json)."""
import pytest

CAPTURE = "piCamera.CAPTURE"
PICTURE_MAX_SIZE = 262144
CAPTURE_MAX_S = 15.0
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


def complete(require):
    require("STD")
    require("every command sent in the window was dispatched", commands_dispatched)


def bracket(bench):
    bench.wait_samples("imuManager.Reading", 2, 30)


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
    # The opcode of CAPTURE is the one dispatched with the first CaptureStarted (same time tag)
    codes = {opcode(e.args["opCode"]) for e in dispatched if e.t == captures[0].t}
    if len(codes) != 1:
        return False, f"dispatch of CAPTURE not identified: {sorted(codes)}"
    code = codes.pop()
    starts = [e.t for e in dispatched if opcode(e.args["opCode"]) == code]
    ends = [e.t for name in RESPONSES for e in h.window.events(name) if opcode(e.args["opCode"]) == code]
    times = response_times(starts, ends)
    ok = len(times) > 0 and all(t is not None and t <= CAPTURE_MAX_S for t in times)
    return ok, f"response times {times} s for opcode {code:#x}"


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


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-020")
def test_C_1(window, send, bench, check, require):
    with window(10, 11):
        complete(require)
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        check("ABS")
        check("event piCamera.CaptureStarted count == 1")
        check("event piCamera.CaptureStarted precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")
        check("picture size within PICTURE_MAX_SIZE", picture_within_limit)
        check("every CAPTURE answered within CAPTURE_MAX_MS", responses_within_bound)


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-016", "REQ-PiCamera-019")
def test_C_2(window, send, bench, check, require):
    with window(20, 21):
        complete(require)
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
        check("first CaptureFailed is CAMERA_ERROR at OPEN", first_failure_is_camera_open)
        check("event piCamera.CaptureFailed count == 1")
        check("event cmdDisp.OpCodeError count == 1")
        check("event piCamera.CaptureFailed precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")
        check("no start-up between the failure and the success", no_start_between_failure_and_success)
        check("every CAPTURE answered within CAPTURE_MAX_MS", responses_within_bound)


@pytest.mark.req("REQ-PiCamera-024")
def test_C_3(window, send, bench, check, require):
    with window(30, 31):
        complete(require)
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bench.action("fsw_restart")
        bench.wait(20)
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        check("ABS")
        check("event piCamera.CaptureCompleted count == 2")
        check("event dpWriter.FileWritten count == 2")
        check("last(piCamera.CapturesCompleted) == 1")
        check("event version.ProjectVersion count == 1")
