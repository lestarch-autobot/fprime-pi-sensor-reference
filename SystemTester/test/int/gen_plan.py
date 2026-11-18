#!/usr/bin/env python3
"""Generates plan.json for the PiSensor system test plan (design phase). Run from this directory."""
import json, collections
R = lambda *n: [f"REQ-PiSensor-{i:03d}" for i in n]
def W(a, b, name="W"): return {"name": name, "start_id": a, "end_id": b, "reset": False}
def H(name, text, **args): return {"helper": name, "text": text, "args": args}
T1 = ["sensorMonitor.Temperature", "sensorMonitor.TemperatureValid", "sensorMonitor.Roll", "sensorMonitor.Pitch",
      "sensorMonitor.AttitudeValid", "sensorMonitor.GyroX", "sensorMonitor.GyroY", "sensorMonitor.GyroZ",
      "sensorMonitor.Latitude", "sensorMonitor.Longitude", "sensorMonitor.Altitude", "sensorMonitor.FixValid"]
def gap(bound, where="the window"): return H("max_ground_gap", f"largest gap between ground reception times of every Table 1 channel in {where} <= {bound} s", channels="Table1", bound_s=bound)
T = []
def t(id, title, purpose, covers, setup, procedure, windows, metrics=(), knobs=(), evidence="", rationale=()):
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup,
              "procedure": list(procedure), "windows": windows, "metrics": list(metrics),
              "rationale": [{"pred": p, "text": x} for p, x in rationale], "knobs": list(knobs), "evidence": evidence})
NOM = "Prototype image running, link up, all four sensors answering, product directory empty."
FLT = "Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty."
NORESTART = "event sysTester.Started count == 0"
CAP30 = H("command_completed_within", "CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s", command="productManager.CAPTURE", bound_s=30)
SHA = "check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event"
REC = ("checks on the ground file: starts FFD8 and ends FFD9; SOF0 width >= 640 and height >= 480; one picture, location, attitude and temperature record; "
       "all three validity records VALID")
TIMES = [H("product_time_within", "bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s", tol_s=2),
         H("product_sample_age_within", "|sample time - capture time| <= 2 s for temperature, attitude and location", bound_s=2)]

# ---- prototype block (TCP) ----
t("L0-1", "Image and platform identity, prototype image", "Proves the running image is the manifest's prototype image and runs on a Raspberry Pi 5 under Raspberry Pi OS 13, over TCP.", R(42, 16),
  "Prototype image running on the Raspberry Pi 5; link up.",
  ["MARK(10)", "VERSION(ALL)", "PLATFORM()", "bracket (2 Heartbeat samples)", "action: list TCP sockets of the deployment process", "MARK(11)"], [W(10, 11)],
  metrics=[H("clock_offset_within", "|time of the sysTester.Platform event - bench time of its reception| <= 0.5 s (require)", bound_s=0.5)],
  evidence="Version events equal the manifest describe strings; check: sysTester.Platform model starts with \"Raspberry Pi 5\" and os_version == 13; check: one TCP connection, to the bridge port.")
t("L0-2", "Marker round-trip", "Proves the marker command round-trips so every later window can be bracketed.", [], "As L0-1.",
  ["MARK(20)", "bracket (2 Heartbeat samples)", "MARK(0xA5A5)", "MARK(21)"], [W(20, 21)], evidence="Three Marker events in order, ids byte-exact.")
t("L2-1", "Sensor telemetry period", "Proves every Table 1 channel arrives at the ground at least every 2 s.", R(1, 2, 3, 16, 17), NOM,
  ["MARK(30)", "wait 60 s", "MARK(31)"], [W(30, 31)], metrics=[gap(2)],
  evidence="Channel strips over 60 s; check: every Table 1 channel has samples and all three validity channels read VALID.")
t("L2-2", "Sensor telemetry period under command traffic", "Proves the 2 s telemetry period holds while commands are dispatched.", R(1, 2, 3, 16, 17), NOM,
  ["MARK(32)", "NO_OP()", "wait 10 s", "NO_OP()", "wait 10 s", "NO_OP()", "wait 10 s", "MARK(33)"], [W(32, 33)], metrics=[gap(2)],
  evidence="As L2-1; check: event cmdDisp.NoOpReceived count == 3.")
t("L2-3", "Capture and downlink of one product", "Proves one capture makes one product with a JPEG of at least 640x480 and valid, timed metrics, delivered byte-identical by CFDP class 2.", R(4, 5, 6, 7, 10, 12, 13, 16, 17), NOM,
  ["MARK(40)", "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(41)"], [W(40, 41)],
  metrics=[CAP30] + TIMES, knobs=["capture_twice"],
  evidence="check: event productManager.ProductWritten count == 1 (names P); " + SHA + "; check: CFDP transaction of P at the ground is class 2 and finished complete; " + REC + ".")
t("L2-4", "Capture and downlink, repeated", "Proves a second capture makes a new product with its own name and capture time, delivered byte-identical.", R(4, 5, 6, 7, 10, 12, 13, 16, 17), NOM,
  ["MARK(42)", "CAPTURE()", "wait 5 s", "CAPTURE()", "DUMP_SHA256(P2, 1)", "DOWNLINK(P2)", "wait CFDP transaction finished at the ground", "MARK(43)"], [W(42, 43)],
  metrics=[CAP30] + TIMES,
  evidence="check: event productManager.ProductWritten count == 2 with different names; capture time of P2 later than the first; " + SHA.replace("<P>", "<P2>") + "; class 2 check; " + REC + ".")
t("L2-5", "Downlink selects the named product", "Proves a downlink command sends the product it names and no other.", R(12, 13), NOM,
  ["MARK(44)", "CAPTURE()", "wait 5 s", "CAPTURE()", "DUMP_SHA256(P2, 1)", "DOWNLINK(P2)", "wait CFDP transaction finished at the ground", "MARK(45)"], [W(44, 45)],
  knobs=["corrupt_product"], evidence="check: exactly one file arrived and its name is P2; " + SHA.replace("<P>", "<P2>") + "; class 2 check.")
t("L2-6", "Product content at the ground", "Proves the picture and the three metric records of a product are intact in the ground copy.", R(4, 5), NOM,
  ["MARK(46)", "CAPTURE()", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(47)"], [W(46, 47)],
  knobs=["corrupt_product"], evidence=REC + ".")
def restart(id, m, title, action, extra):
    t(id, title, f"Proves Table 1 telemetry resumes within 60 s of {extra} without ground commands and a stored product is still downlinkable, unchanged.", R(38, 39), NOM,
      [f"MARK({m})", "CAPTURE()", "DUMP_SHA256(P, 1)", f"MARK({m+1})", f"action: {action}", "wait first Table 1 samples at the ground", f"MARK({m+2})", "PLATFORM()", "DUMP_SHA256(P, 2)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", f"MARK({m+3})"],
      [W(m, m+1, "W1"), W(m+1, m+2, "R"), W(m+2, m+3, "W2")],
      metrics=[H("first_samples_after_action_within", "first sample of every Table 1 channel - bench time of the action <= 60 s, no command sent between them", action=action, bound_s=60), H("clock_offset_within", "W2: |time of the sysTester.Platform event - bench time of its reception| <= 0.5 s (require)", bound_s=0.5)],
      knobs=["corrupt_before_second_hash"] if id == "L3-1" else [],
      evidence="R: check event sysTester.Started count == 1 and last(sysTester.UptimeS) < 60; W2: check the two Sha256 events are equal and sha256 of record/raw/files/<P> == hash in the first Sha256 event.",
      rationale=[("event sysTester.Started count == 1", "the Pi system clock does not step back at a restart, so the restart is judged by the start-up event, not by a clock epoch")])
restart("L3-1", 70, "Process restart", "kill the deployment process (SIGKILL); the service unit restarts it", "a process restart")
restart("L3-2", 74, "Reboot", "reboot the Raspberry Pi", "a reboot")
def interrupted(id, m, title, action):
    t(id, title, "Proves a capture interrupted by a restart leaves no product, complete or partial.", R(29), NOM,
      [f"MARK({m})", "LIST_DIR(products)", "CAPTURE() without waiting for completion", "wait event piCamera.CaptureStarted", f"action: {action}, triggered by the CaptureStarted event", "wait first Table 1 samples at the ground", "LIST_DIR(products)", "LIST_PRODUCTS()", f"MARK({m+1})"], [W(m, m+1)],
      evidence="require (else UNVERIFIED, the race was lost): event piCamera.CaptureStarted count == 1 and event productManager.ProductWritten count == 0 before the action. An orderly stop that lets the capture finish is not allowed: the product count must be unchanged. check: event sysTester.Started count == 1; check: file names and count of the two sysTester.DirListing events are equal; check: event productManager.ProductWritten count == 0; product list empty.",
      rationale=[("commands_sent == count(event cmdDisp.OpCodeDispatched)", "the CAPTURE has no completion; the window requires STD-RST (dispatch counted per process run)")])
interrupted("L3-3", 80, "Capture interrupted by a process kill", "kill the deployment process (SIGKILL)")
interrupted("L3-4", 82, "Capture interrupted by a service stop", "stop and start the service unit (SIGTERM, then SIGKILL after the unit stop time of 2 s)")
def lost_metrics(ev, valid, cmd_off="sysTester.BENCH_LINE"):
    return [f"t(event {ev}) - t({cmd_off} sent) <= 10 s",
            H("valid_after_return_within", f"first {valid} == VALID after the return - time of the return <= 10 s", channel=valid, bound_s=10)]
t("L5-1", "BMP280 failure and return", "Proves a failed BMP280 raises WARNING_HI within 10 s, temperature reads invalid, and it is valid again within 10 s of the return, without a restart.", R(19, 22, 23), NOM,
  ["MARK(100)", "BENCH_LINE(BMP280, OFF)", "wait 15 s", "MARK(101)", "BENCH_LINE(BMP280, ON)", "wait 15 s", "MARK(102)"], [W(100, 101, "F"), W(101, 102, "B")],
  metrics=lost_metrics("sensorMonitor.Bmp280Lost", "sensorMonitor.TemperatureValid"), knobs=["sensor_line_kept_on"],
  evidence="F: check event sensorMonitor.Bmp280Lost count == 1 (WARNING_HI), last(sensorMonitor.TemperatureValid) == INVALID, attitude and fix stay VALID. B: last(sensorMonitor.TemperatureValid) == VALID; both: " + NORESTART + ".")
t("L5-2", "BMP280 failure before a capture", "Proves a BMP280 failed for 3 s is reported and its temperature is marked invalid in a product captured then.", R(19, 22, 23, 8), NOM,
  ["MARK(103)", "BENCH_LINE(BMP280, OFF)", "wait 3 s", "CAPTURE()", "wait 10 s", "MARK(104)", "BENCH_LINE(BMP280, ON)", "wait 15 s", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(105)"], [W(103, 104, "F"), W(104, 105, "B")],
  metrics=lost_metrics("sensorMonitor.Bmp280Lost", "sensorMonitor.TemperatureValid"),
  evidence="As L5-1; ground file: temperature validity record INVALID, attitude and location VALID.")
t("L5-3", "MPU6050 failure and return", "Proves a failed MPU6050 raises WARNING_HI within 10 s, attitude reads invalid, and it is valid again within 10 s of the return, without a restart.", R(20, 22, 23), NOM,
  ["MARK(110)", "BENCH_LINE(MPU6050, OFF)", "wait 15 s", "MARK(111)", "BENCH_LINE(MPU6050, ON)", "wait 15 s", "MARK(112)"], [W(110, 111, "F"), W(111, 112, "B")],
  metrics=lost_metrics("sensorMonitor.Mpu6050Lost", "sensorMonitor.AttitudeValid"), knobs=["sensor_line_kept_on"],
  evidence="F: check event sensorMonitor.Mpu6050Lost count == 1 (WARNING_HI), last(sensorMonitor.AttitudeValid) == INVALID. B: VALID; both: " + NORESTART + ".")
t("L5-4", "MPU6050 failure twice", "Proves the MPU6050 loss report and the recovery repeat on a second failure in the same run.", R(20, 22, 23), NOM,
  ["MARK(113)", "BENCH_LINE(MPU6050, OFF)", "wait 15 s", "BENCH_LINE(MPU6050, ON)", "wait 15 s", "MARK(114)", "BENCH_LINE(MPU6050, OFF)", "wait 15 s", "BENCH_LINE(MPU6050, ON)", "wait 15 s", "MARK(115)"], [W(113, 114, "C1"), W(114, 115, "C2")],
  metrics=[H("event_after_each_command_within", "each sensorMonitor.Mpu6050Lost - its BENCH_LINE(MPU6050, OFF) sent <= 10 s", bound_s=10),
           H("valid_after_return_within", "first sensorMonitor.AttitudeValid == VALID after each return - time of the return <= 10 s", channel="sensorMonitor.AttitudeValid", bound_s=10)],
  evidence="Each window: check event sensorMonitor.Mpu6050Lost count == 1, last(sensorMonitor.AttitudeValid) == VALID, " + NORESTART + ".")
GPSM = lambda s: [H("event_after_action_within", f"t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s", action="gps_stop", bound_s=10),
                  H("valid_after_return_within", "first sensorMonitor.FixValid == VALID after the restart action - bench time of the action <= 10 s", channel="sensorMonitor.FixValid", bound_s=10)]
t("L5-5", "GPS silence and return", "Proves GPS silence raises WARNING_HI within 10 s, location reads invalid, and it is valid again within 10 s of the return, without a restart.", R(21, 22, 23), NOM,
  ["MARK(120)", "action: stop the GPS sentence source", "wait 15 s", "MARK(121)", "action: restart the GPS sentence source (1 Hz, fix)", "wait 15 s", "MARK(122)"], [W(120, 121, "F"), W(121, 122, "B")],
  metrics=GPSM(0), evidence="F: check event sensorMonitor.GpsSilent count == 1 (WARNING_HI), last(sensorMonitor.FixValid) == INVALID; source byte counter in bench-actions.log does not advance. B: VALID; both: " + NORESTART + ".")
t("L5-6", "GPS silence for 120 s", "Proves a long GPS silence is reported once and recovery still takes at most 10 s.", R(21, 22, 23), NOM,
  ["MARK(123)", "action: stop the GPS sentence source", "wait 120 s", "MARK(124)", "action: restart the GPS sentence source (1 Hz, fix)", "wait 15 s", "MARK(125)"], [W(123, 124, "F"), W(124, 125, "B")],
  metrics=GPSM(0), evidence="As L5-5 with one GpsSilent event over 120 s.")
t("L5-7", "GPS without a fix", "Proves a receiver reporting no fix reads fix invalid, raises no silence event, and gives location invalid in a product.", R(24, 9), NOM,
  ["MARK(130)", "action: GPS source sends no-fix GGA sentences at 1 Hz", "wait 10 s", "CAPTURE()", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "action: GPS source sends fix sentences at 1 Hz", "MARK(131)"], [W(130, 131)],
  metrics=[H("invalid_after_action_within", "first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 3 s (one GGA period of 1 s plus one telemetry period of 2 s), INVALID from then to the CAPTURE", channel="sensorMonitor.FixValid", bound_s=3)],
  evidence="check: sensorMonitor.FixValid == INVALID from 3 s after the action to the CAPTURE; event sensorMonitor.GpsSilent count == 0; source byte counter advances; ground file: location validity record INVALID, temperature and attitude VALID.")
t("L5-8", "GPS fix lost and regained", "Proves the no-fix indication clears when the fix returns and a product captured then has a valid location.", R(24, 9), NOM,
  ["MARK(132)", "action: GPS source sends no-fix GGA sentences at 1 Hz", "wait 10 s", "CAPTURE()", "action: GPS source sends fix sentences at 1 Hz", "wait 10 s", "CAPTURE()", "DOWNLINK(P1)", "DOWNLINK(P2)", "wait CFDP transactions finished at the ground", "MARK(133)"], [W(132, 133)],
  evidence="Ground files: location validity INVALID in P1 and VALID in P2; last(sensorMonitor.FixValid) == VALID; event sensorMonitor.GpsSilent count == 0.")
t("L5-9", "Stale attitude at capture", "Proves attitude older than 2 s at capture is marked invalid in the product while the others stay valid.", R(8), NOM,
  ["MARK(134)", "BENCH_LINE(MPU6050, OFF)", "wait 3 s", "CAPTURE()", "BENCH_LINE(MPU6050, ON)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(135)"], [W(134, 135)],
  knobs=["sensor_line_kept_on"], evidence="Ground file: attitude validity record INVALID, temperature and location VALID.")
t("L5-10", "Stale location at capture", "Proves a location older than 2 s at capture is marked invalid in the product while the others stay valid.", R(8), NOM,
  ["MARK(136)", "action: stop the GPS sentence source", "wait 3 s", "CAPTURE()", "action: restart the GPS sentence source (1 Hz, fix)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(137)"], [W(136, 137)],
  evidence="Ground file: location validity record INVALID, temperature and attitude VALID.")
ERR = [("event cmdDisp.OpCodeError count == 0", "the CAPTURE is expected to fail; the window requires STD-ERR (exactly one OpCodeError, of CAPTURE)")]
t("L5-11", "Camera absent", "Proves a capture with the camera unavailable fails its command with WARNING_HI and leaves no file.", R(28, 29), NOM,
  ["MARK(140)", "action: make the camera unavailable (unbind its driver)", "LIST_DIR(products)", "CAPTURE()", "LIST_DIR(products)", "LIST_PRODUCTS()", "action: make the camera available", "MARK(141)"], [W(140, 141)], rationale=ERR,
  evidence="check: CAPTURE completes with error; event productManager.CaptureFailed count == 1 (WARNING_HI); the two sysTester.DirListing events are equal; product list unchanged.")
t("L5-12", "Camera absent, then present", "Proves a failed capture leaves no file and the next capture succeeds once the camera is back.", R(28, 29), NOM,
  ["MARK(142)", "action: make the camera unavailable (unbind its driver)", "LIST_DIR(products)", "CAPTURE()", "LIST_DIR(products)", "action: make the camera available", "CAPTURE()", "MARK(143)"], [W(142, 143)], rationale=ERR,
  evidence="As L5-11, then event productManager.ProductWritten count == 1.")
t("L5-13", "Storage read-only", "Proves a capture that cannot store its product fails its command with WARNING_HI and leaves no file.", R(31, 29), NOM,
  ["MARK(144)", "action: remount the product file system read-only", "LIST_DIR(products)", "CAPTURE()", "action: remount the product file system read-write", "LIST_DIR(products)", "MARK(145)"], [W(144, 145)], rationale=ERR,
  evidence="check: CAPTURE completes with error; event productManager.StorageFailed count == 1 (WARNING_HI); the two DirListing events are equal.")
t("L5-14", "Storage full", "Proves a capture with no free space fails its command with WARNING_HI and leaves no partial file.", R(31, 29), NOM,
  ["MARK(146)", "action: fill the product file system (64 MB, its own) with one bench file", "LIST_DIR(products)", "CAPTURE()", "LIST_DIR(products)", "action: remove the fill file", "MARK(147)"], [W(146, 147)], rationale=ERR,
  evidence="As L5-13; the two DirListing events (taken while full) are equal.")
t("L5-15", "CFDP transfer with no ground peer", "Proves a transfer that makes no progress for 60 s ends with WARNING_HI and the product is unchanged and downlinkable afterwards.", R(34, 35), NOM,
  ["MARK(150)", "CAPTURE()", "DUMP_SHA256(P, 1)", "action: stop the ground CFDP service", "DOWNLINK(P)", "wait 95 s", "action: start the ground CFDP service", "DUMP_SHA256(P, 2)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(151)"], [W(150, 151)],
  metrics=[H("stall_time_between", "55 s <= t(event productManager.DownlinkStalled) - t(first productManager.DOWNLINK sent) <= 90 s", lo_s=55, hi_s=90)], knobs=["corrupt_before_second_hash"],
  evidence="check: event productManager.DownlinkStalled count == 1 (WARNING_HI); the two Sha256 events are equal; sha256 of record/raw/files/<P> == hash in the first Sha256 event.",
  rationale=[("55 s <= ... <= 90 s", "60 s of the requirement, less 5 s for the last progress before the stop, plus two periods of the 10 s check timer and the CFDP inactivity timer granularity")])
t("L5-17", "Link outage of 65 s", "Proves commanding and telemetry resume within 10 s of the end of a 65 s link outage, without a restart, and a product stored before it is downlinkable.", R(36, 38), NOM,
  ["MARK(160)", "CAPTURE()", "DUMP_SHA256(P, 1)", "action: block the TCP link at the workstation", "wait 65 s", "action: unblock the TCP link", "NO_OP()", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(161)"], [W(160, 161)],
  metrics=[H("ground_gap_at_least", "gap of ground reception of Table 1 channels during the outage >= 60 s", bound_s=60),
           H("resume_after_action_within", "first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s", action="link_unblock", bound_s=10)],
  evidence="check: " + NORESTART + "; delta(sysTester.UptimeS) > 65; " + SHA + ".",
  rationale=[("event comQueue.QueueOverflow count == 0", "queue overflow is expected during the outage; the window requires STD-OUT and judges no absence")])
t("L5-18", "Link outage of 120 s", "Proves recovery within 10 s from a longer link outage, without a restart.", R(36), NOM,
  ["MARK(162)", "action: block the TCP link at the workstation", "wait 120 s", "action: unblock the TCP link", "NO_OP()", "MARK(163)"], [W(162, 163)],
  metrics=[H("ground_gap_at_least", "gap of ground reception of Table 1 channels during the outage >= 115 s", bound_s=115),
           H("resume_after_action_within", "first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s", action="link_unblock", bound_s=10)],
  evidence="check: " + NORESTART + "; delta(sysTester.UptimeS) > 120.", rationale=[("event comQueue.QueueOverflow count == 0", "as L5-17")])
t("L5-19", "Ground-system outage of 65 s", "Proves commanding and telemetry resume within 10 s of the ground system's return, without a restart of the flight software, and a stored product is downlinkable.", R(37, 38), NOM,
  ["MARK(164)", "CAPTURE()", "DUMP_SHA256(P, 1)", "action: stop the YAMCS server only (`fprime-comm-bridge`, run from its own command line, and the frame recorder stay up)", "wait 65 s", "action: start the YAMCS server", "NO_OP()", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(165)"], [W(164, 165)],
  metrics=[H("resume_after_action_within", "first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s", action="yamcs_ready", bound_s=10)],
  evidence="check: " + NORESTART + "; delta(sysTester.UptimeS) > 65; " + SHA + ".", rationale=[("event comQueue.QueueOverflow count == 0", "as L5-17")])
t("L5-20", "Ground-system outage of 120 s", "Proves recovery within 10 s from a longer ground-system outage, without a restart of the flight software.", R(37), NOM,
  ["MARK(166)", "action: stop the whole ground stack (YAMCS server and `fprime-comm-bridge`)", "wait 120 s", "action: start the whole ground stack", "NO_OP()", "MARK(167)"], [W(166, 167)],
  metrics=[H("resume_after_action_within", "first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s", action="yamcs_ready", bound_s=10)],
  evidence="check: " + NORESTART + "; delta(sysTester.UptimeS) > 120.", rationale=[("event comQueue.QueueOverflow count == 0", "as L5-17")])
A, B, C = "A (48.1173 N, 11.5167 E)", "B (10.0000 N, 20.0000 E)", "C (48.2000 N, 11.6000 E)"
t("L5-21", "NMEA sentence with a bad checksum", "Proves a sentence with a bad checksum is discarded and the next good sentence is used.", R(25), NOM,
  ["MARK(170)", f"action: GPS source sends position {A} at 1 Hz for 5 s", f"action: GPS source sends position {B} with checksum + 1, at 1 Hz for 5 s", f"action: GPS source sends position {C} at 1 Hz for 5 s", "MARK(171)"], [W(170, 171)],
  evidence="check: latitude samples take the values of A then C and never B; source byte counter in bench-actions.log advanced by all 15 sentences; event sensorMonitor.GpsSilent count == 0.")
t("L5-22", "Bad checksums between good sentences", "Proves bad-checksum sentences interleaved with good ones never change the reported position.", R(25), NOM,
  ["MARK(172)", f"action: GPS source alternates position {A} (good) and position {B} (checksum + 1), 1 Hz each, for 10 s", f"action: GPS source sends position {C} at 1 Hz for 5 s", "MARK(173)"], [W(172, 173)],
  evidence="check: latitude samples take the values of A then C and never B; byte counter advanced by all 25 sentences; event sensorMonitor.GpsSilent count == 0.")
t("L6-1", "Corrupted uplink frame", "Proves an uplink frame that fails its frame check dispatches no command and an intact command still does.", R(27), NOM,
  ["MARK(180)", "action: inject one NO_OP frame with bit 0 of its last data byte flipped, at the bridge", "wait 5 s", "NO_OP()", "MARK(181)"], [W(180, 181)],
  evidence="check: event tcDeframer.InvalidCrc count == 1; event cmdDisp.NoOpReceived count == 1.")
t("L6-2", "Corrupted uplink frames, burst", "Proves five corrupted frames dispatch nothing and commanding works after them.", R(27), NOM,
  ["MARK(182)", "action: inject 5 NO_OP frames with the frame check field + 1, at the bridge", "wait 5 s", "NO_OP()", "MARK(183)"], [W(182, 183)],
  evidence="check: event tcDeframer.InvalidCrc count == 5; event cmdDisp.NoOpReceived count == 1.")

# ---- flight block (RFM69), last ----
t("L0-3", "Image and platform identity, flight image", "Proves the flight image is the manifest's and the marker round-trips over the RFM69.", R(42, 15),
  "action before the window: stop the prototype service unit, start the flight service unit. " + FLT,
  ["MARK(200)", "VERSION(ALL)", "PLATFORM()", "MARK(0x5A5A)", "bracket (2 Heartbeat samples)", "action: list TCP sockets of the deployment process", "MARK(201)"], [W(200, 201)],
  metrics=[H("clock_offset_within", "|time of the sysTester.Platform event - bench time of its reception| <= 0.5 s (require)", bound_s=0.5)],
  evidence="Version events equal the manifest describe strings of the flight image; Platform check as L0-1; marker ids byte-exact; socket list empty.")
t("L2-9", "Flight configuration: telemetry, capture, downlink", "Proves commands, telemetry, events and a CFDP file pass over the RFM69, with the 2 s period outside the downlink and the 10 s period during it.", R(15, 17, 1, 2, 3, 12, 13, 18), FLT,
  ["MARK(210)", "wait 30 s", "CAPTURE()", "DUMP_SHA256(P, 1)", "MARK(211)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "action: list TCP sockets of the deployment process", "MARK(212)"], [W(210, 211, "Q"), W(211, 212, "D")],
  metrics=[gap(2, "the first 30 s of Q"), gap(10, "D"), H("downlink_duration_at_least", "CFDP transaction duration in D >= 30 s", bound_s=30)], knobs=["corrupt_product"],
  evidence=SHA + "; class 2 check; socket list empty.",
  rationale=[("CFDP transaction duration in D >= 30 s", "a precondition (require): a downlink shorter than 30 s cannot show the 10 s bound")])
t("L2-10", "Flight configuration, repeated", "Proves a second capture and downlink pass over the RFM69 with telemetry continuing.", R(15, 17, 12, 13, 18), FLT,
  ["MARK(213)", "CAPTURE()", "DUMP_SHA256(P, 1)", "MARK(214)", "DOWNLINK(P)", "wait 15 s", "NO_OP()", "wait CFDP transaction finished at the ground", "action: list TCP sockets of the deployment process", "MARK(215)"], [W(213, 214, "Q"), W(214, 215, "D")],
  metrics=[gap(10, "D"), H("downlink_duration_at_least", "CFDP transaction duration in D >= 30 s", bound_s=30)],
  evidence=SHA + "; class 2 check; event cmdDisp.NoOpReceived count == 1 during the downlink; socket list empty.", rationale=[("CFDP transaction duration in D >= 30 s", "as L2-9")])
t("L5-16", "CFDP transfer cut mid-file", "Proves a transfer cut after it started ends with WARNING_HI and a repeated downlink delivers the product unchanged.", R(34, 35), FLT,
  ["MARK(220)", "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P)", "wait first file data PDU at the ground", "action: power off the ground radio", "wait 95 s", "action: power on the ground radio", "DUMP_SHA256(P, 2)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(221)"], [W(220, 221)],
  metrics=[H("stall_time_between", "55 s <= t(event productManager.DownlinkStalled) - bench time of the power-off action <= 90 s", lo_s=55, hi_s=90)],
  evidence="check: first transaction incomplete at the power-off (require); event productManager.DownlinkStalled count == 1; the two Sha256 events are equal; sha256 of record/raw/files/<P> == hash in the first Sha256 event.",
  rationale=[("event comQueue.QueueOverflow count == 0", "as L5-17")])
t("L5-23", "Link outage of 65 s, flight configuration", "Proves commanding and telemetry resume within 10 s of the end of a radio outage, without a restart.", R(36), FLT,
  ["MARK(222)", "action: power off the ground radio", "wait 65 s", "action: power on the ground radio", "NO_OP()", "MARK(223)"], [W(222, 223)],
  metrics=[H("ground_gap_at_least", "gap of ground reception of Table 1 channels during the outage >= 60 s", bound_s=60),
           H("resume_after_action_within", "first Table 1 sample received and NO_OP completion - bench time the ground radio is ready <= 10 s", action="radio_ready", bound_s=10)],
  evidence="check: " + NORESTART + "; delta(sysTester.UptimeS) > 65.", rationale=[("event comQueue.QueueOverflow count == 0", "as L5-17")])
t("L7-1", "Final state", "Leaves one known product on board for the independent final-state check.", R(13, 5), FLT,
  ["MARK(230)", "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "LIST_DIR(products)", "MARK(231)"], [W(230, 231)],
  evidence=SHA + "; " + REC + "; DirListing names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt.")

ids = [x["id"] for x in T]; assert len(ids) == len(set(ids))
cov = collections.defaultdict(list)
for x in T:
    for r in x["covers"]: cov[r].append(x["id"])
P = ("Component test (delegated: prodmgr)", "component row of a NEW element")
note = {11: P, 14: P, 30: P, 32: P, 33: P, 41: P,
        43: ("Component test (delegated: sensmon)", "component row of a NEW element"), 40: ("Inspection (delegated: picam)", "component row of a NEW element"),
        26: ("UT only", "decision D11: unit test for the unchanged catalog BMP280 manager, written in the base-deployment lane; a real BMP280 cannot return a wrong identity value")}
req = {}
for i in range(1, 44):
    k = R(i)[0]
    if i in note: req[k] = {"tests": [], "verification": note[i][0], "note": note[i][1]}
    else:
        assert len(cov[k]) >= 2, (k, cov[k]); req[k] = {"tests": cov[k], "verification": ", ".join(cov[k]), "note": ""}
STD = ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)", "event cmdDisp.OpCodeError count == 0",
       "event cmdDisp.TooManyCommands count == 0", "event comQueue.QueueOverflow count == 0",
       "Heartbeat samples >= 2"]
plan = {
 "name": "PiSensor system test plan",
 "markers": {"command": "sysTester.MARK", "event": "sysTester.Marker", "arg": "id", "reserved_min": 4294901760},
 "event_patterns": {"sysTester.Marker": "SystemTester marker (?P<id>\\d+)$"},
 "packets": {"Heartbeat": ["sysTester.UptimeS", "cmdDisp.CommandsDispatched"], "Table1": T1},
 "std_complete": STD,
 "abs": {"ABS": ["event productManager.CaptureFailed count == 0", "event productManager.StorageFailed count == 0", "event productManager.DownlinkStalled count == 0", "event sysTester.Started count == 0"],
         "STD-OUT": [p for p in STD if p != "event comQueue.QueueOverflow count == 0" and not isinstance(p, dict)],
         "STD-ERR": [("event cmdDisp.OpCodeError count == 1" if p == "event cmdDisp.OpCodeError count == 0" else p) for p in STD if not isinstance(p, dict)],
         "STD-RST": ["both markers present", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"]},
 "helpers_module": "planted_faults.py",
 "helpers": [{"instance": "sysTester", "component": "SystemTester", "src": "SystemTester", "repo": "https://github.com/lestarch-autobot/fprime-pi-sensor-reference"}],
 "uut": "PiSensor deployment (docs/ssdd.md)",
 "deployment": "PiSensor full system deployment plus the harness component sysTester; two images: prototype (TCP) and flight (RFM69)",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 75},
              "not_covered_ack": ["Error branches of inherited components that need a bus or driver fault not plantable on this bench: unit tests of the catalog cover them."],
              "rationale": "Baselines of the skill; thresholds apply to the three new components, whose campaigns report unit-test coverage. The coverage-dump component is in the development-campaign image only, never in the images of the run-for-record."},
 "image_version": {"policy": "required"},
 "final_state": {"accepted_evidence": "bench sha256sum of the L7-1 product file, taken over ssh after the run into record/raw/final-state.txt, compared by the auditor with the sha256 of the ground file in record/raw/files/",
                 "rationale": "The on-board hash command runs inside the UUT process; the bench reads the file itself, outside the UUT's reporting path."},
 "requirements": req,
 "scope": ["L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)` (the deployment has no command with a free 32-bit argument that echoes). Event rate: at most 5 events per second in any window. Link budget [I]: RFM69 at the catalog default `DATA_RATE` 19200 bit/s (`Rfm69Manager.fpp`) carries 2400 byte/s, about nine 255-byte frames; Table 1 telemetry at 1 Hz and 5 events/s are estimated at under 800 byte/s, leaving 1600 byte/s for CFDP, so a 100 kB JPEG takes at least 60 s. The bench check at L0 replaces this estimate.",
           "- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.",
           "- Test deployment (SSDD decision D13, the human's ruling): the full deployment plus the harness component `sysTester`. Constraint: without it there is no marker command, no on-board file hash, no directory listing outside `productManager` and no commandable bench line. Images named in the manifest `images[]`: `PiSensor-prototype` (TCP) and `PiSensor-flight` (RFM69).",
           "- `sysTester` commands: `MARK(id)`, `PLATFORM()`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `BENCH_LINE(line, state)`, `CORRUPT_PRODUCT(name)`. `DUMP_SHA256` and `CORRUPT_PRODUCT` act on a named file of the product directory only; `pass` is echoed in the `Sha256` event. Design constraint sent to campaign `prodmgr`: a downlink does not check product content, so a corrupted product is sent as stored. Events: `Marker`, `Started` (once per process start), `Platform`, `DirListing`, `Sha256`. Channel `UptimeS` every second (always written).",
           "- Ground system: fprime-yamcs at the ledger pin with the project YAMCS configuration directory (CFDP service).",
           "- Order: the prototype block (L0-1 to L6-2, TCP) runs first; the flight block (L0-3, L2-9, L2-10, L5-16, L5-23, L7-1, RFM69) runs last. The switch is the bench action at the head of L0-3.",
           "- Record content (`record/`): every exported row carries the ground reception time beside the FSW time; `record/raw/bench-actions.log` holds each bench action with its bench start and end time and, for the GPS source, its byte counter; every CFDP file received is copied to `record/raw/files/` before it is hashed; CFDP class and outcome come from the YAMCS transfer record exported to `record/raw/cfdp.json` and from the F Prime CFDP events; frames are recorded at `fprime-comm-bridge`, which stays up when YAMCS is stopped.",
           "- Completeness: every window requires STD and the helper `no_frame_gaps` (no gap in the telemetry frame counter of the ground recorder); a dropped frame or an overflowed queue makes the window UNVERIFIED, never a pass of an absence check. `STD-OUT`, `STD-ERR` and `STD-RST` are completeness blocks used with `require`, not absence blocks (the plan format lists them with the absence blocks). The helper takes `{except: [interval]}`: `STD-OUT` (link, radio and ground-stack outages) has no overflow predicate and exempts frame gaps from the outage action to the return action; `STD-RST` (restart windows) exempts them from the action to the first `sysTester.Started`, and a frame counter that restarts at 0 directly before a `Started` event is a restart, any other discontinuity a gap; `STD-ERR` expects exactly one failed command. Outside the exempt interval the gap rule holds; no absence is judged inside it.",
           "- Bench and Pi clocks: both synchronised by NTP; the offset is measured at L0-1 (`PLATFORM()` event time against bench time) and must be under 0.5 s; time tolerances that compare the two clocks use 2 s (SSDD decision D12).",
           "- Validity channels (`TemperatureValid`, `AttitudeValid`, `FixValid`) are written every period, not on change; a window without samples of them fails.",
           "- Out of scope: BMP280 pressure (decision D9); yaw."],
 "entry_gates": ["- Component campaigns `sensmon`, `picam`, `prodmgr` closed; their unit tests pass.",
                 "- Images built from the manifest SHAs; L0-1, L0-2 and L0-3 pass on the bench.",
                 "- Product directory on its own 64 MB file system (loop-mounted image file, kept across a reboot), empty at the start of each test (bench teardown removes the products of the test; L7-1 has no teardown, its product stays for the final-state check). The fill and read-only actions touch only that file system.",
                 "- Bench recipe: BMP280, MPU6050, Pi Camera attached; bench line BMP280 = a switch on the BMP280 supply driven by a Pi GPIO; bench line MPU6050 = the same on the MPU6050 supply, with SDA and SCL isolated by the same switch so the unpowered part does not load I2C bus 1 (L0 bench confirmation: the other sensors still answer with each line off); a GPS sentence source (workstation USB serial adapter on the GPS UART, 9600 baud, driven by a bench script) in place of the receiver for every test but L2-1 and L2-2; ground Pi with RFM69 for the flight block, its radio supply switchable from the workstation.",
                 "- Privileges on `soakee` (none today: user `fprime` has no passwordless sudo): root for the service units, the reboot, the loop mount and remount, and the camera driver unbind. The TCP link block and the YAMCS and CFDP service actions run on the workstation and need none."],
 "levels": ["L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L6 negative controls · L7 final state. No L4 endurance test: no requirement has an endurance bound."],
 "not_covered": ["- delegated: prodmgr — REQ-PiSensor-011, -014, -030, -032, -033, -041 (component rows of `productManager`).",
                 "- delegated: sensmon — REQ-PiSensor-043 (component row of `sensorMonitor`).",
                 "- delegated: picam — REQ-PiSensor-040 (inspection of the camera library).",
                 "- REQ-PiSensor-026: unit test only (decision D11).",
                 "- A sensor fault is planted by removing the sensor's supply or its sentence stream; a sensor that answers with wrong data is not planted.",
                 "- REQ-PiSensor-008 at its 2 s boundary: the tests use 3 s; a case just under 2 s is not run because the bench action timing error is of the size of the margin. The boundary is a unit test of `productManager`.",
                 "- REQ-PiSensor-037: L5-19 stops the YAMCS server only (requires STD; the flight software sees no outage, so it shows ground-side recovery only). L5-20 stops the bridge too; the flight software loses its TCP peer and must reconnect (requires STD-OUT).",
                 "- REQ-PiSensor-018 over TCP: a file finishes in about a second, so the bound is tested in the flight block only.",
                 "- Radio interference and range: the RFM69 link is tested at bench range only.",
                 "- Today's bench cannot run these tests: the BMP280 and GPS receiver do not answer (L2-1, L2-2 and every test whose setup needs four sensors), and the bench lines, the GPS sentence source, the camera, the ground Pi and root on `soakee` are absent."],
 "decision_log": ["1. 2026-11-17 designer — test deployment = full deployment + `sysTester`; proposed to the human as SSDD decision D13.",
                  "2. 2026-11-17 designer — product content and identity are judged on the ground copy of the file; `DUMP_SHA256` gives the on-board hash and the bench `sha256sum` the independent final state.",
                  "3. 2026-11-17 designer — GPS faults are planted with a bench sentence source in place of the receiver; the receiver itself is used in L2-1 and L2-2.",
                  "4. 2026-11-17 designer — corrupted uplink frames are injected at `fprime-comm-bridge` by a bench script; the intact command that follows is sent by the harness.",
                  "5. 2026-11-17 designer, review round 1 — a restart is judged by `sysTester.Started` and `UptimeS`, not by a clock epoch: the time source is the Pi system clock, which does not step back. All windows are `reset: false`.",
                  "6. 2026-11-17 designer, review round 1 — planted faults rewrite or insert commands only; bench actions that a fault must change are `sysTester.BENCH_LINE` commands. Tests whose fault stimulus is a bench script carry no planted fault.",
                  "7. 2026-11-17 designer, review round 1 — every test makes its own product; no test depends on a product of another test."],
 "tests": T,
}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
print(len(T), "tests")
