# SensorMonitor component test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, as in the project plan (`SystemTester/test/int/plan.json`). Event rate of this plan: at most 2 events per second in any window. The 19 component channels at 1 Hz fit the project's link budget for Table 1 telemetry [I: seven added channels of 1 to 4 bytes].
- UUT: component `PiSensor.SensorMonitor`, instance `sensorMonitor`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Test deployment: the project's full deployment plus `sysTester` (SSDD decision D13), prototype image over TCP; ground system fprime-yamcs at the project pin.
- `sysTester` commands used: `MARK(id)`, `BENCH_LINE(line, state)` with lines BMP280, MPU6050, GPS (GPS = the bench sentence source stops or resumes). Bench actions drive the GPS sentence source content and the tilt of L2-2; each is logged with bench time in bench-actions.log.
- Out of scope: data product content (campaign `prodmgr` and the project plan), downlink period at the ground (project L2-1), RFM69 link (project flight block).

## 1 Entry gates
- Unit tests of `SensorMonitor` pass with the plan's coverage; the project's base deployment with `sensorMonitor` wired builds from the manifest SHAs.
- L0-1 passes on the bench; marker round-trip and event rate confirmed (replaces the desk check).
- Bench recipe of the project plan: bench lines BMP280 and MPU6050 (supply switches, I2C isolated), GPS sentence source on the GPS UART in place of the receiver.
- Today's bench cannot run L2-1 to L7-1: the BMP280 and the GPS source do not answer and the bench lines are absent (project ledger).

## 2 Test levels
L0 provenance and feasibility · L2 functional · L5 fault paths · L7 final state. No L3 (the component keeps no state across a restart), no L4 (no endurance bound), no L6 (the component has no commands to reject).

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event sysTester.Started count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched; SensorMonitorTable1 = sensorMonitor.Temperature, sensorMonitor.TemperatureValid, sensorMonitor.Roll, sensorMonitor.Pitch, sensorMonitor.AttitudeValid, sensorMonitor.GyroX, sensorMonitor.GyroY, sensorMonitor.GyroZ, sensorMonitor.Latitude, sensorMonitor.Longitude, sensorMonitor.Altitude, sensorMonitor.FixValid; SensorMonitorTable2 = sensorMonitor.TemperatureInvalidReason, sensorMonitor.AttitudeInvalidReason, sensorMonitor.FixInvalidReason, sensorMonitor.Bmp280State, sensorMonitor.Mpu6050State, sensorMonitor.GpsState, sensorMonitor.GpsQuality.

ID:        L0-1
Title:     Image identity
Purpose:   Proves the running image is the manifest's prototype image and contains the component.
Covers:    REQ-SensorMonitor-001
Setup:     Prototype image running on the Raspberry Pi 5; link up.
Procedure: MARK(10); VERSION(ALL); bracket (2 Heartbeat samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  Version events equal the manifest describe strings; check: SensorMonitorTable1 samples >= 1 and SensorMonitorTable2 samples >= 1 (the component is in the image and scheduled).
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry, all sensors present
Purpose:   Proves every Table 1 and Table 2 channel is published each second and reads valid.
Covers:    REQ-SensorMonitor-001, REQ-SensorMonitor-002, REQ-SensorMonitor-003, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(30); wait 60 s; BENCH_LINE(BMP280, ON); MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: largest gap between FSW time tags of every Table 1 and Table 2 channel in the window <= 1.5 s (1 Hz schedule call plus half a period of rate-group jitter; FSW time tags, so the downlink does not enter); Temperature, GyroX, GyroY, GyroZ, Latitude, Longitude, Altitude equal the manager Reading sample nearest in time; |Roll - atan2(a_y, a_z)| <= 0.1 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 0.1 deg against the imuManager.Reading sample of the same second, Pi at rest (0.1 degrees is REQ-SensorMonitor-003; reference computed on the ground from the manager's channel).
Evidence:  Channel strips over 60 s; check: last(sensorMonitor.TemperatureValid) == VALID, last(sensorMonitor.AttitudeValid) == VALID, last(sensorMonitor.FixValid) == VALID, last(sensorMonitor.TemperatureInvalidReason) == NONE, last(sensorMonitor.AttitudeInvalidReason) == NONE, last(sensorMonitor.FixInvalidReason) == NONE, last(sensorMonitor.Bmp280State) == PRESENT, last(sensorMonitor.Mpu6050State) == PRESENT, last(sensorMonitor.GpsState) == PRESENT, event sensorMonitor.Bmp280Lost count == 0, event sensorMonitor.Mpu6050Lost count == 0, event sensorMonitor.GpsSilent count == 0. The closing BENCH_LINE(BMP280, ON) is a no-op on a healthy bench.
Planted faults:bmp_line_dropped

ID:        L2-2
Title:     Roll and pitch against the acceleration
Purpose:   Proves roll and pitch follow the Table 1 formulas for the reported acceleration.
Covers:    REQ-SensorMonitor-001, REQ-SensorMonitor-002, REQ-SensorMonitor-003, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT. The Pi rests in two attitudes in turn: flat, then tilted by more than 20 degrees about one axis (bench action).
Procedure: MARK(40); wait 20 s; action: tilt the Pi by more than 20 degrees and hold; wait 20 s; MARK(41).
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: |Roll - atan2(a_y, a_z)| <= 0.1 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 0.1 deg against the imuManager.Reading sample of the same second (0.1 degrees is REQ-SensorMonitor-003; the reference is computed on the ground from the manager's own channel, outside the component); Roll, Pitch, AttitudeValid of one schedule call carry one FSW time tag.
Evidence:  Roll and pitch strips beside the angles computed from imuManager.Reading; check: last(sensorMonitor.AttitudeValid) == VALID; the tilt shows as a step of more than 20 degrees in Roll or Pitch.
Planted faults:none

ID:        L5-1
Title:     BMP280 loss and return
Purpose:   Proves a stopped BMP280 is reported lost once, reads invalid, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(100); BENCH_LINE(BMP280, OFF); wait 15 s; MARK(101); BENCH_LINE(BMP280, ON); wait 15 s; MARK(102).
Window:    F = Marker(id=100) … Marker(id=101); B = Marker(id=101) … Marker(id=102)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s (N = 5 schedule calls at 1 Hz (SDD Table 2) plus 2 s reading age and command latency; the system bound of REQ-PiSensor-019 to -021 is 10 s); first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.Bmp280Lost count == 1 (WARNING_HI), last(sensorMonitor.Bmp280State) == LOST, last(sensorMonitor.TemperatureValid) == INVALID, event sensorMonitor.Bmp280Returned count == 0, the other two states PRESENT and validities VALID. B: event sensorMonitor.Bmp280Returned count == 1, event sensorMonitor.Bmp280Lost count == 0, last(sensorMonitor.Bmp280State) == PRESENT, last(sensorMonitor.TemperatureValid) == VALID; both: event sysTester.Started count == 0.
Planted faults:sensor_line_kept_on

ID:        L5-2
Title:     MPU6050 loss and return
Purpose:   Proves a stopped MPU6050 is reported lost once, reads invalid, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-010, REQ-SensorMonitor-011, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-021, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(110); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(111); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(112).
Window:    F = Marker(id=110) … Marker(id=111); B = Marker(id=111) … Marker(id=112)
Pass rule: named checks declared in the integration test (test_L5_2). metrics: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s (N = 5 schedule calls at 1 Hz (SDD Table 2) plus 2 s reading age and command latency; the system bound of REQ-PiSensor-019 to -021 is 10 s); first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.Mpu6050Lost count == 1 (WARNING_HI), last(sensorMonitor.Mpu6050State) == LOST, last(sensorMonitor.AttitudeValid) == INVALID, event sensorMonitor.Mpu6050Returned count == 0, the other two states PRESENT and validities VALID. B: event sensorMonitor.Mpu6050Returned count == 1, event sensorMonitor.Mpu6050Lost count == 0, last(sensorMonitor.Mpu6050State) == PRESENT, last(sensorMonitor.AttitudeValid) == VALID; both: event sysTester.Started count == 0.
Planted faults:sensor_line_kept_on

ID:        L5-3
Title:     GPS silence and return
Purpose:   Proves a silent GPS is reported once, reads invalid, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(120); BENCH_LINE(GPS, OFF); wait 15 s; MARK(121); BENCH_LINE(GPS, ON); wait 15 s; MARK(122).
Window:    F = Marker(id=120) … Marker(id=121); B = Marker(id=121) … Marker(id=122)
Pass rule: named checks declared in the integration test (test_L5_3). metrics: t(event sensorMonitor.GpsSilent) - t(sysTester.BENCH_LINE sent) <= 10 s (N = 5 schedule calls at 1 Hz (SDD Table 2) plus 2 s reading age and command latency; the system bound of REQ-PiSensor-019 to -021 is 10 s); first sensorMonitor.FixValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.GpsSilent count == 1 (WARNING_HI), last(sensorMonitor.GpsState) == LOST, last(sensorMonitor.FixValid) == INVALID, event sensorMonitor.GpsReturned count == 0, the other two states PRESENT and validities VALID. B: event sensorMonitor.GpsReturned count == 1, event sensorMonitor.GpsSilent count == 0, last(sensorMonitor.GpsState) == PRESENT, last(sensorMonitor.FixValid) == VALID; both: event sysTester.Started count == 0.
Planted faults:sensor_line_kept_on

ID:        L5-4
Title:     MPU6050 lost twice
Purpose:   Proves each loss and each return of one sensor gives exactly one event.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-010, REQ-SensorMonitor-011, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-021, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, MPU6050, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(130); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(131); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(132); BENCH_LINE(MPU6050, OFF); wait 15 s; BENCH_LINE(MPU6050, ON); wait 15 s; MARK(133).
Window:    F = Marker(id=130) … Marker(id=131); B = Marker(id=131) … Marker(id=132); S = Marker(id=132) … Marker(id=133)
Pass rule: named checks declared in the integration test (test_L5_4). metrics: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s (N = 5 schedule calls at 1 Hz (SDD Table 2) plus 2 s reading age and command latency; the system bound of REQ-PiSensor-019 to -021 is 10 s); first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s.
Evidence:  F: check event sensorMonitor.Mpu6050Lost count == 1 (WARNING_HI), last(sensorMonitor.Mpu6050State) == LOST, last(sensorMonitor.AttitudeValid) == INVALID, event sensorMonitor.Mpu6050Returned count == 0, the other two states PRESENT and validities VALID. B: event sensorMonitor.Mpu6050Returned count == 1, event sensorMonitor.Mpu6050Lost count == 0, last(sensorMonitor.Mpu6050State) == PRESENT, last(sensorMonitor.AttitudeValid) == VALID; both: event sysTester.Started count == 0. S: event sensorMonitor.Mpu6050Lost count == 1 precedes event sensorMonitor.Mpu6050Returned count == 1; last state PRESENT. In F and S the Mpu6050Lost event text names the failed identity read status (the unpowered device does not acknowledge).
Planted faults:none

ID:        L5-5
Title:     GPS without a fix
Purpose:   Proves no-fix GGA sentences read location invalid, raise no silence event, and pass on.
Covers:    REQ-SensorMonitor-009, REQ-SensorMonitor-017, REQ-SensorMonitor-022, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(140); action: GPS source sends no-fix GGA sentences (quality 0) at 1 Hz; wait 15 s; MARK(141); action: GPS source sends fix sentences (quality 1) at 1 Hz; wait 15 s; MARK(142).
Window:    F = Marker(id=140) … Marker(id=141); B = Marker(id=141) … Marker(id=142)
Pass rule: named checks declared in the integration test (test_L5_5). metrics: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s (1 s GGA period + 1 s schedule call + 2 s clock tolerance + 1 s margin; a test settling time, REQ-SensorMonitor-009 has no time bound); gpsManager.Reading has a new sample for every fix sentence of window B.
Evidence:  F: check last(sensorMonitor.FixValid) == INVALID, last(sensorMonitor.FixInvalidReason) == NO_FIX, last(sensorMonitor.GpsQuality) == 0, last(sensorMonitor.GpsState) == PRESENT, event sensorMonitor.GpsSilent count == 0. B: last(sensorMonitor.FixValid) == VALID, last(sensorMonitor.GpsQuality) == 1, event sensorMonitor.GpsReturned count == 0; the bench source byte counter advances in both.
Planted faults:none

ID:        L5-6
Title:     GPS fix kinds
Purpose:   Proves the quality channel follows the GGA indicator and an empty indicator reads location invalid.
Covers:    REQ-SensorMonitor-009, REQ-SensorMonitor-017, REQ-SensorMonitor-022
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(150); action: GPS source sends GGA sentences with quality 2 at 1 Hz; wait 10 s; MARK(151); action: GPS source sends GGA sentences with an empty quality field at 1 Hz; wait 10 s; MARK(152); action: GPS source sends GGA sentences with quality 8 at 1 Hz; wait 10 s; MARK(153); action: GPS source sends fix sentences (quality 1) at 1 Hz.
Window:    Q2 = Marker(id=150) … Marker(id=151); E = Marker(id=151) … Marker(id=152); Q8 = Marker(id=152) … Marker(id=153)
Pass rule: named checks declared in the integration test (test_L5_6).
Evidence:  Q2: check last(sensorMonitor.GpsQuality) == 2, last(sensorMonitor.FixValid) == VALID. E: last(sensorMonitor.GpsQuality) == 255, last(sensorMonitor.FixValid) == INVALID, event sensorMonitor.GpsSilent count == 0. Q8: last(sensorMonitor.GpsQuality) == 8; FixValid in Q8 is not judged (the catalog GPS manager's handling of quality 8 decides the reading age; see not covered).
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves every sensor present and valid, with the MPU6050 identity read independently on the bench.
Covers:    REQ-SensorMonitor-010, REQ-SensorMonitor-021, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280, MPU6050 and the GPS sentence source answering, all three sensor states PRESENT.
Procedure: MARK(230); wait 10 s; MARK(231).
Window:    Marker(id=230) … Marker(id=231)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  check: last(sensorMonitor.Mpu6050State) == PRESENT, last(sensorMonitor.AttitudeValid) == VALID, last(sensorMonitor.Bmp280State) == PRESENT, last(sensorMonitor.GpsState) == PRESENT. After the run the bench reads MPU6050 register 0x75 on I2C bus 1 address 0x68 (`i2cget -y 1 0x68 0x75`) over ssh into record/raw/final-state.txt; the auditor compares it with 0x68 (RM-MPU-6000A-00 Rev. 4.2).
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-SensorMonitor-001 | L0-1, L2-1, L2-2 |  |
| REQ-SensorMonitor-002 | L2-1, L2-2 |  |
| REQ-SensorMonitor-003 | L2-1, L2-2 |  |
| REQ-SensorMonitor-004 | waived: UT only | start-up state before a first reading cannot be held on the bench |
| REQ-SensorMonitor-005 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-006 | waived: UT only | a reading time ahead of the clock needs a clock step, not plantable on a shared bench |
| REQ-SensorMonitor-007 | waived: UT only | start-up state; a sensor absent at boot needs a restart of the shared deployment per sensor |
| REQ-SensorMonitor-008 | waived: UT only | a sensor that answers with out-of-limit data is not plantable (project plan, not covered) |
| REQ-SensorMonitor-009 | L5-5, L5-6 |  |
| REQ-SensorMonitor-010 | L5-2, L5-4, L7-1 |  |
| REQ-SensorMonitor-011 | L5-2, L5-4 |  |
| REQ-SensorMonitor-012 | L2-1, L2-2, L5-1, L5-2, L5-3, L5-4, L5-5, L7-1 |  |
| REQ-SensorMonitor-013 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-014 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-015 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-016 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-017 | L5-5, L5-6 |  |
| REQ-SensorMonitor-018 | waived: UT only | the request port is driven by productManager; its system tests are the project's L2-3 to L2-6 and L5-9, L5-10 |
| REQ-SensorMonitor-019 | waived: UT only | as REQ-SensorMonitor-018; the age boundary is a unit test |
| REQ-SensorMonitor-020 | waived: Inspection | Inspection of the FPP port kinds and the guard |
| REQ-SensorMonitor-021 | L5-2, L5-4, L7-1 |  |
| REQ-SensorMonitor-022 | L5-5, L5-6 |  |

## 5 Metrics
- L2-1: largest gap between FSW time tags of every Table 1 and Table 2 channel in the window <= 1.5 s; Temperature, GyroX, GyroY, GyroZ, Latitude, Longitude, Altitude equal the manager Reading sample nearest in time; |Roll - atan2(a_y, a_z)| <= 0.1 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 0.1 deg against the imuManager.Reading sample of the same second, Pi at rest
- L2-2: |Roll - atan2(a_y, a_z)| <= 0.1 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 0.1 deg against the imuManager.Reading sample of the same second; Roll, Pitch, AttitudeValid of one schedule call carry one FSW time tag
- L5-1: t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.TemperatureValid == VALID after the return - time of the return <= 10 s
- L5-2: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s
- L5-3: t(event sensorMonitor.GpsSilent) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.FixValid == VALID after the return - time of the return <= 10 s
- L5-4: t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE sent) <= 10 s; first sensorMonitor.AttitudeValid == VALID after the return - time of the return <= 10 s
- L5-5: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s; gpsManager.Reading has a new sample for every fix sentence of window B

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): bmp_line_dropped (uut-state; L2-1); sensor_line_kept_on (stimulus; L5-1, L5-2, L5-3).

## 7 Not covered
- REQ-SensorMonitor-004, -006, -007, -008, -018, -019, -020: unit test or inspection only; reasons in the requirements block.
- Wrong MPU6050 identity value with the device answering (REQ-PiSensor-043): not plantable on the bench without another device at address 0x68; unit test.
- Identity persistence M = 3 and loss count N = 5 at their boundaries: unit tests; the bench tests judge the 10 s system bound only.
- GGA quality 8 with a valid location: the catalog GPS manager's handling of quality values above 1 is not confirmed on the bench (no receiver identified); L5-6 judges the quality channel only.
- Concurrency of the five inputs under load: inspection (REQ-SensorMonitor-020); no bench stimulus forces an interleaving.

## 8 Decision log
1. 2026-11-17 designer — test deployment = the project's full deployment + `sysTester` (project decision D13); no component-only deployment.
2. 2026-11-17 designer — coverage thresholds at the skill baselines (UT 95 % lines, on-target 75 % lines).
3. 2026-11-17 designer — markers, bench lines and helpers follow the project plan so one harness serves both plans; marker ids 10 to 231 are local to this plan's record.
4. 2026-11-17 designer — requirements with a single system test are verified by unit test of record (waiver in the requirements block), not counted as system-covered.
