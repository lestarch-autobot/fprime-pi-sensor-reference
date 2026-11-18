# ProductManager component system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, ids 1000 to 1051 (the project plan uses 10 to 231). Event rate: at most 5 events per second in any window; `LIST_PRODUCTS` emits at most 4 `ProductStored` events per second by design.
- UUT: component `PiSensor::ProductManager`, instance `productManager`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Test deployment: the project's base deployment plus `sysTester` (SSDD decision D13), the configuration of the project plan `SystemTester/test/int/plan.json`; its scope lines on the ground system, record content, completeness and clocks apply unchanged.
- This plan holds the component rows the project plan delegates (`delegated: prodmgr`): REQ-PiSensor-011, -014, -030, -032, -033, -041, and the one requirement of the component verified by integration test (REQ-ProductManager-015). Every other requirement is verified by the unit-test list of the SDD.
- `sysTester` commands used: `MARK(id)`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `CORRUPT_PRODUCT(name)` (planted fault only). `CORRUPT_PRODUCT` overwrites the first two bytes of the picture record and leaves the header, so the file stays a stored product (ledger note N1).
- Order: the prototype block (L0-1 to L2-4, L5-1, L5-2, L6-1 to L6-3, L7-1 last, TCP), then the flight block (L5-3 to L5-6, RFM69). L7-1 runs after the flight block on the prototype image when both blocks run in one record.
- Downlink-in-progress tests run on the flight image: over RFM69 a product takes at least 60 s (project plan link budget), over TCP about a second, too short to send a second command inside the transfer. Each requires a transfer of at least 10 s, else UNVERIFIED.
- Capture-in-progress tests rely on the capture taking longer than one command round trip (SSDD: a capture may take seconds); each requires the second command dispatched before `ProductWritten`, else UNVERIFIED. L0 bench confirmation measures the capture duration.
- Out of scope: product content, timing of metrics, camera, storage, link and restart faults (project plan L2, L3, L5).

## 1 Entry gates
- Unit tests of `ProductManager` pass with line coverage at or above the plan's threshold.
- Images built from the base deployment `repo@sha` sent with the DEVELOPMENT stretch plus the component; L0-1 passes on the bench.
- Product directory on its own 64 MB file system, empty at the start of each test (bench teardown removes the products of the test; L7-1 has no teardown).
- Bench recipe: Pi Camera attached; ground Pi with RFM69 for the flight block. Sensors need not answer: metrics are marked invalid and the capture still succeeds.

## 2 Test levels
L0 provenance and feasibility · L2 functional · L5 fault paths · L6 negative controls · L7 final state. No L3 test: restart behaviour of products is in the project plan (L3-1 to L3-4). No L4 endurance test: no requirement has an endurance bound.

## 3 Test entries

Window rule: rows from the **last** `sysTester.Marker(id=START)` row that precedes the first `sysTester.Marker(id=END)` row following it, through that END row plus the END `sysTester.MARK` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 0; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Standard absence block (STD-ERR): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.OpCodeError count == 1; event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched.

ID:        L0-1
Title:     Image identity and marker round-trip
Purpose:   Proves the running image is the manifest's prototype image and the marker round-trips.
Covers:    —
Setup:     Prototype image running on the Raspberry Pi 5; link up.
Procedure: MARK(1000); VERSION(ALL); bracket (2 Heartbeat samples); MARK(0xA5A5); MARK(1001).
Window:    Marker(id=1000) … Marker(id=1001)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  Version events equal the manifest describe strings; three Marker events in order, ids byte-exact.
Planted faults:none

ID:        L2-1
Title:     Capture names its product
Purpose:   Proves a successful capture emits ProductWritten naming the one new product file.
Covers:    REQ-ProductManager-014
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1010); CAPTURE(); LIST_DIR(products); MARK(1011).
Window:    Marker(id=1010) … Marker(id=1011)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s.
Evidence:  check: event productManager.ProductWritten count == 1 (ACTIVITY_HI, names P); check: the sysTester.DirListing event names P and no other file; check: ABS.
Planted faults:capture_twice

ID:        L2-2
Title:     Second capture leaves the first product unchanged
Purpose:   Proves a second capture names a new product and leaves the first unchanged.
Covers:    REQ-ProductManager-014, REQ-ProductManager-015
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1012); CAPTURE(); DUMP_SHA256(P1, 1); CAPTURE(); DUMP_SHA256(P1, 2); LIST_DIR(products); MARK(1013).
Window:    Marker(id=1012) … Marker(id=1013)
Pass rule: named checks declared in the integration test (test_L2_2).
Evidence:  check: event productManager.ProductWritten count == 2 with different names (P1, P2); check: the two sysTester.Sha256 events of P1 are equal; check: the sysTester.DirListing event names P1 and P2 only; check: ABS.
Planted faults:corrupt_first_product

ID:        L2-3
Title:     Captures around a delete leave the first product unchanged
Purpose:   Proves captures and a delete of another product leave a stored product unchanged.
Covers:    REQ-ProductManager-015, REQ-ProductManager-034
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1014); CAPTURE(); DUMP_SHA256(P1, 1); CAPTURE(); DELETE(P2); CAPTURE(); DUMP_SHA256(P1, 2); LIST_DIR(products); MARK(1015).
Window:    Marker(id=1014) … Marker(id=1015)
Pass rule: named checks declared in the integration test (test_L2_3).
Evidence:  check: event productManager.ProductWritten count == 3 with three different names (P1, P2, P3); check: event productManager.ProductDeleted count == 1 and names P2; check: the two sysTester.Sha256 events of P1 are equal; check: the sysTester.DirListing event names P1 and P3 only; check: ABS.
Planted faults:none

ID:        L2-4
Title:     Delete removes the named product
Purpose:   Proves DELETE removes the named product and no other, before its command response.
Covers:    REQ-ProductManager-034
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1016); CAPTURE(); CAPTURE(); DUMP_SHA256(P2, 1); DELETE(P1); LIST_DIR(products); DUMP_SHA256(P2, 2); LIST_PRODUCTS(); MARK(1017).
Window:    Marker(id=1016) … Marker(id=1017)
Pass rule: named checks declared in the integration test (test_L2_4).
Evidence:  check: event productManager.ProductDeleted count == 1 and names P1; check: the sysTester.DirListing event names P2 only; check: the two sysTester.Sha256 events of P2 are equal; check: event productManager.ProductStored count == 1 and names P2; check: event productManager.ProductsListed count == 1 with count 1; check: ABS.
Planted faults:delete_other

ID:        L5-1
Title:     Capture during a capture
Purpose:   Proves a CAPTURE during a capture is rejected and the first capture stores its product.
Covers:    REQ-ProductManager-025
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1020); CAPTURE() without waiting for completion; CAPTURE(); wait event productManager.ProductWritten; LIST_DIR(products); MARK(1021).
Window:    Marker(id=1020) … Marker(id=1021)
Pass rule: named checks declared in the integration test (test_L5_1). metrics: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s.
Evidence:  require (else UNVERIFIED, the race was lost): the second CAPTURE is dispatched before the ProductWritten event. check: event productManager.CommandRejected count == 1 (WARNING_LO, reason CAPTURE_IN_PROGRESS); check: event productManager.ProductWritten count == 1; check: the sysTester.DirListing event names one file, the product named by ProductWritten; check: ABS.
Planted faults:second_capture_dropped

ID:        L5-2
Title:     Capture after a rejected capture
Purpose:   Proves a rejected CAPTURE does not disturb the capture in progress or the next one.
Covers:    REQ-ProductManager-025
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1022); CAPTURE() without waiting for completion; CAPTURE(); wait event productManager.ProductWritten; CAPTURE(); LIST_DIR(products); MARK(1023).
Window:    Marker(id=1022) … Marker(id=1023)
Pass rule: named checks declared in the integration test (test_L5_2).
Evidence:  require (else UNVERIFIED, the race was lost): the second CAPTURE is dispatched before the first ProductWritten event. check: event productManager.CommandRejected count == 1 (reason CAPTURE_IN_PROGRESS); check: event productManager.ProductWritten count == 2 with different names; check: the sysTester.DirListing event names those two files only; check: ABS.
Planted faults:none

ID:        L5-3
Title:     Downlink during a downlink
Purpose:   Proves a DOWNLINK during a downlink is rejected and the first transfer delivers its product.
Covers:    REQ-ProductManager-031
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering, product directory empty.
Procedure: MARK(1030); CAPTURE(); CAPTURE(); DUMP_SHA256(P1, 1); DOWNLINK(P1) without waiting for completion; wait event productManager.DownlinkStarted; DOWNLINK(P2); wait CFDP transaction finished at the ground; MARK(1031).
Window:    Marker(id=1030) … Marker(id=1031)
Pass rule: named checks declared in the integration test (test_L5_3). metrics: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require).
Evidence:  check: event productManager.CommandRejected count == 1 (WARNING_LO, reason DOWNLINK_IN_PROGRESS); check: event productManager.DownlinkStarted count == 1; check: exactly one file arrived and its name is P1; check: sha256 of record/raw/files/<P1> == hash in the sysTester.Sha256 event; check: event productManager.DownlinkComplete count == 1; check: ABS.
Planted faults:none

ID:        L5-4
Title:     Repeated downlink of the product in transfer
Purpose:   Proves a DOWNLINK naming the product in transfer is rejected without a second transfer.
Covers:    REQ-ProductManager-031
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering, product directory empty.
Procedure: MARK(1032); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted; DOWNLINK(P); wait CFDP transaction finished at the ground; MARK(1033).
Window:    Marker(id=1032) … Marker(id=1033)
Pass rule: named checks declared in the integration test (test_L5_4). metrics: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require).
Evidence:  check: event productManager.CommandRejected count == 1 (reason DOWNLINK_IN_PROGRESS); check: exactly one CFDP transaction at the ground, finished complete; check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; check: ABS.
Planted faults:none

ID:        L5-5
Title:     Delete during the product's downlink
Purpose:   Proves a DELETE of the product in transfer is rejected and the product is delivered and kept.
Covers:    REQ-ProductManager-035
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering, product directory empty.
Procedure: MARK(1034); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted; DELETE(P); wait CFDP transaction finished at the ground; DUMP_SHA256(P, 2); LIST_DIR(products); MARK(1035).
Window:    Marker(id=1034) … Marker(id=1035)
Pass rule: named checks declared in the integration test (test_L5_5). metrics: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require).
Evidence:  check: event productManager.CommandRejected count == 1 (WARNING_LO, reason PRODUCT_IN_DOWNLINK); check: event productManager.ProductDeleted count == 0; check: sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event; check: the two sysTester.Sha256 events are equal; check: the sysTester.DirListing event names P; check: ABS.
Planted faults:delete_before_downlink

ID:        L5-6
Title:     Delete after the product's downlink
Purpose:   Proves a DELETE rejected during the downlink succeeds once the transfer has ended.
Covers:    REQ-ProductManager-035, REQ-ProductManager-034
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering, product directory empty.
Procedure: MARK(1036); CAPTURE(); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted; DELETE(P); wait CFDP transaction finished at the ground; wait event productManager.DownlinkComplete; DELETE(P); LIST_DIR(products); MARK(1037).
Window:    Marker(id=1036) … Marker(id=1037)
Pass rule: named checks declared in the integration test (test_L5_6). metrics: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require).
Evidence:  check: event productManager.CommandRejected count == 1 (reason PRODUCT_IN_DOWNLINK) and it precedes event productManager.DownlinkComplete; check: event productManager.ProductDeleted count == 1 and it follows DownlinkComplete; check: the sysTester.DirListing event names no file; check: ABS.
Planted faults:none

ID:        L6-1
Title:     Downlink of a missing product
Purpose:   Proves a DOWNLINK naming no stored product is rejected and nothing is sent.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1040); CAPTURE(); LIST_DIR(products); DOWNLINK(Dp_missing.fxd); wait 10 s; LIST_DIR(products); MARK(1041).
Window:    Marker(id=1040) … Marker(id=1041)
Pass rule: named checks declared in the integration test (test_L6_1).
Evidence:  check: event productManager.ProductNotFound count == 1 (WARNING_LO, names Dp_missing.fxd); check: event productManager.DownlinkStarted count == 0; check: no CFDP transaction starts at the ground in the window; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.
Planted faults:downlink_existing

ID:        L6-2
Title:     Delete of a missing product
Purpose:   Proves a DELETE naming no stored product is rejected and removes nothing.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1042); CAPTURE(); LIST_DIR(products); DELETE(Dp_missing.fxd); LIST_DIR(products); MARK(1043).
Window:    Marker(id=1042) … Marker(id=1043)
Pass rule: named checks declared in the integration test (test_L6_2).
Evidence:  check: event productManager.ProductNotFound count == 1 (names Dp_missing.fxd); check: event productManager.ProductDeleted count == 0; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.
Planted faults:none

ID:        L6-3
Title:     Delete with a path as name
Purpose:   Proves a DELETE whose name is a path to a stored product is rejected and removes nothing.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1044); CAPTURE(); LIST_DIR(products); DELETE(./P); LIST_DIR(products); MARK(1045).
Window:    Marker(id=1044) … Marker(id=1045)
Pass rule: named checks declared in the integration test (test_L6_3).
Evidence:  check: event productManager.ProductNotFound count == 1; check: event productManager.ProductDeleted count == 0; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board for the independent final-state check.
Covers:    REQ-ProductManager-014
Setup:     Prototype image running, link up, camera answering, product directory empty.
Procedure: MARK(1050); CAPTURE(); DUMP_SHA256(P, 1); LIST_DIR(products); MARK(1051).
Window:    Marker(id=1050) … Marker(id=1051)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  check: event productManager.ProductWritten count == 1 (names P); the DirListing event names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt; the auditor compares it with the hash of the Sha256 event.
Planted faults:none

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-ProductManager-001 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-002 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-003 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-004 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-005 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-006 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-007 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-008 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-009 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-010 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-011 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-012 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-013 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-014 | L2-1, L2-2, L7-1; unit test |  |
| REQ-ProductManager-015 | L2-2, L2-3 |  |
| REQ-ProductManager-016 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-017 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-018 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-019 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-020 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-021 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-022 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-023 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-024 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-025 | L5-1, L5-2; unit test |  |
| REQ-ProductManager-026 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-027 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-028 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-029 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-030 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-031 | L5-3, L5-4; unit test |  |
| REQ-ProductManager-032 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-033 | L6-1, L6-2, L6-3; unit test |  |
| REQ-ProductManager-034 | L2-3, L2-4, L5-6; unit test |  |
| REQ-ProductManager-035 | L5-5, L5-6; unit test |  |
| REQ-ProductManager-036 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-037 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-038 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-039 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-040 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-041 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-042 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-043 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-044 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-045 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-046 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-047 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |
| REQ-ProductManager-048 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |

## 5 Metrics
- L2-1: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s
- L5-1: CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s
- L5-3: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require)
- L5-4: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require)
- L5-5: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require)
- L5-6: CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require)

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): capture_twice (stimulus; L2-1); corrupt_first_product (uut-state; L2-2); delete_before_downlink (uut-state; L5-5); delete_other (stimulus; L2-4); downlink_existing (stimulus; L6-1); second_capture_dropped (stimulus; L5-1).

## 7 Not covered
- Every requirement marked `UT only`: verified by the unit-test list, and at system level by the project plan where it traces a system requirement.
- REQ-ProductManager-046 (name in use): the clock cannot be made to repeat a capture time on the bench without stepping the system clock of a shared machine; unit test only.
- A listing during a listing, a delete during a listing and queue overflow: timing not reachable through the ground link at 5 events per second; unit tests.
- Today's bench cannot run these tests: the camera and the ground Pi are absent.

## 8 Decision log
1. 2026-11-17 designer — the component tests run in the project's base deployment with `sysTester`; no component-only deployment.
2. 2026-11-17 designer — downlink-in-progress tests run on the flight image, where a transfer lasts long enough to command inside it.
3. 2026-11-17 designer — planted faults rewrite or insert commands only; one is `uut-state` (`corrupt_first_product`).
