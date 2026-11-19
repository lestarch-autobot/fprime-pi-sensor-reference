# PiCamera component bench plan

## 0 Scope
Bench behaviour of `piCamera` that unit tests cannot show: the real camera, the response time on the target, a camera held by another process, a restart. Product content and downlink are judged by the project plan (`test/int/plan.json`, L2-3 to L2-6).
C-1 and the second half of C-2 and C-3 need a GPS fix: without one every capture fails with `SENSOR_STALE` or `SENSOR_NO_DATA` at `LOCATION` and the tests FAIL.

## 1 Entry gates
- (none)

## 2 Test levels
- (none)

## 3 Test entries

Window rule: rows from the **last** `cmdDisp.NoOpStringReceived(id=START)` row that precedes the first `cmdDisp.NoOpStringReceived(id=END)` row following it, through that END row plus the END `cmdDisp.CMD_NO_OP_STRING` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event piCamera.CaptureFailed count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = imuManager.Reading.

ID:        C-1
Title:     Capture on the target
Purpose:   Proves one capture command stores one product through the real camera within the response bound.
Covers:    REQ-PiCamera-009, REQ-PiCamera-020
Setup:     Deployment running on the Raspberry Pi 5, camera free, GPS fix, RFM69 link up.
Procedure: MARK(10); bracket (2 Heartbeat samples); piCamera.CAPTURE(); wait event dpWriter.FileWritten; bracket (2 Heartbeat samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_C_1). metrics: t(event piCamera.CaptureCompleted) - t(piCamera.CAPTURE sent) <= 15 s.
Evidence:  
Planted faults:c1_second_capture

ID:        C-2
Title:     Camera held by another process, then freed
Purpose:   Proves a capture fails cleanly while another process holds the camera and succeeds once it is freed.
Covers:    REQ-PiCamera-009, REQ-PiCamera-016, REQ-PiCamera-019
Setup:     As C-1. The bench action `camera_hold` starts `rpicam-hello` on the Pi, which opens the camera.
Procedure: MARK(20); bracket (2 Heartbeat samples); action: camera_hold; piCamera.CAPTURE(); wait event cmdDisp.OpCodeError; bracket (2 Heartbeat samples); action: camera_release; piCamera.CAPTURE(); wait event dpWriter.FileWritten; bracket (2 Heartbeat samples); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_C_2). metrics: t(event piCamera.CaptureFailed) - t(piCamera.CAPTURE sent) <= 15 s.
Evidence:  
Planted faults:c2_capture_before_hold

ID:        C-3
Title:     Capture after a restart
Purpose:   Proves the component captures again after the deployment is stopped and started.
Covers:    REQ-PiCamera-024
Setup:     As C-1. The bench action `fsw_restart` stops the deployment process on the Pi and starts it again.
Procedure: MARK(30); bracket (2 Heartbeat samples); piCamera.CAPTURE(); wait event dpWriter.FileWritten; action: fsw_restart; wait 20 s; piCamera.CAPTURE(); wait event dpWriter.FileWritten; bracket (2 Heartbeat samples); MARK(31).
Window:    Marker(id=30) … Marker(id=31)
Pass rule: named checks declared in the integration test (test_C_3).
Evidence:  
Planted faults:c3_capture_after_restart

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-PiCamera-009 | C-1, C-2 | Response bound CAPTURE_MAX_MS on the target. |
| REQ-PiCamera-016 | C-2 | Camera held by another process. |
| REQ-PiCamera-019 | C-2 | Capture after the camera is freed. |
| REQ-PiCamera-020 | C-1 |  |
| REQ-PiCamera-024 | C-3 (restart after a capture), unit test RecoveryAfterFailure | Not verified as written on the bench: the restart of C-3 follows a completed capture, not one in progress (not covered list). |

## 5 Metrics
- C-1: t(event piCamera.CaptureCompleted) - t(piCamera.CAPTURE sent) <= 15 s
- C-2: t(event piCamera.CaptureFailed) - t(piCamera.CAPTURE sent) <= 15 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): c1_second_capture (stimulus; C-1); c2_capture_before_hold (stimulus; C-2); c3_capture_after_restart (uut-state; C-3).

## 7 Not covered
- No camera attached (REQ-PiCamera-016, `NO_CAMERA`): needs the cable removed; unit test `NoCamera`.
- Restart during a capture: the restart of C-3 comes after a completed capture; a capture lasts under 1 s on the bench and the bench action takes longer.

## 8 Decision log
- (none)
