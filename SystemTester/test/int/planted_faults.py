"""Helpers and planted faults for the PiSensor system test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``.

Planted faults rewrite or insert commands that pass through ``send()``; none changes a bench
action. ``fails`` names the checks each fault must break; the names are those of the plan's
evidence lines and are replaced by the names declared in the stimulus module in the harness
phase (``fth verify-plan --tests`` then refuses any name no test declares).

Helpers are declared here so the plan's metrics name them; their bodies are written in the
harness phase against the record layout of the plan's scope ("Record content"). Until then each
returns UNVERIFIED, never a pass.
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
    ("max_ground_gap", "Largest gap between ground reception times of each listed channel <= bound_s."),
    ("ground_gap_at_least", "Ground reception of the listed channels stops for at least bound_s inside the window."),
    ("command_completed_within", "OpCodeCompleted of the command's opcode - its dispatch <= bound_s (FSW clock)."),
    ("product_time_within", "Capture time record of the ground file against the bench time of the CAPTURE, bound_s."),
    ("product_sample_age_within", "Sample time of each valid metric record against the capture time record, bound_s."),
    ("first_samples_after_action_within", "First sample of each Table 1 channel after a bench action, bound_s; no command between."),
    ("valid_after_return_within", "First VALID sample of a validity channel after the return command or action, bound_s."),
    ("event_after_each_command_within", "Each loss event follows its BENCH_LINE OFF command within bound_s."),
    ("event_after_action_within", "Event time against the bench time of a bench action (bench-actions.log), bound_s."),
    ("resume_after_action_within", "First sample received and first command completion after a bench action, bound_s."),
    ("stall_time_between", "Stall event time against the start of the no-progress period, between lo_s and hi_s."),
    ("downlink_duration_at_least", "CFDP transaction duration from the ground transfer record >= bound_s."),
    ("no_frame_gaps", "Telemetry frame counter of the ground recorder has no gap inside the window, outside the `except` intervals."),
    ("clock_offset_within", "Pi clock against bench clock from the Platform event; a precondition (UNVERIFIED when not met)."),
    ("invalid_after_action_within", "First INVALID sample of a validity channel after a bench action, bound_s, and INVALID until the next command."),
]:
    _declare(_name, _doc)


@planted_fault("capture_twice", applies_to=["L2-3"], cls="stimulus", kind="insert",
               mechanism="CAPTURE is sent twice in a row (command productManager.CAPTURE, inserted copy); two products are written where the test expects one",
               fails={"L2-3": ["event productManager.ProductWritten count == 1"]})
def capture_twice(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return [(command_name, args), (command_name, args)]
    return None


@planted_fault("corrupt_product", applies_to=["L2-5", "L2-6", "L2-9"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(name) is inserted before productManager.DOWNLINK (after any DUMP_SHA256): the first two bytes of the picture record of the stored product are overwritten on board, so the file sent differs from the file hashed and is no JPEG; each test removes its products at teardown, so no later test or the final state sees it",
               fails={"L2-5": ["sha256 of record/raw/files/<P2> == hash in the sysTester.Sha256 event"],
                      "L2-6": ["ground file starts FFD8 and ends FFD9"],
                      "L2-9": ["sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event"]})
def corrupt_product(test_id, command_name, args):
    if _is(command_name, "DOWNLINK"):
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None


@planted_fault("sensor_line_kept_on", applies_to=["L5-1", "L5-3", "L5-9"], cls="stimulus",
               mechanism="argument `state` of sysTester.BENCH_LINE is rewritten from OFF to ON: the sensor keeps answering",
               fails={"L5-1": ["event sensorMonitor.Bmp280Lost count == 1", "F: last(sensorMonitor.TemperatureValid) == INVALID",
                               "t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s"],
                      "L5-3": ["event sensorMonitor.Mpu6050Lost count == 1", "F: last(sensorMonitor.AttitudeValid) == INVALID",
                               "t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s"],
                      "L5-9": ["attitude validity record INVALID"]})
def sensor_line_kept_on(test_id, command_name, args):
    if _is(command_name, "BENCH_LINE") and len(args) == 2 and str(args[1]) == "OFF":
        return [args[0], "ON"]
    return None


@planted_fault("corrupt_before_second_hash", applies_to=["L3-1", "L5-15"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(name) is inserted before the sysTester.DUMP_SHA256 whose argument `pass` is 2: the stored product changes between the two hashes and before the downlink; the test removes its product at teardown",
               fails={"L3-1": ["the two Sha256 events are equal", "sha256 of record/raw/files/<P> == hash in the first Sha256 event"],
                      "L5-15": ["the two Sha256 events are equal", "sha256 of record/raw/files/<P> == hash in the first Sha256 event"]})
def corrupt_before_second_hash(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256") and len(args) == 2 and int(args[1]) == 2:
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None
