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
| P13 | requirements, round 1 | Queue overflow: the picture buffer is returned to the camera and a command gets a busy response. REQ-ProductManager-044 | proposed |
| N1 | note to parent | A stored product is judged by the length its header declares; `sysTester.CORRUPT_PRODUCT` must not overwrite the header length field, or the product stops being a stored product | open |

## Reviews

- Requirements round 1 [V record `review-requirements-requirements-review-round-1.md`, separate session 86f3b137]: must fix 23, could fix 12, disagreements 0. Close: all must-fix edited (rows renumbered 001 to 044; every row `Unit Test`); could-fix fixed except `req-unclear:REQ-ProductManager-020` declined (the system plan names `DownlinkStalled`; P4).
