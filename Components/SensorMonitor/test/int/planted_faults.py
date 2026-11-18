"""Helpers and planted faults for the SensorMonitor component test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``.

Planted faults rewrite or insert commands that pass through ``send()``; none changes a bench
action. ``fails`` names the checks each fault must break; the names are those of the plan's
evidence lines and are replaced by the names declared in the stimulus module in the harness
phase (``fth verify-plan --tests`` then refuses any name no test declares).

Helpers are declared here so the plan's metrics name them; their bodies are written in the
harness phase. Until then each returns UNVERIFIED, never a pass.
"""
import json
from pathlib import Path

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
    ("bench_ready_at_start", "Precondition: bmpManager.Reading and imuManager.Reading advance in the lookback before the START marker and the bench log shows the GPS source sending; UNVERIFIED when not met; reads no sensorMonitor channel."),
    ("max_fsw_gap", "Largest gap between FSW time tags of each listed channel, window edges included, <= bound_s, with at least min_samples samples."),
    ("same_time_tag", "The listed channels carry one FSW time tag per schedule call, every call of the window."),
    ("angles_match_reading", "Roll and pitch against atan2 of the acceleration in the imuManager.Reading sample nearest in FSW time, bound_deg, at least min_pairs pairs."),
    ("values_match_reading", "Temperature and gyro channels against the manager Reading sample nearest in FSW time, within the allowances, at least min_pairs pairs."),
    ("angle_step_after_action", "Roll or pitch changes by at least bound_deg between the samples before and after the logged tilt action."),
    ("location_equals_script", "Latitude, Longitude, Altitude samples equal the values of the bench sentence script, at least min_samples samples."),
    ("event_after_command_within", "Time from the one matching command of the window to the one matching event, between lo_s and hi_s (FSW clock)."),
    ("valid_after_command_within", "First VALID sample of a validity channel after the matching command of the window, bound_s (FSW clock)."),
    ("event_after_action_within", "Event time against the bench time of a bench action (bench-actions.log), between lo_s and hi_s."),
    ("valid_after_action_within", "First VALID sample of a validity channel after a bench action, bound_s."),
    ("invalid_after_action_within", "First INVALID sample of a validity channel after a bench action, bound_s, and INVALID until the END marker."),
]:
    _declare(_name, _doc)


def _metric(test_id, helper_name, window=None):
    """Verbatim text of a plan metric, so `fails` cannot drift from the plan."""
    plan = json.loads((Path(__file__).parent / "plan.json").read_text(encoding="utf-8"))
    for t in plan["tests"]:
        if t["id"] == test_id:
            for m in t["metrics"]:
                if isinstance(m, dict) and m["helper"] == helper_name and (window is None or m["args"].get("window") == window):
                    return m["text"]
    raise KeyError((test_id, helper_name, window))


_SM = "sensorMonitor."


@planted_fault("sensor_line_kept_on", applies_to=["L5-1", "L5-2"], cls="stimulus",
               mechanism="argument `state` of sysTester.BENCH_LINE is rewritten from OFF to ON: the sensor keeps answering, so it is never lost and never returns",
               fails={"L5-1": ["F: event sensorMonitor.Bmp280Lost count == 1", "F: last(sensorMonitor.Bmp280State) == LOST",
                               "F: last(sensorMonitor.TemperatureValid) == INVALID", "F: last(sensorMonitor.TemperatureInvalidReason) == STALE",
                               "B: event sensorMonitor.Bmp280Returned count == 1", _metric("L5-1", "event_after_command_within", "F")],
                      "L5-2": ["F: event sensorMonitor.Mpu6050Lost count == 1",
                               "F: event sensorMonitor.Mpu6050Lost(reason=IDENTITY, status=I2C_OTHER_ERR) count == 1",
                               "F: last(sensorMonitor.Mpu6050State) == LOST", "F: last(sensorMonitor.AttitudeValid) == INVALID",
                               "F: last(sensorMonitor.AttitudeInvalidReason) == IDENTITY",
                               "B: event sensorMonitor.Mpu6050Returned count == 1", _metric("L5-2", "event_after_command_within", "F")]})
def sensor_line_kept_on(test_id, command_name, args):
    if _is(command_name, "BENCH_LINE") and len(args) == 2 and str(args[1]) == "OFF":
        return [args[0], "ON"]
    return None


@planted_fault("bmp_line_dropped", applies_to=["L2-1"], cls="uut-state", kind="insert",
               mechanism="sysTester.BENCH_LINE(BMP280, OFF) is inserted before the START marker: the BMP280 is unpowered for the whole window; the procedure's BENCH_LINE(BMP280, ON) after the END marker and its settle wait restore it, so no later test is disturbed. The unpowered sensor fails the manager's reset write (DeviceFailure, BmpManager.cpp lines 57 to 63) and leaves no Reading sample to pair within 1.5 s",
               fails={"L2-1": ["last(sensorMonitor.TemperatureValid) == VALID", "last(sensorMonitor.TemperatureInvalidReason) == NONE",
                               "last(sensorMonitor.Bmp280State) == PRESENT", "event sensorMonitor.Bmp280Lost count == 0",
                               "event bmpManager.DeviceFailure count == 0", _metric("L2-1", "values_match_reading")]})
def bmp_line_dropped(test_id, command_name, args):
    if _is(command_name, "MARK") and len(args) == 1 and int(args[0]) == 30:
        return [("sysTester.BENCH_LINE", ["BMP280", "OFF"]), (command_name, args)]
    return None


@planted_fault("mpu_line_dropped", applies_to=["L2-2"], cls="uut-state", kind="insert",
               mechanism="sysTester.BENCH_LINE(MPU6050, OFF) is inserted before the START marker: the MPU6050 is unpowered for the whole window, so roll and pitch freeze and the tilt is not seen; the procedure's BENCH_LINE(MPU6050, ON) after the END marker and its settle wait restore it",
               fails={"L2-2": ["last(sensorMonitor.AttitudeValid) == VALID", "last(sensorMonitor.AttitudeInvalidReason) == NONE",
                               "last(sensorMonitor.Mpu6050State) == PRESENT", "event sensorMonitor.Mpu6050Lost count == 0",
                               "event imuManager.I2cError count == 0", _metric("L2-2", "angle_step_after_action"),
                               _metric("L2-2", "angles_match_reading")]})
def mpu_line_dropped(test_id, command_name, args):
    if _is(command_name, "MARK") and len(args) == 1 and int(args[0]) == 40:
        return [("sysTester.BENCH_LINE", ["MPU6050", "OFF"]), (command_name, args)]
    return None
