# PiSensor::SensorMonitor

## 1. Introduction

`SensorMonitor` turns the latest BMP280, MPU6050 and GPS readings into the
sensor telemetry of the PiSensor system: temperature, roll and pitch, gyro
rates and location, with a validity flag for temperature, attitude and
location. It decides validity from the age and range of each reading, from the
identity register of the MPU6050 and from the GPS quality indicator of the GGA
sentences that pass through it. It reports a sensor that is lost and a sensor
that returns, and it hands the product manager every metric with validity and
reading time for a data product. Attitude is roll and pitch plus raw gyro
rates; yaw is not reported.

The identity register is read as the MPU-6000 and MPU-6050 Register Map and
Descriptions, RM-MPU-6000A-00 Rev. 4.2, defines it: the bench MPU6050 on I2C
bus 1, address 0x68, returns 0x68 from register 0x75. The GPS receiver is not
identified on the bench yet; its identification reopens REQ-SensorMonitor-009,
-013 to -016 for GPS, and -022.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-SensorMonitor-001 | On each schedule call, the component shall publish every Table 1 channel. | Unit Test |
| REQ-SensorMonitor-002 | Each value channel shall carry its Table 1 value, computed from the latest source reading. | Unit Test |
| REQ-SensorMonitor-003 | Roll and pitch shall be within 0.1 degrees of their Table 1 formulas. | Unit Test |
| REQ-SensorMonitor-004 | A value channel shall carry zero until its source delivers a first reading. | Unit Test |
| REQ-SensorMonitor-005 | A metric shall be reported invalid while its reading is over 2 s old. | Unit Test |
| REQ-SensorMonitor-006 | A metric shall be reported invalid while its reading time is after the current time. | Unit Test |
| REQ-SensorMonitor-007 | A metric shall be reported invalid until its source delivers a first reading. | Unit Test |
| REQ-SensorMonitor-008 | A metric shall be reported invalid while its reading is outside its Table 1 limits. | Unit Test |
| REQ-SensorMonitor-009 | The component shall report location invalid unless the newest GGA quality indicator is 1 to 8. | Unit Test |
| REQ-SensorMonitor-010 | The component shall read the MPU6050 identity register on each schedule call. | Unit Test |
| REQ-SensorMonitor-011 | The component shall report attitude invalid unless the latest identity read returned the identity value. | Unit Test |
| REQ-SensorMonitor-012 | A metric shall be reported valid while no condition of REQ-SensorMonitor-005 to -011 holds. | Unit Test |
| REQ-SensorMonitor-013 | A sensor shall become lost when one of its Table 2 loss conditions holds. | Unit Test |
| REQ-SensorMonitor-014 | The component shall emit the sensor's `WARNING_HI` Table 2 loss event once per loss. | Unit Test |
| REQ-SensorMonitor-015 | A lost sensor shall return when none of its Table 2 loss conditions holds. | Unit Test |
| REQ-SensorMonitor-016 | The component shall emit the sensor's `ACTIVITY_HI` Table 2 return event once per return. | Unit Test |
| REQ-SensorMonitor-017 | The component shall pass each received GPS sentence on once, in order, unchanged. | Unit Test |
| REQ-SensorMonitor-018 | On request, the component shall return every Table 1 metric with validity and reading time. | Unit Test |
| REQ-SensorMonitor-019 | Returned validity shall follow REQ-SensorMonitor-005 to -012 with reading age taken at the request time. | Unit Test |
| REQ-SensorMonitor-020 | Schedule calls, GPS sentences and sample requests shall be handled one at a time. | Inspection |
| REQ-SensorMonitor-021 | The MPU6050 identity read shall be compliant with RM-MPU-6000A-00 Rev. 4.2. | Unit Test |
| REQ-SensorMonitor-022 | The GGA quality indicator read shall be compliant with NMEA 0183 Version 4.11. | Unit Test |

Table 1 — metrics. A reading is the value set a sensor's manager component
last published, with the time it published it (the reading time). Age is the
current time minus the reading time. A value that is not a finite number is
outside its limits.

| Metric | Validity channel | Source reading | Value channel | Unit | Value | Limits |
|---|---|---|---|---|---|---|
| Temperature | `TemperatureValid` | BMP280 | `Temperature` | degC | temperature | -40 to 85 |
| Attitude | `AttitudeValid` | MPU6050 | `Roll` | deg | atan2(a_y, a_z) | acceleration (a_x, a_y, a_z) not zero, each axis -16 to 16 g |
| | | | `Pitch` | deg | atan2(-a_x, sqrt(a_y^2 + a_z^2)) | as `Roll` |
| | | | `GyroX`, `GyroY`, `GyroZ` | deg/s | rotation rate x, y, z, unchanged | -2000 to 2000 |
| Location | `FixValid` | GPS | `Latitude` | deg | latitude | -90 to 90 |
| | | | `Longitude` | deg | longitude | -180 to 180 |
| | | | `Altitude` | m | altitude | -1000 to 100000 |

Table 2 — sensors. Counts start at start-up; a new reading is one whose
reading time differs from that of the schedule call before. The identity value
is 0x68.

| Sensor | Loss condition | Loss event | Return event |
|---|---|---|---|
| BMP280 | the last 5 schedule calls saw no new BMP280 reading | `Bmp280Lost` | `Bmp280Returned` |
| MPU6050 | the last 5 schedule calls saw no new MPU6050 reading; or the latest identity read failed or returned another value than the identity value | `Mpu6050Lost` | `Mpu6050Returned` |
| GPS | the last 5 schedule calls saw no GPS sentence | `GpsSilent` | `GpsReturned` |

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| MPU-6000 and MPU-6050 Register Map and Descriptions | RM-MPU-6000A-00 Rev. 4.2 | Datasheet | identity register address and value |
| NMEA 0183 Standard for Interfacing Marine Electronic Devices | Version 4.11 | Standard | GGA sentence, GPS quality indicator field |
