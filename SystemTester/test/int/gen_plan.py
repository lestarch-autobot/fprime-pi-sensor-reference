#!/usr/bin/env python3
"""Generates SystemTester/test/int/plan.json for the PiSensor system test plan (design phase)."""
import json, collections
R = lambda *n: [f"REQ-PiSensor-{i:03d}" for i in n]
W = lambda a, b, reset=False, name="W": {"name": name, "start_id": a, "end_id": b, "reset": reset}
T = []
def t(id, title, purpose, covers, setup, procedure, windows, metrics=(), knobs=(), evidence="", rationale=()):
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup,
              "procedure": list(procedure), "windows": windows, "metrics": list(metrics),
              "rationale": list(rationale), "knobs": list(knobs), "evidence": evidence})
NOM = "Deployment running, link up, all four sensors attached and answering."
t("L0-1", "Image identity", "Proves the running image is the one named in the manifest.", R(42), "Deployment running on the Raspberry Pi 5; link up.",
  ["MARK(10)", "VERSION(ALL)", "bracket (2 Sensors samples)", "MARK(11)"], [W(10, 11)],
  evidence="Version events equal to the manifest describe strings; board model and OS release in the run record.")
t("L0-2", "Marker round-trip", "Proves the marker command round-trips so every later window can be bracketed.", [], "As L0-1.",
  ["MARK(20)", "bracket (2 Sensors samples)", "MARK(0xA5A5)", "MARK(21)"], [W(20, 21)], evidence="Three Marker events in order.")
t("L2-1", "Sensor telemetry period", "Proves temperature, attitude and location telemetry each arrive at the ground at least every 2 s.", R(1, 2, 3, 16, 17, 42), NOM,
  ["MARK(30)", "wait 60 s", "MARK(31)"], [W(30, 31)],
  knobs=["period_window_cut"], evidence="Channel strips over 60 s; check: largest gap between ground receipt times of temperature, attitude and location samples <= 2 s.")
t("L2-2", "Sensor telemetry period, repeated after commanding", "Proves the 2 s telemetry period holds again after command traffic.", R(1, 2, 3, 16, 17), NOM,
  ["MARK(32)", "NO_OP()", "NO_OP()", "NO_OP()", "wait 30 s", "MARK(33)"], [W(32, 33)],
  evidence="Channel strips over 30 s; same 2 s gap check; three NoOpReceived events.")
t("L2-3", "Capture makes one correlated product", "Proves one capture command makes one product holding a JPEG of at least 640x480 and valid, timed metrics.", R(4, 5, 6, 7, 10), NOM,
  ["MARK(40)", "CAPTURE()", "bracket (2 Sensors samples)", "MARK(41)"], [W(40, 41)],
  metrics=["t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s"], knobs=["capture_twice"],
  evidence="ProductWritten event naming the file; product records read from the downlinked copy in L2-5.")
t("L2-4", "Second capture makes a second product", "Proves a later capture makes a new product with its own capture time and fresh metrics.", R(4, 5, 6, 7, 10), "As L2-3, one product stored.",
  ["MARK(42)", "CAPTURE()", "bracket (2 Sensors samples)", "MARK(43)"], [W(42, 43)],
  metrics=["t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s"],
  evidence="Second ProductWritten event with a different name; records read from the downlinked copy in L2-6.")
t("L2-5", "Downlink of the first product", "Proves a downlink command delivers the named product by CFDP class 2, byte-identical, to fprime-yamcs.", R(12, 13, 16, 17, 4, 5, 6, 7), "Product of L2-3 stored.",
  ["MARK(50)", "DOWNLINK(product of L2-3)", "wait CFDP transfer finished", "DUMP_SHA256(product of L2-3)", "MARK(51)"], [W(50, 51)],
  knobs=["downlink_other_product"], evidence="CFDP class 2 transaction finished at YAMCS; ground file sha256 equals the on-board sha256 event; product records decoded from the ground file.")
t("L2-6", "Downlink of the second product", "Proves a second downlink delivers the second product byte-identical.", R(12, 13, 16, 17, 4, 5, 6, 7), "Product of L2-4 stored.",
  ["MARK(52)", "DOWNLINK(product of L2-4)", "wait CFDP transfer finished", "DUMP_SHA256(product of L2-4)", "MARK(53)"], [W(52, 53)],
  evidence="As L2-5 for the second product.")
t("L2-7", "Telemetry during a downlink", "Proves sensor telemetry still arrives at least every 10 s while a product is downlinked.", R(18), "One product stored.",
  ["MARK(54)", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "MARK(55)"], [W(54, 55)],
  knobs=["period_window_cut"], evidence="Channel strips between the CFDP start and finish events; check: largest gap <= 10 s.")
t("L2-8", "Telemetry during a second downlink", "Proves the 10 s telemetry bound holds during a repeated downlink of a stored product.", R(18), "Product of L2-7 stored.",
  ["MARK(56)", "DOWNLINK(product of L2-7)", "wait CFDP transfer finished", "MARK(57)"], [W(56, 57)],
  evidence="As L2-7.")
t("L2-9", "Flight configuration over the RFM69", "Proves commands, telemetry, events and a CFDP file pass over the RFM69 with no TCP socket open on the Pi.", R(15, 17, 1, 2, 3, 12, 13), "Flight image running; ground Pi with RFM69 and groundRadio up.",
  ["MARK(60)", "NO_OP()", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "action: list TCP sockets of the deployment process", "MARK(61)"], [W(60, 61)],
  knobs=["downlink_other_product"], evidence="Command response, channel samples, events and file at the ground; socket list empty.")
t("L2-10", "Flight configuration, repeated", "Proves the RFM69 path carries a second command, telemetry and file exchange.", R(15, 17, 1, 2, 3, 12, 13), "As L2-9.",
  ["MARK(62)", "NO_OP()", "DOWNLINK(product of L2-9)", "wait CFDP transfer finished", "action: list TCP sockets of the deployment process", "MARK(63)"], [W(62, 63)],
  evidence="As L2-9.")
t("L3-1", "Process restart", "Proves sensor telemetry resumes within 60 s of a process restart without commands and a stored product is still downlinkable.", R(38, 39), "One product stored.",
  ["MARK(70)", "action: kill the deployment process", "wait telemetry", "MARK(71)", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(72)"],
  [W(70, 71, True, "R"), W(71, 72, False, "W2")],
  evidence="Clock restart; first Sensors sample within 60 s with no command before it; ground file sha256 equals the pre-restart sha256.")
t("L3-2", "Reboot", "Proves sensor telemetry resumes within 60 s of a reboot without commands and a stored product is still downlinkable.", R(38, 39), "One product stored.",
  ["MARK(73)", "action: reboot the Raspberry Pi", "wait telemetry", "MARK(74)", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(75)"],
  [W(73, 74, True, "R"), W(74, 75, False, "W2")], evidence="As L3-1 after a reboot.")
def sensor(idA, idB, m, name, reqA, chan, ev, action_off, action_on, knob):
    t(idA, f"{name} failure and return", f"Proves a failed {name} raises WARNING_HI within 10 s, its metric reads invalid, and telemetry resumes within 10 s of its return.", reqA, NOM,
      [f"MARK({m})", f"action: {action_off}", "wait 15 s", f"MARK({m+1})", f"action: {action_on}", "wait 15 s", f"MARK({m+2})"],
      [W(m, m+1, False, "F"), W(m+1, m+2, False, "B")], knobs=[knob],
      evidence=f"{ev} event within 10 s of the action; {chan} invalid in F, valid within 10 s in B; no clock restart.")
    t(idB, f"{name} failure and return, repeated", f"Proves the {name} loss report and recovery repeat on a second failure.", reqA, NOM,
      [f"MARK({m+3})", f"action: {action_off}", "wait 15 s", f"MARK({m+4})", f"action: {action_on}", "wait 15 s", f"MARK({m+5})"],
      [W(m+3, m+4, False, "F"), W(m+4, m+5, False, "B")], evidence=f"As {idA}.")
sensor("L5-1", "L5-2", 100, "BMP280", R(19, 22, 23), "sensorMonitor.TemperatureValid", "sensorMonitor.Bmp280Lost", "hold the BMP280 chip select inactive (bench switch)", "release the BMP280 chip select", "skip_sensor_off")
sensor("L5-3", "L5-4", 110, "MPU6050", R(20, 22, 23), "sensorMonitor.AttitudeValid", "sensorMonitor.Mpu6050Lost", "disconnect the MPU6050 from the I2C bus (bench switch)", "reconnect the MPU6050", "skip_sensor_off")
sensor("L5-5", "L5-6", 120, "GPS", R(21, 22, 23), "sensorMonitor.LocationValid", "sensorMonitor.GpsSilent", "stop the GPS sentence source", "restart the GPS sentence source", "skip_sensor_off")
t("L5-7", "GPS without a fix", "Proves a receiver reporting no fix reads fix invalid in telemetry and location invalid in a captured product.", R(24, 9), "GPS sentence source set to no fix.",
  ["MARK(130)", "action: GPS source sends no-fix sentences", "wait 10 s", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "action: GPS source sends fix sentences", "MARK(131)"], [W(130, 131)],
  knobs=["gps_keep_fix"], evidence="FixValid channel invalid with no GpsSilent event; location validity record invalid in the ground file.")
t("L5-8", "GPS without a fix, repeated", "Proves the no-fix indication repeats and clears when the fix returns.", R(24, 9), "As L5-7.",
  ["MARK(132)", "action: GPS source sends no-fix sentences", "wait 10 s", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "action: GPS source sends fix sentences", "wait 10 s", "MARK(133)"], [W(132, 133)],
  evidence="As L5-7; FixValid valid again at the end.")
t("L5-9", "Stale metric at capture", "Proves a metric older than 2 s at capture is marked invalid in the product while the others stay valid.", R(8), NOM,
  ["MARK(134)", "action: disconnect the MPU6050 from the I2C bus (bench switch)", "wait 5 s", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "action: reconnect the MPU6050", "MARK(135)"], [W(134, 135)],
  knobs=["skip_sensor_off"], evidence="Attitude validity record invalid, temperature and location valid, in the ground file.")
t("L5-10", "Stale location at capture", "Proves a location older than 2 s at capture is marked invalid in the product.", R(8), NOM,
  ["MARK(136)", "action: stop the GPS sentence source", "wait 5 s", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "action: restart the GPS sentence source", "MARK(137)"], [W(136, 137)],
  evidence="Location validity record invalid, temperature and attitude valid, in the ground file.")
t("L5-11", "Camera absent", "Proves a capture with the camera unavailable fails its command with WARNING_HI and leaves no product.", R(28, 29), "Camera made unavailable to the process.",
  ["MARK(140)", "action: make the camera unavailable", "LIST_PRODUCTS()", "CAPTURE()", "LIST_PRODUCTS()", "action: make the camera available", "MARK(141)"], [W(140, 141)],
  knobs=["camera_left_on"], evidence="CAPTURE completes with error; CaptureFailed WARNING_HI; product count unchanged between the two lists.")
t("L5-12", "Camera absent, repeated", "Proves a second failed capture also leaves no product and a later capture succeeds.", R(28, 29), "As L5-11.",
  ["MARK(142)", "action: make the camera unavailable", "LIST_PRODUCTS()", "CAPTURE()", "LIST_PRODUCTS()", "action: make the camera available", "CAPTURE()", "MARK(143)"], [W(142, 143)],
  evidence="As L5-11, then one ProductWritten event.")
t("L5-13", "Storage unavailable", "Proves a capture that cannot store its product fails its command with WARNING_HI and leaves no product.", R(31, 29), "Product directory made read-only.",
  ["MARK(144)", "action: make the product directory read-only", "CAPTURE()", "action: make the product directory writable", "LIST_PRODUCTS()", "MARK(145)"], [W(144, 145)],
  knobs=["storage_left_writable"], evidence="CAPTURE completes with error; StorageFailed WARNING_HI; product count unchanged.")
t("L5-14", "Storage full", "Proves a capture with no free space fails its command with WARNING_HI and leaves no partial file.", R(31, 29), "Product file system filled by a bench file.",
  ["MARK(146)", "action: fill the product file system", "CAPTURE()", "action: remove the fill file", "LIST_PRODUCTS()", "MARK(147)"], [W(146, 147)],
  evidence="As L5-13; directory listing by the bench shows no partial file.")
t("L5-15", "CFDP transfer without progress", "Proves a transfer with no progress for 60 s ends with WARNING_HI and the product can be downlinked again intact.", R(34, 35, 38), "One product stored.",
  ["MARK(150)", "DOWNLINK(stored product)", "action: stop the ground CFDP service", "wait 75 s", "action: start the ground CFDP service", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(151)"], [W(150, 151)],
  metrics=["t(event productManager.DownlinkStalled) - t(productManager.DOWNLINK sent) <= 90 s"], knobs=["cfdp_left_running"],
  evidence="DownlinkStalled WARNING_HI; second transfer finished; ground file sha256 equals the on-board sha256.")
t("L5-16", "CFDP transfer cut mid-file", "Proves a transfer cut after it started ends with WARNING_HI and a repeated downlink delivers the product intact.", R(34, 35, 38), "One product stored.",
  ["MARK(152)", "DOWNLINK(stored product)", "wait first file data at the ground", "action: block the link", "wait 75 s", "action: unblock the link", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(153)"], [W(152, 153)],
  evidence="As L5-15.")
t("L5-17", "Link outage", "Proves commanding and telemetry resume within 10 s of the end of a 60 s link outage, without a restart.", R(36, 38), "One product stored.",
  ["MARK(160)", "action: block the link", "wait 65 s", "action: unblock the link", "NO_OP()", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(161)"], [W(160, 161)],
  knobs=["outage_skipped"], evidence="Telemetry gap of at least 60 s; first sample and NO_OP response within 10 s of the unblock action; no clock restart; file delivered.")
t("L5-18", "Link outage, repeated", "Proves recovery from a second 60 s link outage.", R(36, 38), "As L5-17.",
  ["MARK(162)", "action: block the link", "wait 65 s", "action: unblock the link", "NO_OP()", "MARK(163)"], [W(162, 163)], evidence="As L5-17 without the file.")
t("L5-19", "Ground-system outage", "Proves commanding and telemetry resume within 10 s of the ground system's return after 60 s, without a restart of the flight software.", R(37, 38), "One product stored.",
  ["MARK(164)", "action: stop fprime-yamcs", "wait 65 s", "action: start fprime-yamcs", "NO_OP()", "DOWNLINK(stored product)", "wait CFDP transfer finished", "MARK(165)"], [W(164, 165)],
  knobs=["outage_skipped"], evidence="As L5-17 with the ground system stopped; flight clock does not restart.")
t("L5-20", "Ground-system outage, repeated", "Proves recovery from a second ground-system outage.", R(37, 38), "As L5-19.",
  ["MARK(166)", "action: stop fprime-yamcs", "wait 65 s", "action: start fprime-yamcs", "NO_OP()", "MARK(167)"], [W(166, 167)], evidence="As L5-19 without the file.")
t("L5-21", "NMEA sentence with a bad checksum", "Proves a sentence with a bad checksum and a new position is discarded and the next good sentence is used.", R(25), "GPS sentence source under bench control.",
  ["MARK(170)", "action: GPS source sends position A", "wait 4 s", "action: GPS source sends position B with a bad checksum", "wait 4 s", "action: GPS source sends position C", "wait 4 s", "MARK(171)"], [W(170, 171)],
  knobs=["gps_good_checksum"], evidence="Latitude strip shows A then C, never B.")
t("L5-22", "NMEA sentences with bad checksums, burst", "Proves a burst of bad-checksum sentences leaves the reported position unchanged.", R(25), "As L5-21.",
  ["MARK(172)", "action: GPS source sends position A", "wait 4 s", "action: GPS source sends 10 sentences of position B with bad checksums", "wait 4 s", "MARK(173)"], [W(172, 173)],
  evidence="Latitude strip stays at A.")
t("L6-1", "Corrupted uplink frame", "Proves an uplink frame that fails its integrity check dispatches no command and the same frame uncorrupted does.", R(27), NOM,
  ["MARK(180)", "action: inject a NO_OP frame with one bit flipped", "wait 5 s", "action: inject the same NO_OP frame intact", "MARK(181)"], [W(180, 181)],
  knobs=["frame_not_corrupted"], evidence="Exactly one NoOpReceived event, after the intact frame.")
t("L6-2", "Corrupted uplink frames, burst", "Proves several corrupted frames dispatch nothing and commanding still works after them.", R(27), NOM,
  ["MARK(182)", "action: inject 5 NO_OP frames with a wrong frame check field", "wait 5 s", "NO_OP()", "MARK(183)"], [W(182, 183)],
  evidence="Exactly one NoOpReceived event, from the planned command.")
t("L7-1", "Final state", "Leaves one known product on board whose ground copy and on-board hash an auditor can compare.", R(13, 5), NOM,
  ["MARK(190)", "CAPTURE()", "DOWNLINK(new product)", "wait CFDP transfer finished", "DUMP_SHA256(new product)", "LIST_PRODUCTS()", "MARK(191)"], [W(190, 191)],
  evidence="Ground file kept in the record; on-board sha256 event; product list.")
ids = [x["id"] for x in T]; assert len(ids) == len(set(ids)) and all(len(i) <= 8 for i in ids)
cov = collections.defaultdict(list)
for x in T:
    for r in x["covers"]: cov[r].append(x["id"])
req = {}
note = {
 11: ("Component test (delegated: prodmgr)", "component row of a NEW element"), 14: ("Component test (delegated: prodmgr)", "component row of a NEW element"),
 30: ("Component test (delegated: prodmgr)", "component row of a NEW element"), 32: ("Component test (delegated: prodmgr)", "component row of a NEW element"),
 33: ("Component test (delegated: prodmgr)", "component row of a NEW element"), 41: ("Component test (delegated: prodmgr)", "component row of a NEW element"),
 43: ("Component test (delegated: sensmon)", "component row of a NEW element"), 40: ("Inspection (delegated: picam)", "component row of a NEW element"),
 26: ("UT only", "decision D11: unit test for the unchanged catalog BMP280 manager, written in the base-deployment lane; a real BMP280 cannot return a wrong identity value"),
}
for i in range(1, 44):
    k = R(i)[0]
    if i in note: req[k] = {"tests": [], "verification": note[i][0], "note": note[i][1]}
    else:
        assert len(cov[k]) >= 2, (k, cov[k]); req[k] = {"tests": cov[k], "verification": ", ".join(cov[k]), "note": ""}
plan = {
 "name": "PiSensor system test plan",
 "markers": {"command": "sysTester.MARK", "event": "sysTester.Marker", "arg": "id", "reserved_min": 4294901760},
 "event_patterns": {"sysTester.Marker": "SystemTester marker (?P<id>\\d+)$"},
 "packets": {"Sensors": ["sensorMonitor.Temperature", "sensorMonitor.Roll", "sensorMonitor.Pitch", "sensorMonitor.Latitude", "sensorMonitor.Longitude"]},
 "std_complete": ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)", "event cmdDisp.OpCodeError count == 0", "Sensors samples >= 2"],
 "abs": {"ABS": ["event productManager.CaptureFailed count == 0", "event productManager.StorageFailed count == 0", "event productManager.DownlinkStalled count == 0"]},
 "helpers_module": "planted_faults.py",
 "helpers": [{"instance": "sysTester", "component": "SystemTester", "src": "SystemTester", "repo": "https://github.com/lestarch-autobot/fprime-pi-sensor-reference"}],
 "uut": "PiSensor deployment (docs/ssdd.md)",
 "deployment": "PiSensor, the project's full system deployment, with the harness component sysTester and the coverage-dump component",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 75},
              "not_covered_ack": ["Error branches of inherited components that need a bus or driver fault not plantable on this bench: unit tests of the catalog cover them."],
              "rationale": "Baselines of the skill; thresholds apply to the three new components, whose campaigns report unit-test coverage."},
 "reboot_min_backstep_s": 1,
 "image_version": {"policy": "required"},
 "requirements": req,
 "scope": ["L0: desk-checked; bench confirmation pending (marker `sysTester.MARK(U32)`; event rate at most 5 per second against a 255-byte RFM69 frame).", "- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.",
           "- Ground system: fprime-yamcs at the ledger pin, with the project YAMCS configuration directory (CFDP service).",
           "- Prototype configuration (TCP through `fprime-comm-bridge`) for every test except L2-9 and L2-10, which run the flight configuration over the RFM69.",
           "- Out of scope: BMP280 pressure (decision D9); yaw."],
 "entry_gates": ["- Component campaigns `sensmon`, `picam`, `prodmgr` closed; their unit tests pass.",
                 "- Images built from the manifest SHAs; L0-1 and L0-2 pass on the bench.",
                 "- Event rate fits the downlink: at most 5 events per second in any window.",
                 "- Bench recipe: BMP280, MPU6050, GPS sentence source and Pi Camera attached; bench switches for the BMP280 chip select and the MPU6050 bus; ground Pi with RFM69 for L2-9 and L2-10."],
 "levels": ["L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L6 negative controls · L7 final state. No L4 endurance test: no requirement has an endurance bound."],
 "not_covered": ["- delegated: prodmgr — REQ-PiSensor-011, -014, -030, -032, -033, -041 (component rows of `productManager`).",
                 "- delegated: sensmon — REQ-PiSensor-043 (component row of `sensorMonitor`).",
                 "- delegated: picam — REQ-PiSensor-040 (inspection of the camera library).",
                 "- REQ-PiSensor-026: unit test only (decision D11).",
                 "- A sensor fault is planted by removing the device from its bus; a device that answers with wrong data is not planted (out-of-range data is waived in the requirements rationale).",
                 "- Radio interference and range: the RFM69 link is tested on the bench at short range only.",
                 "- The BMP280 and the GPS receiver do not answer on the bench yet; L2-1, L2-2, L5-1, L5-2, L5-5 to L5-10, L5-21, L5-22 cannot run until they are wired."],
 "decision_log": ["1. 2026-11-17 designer — deployment = the project's full system deployment plus the harness component `sysTester` (`MARK(U32)`) and the coverage-dump component.",
                  "2. 2026-11-17 designer — product content is judged on the ground copy of the file (evidence outside the UUT's own reporting path); `DUMP_SHA256` is a `sysTester` command that hashes the on-board file.",
                  "3. 2026-11-17 designer — GPS faults are planted with a bench sentence source on the GPS UART in place of the receiver; the receiver itself is used in L2-1 and L2-2.",
                  "4. 2026-11-17 designer — corrupted uplink frames are injected at the ground side of the link by a bench script, not by fprime-yamcs."],
 "tests": T,
}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
print(len(T), "tests")
