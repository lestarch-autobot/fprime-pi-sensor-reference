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
| P1 | requirements | Camera time-out 20 s and storage time-out 5 s, so a capture ends within 30 s (REQ-PiSensor-010). REQ-ProductManager-012, -014 | proposed |
| P2 | requirements | A partial product is a file of the product directory whose length differs from the length its data product header declares; removed after a failed capture and at start-up (REQ-PiSensor-029). `Svc.DpWriter` leaves the file of a failed write in place [V `DpWriter.cpp` `writeFile`]. REQ-ProductManager-015, -016 | proposed |
| P3 | requirements | A name with a path separator is refused, so a command cannot reach a file outside the product directory. REQ-ProductManager-025 | proposed |
| P4 | requirements | `DownlinkStalled` is emitted on a failed completion report of the file transfer; the 60 s no-progress timing is that of the CFDP timers (SSDD fault table: detected by `Cfdp`). `ProductManager` cannot see transfer progress on its ports. REQ-ProductManager-020 | proposed |
| P5 | requirements | Downlink, delete and list are accepted during a capture; a delete or downlink of a product other than the one in transfer is accepted during a downlink. REQ-ProductManager-030 | proposed |
| P6 | requirements | A transfer request refused by the file transfer (busy or invalid) fails the command with `WARNING_LO`. REQ-ProductManager-021 | proposed |
| P7 | requirements | No telemetry channel: no allocated requirement names one. The sketch port `tlmOut` is dropped | proposed |
