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
    ("picture_is_jfif", "Picture record of the ground file: starts FFD8 FFE0 'JFIF', ends FFD9, SOF0 width and height equal the arguments."),
    ("pictures_differ", "sha256 of the picture records of the two ground files of the window differ."),
    ("picture_time_between", "Capture time record of the ground file lies between the bench time of CAPTURE sent - tol_s and the completion time + tol_s."),
    ("library_identity", "bench-actions.log: dpkg version of libcamera-dev starts with the argument; ldd of the image lists libcamera and no opencv library."),
    ("final_sha256_matches", "sha256 in record/raw/final-state.txt equals the sha256 of the ground file of the window."),
]:
    _declare(_name, _doc)


@planted_fault("capture_dropped", applies_to=["L2-1"], cls="stimulus",
               mechanism="command productManager.CAPTURE is rewritten to cmdDisp.CMD_NO_OP: no picture is acquired where the test expects one",
               fails={"L2-1": ["event piCamera.CaptureStarted count == 1", "delta(piCamera.CapturesCompleted) == 1"]})
def capture_dropped(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return ("cmdDisp.CMD_NO_OP", [])
    return None


@planted_fault("corrupt_picture", applies_to=["L2-2"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(name) is inserted before the second productManager.DOWNLINK: the first two bytes of the picture record of the stored product are overwritten on board; the test removes its products at teardown",
               fails={"L2-2": ["picture record of P2 is JFIF, SOI to EOI, 640 x 480"]})
def corrupt_picture(test_id, command_name, args):
    if _is(command_name, "DOWNLINK") and str(args[0]) == "P2":
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None


@planted_fault("camera_kept_absent", applies_to=["L5-1"], cls="stimulus",
               mechanism="argument `state` of the second sysTester.BENCH_LINE(CAMERA, ON) is rewritten to OFF: the camera stays unavailable for the capture that must succeed",
               fails={"L5-1": ["event piCamera.CaptureFailed count == 1", "delta(piCamera.CapturesCompleted) == 1"]})
def camera_kept_absent(test_id, command_name, args):
    if _is(command_name, "BENCH_LINE") and len(args) == 2 and str(args[0]) == "CAMERA" and str(args[1]) == "ON":
        return [args[0], "OFF"]
    return None


@planted_fault("no_restart", applies_to=["L3-1"], cls="harness-expectation",
               mechanism="the harness expects two process starts in the window where the procedure makes one",
               fails={"L3-1": ["event sysTester.Started count == 1"]})
def no_restart(test_id, command_name, args):
    return None
