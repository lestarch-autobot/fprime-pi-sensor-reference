# PiSensor system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)` (the deployment has no command with a free 32-bit argument that echoes). Event rate: at most 5 events per second in any window. Link budget [I]: RFM69 at the catalog default `DATA_RATE` 19200 bit/s (`Rfm69Manager.fpp`) carries 2400 byte/s, about nine 255-byte frames; Table 1 telemetry at 1 Hz and 5 events/s are estimated at under 800 byte/s, leaving 1600 byte/s for CFDP, so a 100 kB JPEG takes at least 60 s. The bench check at L0 replaces this estimate.
- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Test deployment (SSDD decision D13, the human's ruling): the full deployment plus the harness component `sysTester`. Constraint: without it there is no marker command, no on-board file hash, no directory listing outside `productManager` and no commandable bench line. Images named in the manifest `images[]`: `PiSensor-prototype` (TCP) and `PiSensor-flight` (RFM69).
- `sysTester` commands: `MARK(id)`, `PLATFORM()`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `BENCH_LINE(line, state)`, `CORRUPT_PRODUCT(name)`. `DUMP_SHA256` and `CORRUPT_PRODUCT` act on a named file of the product directory only; `pass` is echoed in the `Sha256` event. Design constraint sent to campaign `prodmgr`: a downlink does not check product content, so a corrupted product is sent as stored. Events: `Marker`, `Started` (once per process start), `Platform`, `DirListing`, `Sha256`. Channel `UptimeS` every second (always written).
- Ground system: fprime-yamcs at the ledger pin with the project YAMCS configuration directory (CFDP service).
- Order: the prototype block (L0-1 to L6-2, TCP) runs first; the flight block (L0-3, L2-9, L2-10, L5-16, L5-23, L7-1, RFM69) runs last. The switch is the bench action at the head of L0-3.
- Record content (`record/`): every exported row carries the ground reception time beside the FSW time; `record/raw/bench-actions.log` holds each bench action with its bench start and end time and, for the GPS source, its byte counter; every CFDP file received is copied to `record/raw/files/` before it is hashed; CFDP class and outcome come from the YAMCS transfer record exported to `record/raw/cfdp.json` and from the F Prime CFDP events; frames are recorded at `fprime-comm-bridge`, which stays up when YAMCS is stopped.
- Completeness: every window requires STD and the helper `no_frame_gaps` (no gap in the telemetry frame counter of the ground recorder); a dropped frame or an overflowed queue makes the window UNVERIFIED, never a pass of an absence check. `STD-OUT`, `STD-ERR` and `STD-RST` are completeness blocks used with `require`, not absence blocks (the plan format lists them with the absence blocks). The helper takes `{except: [interval]}`: `STD-OUT` (link, radio and ground-stack outages) has no overflow predicate and exempts frame gaps from the outage action to the return action; `STD-RST` (restart windows) exempts them from the action to the first `sysTester.Started`, and a frame counter that restarts at 0 directly before a `Started` event is a restart, any other discontinuity a gap; `STD-ERR` expects exactly one failed command. Outside the exempt interval the gap rule holds; no absence is judged inside it.
- Bench and Pi clocks: both synchronised by NTP; the offset is measured at L0-1 (`PLATFORM()` event time against bench time) and must be under 0.5 s; time tolerances that compare the two clocks use 2 s (SSDD decision D12).
- Validity channels (`TemperatureValid`, `AttitudeValid`, `FixValid`) are written every period, not on change; a window without samples of them fails.
- Out of scope: BMP280 pressure (decision D9); yaw.

## 1 Entry gates
- Component campaigns `sensmon`, `picam`, `prodmgr` closed; their unit tests pass.
- Images built from the manifest SHAs; L0-1, L0-2 and L0-3 pass on the bench.
- Product directory on its own 64 MB file system (loop-mounted image file, kept across a reboot), empty at the start of each test (bench teardown removes the products of the test; L7-1 has no teardown, its product stays for the final-state check). The fill and read-only actions touch only that file system.
- Bench recipe: BMP280, MPU6050, Pi Camera attached; bench line BMP280 = a switch on the BMP280 supply driven by a Pi GPIO; bench line MPU6050 = the same on the MPU6050 supply, with SDA and SCL isolated by the same switch so the unpowered part does not load I2C bus 1 (L0 bench confirmation: the other sensors still answer with each line off); a GPS sentence source (workstation USB serial adapter on the GPS UART, 9600 baud, driven by a bench script) in place of the receiver for every test but L2-1 and L2-2; ground Pi with RFM69 for the flight block, its radio supply switchable from the workstation.
- Privileges on `soakee` (none today: user `fprime` has no passwordless sudo): root for the service units, the reboot, the loop mount and remount, and the camera driver unbind. The TCP link block and the YAMCS and CFDP service actions run on the workstation and need none.

## 2 Test levels
L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L6 negative controls · L7 final state. No L4 endurance test: no requirement has an endurance bound.

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event sysTester.Started count == 0.
Standard absence block (STD-OUT): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; Heartbeat samples >= 2.
Standard absence block (STD-ERR): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 1; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (STD-RST): both markers present; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched; Table1 = sensorMonitor.Temperature, sensorMonitor.TemperatureValid, sensorMonitor.Roll, sensorMonitor.Pitch, sensorMonitor.AttitudeValid, sensorMonitor.GyroX, sensorMonitor.GyroY, sensorMonitor.GyroZ, sensorMonitor.Latitude, sensorMonitor.Longitude, sensorMonitor.Altitude, sensorMonitor.FixValid.

ID:        L0-1
Title:     Image and platform identity, prototype image
Purpose:   Proves the running image is the manifest's prototype image and runs on a Raspberry Pi 5 under Raspberry Pi OS 13, over TCP.
Covers:    REQ-PiSensor-042, REQ-PiSensor-016
Setup:     Prototype image running on the Raspberry Pi 5; link up.
Procedure: MARK(10); VERSION(ALL); PLATFORM(); bracket (2 Heartbeat samples); action: list TCP sockets of the deployment process; MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1). metrics: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  Version events equal the manifest describe strings; check: sysTester.Platform model starts with "Raspberry Pi 5" and os_version == 13; check: one TCP connection, to the bridge port.
Planted faults:none

ID:        L0-2
Title:     Marker round-trip
Purpose:   Proves the marker command round-trips so every later window can be bracketed.
Covers:    —
Setup:     As L0-1.
Procedure: MARK(20); bracket (2 Heartbeat samples); MARK(0xA5A5); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  Three Marker events in order, ids byte-exact.
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry period
Purpose:   Proves every Table 1 channel arrives at the ground at least every 2 s.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-016, REQ-PiSensor-017
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(30); wait 60 s; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: largest gap between ground reception times of every Table 1 channel in the window <= 2 s.
Evidence:  Channel strips over 60 s; check: every Table 1 channel has samples and all three validity channels read VALID.
Planted faults:none

ID:        L2-2
Title:     Sensor telemetry period under command traffic
Purpose:   Proves the 2 s telemetry period holds while commands are dispatched.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-016, REQ-PiSensor-017
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(32); NO_OP(); wait 10 s; NO_OP(); wait 10 s; NO_OP(); wait 10 s; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: largest gap between ground reception times of every Table 1 channel in the window <= 2 s.
Evidence:  As L2-1; check: event cmdDisp.NoOpReceived count == 3.
Planted faults:none

ID:        L2-3
Title:     Capture and downlink of one product
Purpose:   Proves one capture makes one product with a JPEG of at least 640x480 and valid, timed metrics, delivered byte-identical by CFDP class 2.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-010, REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-016, REQ-PiSensor-017
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(40); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_3). metrics: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; |sample time - capture time| <= 2 s for temperature, attitude and location.
Evidence:  check: event productManager.ProductWritten count == 1 (names P); check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; check: CFDP transaction of P at the ground is class 2 and finished complete; checks on the ground file: starts FFD8 and ends FFD9; SOF0 width >= 640 and height >= 480; one picture, location, attitude and temperature record; all three validity records VALID.
Planted faults:capture_twice

ID:        L2-4
Title:     Capture and downlink, repeated
Purpose:   Proves a second capture makes a new product with its own name and capture time, delivered byte-identical.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-010, REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-016, REQ-PiSensor-017
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(42); CAPTURE(); wait 5 s; CAPTURE(); DUMP_SHA256(P2, 1); DOWNLINK(P2); wait CFDP transaction finished at the ground; MARK(43).
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L2_4). metrics: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; |sample time - capture time| <= 2 s for temperature, attitude and location.
Evidence:  check: event productManager.ProductWritten count == 2 with different names; capture time of P2 later than the first; check: sha256 of record/raw/files/<P2> == hash in the sysTester.Sha256 event; class 2 check; checks on the ground file: starts FFD8 and ends FFD9; SOF0 width >= 640 and height >= 480; one picture, location, attitude and temperature record; all three validity records VALID.
Planted faults:none

ID:        L2-5
Title:     Downlink selects the named product
Purpose:   Proves a downlink command sends the product it names and no other.
Covers:    REQ-PiSensor-012, REQ-PiSensor-013
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(44); CAPTURE(); wait 5 s; CAPTURE(); DUMP_SHA256(P2, 1); DOWNLINK(P2); wait CFDP transaction finished at the ground; MARK(45).
Window:    Marker(id=44) … Marker(id=45)
Pass rule: named checks declared in the integration test (test_L2_5).
Evidence:  check: exactly one file arrived and its name is P2; check: sha256 of record/raw/files/<P2> == hash in the sysTester.Sha256 event; class 2 check.
Planted faults:corrupt_product

ID:        L2-6
Title:     Product content at the ground
Purpose:   Proves the picture and the three metric records of a product are intact in the ground copy.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(46); CAPTURE(); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(47).
Window:    Marker(id=46) … Marker(id=47)
Pass rule: named checks declared in the integration test (test_L2_6).
Evidence:  checks on the ground file: starts FFD8 and ends FFD9; SOF0 width >= 640 and height >= 480; one picture, location, attitude and temperature record; all three validity records VALID.
Planted faults:corrupt_product

ID:        L3-1
Title:     Process restart
Purpose:   Proves Table 1 telemetry resumes within 60 s of a process restart without ground commands and a stored product is still downlinkable, unchanged.
Covers:    REQ-PiSensor-038, REQ-PiSensor-039
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(70); CAPTURE(); DUMP_SHA256(P, 1); MARK(71); action: kill the deployment process (SIGKILL); the service unit restarts it; wait first Table 1 samples at the ground; MARK(72); PLATFORM(); DUMP_SHA256(P, 2); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(73).
Window:    W1 = Marker(id=70) … Marker(id=71); R = Marker(id=71) … Marker(id=72); W2 = Marker(id=72) … Marker(id=73)
Pass rule: named checks declared in the integration test (test_L3_1). metrics: first sample of every Table 1 channel - bench time of the action <= 60 s, no command sent between them; W2: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  R: check event sysTester.Started count == 1 and last(sysTester.UptimeS) < 60; W2: check the two Sha256 events are equal and sha256 of record/raw/files/<P> == hash in the first Sha256 event.
Planted faults:corrupt_before_second_hash

ID:        L3-2
Title:     Reboot
Purpose:   Proves Table 1 telemetry resumes within 60 s of a reboot without ground commands and a stored product is still downlinkable, unchanged.
Covers:    REQ-PiSensor-038, REQ-PiSensor-039
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(74); CAPTURE(); DUMP_SHA256(P, 1); MARK(75); action: reboot the Raspberry Pi; wait first Table 1 samples at the ground; MARK(76); PLATFORM(); DUMP_SHA256(P, 2); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(77).
Window:    W1 = Marker(id=74) … Marker(id=75); R = Marker(id=75) … Marker(id=76); W2 = Marker(id=76) … Marker(id=77)
Pass rule: named checks declared in the integration test (test_L3_2). metrics: first sample of every Table 1 channel - bench time of the action <= 60 s, no command sent between them; W2: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  R: check event sysTester.Started count == 1 and last(sysTester.UptimeS) < 60; W2: check the two Sha256 events are equal and sha256 of record/raw/files/<P> == hash in the first Sha256 event.
Planted faults:none

ID:        L3-3
Title:     Capture interrupted by a process kill
Purpose:   Proves a capture interrupted by a restart leaves no product, complete or partial.
Covers:    REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(80); LIST_DIR(products); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: kill the deployment process (SIGKILL), triggered by the CaptureStarted event; wait first Table 1 samples at the ground; LIST_DIR(products); LIST_PRODUCTS(); MARK(81).
Window:    Marker(id=80) … Marker(id=81)
Pass rule: named checks declared in the integration test (test_L3_3).
Evidence:  require (else UNVERIFIED, the race was lost): event piCamera.CaptureStarted count == 1 and event productManager.ProductWritten count == 0 before the action. An orderly stop that lets the capture finish is not allowed: the product count must be unchanged. `DirListing` carries file times: a new complete product older than the bench time of the action means the capture ended before the action (UNVERIFIED, not FAIL). L0 bench confirmation measures the capture duration against the trigger latency. check: event sysTester.Started count == 1; check: file names and count of the two sysTester.DirListing events are equal; check: event productManager.ProductWritten count == 0; product list empty.
Planted faults:none

ID:        L3-4
Title:     Capture interrupted by a service stop
Purpose:   Proves a capture interrupted by a restart leaves no product, complete or partial.
Covers:    REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(82); LIST_DIR(products); CAPTURE() without waiting for completion; wait event piCamera.CaptureStarted; action: stop and start the service unit (SIGTERM, then SIGKILL after the unit stop time of 2 s), triggered by the CaptureStarted event; wait first Table 1 samples at the ground; LIST_DIR(products); LIST_PRODUCTS(); MARK(83).
Window:    Marker(id=82) … Marker(id=83)
Pass rule: named checks declared in the integration test (test_L3_4).
Evidence:  require (else UNVERIFIED, the race was lost): event piCamera.CaptureStarted count == 1 and event productManager.ProductWritten count == 0 before the action. An orderly stop that lets the capture finish is not allowed: the product count must be unchanged. `DirListing` carries file times: a new complete product older than the bench time of the action means the capture ended before the action (UNVERIFIED, not FAIL). L0 bench confirmation measures the capture duration against the trigger latency. check: event sysTester.Started count == 1; check: file names and count of the two sysTester.DirListing events are equal; check: event productManager.ProductWritten count == 0; product list empty.
Planted faults:none

ID:        L5-1
Title:     BMP280 failure and return
Purpose:   Proves a failed BMP280 raises WARNING_HI within 10 s, temperature reads invalid, and it is valid again within 10 s of the return, without a restart.
Covers:    REQ-PiSensor-019, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(100); BENCH_LINE(BMP280, OFF); wait 15 s; MARK(101); BENCH_LINE(BMP280, ON); wait 15 s; MARK(102).
Window:    F = Marker(id=100) … Marker(id=101); B = Marker(id=101) … Marker(id=102)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.Bmp280Lost count == 1 (WARNING_HI), last(sensorMonitor.TemperatureValid) == INVALID, attitude and fix stay VALID. B: last(sensorMonitor.TemperatureValid) == VALID; both: event sysTester.Started count == 0.
Planted faults:sensor_line_kept_on

ID:        L5-2
Title:     BMP280 failure before a capture
Purpose:   Proves a BMP280 failed for 3 s is reported and its temperature is marked invalid in a product captured then.
Covers:    REQ-PiSensor-019, REQ-PiSensor-022, REQ-PiSensor-023, REQ-PiSensor-008
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(103); BENCH_LINE(BMP280, OFF); wait 3 s; CAPTURE(); wait 10 s; MARK(104); BENCH_LINE(BMP280, ON); wait 15 s; DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(105).
Window:    F = Marker(id=103) … Marker(id=104); B = Marker(id=104) … Marker(id=105)
Pass rule: named checks declared in the integration test (test_L5_2). metrics: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s.
Evidence:  As L5-1; ground file: temperature validity record INVALID, attitude and location VALID.
Planted faults:none

ID:        L5-3
Title:     MPU6050 failure and return
Purpose:   Proves a failed MPU6050 raises WARNING_HI within 10 s, attitude reads invalid, and it is valid again within 10 s of the return, without a restart.
Covers:    REQ-PiSensor-020, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(110); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(111); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(112).
Window:    F = Marker(id=110) … Marker(id=111); B = Marker(id=111) … Marker(id=112)
Pass rule: named checks declared in the integration test (test_L5_3). metrics: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.Mpu6050Lost count == 1 (WARNING_HI), last(sensorMonitor.AttitudeValid) == INVALID. B: VALID; both: event sysTester.Started count == 0.
Planted faults:sensor_line_kept_on

ID:        L5-4
Title:     MPU6050 failure twice
Purpose:   Proves the MPU6050 loss report and the recovery repeat on a second failure in the same run.
Covers:    REQ-PiSensor-020, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(113); BENCH_LINE(MPU6050, OFF); wait 15 s; BENCH_LINE(MPU6050, ON); wait 15 s; MARK(114); BENCH_LINE(MPU6050, OFF); wait 15 s; BENCH_LINE(MPU6050, ON); wait 15 s; MARK(115).
Window:    C1 = Marker(id=113) … Marker(id=114); C2 = Marker(id=114) … Marker(id=115)
Pass rule: named checks declared in the integration test (test_L5_4). metrics: each sensorMonitor.Mpu6050Lost - its BENCH_LINE(MPU6050, OFF) sent <= 10 s; first sensorMonitor.AttitudeValid == VALID after each return - time of the return <= 10 s.
Evidence:  Each window: check event sensorMonitor.Mpu6050Lost count == 1, last(sensorMonitor.AttitudeValid) == VALID, event sysTester.Started count == 0.
Planted faults:none

ID:        L5-5
Title:     GPS silence and return
Purpose:   Proves GPS silence raises WARNING_HI within 10 s, location reads invalid, and it is valid again within 10 s of the return, without a restart.
Covers:    REQ-PiSensor-021, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(120); action: stop the GPS sentence source; wait 15 s; MARK(121); action: restart the GPS sentence source (1 Hz, fix); wait 15 s; MARK(122).
Window:    F = Marker(id=120) … Marker(id=121); B = Marker(id=121) … Marker(id=122)
Pass rule: named checks declared in the integration test (test_L5_5). metrics: t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s; first sensorMonitor.FixValid == VALID after the restart action - bench time of the action <= 10 s.
Evidence:  F: check event sensorMonitor.GpsSilent count == 1 (WARNING_HI), last(sensorMonitor.FixValid) == INVALID; source byte counter in bench-actions.log does not advance. B: VALID; both: event sysTester.Started count == 0.
Planted faults:none

ID:        L5-6
Title:     GPS silence for 120 s
Purpose:   Proves a long GPS silence is reported once and recovery still takes at most 10 s.
Covers:    REQ-PiSensor-021, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(123); action: stop the GPS sentence source; wait 120 s; MARK(124); action: restart the GPS sentence source (1 Hz, fix); wait 15 s; MARK(125).
Window:    F = Marker(id=123) … Marker(id=124); B = Marker(id=124) … Marker(id=125)
Pass rule: named checks declared in the integration test (test_L5_6). metrics: t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s; first sensorMonitor.FixValid == VALID after the restart action - bench time of the action <= 10 s.
Evidence:  As L5-5 with one GpsSilent event over 120 s.
Planted faults:none

ID:        L5-7
Title:     GPS without a fix
Purpose:   Proves a receiver reporting no fix reads fix invalid, raises no silence event, and gives location invalid in a product.
Covers:    REQ-PiSensor-024, REQ-PiSensor-009
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(130); action: GPS source sends no-fix GGA sentences at 1 Hz; wait 10 s; CAPTURE(); DOWNLINK(P); wait CFDP transaction finished at the ground; action: GPS source sends fix sentences at 1 Hz; MARK(131).
Window:    Marker(id=130) … Marker(id=131)
Pass rule: named checks declared in the integration test (test_L5_7). metrics: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s (1 s GGA period + 2 s telemetry period + 2 s clock tolerance, decision D12; a test settling time, REQ-PiSensor-024 has no time bound), INVALID from then to the CAPTURE.
Evidence:  check: sensorMonitor.FixValid == INVALID from 3 s after the action to the CAPTURE; event sensorMonitor.GpsSilent count == 0; source byte counter advances; ground file: location validity record INVALID, temperature and attitude VALID.
Planted faults:none

ID:        L5-8
Title:     GPS fix lost and regained
Purpose:   Proves the no-fix indication clears when the fix returns and a product captured then has a valid location.
Covers:    REQ-PiSensor-024, REQ-PiSensor-009
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(132); action: GPS source sends no-fix GGA sentences at 1 Hz; wait 10 s; CAPTURE(); action: GPS source sends fix sentences at 1 Hz; wait 10 s; CAPTURE(); DOWNLINK(P1); DOWNLINK(P2); wait CFDP transactions finished at the ground; MARK(133).
Window:    Marker(id=132) … Marker(id=133)
Pass rule: named checks declared in the integration test (test_L5_8).
Evidence:  Ground files: location validity INVALID in P1 and VALID in P2; last(sensorMonitor.FixValid) == VALID; event sensorMonitor.GpsSilent count == 0.
Planted faults:none

ID:        L5-9
Title:     Stale attitude at capture
Purpose:   Proves attitude older than 2 s at capture is marked invalid in the product while the others stay valid.
Covers:    REQ-PiSensor-008
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(134); BENCH_LINE(MPU6050, OFF); wait 3 s; CAPTURE(); BENCH_LINE(MPU6050, ON); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(135).
Window:    Marker(id=134) … Marker(id=135)
Pass rule: named checks declared in the integration test (test_L5_9).
Evidence:  Ground file: attitude validity record INVALID, temperature and location VALID.
Planted faults:sensor_line_kept_on

ID:        L5-10
Title:     Stale location at capture
Purpose:   Proves a location older than 2 s at capture is marked invalid in the product while the others stay valid.
Covers:    REQ-PiSensor-008
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(136); action: stop the GPS sentence source; wait 3 s; CAPTURE(); action: restart the GPS sentence source (1 Hz, fix); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(137).
Window:    Marker(id=136) … Marker(id=137)
Pass rule: named checks declared in the integration test (test_L5_10).
Evidence:  Ground file: location validity record INVALID, temperature and attitude VALID.
Planted faults:none

ID:        L5-11
Title:     Camera absent
Purpose:   Proves a capture with the camera unavailable fails its command with WARNING_HI and leaves no file.
Covers:    REQ-PiSensor-028, REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(140); action: make the camera unavailable (unbind its driver); LIST_DIR(products); CAPTURE(); LIST_DIR(products); LIST_PRODUCTS(); action: make the camera available; MARK(141).
Window:    Marker(id=140) … Marker(id=141)
Pass rule: named checks declared in the integration test (test_L5_11).
Evidence:  check: CAPTURE completes with error; event productManager.CaptureFailed count == 1 (WARNING_HI); the two sysTester.DirListing events are equal; product list unchanged.
Planted faults:none

ID:        L5-12
Title:     Camera absent, then present
Purpose:   Proves a failed capture leaves no file and the next capture succeeds once the camera is back.
Covers:    REQ-PiSensor-028, REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(142); action: make the camera unavailable (unbind its driver); LIST_DIR(products); CAPTURE(); LIST_DIR(products); action: make the camera available; CAPTURE(); MARK(143).
Window:    Marker(id=142) … Marker(id=143)
Pass rule: named checks declared in the integration test (test_L5_12).
Evidence:  As L5-11, then event productManager.ProductWritten count == 1.
Planted faults:none

ID:        L5-13
Title:     Storage read-only
Purpose:   Proves a capture that cannot store its product fails its command with WARNING_HI and leaves no file.
Covers:    REQ-PiSensor-031, REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(144); action: remount the product file system read-only; LIST_DIR(products); CAPTURE(); action: remount the product file system read-write; LIST_DIR(products); MARK(145).
Window:    Marker(id=144) … Marker(id=145)
Pass rule: named checks declared in the integration test (test_L5_13).
Evidence:  check: CAPTURE completes with error; event productManager.StorageFailed count == 1 (WARNING_HI); the two DirListing events are equal.
Planted faults:none

ID:        L5-14
Title:     Storage full
Purpose:   Proves a capture with no free space fails its command with WARNING_HI and leaves no partial file.
Covers:    REQ-PiSensor-031, REQ-PiSensor-029
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(146); action: fill the product file system (64 MB, its own) with one bench file; LIST_DIR(products); CAPTURE(); LIST_DIR(products); action: remove the fill file; MARK(147).
Window:    Marker(id=146) … Marker(id=147)
Pass rule: named checks declared in the integration test (test_L5_14).
Evidence:  As L5-13; the two DirListing events (taken while full) are equal.
Planted faults:none

ID:        L5-15
Title:     CFDP transfer with no ground peer
Purpose:   Proves a transfer that makes no progress for 60 s ends with WARNING_HI and the product is unchanged and downlinkable afterwards.
Covers:    REQ-PiSensor-034, REQ-PiSensor-035
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(150); CAPTURE(); DUMP_SHA256(P, 1); action: stop the ground CFDP service; DOWNLINK(P); wait 95 s; action: start the ground CFDP service; DUMP_SHA256(P, 2); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(151).
Window:    Marker(id=150) … Marker(id=151)
Pass rule: named checks declared in the integration test (test_L5_15). metrics: 55 s <= t(event productManager.DownlinkStalled) - t(first productManager.DOWNLINK sent) <= 90 s.
Evidence:  check: event productManager.DownlinkStalled count == 1 (WARNING_HI); the two Sha256 events are equal; sha256 of record/raw/files/<P> == hash in the first Sha256 event.
Planted faults:corrupt_before_second_hash

ID:        L5-17
Title:     Link outage of 65 s
Purpose:   Proves commanding and telemetry resume within 10 s of the end of a 65 s link outage, without a restart, and a product stored before it is downlinkable.
Covers:    REQ-PiSensor-036, REQ-PiSensor-038
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(160); CAPTURE(); DUMP_SHA256(P, 1); action: block the TCP link at the workstation; wait 65 s; action: unblock the TCP link; NO_OP(); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(161).
Window:    Marker(id=160) … Marker(id=161)
Pass rule: named checks declared in the integration test (test_L5_17). metrics: gap of ground reception of Table 1 channels during the outage >= 60 s; first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 65; check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event.
Planted faults:none

ID:        L5-18
Title:     Link outage of 120 s
Purpose:   Proves recovery within 10 s from a longer link outage, without a restart.
Covers:    REQ-PiSensor-036
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(162); action: block the TCP link at the workstation; wait 120 s; action: unblock the TCP link; NO_OP(); MARK(163).
Window:    Marker(id=162) … Marker(id=163)
Pass rule: named checks declared in the integration test (test_L5_18). metrics: gap of ground reception of Table 1 channels during the outage >= 115 s; first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 120.
Planted faults:none

ID:        L5-19
Title:     Ground-system outage of 65 s
Purpose:   Proves commanding and telemetry resume within 10 s of the ground system's return, without a restart of the flight software, and a stored product is downlinkable.
Covers:    REQ-PiSensor-037, REQ-PiSensor-038
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(164); CAPTURE(); DUMP_SHA256(P, 1); action: stop the YAMCS server only (`fprime-comm-bridge`, run from its own command line, and the frame recorder stay up); wait 65 s; action: start the YAMCS server; NO_OP(); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(165).
Window:    Marker(id=164) … Marker(id=165)
Pass rule: named checks declared in the integration test (test_L5_19). metrics: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 65; check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event.
Planted faults:none

ID:        L5-20
Title:     Ground-system outage of 120 s
Purpose:   Proves recovery within 10 s from a longer ground-system outage, without a restart of the flight software.
Covers:    REQ-PiSensor-037
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(166); action: stop the whole ground stack (YAMCS server and `fprime-comm-bridge`); wait 120 s; action: start the whole ground stack; NO_OP(); MARK(167).
Window:    Marker(id=166) … Marker(id=167)
Pass rule: named checks declared in the integration test (test_L5_20). metrics: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 120.
Planted faults:none

ID:        L5-24
Title:     Ground-stack outage of 65 s
Purpose:   Proves the flight software reconnects and commanding and telemetry resume within 10 s after the whole ground stack, bridge included, was down for 65 s.
Covers:    REQ-PiSensor-037
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(168); action: stop the whole ground stack (YAMCS server and `fprime-comm-bridge`); wait 65 s; action: start the whole ground stack; NO_OP(); MARK(169).
Window:    Marker(id=168) … Marker(id=169)
Pass rule: named checks declared in the integration test (test_L5_24). metrics: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 65.
Planted faults:none

ID:        L5-21
Title:     NMEA sentence with a bad checksum
Purpose:   Proves a sentence with a bad checksum is discarded and the next good sentence is used.
Covers:    REQ-PiSensor-025
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(170); action: GPS source sends position A (48.1173 N, 11.5167 E) at 1 Hz for 5 s; action: GPS source sends position B (10.0000 N, 20.0000 E) with checksum + 1, at 1 Hz for 5 s; action: GPS source sends position C (48.2000 N, 11.6000 E) at 1 Hz for 5 s; MARK(171).
Window:    Marker(id=170) … Marker(id=171)
Pass rule: named checks declared in the integration test (test_L5_21).
Evidence:  check: latitude samples take the values of A then C and never B; source byte counter in bench-actions.log advanced by all 15 sentences; event sensorMonitor.GpsSilent count == 0.
Planted faults:none

ID:        L5-22
Title:     Bad checksums between good sentences
Purpose:   Proves bad-checksum sentences interleaved with good ones never change the reported position.
Covers:    REQ-PiSensor-025
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(172); action: GPS source alternates position A (48.1173 N, 11.5167 E) (good) and position B (10.0000 N, 20.0000 E) (checksum + 1), 1 Hz each, for 10 s; action: GPS source sends position C (48.2000 N, 11.6000 E) at 1 Hz for 5 s; MARK(173).
Window:    Marker(id=172) … Marker(id=173)
Pass rule: named checks declared in the integration test (test_L5_22).
Evidence:  check: latitude samples take the values of A then C and never B; byte counter advanced by all 25 sentences; event sensorMonitor.GpsSilent count == 0.
Planted faults:none

ID:        L6-1
Title:     Corrupted uplink frame
Purpose:   Proves an uplink frame that fails its frame check dispatches no command and an intact command still does.
Covers:    REQ-PiSensor-027
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(180); action: inject one NO_OP frame with bit 0 of its last data byte flipped, at the bridge; wait 5 s; NO_OP(); MARK(181).
Window:    Marker(id=180) … Marker(id=181)
Pass rule: named checks declared in the integration test (test_L6_1).
Evidence:  check: event tcDeframer.InvalidCrc count == 1; event cmdDisp.NoOpReceived count == 1.
Planted faults:none

ID:        L6-2
Title:     Corrupted uplink frames, burst
Purpose:   Proves five corrupted frames dispatch nothing and commanding works after them.
Covers:    REQ-PiSensor-027
Setup:     Prototype image running, link up, all four sensors answering, product directory empty.
Procedure: MARK(182); action: inject 5 NO_OP frames with the frame check field + 1, at the bridge; wait 5 s; NO_OP(); MARK(183).
Window:    Marker(id=182) … Marker(id=183)
Pass rule: named checks declared in the integration test (test_L6_2).
Evidence:  check: event tcDeframer.InvalidCrc count == 5; event cmdDisp.NoOpReceived count == 1.
Planted faults:none

ID:        L0-3
Title:     Image and platform identity, flight image
Purpose:   Proves the flight image is the manifest's and the marker round-trips over the RFM69.
Covers:    REQ-PiSensor-042, REQ-PiSensor-015
Setup:     action before the window: stop the prototype service unit, start the flight service unit. Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(200); VERSION(ALL); PLATFORM(); MARK(0x5A5A); bracket (2 Heartbeat samples); action: list TCP sockets of the deployment process; MARK(201).
Window:    Marker(id=200) … Marker(id=201)
Pass rule: named checks declared in the integration test (test_L0_3). metrics: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require).
Evidence:  Version events equal the manifest describe strings of the flight image; Platform check as L0-1; marker ids byte-exact; socket list empty.
Planted faults:none

ID:        L2-9
Title:     Flight configuration: telemetry, capture, downlink
Purpose:   Proves commands, telemetry, events and a CFDP file pass over the RFM69, with the 2 s period outside the downlink and the 10 s period during it.
Covers:    REQ-PiSensor-015, REQ-PiSensor-017, REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-018
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(210); wait 30 s; CAPTURE(); DUMP_SHA256(P, 1); MARK(211); DOWNLINK(P); wait CFDP transaction finished at the ground; action: list TCP sockets of the deployment process; MARK(212).
Window:    Q = Marker(id=210) … Marker(id=211); D = Marker(id=211) … Marker(id=212)
Pass rule: named checks declared in the integration test (test_L2_9). metrics: largest gap between ground reception times of every Table 1 channel in the first 30 s of Q <= 2 s; largest gap between ground reception times of every Table 1 channel in D <= 10 s; CFDP transaction duration in D >= 30 s (a precondition (require): a downlink shorter than 30 s cannot show the 10 s bound).
Evidence:  check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; class 2 check; socket list empty.
Planted faults:corrupt_product

ID:        L2-10
Title:     Flight configuration, repeated
Purpose:   Proves a second capture and downlink pass over the RFM69 with telemetry continuing.
Covers:    REQ-PiSensor-015, REQ-PiSensor-017, REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-018
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(213); CAPTURE(); DUMP_SHA256(P, 1); MARK(214); DOWNLINK(P); wait 15 s; NO_OP(); wait CFDP transaction finished at the ground; action: list TCP sockets of the deployment process; MARK(215).
Window:    Q = Marker(id=213) … Marker(id=214); D = Marker(id=214) … Marker(id=215)
Pass rule: named checks declared in the integration test (test_L2_10). metrics: largest gap between ground reception times of every Table 1 channel in D <= 10 s; CFDP transaction duration in D >= 30 s (as L2-9).
Evidence:  check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; class 2 check; event cmdDisp.NoOpReceived count == 1 during the downlink; socket list empty.
Planted faults:none

ID:        L5-16
Title:     CFDP transfer cut mid-file
Purpose:   Proves a transfer cut after it started ends with WARNING_HI and a repeated downlink delivers the product unchanged.
Covers:    REQ-PiSensor-034, REQ-PiSensor-035
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(220); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P); wait first file data PDU at the ground; action: power off the ground radio; wait 95 s; action: power on the ground radio; DUMP_SHA256(P, 2); DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(221).
Window:    Marker(id=220) … Marker(id=221)
Pass rule: named checks declared in the integration test (test_L5_16). metrics: 55 s <= t(event productManager.DownlinkStalled) - bench time of the power-off action <= 90 s.
Evidence:  check: first transaction incomplete at the power-off (require); event productManager.DownlinkStalled count == 1; the two Sha256 events are equal; sha256 of record/raw/files/<P> == hash in the first Sha256 event.
Planted faults:none

ID:        L5-23
Title:     Link outage of 65 s, flight configuration
Purpose:   Proves commanding and telemetry resume within 10 s of the end of a radio outage, without a restart.
Covers:    REQ-PiSensor-036
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(222); action: power off the ground radio; wait 65 s; action: power on the ground radio; NO_OP(); MARK(223).
Window:    Marker(id=222) … Marker(id=223)
Pass rule: named checks declared in the integration test (test_L5_23). metrics: gap of ground reception of Table 1 channels during the outage >= 60 s; first Table 1 sample received and NO_OP completion - bench time the ground radio is ready <= 10 s.
Evidence:  check: event sysTester.Started count == 0; delta(sysTester.UptimeS) > 65.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board for the independent final-state check.
Covers:    REQ-PiSensor-013, REQ-PiSensor-005
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, all four sensors answering, product directory empty.
Procedure: MARK(230); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P); wait CFDP transaction finished at the ground; LIST_DIR(products); MARK(231).
Window:    Marker(id=230) … Marker(id=231)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; checks on the ground file: starts FFD8 and ends FFD9; SOF0 width >= 640 and height >= 480; one picture, location, attitude and temperature record; all three validity records VALID; DirListing names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-PiSensor-001 | L2-1, L2-2, L2-9 |  |
| REQ-PiSensor-002 | L2-1, L2-2, L2-9 |  |
| REQ-PiSensor-003 | L2-1, L2-2, L2-9 |  |
| REQ-PiSensor-004 | L2-3, L2-4, L2-6 |  |
| REQ-PiSensor-005 | L2-3, L2-4, L2-6, L7-1 |  |
| REQ-PiSensor-006 | L2-3, L2-4 |  |
| REQ-PiSensor-007 | L2-3, L2-4 |  |
| REQ-PiSensor-008 | L5-2, L5-9, L5-10 |  |
| REQ-PiSensor-009 | L5-7, L5-8 |  |
| REQ-PiSensor-010 | L2-3, L2-4 |  |
| REQ-PiSensor-011 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-012 | L2-3, L2-4, L2-5, L2-9, L2-10 |  |
| REQ-PiSensor-013 | L2-3, L2-4, L2-5, L2-9, L2-10, L7-1 |  |
| REQ-PiSensor-014 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-015 | L0-3, L2-9, L2-10 |  |
| REQ-PiSensor-016 | L0-1, L2-1, L2-2, L2-3, L2-4 |  |
| REQ-PiSensor-017 | L2-1, L2-2, L2-3, L2-4, L2-9, L2-10 |  |
| REQ-PiSensor-018 | L2-9, L2-10 |  |
| REQ-PiSensor-019 | L5-1, L5-2 |  |
| REQ-PiSensor-020 | L5-3, L5-4 |  |
| REQ-PiSensor-021 | L5-5, L5-6 |  |
| REQ-PiSensor-022 | L5-1, L5-2, L5-3, L5-4, L5-5, L5-6 |  |
| REQ-PiSensor-023 | L5-1, L5-2, L5-3, L5-4, L5-5, L5-6 |  |
| REQ-PiSensor-024 | L5-7, L5-8 |  |
| REQ-PiSensor-025 | L5-21, L5-22 |  |
| REQ-PiSensor-026 | waived: UT only | decision D11: unit test for the unchanged catalog BMP280 manager, written in the base-deployment lane; a real BMP280 cannot return a wrong identity value |
| REQ-PiSensor-027 | L6-1, L6-2 |  |
| REQ-PiSensor-028 | L5-11, L5-12 |  |
| REQ-PiSensor-029 | L3-3, L3-4, L5-11, L5-12, L5-13, L5-14 |  |
| REQ-PiSensor-030 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-031 | L5-13, L5-14 |  |
| REQ-PiSensor-032 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-033 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-034 | L5-15, L5-16 |  |
| REQ-PiSensor-035 | L5-15, L5-16 |  |
| REQ-PiSensor-036 | L5-17, L5-18, L5-23 |  |
| REQ-PiSensor-037 | L5-19, L5-20, L5-24 |  |
| REQ-PiSensor-038 | L3-1, L3-2, L5-17, L5-19 |  |
| REQ-PiSensor-039 | L3-1, L3-2 |  |
| REQ-PiSensor-040 | waived: Inspection (delegated: picam) | component row of a NEW element |
| REQ-PiSensor-041 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-042 | L0-1, L0-3 |  |
| REQ-PiSensor-043 | waived: Component test (delegated: sensmon) | component row of a NEW element |

## 5 Metrics
- L0-1: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L2-1: largest gap between ground reception times of every Table 1 channel in the window <= 2 s
- L2-2: largest gap between ground reception times of every Table 1 channel in the window <= 2 s
- L2-3: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; |sample time - capture time| <= 2 s for temperature, attitude and location
- L2-4: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s; bench time of CAPTURE sent - 2 s <= capture time record <= time of CAPTURE completion + 2 s; |sample time - capture time| <= 2 s for temperature, attitude and location
- L3-1: first sample of every Table 1 channel - bench time of the action <= 60 s, no command sent between them; W2: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L3-2: first sample of every Table 1 channel - bench time of the action <= 60 s, no command sent between them; W2: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L5-1: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s
- L5-2: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s
- L5-3: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s
- L5-4: each sensorMonitor.Mpu6050Lost - its BENCH_LINE(MPU6050, OFF) sent <= 10 s; first sensorMonitor.AttitudeValid == VALID after each return - time of the return <= 10 s
- L5-5: t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s; first sensorMonitor.FixValid == VALID after the restart action - bench time of the action <= 10 s
- L5-6: t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s; first sensorMonitor.FixValid == VALID after the restart action - bench time of the action <= 10 s
- L5-7: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s (1 s GGA period + 2 s telemetry period + 2 s clock tolerance, decision D12; a test settling time, REQ-PiSensor-024 has no time bound), INVALID from then to the CAPTURE
- L5-15: 55 s <= t(event productManager.DownlinkStalled) - t(first productManager.DOWNLINK sent) <= 90 s
- L5-17: gap of ground reception of Table 1 channels during the outage >= 60 s; first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s
- L5-18: gap of ground reception of Table 1 channels during the outage >= 115 s; first Table 1 sample received and NO_OP completion - bench time of the unblock action <= 10 s
- L5-19: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s
- L5-20: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s
- L5-24: first Table 1 sample received by YAMCS and NO_OP completion - bench time YAMCS reports ready <= 10 s
- L0-3: |Pi clock - bench clock| <= 0.5 s, measured by a bench action (`date` over ssh, logged in bench-actions.log) (require)
- L2-9: largest gap between ground reception times of every Table 1 channel in the first 30 s of Q <= 2 s; largest gap between ground reception times of every Table 1 channel in D <= 10 s; CFDP transaction duration in D >= 30 s
- L2-10: largest gap between ground reception times of every Table 1 channel in D <= 10 s; CFDP transaction duration in D >= 30 s
- L5-16: 55 s <= t(event productManager.DownlinkStalled) - bench time of the power-off action <= 90 s
- L5-23: gap of ground reception of Table 1 channels during the outage >= 60 s; first Table 1 sample received and NO_OP completion - bench time the ground radio is ready <= 10 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): capture_twice (stimulus; L2-3); corrupt_before_second_hash (uut-state; L3-1, L5-15); corrupt_product (uut-state; L2-5, L2-6, L2-9); sensor_line_kept_on (stimulus; L5-1, L5-3, L5-9).

## 7 Not covered
- delegated: prodmgr — REQ-PiSensor-011, -014, -030, -032, -033, -041 (component rows of `productManager`).
- delegated: sensmon — REQ-PiSensor-043 (component row of `sensorMonitor`).
- delegated: picam — REQ-PiSensor-040 (inspection of the camera library).
- REQ-PiSensor-026: unit test only (decision D11).
- A sensor fault is planted by removing the sensor's supply or its sentence stream; a sensor that answers with wrong data is not planted.
- REQ-PiSensor-008 at its 2 s boundary: the tests use 3 s; a case just under 2 s is not run because the bench action timing error is of the size of the margin. The boundary is a unit test of `productManager`.
- REQ-PiSensor-037: L5-19 stops the YAMCS server only (requires STD; the flight software sees no outage, so it shows ground-side recovery only). L5-20 stops the bridge too; the flight software loses its TCP peer and must reconnect (requires STD-OUT).
- REQ-PiSensor-018 over TCP: a file finishes in about a second, so the bound is tested in the flight block only.
- Radio interference and range: the RFM69 link is tested at bench range only.
- Today's bench cannot run these tests: the BMP280 and GPS receiver do not answer (L2-1, L2-2 and every test whose setup needs four sensors), and the bench lines, the GPS sentence source, the camera, the ground Pi and root on `soakee` are absent.

## 8 Decision log
1. 2026-11-17 designer — test deployment = full deployment + `sysTester`; proposed to the human as SSDD decision D13.
2. 2026-11-17 designer — product content and identity are judged on the ground copy of the file; `DUMP_SHA256` gives the on-board hash and the bench `sha256sum` the independent final state.
3. 2026-11-17 designer — GPS faults are planted with a bench sentence source in place of the receiver; the receiver itself is used in L2-1 and L2-2.
4. 2026-11-17 designer — corrupted uplink frames are injected at `fprime-comm-bridge` by a bench script; the intact command that follows is sent by the harness.
5. 2026-11-17 designer, review round 1 — a restart is judged by `sysTester.Started` and `UptimeS`, not by a clock epoch: the time source is the Pi system clock, which does not step back. All windows are `reset: false`.
6. 2026-11-17 designer, review round 1 — planted faults rewrite or insert commands only; bench actions that a fault must change are `sysTester.BENCH_LINE` commands. Tests whose fault stimulus is a bench script carry no planted fault.
7. 2026-11-17 designer, review round 1 — every test makes its own product; no test depends on a product of another test.
