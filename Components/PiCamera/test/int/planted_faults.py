"""Planted faults of the PiCamera component bench plan.

Each one inserts a command of the deployment as flown; none needs a test component.
"""
from fth.registry import planted_fault

CAPTURE = "piCamera.CAPTURE"


class _Once:
    """Insert one extra CAPTURE before the n-th CAPTURE of a test."""

    def __init__(self, nth):
        self.nth = nth
        self.seen = {}

    def __call__(self, test_id, command_name, args):
        if command_name != CAPTURE:
            return None
        count = self.seen.get(test_id, 0) + 1
        self.seen[test_id] = count
        if count == self.nth:
            return [(CAPTURE, []), (CAPTURE, list(args))]
        return None


_c1 = _Once(1)
_c2 = _Once(1)
_c3 = _Once(2)


@planted_fault("c1_second_capture", applies_to=["C-1"],
               fails={"C-1": ["event piCamera.CaptureCompleted count == 1", "event dpWriter.FileWritten count == 1",
                               "delta(piCamera.CapturesCompleted) == 1"]},
               cls="stimulus", mechanism="a second CAPTURE is sent before the one of the test", kind="insert")
def c1_second_capture(test_id, command_name, args):
    return _c1(test_id, command_name, args)


@planted_fault("c2_capture_before_hold", applies_to=["C-2"],
               fails={"C-2": ["event piCamera.CaptureFailed(reason=CAMERA_ERROR, step=OPEN) count == 1",
                               "event piCamera.CaptureFailed count == 1", "event cmdDisp.OpCodeError count == 1"]},
               cls="stimulus", mechanism="a second CAPTURE is sent while the camera is held", kind="insert")
def c2_capture_before_hold(test_id, command_name, args):
    return _c2(test_id, command_name, args)


@planted_fault("c3_capture_after_restart", applies_to=["C-3"],
               fails={"C-3": ["event piCamera.CaptureCompleted count == 2", "event dpWriter.FileWritten count == 2",
                               "last(piCamera.CapturesCompleted) == 1"]},
               cls="stimulus", mechanism="a second CAPTURE is sent after the restart", kind="insert")
def c3_capture_after_restart(test_id, command_name, args):
    return _c3(test_id, command_name, args)
