#!/usr/bin/env python3
"""Generates plan.json for the PiSensor system test plan (design phase). Run from this directory."""
import json, collections
R = lambda *n: [f"REQ-PiSensor-{i:03d}" for i in n]
def W(a, b, name="W"): return {"name": name, "start_id": a, "end_id": b, "reset": False}
def H(name, text, **args): return {"helper": name, "text": text, "args": args}
SENS = ["bmpManager.Reading", "imuManager.Reading", "gpsManager.Reading"]
def gap(bound, where="the window", n=30): return H("max_ground_gap", f"for every sensor channel in {where}: samples >= {n}, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= {bound} s", channels="Sensors", bound_s=bound, min_samples=n)
T = []
def t(id, title, purpose, covers, procedure, windows, metrics=(), knobs=(), evidence="", rationale=(), setup=None):
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup or NOM,
              "procedure": list(procedure), "windows": windows, "metrics": list(metrics),
              "rationale": [{"pred": p, "text": x} for p, x in rationale], "knobs": list(knobs), "evidence": evidence})
NOM = "Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty."
CAP30 = H("event_after_command_within", "t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock)", command="piCamera.CAPTURE", event="dpWriter.FileWritten", bound_s=30)
CRC = "check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P"
REC = ("checks on the ground file: it parses as an F Prime data product container; the picture record starts FFD8 and ends FFD9, SOF0 width >= 640 and height >= 480; "
       "one latitude, one longitude, one roll, one pitch and one temperature record")
TIMES = [H("product_time_within", "bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s", tol_s=2),
         H("product_sample_times_within", "the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each", bound_s=2)]
XMIT = ["dpCat.BUILD_CATALOG()", "dpCat.START_XMIT_CATALOG(NO_WAIT)", "wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground"]
CLS2 = "check: every CFDP transaction in the window is class 2 and finished complete at the ground"
PLAT = "action: read /proc/device-tree/model, /etc/os-release and `getconf LONG_BIT` on the Pi over ssh into bench-actions.log"

t("L0-1", "Image and platform identity", "Proves the running image is the manifest's image and runs on a Raspberry Pi 5 under 64-bit Raspberry Pi OS, reached over the RFM69.", R(13, 10),
  ["MARK(10)", "version.VERSION(ALL)", PLAT, "bracket (2 Heartbeat samples)", "action: list TCP sockets of the deployment process", "MARK(11)"], [W(10, 11)],
  metrics=[H("clock_offset_within", "|Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)", bound_s=0.5)],
  evidence="Version events equal the manifest describe strings; check: model starts with \"Raspberry Pi 5\", os-release ID is the Raspberry Pi OS (Debian) release of the manifest, LONG_BIT == 64; socket list empty; check: the dictionary of the image holds no command of a test component.",
  setup="Deployment running on the Raspberry Pi 5; RFM69 link up.")
t("L0-2", "Marker round-trip", "Proves the marker command round-trips over the RFM69 on the Raspberry Pi 5 so every later window can be bracketed.", R(13, 10),
  ["MARK(20)", "bracket (2 Heartbeat samples)", "MARK(42405)", PLAT, "MARK(21)"], [W(20, 21)],
  evidence="Three NoOpStringReceived events in order, strings byte-exact; platform check as L0-1.", setup="As L0-1.")
t("L2-1", "Sensor telemetry period", "Proves every sensor channel arrives at the ground at least every 2 s.", R(1, 2, 3, 10, 11),
  ["MARK(30)", "wait 60 s", "MARK(31)"], [W(30, 31)], metrics=[gap(2)],
  evidence="Channel strips over 60 s; check: bmpManager.Reading temperature between -20 and 60 degC; imuManager.Reading acceleration magnitude between 8 and 12 m/s^2 and angular rate magnitude <= 0.5 rad/s (bench at rest; MPU6050 datasheet zero-rate offset 20 deg/s); gpsManager.Reading within 1 km of the bench position in the manifest.")
t("L2-2", "Sensor telemetry period under command traffic", "Proves the 2 s telemetry period holds while commands are dispatched.", R(1, 2, 3, 10, 11),
  ["MARK(32)", "cmdDisp.CMD_NO_OP()", "wait 10 s", "cmdDisp.CMD_NO_OP()", "wait 10 s", "cmdDisp.CMD_NO_OP()", "wait 10 s", "MARK(33)"], [W(32, 33)], metrics=[gap(2)],
  knobs=["extra_noop"], evidence="As L2-1; check: event cmdDisp.NoOpReceived count == 3.")
t("L2-3", "Capture and downlink of one product", "Proves one capture stores one product with a JPEG of at least 640x480, the metrics and their times, sampled within 2 s of the capture, delivered byte-identical by CFDP class 2.", R(4, 5, 6, 7, 8, 9, 11, 14),
  ["MARK(40)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P)", "fileManager.CalculateCrc(P)"] + XMIT + ["MARK(41)"], [W(40, 41)],
  metrics=[CAP30] + TIMES, knobs=["capture_before_xmit"],
  evidence="check: event dpWriter.FileWritten count == 1; check: exactly one file arrived; " + CRC + "; " + CLS2 + "; " + REC + ".")
t("L2-4", "Two captures, one catalog downlink", "Proves a second capture stores a second product with its own capture time and the catalog downlinks both, byte-identical.", R(4, 5, 6, 7, 8, 9, 14),
  ["MARK(42)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P1)", "wait 5 s", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P2)", "fileManager.CalculateCrc(P1)", "fileManager.CalculateCrc(P2)"] + XMIT + ["MARK(43)"], [W(42, 43)],
  metrics=[CAP30] + TIMES, knobs=["capture_before_xmit"],
  evidence="check: event dpWriter.FileWritten count == 2 with different names; capture time of P2 later than that of P1; check: exactly two files arrived; " + CRC.replace("<P>", "<P1> and <P2>") + "; " + CLS2 + "; " + REC + ".")
t("L2-5", "Product content against the telemetry", "Proves the metrics stored in a product are the sensor readings downlinked around its capture.", R(5, 6, 14),
  ["MARK(44)", "wait 10 s", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P)", "wait 10 s"] + XMIT + ["MARK(45)"], [W(44, 45)],
  metrics=TIMES,
  evidence=REC + "; check: the temperature record equals a bmpManager.Reading sample of the window; the latitude and longitude records equal a gpsManager.Reading sample of the window; roll and pitch equal, within 0.1 deg, the bench computation from the acceleration of an imuManager.Reading sample of the window.")
t("L2-6", "Capture time bound, repeated", "Proves three captures in a row each store their product within 30 s.", R(4, 7),
  ["MARK(46)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten", "MARK(47)"], [W(46, 47)],
  metrics=[CAP30], evidence="check: event dpWriter.FileWritten count == 3.")
t("L2-7", "Telemetry during a downlink", "Proves sensor telemetry continues at least every 10 s while products are downlinked over the RFM69.", R(12, 8, 9, 10, 11),
  ["MARK(50)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P)", "fileManager.CalculateCrc(P)", "MARK(51)"] + XMIT + ["MARK(52)"], [W(50, 51, "Q"), W(51, 52, "D")],
  metrics=[gap(10, "D", 3), H("downlink_duration_at_least", "CFDP transaction duration in D >= 30 s", bound_s=30)], knobs=["capture_before_xmit"],
  evidence="check: event dpWriter.FileWritten count == 1; check: exactly one file arrived; check: rfm69Manager.PacketsTransmitted and rfm69Manager.PacketsReceived each rise in D; " + CRC + "; " + CLS2 + ".",
  rationale=[("CFDP transaction duration in D >= 30 s", "a precondition (require): a downlink shorter than 30 s cannot show the 10 s bound")])
t("L2-8", "Telemetry and commands during a downlink", "Proves sensor telemetry continues and a command is served while two products are downlinked.", R(12, 10),
  ["MARK(53)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten", "MARK(54)", "dpCat.BUILD_CATALOG()", "dpCat.START_XMIT_CATALOG(NO_WAIT)", "wait 15 s", "cmdDisp.CMD_NO_OP()", "wait event dpCat.CatalogXmitCompleted and both CFDP transactions finished at the ground", "MARK(55)"], [W(53, 54, "Q"), W(54, 55, "D")],
  metrics=[gap(10, "D", 3), H("downlink_duration_at_least", "CFDP transaction duration in D >= 30 s", bound_s=30)],
  knobs=["extra_noop"], evidence="check: event cmdDisp.NoOpReceived count == 1 during the downlink; check: exactly two files arrived; " + CLS2 + ".", rationale=[("CFDP transaction duration in D >= 30 s", "as L2-7")])
t("L7-1", "Final state", "Leaves one known product on board for the independent final-state check.", R(9, 5),
  ["MARK(60)", "cfdpManager.FileInDefaultKeep_PRM_SET(KEEP)", "piCamera.CAPTURE()", "wait event dpWriter.FileWritten (names P)", "fileManager.CalculateCrc(P)"] + XMIT + ["fileManager.ListDirectory(product directory)", "MARK(61)"], [W(60, 61)],
  evidence=CRC + "; " + REC + "; the directory listing names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt.")

ids = [x["id"] for x in T]; assert len(ids) == len(set(ids))
cov = collections.defaultdict(list)
for x in T:
    for r in x["covers"]: cov[r].append(x["id"])
req = {}
for i in range(1, 15):
    k = R(i)[0]
    assert len(cov[k]) >= 2, (k, cov[k]); req[k] = {"tests": cov[k], "verification": ", ".join(cov[k]), "note": ""}
STD = ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)", "event cmdDisp.OpCodeError count == 0",
       "event cmdDisp.TooManyCommands count == 0", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"]
plan = {
 "name": "PiSensor system test plan",
 "markers": {"command": "cmdDisp.CMD_NO_OP_STRING", "event": "cmdDisp.NoOpStringReceived", "arg": "arg1", "reserved_min": 4294901760},
 "event_patterns": {"cmdDisp.NoOpStringReceived": "Received a NO-OP string=(?P<arg1>\\d+)$"},
 "packets": {"Heartbeat": ["imuManager.Reading"], "Sensors": SENS},
 "std_complete": STD,
 "abs": {"ABS": ["event piCamera.CaptureFailed count == 0", "severity FATAL count == 0"]},
 "helpers_module": "planted_faults.py",
 "helpers": [],
 "uut": "PiSensor deployment (docs/ssdd.md)",
 "deployment": "PiSensor full system deployment, as flown: no test component",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 75},
              "not_covered_ack": ["Error branches of inherited components that need a bus or driver fault not plantable on this bench: unit tests of the catalog cover them."],
              "rationale": "Baselines of the skill; thresholds apply to the new component piCamera, whose campaign reports unit-test coverage."},
 "image_version": {"policy": "required"},
 "final_state": {"accepted_evidence": "bench sha256sum of the L7-1 product file, taken over ssh after the run into record/raw/final-state.txt, compared by the auditor with the sha256 of the ground file in record/raw/files/",
                 "rationale": "The on-board CRC command runs inside the UUT process; the bench reads the file itself, outside the UUT's reporting path."},
 "requirements": req,
 "scope": ["L0: desk-checked; bench confirmation pending. Marker: `cmdDisp.CMD_NO_OP_STRING(arg1)` -> event `cmdDisp.NoOpStringReceived`, the id sent as a decimal string. Link budget [I]: RFM69 at the catalog default data rate 19200 bit/s carries about 2400 byte/s; sensor telemetry at 1 Hz leaves the rest to CFDP, so a 100 kB product takes on the order of a minute.",
           "- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS.",
           "- Test deployment: the deployment itself. No component is added for testing. Markers use `cmdDisp`, the on-board file check uses `fileManager.CalculateCrc`, the directory listing uses `fileManager.ListDirectory`, product names come from `dpWriter.FileWritten`, platform identity is a bench action over ssh.",
           "- Ground system: fprime-yamcs at the ledger pin with the project YAMCS configuration directory (CFDP service), joined to the radio by the RFM69 Feather ground station on USB serial.",
           "- Record content (`record/`): every exported row carries the ground reception time beside the FSW time; `record/raw/bench-actions.log` holds each bench action with its bench start and end time; every CFDP file received is copied to `record/raw/files/` before it is checked; CFDP class and outcome come from the YAMCS transfer record exported to `record/raw/cfdp.json`.",
           "- Completeness: every window requires STD; an overflowed queue makes the window UNVERIFIED, never a pass of an absence check.",
           "- Bench and Pi clocks: both synchronised by NTP; the offset is measured at L0-1 and must be under 0.5 s; tolerances that compare the two clocks use 2 s.",
           "- Heartbeat: `imuManager.Reading`, written to the telemetry packet every 1 Hz cycle; `cmdDisp.CommandsDispatched` updates on change only.",
           "- Telemetry gaps are judged on ground reception time: the requirement is stated at the ground. Telemetry is sent at 1 Hz, so the 2 s bound leaves one period of margin for radio delay.",
           "- A CAPTURE that fails makes its window UNVERIFIED through STD (`OpCodeError`), not FAIL: the run is then repeated after the cause is found.",
           "- CFDP as shipped deletes a file after sending it (`cfdpManager.FileInDefaultKeep`, default DELETE): the on-board CRC is taken before the downlink, and L7-1 sets KEEP.",
           "- Constants: temperature -20 to 60 degC and gravity 8 to 12 m/s^2 are plausibility bounds for an indoor bench at rest; 1 km is the GPS plausibility bound around the surveyed bench position; 0.1 deg is the rounding allowance of the roll and pitch computation; the 30 s downlink precondition is three times the 10 s bound; the file CRC is that of `Os::File::calculateCrc`; the product directory is `DataProductsConfig.Paths.dpDir`.",
           "- Out of scope: BMP280 pressure; yaw."],
 "entry_gates": ["- Component campaign `picam` closed; its unit tests pass.",
                 "- Image built from the manifest SHAs; L0-1 and L0-2 pass on the bench.",
                 "- Product directory empty at the start of each test (bench teardown removes the products of the test over ssh; L7-1 has no teardown).",
                 "- Bench recipe: BMP280, MPU6050, GPS receiver with a fix and Pi Camera attached to the Pi 5; Feather M0 RFM69HCW ground station on the ground host USB."],
 "levels": ["L0 provenance and feasibility · L2 functional · L7 final state. No L3, L4, L5 or L6 test: no system requirement states restart, endurance, fault or rejection behaviour; those belong to the components."],
 "not_covered": ["- Fault, warning and rejection behaviour of `piCamera`: its component campaign.",
                 "- Fault and warning behaviour of inherited components: not required at system level; their own tests, where they exist, cover it.",
                 "- CFDP uplink, packet loss and retransmission: no system requirement.",
                 "- Radio interference and range: the RFM69 link is tested at bench range only.",
                 "- Today's bench cannot run these tests: the BMP280 and GPS receiver do not answer, and the camera and the Feather ground station are absent."],
 "decision_log": ["1. 2026-11-18 designer — test deployment = the deployment as flown; no test component (human direction).",
                  "2. 2026-11-18 designer — product content is judged on the ground copy of the file; `fileManager.CalculateCrc` gives the on-board check and the bench `sha256sum` the independent final state.",
                  "3. 2026-11-18 designer — planted faults insert commands of existing components only; a grown or altered product file is not usable as a fault because `Svc.DpCatalog` refuses it (size check).",
                  "4. 2026-11-18 designer — every test makes its own product; no test depends on a product of another test."],
 "tests": T,
}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
print(len(T), "tests")
