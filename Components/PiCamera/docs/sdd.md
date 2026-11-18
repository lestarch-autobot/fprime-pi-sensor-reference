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
| REQ-PiCamera-015 | The component shall publish each Table 2 channel after every reply or return that changes it. | Unit Test |
| REQ-PiCamera-016 | The component shall use only Raspberry Pi OS packaged camera libraries, not OpenCV. | Inspection |
| REQ-PiCamera-017 | Camera use shall be compliant with the libcamera API of `libcamera-dev` 0.8.0. | Integration Test |
| REQ-PiCamera-018 | The component shall release each picture buffer when the requester returns it. | Unit Test |
| REQ-PiCamera-019 | After a restart during a capture, the first request shall succeed. | Integration Test |
| REQ-PiCamera-020 | The component shall release only picture buffers it delivered and has not yet released. | Unit Test |
| REQ-PiCamera-021 | A returned buffer the component does not release shall emit `ReturnRejected` (`WARNING_LO`). | Unit Test |
| REQ-PiCamera-022 | At start the component shall emit `CameraFound` with the camera's identification, or `CameraNotFound`. | Unit Test |
| REQ-PiCamera-023 | Each `CaptureFailed` shall carry the step and the library return code of its failure. | Unit Test |
| REQ-PiCamera-024 | The component shall publish every Table 2 channel once at start. | Unit Test |

Table 1: failure reasons.

| Reason | Condition |
|---|---|
| `NO_CAMERA` | No camera is detected |
| `CAMERA_ERROR` | The camera, its library or the JPEG encoding reports an error or yields no complete picture |
| `TIMEOUT` | No picture was ready within `CAPTURE_TIMEOUT_TICKS` ticks of the request |
| `NO_BUFFER` | No picture buffer is available |
| `PICTURE_OUTSTANDING` | The last delivered picture is not yet returned |
| `TOO_LARGE` | The JPEG does not fit the picture buffer |
| `BUSY` | An earlier request has no reply yet |

Table 2: telemetry.

| Channel | Content |
|---|---|
| `CapturesCompleted` | Count of success replies since start |
| `CapturesFailed` | Count of failure replies since start |
| `LastPictureSize` | Size in bytes of the last delivered JPEG |
| `CameraPresent` | A camera was detected at the last detection |
| `PictureOutstanding` | A delivered picture is not yet returned |

Table 3: constants.

| Constant | Value | Meaning |
|---|---|---|
| `CAPTURE_TIMEOUT_TICKS` | 10 | Ticks of the `run` port from receipt of a request to its reply |
| `PICTURE_WIDTH`, `PICTURE_HEIGHT` | 640, 480 | Picture size in pixels |

External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| libcamera public API | `libcamera-dev` 0.8.0+rpt20261104-1, Raspberry Pi OS 13 (trixie) archive | Other | camera discovery, configuration, frame request |
| libjpeg-turbo API | `libjpeg62-turbo-dev` 1:2.1.5-4, Raspberry Pi OS 13 (trixie) archive | Other | JPEG compression calls |
| JPEG File Interchange Format | JFIF 1.02; ITU-T T.81 | Standard | picture encoding |

## 3. Design

### 3.1 Component Diagram

```
                      +------------------------+
captureIn :         [ ]                        [ ] imageOut : PiSensor.CaptureReply
PiSensor.CaptureRequest                        |
imageReturnIn :     [ ]       PiCamera         [ ] allocate : Fw.BufferGet
Fw.BufferSend         |                        |
run : Svc.Sched     [ ]                        [ ] deallocate : Fw.BufferSend
                      |                        |
pingIn : Svc.Ping   [ ]                        [ ] pingOut : Svc.Ping
                      +------------------------+
  special ports: eventOut, textEventOut, tlmOut, timeGetOut
```

### 3.2 Ports

| Name | Kind | Type | Purpose |
|---|---|---|---|
| `captureIn` | guarded input | `PiSensor.CaptureRequest` | Request for one picture |
| `imageOut` | output | `PiSensor.CaptureReply` | One reply per request; connects to an async input |
| `imageReturnIn` | guarded input | `Fw.BufferSend` | Delivered picture buffer comes back |
| `run` | guarded input | `Svc.Sched` | 1 Hz tick that counts the capture timeout |
| `allocate` | output | `Fw.BufferGet` | Gets the picture buffer |
| `deallocate` | output | `Fw.BufferSend` | Releases the picture buffer |
| `pingIn`, `pingOut` | async input (drop), output | `Svc.Ping` | Health ping of the component thread |
| `detect` | internal, drop | — | Camera detection at start |
| `acquire` | internal, drop | — | Camera work of one capture |
| `frameDone` | internal, drop | — | Camera library thread reports the frame |

`CaptureStatus`, `CaptureRequest` and `CaptureReply` are in `Components/CapturePorts`, a library of their own, so a requester does not link the camera library.

`CaptureReply` carries `context: U32`, `status: CaptureStatus`, `acquired: Fw.Time` and `picture: Fw.Buffer`; the size of `picture` is the JPEG length in bytes.

Three threads enter the component.

| Thread | Runs | Touches |
|---|---|---|
| Caller of a guarded port | `captureIn`, `imageReturnIn`, `run` | Table of 3.3, under the component guard |
| Component thread | `detect`, `acquire`, `frameDone`, `pingIn` | Camera interface, outside the guard; table of 3.3 and the encoder, under the guard |
| Camera library thread | Frame callback of the camera interface | Reads the time, counts settle frames, sends `frameDone`; no member of 3.3 |

### 3.3 State

| Member | Values | Meaning |
|---|---|---|
| `m_state` | `IDLE`, `ACQUIRING` | A request without a reply exists |
| `m_context` | U32 | Context of the request in `ACQUIRING` |
| `m_capture` | U32 | Number of the current capture; compared for equality only |
| `m_ticks` | 0..`CAPTURE_TIMEOUT_TICKS` | Ticks since receipt of the request in `ACQUIRING` |
| `m_delivered` | `Fw.Buffer` or invalid | The delivered picture not yet returned |
| `m_completed`, `m_failed` | U32 | Counts behind `CapturesCompleted`, `CapturesFailed`; wrap to 0 after 4294967295 |
| `m_detected` | bool | `detect` was sent |

At start `m_state` is `IDLE`, `m_delivered` is invalid, the counts are 0 and the camera is closed, whatever an earlier run left.

The camera interface is closed, open or started; it is closed whenever the component thread is not inside `acquire` or between `acquire` and its `frameDone`.

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> ACQUIRING: request
    IDLE --> IDLE: request, picture outstanding (PICTURE_OUTSTANDING)
    ACQUIRING --> ACQUIRING: request (BUSY)
    ACQUIRING --> IDLE: picture encoded (OK)
    ACQUIRING --> IDLE: camera step fails, no buffer, JPEG too large
    ACQUIRING --> IDLE: tick CAPTURE_TIMEOUT_TICKS (TIMEOUT)
```

### 3.4 Configuration and Setup

```fpp
constant PICTURE_WIDTH = 640
constant PICTURE_HEIGHT = 480
constant PICTURE_BUFFER_SIZE = 262144
constant CAPTURE_TIMEOUT_TICKS = 10
constant SETTLE_FRAMES = 10
```

Picture size, size of the buffer asked per capture, reply limit in ticks, and the frames discarded while exposure settles.

```fpp
instance piCamera: PiSensor.PiCamera base id 0x10008000 queue size 10 stack size 1048576 priority 30
```

The instance of the system sketch with a larger queue and stack; `run` connects to the 1 Hz rate group.

`allocate` and `deallocate` connect to one `Svc.BufferManager` that holds at least one buffer of `PICTURE_BUFFER_SIZE` bytes for this component; the component holds at most one.

The camera is reached through one interface class (`detect`, `open`, `configure`, `start`, `stop`, `close`, frame access) implemented with libcamera; JPEG encoding uses libjpeg-turbo. Both are Raspberry Pi OS packages. Unit tests substitute the interface, and a build that finds no libcamera uses an implementation that detects no camera.

### 3.5 Port Handlers

#### captureIn

Admitted always. In `ACQUIRING` it replies `BUSY`; with a picture outstanding it replies `PICTURE_OUTSTANDING`. Otherwise it takes the next capture number, zeroes `m_ticks`, enters `ACQUIRING`, emits `CaptureStarted` and sends `acquire`.

#### acquire

Admitted when its capture number is current. It detects, opens, configures and starts the camera outside the guard. A step that fails closes the camera and, when the capture is still current, replies `NO_CAMERA` or `CAMERA_ERROR`.

#### frameDone

The camera interface discards `SETTLE_FRAMES` frames, reports the next one once and keeps its pixels unchanged until `close`.

The handler stops the camera. Under the guard, when its capture number is current, it gets a buffer, encodes the frame into it and replies `OK` with the reported time, or releases the buffer and replies `CAMERA_ERROR`, `NO_BUFFER` or `TOO_LARGE`. It then closes the camera.

The guard is held during encoding, so a tick cannot end a capture whose buffer is in use.

#### run

The first tick sends `detect`. In `ACQUIRING` it counts a tick and at `CAPTURE_TIMEOUT_TICKS` replies `TIMEOUT` and enters `IDLE`, also while the component thread is inside a camera call; that call's result is then discarded by its capture number and the camera closed.

#### detect

It detects the camera, emits `CameraFound` with the library's identification or `CameraNotFound`, and publishes every channel once.

#### imageReturnIn

Admitted when the buffer's data pointer is that of the delivered picture. It releases the buffer and forgets it; any other buffer is left alone and emits `ReturnRejected`.

#### pingIn

It echoes the key on `pingOut`.

Every reply publishes the channels it changed. Every failure reply emits `CaptureFailed` with its reason, its step and the library return code; each step value has one emission site.

| Reason | Steps |
|---|---|
| `BUSY` | `RECEIVE` |
| `PICTURE_OUTSTANDING` | `RETURN` |
| `NO_CAMERA` | `DETECT` |
| `CAMERA_ERROR` | `OPEN`, `CONFIGURE`, `START`, `FRAME`, `ENCODE` |
| `NO_BUFFER` | `ALLOCATE` |
| `TOO_LARGE` | `ENCODE` |
| `TIMEOUT` | `TICKS` |

## 4. Data Product Format

None; the picture leaves through `imageOut` and the requester builds the data product.

## 5. Ground Interface

The component has no commands and no parameters.

| Telemetry | Type | Content |
|---|---|---|
| `CapturesCompleted` | U32 | Count of success replies since start |
| `CapturesFailed` | U32 | Count of failure replies since start |
| `LastPictureSize` | U32 | Size in bytes of the last delivered JPEG |
| `CameraPresent` | bool | A camera was detected at the last detection |
| `PictureOutstanding` | bool | A delivered picture is not yet returned |

| Event | Severity | Arguments | Meaning |
|---|---|---|---|
| `CaptureStarted` | `ACTIVITY_LO` | `context` | Acquisition of a picture begins |
| `CaptureFailed` | `WARNING_LO` | `context`, `reason`, `step`, `code` | A request got a failure reply |
| `ReturnRejected` | `WARNING_LO` | `bytes` | A returned buffer was not released |
| `CameraFound` | `ACTIVITY_LO` | `camera` | A camera is detected at start |
| `CameraNotFound` | `WARNING_LO` | — | No camera is detected at start |

## 6. Example Uses

```mermaid
sequenceDiagram
    participant R as Requester
    participant C as PiCamera
    participant B as Buffer provider
    participant L as Camera library
    R->>C: captureIn(context)
    C-->>R: event CaptureStarted
    C->>L: detect, open, configure, start
    L-->>C: frameDone(capture, ok, acquired)
    C->>L: stop
    C->>B: allocate(PICTURE_BUFFER_SIZE)
    C->>R: imageOut(context, OK, acquired, picture)
    C->>L: close
    R->>C: imageReturnIn(picture)
    C->>B: deallocate(picture)
```

## 7. Idiosyncrasies

| Failure or limit | Owner |
|---|---|
| Camera model, sensor modes and identification reply | Recorded when the camera is attached; `CameraFound` reports it |
| Requester never returns a picture: later requests get `PICTURE_OUTSTANDING` | Requester |
| Component thread stuck in a camera call: requests get `TIMEOUT`, health ping fails | System health |
| Constants change by rebuild only | Deployment |
| Picture content (exposure, focus, scene) | Not judged |
| Command failure, `WARNING_HI` event and product removal after a failure reply | Requester |

Differences from the system sketch:

- `imageOut` is `PiSensor.CaptureReply`, so the reply carries status and acquisition time; the requester's input changes with it.
- `captureIn` and `imageReturnIn` are guarded, so refusals and returns need no queue.
- `run` joins the 1 Hz rate group, so the timeout is counted off the component thread.
- `pingIn` and `pingOut` join the health pattern.
- One delivered picture is outstanding at a time.

## 8. Tests

<!-- fth:tests:begin -->
_Generated by `fth render-sdd-tests` from the plan — do not edit by hand; the package renderer fails when this table and the plan disagree._

| Test | Purpose | Requirements |
|---|---|---|
| L0-1 | Proves the running image is the manifest's image. | — |
| L0-2 | Proves the image links the packaged libcamera of the pinned version and no OpenCV. | REQ-PiCamera-017 |
| L2-1 | Proves a capture request delivers one 640x480 JFIF picture acquired after the request. | REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017 |
| L2-2 | Proves each capture delivers a newly acquired 640x480 JFIF picture. | REQ-PiCamera-001, REQ-PiCamera-002, REQ-PiCamera-017 |
| L3-1 | Proves the first capture after a process kill during a capture succeeds. | REQ-PiCamera-019 |
| L3-2 | Proves the first capture after a service restart during a capture succeeds. | REQ-PiCamera-019 |
| L5-1 | Proves an absent camera gives NO_CAMERA and the next capture succeeds without a restart. | REQ-PiCamera-014 |
| L5-2 | Proves a camera in use elsewhere gives CAMERA_ERROR and the next capture succeeds without a restart. | REQ-PiCamera-014 |
| L7-1 | Proves the last picture on board is the 640x480 JFIF picture received at the ground. | REQ-PiCamera-001, REQ-PiCamera-002 |
<!-- fth:tests:end -->

### Unit-test list

| Test | Description | Requirements |
|---|---|---|
| CaptureDeliversPicture | A request with a good frame gets one `OK` reply carrying the encoded picture. | REQ-PiCamera-004, REQ-PiCamera-005 |
| AcquisitionTimeIsFrameTime | The reply carries the system time read when the frame arrived. | REQ-PiCamera-003 |
| ReplyEchoesContext | Success and every failure reply carry the context of their request. | REQ-PiCamera-006 |
| CaptureStartedOncePerAcquisition | `CaptureStarted` is emitted once, before the camera is asked for a frame. | REQ-PiCamera-007 |
| NoCameraFails | No camera detected gives one `NO_CAMERA` reply, event and no buffer held. | REQ-PiCamera-005, REQ-PiCamera-009, REQ-PiCamera-010, REQ-PiCamera-011 |
| CameraErrorFails | Each camera step error and a bad frame give `CAMERA_ERROR`. | REQ-PiCamera-005, REQ-PiCamera-009, REQ-PiCamera-010, REQ-PiCamera-011 |
| TimeoutFails | No frame gives `TIMEOUT` at tick `CAPTURE_TIMEOUT_TICKS`, not before. | REQ-PiCamera-005, REQ-PiCamera-008, REQ-PiCamera-009, REQ-PiCamera-010, REQ-PiCamera-011 |
| TimeoutDuringCameraCall | A tick at `CAPTURE_TIMEOUT_TICKS` while `acquire` has not run replies `TIMEOUT`; the later camera result sends no reply and closes the camera. | REQ-PiCamera-004, REQ-PiCamera-008, REQ-PiCamera-010 |
| LateFrameOfEarlierCaptureIgnored | A frame report of a timed-out capture does not answer the next request. | REQ-PiCamera-004, REQ-PiCamera-005 |
| NoBufferFails | An invalid or short allocation gives `NO_BUFFER`. | REQ-PiCamera-005, REQ-PiCamera-009, REQ-PiCamera-011 |
| PictureOutstandingFails | A request before the delivered picture returns gives `PICTURE_OUTSTANDING`. | REQ-PiCamera-005, REQ-PiCamera-020 |
| TooLargeFails | A JPEG larger than the buffer gives `TOO_LARGE` and the buffer is released. | REQ-PiCamera-005, REQ-PiCamera-009, REQ-PiCamera-010, REQ-PiCamera-011 |
| BusyDuringCapture | A request during a capture gets `BUSY` and the capture ends with the same reply. | REQ-PiCamera-012, REQ-PiCamera-013 |
| AcquireDroppedTimesOut | A request whose `acquire` finds the queue full gets `TIMEOUT`. | REQ-PiCamera-004, REQ-PiCamera-008 |
| FailureStepAndCode | Each failure site emits its own step value and the library return code. | REQ-PiCamera-023 |
| CameraReportedAtStart | The first tick gives `CameraFound` with the identification, or `CameraNotFound`, once, and every channel. | REQ-PiCamera-022, REQ-PiCamera-024 |
| CameraClosedAfterEachCapture | Success and each failure leave the camera closed. | REQ-PiCamera-014 |
| PingEchoed | A ping returns its key. | — |
| TelemetryAfterEachReply | Each reply and return publishes the Table 2 channels it changed, with their values. | REQ-PiCamera-015 |
| ReturnReleasesPicture | Returning the delivered picture releases it once and allows the next capture. | REQ-PiCamera-018 |
| UnknownReturnRejected | A buffer not delivered, or returned twice, is not released and emits `ReturnRejected`. | REQ-PiCamera-020, REQ-PiCamera-021 |
| RunWhileIdle | Ticks in `IDLE` after the first send no reply, event or telemetry. | REQ-PiCamera-004 |
| RandomRequestsAndFaults | Random requests, frames, ticks and returns keep one reply per request and no leaked buffer. | REQ-PiCamera-004, REQ-PiCamera-010, REQ-PiCamera-018 |
| REQ-PiCamera-016 | No test: inspection of the build inputs and linked libraries. | REQ-PiCamera-016 |
