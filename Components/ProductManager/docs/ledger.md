# Campaign ledger: prodmgr (ProductManager)

Child of project campaign `fvp-2026-11-17-1`; node `comp_design_child`;
approver `project-campaign` (contract §9.2). `[V]` read from an artifact or
tool output, `[I]` inference.

## Setup

- [V] Skills source: lestarch-autobot/fprime `system-campaign-skills` at aa3ab031a6c67d40652e8047a2e1f9a8a8c2b26c; nasa/fprime#6388 open at session start.
- [V] UUT: lestarch-autobot/fprime-pi-sensor-reference, branch `design/prodmgr` cut from `design/ssdd` at ba498d76c87b83b2394523de6496df6cfd0e10e9.
- [V] Catalog read: nasa/fprime v4.4.2 (`Svc/DpWriter`, `Svc/DpManager`, `Svc/Ccsds/CfdpManager`, `Svc/FileDownlinkPorts`).
- Review bound: 3 per phase (source: default). Reviews LOCAL ONLY.
- Bench: not touched in this lane; bench facts are those of the project ledger.
- Needs checklist (contract): request + goals known; test configuration known for DESIGN (SSDD topology), `repo@sha` unknown until DEVELOPMENT; bench facts known from the project ledger (camera, BMP280, GPS absent today); approver known; seed not requested (project campaign runs the record).

## Decisions and proposals

| # | Phase | Item | Status |
|---|---|---|---|
| P1 | requirements | Camera time-out 20 s and storage time-out 5 s, so a capture ends within 30 s (REQ-PiSensor-010). REQ-ProductManager-018, -021 (20 and 5 ticks of the 1 Hz `run` port) | proposed |
| P2 | requirements | A partial product is a file of the product directory whose length differs from the length its data product header declares; removed after a failed capture and at start-up (REQ-PiSensor-029). `Svc.DpWriter` leaves the file of a failed write in place [V `DpWriter.cpp` `writeFile`]. REQ-ProductManager-022, -024; definition in the SDD Introduction | proposed |
| P3 | requirements | A name that is not a stored product (missing, partial, a directory, a path) is refused with `ProductNotFound`; the product of a capture in progress is not yet stored. REQ-ProductManager-033 | proposed |
| P4 | requirements | `DownlinkStalled` is emitted on a failed completion report of the file transfer; the 60 s no-progress timing is that of the CFDP timers (SSDD fault table: detected by `Cfdp`). `ProductManager` cannot see transfer progress on its ports. REQ-ProductManager-028 | proposed |
| P5 | requirements | Downlink, delete and list are accepted during a capture; a capture, a listing and a delete of a product other than the one in transfer are accepted during a downlink (rejections are limited to those the system requirements name). REQ-ProductManager-041 | proposed |
| P6 | requirements | A transfer request refused by the file transfer (busy or invalid) fails the command with `WARNING_LO`. REQ-ProductManager-029 (`DownlinkRefused`) | proposed |
| P7 | requirements | No telemetry channel: no allocated requirement names one. The sketch port `tlmOut` is dropped | proposed |
| P8 | requirements, round 1 | Sample age is judged in both directions: a metric is invalid when its sample time differs from capture time by more than 2 s. REQ-ProductManager-009, -010 | proposed |
| P9 | requirements, round 1 | `LIST_PRODUCTS`: `ACTIVITY_LO` `ProductStored` per product, at most 4 per `run` tick (plan event rate 5/s), then `ACTIVITY_HI` `ProductsListed(count)`; a listing during a listing is rejected. REQ-ProductManager-036 to -039 | proposed |
| P10 | requirements, round 1 | An empty picture fails the capture with `CaptureFailed`; a picture too large for a product buffer fails it with `StorageFailed` (no separate size constant). REQ-ProductManager-017, -020 | proposed |
| P11 | requirements, round 1 | A file system error on `DELETE`, `LIST_PRODUCTS` or the start-up scan gives `WARNING_HI` `FileSystemError`. REQ-ProductManager-042, -043 | proposed |
| P12 | requirements, round 1 | A late picture is returned and writes no product; a product whose written notification arrives outside a capture is removed. REQ-ProductManager-019, -023 | proposed |
| P13 | requirements, round 1 | Queue overflow: the picture buffer is returned to the camera and a command gets a busy response. REQ-ProductManager-044, -045 | proposed |
| N1 | note to parent | A stored product is judged by the length its header declares; `sysTester.CORRUPT_PRODUCT` must not overwrite the header length field, or the product stops being a stored product | open |
| N2 | note to parent | Samples are requested when the picture is delivered and judged within 2 s of capture time in both directions (P8); `piCamera` must deliver the picture within 1 s of the acquisition time it reports, or every metric is marked invalid | open |
| P14 | requirements, round 2 | A capture whose product name is that of a stored product fails with `StorageFailed`, so no stored product is overwritten. REQ-ProductManager-015, -046 | proposed |
| P15 | design | Interface changes against the sketch, shared with `sensorMonitor` and `piCamera`: `SamplesGet(ref samples: SampleSet)` returns the samples; `imageIn` is `PictureDone(context, status, captureTime, ref picture)`; `tlmOut` dropped (P7). Types defined in `Components/ProductManager/ProductManager.fpp` | proposed |
| P16 | design | The product name is computed with `DP_FILENAME_FORMAT` from container id and capture time, the rule of `Svc.DpWriter`; the container time tag is the capture time. Two captures collide only if the clock repeats a capture time | proposed |
| P17 | design | Informational events added: `DownlinkStarted`, `DownlinkComplete`, `ProductDeleted`, `ProductDiscarded` (one event per command, CPP-37) | proposed |
| N3 | note to parent | Topology: `run` at 1 Hz; `configure(productDirectory)` with the directory of `DataProducts`; the product buffer pool must hold one picture plus 200 bytes | open |

## Trace

System requirement (REQ-PiSensor-) to component rows (REQ-ProductManager-):

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

## Reviews

- Requirements round 1 [V record `review-requirements-requirements-review-round-1.md`, separate session 86f3b137]: must fix 23, could fix 12, disagreements 0. Close: all must-fix edited (rows renumbered 001 to 044; every row `Unit Test`); could-fix fixed except `req-unclear:REQ-ProductManager-020` declined (the system plan names `DownlinkStalled`; P4).
- Requirements round 2 [V record `review-requirements-requirements-review-round-2.md`]: must fix 4, could fix 4, disagreements 0 (the round-1 decline accepted by the reviewer). Close: all 8 edited (rows 002, 009, 015, 019, 021, 023, 034, 041, 044, new 045, 046, Table 4).
- Requirements round 3 [V record `review-requirements-requirements-review-round-3.md`]: must fix 0, could fix 3, disagreements 0. Loop closed at zero must-fix; the 3 could-fix edited (rows 038, 041, 046, Introduction, External References).
