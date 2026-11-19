# PiSensor system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker: `cmdDisp.CMD_NO_OP_STRING(arg1)` -> event `cmdDisp.NoOpStringReceived`, the id sent as a decimal string. Link budget [I]: RFM69 at the catalog default data rate 19200 bit/s carries about 2400 byte/s; sensor telemetry at 1 Hz leaves the rest to CFDP, so a 100 kB product takes on the order of a minute.
- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS.
- Test deployment: the deployment itself. No component is added for testing. Markers use `cmdDisp`, the on-board file check uses `fileManager.CalculateCrc`, the directory listing uses `fileManager.ListDirectory`, product names come from `dpWriter.FileWritten`, platform identity is a bench action over ssh.
- Ground system: fprime-yamcs at the ledger pin with the project YAMCS configuration directory (CFDP service), joined to the RFM69 link by the bench ground radio (bench setup, not part of the SSDD; it passes TM and TC frames unchanged and is recorded in the manifest).
- Record content (`record/`): every exported row carries the ground reception time beside the FSW time; `record/raw/bench-actions.log` holds each bench action with its bench start and end time; every CFDP file received is copied to `record/raw/files/` before it is checked; CFDP class and outcome come from the YAMCS transfer record exported to `record/raw/cfdp.json`.
- Completeness: every window requires STD; an overflowed queue or a gap in the downlinked TM frame count makes the window UNVERIFIED, never a pass of an absence or count check. The frame counts come from the YAMCS frame record, exported to `record/raw/frames.json`.
- Bench and Pi clocks: both synchronised by NTP; the offset is measured at L0-1 and must be under 0.5 s; tolerances that compare the two clocks use 2 s.
- Heartbeat: `imuManager.Reading`, written to the telemetry packet every 1 Hz cycle; `cmdDisp.CommandsDispatched` updates on change only.
- Minimum sample counts come from the requirement: one sample per 2 s of window outside a downlink (30 in 60 s, 15 in 30 s).
- `dpCat.START_XMIT_CATALOG` is always sent with `remainActive` false: a product stored after the catalog is built is not sent once that downlink has finished. Each test waits 30 s (the REQ-PiSensor-007 bound) before it builds the catalog, so every product of the test is stored first.
- Telemetry gaps are judged on ground reception time: the requirement is stated at the ground. Telemetry is sent at 1 Hz, so the 2 s bound leaves one period of margin for radio delay.
- CFDP as shipped deletes a file after sending it (`cfdpManager.FileInDefaultKeep`, default DELETE): the on-board CRC is taken before the downlink, and L7-1 sets KEEP.
- Constants: temperature -20 to 60 degC and gravity 8 to 12 m/s^2 are plausibility bounds for an indoor bench at rest; 1 km is the GPS plausibility bound around the surveyed bench position; 0.1 deg is the rounding allowance of the roll and pitch computation; the L2-5 widening values (0.5 degC, 2 deg, 0.0001 deg) are noise allowances for a bench at rest [I], to be confirmed against the BMP280 and MPU6050 datasheets and the receiver accuracy at the bench refresh; `piCamera.CaptureFailed` is the name planned for the capture failure event, confirmed against the `piCamera` SDD at the same refresh; the 30 s downlink precondition is three times the 10 s bound; the file CRC is that of `Os::File::calculateCrc`; the product directory is `DataProductsConfig.Paths.dpDir`.
- Out of scope: BMP280 pressure; yaw.

## 1 Entry gates
- Component campaign `picam` closed; its unit tests pass.
- Image built from the manifest SHAs; L0-1 and L0-2 pass on the bench.
- Product directory empty at the start of each test (bench teardown empties the product directory over ssh; L7-1 has no teardown).
- Bench recipe: BMP280, MPU6050, GPS receiver with a fix and Pi Camera attached to the Pi 5; RFM69 ground radio joined to fprime-yamcs on the ground host (supplied with the bench).

## 2 Test levels
L0 provenance and feasibility · L2 functional · L7 final state. No L3, L4, L5 or L6 test: no system requirement states restart, endurance, fault or rejection behaviour; those belong to the components.

## 3 Test entries

Window rule: rows from the **last** `cmdDisp.NoOpStringReceived(id=START)` row that precedes the first `cmdDisp.NoOpStringReceived(id=END)` row following it, through that END row plus the END `cmdDisp.CMD_NO_OP_STRING` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0 for every opcode but piCamera.CAPTURE (a failed capture is judged by the test, as FAIL); no gap in the TM transfer frame count received by YAMCS between the markers (record/raw/frames.json); event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event piCamera.CaptureFailed count == 0; severity FATAL count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = imuManager.Reading; Sensors = bmpManager.Reading, imuManager.Reading, gpsManager.Reading.

ID:        L0-1
Title:     Image and platform identity
Purpose:   Proves the image is the manifest's, on a Pi 5, reached only by RFM69.
Covers:    REQ-PiSensor-013, REQ-PiSensor-010
Setup:     Deployment running on the Raspberry Pi 5; RFM69 link up.
Procedure: MARK(10); version.VERSION(ALL); action: read /proc/device-tree/model, /etc/os-release, /etc/rpi-issue and `getconf LONG_BIT` on the Pi over ssh into bench-actions.log; bracket (2 Heartbeat samples); action: list TCP and UDP sockets and open devices of the deployment process; MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1). metrics: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  Version events equal the manifest describe strings; check: model starts with "Raspberry Pi 5", /etc/os-release VERSION_ID == 13 and VERSION_CODENAME == trixie (REQ-PiSensor-013), /etc/rpi-issue exists and names Raspberry Pi OS, LONG_BIT == 64; check: the process holds no TCP or UDP socket and no open device but the radio SPI device and the sensor buses; check: LibraryVersions names fprime-sensors only; check: the dictionary of the image holds no command of a test component.
Planted faults:none

ID:        L0-2
Title:     Marker round-trip
Purpose:   Proves the marker command round-trips, so later windows can be bracketed.
Covers:    REQ-PiSensor-013
Setup:     As L0-1.
Procedure: MARK(20); bracket (2 Heartbeat samples); MARK(42405); action: read /proc/device-tree/model, /etc/os-release, /etc/rpi-issue and `getconf LONG_BIT` on the Pi over ssh into bench-actions.log; MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  Three NoOpStringReceived events in order, strings byte-exact; platform check as L0-1.
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry period
Purpose:   Proves every sensor channel arrives at the ground at least every 2 s.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(30); wait 60 s; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: for every sensor channel in the window: samples >= 30, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 2 s.
Evidence:  Channel strips over 60 s; check: bmpManager.Reading temperature between -20 and 60 degC; imuManager.Reading acceleration magnitude between 8 and 12 m/s^2 and angular rate magnitude <= 0.5 rad/s (bench at rest; MPU6050 datasheet zero-rate offset 20 deg/s); gpsManager.Reading within 1 km of the bench position in the manifest.
Planted faults:none

ID:        L2-2
Title:     Sensor telemetry period under command traffic
Purpose:   Proves the 2 s telemetry period holds while commands are dispatched.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(32); cmdDisp.CMD_NO_OP(); wait 10 s; cmdDisp.CMD_NO_OP(); wait 10 s; cmdDisp.CMD_NO_OP(); wait 10 s; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: for every sensor channel in the window: samples >= 15, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 2 s.
Evidence:  As L2-1; check: event cmdDisp.NoOpReceived count == 3.
Planted faults:extra_noop

ID:        L2-3
Title:     Capture and downlink of one product
Purpose:   Proves one capture stores one complete product, delivered byte-identical by CFDP class 2.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-008, REQ-PiSensor-009, REQ-PiSensor-011, REQ-PiSensor-014
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(40); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); fileManager.CalculateCrc(P); wait 30 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground; MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_3). metrics: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock); bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each.
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1; check: event dpWriter.FileWritten count == 1; check: exactly one file arrived; check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground; checks on the ground file: it parses as an F Prime data product container; the picture record decodes with the bench JPEG decoder, decoded width >= 640 and height >= 480; one latitude, one longitude, one roll, one pitch and one temperature record.
Planted faults:capture_before_xmit

ID:        L2-4
Title:     Two captures, one catalog downlink
Purpose:   Proves two captures store two products and the catalog downlinks both.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-008, REQ-PiSensor-009, REQ-PiSensor-014
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(42); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P1); wait 5 s; piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P2); fileManager.CalculateCrc(P1); fileManager.CalculateCrc(P2); wait 30 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground; MARK(43).
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L2_4). metrics: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock); bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each.
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2; check: event dpWriter.FileWritten count == 2 with different names; capture time of P2 later than that of P1; picture records of P1 and P2 differ; check: exactly two files arrived; check: CRC of record/raw/files/<P1> and <P2>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground; checks on the ground file: it parses as an F Prime data product container; the picture record decodes with the bench JPEG decoder, decoded width >= 640 and height >= 480; one latitude, one longitude, one roll, one pitch and one temperature record.
Planted faults:capture_before_xmit

ID:        L2-5
Title:     Product content against the telemetry
Purpose:   Proves the metrics stored in a product are the sensor readings downlinked around its capture.
Covers:    REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-014, REQ-PiSensor-008
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(44); wait 10 s; piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); wait 10 s; wait 30 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground; MARK(45).
Window:    Marker(id=44) … Marker(id=45)
Pass rule: named checks declared in the integration test (test_L2_5). metrics: bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each.
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1; check: every CFDP transaction in the window is class 2 and finished complete at the ground; check: exactly one file arrived; checks on the ground file: it parses as an F Prime data product container; the picture record decodes with the bench JPEG decoder, decoded width >= 640 and height >= 480; one latitude, one longitude, one roll, one pitch and one temperature record; check, for each metric: its sample time equals, or lies between, FSW time tags of that channel's samples in the window; where a window sample has the same FSW time the values are equal (roll and pitch within 0.1 deg of the bench computation); otherwise the value lies between the two samples that bracket the sample time, widened by 0.5 degC for temperature, 2 deg for roll and pitch, and 0.0001 deg for latitude and longitude.
Planted faults:none

ID:        L2-6
Title:     Capture time bound, repeated
Purpose:   Proves three captures in a row each store their product within 30 s.
Covers:    REQ-PiSensor-004, REQ-PiSensor-007
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(46); piCamera.CAPTURE(); wait event dpWriter.FileWritten; piCamera.CAPTURE(); wait event dpWriter.FileWritten; piCamera.CAPTURE(); wait event dpWriter.FileWritten; MARK(47).
Window:    Marker(id=46) … Marker(id=47)
Pass rule: named checks declared in the integration test (test_L2_6). metrics: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock).
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 3; check: event dpWriter.FileWritten count == 3.
Planted faults:none

ID:        L2-7
Title:     Telemetry during a downlink
Purpose:   Proves sensor telemetry continues every 10 s during a downlink.
Covers:    REQ-PiSensor-012, REQ-PiSensor-008, REQ-PiSensor-009, REQ-PiSensor-010, REQ-PiSensor-011
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(50); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P1); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P2); fileManager.CalculateCrc(P1); fileManager.CalculateCrc(P2); MARK(51); wait 30 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground; MARK(52).
Window:    Q = Marker(id=50) … Marker(id=51); D = Marker(id=51) … Marker(id=52)
Pass rule: named checks declared in the integration test (test_L2_7). metrics: for every sensor channel in D: samples >= 3, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 10 s; CFDP transaction duration in D >= 30 s (a precondition (require): a downlink shorter than 30 s cannot show the 10 s bound).
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2; check: event dpWriter.FileWritten count == 2 over the whole test (Q and D); check: exactly two files arrived; check: rfm69Manager.PacketsTransmitted and rfm69Manager.PacketsReceived each rise in D; check: CRC of record/raw/files/<P1> and <P2>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; check: every CFDP transaction in the window is class 2 and finished complete at the ground.
Planted faults:capture_before_xmit

ID:        L2-8
Title:     Telemetry and commands during a downlink
Purpose:   Proves telemetry continues and a command is served during a downlink.
Covers:    REQ-PiSensor-012, REQ-PiSensor-010
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(53); piCamera.CAPTURE(); wait event dpWriter.FileWritten; piCamera.CAPTURE(); wait event dpWriter.FileWritten; MARK(54); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait 15 s; cmdDisp.CMD_NO_OP(); wait event dpCat.CatalogXmitCompleted and both CFDP transactions finished at the ground; MARK(55).
Window:    Q = Marker(id=53) … Marker(id=54); D = Marker(id=54) … Marker(id=55)
Pass rule: named checks declared in the integration test (test_L2_8). metrics: for every sensor channel in D: samples >= 3, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 10 s; CFDP transaction duration in D >= 30 s (as L2-7).
Evidence:  check: event cmdDisp.NoOpReceived count == 1 between dpCat.CatalogXmitStarted and dpCat.CatalogXmitCompleted; check: exactly two files arrived; check: rfm69Manager.PacketsTransmitted and rfm69Manager.PacketsReceived each rise in D; check: every CFDP transaction in the window is class 2 and finished complete at the ground.
Planted faults:extra_noop

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board for the independent final-state check.
Covers:    REQ-PiSensor-009, REQ-PiSensor-005, REQ-PiSensor-008
Setup:     Deployment running on the Raspberry Pi 5, RFM69 link up through the bench ground radio to fprime-yamcs, all four sensors answering, product directory empty.
Procedure: MARK(60); cfdpManager.FileInDefaultKeep_PRM_SET(KEEP); piCamera.CAPTURE(); wait event dpWriter.FileWritten (names P); fileManager.CalculateCrc(P); wait 30 s; dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait event dpCat.CatalogXmitCompleted and every CFDP transaction of the window finished at the ground; fileManager.ListDirectory(product directory); dpCat.BUILD_CATALOG(); dpCat.START_XMIT_CATALOG(NO_WAIT, false); wait 30 s; MARK(61).
Window:    Marker(id=60) … Marker(id=61)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  check: event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1; check: CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P; checks on the ground file: it parses as an F Prime data product container; the picture record decodes with the bench JPEG decoder, decoded width >= 640 and height >= 480; one latitude, one longitude, one roll, one pitch and one temperature record; the directory listing names P only; check: no CFDP transaction starts after the second START_XMIT_CATALOG. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt.
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
| REQ-PiSensor-008 | L2-3, L2-4, L2-5, L2-7, L7-1 |  |
| REQ-PiSensor-009 | L2-3, L2-4, L2-7, L7-1 |  |
| REQ-PiSensor-010 | L0-1, L2-7, L2-8 |  |
| REQ-PiSensor-011 | L2-1, L2-2, L2-3, L2-7 |  |
| REQ-PiSensor-012 | L2-7, L2-8 |  |
| REQ-PiSensor-013 | L0-1, L0-2 |  |
| REQ-PiSensor-014 | L2-3, L2-4, L2-5 |  |

## 5 Metrics
- L0-1: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L2-1: for every sensor channel in the window: samples >= 30, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 2 s
- L2-2: for every sensor channel in the window: samples >= 15, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 2 s
- L2-3: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock); bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each
- L2-4: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock); bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each
- L2-5: bench time of CAPTURE sent - 2 s <= capture time record <= bench time at which the OpCodeCompleted row of piCamera.CAPTURE was received + 2 s; the latitude, longitude, roll, pitch and temperature records each carry a sample time, and |sample time - capture time record| <= 2 s for each
- L2-6: t(event dpWriter.FileWritten) - t(cmdDisp.OpCodeDispatched of piCamera.CAPTURE) <= 30 s, for each CAPTURE (FSW clock)
- L2-7: for every sensor channel in D: samples >= 3, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 10 s; CFDP transaction duration in D >= 30 s
- L2-8: for every sensor channel in D: samples >= 3, and the largest gap between ground reception times, counting window start to first sample and last sample to window end, <= 10 s; CFDP transaction duration in D >= 30 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): capture_before_xmit (uut-state; L2-3, L2-4, L2-7); extra_noop (stimulus; L2-2, L2-8).

## 7 Not covered
- Fault, warning and rejection behaviour of `piCamera`: its component campaign.
- Fault and warning behaviour of inherited components: not required at system level; their own tests, where they exist, cover it.
- CFDP uplink, packet loss and retransmission: no system requirement.
- Radio interference and range: the RFM69 link is tested at bench range only.
- Today's bench cannot run these tests: the BMP280 and GPS receiver do not answer, and the camera and the ground radio are absent.

## 8 Decision log
1. 2026-11-18 designer — test deployment = the deployment as flown; no test component (human direction).
2. 2026-11-18 designer — product content is judged on the ground copy of the file; `fileManager.CalculateCrc` gives the on-board check and the bench `sha256sum` the independent final state.
3. 2026-11-18 designer — planted faults insert commands of existing components only; a grown or altered product file is not usable as a fault because `Svc.DpCatalog` refuses it (size check).
4. 2026-11-18 designer — every test makes its own product; no test depends on a product of another test.
