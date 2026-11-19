"""Stimulus and named checks of the PiCamera component bench plan (plan.json)."""
import pytest

CAPTURE = "piCamera.CAPTURE"
PICTURE_MAX_SIZE = 262144


def bracket(bench):
    bench.wait_samples("imuManager.Reading", 2, 30)


def picture_within_limit(h):
    done = h.window.events("piCamera.CaptureCompleted")
    sizes = [int(e.args["bytes"]) for e in done]
    return all(0 < s <= PICTURE_MAX_SIZE for s in sizes) and len(sizes) > 0, f"picture sizes {sizes}"


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-020")
def test_C_1(window, send, bench, check, require):
    with window(10, 11):
        require("STD")
        bracket(bench)
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        check("ABS")
        check("event piCamera.CaptureStarted precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")
        check("picture size within PICTURE_MAX_SIZE", picture_within_limit)
        check("delta(piCamera.CapturesCompleted) == 1")


@pytest.mark.req("REQ-PiCamera-009", "REQ-PiCamera-016", "REQ-PiCamera-019")
def test_C_2(window, send, bench, check, require):
    with window(20, 21):
        require("STD")
        bracket(bench)
        bench.action("camera_hold")
        try:
            send(CAPTURE, [], wait_completion=False)
            bench.wait_event("cmdDisp.OpCodeError", 30)
        finally:
            bench.action("camera_release")
        send(CAPTURE, [])
        bench.wait_event("dpWriter.FileWritten", 30)
        bracket(bench)
        check("event piCamera.CaptureFailed(reason=CAMERA_ERROR, step=OPEN) count == 1")
        check("event piCamera.CaptureFailed count == 1")
        check("event cmdDisp.OpCodeError count == 1")
        check("event piCamera.CaptureFailed precedes event piCamera.CaptureCompleted")
        check("event piCamera.CaptureCompleted count == 1")
        check("event dpWriter.FileWritten count == 1")


@pytest.mark.req("REQ-PiCamera-024")
def test_C_3(window, send, bench, check, require):
    with window(30, 31):
        require("STD")
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
