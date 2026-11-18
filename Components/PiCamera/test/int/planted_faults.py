"""Helpers and planted faults for the PiCamera component test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``. Planted faults rewrite or insert
commands that pass through ``send()``; none changes a bench action. Helper bodies are written
in the harness phase; until then each returns UNVERIFIED, never a pass.
"""
from fth.registry import helper, planted_fault


def _is(command_name, short):
    return command_name == short or command_name.endswith("." + short)


def _declare(name, doc):
    @helper(name)
    def _h(ctx, **kwargs):
        return None, "helper body not written (design phase)", [], True
    _h.__name__ = name
    _h.__doc__ = doc


for _name, _doc in [
    ("picture_is_jfif", "Picture record of the ground file: bytes 0-1 FFD8, APP0 'JFIF', last two bytes FFD9 with nothing after, and a full decode by Pillow 11 (Image.load) without error or warning giving width x height."),
    ("pictures_differ", "sha256 of the picture records of the two ground files of the window differ."),
    ("picture_time_between", "Capture time record of the ground file lies between the bench time of CAPTURE sent - tol_s and the completion time + tol_s."),
    ("library_identity", "bench-actions.log: the package owning the libcamera.so that ldd resolves has the given version; every resolved library belongs to a package; no opencv library."),
    ("picture_time_after", "Capture time record of product b is later than that of product a."),
    ("trigger_margin", "Capture duration (CaptureStarted to ProductWritten, FSW clock) is at least factor times the bench trigger latency logged in bench-actions.log."),
    ("holder_acquired_within", "bench-actions.log: first frame line of the camera holder - its start <= bound_s."),
    ("final_sha256_matches", "sha256 in record/raw/final-state.txt equals the sha256 of the ground file of the window."),
]:
    _declare(_name, _doc)


_count = {}


def _nth(test_id, key):
    _count[(test_id, key)] = _count.get((test_id, key), 0) + 1
    return _count[(test_id, key)]


@planted_fault("capture_twice", applies_to=["L2-1"], cls="stimulus", kind="insert",
               mechanism="productManager.CAPTURE is sent twice in a row (inserted copy): two pictures are acquired where the test expects one; the window stays complete and P1 is still downlinked",
               fails={"L2-1": ["event piCamera.CaptureStarted count == 1", "delta(piCamera.CapturesCompleted) == 1",
                               "last(piCamera.LastPictureSize) == size of the picture record of the ground file of the last product written"]})
def capture_twice(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return [(command_name, args), (command_name, args)]
    return None


@planted_fault("corrupt_picture", applies_to=["L2-2"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(name) is inserted before the second productManager.DOWNLINK of the test (selected by occurrence): the first two bytes of the picture record of the stored product are overwritten on board; the test removes its products at teardown",
               fails={"L2-2": ["picture record of P2 is JFIF, SOI to EOI, 640 x 480", "sha256 of the picture records of P1 and P2 differ"]})
def corrupt_picture(test_id, command_name, args):
    if _is(command_name, "DOWNLINK") and _nth(test_id, "DOWNLINK") == 2:
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None


@planted_fault("camera_kept_absent", applies_to=["L5-1"], cls="stimulus",
               mechanism="argument `state` of sysTester.BENCH_LINE(CAMERA, ON) is rewritten to OFF: the camera stays unavailable for the capture that must succeed; the test's teardown binds the driver again by a bench action, so no later test is affected",
               fails={"L5-1": ["event cmdDisp.OpCodeError count == 1", "event piCamera.CaptureFailed(reason=NO_CAMERA, step=DETECT) count == 1",
                               "event piCamera.CaptureFailed count == 1", "delta(piCamera.CapturesFailed) == 1", "second CAPTURE completes",
                               "delta(piCamera.CapturesCompleted) == 1", "last(piCamera.CameraPresent) == true",
                               "picture record of P1 is JFIF, SOI to EOI, 640 x 480"]})
def camera_kept_absent(test_id, command_name, args):
    if _is(command_name, "BENCH_LINE") and len(args) == 2 and str(args[0]) == "CAMERA" and str(args[1]) == "ON":
        return [args[0], "OFF"]
    return None


@planted_fault("capture_after_restart_dropped", applies_to=["L3-1"], cls="stimulus",
               mechanism="the second productManager.CAPTURE of the test (the one after the restart, selected by occurrence) is rewritten to cmdDisp.CMD_NO_OP: no picture is acquired after the restart",
               fails={"L3-1": ["B: event piCamera.CaptureStarted count == 1", "B: event productManager.ProductWritten count == 1",
                               "picture record of P1 is JFIF, SOI to EOI, 640 x 480"]})
def capture_after_restart_dropped(test_id, command_name, args):
    if _is(command_name, "CAPTURE") and _nth(test_id, "CAPTURE") == 2:
        return ("cmdDisp.CMD_NO_OP", [])
    return None
