# PiSensor::ProductManager

## 1. Introduction

`ProductManager` runs the capture, downlink, delete and list commands of the
PiSensor deployment. On a capture command it asks the camera for one picture,
asks the sensor monitor for the latest location, attitude and temperature, and
hands them to the storage as one data product; the storage notifies the
component when the product file is written. A stored product is a regular
file of the one product directory whose length equals the length its data
product header declares; its name is its file name. A partial product is any
other regular file of that directory. The component hands a named product to
the CFDP file transfer, removes a named product, and lists the stored products.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-ProductManager-001 | On a `CAPTURE` command, the component shall request one picture from the camera. | Unit Test |
| REQ-ProductManager-002 | On the picture of the capture in progress, the component shall request the latest samples. | Unit Test |
| REQ-ProductManager-003 | Each product shall hold one picture, capture time, location, attitude and temperature record. | Unit Test |
| REQ-ProductManager-004 | The picture record of each product shall equal the delivered picture, byte for byte. | Unit Test |
| REQ-ProductManager-005 | Each metric record shall hold the Table 2 fields as delivered by its source. | Unit Test |
| REQ-ProductManager-006 | Each product file shall comply with the F Prime data product file format. | Unit Test |
| REQ-ProductManager-007 | The capture time record shall equal the acquisition time delivered with the picture. | Unit Test |
| REQ-ProductManager-008 | Each metric record shall carry its sample time and a validity mark. | Unit Test |
| REQ-ProductManager-009 | The component shall mark valid each valid-reported metric sampled within 2 s of capture time. | Unit Test |
| REQ-ProductManager-010 | The component shall mark invalid each metric sampled more than 2 s from capture time. | Unit Test |
| REQ-ProductManager-011 | The component shall mark invalid each metric its source reports invalid. | Unit Test |
| REQ-ProductManager-012 | The component shall return each delivered picture buffer to the camera exactly once. | Unit Test |
| REQ-ProductManager-013 | On the written notification of its product, the component shall complete `CAPTURE` successfully. | Unit Test |
| REQ-ProductManager-014 | On each successful capture, the component shall emit `ACTIVITY_HI` event `ProductWritten` naming the product. | Unit Test |
| REQ-ProductManager-015 | A capture shall leave every stored product unchanged. | Integration Test |
| REQ-ProductManager-016 | The component shall fail `CAPTURE` with `WARNING_HI` event `CaptureFailed` when the camera reports failure. | Unit Test |
| REQ-ProductManager-017 | The component shall fail `CAPTURE` with `CaptureFailed` when the delivered picture is empty. | Unit Test |
| REQ-ProductManager-018 | The component shall fail `CAPTURE` with `CaptureFailed` when no picture arrives within 20 `run` ticks. | Unit Test |
| REQ-ProductManager-019 | The component shall write no product for a picture not of the current capture. | Unit Test |
| REQ-ProductManager-020 | The component shall fail `CAPTURE` with `WARNING_HI` event `StorageFailed` when no product buffer fits. | Unit Test |
| REQ-ProductManager-021 | `CAPTURE` shall fail with `StorageFailed` when no written notification arrives in 5 `run` ticks. | Unit Test |
| REQ-ProductManager-022 | After a failed capture, the component shall remove every partial product. | Unit Test |
| REQ-ProductManager-023 | The component shall remove a product whose written notification is not of the current capture. | Unit Test |
| REQ-ProductManager-024 | At start-up, the component shall remove every partial product. | Unit Test |
| REQ-ProductManager-025 | A `CAPTURE` during a capture shall fail with `WARNING_LO` event `CommandRejected` and not disturb it. | Unit Test |
| REQ-ProductManager-026 | On `DOWNLINK`, the component shall request file transfer of the named product under its name. | Unit Test |
| REQ-ProductManager-027 | The component shall complete `DOWNLINK` successfully when the file transfer reports success. | Unit Test |
| REQ-ProductManager-028 | The component shall fail `DOWNLINK` with `WARNING_HI` event `DownlinkStalled` when the transfer reports failure. | Unit Test |
| REQ-ProductManager-029 | The component shall fail `DOWNLINK` with `WARNING_LO` event `DownlinkRefused` when the transfer refuses the request. | Unit Test |
| REQ-ProductManager-030 | The component shall leave the product file unchanged by a downlink, complete or failed. | Unit Test |
| REQ-ProductManager-031 | A `DOWNLINK` command during a downlink shall fail with `CommandRejected` and not disturb that downlink. | Unit Test |
| REQ-ProductManager-032 | After a `CAPTURE` or `DOWNLINK` completes or fails, the component shall accept the next one. | Unit Test |
| REQ-ProductManager-033 | A `DOWNLINK` or `DELETE` naming no stored product shall fail with `WARNING_LO` event `ProductNotFound`. | Unit Test |
| REQ-ProductManager-034 | On `DELETE`, the component shall remove the named product, then complete the command successfully. | Unit Test |
| REQ-ProductManager-035 | A `DELETE` command naming the product being downlinked shall fail with `CommandRejected`. | Unit Test |
| REQ-ProductManager-036 | On `LIST_PRODUCTS`, the component shall emit `ACTIVITY_LO` event `ProductStored` naming each stored product. | Unit Test |
| REQ-ProductManager-037 | The component shall emit at most 4 `ProductStored` events per `run` tick. | Unit Test |
| REQ-ProductManager-038 | The component shall complete `LIST_PRODUCTS` with `ACTIVITY_HI` event `ProductsListed` giving the product count. | Unit Test |
| REQ-ProductManager-039 | A `LIST_PRODUCTS` command during a listing shall fail with `CommandRejected`. | Unit Test |
| REQ-ProductManager-040 | `DOWNLINK`, `DELETE` and `LIST_PRODUCTS` shall act on every product stored before a restart. | Unit Test |
| REQ-ProductManager-041 | The component shall accept every command Table 4 does not reject, during any activity. | Unit Test |
| REQ-ProductManager-042 | The component shall fail a command with `WARNING_HI` event `FileSystemError` on a file system error. | Unit Test |
| REQ-ProductManager-043 | At start-up, the component shall emit `FileSystemError` when the product directory cannot be read. | Unit Test |
| REQ-ProductManager-044 | The component shall return to the camera each picture it cannot queue. | Unit Test |
| REQ-ProductManager-045 | The component shall give a busy response to each command it cannot queue. | Unit Test |
| REQ-ProductManager-046 | `CAPTURE` shall fail with `StorageFailed` when its product name is that of a stored product. | Unit Test |

Table 1: commands.

| Command | Argument |
|---|---|
| `CAPTURE` | none |
| `DOWNLINK` | product name |
| `DELETE` | product name |
| `LIST_PRODUCTS` | none |

An activity is a capture, a downlink or a listing; the current capture is the one in progress.

Table 2: metric records.

| Record | Fields |
|---|---|
| Temperature | temperature (°C) |
| Attitude | roll, pitch (°); gyro rate x, y, z (°/s) |
| Location | latitude, longitude (°); altitude (m) |

Table 4: commands rejected with `CommandRejected`.

| Command | Rejected during |
|---|---|
| `CAPTURE` | a capture |
| `DOWNLINK` | a downlink |
| `DELETE` | the downlink of the named product |
| `LIST_PRODUCTS` | a listing |

Table 3: system requirement (REQ-PiSensor-) traced by the component rows.

| System | Component rows |
|---|---|
| 004 | 001, 004 |
| 005 | 002, 003, 004, 005, 006, 012, 013, 015, 044, 046 |
| 006 | 007 |
| 007 | 008, 009 |
| 008 | 010 |
| 009 | 011 |
| 010 | 013, 018, 021 |
| 011 | 014 |
| 012 | 026, 027, 029 |
| 014 | 034, 042 |
| 028 | 016, 017, 018 |
| 029 | 019, 022, 023, 024 |
| 030 | 025, 041, 045 |
| 031 | 020, 021 |
| 032 | 033 |
| 033 | 031, 041 |
| 034 | 028 |
| 035 | 030, 032 |
| 038 | 036, 037, 038, 039, 040, 042, 043 |
| 041 | 035, 041 |

### External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| PiSensor SSDD | `docs/ssdd.md` at `ba498d7` | System design | Allocated requirements, decisions D1 to D13 |
| F Prime data product file format | nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md` | Format | REQ-ProductManager-006 |
