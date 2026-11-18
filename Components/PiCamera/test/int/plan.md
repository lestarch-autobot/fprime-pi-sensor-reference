# PiCamera component test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)` as in the project plan. Event rate: at most 2 events per second in any window. The piCamera channels are added to the heartbeat set so each window brackets them.
- UUT: `piCamera` in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13; ground system fprime-yamcs over TCP.
- The picture is judged on the ground copy of the data product (picture record), delivered by `productManager` and CFDP; `CAPTURE`, `DOWNLINK` are `productManager` commands, `BENCH_LINE`, `MARK` are `sysTester` commands.
- Out of scope: the data product's other records, the RFM69 link, picture content.

## 1 Entry gates
- Unit tests of PiCamera pass with line coverage at or above the plan's threshold.
- Camera attached; its model and `rpicam-still --list-cameras` reply recorded in the SDD Introduction (a module libcamera does not support reopens the requirements).
- `dpkg-query -W libcamera-dev` on the target read once; a version other than 0.8.0 reopens REQ-PiCamera-017 before any run.
- Bench line CAMERA of `sysTester.BENCH_LINE` makes the camera unavailable and available without a process restart (driver unbind and bind, as project test L5-11); confirmed at L0 on the bench.
- Image built from the manifest SHAs; L0-1 passes; product directory empty at the start of each test (teardown removes the products; L7-1 has no teardown).

## 2 Test levels
L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L7 final state. No L4: no requirement has an endurance bound. No L6: the component has no command to reject; refusals at its ports (`BUSY`, `PICTURE_OUTSTANDING`, rejected return) are unit tests.

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (STD-ERR): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 1; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (STD-RST): both markers present; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched, piCamera.CapturesCompleted, piCamera.CapturesFailed, piCamera.LastPictureSize, piCamera.CameraPresent, piCamera.PictureOutstanding.

ID:        L0-1
Title:     Image identity
Purpose:   Proves the running image is the manifest's image.
Covers:    —
Setup:     Prototype image running; link up.
Procedure: MARK(10); VERSION(ALL); bracket (2 Heartbeat samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  require: Version events equal the manifest describe strings.
Planted faults:none

ID:        L0-2
Title:     Camera library identity
Purpose:   Proves the image links the packaged libcamera of the pinned version and no OpenCV.
Covers:    REQ-PiCamera-017
Setup:     Prototype image running; link up.
Procedure: MARK(12); action: log `dpkg-query -W libcamera-dev` and `ldd` of the deployment binary, over ssh, into bench-actions.log; bracket (2 Heartbeat samples); MARK(13).
Window:    Marker(id=12) … Marker(id=13)
Pass rule: named checks declared in the integration test (test_L0_2). metrics: libcamera-dev version starts with 0.8.0; ldd lists libcamera and no opencv.
Evidence:  The two bench log lines; evidence outside the UUT's reporting path. Also the record the REQ-PiCamera-016 inspection reads.
Planted faults:none

ID:        L2-1
Title:     One capture delivers one picture
Purpose:   Proves a capture request delivers one 640x480 JFIF picture acquired after the request.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(20); bracket (2 Heartbeat samples); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench time of CAPTURE sent - 2 s <= capture time record of P1 <= CAPTURE completion + 2 s.
Evidence:  check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 1; check: delta(piCamera.CapturesFailed) == 0; check: last(piCamera.LastPictureSize) == size of the picture record of the ground file.
Planted faults:capture_dropped

ID:        L2-2
Title:     Two captures deliver two different pictures
Purpose:   Proves each capture delivers a newly acquired 640x480 JFIF picture.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(22); bracket (2 Heartbeat samples); CAPTURE(); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; DOWNLINK(P2); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(23).
Window:    Marker(id=22) … Marker(id=23)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; picture record of P2 is JFIF, SOI to EOI, 640 x 480; sha256 of the picture records of P1 and P2 differ (sensor noise makes two frames of one scene differ; equal bytes mean a frame was reused); bench time of CAPTURE sent - 2 s <= capture time record of P2 <= CAPTURE completion + 2 s.
Evidence:  check: event piCamera.CaptureStarted count == 2; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 2.
Planted faults:corrupt_picture

ID:        L3-1
Title:     Capture after a process kill during a capture
Purpose:   Proves the first capture after a process kill during a capture succeeds.
Covers:    REQ-PiCamera-019
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(30); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: kill the deployment process (SIGKILL), triggered by the CaptureStarted event; wait first Heartbeat samples at the ground; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L3_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  require (else UNVERIFIED, the race was lost): event piCamera.CaptureStarted count == 1 and event productManager.ProductWritten count == 0 before the action. check: event sysTester.Started count == 1; after the restart: check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: event productManager.ProductWritten count == 1.
Planted faults:no_restart

ID:        L3-2
Title:     Capture after a service restart during a capture
Purpose:   Proves the first capture after a service restart during a capture succeeds.
Covers:    REQ-PiCamera-019
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(32); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: restart the deployment service (systemctl restart), triggered by the CaptureStarted event; wait first Heartbeat samples at the ground; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L3_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  require (else UNVERIFIED, the race was lost): event piCamera.CaptureStarted count == 1 and event productManager.ProductWritten count == 0 before the action. check: event sysTester.Started count == 1; after the restart: check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: event productManager.ProductWritten count == 1.
Planted faults:none

ID:        L5-1
Title:     Camera absent, then back
Purpose:   Proves an absent camera gives NO_CAMERA and the next capture succeeds without a restart.
Covers:    REQ-PiCamera-014
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(40); bracket (2 Heartbeat samples); BENCH_LINE(CAMERA, OFF); CAPTURE(); BENCH_LINE(CAMERA, ON); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  check: first CAPTURE completes with error; check: event piCamera.CaptureFailed(reason=NO_CAMERA, step=DETECT) count == 1; check: event piCamera.CaptureFailed count == 1; check: delta(piCamera.CapturesFailed) == 1; check: second CAPTURE completes; check: delta(piCamera.CapturesCompleted) == 1; check: event sysTester.Started count == 0.
Planted faults:camera_kept_absent

ID:        L5-2
Title:     Camera held by another process, then free
Purpose:   Proves a camera in use elsewhere gives CAMERA_ERROR and the next capture succeeds without a restart.
Covers:    REQ-PiCamera-014
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(42); bracket (2 Heartbeat samples); action: start `rpicam-hello -t 0` on the Pi (holds the camera); CAPTURE(); action: stop rpicam-hello; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(43).
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L5_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  check: first CAPTURE completes with error; check: event piCamera.CaptureFailed(reason=CAMERA_ERROR, step=OPEN) count == 1; check: event piCamera.CaptureFailed count == 1; check: delta(piCamera.CapturesFailed) == 1; check: second CAPTURE completes; check: delta(piCamera.CapturesCompleted) == 1; check: event sysTester.Started count == 0.
Planted faults:none

ID:        L7-1
Title:     Final picture for independent verification
Purpose:   Proves the last picture on board is the 640x480 JFIF picture received at the ground.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(50); bracket (2 Heartbeat samples); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(51).
Window:    Marker(id=50) … Marker(id=51)
Pass rule: named checks declared in the integration test (test_L7_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench sha256 of the product file on board == sha256 of the ground file.
Evidence:  check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 1; check: delta(piCamera.CapturesFailed) == 0; No teardown: the product stays for the bench `sha256sum` taken over ssh after the run.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-PiCamera-001 | Integration Test |  |
| REQ-PiCamera-002 | Integration Test |  |
| REQ-PiCamera-003 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-004 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-005 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-006 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-007 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-008 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-009 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-010 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-011 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-012 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-013 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-014 | Integration Test |  |
| REQ-PiCamera-015 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-016 | waived: Inspection | build inputs and linked libraries of the camera software; L0-2 records the linked libraries |
| REQ-PiCamera-017 | Integration Test |  |
| REQ-PiCamera-018 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-019 | Integration Test |  |
| REQ-PiCamera-020 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-021 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-022 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-023 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-024 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |

## 5 Metrics
- L0-2: libcamera-dev version starts with 0.8.0; ldd lists libcamera and no opencv
- L2-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench time of CAPTURE sent - 2 s <= capture time record of P1 <= CAPTURE completion + 2 s
- L2-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480; picture record of P2 is JFIF, SOI to EOI, 640 x 480; sha256 of the picture records of P1 and P2 differ; bench time of CAPTURE sent - 2 s <= capture time record of P2 <= CAPTURE completion + 2 s
- L3-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L3-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L5-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L5-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L7-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench sha256 of the product file on board == sha256 of the ground file

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): camera_kept_absent (stimulus; L5-1); capture_dropped (stimulus; L2-1); corrupt_picture (uut-state; L2-2); no_restart (harness-expectation; L3-1).

## 7 Not covered
- REQ-PiCamera-003 to -013, -015, -018, -020 to -024: unit tests; the requester (`productManager`) sends one request at a time and returns every picture, so `BUSY`, `TIMEOUT`, `NO_BUFFER`, `PICTURE_OUTSTANDING`, `TOO_LARGE` and a rejected return cannot be forced on the bench.
- REQ-PiCamera-016: inspection.
- A camera that stops answering during a capture (`TIMEOUT`) and a frame the library marks bad: not plantable on the bench without touching the ribbon cable under power.
- Picture content (exposure, focus).

## 8 Decision log
1. 2026-11-17 designer — the component is tested in the project's test deployment (full deployment + `sysTester`), not a reduced one.
2. 2026-11-17 designer — REQ-PiCamera-001 'acquired after its request' is judged by two captures giving different picture bytes and by the capture time record against bench time (tolerance 2 s, project decision D12).
3. 2026-11-17 designer — max planted faults per draw 2; menu covers L2-1, L2-2, L3-1, L5-1.
4. 2026-11-17 designer — `BENCH_LINE(CAMERA, state)` is a bench line this plan needs from `sysTester`; reported to the parent campaign.
