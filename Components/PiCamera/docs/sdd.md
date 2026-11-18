# PiSensor::PiCamera

## 1. Introduction

`PiCamera` manages the Raspberry Pi Camera attached to the CSI port of a
Raspberry Pi 5. On each capture request it acquires one still picture, encodes
it as a JPEG, stamps it with the time the frame was acquired and hands it to
the requester, or reports why it could not. It uses the camera library packaged
with Raspberry Pi OS and no OpenCV. The camera module is not yet attached to the
bench, so its model is recorded when it arrives.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-PiCamera-001 | On a capture request, the component shall acquire one picture from the Pi Camera. | Integration Test |
| REQ-PiCamera-002 | Each delivered picture shall be one complete JPEG of at least 640x480 pixels. | Integration Test |
| REQ-PiCamera-003 | Each delivered picture shall carry the time its frame was acquired. | Unit Test |
| REQ-PiCamera-004 | The component shall answer each capture request with exactly one reply. | Unit Test |
| REQ-PiCamera-005 | Each reply shall state success or one failure reason of Table 1. | Unit Test |
| REQ-PiCamera-006 | Each reply shall carry the context value of its request. | Unit Test |
| REQ-PiCamera-007 | The component shall emit `CaptureStarted` (`ACTIVITY_LO`) when acquisition of a picture begins. | Unit Test |
| REQ-PiCamera-008 | The component shall reply within `CAPTURE_TIMEOUT_TICKS` ticks of starting a request. | Unit Test |
| REQ-PiCamera-009 | A failure reply shall carry no picture. | Unit Test |
| REQ-PiCamera-010 | After a failure reply the component shall hold no picture buffer. | Unit Test |
| REQ-PiCamera-011 | Each failure shall emit `CaptureFailed` (`WARNING_LO`) naming its Table 1 reason. | Unit Test |
| REQ-PiCamera-012 | A request received during a capture shall get a `BUSY` reply. | Unit Test |
| REQ-PiCamera-013 | A request received during a capture shall not disturb that capture. | Unit Test |
| REQ-PiCamera-014 | After a failure, the next request shall succeed once the camera answers, without a restart. | Integration Test |
| REQ-PiCamera-015 | The component shall report the Table 2 telemetry. | Unit Test |
| REQ-PiCamera-016 | The component shall use only Raspberry Pi OS packaged camera libraries, not OpenCV. | Inspection |
| REQ-PiCamera-017 | Camera use shall be compliant with the libcamera API of Raspberry Pi OS 13. | Integration Test |
| REQ-PiCamera-018 | The component shall release each picture buffer when the requester returns it. | Unit Test |

Table 1: failure reasons.

| Reason | Meaning |
|---|---|
| `NO_CAMERA` | No camera is detected |
| `CAMERA_ERROR` | The camera or its library reports an error |
| `TIMEOUT` | No frame arrived within `CAPTURE_TIMEOUT_TICKS` |
| `NO_BUFFER` | No picture buffer is available |
| `TOO_LARGE` | The JPEG does not fit the picture buffer |
| `BUSY` | A capture is in progress |

Table 2: telemetry.

| Channel | Content |
|---|---|
| `CapturesCompleted` | Count of success replies since start |
| `CapturesFailed` | Count of failure replies since start |
| `LastPictureSize` | Size in bytes of the last delivered JPEG |

Table 3: constants.

| Constant | Value | Meaning |
|---|---|---|
| `CAPTURE_TIMEOUT_TICKS` | 10 | Ticks of the `run` port from start of a request to its reply |
| `PICTURE_WIDTH`, `PICTURE_HEIGHT` | 1280, 960 | Requested picture size in pixels |

External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| libcamera public API | `libcamera-dev` package of Raspberry Pi OS 13 (trixie) | Other | camera discovery, configuration, frame request |
| JPEG File Interchange Format | ITU-T T.81 / JFIF 1.02 | Standard | picture encoding |
