"""Helpers and planted faults for the SensorMonitor component test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``.

Planted faults rewrite or insert commands that pass through ``send()``; none changes a bench
action. ``fails`` names the checks each fault must break; the names are those of the plan's
evidence lines and are replaced by the names declared in the stimulus module in the harness
phase (``fth verify-plan --tests`` then refuses any name no test declares).

Helpers are declared here so the plan's metrics name them; their bodies are written in the
harness phase. Until then each returns UNVERIFIED, never a pass.
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
    ("max_fsw_gap", "Largest gap between FSW time tags of each listed channel <= bound_s."),
    ("same_time_tag", "Every sample set of the listed channels inside the window carries one FSW time tag per schedule call."),
    ("angles_match_reading", "Roll and pitch against atan2 of the acceleration in the imuManager.Reading sample nearest in time, bound_deg."),
    ("values_match_reading", "Value channels against the manager Reading sample nearest in time, exact for unchanged values."),
    ("valid_after_return_within", "First VALID sample of a validity channel after the return command or action, bound_s."),
    ("event_after_each_command_within", "Each loss event follows its BENCH_LINE OFF command within bound_s."),
    ("event_after_action_within", "Event time against the bench time of a bench action (bench-actions.log), bound_s."),
    ("invalid_after_action_within", "First INVALID sample of a validity channel after a bench action, bound_s, and INVALID until the next command."),
    ("gps_reading_advances", "nmeaGps gpsManager.Reading has a new sample for every fix sentence the bench source sent in the window."),
]:
    _declare(_name, _doc)


@planted_fault("sensor_line_kept_on", applies_to=["L5-1", "L5-2", "L5-3"], cls="stimulus",
               mechanism="argument `state` of sysTester.BENCH_LINE is rewritten from OFF to ON: the sensor keeps answering",
               fails={"L5-1": ["event sensorMonitor.Bmp280Lost count == 1", "F: last(sensorMonitor.Bmp280State) == LOST",
                               "F: last(sensorMonitor.TemperatureValid) == INVALID"],
                      "L5-2": ["event sensorMonitor.Mpu6050Lost count == 1", "F: last(sensorMonitor.Mpu6050State) == LOST",
                               "F: last(sensorMonitor.AttitudeValid) == INVALID"],
                      "L5-3": ["event sensorMonitor.GpsSilent count == 1", "F: last(sensorMonitor.GpsState) == LOST",
                               "F: last(sensorMonitor.FixValid) == INVALID"]})
def sensor_line_kept_on(test_id, command_name, args):
    if _is(command_name, "BENCH_LINE") and len(args) == 2 and str(args[1]) == "OFF":
        return [args[0], "ON"]
    return None


@planted_fault("bmp_line_dropped", applies_to=["L2-1"], cls="uut-state", kind="insert",
               mechanism="sysTester.BENCH_LINE(BMP280, OFF) is inserted before the first MARK of the test: the BMP280 is unpowered during a window that expects every metric valid; the closing BENCH_LINE(BMP280, ON) of the procedure restores it",
               fails={"L2-1": ["last(sensorMonitor.TemperatureValid) == VALID", "last(sensorMonitor.TemperatureInvalidReason) == NONE",
                               "last(sensorMonitor.Bmp280State) == PRESENT", "event sensorMonitor.Bmp280Lost count == 0"]})
def bmp_line_dropped(test_id, command_name, args):
    if _is(command_name, "MARK") and len(args) == 1 and int(args[0]) == 30:
        return [("sysTester.BENCH_LINE", ["BMP280", "OFF"]), (command_name, args)]
    return None
