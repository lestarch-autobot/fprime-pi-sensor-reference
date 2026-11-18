# PiSensor::PiCamera

## 1. Introduction

`PiCamera` manages the Raspberry Pi Camera attached to the CSI port of a
Raspberry Pi 5. On each capture request it acquires one still picture, encodes
it as a JPEG, stamps it with the time the frame was acquired and hands it to
the requester, or reports why it could not. It uses the camera library packaged
with Raspberry Pi OS and no OpenCV. The camera module is not yet attached to the
bench: its model, datasheet and identification reply are recorded on arrival.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-PiCamera-001 | A success reply shall carry one picture acquired from the Pi Camera after its request. | Integration Test |
| REQ-PiCamera-002 | Each delivered picture shall be one JFIF file, SOI to EOI, `PICTURE_WIDTH` x `PICTURE_HEIGHT` pixels. | Integration Test |
| REQ-PiCamera-003 | Each delivered picture shall carry the system time read when its frame arrived. | Unit Test |
| REQ-PiCamera-004 | The component shall answer each capture request with exactly one reply. | Unit Test |
| REQ-PiCamera-005 | Each reply shall state success, or the Table 1 reason whose condition occurred. | Unit Test |
| REQ-PiCamera-006 | Each reply shall carry the context value of its request. | Unit Test |
| REQ-PiCamera-007 | The component shall emit `CaptureStarted` (`ACTIVITY_LO`) once per acquisition, before requesting the camera frame. | Unit Test |
| REQ-PiCamera-008 | The component shall reply within `CAPTURE_TIMEOUT_TICKS` ticks of receiving a request. | Unit Test |
| REQ-PiCamera-009 | A failure reply shall carry no picture. | Unit Test |
| REQ-PiCamera-010 | After a failure reply the component shall hold no picture buffer of that request. | Unit Test |
| REQ-PiCamera-011 | Each failure reply shall emit one `CaptureFailed` (`WARNING_LO`) naming its Table 1 reason. | Unit Test |
| REQ-PiCamera-012 | A request received before the reply to an earlier request shall get a `BUSY` reply. | Unit Test |
| REQ-PiCamera-013 | A capture shall end with the same reply whether or not requests arrive during it. | Unit Test |
| REQ-PiCamera-014 | A request made after a failure's cause has cleared shall succeed without a restart. | Integration Test |
| REQ-PiCamera-015 | The component shall publish each Table 2 channel after every reply that changes it. | Unit Test |
| REQ-PiCamera-016 | The component shall use only Raspberry Pi OS packaged camera libraries, not OpenCV. | Inspection |
| REQ-PiCamera-017 | Camera use shall be compliant with the libcamera API of `libcamera-dev` 0.8.0. | Integration Test |
| REQ-PiCamera-018 | The component shall release each picture buffer when the requester returns it. | Unit Test |
| REQ-PiCamera-019 | After a restart during a capture, the first request shall succeed. | Integration Test |
| REQ-PiCamera-020 | The component shall release only picture buffers it delivered and has not yet released. | Unit Test |
| REQ-PiCamera-021 | A returned buffer the component does not release shall emit `ReturnRejected` (`WARNING_LO`). | Unit Test |

Table 1: failure reasons.

| Reason | Condition |
|---|---|
| `NO_CAMERA` | No camera is detected |
| `CAMERA_ERROR` | The camera, its library or the JPEG encoding reports an error or yields no complete picture |
| `TIMEOUT` | No picture was ready within `CAPTURE_TIMEOUT_TICKS` ticks of the request |
| `NO_BUFFER` | No picture buffer is available, or the last delivered picture is not yet returned |
| `TOO_LARGE` | The JPEG does not fit the picture buffer |
| `BUSY` | An earlier request has no reply yet |

Table 2: telemetry.

| Channel | Content |
|---|---|
| `CapturesCompleted` | Count of success replies since start |
| `CapturesFailed` | Count of failure replies since start |
| `LastPictureSize` | Size in bytes of the last delivered JPEG |

Table 3: constants.

| Constant | Value | Meaning |
|---|---|---|
| `CAPTURE_TIMEOUT_TICKS` | 10 | Ticks of the `run` port from receipt of a request to its reply |
| `PICTURE_WIDTH`, `PICTURE_HEIGHT` | 640, 480 | Picture size in pixels |

External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| libcamera public API | `libcamera-dev` 0.8.0+rpt20261104-1, Raspberry Pi OS 13 (trixie) archive | Other | camera discovery, configuration, frame request |
| JPEG File Interchange Format | JFIF 1.02; ITU-T T.81 | Standard | picture encoding |
