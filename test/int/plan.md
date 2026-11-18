# PiSensor system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker: `cmdDisp.CMD_NO_OP_STRING(arg1)` -> event `cmdDisp.NoOpStringReceived`, the id sent as a decimal string. Link budget [I]: RFM69 at the catalog default data rate 19200 bit/s carries about 2400 byte/s; sensor telemetry at 1 Hz leaves the rest to CFDP, so a 100 kB product takes on the order of a minute.
- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS.
- Test deployment: the deployment itself. No component is added for testing. Markers use `cmdDisp`, the on-board file check uses `fileManager.CalculateCrc`, the directory listing uses `fileManager.ListDirectory`, product names come from `dpWriter.FileWritten`, platform identity is a bench action over ssh.
- Ground system: fprime-yamcs at the ledger pin with the project YAMCS configuration directory (CFDP service), joined to the radio by the RFM69 Feather ground station on USB serial.
- Record content (`record/`): every exported row carries the ground reception time beside the FSW time; `record/raw/bench-actions.log` holds each bench action with its bench start and end time; every CFDP file received is copied to `record/raw/files/` before it is checked; CFDP class and outcome come from the YAMCS transfer record exported to `record/raw/cfdp.json`.
- Completeness: every window requires STD; an overflowed queue makes the window UNVERIFIED, never a pass of an absence check.
- Bench and Pi clocks: both synchronised by NTP; the offset is measured at L0-1 and must be under 0.5 s; tolerances that compare the two clocks use 2 s.
- Out of scope: BMP280 pressure; yaw.

## 1 Entry gates
- Component campaign `picam` closed; its unit tests pass.
- Image built from the manifest SHAs; L0-1 and L0-2 pass on the bench.
- Product directory empty at the start of each test (bench teardown removes the products of the test over ssh; L7-1 has no teardown).
- Bench recipe: BMP280, MPU6050, GPS receiver with a fix and Pi Camera attached to the Pi 5; Feather M0 RFM69HCW ground station on the ground host USB.

## 2 Test levels
L0 provenance and feasibility · L2 functional · L7 final state. No L3, L4, L5 or L6 test: no system requirement states restart, endurance, fault or rejection behaviour; those belong to the components.

## 3 Test entries

Window rule: rows from the **last** `cmdDisp.NoOpStringReceived(id=START)` row that precedes the first `cmdDisp.NoOpStringReceived(id=END)` row following it, through that END row plus the END `cmdDisp.CMD_NO_OP_STRING` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event piCamera.CaptureFailed count == 0; severity FATAL count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = cmdDisp.CommandsDispatched; Sensors = bmpManager.Reading, imuManager.Reading, gpsManager.Reading.

ID:        L0-1
Title:     Image and platform identity
Purpose:   Proves the running image is the manifest's image and runs on a Raspberry Pi 5 under 64-bit Raspberry Pi OS, reached over the RFM69.
Covers:    REQ-PiSensor-013, REQ-PiSensor-010
Setup:     Deployment running on the Raspberry Pi 5; RFM69 link up.
Procedure: MARK(10); version.VERSION(ALL); action: read /proc/device-tree/model, /etc/os-release and `getconf LONG_BIT` on the Pi over ssh into bench-actions.log; bracket (2 Heartbeat samples); action: list TCP sockets of the deployment process; MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1). metrics: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  Version events equal the manifest describe strings; check: model starts with "Raspberry Pi 5", os-release ID is the Raspberry Pi OS (Debian) release of the manifest, LONG_BIT == 64; socket list empty.
Planted faults:none

ID:        L0-2
Title:     Marker round-trip
Purpose:   Proves the marker command round-trips over the RFM69 on the Raspberry Pi 5 so every later window can be bracketed.
Covers:    REQ-PiSensor-013, REQ-PiSensor-010
Setup:     As L0-1.
Procedure: MARK(20); bracket (2 Heartbeat samples); MARK(42405); action: read /proc/device-tree/model, /etc/os-release and `getconf LONG_BIT` on the Pi over ssh into bench-actions.log; MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  Three NoOpStringReceived events in order, strings byte-exact; platform check as L0-1.
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry period
Purpose:   Proves every sensor channel arrives at the ground at least every 2 s.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-010, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(30); wait 60 s; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: largest gap between ground reception times of every sensor channel in the window <= 2 s.
Evidence:  Channel strips over 60 s; check: bmpManager.Reading temperature between -20 and 60 degC; imuManager.Reading acceleration magnitude between 8 and 12 m/s^2; gpsManager.Reading within 1 km of the bench position in the manifest.
Planted faults:none

ID:        L2-2
Title:     Sensor telemetry period under command traffic
Purpose:   Proves the 2 s telemetry period holds while commands are dispatched.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-010, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(32); cmdDisp.CMD_NO_OP(); wait 10 s; cmdDisp.CMD_NO_OP(); wait 10 s; cmdDisp.CMD_NO_OP(); wait 10 s; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: largest gap between ground reception times of every sensor channel in the window <= 2 s.
Evidence:  As L2-1; check: event cmdDisp.NoOpReceived count == 3.
Planted faults:none

ID:        L2-3
Title:     Capture and downlink of one product
Purpose:   Proves one capture stores one product with a JPEG of at least 640x480, the three metrics and their times, delivered byte-identical by CFDP class 2.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-008, REQ-PiSensor-009, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(40); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); fileManager.CalculateCrc(P); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait CFDP transactions finished at the ground; MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_3). metrics: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s.
Evidence:  check: event dpWriter.FileWritten count == 1; check: exactly one file arrived; check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground; checks on the ground file: it parses as an F Prime data product container; the picture record starts FFD8 and ends FFD9, SOF0 width >= 640 and height >= 480; one location, one attitude and one temperature record.
Planted faults:capture_twice

ID:        L2-4
Title:     Two captures, one catalog downlink
Purpose:   Proves a second capture stores a second product with its own capture time and the catalog downlinks both, byte-identical.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-008, REQ-PiSensor-009
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(42); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P1); wait 5 s; piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P2); fileManager.CalculateCrc(P1); fileManager.CalculateCrc(P2); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait CFDP transactions finished at the ground; MARK(43).
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L2_4). metrics: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s.
Evidence:  check: event dpWriter.FileWritten count == 2 with different names; capture time of P2 later than that of P1; check: exactly two files arrived; check: CRC of record/raw/files/<P1> and <P2>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground; checks on the ground file: it parses as an F Prime data product container; the picture record starts FFD8 and ends FFD9, SOF0 width >= 640 and height >= 480; one location, one attitude and one temperature record.
Planted faults:append_before_xmit

ID:        L2-5
Title:     Product content against the telemetry
Purpose:   Proves the metrics stored in a product are the sensor readings downlinked around its capture.
Covers:    REQ-PiSensor-005, REQ-PiSensor-006
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(44); wait 10 s; piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); wait 10 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait CFDP transactions finished at the ground; MARK(45).
Window:    Marker(id=44) … Marker(id=45)
Pass rule: named checks declared in the integration test (test_L2_5). metrics: bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s.
Evidence:  checks on the ground file: it parses as an F Prime data product container; the picture record starts FFD8 and ends FFD9, SOF0 width >= 640 and height >= 480; one location, one attitude and one temperature record; check: the temperature record equals a bmpManager.Reading sample of the window, the acceleration and angular rate of the attitude record equal an imuManager.Reading sample, the location record equals a gpsManager.Reading sample; roll and pitch equal the bench computation from that acceleration within 0.1 deg.
Planted faults:none

ID:        L2-6
Title:     Capture time bound, repeated
Purpose:   Proves three captures in a row each complete within 30 s.
Covers:    REQ-PiSensor-004, REQ-PiSensor-007
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(46); piCamera.CAPTURE(); wait command completion; piCamera.CAPTURE(); wait command completion; piCamera.CAPTURE(); wait command completion; MARK(47).
Window:    Marker(id=46) … Marker(id=47)
Pass rule: named checks declared in the integration test (test_L2_6). metrics: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s.
Evidence:  check: event dpWriter.FileWritten count == 3.
Planted faults:none

ID:        L2-7
Title:     Telemetry during a downlink
Purpose:   Proves sensor telemetry continues at least every 10 s while products are downlinked over the RFM69.
Covers:    REQ-PiSensor-012, REQ-PiSensor-008, REQ-PiSensor-009, REQ-PiSensor-010, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(50); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); fileManager.CalculateCrc(P); MARK(51); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait CFDP transactions finished at the ground; MARK(52).
Window:    Q = Marker(id=50) … Marker(id=51); D = Marker(id=51) … Marker(id=52)
Pass rule: named checks declared in the integration test (test_L2_7). metrics: largest gap between ground reception times of every sensor channel in D <= 10 s; CFDP transaction duration in D >= 30 s (a precondition (require): a downlink shorter than 30 s cannot show the 10 s bound).
Evidence:  check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground.
Planted faults:append_before_xmit

ID:        L2-8
Title:     Telemetry and commands during a downlink
Purpose:   Proves sensor telemetry continues and a command is served while two products are downlinked.
Covers:    REQ-PiSensor-012, REQ-PiSensor-010
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(53); piCamera.CAPTURE(); wait event dpWriter.FileWritten; piCamera.CAPTURE(); wait event dpWriter.FileWritten; MARK(54); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait 15 s; cmdDisp.CMD_NO_OP(); wait CFDP transactions finished at the ground; MARK(55).
Window:    Q = Marker(id=53) … Marker(id=54); D = Marker(id=54) … Marker(id=55)
Pass rule: named checks declared in the integration test (test_L2_8). metrics: largest gap between ground reception times of every sensor channel in D <= 10 s; CFDP transaction duration in D >= 30 s (as L2-7).
Evidence:  check: event cmdDisp.NoOpReceived count == 1 during the downlink; check: every CFDP transaction in the window is class 2 and finished complete at the ground.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board for the independent final-state check.
Covers:    REQ-PiSensor-009, REQ-PiSensor-005
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the Feather ground station to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(60); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); fileManager.CalculateCrc(P); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT); wait CFDP transactions finished at the ground; fileManager.ListDirectory(product directory); MARK(61).
Window:    Marker(id=60) … Marker(id=61)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; checks on the ground file: it parses as an F Prime data product container; the picture record starts FFD8 and ends FFD9, SOF0 width >= 640 and height >= 480; one location, one attitude and one temperature record; the directory listing names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-PiSensor-001 | L2-1, L2-2 |  |
| REQ-PiSensor-002 | L2-1, L2-2 |  |
| REQ-PiSensor-003 | L2-1, L2-2 |  |
| REQ-PiSensor-004 | L2-3, L2-4, L2-6 |  |
| REQ-PiSensor-005 | L2-3, L2-4, L2-5, L7-1 |  |
| REQ-PiSensor-006 | L2-3, L2-4, L2-5 |  |
| REQ-PiSensor-007 | L2-3, L2-4, L2-6 |  |
| REQ-PiSensor-008 | L2-3, L2-4, L2-7 |  |
| REQ-PiSensor-009 | L2-3, L2-4, L2-7, L7-1 |  |
| REQ-PiSensor-010 | L0-1, L0-2, L2-1, L2-2, L2-7, L2-8 |  |
| REQ-PiSensor-011 | L2-1, L2-2, L2-3, L2-7 |  |
| REQ-PiSensor-012 | L2-7, L2-8 |  |
| REQ-PiSensor-013 | L0-1, L0-2 |  |

## 5 Metrics
- L0-1: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L2-1: largest gap between ground reception times of every sensor channel in the window <= 2 s
- L2-2: largest gap between ground reception times of every sensor channel in the window <= 2 s
- L2-3: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s
- L2-4: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s
- L2-5: bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; the location, attitude and temperature records each carry a sample time, none later than the capture time record + 2 s
- L2-6: CAPTURE completion (cmdDisp.OpCodeCompleted of its opcode) - t(piCamera.CAPTURE sent) <= 30 s
- L2-7: largest gap between ground reception times of every sensor channel in D <= 10 s; CFDP transaction duration in D >= 30 s
- L2-8: largest gap between ground reception times of every sensor channel in D <= 10 s; CFDP transaction duration in D >= 30 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): append_before_xmit (uut-state; L2-4, L2-7); capture_twice (stimulus; L2-3).

## 7 Not covered
- Fault, warning and rejection behaviour of `piCamera`: its component campaign.
- Fault and warning behaviour of inherited components: not required at system level; their own tests, where they exist, cover it.
- CFDP uplink, packet loss and retransmission: no system requirement.
- Radio interference and range: the RFM69 link is tested at bench range only.
- Today's bench cannot run these tests: the BMP280 and GPS receiver do not answer, and the camera and the Feather ground station are absent.

## 8 Decision log
1. 2026-11-18 designer — test deployment = the deployment as flown; no test component (human direction).
2. 2026-11-18 designer — product content is judged on the ground copy of the file; `fileManager.CalculateCrc` gives the on-board check and the bench `sha256sum` the independent final state.
3. 2026-11-18 designer — planted faults rewrite or insert commands of existing components only.
4. 2026-11-18 designer — every test makes its own product; no test depends on a product of another test.
