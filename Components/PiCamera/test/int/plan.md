# PiCamera component test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)` as in the project plan. Event rate [I]: at most 2 events per second in any window (one capture gives CaptureStarted, ProductWritten and two command events over about 2 s; measured at L0-4). The piCamera channels are added to the heartbeat set so each window brackets them.
- UUT: `piCamera` in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13; ground system fprime-yamcs over TCP.
- The picture is judged on the ground copy of the data product (picture record), delivered by `productManager` and CFDP; `CAPTURE`, `DOWNLINK` are `productManager` commands, `BENCH_LINE`, `MARK` are `sysTester` commands.
- Out of scope: the data product's other records, the RFM69 link, picture content.

## 1 Entry gates
- Unit tests of PiCamera pass with line coverage at or above the plan's threshold.
- Camera attached; its model and `rpicam-still --list-cameras` reply recorded in the SDD Introduction (a module libcamera does not support reopens the requirements).
- `dpkg-query -W libcamera-dev` on the target read once; a version other than 0.8.0 reopens REQ-PiCamera-017 before any run.
- Bench line CAMERA of `sysTester.BENCH_LINE` makes the camera unavailable and available without a process restart (driver unbind and bind, as project test L5-11); L0-3 passes.
- Image built from the manifest SHAs; L0-1 to L0-5 pass; product directory empty at the start of each test (teardown removes the products; L7-1 has no teardown).

## 2 Test levels
L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L7 final state. No L4: no requirement has an endurance bound. No L6: the component has no command to reject; refusals at its ports (`BUSY`, `PICTURE_OUTSTANDING`, rejected return) are unit tests.

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (STD-RST): both markers present; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (STD-NOERR): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
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
Purpose:   Proves the image runs the packaged libcamera of the pinned version and links no OpenCV.
Covers:    REQ-PiCamera-016, REQ-PiCamera-017
Setup:     Prototype image running; link up.
Procedure: MARK(12); action: log `ldd` of the deployment binary and `dpkg -S` plus `dpkg-query -W` of the package owning each resolved libcamera and libjpeg library, over ssh, into bench-actions.log; bracket (2 Heartbeat samples); MARK(13).
Window:    Marker(id=12) … Marker(id=13)
Pass rule: named checks declared in the integration test (test_L0_2). metrics: package owning the resolved libcamera.so has version 0.8.0; every resolved library belongs to a Raspberry Pi OS package; ldd lists no opencv library.
Evidence:  The bench log lines; evidence outside the UUT's reporting path. REQ-PiCamera-016 is also inspected (build inputs).
Planted faults:none

ID:        L0-3
Title:     Camera line off and on
Purpose:   Proves the bench can make the camera unavailable and available without a process restart.
Covers:    —
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(14); bracket (2 Heartbeat samples); BENCH_LINE(CAMERA, OFF); action: log `rpicam-still --list-cameras` into bench-actions.log; BENCH_LINE(CAMERA, ON); action: log `rpicam-still --list-cameras` into bench-actions.log; bracket (2 Heartbeat samples); MARK(15).
Window:    Marker(id=14) … Marker(id=15)
Pass rule: named checks declared in the integration test (test_L0_3).
Evidence:  Feasibility entry: covers no requirement, takes no planted fault; a `require` that does not hold makes the tests named UNVERIFIED. require (L5-1): first listing names no camera, second names the camera of the SDD Introduction; check: event sysTester.Started count == 0.
Planted faults:none

ID:        L0-4
Title:     Capture duration against trigger latency
Purpose:   Proves a capture lasts long enough for the bench to act between CaptureStarted and the reply.
Covers:    —
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(16); bracket (2 Heartbeat samples); CAPTURE(); action: log the bench time CaptureStarted was received and a no-op action triggered on it, into bench-actions.log; bracket (2 Heartbeat samples); MARK(17).
Window:    Marker(id=16) … Marker(id=17)
Pass rule: named checks declared in the integration test (test_L0_4). metrics: t(event productManager.ProductWritten) - t(event piCamera.CaptureStarted) >= 2 x (bench time of the triggered action - t(event piCamera.CaptureStarted)) (require, L3-1 and L3-2).
Evidence:  Feasibility entry: covers no requirement, takes no planted fault; a `require` that does not hold makes the tests named UNVERIFIED. The measured capture duration and trigger latency are recorded in the ledger.
Planted faults:none

ID:        L0-5
Title:     Camera holder acquisition
Purpose:   Proves the bench holder process owns the camera within the settle time the fault test uses.
Covers:    —
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(18); bracket (2 Heartbeat samples); action: start `rpicam-hello -t 0 --nopreview` on the Pi; log its pid and the time of its first frame line into bench-actions.log; action: stop rpicam-hello; log its exit into bench-actions.log; bracket (2 Heartbeat samples); MARK(19).
Window:    Marker(id=18) … Marker(id=19)
Pass rule: named checks declared in the integration test (test_L0_5). metrics: first frame line of the holder - its start <= 5 s (require, L5-2).
Evidence:  Feasibility entry: covers no requirement, takes no planted fault; a `require` that does not hold makes the tests named UNVERIFIED. The measured acquisition time is the settle time of L5-2.
Planted faults:none

ID:        L2-1
Title:     One capture delivers one picture
Purpose:   Proves a capture request delivers one 640x480 JFIF picture acquired after the request.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(20); bracket (2 Heartbeat samples); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench time of CAPTURE sent - 2 s <= capture time record of P1 <= its completion + 2 s.
Evidence:  check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 1; check: delta(piCamera.CapturesFailed) == 0; check: last(piCamera.LastPictureSize) == size of the picture record of the ground file of the last product written.
Planted faults:capture_twice

ID:        L2-2
Title:     Two captures deliver two different pictures
Purpose:   Proves each capture delivers a newly acquired 640x480 JFIF picture.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(22); bracket (2 Heartbeat samples); CAPTURE(); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; DOWNLINK(P2); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(23).
Window:    Marker(id=22) … Marker(id=23)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; picture record of P2 is JFIF, SOI to EOI, 640 x 480; sha256 of the picture records of P1 and P2 differ (sensor noise makes two frames of one scene differ; equal bytes mean a frame was reused); bench time of the second CAPTURE sent - 2 s <= capture time record of P2 <= its completion + 2 s; capture time record of P2 > capture time record of P1.
Evidence:  check: event piCamera.CaptureStarted count == 2; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 2; check: delta(piCamera.CapturesFailed) == 0.
Planted faults:corrupt_picture

ID:        L3-1
Title:     Capture after a process kill during a capture
Purpose:   Proves the first capture after a process kill during a capture succeeds.
Covers:    REQ-PiCamera-019
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(30); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: kill the deployment process (SIGKILL), triggered by the CaptureStarted event; wait first Heartbeat samples at the ground; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L3_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  The window is split at its single sysTester.Started row: part A is the rows before it, part B the rows after it. require (else UNVERIFIED, the race was lost): A: event piCamera.CaptureStarted count == 1; A: event productManager.ProductWritten count == 0. check: event sysTester.Started count == 1; check: B: event piCamera.CameraFound count == 1, its camera argument equal to the identification of the SDD Introduction; check: B: event piCamera.CaptureStarted count == 1; check: B: event piCamera.CaptureFailed count == 0; check: B: event productManager.ProductWritten count == 1; require: B: event cmdDisp.OpCodeError count == 0; require: B: commands sent after the restart == count(event cmdDisp.OpCodeDispatched).
Planted faults:capture_after_restart_dropped

ID:        L3-2
Title:     Capture after a service restart during a capture
Purpose:   Proves the first capture after a service restart during a capture succeeds.
Covers:    REQ-PiCamera-019
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(32); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: restart the deployment service (systemctl restart), triggered by the CaptureStarted event; wait first Heartbeat samples at the ground; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L3_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  The window is split at its single sysTester.Started row: part A is the rows before it, part B the rows after it. require (else UNVERIFIED, the race was lost): A: event piCamera.CaptureStarted count == 1; A: event productManager.ProductWritten count == 0. check: event sysTester.Started count == 1; check: B: event piCamera.CameraFound count == 1, its camera argument equal to the identification of the SDD Introduction; check: B: event piCamera.CaptureStarted count == 1; check: B: event piCamera.CaptureFailed count == 0; check: B: event productManager.ProductWritten count == 1; require: B: event cmdDisp.OpCodeError count == 0; require: B: commands sent after the restart == count(event cmdDisp.OpCodeDispatched).
Planted faults:none

ID:        L5-1
Title:     Camera absent, then back
Purpose:   Proves an absent camera gives NO_CAMERA and the next capture succeeds without a restart.
Covers:    REQ-PiCamera-014
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(40); bracket (2 Heartbeat samples); BENCH_LINE(CAMERA, OFF); CAPTURE(); bracket (2 Heartbeat samples); BENCH_LINE(CAMERA, ON); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(41); teardown: action: bind the camera driver over ssh (not a command, outside the planted path); log `rpicam-still --list-cameras`.
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  The window requires STD-NOERR; the command error count is a check. check: event cmdDisp.OpCodeError count == 1; check: first CAPTURE completes with error; check: event piCamera.CaptureFailed(reason=NO_CAMERA, step=DETECT) count == 1; check: event piCamera.CaptureFailed count == 1; check: event piCamera.CaptureStarted count == 2; check: delta(piCamera.CapturesFailed) == 1; check: second CAPTURE completes; check: delta(piCamera.CapturesCompleted) == 1; check: event sysTester.Started count == 0. check: piCamera.CameraPresent == false in the bracket after the first CAPTURE; check: last(piCamera.CameraPresent) == true.
Planted faults:camera_kept_absent

ID:        L5-2
Title:     Camera held by another process, then free
Purpose:   Proves a camera in use elsewhere gives CAMERA_ERROR and the next capture succeeds without a restart.
Covers:    REQ-PiCamera-014
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(42); bracket (2 Heartbeat samples); action: start `rpicam-hello -t 0 --nopreview` on the Pi (holds the camera); wait the L0-5 settle time; log its pid; CAPTURE(); action: log that the holder pid is alive; stop rpicam-hello; log its exit; CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(43); teardown: action: stop any rpicam-hello over ssh.
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L5_2). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480.
Evidence:  require: bench-actions.log shows the holder alive at the first CAPTURE send and after its completion. The window requires STD-NOERR; the command error count is a check. check: event cmdDisp.OpCodeError count == 1; check: first CAPTURE completes with error; check: event piCamera.CaptureFailed(reason=CAMERA_ERROR, step=OPEN) count == 1; check: event piCamera.CaptureFailed count == 1; check: event piCamera.CaptureStarted count == 2; check: delta(piCamera.CapturesFailed) == 1; check: second CAPTURE completes; check: delta(piCamera.CapturesCompleted) == 1; check: event sysTester.Started count == 0.
Planted faults:none

ID:        L7-1
Title:     Final picture for independent verification
Purpose:   Leaves the final-state record: the last picture on board is the 640x480 JFIF picture received at the ground.
Covers:    REQ-PiCamera-001, REQ-PiCamera-002
Setup:     Prototype image running, link up, camera attached and free, product directory empty.
Procedure: MARK(50); bracket (2 Heartbeat samples); CAPTURE(); DOWNLINK(P1); wait CFDP transaction finished at the ground; bracket (2 Heartbeat samples); MARK(51).
Window:    Marker(id=50) … Marker(id=51)
Pass rule: named checks declared in the integration test (test_L7_1). metrics: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench sha256 of the product file on board == sha256 of the ground file.
Evidence:  check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 1; check: delta(piCamera.CapturesFailed) == 0; No teardown: the product stays for the bench `sha256sum` taken over ssh after the run. The hash equality is transport evidence; the picture predicates are the component's.
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
| REQ-PiCamera-016 | Inspection and Integration Test | inspection of the build inputs; L0-2 records the linked libraries |
| REQ-PiCamera-017 | Integration Test |  |
| REQ-PiCamera-018 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-019 | Integration Test |  |
| REQ-PiCamera-020 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-021 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-022 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-023 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |
| REQ-PiCamera-024 | waived: Unit Test (unit-test list, SDD section 8) | needs the camera substitute and the port tester of the unit-test build |

## 5 Metrics
- L0-2: package owning the resolved libcamera.so has version 0.8.0; every resolved library belongs to a Raspberry Pi OS package; ldd lists no opencv library
- L0-4: t(event productManager.ProductWritten) - t(event piCamera.CaptureStarted) >= 2 x (bench time of the triggered action - t(event piCamera.CaptureStarted)) (require, L3-1 and L3-2)
- L0-5: first frame line of the holder - its start <= 5 s (require, L5-2)
- L2-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench time of CAPTURE sent - 2 s <= capture time record of P1 <= its completion + 2 s
- L2-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480; picture record of P2 is JFIF, SOI to EOI, 640 x 480; sha256 of the picture records of P1 and P2 differ; bench time of the second CAPTURE sent - 2 s <= capture time record of P2 <= its completion + 2 s; capture time record of P2 > capture time record of P1
- L3-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L3-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L5-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L5-2: picture record of P1 is JFIF, SOI to EOI, 640 x 480
- L7-1: picture record of P1 is JFIF, SOI to EOI, 640 x 480; bench sha256 of the product file on board == sha256 of the ground file

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): camera_kept_absent (stimulus; L5-1); capture_after_restart_dropped (stimulus; L3-1); capture_twice (stimulus; L2-1); corrupt_picture (uut-state; L2-2).

## 7 Not covered
- REQ-PiCamera-003 to -013, -015, -018, -020 to -024: unit tests; the requester (`productManager`) sends one request at a time and returns every picture, so `BUSY`, `TIMEOUT`, `NO_BUFFER`, `PICTURE_OUTSTANDING`, `TOO_LARGE` and a rejected return cannot be forced on the bench.
- REQ-PiCamera-016: the build inputs are inspected; L0-2 judges the linked libraries only.
- A camera that stops answering during a capture (`TIMEOUT`) and a frame the library marks bad: not plantable on the bench without touching the ribbon cable under power.
- Picture content (exposure, focus).

## 8 Decision log
1. 2026-11-17 designer — the component is tested in the project's test deployment (full deployment + `sysTester`), not a reduced one.
2. 2026-11-17 designer — REQ-PiCamera-001 'acquired after its request' is judged by two captures giving different picture bytes and by the capture time record against bench time (tolerance 2 s, project decision D12).
3. 2026-11-17 designer — max planted faults per draw 2; menu covers L2-1, L2-2, L3-1, L5-1.
5. 2026-11-17 designer — `picture_is_jfif` decodes the picture record on the bench with Pillow 11 (`Image.load()`), an independent decoder: bytes 0-1 FFD8, APP0 `JFIF`, last two bytes FFD9 with nothing after, full decode without error or warning, 640 x 480.
6. 2026-11-17 designer — a restart window is split at its `sysTester.Started` row; the Pi clock is wall time, so a restart gives no clock backstep to split on.
4. 2026-11-17 designer — `BENCH_LINE(CAMERA, state)` is a bench line this plan needs from `sysTester`; reported to the parent campaign.
