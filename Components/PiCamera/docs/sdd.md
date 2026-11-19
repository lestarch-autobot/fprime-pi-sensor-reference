# PiSensor::PiCamera

## 1. Introduction

`PiCamera` manages the Raspberry Pi Camera attached to the CSI port of a
Raspberry Pi 5. On a capture command it acquires one picture, encodes it as a
JPEG, reads the latest temperature, acceleration and location readings with
their sample times from the telemetry store, derives roll and pitch from the
acceleration, and writes the picture and the metrics as one data product
container. Storage and downlink of the container belong to the data product
components it hands the container to.

Open: camera model, datasheet (title, revision) and the identification the
camera library reports. The camera is not yet attached to the bench. A camera
that libcamera does not support reopens REQ-PiCamera-001, 002 and 003.

## 2. Requirements

| ID | Requirement | Traces to | Verification |
|---|---|---|---|
| REQ-PiCamera-001 | For each accepted `CAPTURE` command the component shall acquire one picture from the Pi Camera after it receives the command. | REQ-PiSensor-004 | Integration Test |
| REQ-PiCamera-002 | Each stored picture shall be one JFIF file, SOI to EOI, `PICTURE_WIDTH` x `PICTURE_HEIGHT` pixels. | REQ-PiSensor-004 | Integration Test |
| REQ-PiCamera-003 | The component shall use only Raspberry Pi OS packaged camera and JPEG libraries, not OpenCV. | REQ-PiSensor-004 | Inspection |
| REQ-PiCamera-004 | Each successful capture shall send exactly one `Capture` container holding one `Picture` record and one `Metrics` record. | REQ-PiSensor-005 | Unit Test |
| REQ-PiCamera-005 | The `Metrics` record shall hold the latitude, longitude and temperature of the latest Table 3 readings, unchanged. | REQ-PiSensor-005 | Unit Test |
| REQ-PiCamera-006 | The `Metrics` record shall hold roll = atan2(ay, az) and pitch = atan2(-ax, sqrt(ay² + az²)) in degrees, from the latest acceleration reading (ax, ay, az). | REQ-PiSensor-005 | Unit Test |
| REQ-PiCamera-007 | The capture time shall be the system time read when the frame arrives from the camera, stored in the `Metrics` record and as the container time tag. | REQ-PiSensor-006 | Unit Test |
| REQ-PiCamera-008 | The `Metrics` record shall hold, for location, attitude and temperature, the time tag the telemetry store returns with the reading. | REQ-PiSensor-006 | Unit Test |
| REQ-PiCamera-009 | The component shall end the wait for a frame `FRAME_TIMEOUT_MS` after the camera starts and fail the capture with `TIMEOUT`. | REQ-PiSensor-007 | Unit Test |
| REQ-PiCamera-010 | A capture shall fail with `SENSOR_STALE` when a sample time differs from the capture time by more than `METRIC_MAX_AGE_MS` or has another time base. | REQ-PiSensor-014 | Unit Test |
| REQ-PiCamera-011 | A capture shall fail with `SENSOR_NO_DATA` when the telemetry store returns no value for a Table 3 channel or a value that does not decode. | REQ-PiSensor-014 | Unit Test |
| REQ-PiCamera-012 | A capture shall fail with `METRIC_INVALID` when a reading holds a non-finite value, a latitude outside ±90, a longitude outside ±180 or an acceleration of magnitude 0. | REQ-PiSensor-005 | Unit Test |
| REQ-PiCamera-013 | A failed capture shall send no container. | REQ-PiSensor-005, REQ-PiSensor-014 | Unit Test |
| REQ-PiCamera-014 | Each `CAPTURE` command shall get exactly one command response: `OK` after the container is sent, `EXECUTION_ERROR` on failure. | Component | Unit Test |
| REQ-PiCamera-015 | Each failed `CAPTURE` command shall emit one `CaptureFailed` (`WARNING_HI`) with the Table 1 reason and step of the failure and the failing library call's return code, 0 when none failed. | Component | Unit Test |
| REQ-PiCamera-016 | A capture shall fail with `NO_CAMERA` when the camera library lists no camera, and with `CAMERA_ERROR` when a camera or JPEG library call fails. | Component | Unit Test |
| REQ-PiCamera-017 | A capture shall fail with `TOO_LARGE` when the JPEG exceeds `PICTURE_MAX_SIZE` bytes, and with `NO_CONTAINER` when no container buffer is obtained. | Component | Unit Test |
| REQ-PiCamera-018 | A `CAPTURE` command received before an earlier capture ended shall fail with `BUSY` and shall not change the earlier capture's result. | Component | Unit Test |
| REQ-PiCamera-019 | After a failed capture, the next capture shall succeed without a restart once the cause is gone. | Component | Unit Test |
| REQ-PiCamera-020 | Each accepted `CAPTURE` command shall emit one `CaptureStarted` (`ACTIVITY_LO`) before acquisition, and each successful capture one `CaptureCompleted` (`ACTIVITY_HI`) with the JPEG size. | Component | Unit Test |
| REQ-PiCamera-021 | The component shall publish each Table 2 channel whenever its value changes. | Component | Unit Test |
| REQ-PiCamera-022 | The component shall answer each health ping from its thread with the key it received. | Component | Unit Test |

`Traces to` names the system requirement a row derives from. `Component` marks
fault, warning and reporting behaviour the system design assigns to this
component without a system requirement.

Table 1: failure reasons and steps. `BUSY` is decided on receipt of the command, before any other reason; the others in the order of section 3.5.

| Reason | Meaning | Steps |
|---|---|---|
| `BUSY` | An earlier capture has not ended | `RECEIVE` |
| `NO_CAMERA` | The camera library lists no camera | `DETECT` |
| `CAMERA_ERROR` | A camera or JPEG library call failed | `OPEN`, `CONFIGURE`, `START`, `FRAME`, `ENCODE` |
| `TIMEOUT` | No frame within `FRAME_TIMEOUT_MS` | `FRAME` |
| `SENSOR_NO_DATA` | No usable reading in the telemetry store | `TEMPERATURE`, `ATTITUDE`, `LOCATION` |
| `SENSOR_STALE` | Sample time too far from the capture time | `TEMPERATURE`, `ATTITUDE`, `LOCATION` |
| `METRIC_INVALID` | A reading holds a value outside its range | `TEMPERATURE`, `ATTITUDE`, `LOCATION` |
| `TOO_LARGE` | JPEG larger than `PICTURE_MAX_SIZE` | `ENCODE` |
| `NO_CONTAINER` | No container buffer obtained | `CONTAINER` |

Table 2: telemetry.

| Channel | Content |
|---|---|
| `CapturesCompleted` | Captures that sent a container since start |
| `CapturesFailed` | `CAPTURE` commands that failed since start |
| `LastPictureSize` | Size in bytes of the last stored JPEG |

Table 3: readings taken from the telemetry store.

| Metric | Channel | Type | Fields used |
|---|---|---|---|
| Temperature | `Bmp280.bmpManager.Reading` | `Bmp280.Bmp280Data` | `temperature` (°C) |
| Attitude | `MpuImu.imuManager.Reading` | `MpuImu.ImuData` | `acceleration` x, y, z |
| Location | `NmeaGps.gpsManager.Reading` | `NmeaGps.GpsData` | `latitude`, `longitude` (degrees) |

External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| libcamera public API | `libcamera-dev` 0.8.0+rpt20261104-1, Raspberry Pi OS 13 (trixie) archive | Other | camera discovery, configuration, frame request |
| libjpeg-turbo API | `libjpeg62-turbo-dev` 1:2.1.5-4, Debian 13 (trixie) main, as shipped by Raspberry Pi OS 13 | Other | JPEG compression calls |
| JPEG File Interchange Format | JFIF 1.02; ITU-T T.81 | Standard | picture encoding |
| F Prime data products | `nasa/fprime` `devel@83221ba`, `Fw/Dp`, `Svc/DpManager`, `Svc/DpWriter` | Other | container format, buffer and send ports |
| F Prime telemetry store | `nasa/fprime` `devel@83221ba`, `Svc/TlmChan` port `TlmGet` | Other | latest channel value and time tag |
| Sensor reading types | `fprime-community/fprime-sensors@e5d83d1`, `Bmp280`, `MpuImu`, `NmeaGps` `Types.fpp` | Other | layout and units of the Table 3 readings |

## 3. Design

### 3.1 Component Diagram

```
                           ┌────────────────────┐
cmdIn : Fw.Cmd            [ ]                  [ ] tlmGetOut : Fw.TlmGet
                           │      PiCamera      │
pingIn : Svc.Ping         [ ]     (active)     [ ] productGetOut : Fw.DpGet
                           │                    │
                           │                   [ ] productSendOut : Fw.DpSend
                           │                    │
                           │                   [ ] pingOut : Svc.Ping
                           └────────────────────┘
  special ports: cmdRegOut, cmdResponseOut, eventOut, textEventOut, tlmOut, timeGetOut
```

`PiCamera` is an active component: its thread makes the camera calls, which take seconds.

### 3.2 Ports

| Name | Kind | Type | Purpose |
|---|---|---|---|
| `cmdIn` | command recv | `Fw.Cmd` | `CAPTURE`, a guarded command |
| `tlmGetOut` | output | `Fw.TlmGet` | Latest value and time tag of a Table 3 channel |
| `productGetOut` | product get | `Fw.DpGet` | Gets the container buffer, synchronously |
| `productSendOut` | product send | `Fw.DpSend` | Sends the filled container |
| `pingIn`, `pingOut` | async input (drop), output | `Svc.Ping` | Health ping of the component thread |
| `acquire` | internal, drop | — | Work of one capture, on the component thread |

Two threads enter the component.

| Thread | Runs | Touches |
|---|---|---|
| Command dispatcher | `CAPTURE` handler | `m_busy`, under the component guard |
| Component thread | `acquire`, `pingIn` | Everything else; `m_busy` under the guard |

### 3.3 State

| Member | Values | Meaning |
|---|---|---|
| `m_busy` | bool | A capture is accepted and has not ended |
| `m_opCode`, `m_cmdSeq` | — | Command the capture answers |
| `m_jpeg` | `PICTURE_MAX_SIZE` bytes | Encoded picture until it is copied into the container |
| `m_completed`, `m_failed` | U32 | Counts behind `CapturesCompleted`, `CapturesFailed`; wrap to 0 after 4294967295 |
| `m_channels` | 3 channel identifiers | Table 3 channels, set by `configure` |

At start `m_busy` is false, the counts are 0 and the camera is closed. Nothing is kept across a restart.

The camera is closed outside `acquire`: every capture opens it and closes it again, on success and on failure.

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> CAPTURING: CAPTURE
    CAPTURING --> CAPTURING: CAPTURE (BUSY)
    CAPTURING --> IDLE: container sent (OK)
    CAPTURING --> IDLE: a step fails (Table 1)
```

### 3.4 Configuration and Setup

```fpp
constant PICTURE_WIDTH = 640
constant PICTURE_HEIGHT = 480
constant PICTURE_MAX_SIZE = 262144
constant FRAME_TIMEOUT_MS = 10000
constant SETTLE_FRAMES = 10
constant METRIC_MAX_AGE_MS = 2000
```

Picture size, largest JPEG, longest wait for the frame, frames discarded while exposure settles, and the largest difference between a sample time and the capture time.

```fpp
instance piCamera: PiSensor.PiCamera base id 0x10008000 queue size 5 stack size 1048576 priority 30
```

`configure(temperatureChannel, attitudeChannel, locationChannel)` is called once before the component thread starts, with the identifiers of the Table 3 channels in the topology.

| Port | Connects to |
|---|---|
| `tlmGetOut` | `CdhCore.tlmSend.TlmGet` |
| `productGetOut` | `DataProducts.Subtopology.productGetIn` |
| `productSendOut` | `DataProducts.Subtopology.productSendIn` |
| `pingIn`, `pingOut` | `CdhCore.$health` |

The buffers of `DataProducts.Subtopology` hold at least one `Capture` container: `PICTURE_MAX_SIZE` bytes plus the `Metrics` record and the container overhead (`DataProductsConfig.BuffMgr.dpBufferStoreSize`).

The camera is reached through one interface class (`detect`, `open`, `configure`, `start`, `waitFrame`, `stop`, `close`) implemented with libcamera; JPEG encoding uses libjpeg-turbo. Both are Raspberry Pi OS packages. Unit tests substitute the interface. The CMake option `PICAMERA_NO_CAMERA` selects an implementation that detects no camera; with the option off, a build that finds no libcamera fails.

### 3.5 Handlers

#### CAPTURE

Under the guard: when `m_busy` is set it emits `CaptureFailed(BUSY, RECEIVE, 0)` and responds `EXECUTION_ERROR`. Otherwise it sets `m_busy`, keeps the opcode and sequence number, emits `CaptureStarted` and sends `acquire`.

#### acquire

It runs the steps below in order. The first step that fails closes the camera, emits `CaptureFailed` with its Table 1 reason and step, counts the failure, responds `EXECUTION_ERROR` and clears `m_busy`; no later step runs.

1. Detect, open, configure and start the camera (`DETECT`, `OPEN`, `CONFIGURE`, `START`).
2. Wait for the frame, at most `FRAME_TIMEOUT_MS` (`FRAME`). The camera interface discards `SETTLE_FRAMES` frames and hands over the next one.
3. Read the system time: the capture time.
4. Read the three Table 3 channels through `tlmGetOut` and check each one in the order `TEMPERATURE`, `ATTITUDE`, `LOCATION`: a value is present and decodes, its time tag is within `METRIC_MAX_AGE_MS` of the capture time, its fields are in range. Compute roll and pitch.
5. Encode the frame as a JPEG into `m_jpeg` (`ENCODE`), then stop and close the camera.
6. Get a `Capture` container buffer for the two records through `productGetOut` (`CONTAINER`).
7. Write the `Metrics` record and the `Picture` record, set the container time tag to the capture time and send the container through `productSendOut`.
8. Count the capture, publish the channels, emit `CaptureCompleted`, respond `OK` and clear `m_busy`.

The readings are read after the frame arrives and before encoding, so their age does not include the encoding time.

`m_busy` is set and cleared under the guard; no camera call, port call or wait happens while the guard is held.

#### pingIn

It echoes the key on `pingOut`.

## 4. Data Product Format

Container `Capture`, one per successful capture, default priority, no processing. Its time tag is the capture time.

| Record | Type | Content |
|---|---|---|
| `Metrics` | `CaptureMetrics` | Capture time, metrics and their sample times |
| `Picture` | `U8` array | The JPEG, SOI to EOI; the array size is the JPEG length |

`CaptureMetrics`, in serialization order:

| Field | Type | Unit | Content |
|---|---|---|---|
| `captureTime` | `Fw.TimeValue` | — | Time the frame arrived |
| `latitude` | F64 | degrees, north positive | From `NmeaGps.GpsData` |
| `longitude` | F64 | degrees, east positive | From `NmeaGps.GpsData` |
| `locationTime` | `Fw.TimeValue` | — | Sample time of latitude and longitude |
| `roll` | F32 | degrees | Derived from the acceleration |
| `pitch` | F32 | degrees | Derived from the acceleration |
| `attitudeTime` | `Fw.TimeValue` | — | Sample time of the acceleration |
| `temperature` | F32 | °C | From `Bmp280.Bmp280Data` |
| `temperatureTime` | `Fw.TimeValue` | — | Sample time of the temperature |

## 5. Ground Interface

| Command | Kind | Arguments | Action |
|---|---|---|---|
| `CAPTURE` | guarded | — | Acquire one picture and store it with the latest metrics as one data product |

| Telemetry | Type | Content |
|---|---|---|
| `CapturesCompleted` | U32 | Captures that sent a container since start |
| `CapturesFailed` | U32 | `CAPTURE` commands that failed since start |
| `LastPictureSize` | U32 | Size in bytes of the last stored JPEG |

| Event | Severity | Arguments | Meaning |
|---|---|---|---|
| `CaptureStarted` | `ACTIVITY_LO` | — | A `CAPTURE` command is accepted; acquisition begins |
| `CaptureCompleted` | `ACTIVITY_HI` | `bytes` | The container was sent; `bytes` is the JPEG size |
| `CaptureFailed` | `WARNING_HI` | `reason`, `step`, `code` | A `CAPTURE` command failed |

The component has no parameters.

## 6. Example Uses

```mermaid
sequenceDiagram
    participant G as cmdDisp
    participant C as piCamera
    participant L as camera library
    participant T as tlmSend
    participant D as dpMgr
    G->>C: CAPTURE
    C-->>G: event CaptureStarted
    C->>L: detect, open, configure, start
    L-->>C: frame
    C->>T: TlmGet x 3
    T-->>C: readings and time tags
    C->>L: stop, close
    C->>D: productGetOut
    D-->>C: container buffer
    C->>D: productSendOut (Metrics, Picture)
    C-->>G: event CaptureCompleted, response OK
```

A capture with the GPS receiver silent ends after step 4 with `CaptureFailed(SENSOR_STALE, LOCATION, 0)` or, when the receiver never reported, `CaptureFailed(SENSOR_NO_DATA, LOCATION, 0)`, a command response `EXECUTION_ERROR` and no container.

## 7. Idiosyncrasies

- The command response `OK` means the container was handed to the data product components. The file is written later by `dpWriter`, which reports `FileWritten` or a write error with its own events; the component does not learn of a write failure.
- `NmeaGps.GpsData` has no fix flag. Without a fix the receiver's channel is not updated, so a capture fails with `SENSOR_STALE` or `SENSOR_NO_DATA` at `LOCATION`.
- Roll and pitch assume the sensor is at rest; under acceleration they are wrong by the angle between the measured acceleration and gravity. Yaw is not available.
- A `CAPTURE` command is refused with `BUSY` from its acceptance until the earlier capture's response, at most `FRAME_TIMEOUT_MS` plus the camera start and encoding times.
- A camera library call other than the frame wait that does not return blocks the component thread; the health ping then goes unanswered and later `CAPTURE` commands get `BUSY`.
- `PICTURE_WIDTH`, `PICTURE_HEIGHT`, `PICTURE_MAX_SIZE`, `FRAME_TIMEOUT_MS`, `SETTLE_FRAMES` and `METRIC_MAX_AGE_MS` are compile-time constants; changing one needs a rebuild.
- The picture is held twice during a capture: in `m_jpeg` and in the container.

## 8. Tests

REQ-PiCamera-001 and 002 are verified on the bench by the system tests of the project (`test/int/plan.json`, tests L2-3 to L2-6), which read the picture record of the downlinked product. REQ-PiCamera-003 is verified by inspection of the build inputs and of the libraries the image links.

Unit tests substitute the camera interface, the telemetry store and the data product ports.

| Unit test | Description | Requirements |
|---|---|---|
| NominalCapture | A capture sends one container with one `Metrics` and one `Picture` record holding the substitute's JPEG, and responds `OK` once. | REQ-PiCamera-004, REQ-PiCamera-014 |
| MetricsCopied | Latitude, longitude and temperature in the record equal the readings in the store. | REQ-PiCamera-005 |
| RollPitch | Roll and pitch equal the formula for accelerations along +x, -x, +y, -y, +z, -z and one oblique vector. | REQ-PiCamera-006 |
| CaptureTime | The capture time in the record and the container time tag equal the time set when the substitute hands over the frame, not the command time. | REQ-PiCamera-007 |
| SampleTimes | The three sample times in the record equal three different time tags in the store. | REQ-PiCamera-008 |
| FrameTimeout | No frame: the wait is asked for `FRAME_TIMEOUT_MS` and the capture fails with `TIMEOUT` at `FRAME`. | REQ-PiCamera-009, REQ-PiCamera-015 |
| StaleReading | For each channel: a time tag `METRIC_MAX_AGE_MS` from the capture time passes, 1 ms more fails with `SENSOR_STALE`, earlier and later; another time base fails. | REQ-PiCamera-010, REQ-PiCamera-013 |
| MissingReading | For each channel: invalid status, empty value and a value too short to decode fail with `SENSOR_NO_DATA` at its step. | REQ-PiCamera-011, REQ-PiCamera-013 |
| InvalidMetric | NaN and infinity in each field, latitude ±90 passes and beyond fails, longitude ±180 passes and beyond fails, acceleration (0, 0, 0) fails, with `METRIC_INVALID`. | REQ-PiCamera-012, REQ-PiCamera-013 |
| NoCamera | No camera listed fails with `NO_CAMERA` at `DETECT`. | REQ-PiCamera-016, REQ-PiCamera-015 |
| CameraErrors | A failure at each of `OPEN`, `CONFIGURE`, `START`, `FRAME`, `ENCODE` fails with `CAMERA_ERROR`, that step and the substitute's return code, and closes the camera. | REQ-PiCamera-016, REQ-PiCamera-015 |
| TooLarge | A JPEG of `PICTURE_MAX_SIZE` bytes passes; one byte more fails with `TOO_LARGE`. | REQ-PiCamera-017 |
| NoContainer | A failed container request fails with `NO_CONTAINER`; nothing is sent. | REQ-PiCamera-017, REQ-PiCamera-013 |
| FailureResponse | Every failure above gives one `EXECUTION_ERROR` response, one `CaptureFailed`, no `CaptureCompleted` and no container. | REQ-PiCamera-013, REQ-PiCamera-014, REQ-PiCamera-015 |
| BusyDuringCapture | A `CAPTURE` during a capture gets `BUSY` at `RECEIVE` and one `EXECUTION_ERROR`; the capture in progress ends with the same container as without it. | REQ-PiCamera-018, REQ-PiCamera-014 |
| RecoveryAfterFailure | After each failure reason, a capture with the cause removed succeeds. | REQ-PiCamera-019 |
| Events | An accepted capture emits `CaptureStarted` once before the first camera call; a success emits `CaptureCompleted` with the JPEG size. | REQ-PiCamera-020 |
| TelemetryOnChange | Each success and failure publishes the Table 2 channels it changed, with their values. | REQ-PiCamera-021 |
| Ping | A ping is echoed with its key. | REQ-PiCamera-022 |
| RandomSequences | Random sequences of captures, busy commands and injected failures keep one response per command and the counts equal to the responses. | REQ-PiCamera-014, REQ-PiCamera-018, REQ-PiCamera-021 |

Component Development Checklist: [checklist.md](checklist.md)
