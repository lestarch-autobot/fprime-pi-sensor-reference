# SensorMonitor component test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, as in the project plan (`SystemTester/test/int/plan.json`). Event rate of this plan, from the pinned sources: worst one-second burst 13 events = `MARK` (Marker + 2 cmdDisp events) + `BENCH_LINE` (2 cmdDisp events) + up to 5 throttled manager warnings (`BmpManager.fpp` events with `throttle 5` at 10 Hz, or `imuManager.I2cError`) + 1 loss event + up to 2 `gpsManager` warnings (1 Hz sentences, `throttle 5`); over any 10 s window at most 20 events, 2 per second on average. The burst is above the project plan's figure of 5 events per second in any window: reported to the project campaign; the bench check at L0 replaces this estimate. The 19 component channels at 1 Hz add 7 channels of 1 byte to the project's Table 1 telemetry [I].
- UUT: component `PiSensor.SensorMonitor`, instance `sensorMonitor`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Test deployment: the project's full deployment plus `sysTester` (SSDD decision D13, pending the human's ruling at Approve SSDD), prototype image over TCP; ground system fprime-yamcs at the project pin. Fallback if D13 is refused: the base deployment (`deploy/base`, which already carries `sysTester`) plus `sensorMonitor`.
- Stimuli: `sysTester.MARK(id)`; `sysTester.BENCH_LINE(line, state)` with `line` in {BMP280, MPU6050} and `state` in {OFF, ON} (signature of the project plan; the command is not in `SystemTester.fpp` at the base deployment yet). The GPS sentence source is on the workstation and is driven by bench actions only (stop, resume, sentence content from `bench/gps-script.nmea`), each logged with bench time in bench-actions.log. The tilt of L2-2 is a bench action.
- Pairing rule for the Reading comparisons: each component sample is paired with the manager `Reading` sample nearest in FSW time; the managers run at 10 Hz and the telemetry flush at 1 Hz, so the pair can be two different 10 Hz samples and the bounds are noise allowances; a component sample with no `Reading` sample within 1.5 s is unpaired and does not count towards the minimum pair count.
- Out of scope: data product content (campaign `prodmgr` and the project plan), downlink period at the ground (project L2-1), RFM69 link (project flight block).

## 1 Entry gates
- Unit tests of `SensorMonitor` pass with the plan's coverage; the project's deployment with `sensorMonitor` wired builds from the manifest SHAs.
- L0-1 passes on the bench; marker round-trip, event rate and the noise allowances of L2-1 and L2-2 confirmed (replaces the desk check): the rate of mismatched 10 Hz pairs is recorded and each allowance is set for a false-failure probability of at most 1e-3 per window; the ground rendering of the enum arguments of `Mpu6050Lost` (bare or qualified name) is confirmed against the event pattern.
- `sysTester.BENCH_LINE(line, state)` exists in the harness model with the argument names and enum values above; the planted-fault functions are re-verified against it (`fth verify-plan --tests`).
- Bench recipe of the project plan: bench lines BMP280 and MPU6050 (supply switches, I2C isolated), GPS sentence source on the GPS UART in place of the receiver, with `bench/gps-script.nmea` pinned in the manifest.
- Between tests the harness waits 20 s after the last bench line or source action; each test's `bench_ready_at_start` precondition judges the bench from the managers' channels and bench-actions.log, never from the component's own channels.
- Command times: `t(X sent)` is the FSW time of the `cmdDisp.OpCodeDispatched` event of that command.
- Today's bench cannot run L2-1 to L7-1: the BMP280 and the GPS source do not answer and the bench lines are absent (project ledger).

## 2 Test levels
L0 provenance and feasibility · L2 functional · L5 fault paths · L7 final state. No L3 (the component keeps no state across a restart), no L4 (no endurance bound), no L6 (the component has no commands to reject).

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event sysTester.Started count == 0.
Standard absence block (ABS-LOSS): event sensorMonitor.Bmp280Lost count == 0; event sensorMonitor.Mpu6050Lost count == 0; event sensorMonitor.GpsSilent count == 0.
Standard absence block (ABS-MGR): event bmpManager.DeviceFailure count == 0; event imuManager.I2cError count == 0; event gpsManager.MalformedMessage count == 0; event gpsManager.InvalidData count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched; SensorMonitorTable1 = sensorMonitor.Temperature, sensorMonitor.TemperatureValid, sensorMonitor.Roll, sensorMonitor.Pitch, sensorMonitor.AttitudeValid, sensorMonitor.GyroX, sensorMonitor.GyroY, sensorMonitor.GyroZ, sensorMonitor.Latitude, sensorMonitor.Longitude, sensorMonitor.Altitude, sensorMonitor.FixValid; SensorMonitorTable2 = sensorMonitor.TemperatureInvalidReason, sensorMonitor.AttitudeInvalidReason, sensorMonitor.FixInvalidReason, sensorMonitor.Bmp280State, sensorMonitor.Mpu6050State, sensorMonitor.GpsState, sensorMonitor.GpsQuality.

ID:        L0-1
Title:     Image identity
Purpose:   Proves the running image is the manifest's prototype image and contains the component.
Covers:    REQ-SensorMonitor-001
Setup:     Prototype image running on the Raspberry Pi 5; link up.
Procedure: MARK(10); VERSION(ALL); bracket (2 Heartbeat samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  Version events equal the manifest describe strings; check: SensorMonitorTable1 samples >= 1; SensorMonitorTable2 samples >= 1.
Planted faults:none

ID:        L2-1
Title:     Sensor telemetry, all sensors present
Purpose:   Proves every Table 1 and Table 2 channel is published each second and reads valid.
Covers:    REQ-SensorMonitor-001, REQ-SensorMonitor-002, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz. The Pi is at rest.
Procedure: MARK(30); wait 60 s; MARK(31); BENCH_LINE(BMP280, ON); wait 10 s.
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); largest gap between FSW time tags of every Table 1 and Table 2 channel, counted from the START marker to the first sample and from the last sample to the END marker, <= 1.5 s; at least 55 samples of each channel (1 Hz schedule call plus half a period, a test allowance for rate-group jitter confirmed at L0; FSW time tags, so the downlink does not enter; 55 = 60 s at 1 Hz less the flush phase at both markers); every sample: |Temperature - bmpManager.Reading.temperature| <= 0.5 degC and |GyroX,Y,Z - imuManager.Reading.rotation| <= 1.0 deg/s against the Reading sample nearest in FSW time and within 1.5 s (else unpaired); at least 30 pairs each (0.5 degC and 1.0 deg/s are noise allowances for the 10 Hz pairing race, measured at L0 and replaced at the stage-2 refresh; exact equality is unit test UT-02); |Roll - atan2(a_y, a_z)| <= 1.0 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 1.0 deg for every Roll and Pitch sample against the imuManager.Reading sample nearest in FSW time and within 1.5 s (else unpaired), Pi at rest; at least 30 pairs (the reading the component used and the Reading sample the ground holds can be different 10 Hz samples (managers in rateGroup10Hz, tlmSend flush at 1 Hz), so the bound is a noise allowance, not REQ-SensorMonitor-003: MPU6050 accelerometer noise 400 ug/sqrt(Hz) (PS-MPU-6000A-00 Rev. 3.4, section 6.2) gives about 0.3 deg rms [I]; the allowance is measured at L0 and replaced at the stage-2 refresh; the 0.1 deg requirement is unit test UT-03); every Latitude, Longitude, Altitude sample of the window equals the value of the bench sentence script (bench/gps-script.nmea, sha256 in the manifest) converted as NMEA 0183 ddmm.mmmm, within 1e-7 deg and 0.01 m; the script holds one constant position; at least 5 samples (the script is bench-owned evidence outside the component's reporting path; 1e-7 deg and 0.01 m absorb the last-digit difference between the ground conversion and the manager's degrees + minutes / 60.0 (GpsManager.cpp lines 22 to 27)).
Evidence:  check: first(sensorMonitor.Bmp280State) == PRESENT; first(sensorMonitor.Mpu6050State) == PRESENT; first(sensorMonitor.GpsState) == PRESENT; first(sensorMonitor.TemperatureValid) == VALID; first(sensorMonitor.AttitudeValid) == VALID; first(sensorMonitor.FixValid) == VALID; last(sensorMonitor.TemperatureValid) == VALID; last(sensorMonitor.AttitudeValid) == VALID; last(sensorMonitor.FixValid) == VALID; last(sensorMonitor.TemperatureInvalidReason) == NONE; last(sensorMonitor.AttitudeInvalidReason) == NONE; last(sensorMonitor.FixInvalidReason) == NONE; last(sensorMonitor.Bmp280State) == PRESENT; last(sensorMonitor.Mpu6050State) == PRESENT; last(sensorMonitor.GpsState) == PRESENT; last(sensorMonitor.GpsQuality) == 1; event sensorMonitor.Bmp280Lost count == 0; event sensorMonitor.Mpu6050Lost count == 0; event sensorMonitor.GpsSilent count == 0; ABS; ABS-MGR. The BENCH_LINE(BMP280, ON) after the END marker and its 10 s settle wait are outside the window.
Planted faults:bmp_line_dropped

ID:        L2-2
Title:     Roll and pitch follow a tilt
Purpose:   Proves roll or pitch steps with a bench tilt and matches the reported acceleration.
Covers:    REQ-SensorMonitor-001, REQ-SensorMonitor-002, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz. The Pi rests flat, then is tilted by more than 20 degrees about one axis and held (bench action, logged with bench time).
Procedure: MARK(40); wait 20 s; action: tilt the Pi by more than 20 degrees and hold; wait 20 s; MARK(41); BENCH_LINE(MPU6050, ON); wait 10 s.
Window:    Marker(id=40) … Marker(id=41)
Pass rule: named checks declared in the integration test (test_L2_2). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); |last Roll - first Roll| >= 20 deg or |last Pitch - first Pitch| >= 20 deg across the tilt action; |Roll - atan2(a_y, a_z)| <= 1.0 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 1.0 deg for every Roll and Pitch sample against the imuManager.Reading sample nearest in FSW time and within 1.5 s (else unpaired), samples within 3 s of the logged tilt action excluded; at least 25 pairs (the reading the component used and the Reading sample the ground holds can be different 10 Hz samples (managers in rateGroup10Hz, tlmSend flush at 1 Hz), so the bound is a noise allowance, not REQ-SensorMonitor-003: MPU6050 accelerometer noise 400 ug/sqrt(Hz) (PS-MPU-6000A-00 Rev. 3.4, section 6.2) gives about 0.3 deg rms [I]; the allowance is measured at L0 and replaced at the stage-2 refresh; the 0.1 deg requirement is unit test UT-03); Roll, Pitch and AttitudeValid samples of one schedule call carry one FSW time tag, every call of the window.
Evidence:  check: last(sensorMonitor.AttitudeValid) == VALID; last(sensorMonitor.AttitudeInvalidReason) == NONE; last(sensorMonitor.Mpu6050State) == PRESENT; event sensorMonitor.Mpu6050Lost count == 0; ABS; ABS-MGR. The BENCH_LINE(MPU6050, ON) after the END marker and its settle wait are outside the window.
Planted faults:mpu_line_dropped

ID:        L5-1
Title:     BMP280 loss and return
Purpose:   Proves a stopped BMP280 is reported lost once, reads invalid, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(100); BENCH_LINE(BMP280, OFF); wait 15 s; MARK(101); BENCH_LINE(BMP280, ON); wait 15 s; MARK(102).
Window:    F = Marker(id=100) … Marker(id=101); B = Marker(id=101) … Marker(id=102)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 3.5 s <= t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE(line=BMP280, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window) (lower bound 3.5 s: the fifth schedule call without a new reading falls 4 s to 5 s after the supply is cut (N = 5, SDD Table 2), less 0.5 s command latency allowance; upper bound 10 s is REQ-PiSensor-019); B: first sensorMonitor.TemperatureValid == VALID - t(sysTester.BENCH_LINE(line=BMP280, state=ON) sent) <= 10 s (FSW clock).
Evidence:  check: F: event sensorMonitor.Bmp280Lost count == 1; F: event sensorMonitor.Bmp280Returned count == 0; F: last(sensorMonitor.Bmp280State) == LOST; F: last(sensorMonitor.TemperatureValid) == INVALID; F: last(sensorMonitor.TemperatureInvalidReason) == STALE; F: last(sensorMonitor.Mpu6050State) == PRESENT; F: last(sensorMonitor.GpsState) == PRESENT; F: last(sensorMonitor.AttitudeValid) == VALID; F: last(sensorMonitor.FixValid) == VALID; B: event sensorMonitor.Bmp280Returned count == 1; B: event sensorMonitor.Bmp280Lost count == 0; B: last(sensorMonitor.Bmp280State) == PRESENT; B: last(sensorMonitor.TemperatureValid) == VALID; B: last(sensorMonitor.TemperatureInvalidReason) == NONE; every window: ABS.
Planted faults:sensor_line_kept_on

ID:        L5-2
Title:     MPU6050 loss and return
Purpose:   Proves a stopped MPU6050 is reported lost once by its identity read, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-010, REQ-SensorMonitor-011, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-021, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(110); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(111); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(112).
Window:    F = Marker(id=110) … Marker(id=111); B = Marker(id=111) … Marker(id=112)
Pass rule: named checks declared in the integration test (test_L5_2). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window) (lower bound 1.5 s: the third failed identity read falls 2 s to 3 s after the supply is cut (M = 3, SDD Table 2), less 0.5 s command latency allowance; upper bound 10 s is REQ-PiSensor-020); B: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock).
Evidence:  check: F: event sensorMonitor.Mpu6050Lost count == 1; F: event sensorMonitor.Mpu6050Lost(reason=IDENTITY, status=I2C_OTHER_ERR) count == 1; F: event sensorMonitor.Mpu6050Returned count == 0; F: last(sensorMonitor.Mpu6050State) == LOST; F: last(sensorMonitor.AttitudeValid) == INVALID; F: last(sensorMonitor.AttitudeInvalidReason) == IDENTITY; F: last(sensorMonitor.Bmp280State) == PRESENT; F: last(sensorMonitor.GpsState) == PRESENT; F: last(sensorMonitor.TemperatureValid) == VALID; F: last(sensorMonitor.FixValid) == VALID; B: event sensorMonitor.Mpu6050Returned count == 1; B: event sensorMonitor.Mpu6050Lost count == 0; B: last(sensorMonitor.Mpu6050State) == PRESENT; B: last(sensorMonitor.AttitudeValid) == VALID; B: last(sensorMonitor.AttitudeInvalidReason) == NONE; every window: ABS.
Planted faults:sensor_line_kept_on

ID:        L5-3
Title:     GPS silence and return
Purpose:   Proves a silent GPS is reported once, reads invalid, and returns valid.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(120); action: GPS sentence source stops; wait 15 s; MARK(121); action: GPS sentence source resumes the scripted fix sentences; wait 15 s; MARK(122).
Window:    F = Marker(id=120) … Marker(id=121); B = Marker(id=121) … Marker(id=122)
Pass rule: named checks declared in the integration test (test_L5_3). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 2 s <= t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s (fifth schedule call without a sentence falls 4 s to 5 s after the stop (N = 5); bench time against FSW time carries the 2 s clock tolerance of project decision D12, checked by the project's clock_offset_within at L0; upper bound REQ-PiSensor-021); B: first sensorMonitor.FixValid == VALID - bench time of the resume action <= 10 s.
Evidence:  check: F: event sensorMonitor.GpsSilent count == 1; F: event sensorMonitor.GpsReturned count == 0; F: last(sensorMonitor.GpsState) == LOST; F: last(sensorMonitor.FixValid) == INVALID; F: last(sensorMonitor.FixInvalidReason) == STALE; F: last(sensorMonitor.Bmp280State) == PRESENT; F: last(sensorMonitor.Mpu6050State) == PRESENT; F: last(sensorMonitor.TemperatureValid) == VALID; F: last(sensorMonitor.AttitudeValid) == VALID; B: event sensorMonitor.GpsReturned count == 1; B: event sensorMonitor.GpsSilent count == 0; B: last(sensorMonitor.GpsState) == PRESENT; B: last(sensorMonitor.FixValid) == VALID; B: last(sensorMonitor.FixInvalidReason) == NONE; every window: ABS.
Planted faults:none

ID:        L5-4
Title:     MPU6050 lost twice
Purpose:   Proves each loss and each return of one sensor gives exactly one event.
Covers:    REQ-SensorMonitor-005, REQ-SensorMonitor-010, REQ-SensorMonitor-011, REQ-SensorMonitor-013, REQ-SensorMonitor-014, REQ-SensorMonitor-015, REQ-SensorMonitor-016, REQ-SensorMonitor-021, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(130); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(131); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(132); BENCH_LINE(MPU6050, OFF); wait 15 s; MARK(133); BENCH_LINE(MPU6050, ON); wait 15 s; MARK(134).
Window:    F = Marker(id=130) … Marker(id=131); B = Marker(id=131) … Marker(id=132); F2 = Marker(id=132) … Marker(id=133); B2 = Marker(id=133) … Marker(id=134)
Pass rule: named checks declared in the integration test (test_L5_4). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window) (lower bound 1.5 s: the third failed identity read falls 2 s to 3 s after the supply is cut (M = 3, SDD Table 2), less 0.5 s command latency allowance; upper bound 10 s is REQ-PiSensor-020); B: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock); F2: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window) (lower bound 1.5 s: the third failed identity read falls 2 s to 3 s after the supply is cut (M = 3, SDD Table 2), less 0.5 s command latency allowance; upper bound 10 s is REQ-PiSensor-020); B2: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock).
Evidence:  check: F: event sensorMonitor.Mpu6050Lost count == 1; F: event sensorMonitor.Mpu6050Lost(reason=IDENTITY, status=I2C_OTHER_ERR) count == 1; F: event sensorMonitor.Mpu6050Returned count == 0; F: last(sensorMonitor.Mpu6050State) == LOST; F: last(sensorMonitor.AttitudeValid) == INVALID; F: last(sensorMonitor.AttitudeInvalidReason) == IDENTITY; F: last(sensorMonitor.Bmp280State) == PRESENT; F: last(sensorMonitor.GpsState) == PRESENT; F: last(sensorMonitor.TemperatureValid) == VALID; F: last(sensorMonitor.FixValid) == VALID; B: event sensorMonitor.Mpu6050Returned count == 1; B: event sensorMonitor.Mpu6050Lost count == 0; B: last(sensorMonitor.Mpu6050State) == PRESENT; B: last(sensorMonitor.AttitudeValid) == VALID; B: last(sensorMonitor.AttitudeInvalidReason) == NONE; F2: event sensorMonitor.Mpu6050Lost count == 1; F2: event sensorMonitor.Mpu6050Lost(reason=IDENTITY, status=I2C_OTHER_ERR) count == 1; F2: event sensorMonitor.Mpu6050Returned count == 0; F2: last(sensorMonitor.Mpu6050State) == LOST; F2: last(sensorMonitor.AttitudeValid) == INVALID; F2: last(sensorMonitor.AttitudeInvalidReason) == IDENTITY; F2: last(sensorMonitor.Bmp280State) == PRESENT; F2: last(sensorMonitor.GpsState) == PRESENT; F2: last(sensorMonitor.TemperatureValid) == VALID; F2: last(sensorMonitor.FixValid) == VALID; B2: event sensorMonitor.Mpu6050Returned count == 1; B2: event sensorMonitor.Mpu6050Lost count == 0; B2: last(sensorMonitor.Mpu6050State) == PRESENT; B2: last(sensorMonitor.AttitudeValid) == VALID; B2: last(sensorMonitor.AttitudeInvalidReason) == NONE; every window: ABS.
Planted faults:none

ID:        L5-5
Title:     GPS without a fix
Purpose:   Proves no-fix GGA sentences read location invalid with reason NO_FIX and raise no silence event.
Covers:    REQ-SensorMonitor-009, REQ-SensorMonitor-022, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(140); action: GPS source sends no-fix GGA sentences (quality 0) at 1 Hz; wait 15 s; MARK(141); action: GPS source sends the scripted fix sentences (quality 1) at 1 Hz; wait 15 s; MARK(142).
Window:    F = Marker(id=140) … Marker(id=141); B = Marker(id=141) … Marker(id=142)
Pass rule: named checks declared in the integration test (test_L5_5). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s, INVALID from then to the END marker (1 s GGA period + 1 s schedule call + 2 s clock tolerance (project decision D12) + 1 s allowance; a test settling time, REQ-SensorMonitor-009 has no time bound).
Evidence:  check: F: last(sensorMonitor.FixValid) == INVALID; F: last(sensorMonitor.FixInvalidReason) == NO_FIX; F: last(sensorMonitor.GpsQuality) == 0; F: last(sensorMonitor.GpsState) == PRESENT; F: event sensorMonitor.GpsSilent count == 0; B: last(sensorMonitor.FixValid) == VALID; B: last(sensorMonitor.FixInvalidReason) == NONE; B: last(sensorMonitor.GpsQuality) == 1; B: event sensorMonitor.GpsReturned count == 0; every window: ABS; every window: ABS-LOSS.
Planted faults:none

ID:        L5-6
Title:     GPS quality indicator values
Purpose:   Proves quality 2 and 8 read location valid and an empty indicator reads it invalid.
Covers:    REQ-SensorMonitor-009, REQ-SensorMonitor-022
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(150); action: GPS source sends GGA sentences with quality 2 at 1 Hz; wait 10 s; MARK(151); action: GPS source sends GGA sentences with an empty quality field at 1 Hz; wait 10 s; MARK(152); action: GPS source sends GGA sentences with quality 8 at 1 Hz; wait 10 s; MARK(153); action: GPS source sends the scripted fix sentences (quality 1) at 1 Hz; wait 10 s.
Window:    Q2 = Marker(id=150) … Marker(id=151); E = Marker(id=151) … Marker(id=152); Q8 = Marker(id=152) … Marker(id=153)
Pass rule: named checks declared in the integration test (test_L5_6). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read).
Evidence:  check: Q2: last(sensorMonitor.GpsQuality) == 2; Q2: last(sensorMonitor.FixValid) == VALID; E: last(sensorMonitor.GpsQuality) == 255; E: last(sensorMonitor.FixValid) == INVALID; E: last(sensorMonitor.FixInvalidReason) == NO_FIX; Q8: last(sensorMonitor.GpsQuality) == 8; Q8: last(sensorMonitor.FixValid) == VALID; every window: ABS; every window: ABS-LOSS.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves every sensor present and valid, with the location equal to the bench script.
Covers:    REQ-SensorMonitor-002, REQ-SensorMonitor-012
Setup:     Prototype image running, link up, BMP280 and MPU6050 powered, GPS sentence source sending the scripted fix sentences (quality 1) at 1 Hz.
Procedure: MARK(230); wait 10 s; MARK(231).
Window:    Marker(id=230) … Marker(id=231)
Pass rule: named checks declared in the integration test (test_L7_1). metrics: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); every Latitude, Longitude, Altitude sample of the window equals the value of the bench sentence script (bench/gps-script.nmea, sha256 in the manifest) converted as NMEA 0183 ddmm.mmmm, within 1e-7 deg and 0.01 m; the script holds one constant position; at least 5 samples (the script is bench-owned evidence outside the component's reporting path; the same comparison is repeated by the auditor for the final state).
Evidence:  check: first(sensorMonitor.Bmp280State) == PRESENT; first(sensorMonitor.Mpu6050State) == PRESENT; first(sensorMonitor.GpsState) == PRESENT; first(sensorMonitor.TemperatureValid) == VALID; first(sensorMonitor.AttitudeValid) == VALID; first(sensorMonitor.FixValid) == VALID; last(sensorMonitor.TemperatureValid) == VALID; last(sensorMonitor.AttitudeValid) == VALID; last(sensorMonitor.FixValid) == VALID; last(sensorMonitor.TemperatureInvalidReason) == NONE; last(sensorMonitor.AttitudeInvalidReason) == NONE; last(sensorMonitor.FixInvalidReason) == NONE; last(sensorMonitor.Bmp280State) == PRESENT; last(sensorMonitor.Mpu6050State) == PRESENT; last(sensorMonitor.GpsState) == PRESENT; last(sensorMonitor.GpsQuality) == 1; ABS; ABS-LOSS; ABS-MGR. After the run the bench copies the last sentence the source sent (bench-actions.log) and reads MPU6050 register 0x75 (`i2cget -y 1 0x68 0x75`, a bench health fact) into record/raw/final-state.txt.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-SensorMonitor-001 | L0-1, L2-1, L2-2 |  |
| REQ-SensorMonitor-002 | L2-1, L2-2, L7-1 |  |
| REQ-SensorMonitor-003 | waived: UT only | the 0.1 degree bound is below the noise of the 10 Hz pairing on the bench; L2-1 and L2-2 judge the angles within a noise allowance; unit test UT-03 is the verification of record |
| REQ-SensorMonitor-004 | waived: UT only | start-up state before a first reading cannot be held on the bench |
| REQ-SensorMonitor-005 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-006 | waived: UT only | a reading time ahead of the clock needs a clock step, not plantable on a shared bench |
| REQ-SensorMonitor-007 | waived: UT only | start-up state; a sensor absent at boot needs a restart of the shared deployment per sensor |
| REQ-SensorMonitor-008 | waived: UT only | a sensor that answers with out-of-limit data is not plantable (project plan, not covered) |
| REQ-SensorMonitor-009 | L5-5, L5-6 |  |
| REQ-SensorMonitor-010 | L5-2, L5-4 |  |
| REQ-SensorMonitor-011 | L5-2, L5-4 |  |
| REQ-SensorMonitor-012 | L2-1, L2-2, L5-1, L5-2, L5-3, L5-4, L5-5, L7-1 |  |
| REQ-SensorMonitor-013 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-014 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-015 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-016 | L5-1, L5-2, L5-3, L5-4 |  |
| REQ-SensorMonitor-017 | waived: UT only | once, in order, unchanged cannot be judged through a 1 Hz telemetry flush; unit test UT-23; the system effect (location follows the sentences) is judged by location_equals_script in L2-1 and L7-1 |
| REQ-SensorMonitor-018 | waived: UT only | the request port is driven by productManager; its system tests are the project's L2-3 to L2-6 and L5-9, L5-10 |
| REQ-SensorMonitor-019 | waived: UT only | as REQ-SensorMonitor-018; the age boundary is a unit test |
| REQ-SensorMonitor-020 | waived: Inspection | Inspection of the FPP port kinds and the guard |
| REQ-SensorMonitor-021 | L5-2, L5-4 |  |
| REQ-SensorMonitor-022 | L5-5, L5-6 |  |

## 5 Metrics
- L2-1: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); largest gap between FSW time tags of every Table 1 and Table 2 channel, counted from the START marker to the first sample and from the last sample to the END marker, <= 1.5 s; at least 55 samples of each channel; every sample: |Temperature - bmpManager.Reading.temperature| <= 0.5 degC and |GyroX,Y,Z - imuManager.Reading.rotation| <= 1.0 deg/s against the Reading sample nearest in FSW time and within 1.5 s (else unpaired); at least 30 pairs each; |Roll - atan2(a_y, a_z)| <= 1.0 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 1.0 deg for every Roll and Pitch sample against the imuManager.Reading sample nearest in FSW time and within 1.5 s (else unpaired), Pi at rest; at least 30 pairs; every Latitude, Longitude, Altitude sample of the window equals the value of the bench sentence script (bench/gps-script.nmea, sha256 in the manifest) converted as NMEA 0183 ddmm.mmmm, within 1e-7 deg and 0.01 m; the script holds one constant position; at least 5 samples
- L2-2: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); |last Roll - first Roll| >= 20 deg or |last Pitch - first Pitch| >= 20 deg across the tilt action; |Roll - atan2(a_y, a_z)| <= 1.0 deg and |Pitch - atan2(-a_x, sqrt(a_y^2 + a_z^2))| <= 1.0 deg for every Roll and Pitch sample against the imuManager.Reading sample nearest in FSW time and within 1.5 s (else unpaired), samples within 3 s of the logged tilt action excluded; at least 25 pairs; Roll, Pitch and AttitudeValid samples of one schedule call carry one FSW time tag, every call of the window
- L5-1: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 3.5 s <= t(event sensorMonitor.Bmp280Lost) - t(sysTester.BENCH_LINE(line=BMP280, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window); B: first sensorMonitor.TemperatureValid == VALID - t(sysTester.BENCH_LINE(line=BMP280, state=ON) sent) <= 10 s (FSW clock)
- L5-2: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window); B: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock)
- L5-3: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 2 s <= t(event sensorMonitor.GpsSilent) - bench time of the stop action <= 10 s; B: first sensorMonitor.FixValid == VALID - bench time of the resume action <= 10 s
- L5-4: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window); B: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock); F2: 1.5 s <= t(event sensorMonitor.Mpu6050Lost) - t(sysTester.BENCH_LINE(line=MPU6050, state=OFF) sent) <= 10 s (FSW clock, the one such command and event of the window); B2: first sensorMonitor.AttitudeValid == VALID - t(sysTester.BENCH_LINE(line=MPU6050, state=ON) sent) <= 10 s (FSW clock)
- L5-5: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); F: first sensorMonitor.FixValid == INVALID - bench time of the no-fix action <= 5 s, INVALID from then to the END marker
- L5-6: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read)
- L7-1: precondition: in the 3 s before the START marker bmpManager.Reading and imuManager.Reading each have a new sample and bench-actions.log shows the GPS source sending fix sentences (require; UNVERIFIED when not met; no sensorMonitor channel is read); every Latitude, Longitude, Altitude sample of the window equals the value of the bench sentence script (bench/gps-script.nmea, sha256 in the manifest) converted as NMEA 0183 ddmm.mmmm, within 1e-7 deg and 0.01 m; the script holds one constant position; at least 5 samples

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): bmp_line_dropped (uut-state; L2-1); mpu_line_dropped (uut-state; L2-2); sensor_line_kept_on (stimulus; L5-1, L5-2).

## 7 Not covered
- REQ-SensorMonitor-003, -004, -006, -007, -008, -017, -018, -019, -020: unit test or inspection only; reasons in the requirements block.
- Wrong MPU6050 identity value with the device answering (REQ-PiSensor-043): not plantable on the bench without another device at address 0x68; unit tests UT-13.
- Identity persistence M = 3 and loss count N = 5 at their exact boundaries: unit tests; the bench tests judge a lower and an upper time bound.
- Concurrency of the five inputs under load: inspection (REQ-SensorMonitor-020); no bench stimulus forces an interleaving.

## 8 Decision log
1. 2026-11-17 designer — test deployment = the project's full deployment + `sysTester` (project decision D13, an author proposal pending the human's ruling at Approve SSDD); fallback named in the scope.
2. 2026-11-17 designer — coverage thresholds at the skill baselines (UT 95 % lines, on-target 75 % lines).
3. 2026-11-17 designer — markers, bench lines and helpers follow the project plan so one harness serves both plans; marker ids 10 to 231 are local to this plan's record.
4. 2026-11-17 designer — REQ-SensorMonitor-003 and -017 are verified by unit test of record; the bench judges their system effect within stated allowances.
5. 2026-11-17 designer — review round 1 (system-test-review Mode A, 11 must fix / 12 could fix): all accepted; dispositions in the campaign's review record.
6. 2026-11-17 designer — review round 2 (4 must fix / 3 could fix): all accepted.
7. 2026-11-17 designer — review round 3, the last of the bound (1 must fix, STR-30): accepted and closed after the round, not re-reviewed: both line-dropped faults insert their OFF command directly after the START marker. Review totals: 30 raised, 30 closed, 0 disagreements. Deferred to the bench (L0 / stage-2 refresh): marker round-trip, event rate, noise allowances, clock offset, enum rendering, the I2C_OTHER_ERR status; `sysTester.BENCH_LINE` is not in `SystemTester.fpp` yet; D13 pending.
