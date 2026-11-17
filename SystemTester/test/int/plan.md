# PiSensor system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending (marker `sysTester.MARK(U32)`; event rate at most 5 per second against a 255-byte RFM69 frame).
- UUT: the PiSensor deployment of `docs/ssdd.md` on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Ground system: fprime-yamcs at the ledger pin, with the project YAMCS configuration directory (CFDP service).
- Prototype configuration (TCP through `fprime-comm-bridge`) for every test except L2-9 and L2-10, which run the flight configuration over the RFM69.
- Out of scope: BMP280 pressure (decision D9); yaw.

## 1 Entry gates
- Component campaigns `sensmon`, `picam`, `prodmgr` closed; their unit tests pass.
- Images built from the manifest SHAs; L0-1 and L0-2 pass on the bench.
- Event rate fits the downlink: at most 5 events per second in any window.
- Bench recipe: BMP280, MPU6050, GPS sentence source and Pi Camera attached; bench switches for the BMP280 chip select and the MPU6050 bus; ground Pi with RFM69 for L2-9 and L2-10.

## 2 Test levels
L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L6 negative controls · L7 final state. No L4 endurance test: no requirement has an endurance bound.

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; Sensors samples >= 2.
Standard absence block (ABS): event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0.
Packets (named channel sets for `<packet> samples >= n`): Sensors = sensorMonitor.Temperature, sensorMonitor.Roll, sensorMonitor.Pitch, sensorMonitor.Latitude, sensorMonitor.Longitude.

ID:        L0-1
Title:     Image identity
Purpose:   Proves the running image is the one named in the manifest.
Covers:    REQ-PiSensor-042
Setup:     Deployment running on the Raspberry Pi 5; link up.
Procedure: MARK(10); VERSION(ALL); bracket (2 Sensors samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  Version events equal to the manifest describe strings; board model and OS release in the run record.
Planted faults:none

ID:        L0-2
Title:     Marker round-trip
Purpose:   Proves the marker command round-trips so every later window can be bracketed.
Covers:    —
Setup:     As L0-1.
Procedure: MARK(20); bracket (2 Sensors samples); MARK(0xA5A5); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  Three Marker events in order.
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry period
Purpose:   Proves temperature, attitude and location telemetry each arrive at the ground at least every 2 s.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-016, REQ-PiSensor-017, REQ-PiSensor-042
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(30); wait 60 s; MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1).
Evidence:  Channel strips over 60 s; check: largest gap between ground receipt times of temperature, attitude and location samples <= 2 s.
Planted faults:period_window_cut

ID:        L2-2
Title:     Sensor telemetry period, repeated after commanding
Purpose:   Proves the 2 s telemetry period holds again after command traffic.
Covers:    REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-016, REQ-PiSensor-017
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(32); NO_OP(); NO_OP(); NO_OP(); wait 30 s; MARK(33).
Window:    Marker(id=32) … Marker(id=33)
Pass rule: named checks declared in the integration test (test_L2_2).
Evidence:  Channel strips over 30 s; same 2 s gap check; three NoOpReceived events.
Planted faults:none

ID:        L2-3
Title:     Capture makes one correlated product
Purpose:   Proves one capture command makes one product holding a JPEG of at least 640x480 and valid, timed metrics.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-010
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(40); CAPTURE(); bracket (2 Sensors samples); MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_3). metrics: t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s.
Evidence:  ProductWritten event naming the file; product records read from the downlinked copy in L2-5.
Planted faults:capture_twice

ID:        L2-4
Title:     Second capture makes a second product
Purpose:   Proves a later capture makes a new product with its own capture time and fresh metrics.
Covers:    REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007, REQ-PiSensor-010
Setup:     As L2-3, one product stored.
Procedure: MARK(42); CAPTURE(); bracket (2 Sensors samples); MARK(43).
Window:    Marker(id=42) … Marker(id=43)
Pass rule: named checks declared in the integration test (test_L2_4). metrics: t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s.
Evidence:  Second ProductWritten event with a different name; records read from the downlinked copy in L2-6.
Planted faults:none

ID:        L2-5
Title:     Downlink of the first product
Purpose:   Proves a downlink command delivers the named product by CFDP class 2, byte-identical, to fprime-yamcs.
Covers:    REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-016, REQ-PiSensor-017, REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007
Setup:     Product of L2-3 stored.
Procedure: MARK(50); DOWNLINK(product of L2-3); wait CFDP transfer finished; DUMP_SHA256(product of L2-3); MARK(51).
Window:    Marker(id=50) … Marker(id=51)
Pass rule: named checks declared in the integration test (test_L2_5).
Evidence:  CFDP class 2 transaction finished at YAMCS; ground file sha256 equals the on-board sha256 event; product records decoded from the ground file.
Planted faults:downlink_other_product

ID:        L2-6
Title:     Downlink of the second product
Purpose:   Proves a second downlink delivers the second product byte-identical.
Covers:    REQ-PiSensor-012, REQ-PiSensor-013, REQ-PiSensor-016, REQ-PiSensor-017, REQ-PiSensor-004, REQ-PiSensor-005, REQ-PiSensor-006, REQ-PiSensor-007
Setup:     Product of L2-4 stored.
Procedure: MARK(52); DOWNLINK(product of L2-4); wait CFDP transfer finished; DUMP_SHA256(product of L2-4); MARK(53).
Window:    Marker(id=52) … Marker(id=53)
Pass rule: named checks declared in the integration test (test_L2_6).
Evidence:  As L2-5 for the second product.
Planted faults:none

ID:        L2-7
Title:     Telemetry during a downlink
Purpose:   Proves sensor telemetry still arrives at least every 10 s while a product is downlinked.
Covers:    REQ-PiSensor-018
Setup:     One product stored.
Procedure: MARK(54); CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; MARK(55).
Window:    Marker(id=54) … Marker(id=55)
Pass rule: named checks declared in the integration test (test_L2_7).
Evidence:  Channel strips between the CFDP start and finish events; check: largest gap <= 10 s.
Planted faults:period_window_cut

ID:        L2-8
Title:     Telemetry during a second downlink
Purpose:   Proves the 10 s telemetry bound holds during a repeated downlink of a stored product.
Covers:    REQ-PiSensor-018
Setup:     Product of L2-7 stored.
Procedure: MARK(56); DOWNLINK(product of L2-7); wait CFDP transfer finished; MARK(57).
Window:    Marker(id=56) … Marker(id=57)
Pass rule: named checks declared in the integration test (test_L2_8).
Evidence:  As L2-7.
Planted faults:none

ID:        L2-9
Title:     Flight configuration over the RFM69
Purpose:   Proves commands, telemetry, events and a CFDP file pass over the RFM69 with no TCP socket open on the Pi.
Covers:    REQ-PiSensor-015, REQ-PiSensor-017, REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-012, REQ-PiSensor-013
Setup:     Flight image running; ground Pi with RFM69 and groundRadio up.
Procedure: MARK(60); NO_OP(); CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; action: list TCP sockets of the deployment process; MARK(61).
Window:    Marker(id=60) … Marker(id=61)
Pass rule: named checks declared in the integration test (test_L2_9).
Evidence:  Command response, channel samples, events and file at the ground; socket list empty.
Planted faults:downlink_other_product

ID:        L2-10
Title:     Flight configuration, repeated
Purpose:   Proves the RFM69 path carries a second command, telemetry and file exchange.
Covers:    REQ-PiSensor-015, REQ-PiSensor-017, REQ-PiSensor-001, REQ-PiSensor-002, REQ-PiSensor-003, REQ-PiSensor-012, REQ-PiSensor-013
Setup:     As L2-9.
Procedure: MARK(62); NO_OP(); DOWNLINK(product of L2-9); wait CFDP transfer finished; action: list TCP sockets of the deployment process; MARK(63).
Window:    Marker(id=62) … Marker(id=63)
Pass rule: named checks declared in the integration test (test_L2_10).
Evidence:  As L2-9.
Planted faults:none

ID:        L3-1
Title:     Process restart
Purpose:   Proves sensor telemetry resumes within 60 s of a process restart without commands and a stored product is still downlinkable.
Covers:    REQ-PiSensor-038, REQ-PiSensor-039
Setup:     One product stored.
Procedure: MARK(70); action: kill the deployment process; wait telemetry; MARK(71); DOWNLINK(stored product); wait CFDP transfer finished; MARK(72).
Window:    R = Marker(id=70) … Marker(id=71) (reset window); W2 = Marker(id=71) … Marker(id=72)
Pass rule: named checks declared in the integration test (test_L3_1).
Evidence:  Clock restart; first Sensors sample within 60 s with no command before it; ground file sha256 equals the pre-restart sha256.
Planted faults:none

ID:        L3-2
Title:     Reboot
Purpose:   Proves sensor telemetry resumes within 60 s of a reboot without commands and a stored product is still downlinkable.
Covers:    REQ-PiSensor-038, REQ-PiSensor-039
Setup:     One product stored.
Procedure: MARK(73); action: reboot the Raspberry Pi; wait telemetry; MARK(74); DOWNLINK(stored product); wait CFDP transfer finished; MARK(75).
Window:    R = Marker(id=73) … Marker(id=74) (reset window); W2 = Marker(id=74) … Marker(id=75)
Pass rule: named checks declared in the integration test (test_L3_2).
Evidence:  As L3-1 after a reboot.
Planted faults:none

ID:        L5-1
Title:     BMP280 failure and return
Purpose:   Proves a failed BMP280 raises WARNING_HI within 10 s, its metric reads invalid, and telemetry resumes within 10 s of its return.
Covers:    REQ-PiSensor-019, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(100); action: hold the BMP280 chip select inactive (bench switch); wait 15 s; MARK(101); action: release the BMP280 chip select; wait 15 s; MARK(102).
Window:    F = Marker(id=100) … Marker(id=101); B = Marker(id=101) … Marker(id=102)
Pass rule: named checks declared in the integration test (test_L5_1).
Evidence:  sensorMonitor.Bmp280Lost event within 10 s of the action; sensorMonitor.TemperatureValid invalid in F, valid within 10 s in B; no clock restart.
Planted faults:skip_sensor_off

ID:        L5-2
Title:     BMP280 failure and return, repeated
Purpose:   Proves the BMP280 loss report and recovery repeat on a second failure.
Covers:    REQ-PiSensor-019, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(103); action: hold the BMP280 chip select inactive (bench switch); wait 15 s; MARK(104); action: release the BMP280 chip select; wait 15 s; MARK(105).
Window:    F = Marker(id=103) … Marker(id=104); B = Marker(id=104) … Marker(id=105)
Pass rule: named checks declared in the integration test (test_L5_2).
Evidence:  As L5-1.
Planted faults:none

ID:        L5-3
Title:     MPU6050 failure and return
Purpose:   Proves a failed MPU6050 raises WARNING_HI within 10 s, its metric reads invalid, and telemetry resumes within 10 s of its return.
Covers:    REQ-PiSensor-020, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(110); action: disconnect the MPU6050 from the I2C bus (bench switch); wait 15 s; MARK(111); action: reconnect the MPU6050; wait 15 s; MARK(112).
Window:    F = Marker(id=110) … Marker(id=111); B = Marker(id=111) … Marker(id=112)
Pass rule: named checks declared in the integration test (test_L5_3).
Evidence:  sensorMonitor.Mpu6050Lost event within 10 s of the action; sensorMonitor.AttitudeValid invalid in F, valid within 10 s in B; no clock restart.
Planted faults:skip_sensor_off

ID:        L5-4
Title:     MPU6050 failure and return, repeated
Purpose:   Proves the MPU6050 loss report and recovery repeat on a second failure.
Covers:    REQ-PiSensor-020, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(113); action: disconnect the MPU6050 from the I2C bus (bench switch); wait 15 s; MARK(114); action: reconnect the MPU6050; wait 15 s; MARK(115).
Window:    F = Marker(id=113) … Marker(id=114); B = Marker(id=114) … Marker(id=115)
Pass rule: named checks declared in the integration test (test_L5_4).
Evidence:  As L5-3.
Planted faults:none

ID:        L5-5
Title:     GPS failure and return
Purpose:   Proves a failed GPS raises WARNING_HI within 10 s, its metric reads invalid, and telemetry resumes within 10 s of its return.
Covers:    REQ-PiSensor-021, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(120); action: stop the GPS sentence source; wait 15 s; MARK(121); action: restart the GPS sentence source; wait 15 s; MARK(122).
Window:    F = Marker(id=120) … Marker(id=121); B = Marker(id=121) … Marker(id=122)
Pass rule: named checks declared in the integration test (test_L5_5).
Evidence:  sensorMonitor.GpsSilent event within 10 s of the action; sensorMonitor.LocationValid invalid in F, valid within 10 s in B; no clock restart.
Planted faults:skip_sensor_off

ID:        L5-6
Title:     GPS failure and return, repeated
Purpose:   Proves the GPS loss report and recovery repeat on a second failure.
Covers:    REQ-PiSensor-021, REQ-PiSensor-022, REQ-PiSensor-023
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(123); action: stop the GPS sentence source; wait 15 s; MARK(124); action: restart the GPS sentence source; wait 15 s; MARK(125).
Window:    F = Marker(id=123) … Marker(id=124); B = Marker(id=124) … Marker(id=125)
Pass rule: named checks declared in the integration test (test_L5_6).
Evidence:  As L5-5.
Planted faults:none

ID:        L5-7
Title:     GPS without a fix
Purpose:   Proves a receiver reporting no fix reads fix invalid in telemetry and location invalid in a captured product.
Covers:    REQ-PiSensor-024, REQ-PiSensor-009
Setup:     GPS sentence source set to no fix.
Procedure: MARK(130); action: GPS source sends no-fix sentences; wait 10 s; CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; action: GPS source sends fix sentences; MARK(131).
Window:    Marker(id=130) … Marker(id=131)
Pass rule: named checks declared in the integration test (test_L5_7).
Evidence:  FixValid channel invalid with no GpsSilent event; location validity record invalid in the ground file.
Planted faults:gps_keep_fix

ID:        L5-8
Title:     GPS without a fix, repeated
Purpose:   Proves the no-fix indication repeats and clears when the fix returns.
Covers:    REQ-PiSensor-024, REQ-PiSensor-009
Setup:     As L5-7.
Procedure: MARK(132); action: GPS source sends no-fix sentences; wait 10 s; CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; action: GPS source sends fix sentences; wait 10 s; MARK(133).
Window:    Marker(id=132) … Marker(id=133)
Pass rule: named checks declared in the integration test (test_L5_8).
Evidence:  As L5-7; FixValid valid again at the end.
Planted faults:none

ID:        L5-9
Title:     Stale metric at capture
Purpose:   Proves a metric older than 2 s at capture is marked invalid in the product while the others stay valid.
Covers:    REQ-PiSensor-008
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(134); action: disconnect the MPU6050 from the I2C bus (bench switch); wait 5 s; CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; action: reconnect the MPU6050; MARK(135).
Window:    Marker(id=134) … Marker(id=135)
Pass rule: named checks declared in the integration test (test_L5_9).
Evidence:  Attitude validity record invalid, temperature and location valid, in the ground file.
Planted faults:skip_sensor_off

ID:        L5-10
Title:     Stale location at capture
Purpose:   Proves a location older than 2 s at capture is marked invalid in the product.
Covers:    REQ-PiSensor-008
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(136); action: stop the GPS sentence source; wait 5 s; CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; action: restart the GPS sentence source; MARK(137).
Window:    Marker(id=136) … Marker(id=137)
Pass rule: named checks declared in the integration test (test_L5_10).
Evidence:  Location validity record invalid, temperature and attitude valid, in the ground file.
Planted faults:none

ID:        L5-11
Title:     Camera absent
Purpose:   Proves a capture with the camera unavailable fails its command with WARNING_HI and leaves no product.
Covers:    REQ-PiSensor-028, REQ-PiSensor-029
Setup:     Camera made unavailable to the process.
Procedure: MARK(140); action: make the camera unavailable; LIST_PRODUCTS(); CAPTURE(); LIST_PRODUCTS(); action: make the camera available; MARK(141).
Window:    Marker(id=140) … Marker(id=141)
Pass rule: named checks declared in the integration test (test_L5_11).
Evidence:  CAPTURE completes with error; CaptureFailed WARNING_HI; product count unchanged between the two lists.
Planted faults:camera_left_on

ID:        L5-12
Title:     Camera absent, repeated
Purpose:   Proves a second failed capture also leaves no product and a later capture succeeds.
Covers:    REQ-PiSensor-028, REQ-PiSensor-029
Setup:     As L5-11.
Procedure: MARK(142); action: make the camera unavailable; LIST_PRODUCTS(); CAPTURE(); LIST_PRODUCTS(); action: make the camera available; CAPTURE(); MARK(143).
Window:    Marker(id=142) … Marker(id=143)
Pass rule: named checks declared in the integration test (test_L5_12).
Evidence:  As L5-11, then one ProductWritten event.
Planted faults:none

ID:        L5-13
Title:     Storage unavailable
Purpose:   Proves a capture that cannot store its product fails its command with WARNING_HI and leaves no product.
Covers:    REQ-PiSensor-031, REQ-PiSensor-029
Setup:     Product directory made read-only.
Procedure: MARK(144); action: make the product directory read-only; CAPTURE(); action: make the product directory writable; LIST_PRODUCTS(); MARK(145).
Window:    Marker(id=144) … Marker(id=145)
Pass rule: named checks declared in the integration test (test_L5_13).
Evidence:  CAPTURE completes with error; StorageFailed WARNING_HI; product count unchanged.
Planted faults:storage_left_writable

ID:        L5-14
Title:     Storage full
Purpose:   Proves a capture with no free space fails its command with WARNING_HI and leaves no partial file.
Covers:    REQ-PiSensor-031, REQ-PiSensor-029
Setup:     Product file system filled by a bench file.
Procedure: MARK(146); action: fill the product file system; CAPTURE(); action: remove the fill file; LIST_PRODUCTS(); MARK(147).
Window:    Marker(id=146) … Marker(id=147)
Pass rule: named checks declared in the integration test (test_L5_14).
Evidence:  As L5-13; directory listing by the bench shows no partial file.
Planted faults:none

ID:        L5-15
Title:     CFDP transfer without progress
Purpose:   Proves a transfer with no progress for 60 s ends with WARNING_HI and the product can be downlinked again intact.
Covers:    REQ-PiSensor-034, REQ-PiSensor-035, REQ-PiSensor-038
Setup:     One product stored.
Procedure: MARK(150); DOWNLINK(stored product); action: stop the ground CFDP service; wait 75 s; action: start the ground CFDP service; DOWNLINK(stored product); wait CFDP transfer finished; MARK(151).
Window:    Marker(id=150) … Marker(id=151)
Pass rule: named checks declared in the integration test (test_L5_15). metrics: t(event productManager.DownlinkStalled) - t(productManager.DOWNLINK sent) <= 90 s.
Evidence:  DownlinkStalled WARNING_HI; second transfer finished; ground file sha256 equals the on-board sha256.
Planted faults:cfdp_left_running

ID:        L5-16
Title:     CFDP transfer cut mid-file
Purpose:   Proves a transfer cut after it started ends with WARNING_HI and a repeated downlink delivers the product intact.
Covers:    REQ-PiSensor-034, REQ-PiSensor-035, REQ-PiSensor-038
Setup:     One product stored.
Procedure: MARK(152); DOWNLINK(stored product); wait first file data at the ground; action: block the link; wait 75 s; action: unblock the link; DOWNLINK(stored product); wait CFDP transfer finished; MARK(153).
Window:    Marker(id=152) … Marker(id=153)
Pass rule: named checks declared in the integration test (test_L5_16).
Evidence:  As L5-15.
Planted faults:none

ID:        L5-17
Title:     Link outage
Purpose:   Proves commanding and telemetry resume within 10 s of the end of a 60 s link outage, without a restart.
Covers:    REQ-PiSensor-036, REQ-PiSensor-038
Setup:     One product stored.
Procedure: MARK(160); action: block the link; wait 65 s; action: unblock the link; NO_OP(); DOWNLINK(stored product); wait CFDP transfer finished; MARK(161).
Window:    Marker(id=160) … Marker(id=161)
Pass rule: named checks declared in the integration test (test_L5_17).
Evidence:  Telemetry gap of at least 60 s; first sample and NO_OP response within 10 s of the unblock action; no clock restart; file delivered.
Planted faults:outage_skipped

ID:        L5-18
Title:     Link outage, repeated
Purpose:   Proves recovery from a second 60 s link outage.
Covers:    REQ-PiSensor-036, REQ-PiSensor-038
Setup:     As L5-17.
Procedure: MARK(162); action: block the link; wait 65 s; action: unblock the link; NO_OP(); MARK(163).
Window:    Marker(id=162) … Marker(id=163)
Pass rule: named checks declared in the integration test (test_L5_18).
Evidence:  As L5-17 without the file.
Planted faults:none

ID:        L5-19
Title:     Ground-system outage
Purpose:   Proves commanding and telemetry resume within 10 s of the ground system's return after 60 s, without a restart of the flight software.
Covers:    REQ-PiSensor-037, REQ-PiSensor-038
Setup:     One product stored.
Procedure: MARK(164); action: stop fprime-yamcs; wait 65 s; action: start fprime-yamcs; NO_OP(); DOWNLINK(stored product); wait CFDP transfer finished; MARK(165).
Window:    Marker(id=164) … Marker(id=165)
Pass rule: named checks declared in the integration test (test_L5_19).
Evidence:  As L5-17 with the ground system stopped; flight clock does not restart.
Planted faults:outage_skipped

ID:        L5-20
Title:     Ground-system outage, repeated
Purpose:   Proves recovery from a second ground-system outage.
Covers:    REQ-PiSensor-037, REQ-PiSensor-038
Setup:     As L5-19.
Procedure: MARK(166); action: stop fprime-yamcs; wait 65 s; action: start fprime-yamcs; NO_OP(); MARK(167).
Window:    Marker(id=166) … Marker(id=167)
Pass rule: named checks declared in the integration test (test_L5_20).
Evidence:  As L5-19 without the file.
Planted faults:none

ID:        L5-21
Title:     NMEA sentence with a bad checksum
Purpose:   Proves a sentence with a bad checksum and a new position is discarded and the next good sentence is used.
Covers:    REQ-PiSensor-025
Setup:     GPS sentence source under bench control.
Procedure: MARK(170); action: GPS source sends position A; wait 4 s; action: GPS source sends position B with a bad checksum; wait 4 s; action: GPS source sends position C; wait 4 s; MARK(171).
Window:    Marker(id=170) … Marker(id=171)
Pass rule: named checks declared in the integration test (test_L5_21).
Evidence:  Latitude strip shows A then C, never B.
Planted faults:gps_good_checksum

ID:        L5-22
Title:     NMEA sentences with bad checksums, burst
Purpose:   Proves a burst of bad-checksum sentences leaves the reported position unchanged.
Covers:    REQ-PiSensor-025
Setup:     As L5-21.
Procedure: MARK(172); action: GPS source sends position A; wait 4 s; action: GPS source sends 10 sentences of position B with bad checksums; wait 4 s; MARK(173).
Window:    Marker(id=172) … Marker(id=173)
Pass rule: named checks declared in the integration test (test_L5_22).
Evidence:  Latitude strip stays at A.
Planted faults:none

ID:        L6-1
Title:     Corrupted uplink frame
Purpose:   Proves an uplink frame that fails its integrity check dispatches no command and the same frame uncorrupted does.
Covers:    REQ-PiSensor-027
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(180); action: inject a NO_OP frame with one bit flipped; wait 5 s; action: inject the same NO_OP frame intact; MARK(181).
Window:    Marker(id=180) … Marker(id=181)
Pass rule: named checks declared in the integration test (test_L6_1).
Evidence:  Exactly one NoOpReceived event, after the intact frame.
Planted faults:frame_not_corrupted

ID:        L6-2
Title:     Corrupted uplink frames, burst
Purpose:   Proves several corrupted frames dispatch nothing and commanding still works after them.
Covers:    REQ-PiSensor-027
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(182); action: inject 5 NO_OP frames with a wrong frame check field; wait 5 s; NO_OP(); MARK(183).
Window:    Marker(id=182) … Marker(id=183)
Pass rule: named checks declared in the integration test (test_L6_2).
Evidence:  Exactly one NoOpReceived event, from the planned command.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board whose ground copy and on-board hash an auditor can compare.
Covers:    REQ-PiSensor-013, REQ-PiSensor-005
Setup:     Deployment running, link up, all four sensors attached and answering.
Procedure: MARK(190); CAPTURE(); DOWNLINK(new product); wait CFDP transfer finished; DUMP_SHA256(new product); LIST_PRODUCTS(); MARK(191).
Window:    Marker(id=190) … Marker(id=191)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  Ground file kept in the record; on-board sha256 event; product list.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-PiSensor-001 | L2-1, L2-2, L2-9, L2-10 |  |
| REQ-PiSensor-002 | L2-1, L2-2, L2-9, L2-10 |  |
| REQ-PiSensor-003 | L2-1, L2-2, L2-9, L2-10 |  |
| REQ-PiSensor-004 | L2-3, L2-4, L2-5, L2-6 |  |
| REQ-PiSensor-005 | L2-3, L2-4, L2-5, L2-6, L7-1 |  |
| REQ-PiSensor-006 | L2-3, L2-4, L2-5, L2-6 |  |
| REQ-PiSensor-007 | L2-3, L2-4, L2-5, L2-6 |  |
| REQ-PiSensor-008 | L5-9, L5-10 |  |
| REQ-PiSensor-009 | L5-7, L5-8 |  |
| REQ-PiSensor-010 | L2-3, L2-4 |  |
| REQ-PiSensor-011 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-012 | L2-5, L2-6, L2-9, L2-10 |  |
| REQ-PiSensor-013 | L2-5, L2-6, L2-9, L2-10, L7-1 |  |
| REQ-PiSensor-014 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-015 | L2-9, L2-10 |  |
| REQ-PiSensor-016 | L2-1, L2-2, L2-5, L2-6 |  |
| REQ-PiSensor-017 | L2-1, L2-2, L2-5, L2-6, L2-9, L2-10 |  |
| REQ-PiSensor-018 | L2-7, L2-8 |  |
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
| REQ-PiSensor-029 | L5-11, L5-12, L5-13, L5-14 |  |
| REQ-PiSensor-030 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-031 | L5-13, L5-14 |  |
| REQ-PiSensor-032 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-033 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-034 | L5-15, L5-16 |  |
| REQ-PiSensor-035 | L5-15, L5-16 |  |
| REQ-PiSensor-036 | L5-17, L5-18 |  |
| REQ-PiSensor-037 | L5-19, L5-20 |  |
| REQ-PiSensor-038 | L3-1, L3-2, L5-15, L5-16, L5-17, L5-18, L5-19, L5-20 |  |
| REQ-PiSensor-039 | L3-1, L3-2 |  |
| REQ-PiSensor-040 | waived: Inspection (delegated: picam) | component row of a NEW element |
| REQ-PiSensor-041 | waived: Component test (delegated: prodmgr) | component row of a NEW element |
| REQ-PiSensor-042 | L0-1, L2-1 |  |
| REQ-PiSensor-043 | waived: Component test (delegated: sensmon) | component row of a NEW element |

## 5 Metrics
- L2-3: t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s
- L2-4: t(event productManager.ProductWritten) - t(productManager.CAPTURE sent) <= 30 s
- L5-15: t(event productManager.DownlinkStalled) - t(productManager.DOWNLINK sent) <= 90 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): camera_left_on (stimulus; L5-11); capture_twice (uut-state; L2-3); cfdp_left_running (stimulus; L5-15); downlink_other_product (harness-expectation; L2-5, L2-9); frame_not_corrupted (stimulus; L6-1); gps_good_checksum (stimulus; L5-21); gps_keep_fix (stimulus; L5-7); outage_skipped (stimulus; L5-17, L5-19); period_window_cut (harness-expectation; L2-1, L2-7); skip_sensor_off (stimulus; L5-1, L5-3, L5-5, L5-9); storage_left_writable (stimulus; L5-13).

## 7 Not covered
- delegated: prodmgr — REQ-PiSensor-011, -014, -030, -032, -033, -041 (component rows of `productManager`).
- delegated: sensmon — REQ-PiSensor-043 (component row of `sensorMonitor`).
- delegated: picam — REQ-PiSensor-040 (inspection of the camera library).
- REQ-PiSensor-026: unit test only (decision D11).
- A sensor fault is planted by removing the device from its bus; a device that answers with wrong data is not planted (out-of-range data is waived in the requirements rationale).
- Radio interference and range: the RFM69 link is tested on the bench at short range only.
- The BMP280 and the GPS receiver do not answer on the bench yet; L2-1, L2-2, L5-1, L5-2, L5-5 to L5-10, L5-21, L5-22 cannot run until they are wired.

## 8 Decision log
1. 2026-11-17 designer — deployment = the project's full system deployment plus the harness component `sysTester` (`MARK(U32)`) and the coverage-dump component.
2. 2026-11-17 designer — product content is judged on the ground copy of the file (evidence outside the UUT's own reporting path); `DUMP_SHA256` is a `sysTester` command that hashes the on-board file.
3. 2026-11-17 designer — GPS faults are planted with a bench sentence source on the GPS UART in place of the receiver; the receiver itself is used in L2-1 and L2-2.
4. 2026-11-17 designer — corrupted uplink frames are injected at the ground side of the link by a bench script, not by fprime-yamcs.
