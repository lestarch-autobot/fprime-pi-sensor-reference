# PiSensor::ProductManager

## 1. Introduction

`ProductManager` runs the capture, downlink, delete and list commands of the
PiSensor deployment. On a capture command it asks the camera for one picture,
asks the sensor monitor for the latest location, attitude and temperature,
and stores them as one data product file. It hands a named product file to
the CFDP file transfer, removes a named product file, and lists the stored
products. A product name is the file name of the product in the one product
directory.

## 2. Requirements

| ID | Requirement | Verification |
|---|---|---|
| REQ-ProductManager-001 | On a `CAPTURE` command, the component shall request one picture from the camera. | Unit Test |
| REQ-ProductManager-002 | On a delivered picture, the component shall request the latest sample of every metric. | Unit Test |
| REQ-ProductManager-003 | Each product shall hold one picture, capture time, location, attitude and temperature record. | Unit Test |
| REQ-ProductManager-004 | The capture time record shall equal the acquisition time delivered with the picture. | Unit Test |
| REQ-ProductManager-005 | Each metric record shall carry its sample time and a validity mark. | Unit Test |
| REQ-ProductManager-006 | The component shall mark invalid each metric sampled over 2 s from capture time. | Unit Test |
| REQ-ProductManager-007 | The component shall mark invalid each metric its source reports invalid. | Unit Test |
| REQ-ProductManager-008 | The component shall return each delivered picture buffer to the camera exactly once. | Unit Test |
| REQ-ProductManager-009 | On the written notification of its product, the component shall complete `CAPTURE` successfully. | Unit Test |
| REQ-ProductManager-010 | On each successful capture, the component shall emit `ACTIVITY_HI` event `ProductWritten` naming the product. | Integration Test |
| REQ-ProductManager-011 | The component shall fail `CAPTURE` with `WARNING_HI` event `CaptureFailed` when the camera reports failure. | Unit Test |
| REQ-ProductManager-012 | The component shall fail `CAPTURE` with `CaptureFailed` when no picture arrives within 20 s. | Unit Test |
| REQ-ProductManager-013 | The component shall fail `CAPTURE` with `WARNING_HI` event `StorageFailed` when no product buffer is available. | Unit Test |
| REQ-ProductManager-014 | The component shall fail `CAPTURE` with `StorageFailed` when no written notification arrives within 5 s. | Unit Test |
| REQ-ProductManager-015 | After a failed capture, the component shall remove every partial product file. | Unit Test |
| REQ-ProductManager-016 | At start-up, the component shall remove every partial product file. | Unit Test |
| REQ-ProductManager-017 | A `CAPTURE` command during a capture shall fail with `WARNING_LO` and not disturb that capture. | Integration Test |
| REQ-ProductManager-018 | On a `DOWNLINK` command, the component shall request file transfer of the named product. | Unit Test |
| REQ-ProductManager-019 | The component shall complete `DOWNLINK` successfully when the file transfer reports success. | Unit Test |
| REQ-ProductManager-020 | The component shall fail `DOWNLINK` with `WARNING_HI` event `DownlinkStalled` when the file transfer reports failure. | Unit Test |
| REQ-ProductManager-021 | The component shall fail `DOWNLINK` with `WARNING_LO` when the file transfer refuses the request. | Unit Test |
| REQ-ProductManager-022 | The component shall leave the product file unchanged by a downlink, complete or failed. | Unit Test |
| REQ-ProductManager-023 | A `DOWNLINK` command during a downlink shall fail with `WARNING_LO` and not disturb that downlink. | Integration Test |
| REQ-ProductManager-024 | A `DOWNLINK` or `DELETE` command naming a missing product shall fail with `WARNING_LO`. | Integration Test |
| REQ-ProductManager-025 | A `DOWNLINK` or `DELETE` command whose name contains a path separator shall fail with `WARNING_LO`. | Unit Test |
| REQ-ProductManager-026 | On a `DELETE` command, the component shall remove the named product file. | Integration Test |
| REQ-ProductManager-027 | A `DELETE` command naming the product being downlinked shall fail with `WARNING_LO`. | Integration Test |
| REQ-ProductManager-028 | On a `LIST_PRODUCTS` command, the component shall emit one event per stored product. | Unit Test |
| REQ-ProductManager-029 | The component shall find stored products by reading the product directory at each command. | Unit Test |
| REQ-ProductManager-030 | The component shall accept `DOWNLINK`, `DELETE` and `LIST_PRODUCTS` during a capture. | Unit Test |

System requirement traced by each row (REQ-PiSensor-):

| Component rows | System requirement |
|---|---|
| 001 | 004 |
| 002, 003, 005, 008, 009 | 005 |
| 004 | 006 |
| 005, 006 | 007, 008 |
| 007 | 009 |
| 012, 014 | 010 |
| 010 | 011 |
| 018, 019, 021 | 012 |
| 026 | 014 |
| 011, 012 | 028 |
| 015, 016 | 029 |
| 017, 030 | 030 |
| 013, 014 | 031 |
| 024, 025 | 032 |
| 023 | 033 |
| 020 | 034 |
| 022 | 035 |
| 028, 029 | 038 |
| 027 | 041 |

### External References

| Document | Identifier / Revision | Type | Governs |
|---|---|---|---|
| PiSensor SSDD | `docs/ssdd.md` at `ba498d7` | System design | Allocated requirements, decisions D1 to D13 |
| F Prime data product file | nasa/fprime v4.4.2, `Fw/Dp/docs/sdd.md` | Format | Product file layout |
