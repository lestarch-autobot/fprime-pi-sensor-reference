# PiSensor System Software Design Document

## Introduction

PiSensor is an F Prime deployment for a Raspberry Pi 5. The ask, verbatim:

> I would like you to develop a system that runs on a raspberry pi 5, and communicates with the following sensors:
>
> 1. BMP280
> 2. MPU6050
> 3. PI Camera
> 4. Nmea GPS
>
> The system shall have the goal of reading these sensors and combining the key sensor metrics: location, attitude, and temperature + a picture into a single data product for downlinking using CFDP.  The sensors should stream telemetry, and pictures should be captured, correlated, and made into a data product in response to a command.
>
> System communication should go through an RFM69 packet radio.
>
> My expectation is that the PI camera be rewritten using standard PI libraries that are easy to install rather than using the OpenCV camera setup from fprime-examples as that is complex and overkill.
>
> Note: your development testbed is the PI used for soak testing trials attached to your PI workstation.  Be respectful of other users.  A ground system PI w/ RFM69 will be attached to your workstation for ground testing and a camera will be attached to the soak PI after SSDD approval.  Prototype the initial system over TCP.
>
> Since this is an automatic process, please ask questions now and then proceed through SSDD review!

Attitude is roll and pitch plus raw gyro rates; yaw is not reported. The
ground system is fprime-yamcs. Bench parts: MPU6050 on I2C bus 1 (0x68) and
RFM69 on SPI0 CE1 are identified; BMP280 wiring, GPS receiver and port, Pi
Camera module and RFM69 band are recorded here once identified. The goal is a functional deployment with
respect to the ask, every system requirement proven in system tests on the
complete testbed.

## Requirements

Terms: *data product* is the stored file a capture produces. *Capture time*
is the time the picture is acquired. *Sensor telemetry* is Table 1.

| ID | Requirement | Verification |
|---|---|---|
| REQ-PiSensor-001 | The system shall downlink BMP280 temperature telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-002 | The system shall downlink MPU6050 attitude telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-003 | The system shall downlink GPS location telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-004 | On a capture command, the system shall capture one JPEG of at least 640x480 pixels. | Integration Test |
| REQ-PiSensor-005 | Each successful capture shall produce one data product holding picture, location, attitude and temperature. | Integration Test |
| REQ-PiSensor-006 | Each data product shall carry its capture time. | Integration Test |
| REQ-PiSensor-007 | Each metric marked valid shall carry a sample time within 2 s of capture time. | Integration Test |
| REQ-PiSensor-008 | A data product shall mark invalid each metric older than 2 s. | Integration Test |
| REQ-PiSensor-009 | A data product shall mark location invalid when the GPS reports no fix. | Integration Test |
| REQ-PiSensor-010 | The system shall complete a capture command within 30 s of dispatch. | Integration Test |
| REQ-PiSensor-011 | Each successful capture shall emit an `ACTIVITY_HI` event naming its data product. | Integration Test |
| REQ-PiSensor-012 | On a downlink command, the system shall send the named data product by CFDP class 2. | Integration Test |
| REQ-PiSensor-013 | A downlinked data product shall be byte-identical to the on-board data product. | Integration Test |
| REQ-PiSensor-014 | On a delete command, the system shall remove the named data product. | Integration Test |
| REQ-PiSensor-015 | In the flight configuration, commands, telemetry, events and CFDP files shall pass over the RFM69. | Integration Test |
| REQ-PiSensor-016 | In the prototype configuration, commands, telemetry, events and CFDP files shall pass over TCP. | Integration Test |
| REQ-PiSensor-017 | Commands, telemetry, events and CFDP files shall interoperate with the fprime-yamcs ground system. | Integration Test |
| REQ-PiSensor-018 | During a CFDP downlink, sensor telemetry shall continue at least once every 10 s. | Integration Test |
| REQ-PiSensor-019 | The system shall emit a `WARNING_HI` event within 10 s of BMP280 read failure. | Integration Test |
| REQ-PiSensor-020 | The system shall emit a `WARNING_HI` event within 10 s of MPU6050 read failure. | Integration Test |
| REQ-PiSensor-021 | The system shall emit a `WARNING_HI` event within 10 s of the last GPS sentence. | Integration Test |
| REQ-PiSensor-022 | Sensor telemetry shall report a metric invalid while its sensor is failed. | Integration Test |
| REQ-PiSensor-023 | Sensor telemetry shall resume within 10 s of a sensor's return, without a restart. | Integration Test |
| REQ-PiSensor-024 | GPS telemetry shall report fix invalid while the receiver reports no fix. | Integration Test |
| REQ-PiSensor-025 | The system shall discard NMEA sentences that fail their checksum. | Integration Test |
| REQ-PiSensor-026 | The system shall report a BMP280 or MPU6050 with a wrong identity register as failed. | Integration Test |
| REQ-PiSensor-027 | The system shall discard uplink frames that fail their integrity check. | Integration Test |
| REQ-PiSensor-028 | A capture whose camera is absent or fails shall fail its command and emit `WARNING_HI`. | Integration Test |
| REQ-PiSensor-029 | A failed capture shall leave no data product, complete or partial. | Integration Test |
| REQ-PiSensor-030 | A capture command during a capture shall fail with `WARNING_LO` and not disturb that capture. | Integration Test |
| REQ-PiSensor-031 | A capture that cannot store its data product shall fail its command and emit `WARNING_HI`. | Integration Test |
| REQ-PiSensor-032 | A downlink or delete command naming a missing data product shall fail with `WARNING_LO`. | Integration Test |
| REQ-PiSensor-033 | A downlink command during a downlink shall fail with `WARNING_LO` and not disturb that downlink. | Integration Test |
| REQ-PiSensor-034 | A CFDP transfer that does not complete shall emit a `WARNING_HI` event. | Integration Test |
| REQ-PiSensor-035 | An incomplete CFDP transfer shall leave the data product intact for a repeated downlink command. | Integration Test |
| REQ-PiSensor-036 | Within 10 s of the end of a link outage of at least 60 s, commanding and telemetry shall resume without a restart. | Integration Test |
| REQ-PiSensor-037 | Within 10 s of the end of a ground-system outage of at least 60 s, commanding and telemetry shall resume without a restart. | Integration Test |
| REQ-PiSensor-038 | Data products stored before a link outage, ground-system outage or restart shall remain downlinkable after it. | Integration Test |
| REQ-PiSensor-039 | After a restart, the system shall resume sensor telemetry without ground commands within 60 s. | Integration Test |
| REQ-PiSensor-040 | The camera software shall use only Raspberry Pi OS packaged camera libraries, not OpenCV. | Inspection |
| REQ-PiSensor-041 | The system shall meet REQ-PiSensor-001 to -040 on a Raspberry Pi 5 under 64-bit Raspberry Pi OS 13. | Integration Test |

Table 1: sensor telemetry.

| Sensor | Metric | Unit |
|---|---|---|
| BMP280 | temperature, validity | degrees Celsius |
| MPU6050 | roll, pitch, validity | degrees |
| MPU6050 | gyro rate about x, y, z | degrees per second |
| GPS | latitude, longitude | degrees |
| GPS | altitude | metres |
| GPS | fix validity | valid / invalid |

### Decisions for approval

The ask leaves these open. The author decided them; the human rules on each
at Approve SSDD.

| # | Question | Decision | Rows |
|---|---|---|---|
| D1 | Numeric bounds | Telemetry 2 s; stale after 2 s; fault event 10 s; capture 30 s; resume 10 s after an outage of 60 s or more; telemetry 60 s after restart | 001-003, 007, 008, 010, 019-021, 023, 036, 037, 039 |
| D2 | Downlink trigger | Separate command, not automatic after capture | 012 |
| D3 | CFDP class | Class 2 (acknowledged): the radio link is lossy | 012 |
| D4 | Telemetry during a file downlink | Continues, at least once every 10 s | 018 |
| D5 | Picture | JPEG, at least 640x480 | 004 |
| D6 | Downlink command during a downlink | Rejected | 033 |
| D7 | After a sensor fault | Metric flagged invalid; recovery within 10 s of return, no restart | 022, 023 |
| D8 | Bench parts | Identified on the bench and named in the Introduction | - |
| D9 | BMP280 pressure | Not required: the ask names temperature only | 001 |
| D10 | Storage | Delete command; no automatic storage bound | 014 |
