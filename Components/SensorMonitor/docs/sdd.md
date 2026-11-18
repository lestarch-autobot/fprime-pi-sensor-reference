# PiSensor::SensorMonitor

## 1. Introduction

`SensorMonitor` turns the latest BMP280, MPU6050 and GPS readings into the
sensor telemetry of the PiSensor system: temperature, roll and pitch, gyro
rates, location, and a validity flag for temperature, attitude and location
fix. It decides validity from the age of each reading, from the identity
register of the MPU6050 and from the fix field of the GPS sentences that pass
through it. It reports a sensor that is lost and a sensor that returns, and it
hands the product manager one sample of every metric, with validity and sample
time, for a data product. Attitude is roll and pitch plus raw gyro rates; yaw
is not reported.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-SensorMonitor-001 | On each schedule call, the component shall publish temperature in degrees Celsius. | Unit Test |
| REQ-SensorMonitor-002 | On each schedule call, the component shall publish roll and pitch in degrees. | Unit Test |
| REQ-SensorMonitor-003 | Roll and pitch shall be within 0.1 degrees of the accelerometer gravity-vector angles. | Unit Test |
| REQ-SensorMonitor-004 | On each schedule call, the component shall publish three-axis gyro rates in degrees per second. | Unit Test |
| REQ-SensorMonitor-005 | On each schedule call, the component shall publish latitude and longitude (degrees) and altitude (metres). | Unit Test |
| REQ-SensorMonitor-006 | On each schedule call, the component shall publish temperature, attitude and fix validity. | Unit Test |
| REQ-SensorMonitor-007 | The component shall report a metric invalid while its newest reading is over 2 s old. | Unit Test |
| REQ-SensorMonitor-008 | The component shall report a metric invalid until its sensor delivers a first reading. | Unit Test |
| REQ-SensorMonitor-009 | The component shall report fix invalid while the newest GGA sentence reports no fix. | Unit Test |
| REQ-SensorMonitor-010 | The component shall report fix invalid while the newest GGA sentence lacks a fix field. | Unit Test |
| REQ-SensorMonitor-011 | The component shall report attitude invalid while the MPU6050 identity read does not return 0x68. | Unit Test |
| REQ-SensorMonitor-012 | The component shall emit `WARNING_HI` event `Bmp280Lost` once after 5 s without a BMP280 reading. | Unit Test |
| REQ-SensorMonitor-013 | The component shall emit `WARNING_HI` event `Mpu6050Lost` once after 5 s without an MPU6050 reading. | Unit Test |
| REQ-SensorMonitor-014 | The component shall emit `WARNING_HI` event `Mpu6050Lost` once when the identity read stops returning 0x68. | Unit Test |
| REQ-SensorMonitor-015 | The component shall emit `WARNING_HI` event `GpsSilent` once after 5 s without a GPS sentence. | Unit Test |
| REQ-SensorMonitor-016 | The component shall emit an `ACTIVITY_HI` event when a lost sensor delivers a reading again. | Unit Test |
| REQ-SensorMonitor-017 | The component shall report a metric valid on the first schedule call after its sensor returns. | Unit Test |
| REQ-SensorMonitor-018 | The component shall pass each GPS sentence it receives on, unchanged. | Unit Test |
| REQ-SensorMonitor-019 | On request, the component shall return every metric with its validity and sample time. | Unit Test |
| REQ-SensorMonitor-020 | A returned metric shall be invalid when its validity conditions fail at the request time. | Unit Test |
| REQ-SensorMonitor-021 | The MPU6050 identity read shall be compliant with RM-MPU-6000A-00 Rev. 4.2. | Unit Test |
| REQ-SensorMonitor-022 | The GGA fix field read shall be compliant with NMEA 0183 Version 4.11. | Unit Test |

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| MPU-6000 and MPU-6050 Register Map and Descriptions | RM-MPU-6000A-00 Rev. 4.2 | Datasheet | identity register address and value |
| NMEA 0183 Standard for Interfacing Marine Electronic Devices | Version 4.11 | Standard | GGA sentence, GPS quality indicator field |
