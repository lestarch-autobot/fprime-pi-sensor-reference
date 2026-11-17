"""Planted faults for the PiSensor system test plan.

Loaded by ``fth`` through ``plan.json: helpers_module``. Each fault rewrites or drops one
step of the stimulus of the tests it applies to; ``fails`` names the checks it must break.
The check names are placeholders of the design phase: the harness phase replaces them with
the names declared in ``test_pisensor_plan.py``.
"""
from fth.registry import planted_fault


def _is(command_name, short):
    return command_name == short or command_name.endswith("." + short)


def _fault(name, applies_to, cls, mechanism, fails, match=None, kind="rewrite"):
    @planted_fault(name, applies_to=applies_to, cls=cls, mechanism=mechanism, fails=fails, kind=kind)
    def fault(test_id, command_name, args):
        return match(command_name, args) if match else None
    fault.__name__ = name
    return fault


_fault("period_window_cut", ["L2-1", "L2-7"], "harness-expectation",
       "the harness stops the ground telemetry feed for 15 s inside the window, so the ground sees a gap above the bound",
       {"L2-1": ["max gap of temperature, attitude and location samples <= 2 s"],
        "L2-7": ["max gap of temperature, attitude and location samples <= 10 s"]})
_fault("capture_twice", ["L2-3"], "uut-state",
       "a second CAPTURE is sent while the first is in progress; a WARNING_LO rejection and a failed command response appear in a window that expects none",
       {"L2-3": ["commands completed with error == 0"]},
       match=lambda c, a: [(c, a), (c, a)] if _is(c, "CAPTURE") else None, kind="insert")
_fault("downlink_other_product", ["L2-5", "L2-9"], "harness-expectation",
       "DOWNLINK names the previous product, so the ground file differs from the product whose hash the test compares",
       {"L2-5": ["ground file sha256 == on-board sha256 of the named product"],
        "L2-9": ["ground file sha256 == on-board sha256 of the named product"]})
_fault("skip_sensor_off", ["L5-1", "L5-3", "L5-5", "L5-9"], "stimulus",
       "the bench action that removes the sensor is skipped; the sensor keeps answering",
       {"L5-1": ["event sensorMonitor.Bmp280Lost count == 1"], "L5-3": ["event sensorMonitor.Mpu6050Lost count == 1"],
        "L5-5": ["event sensorMonitor.GpsSilent count == 1"], "L5-9": ["attitude validity record == invalid"]})
_fault("gps_keep_fix", ["L5-7"], "stimulus", "the GPS source keeps sending fix sentences",
       {"L5-7": ["last(sensorMonitor.FixValid) == INVALID"]})
_fault("camera_left_on", ["L5-11"], "stimulus", "the camera is left available, so the capture succeeds",
       {"L5-11": ["event productManager.CaptureFailed count == 1"]})
_fault("storage_left_writable", ["L5-13"], "stimulus", "the product directory is left writable, so the capture succeeds",
       {"L5-13": ["event productManager.StorageFailed count == 1"]})
_fault("cfdp_left_running", ["L5-15"], "stimulus", "the ground CFDP service is left running, so the transfer finishes",
       {"L5-15": ["event productManager.DownlinkStalled count == 1"]})
_fault("outage_skipped", ["L5-17", "L5-19"], "stimulus", "the outage action is skipped; telemetry never stops",
       {"L5-17": ["telemetry gap in the window >= 60 s"], "L5-19": ["telemetry gap in the window >= 60 s"]})
_fault("gps_good_checksum", ["L5-21"], "stimulus", "position B is sent with a correct checksum, so it is reported",
       {"L5-21": ["position B never reported"]})
_fault("frame_not_corrupted", ["L6-1"], "stimulus", "the first frame is injected intact, so two commands are dispatched",
       {"L6-1": ["event cmdDisp.NoOpReceived count == 1"]})
