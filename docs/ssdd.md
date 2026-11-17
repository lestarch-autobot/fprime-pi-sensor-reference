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
ground system is fprime-yamcs. The goal is a functional deployment with
respect to the ask, every system requirement proven in system tests on the
complete testbed.

## Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-PiSensor-001 | The system shall downlink BMP280 temperature telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-002 | The system shall downlink MPU6050 roll, pitch and gyro-rate telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-003 | The system shall downlink GPS latitude, longitude, altitude and fix-validity telemetry at least once every 2 s. | Integration Test |
| REQ-PiSensor-004 | On a capture command, the system shall capture one Pi Camera picture as a JPEG. | Integration Test |
| REQ-PiSensor-005 | Each successful capture shall produce one data product holding picture, location, attitude and temperature. | Integration Test |
| REQ-PiSensor-006 | Each data product metric shall carry a sample time within 2 s of capture time. | Integration Test |
| REQ-PiSensor-007 | The system shall complete a capture command within 30 s of dispatch. | Integration Test |
| REQ-PiSensor-008 | On a downlink command, the system shall send the named data product by CFDP. | Integration Test |
| REQ-PiSensor-009 | A downlinked data product shall be byte-identical to the on-board file. | Integration Test |
| REQ-PiSensor-010 | Commands, telemetry, events and CFDP files shall all pass over the RFM69 radio link. | Integration Test |
| REQ-PiSensor-011 | A prototype configuration shall carry the same traffic over TCP instead of the radio. | Integration Test |
| REQ-PiSensor-012 | The system shall emit a `WARNING_HI` event within 10 s of BMP280 read failure. | Integration Test |
| REQ-PiSensor-013 | The system shall emit a `WARNING_HI` event within 10 s of MPU6050 read failure. | Integration Test |
| REQ-PiSensor-014 | The system shall emit a `WARNING_HI` event within 10 s of GPS sentence loss. | Integration Test |
| REQ-PiSensor-015 | GPS telemetry shall report fix invalid while the receiver reports no fix. | Integration Test |
| REQ-PiSensor-016 | A capture with the camera unavailable shall fail its command, emit `WARNING_HI`, and produce no product. | Integration Test |
| REQ-PiSensor-017 | A capture command received during a capture shall fail with a `WARNING_LO` event. | Integration Test |
| REQ-PiSensor-018 | A data product shall mark each metric older than 2 s as invalid. | Integration Test |
| REQ-PiSensor-019 | A capture that cannot store its product shall fail its command and emit `WARNING_HI`. | Integration Test |
| REQ-PiSensor-020 | A downlink command naming a missing product shall fail with a `WARNING_LO` event. | Integration Test |
| REQ-PiSensor-021 | An incomplete CFDP transfer shall leave the on-board product intact for a repeated downlink command. | Integration Test |
| REQ-PiSensor-022 | After a link outage of 60 s, commanding and telemetry shall resume without a restart. | Integration Test |
| REQ-PiSensor-023 | Products captured before a link or ground-system outage shall remain downlinkable after it. | Integration Test |
| REQ-PiSensor-024 | After a restart, the system shall resume sensor telemetry without ground commands within 60 s. | Integration Test |
| REQ-PiSensor-025 | The camera software shall use only Raspberry Pi OS packaged camera libraries, not OpenCV. | Inspection |
| REQ-PiSensor-026 | The deployment shall run on a Raspberry Pi 5 under 64-bit Raspberry Pi OS. | Integration Test |
