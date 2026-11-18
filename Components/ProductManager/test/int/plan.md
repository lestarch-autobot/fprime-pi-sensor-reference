# ProductManager component system test plan

## 0 Scope
L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, ids 1000 to 1051 (the project plan uses 10 to 231). Event rate: at most 5 events per second in any window; `LIST_PRODUCTS` emits at most 4 `ProductStored` events per second by design.
- UUT: component `PiSensor::ProductManager`, instance `productManager`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.
- Test deployment: the project's base deployment plus `sysTester` (SSDD decision D13), the configuration of the project plan `SystemTester/test/int/plan.json`; its scope lines on the ground system, record content, completeness and clocks apply unchanged.
- This plan holds the component rows the project plan delegates (`delegated: prodmgr`): REQ-PiSensor-011, -014, -030, -032, -033, -041, and the one requirement of the component verified by integration test (REQ-ProductManager-015). Every other requirement is verified by the unit-test list of the SDD.
- `sysTester` commands used: `MARK(id)`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `CORRUPT_PRODUCT(name)` (planted fault only). `CORRUPT_PRODUCT` overwrites the first two bytes of the picture record and leaves the header, so the file stays a stored product (ledger note N1). Dependency on the project's harness lane: `LIST_DIR`, `DUMP_SHA256`, `CORRUPT_PRODUCT` and the events `DirListing` and `Sha256` are not in `sysTester` at `deploy/base`@383a9ce; their formats are fixed there, and the helpers `dir_listing_equals`, `dir_listings_equal`, `sha_events_equal`, `ground_file_hash_equals` and the event patterns for the two events are written against them at the stage-2 refresh. `DUMP_SHA256` of a missing file must fail its command and emit no `Sha256` event.
- Pass rules: every check and precondition of a test is listed by name in its evidence line; a name is a predicate of the plan grammar or the text of a registered helper (`planted_faults.py`), and is the name the stimulus test declares. Event arguments are read with `event_patterns`, taken from the formats of `ProductManager.fpp`. STD holds no UUT fact: a failed command is judged by the check `event cmdDisp.OpCodeError count == 0` (nominal tests) or by the helper `only_failed_command` (rejection tests), never by a precondition.
- Flight block budget [I]: project plan link budget, RFM69 at 19200 bit/s carries 2400 byte/s; events of this plan during a transfer are at most 3 in 10 s (under 100 byte/s) beside 1 Hz telemetry, so markers and rejection events fit while CFDP uses the rest. L0-2 confirms the marker round-trip on the flight image; the bench check replaces the estimate.
- Teardown is a bench action inside the window (`action: teardown`, files removed over ssh, logged in bench-actions.log); every test starts with `LIST_DIR(products)` and the check that it names no file.
- Order: the flight block (L0-2, L5-3 to L5-6, RFM69), then the prototype block (L0-1, L2-1 to L2-4, L5-1, L5-2, L6-1 to L6-4, TCP), L7-1 last.
- Downlink-in-progress tests run on the flight image: over RFM69 a product takes at least 60 s (project plan link budget), over TCP about a second, too short to send a second command inside the transfer. Each requires the second command dispatched inside the transfer by the ground transfer record, else UNVERIFIED.
- Capture-in-progress tests rely on the capture taking longer than one command round trip (SSDD: a capture may take seconds); each requires the second command dispatched at least 1 s (one `run` tick, SDD 3.4) before `ProductWritten`, else UNVERIFIED. L0 bench confirmation measures the capture duration.
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

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.TooManyCommands count == 0; event comQueue.QueueOverflow count == 0; Heartbeat samples >= 2.
Standard absence block (ABS): event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Packets (named channel sets for `<packet> samples >= n`): Heartbeat = sysTester.UptimeS, cmdDisp.CommandsDispatched.

ID:        L0-1
Title:     Image identity and marker round-trip, prototype image
Purpose:   Proves the running image is the manifest's prototype image and the marker round-trips.
Covers:    —
Setup:     Prototype image running on the Raspberry Pi 5; link up over TCP.
Procedure: MARK(1000); VERSION(ALL); bracket (2 Heartbeat samples); MARK(0xA5A5); MARK(1001).
Window:    Marker(id=1000) … Marker(id=1001)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  require (else UNVERIFIED): STD. check: Svc.Version events equal the describe strings of the manifest's prototype image; event sysTester.Marker(id=42405) count == 1; event cmdDisp.OpCodeError count == 0.
Planted faults:none

ID:        L0-2
Title:     Image identity and marker round-trip, flight image
Purpose:   Proves the running image is the manifest's flight image and the marker round-trips.
Covers:    —
Setup:     Flight image running; ground Pi with RFM69 and groundRadio up.
Procedure: MARK(1002); VERSION(ALL); bracket (2 Heartbeat samples); MARK(0xA5A5); MARK(1003).
Window:    Marker(id=1002) … Marker(id=1003)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  require (else UNVERIFIED): STD. check: Svc.Version events equal the describe strings of the manifest's flight image; event sysTester.Marker(id=42405) count == 1; event cmdDisp.OpCodeError count == 0.
Planted faults:none

ID:        L2-1
Title:     Capture names its product
Purpose:   Proves a successful capture emits ProductWritten naming the one new product file.
Covers:    REQ-ProductManager-014
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1010); LIST_DIR(products); CAPTURE(); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1011).
Window:    Marker(id=1010) … Marker(id=1011)
Pass rule: named checks declared in the integration test (test_L2_1).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductWritten count == 1, naming P; every productManager.ProductWritten event has severity ACTIVITY_HI; sysTester.DirListing event 2 names P and no other file; event cmdDisp.OpCodeError count == 0; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:capture_twice

ID:        L2-2
Title:     Second capture leaves the first product unchanged
Purpose:   Proves a second capture names a new product and leaves the first unchanged.
Covers:    REQ-ProductManager-014, REQ-ProductManager-015
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1012); LIST_DIR(products); CAPTURE(); DUMP_SHA256(P1, 1); CAPTURE(); DUMP_SHA256(P1, 2); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1013).
Window:    Marker(id=1012) … Marker(id=1013)
Pass rule: named checks declared in the integration test (test_L2_2).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductWritten count == 2, naming P1 and P2, different; every productManager.ProductWritten event has severity ACTIVITY_HI; the two sysTester.Sha256 events of P1 carry the same hash; sysTester.DirListing event 2 names P1 and P2 only; event cmdDisp.OpCodeError count == 0; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:corrupt_first_product

ID:        L2-3
Title:     A third capture leaves both stored products unchanged
Purpose:   Proves a capture leaves every stored product unchanged, and DELETE then removes one.
Covers:    REQ-ProductManager-015, REQ-ProductManager-034
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1014); LIST_DIR(products); CAPTURE(); CAPTURE(); DUMP_SHA256(P1, 1); DUMP_SHA256(P2, 1); CAPTURE(); DUMP_SHA256(P1, 2); DUMP_SHA256(P2, 2); DELETE(P2); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1015).
Window:    Marker(id=1014) … Marker(id=1015)
Pass rule: named checks declared in the integration test (test_L2_3).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductWritten count == 3, naming P1, P2 and P3, all different; the two sysTester.Sha256 events of P1 carry the same hash; the two sysTester.Sha256 events of P2 carry the same hash; event productManager.ProductDeleted count == 1, naming P2; sysTester.DirListing event 2 names P1 and P3 only; event cmdDisp.OpCodeError count == 0; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L2-4
Title:     Delete removes the named product
Purpose:   Proves DELETE removes the named product and no other, before its command response.
Covers:    REQ-ProductManager-034
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1016); LIST_DIR(products); CAPTURE(); CAPTURE(); DUMP_SHA256(P2, 1); DELETE(P1); LIST_DIR(products); DUMP_SHA256(P2, 2); LIST_PRODUCTS(); action: teardown, remove the product files of this test over ssh; MARK(1017).
Window:    Marker(id=1016) … Marker(id=1017)
Pass rule: named checks declared in the integration test (test_L2_4).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductDeleted count == 1, naming P1; sysTester.DirListing event 2 names P2 only; the two sysTester.Sha256 events of P2 carry the same hash; event productManager.ProductStored count == 1, naming P2; event productManager.ProductsListed(count=1) count == 1; event cmdDisp.OpCodeError count == 0; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:delete_other

ID:        L5-1
Title:     Capture during a capture
Purpose:   Proves a CAPTURE during a capture is rejected and the first capture stores its product.
Covers:    REQ-ProductManager-025
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1020); LIST_DIR(products); CAPTURE() without waiting for completion; CAPTURE(); wait event productManager.ProductWritten (at most 30 s, REQ-PiSensor-010; on time-out continue to END); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1021).
Window:    Marker(id=1020) … Marker(id=1021)
Pass rule: named checks declared in the integration test (test_L5_1).
Evidence:  require (else UNVERIFIED): STD; the command sent after the first CAPTURE is dispatched at least 1 s (one run tick) before event productManager.ProductWritten. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=CAPTURE_IN_PROGRESS) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected CAPTURE; every other command completes; event productManager.ProductWritten count == 1, naming P; sysTester.DirListing event 2 names P and no other file; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:second_capture_dropped

ID:        L5-2
Title:     Capture after a rejected capture
Purpose:   Proves a rejected CAPTURE does not disturb the capture in progress or the next one.
Covers:    REQ-ProductManager-025
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1022); LIST_DIR(products); CAPTURE() without waiting for completion; CAPTURE(); wait event productManager.ProductWritten (at most 30 s, REQ-PiSensor-010; on time-out continue to END); CAPTURE(); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1023).
Window:    Marker(id=1022) … Marker(id=1023)
Pass rule: named checks declared in the integration test (test_L5_2).
Evidence:  require (else UNVERIFIED): STD; the command sent after the first CAPTURE is dispatched at least 1 s (one run tick) before event productManager.ProductWritten. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=CAPTURE_IN_PROGRESS) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected CAPTURE; every other command completes; event productManager.ProductWritten count == 2, naming P1 and P2, different; sysTester.DirListing event 2 names P1 and P2 only; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L5-3
Title:     Downlink during a downlink
Purpose:   Proves a DOWNLINK during a downlink is rejected and the first transfer delivers its product.
Covers:    REQ-ProductManager-031
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering.
Procedure: MARK(1030); LIST_DIR(products); CAPTURE(); CAPTURE(); DUMP_SHA256(P1, 1); DOWNLINK(P1) without waiting for completion; wait event productManager.DownlinkStarted (at most 10 s; on time-out continue to END); DOWNLINK(P2); wait CFDP transaction finished at the ground (at most 600 s; on time-out continue to END); wait event productManager.DownlinkComplete (at most 30 s; on time-out continue to END); action: teardown, remove the product files of this test over ssh; MARK(1031).
Window:    Marker(id=1030) … Marker(id=1031)
Pass rule: named checks declared in the integration test (test_L5_3).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it); the command sent after the first DOWNLINK is dispatched after event productManager.DownlinkStarted and at least 2 s before the ground end time of that CFDP transaction. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=DOWNLINK_IN_PROGRESS) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DOWNLINK; every other command completes; event productManager.DownlinkStarted count == 1, naming P1; event productManager.DownlinkComplete count == 1, naming P1; ground CFDP transactions in the window: exactly one, of file P1, finished complete; sha256 of record/raw/files/<P1> == hash in the first sysTester.Sha256 event of P1; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L5-4
Title:     Repeated downlink of the product in transfer
Purpose:   Proves a DOWNLINK naming the product in transfer is rejected without a second transfer.
Covers:    REQ-ProductManager-031
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering.
Procedure: MARK(1032); LIST_DIR(products); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted (at most 10 s; on time-out continue to END); DOWNLINK(P); wait CFDP transaction finished at the ground (at most 600 s; on time-out continue to END); wait event productManager.DownlinkComplete (at most 30 s; on time-out continue to END); action: teardown, remove the product files of this test over ssh; MARK(1033).
Window:    Marker(id=1032) … Marker(id=1033)
Pass rule: named checks declared in the integration test (test_L5_4).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it); the command sent after the first DOWNLINK is dispatched after event productManager.DownlinkStarted and at least 2 s before the ground end time of that CFDP transaction. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=DOWNLINK_IN_PROGRESS) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DOWNLINK; every other command completes; event productManager.DownlinkStarted count == 1, naming P; event productManager.DownlinkComplete count == 1, naming P; ground CFDP transactions in the window: exactly one, of file P, finished complete; sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event of P; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L5-5
Title:     Delete during the product's downlink
Purpose:   Proves a DELETE of the product in transfer is rejected; the product is delivered, kept.
Covers:    REQ-ProductManager-035
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering.
Procedure: MARK(1034); LIST_DIR(products); CAPTURE(); DUMP_SHA256(P, 1); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted (at most 10 s; on time-out continue to END); DELETE(P); wait CFDP transaction finished at the ground (at most 600 s; on time-out continue to END); wait event productManager.DownlinkComplete (at most 30 s; on time-out continue to END); DUMP_SHA256(P, 2); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1035).
Window:    Marker(id=1034) … Marker(id=1035)
Pass rule: named checks declared in the integration test (test_L5_5).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it); the command sent after the first DOWNLINK is dispatched after event productManager.DownlinkStarted and at least 2 s before the ground end time of that CFDP transaction. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=PRODUCT_IN_DOWNLINK) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DELETE; every other command completes; event productManager.ProductDeleted count == 0; event productManager.DownlinkStarted count == 1, naming P; event productManager.DownlinkComplete count == 1, naming P; sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event of P; the two sysTester.Sha256 events of P carry the same hash; sysTester.DirListing event 2 names P and no other file; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:corrupt_in_transfer

ID:        L5-6
Title:     Delete after the product's downlink
Purpose:   Proves a DELETE rejected during the downlink succeeds once the transfer has ended.
Covers:    REQ-ProductManager-035, REQ-ProductManager-034
Setup:     Flight image running, ground Pi with RFM69 and groundRadio up, camera answering.
Procedure: MARK(1036); LIST_DIR(products); CAPTURE(); DOWNLINK(P) without waiting for completion; wait event productManager.DownlinkStarted (at most 10 s; on time-out continue to END); DELETE(P); wait CFDP transaction finished at the ground (at most 600 s; on time-out continue to END); wait event productManager.DownlinkComplete (at most 30 s; on time-out continue to END); DELETE(P); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1037).
Window:    Marker(id=1036) … Marker(id=1037)
Pass rule: named checks declared in the integration test (test_L5_6).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it); the command sent after the first DOWNLINK is dispatched after event productManager.DownlinkStarted and at least 2 s before the ground end time of that CFDP transaction. check: sysTester.DirListing event 1 names no file; event productManager.CommandRejected(reason=PRODUCT_IN_DOWNLINK) count == 1; every productManager.CommandRejected event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DELETE; every other command completes; event productManager.DownlinkStarted count == 1, naming P; event productManager.DownlinkComplete count == 1, naming P; event productManager.CommandRejected precedes event productManager.DownlinkComplete; event productManager.DownlinkComplete precedes event productManager.ProductDeleted; event productManager.ProductDeleted count == 1, naming P; sysTester.DirListing event 2 names no file; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L6-1
Title:     Downlink of a missing product
Purpose:   Proves a DOWNLINK naming no stored product is rejected and nothing is sent.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1040); LIST_DIR(products); CAPTURE(); DUMP_SHA256(P, 1); LIST_DIR(products); DOWNLINK(Dp_missing.fxd); wait 10 s (twice the time in which DownlinkStarted or a ground transaction follows an accepted DOWNLINK over TCP); DUMP_SHA256(P, 2); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1041).
Window:    Marker(id=1040) … Marker(id=1041)
Pass rule: named checks declared in the integration test (test_L6_1).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it). check: sysTester.DirListing event 1 names no file; event productManager.ProductNotFound(name=Dp_missing.fxd) count == 1; every productManager.ProductNotFound event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DOWNLINK; every other command completes; event productManager.DownlinkStarted count == 0; ground CFDP transactions in the window: none; the two sysTester.Sha256 events of P carry the same hash; sysTester.DirListing events 2 and 3 carry the same file names and count; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:downlink_existing

ID:        L6-2
Title:     Delete of a missing product
Purpose:   Proves a DELETE naming no stored product is rejected and removes nothing.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1042); LIST_DIR(products); CAPTURE(); LIST_DIR(products); DELETE(Dp_missing.fxd); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1043).
Window:    Marker(id=1042) … Marker(id=1043)
Pass rule: named checks declared in the integration test (test_L6_2).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductNotFound(name=Dp_missing.fxd) count == 1; every productManager.ProductNotFound event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DELETE; every other command completes; event productManager.ProductDeleted count == 0; sysTester.DirListing events 2 and 3 carry the same file names and count; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L6-3
Title:     Delete with a path as name
Purpose:   Proves a DELETE naming a path to a stored product is rejected, removing nothing.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1044); LIST_DIR(products); CAPTURE(); LIST_DIR(products); DELETE(./P); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1045).
Window:    Marker(id=1044) … Marker(id=1045)
Pass rule: named checks declared in the integration test (test_L6_3).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductNotFound count == 1, naming ./P; every productManager.ProductNotFound event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DELETE; every other command completes; event productManager.ProductDeleted count == 0; sysTester.DirListing events 2 and 3 carry the same file names and count; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L6-4
Title:     Downlink with a path as name
Purpose:   Proves a DOWNLINK naming a path to a stored product is rejected, sending nothing.
Covers:    REQ-ProductManager-033
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1046); LIST_DIR(products); CAPTURE(); LIST_DIR(products); DOWNLINK(./P); wait 10 s (as L6-1); LIST_DIR(products); action: teardown, remove the product files of this test over ssh; MARK(1047).
Window:    Marker(id=1046) … Marker(id=1047)
Pass rule: named checks declared in the integration test (test_L6_4).
Evidence:  require (else UNVERIFIED): STD; the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it). check: sysTester.DirListing event 1 names no file; event productManager.ProductNotFound count == 1, naming ./P; every productManager.ProductNotFound event has severity WARNING_LO; exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DOWNLINK; every other command completes; event productManager.DownlinkStarted count == 0; ground CFDP transactions in the window: none; sysTester.DirListing events 2 and 3 carry the same file names and count; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0.
Planted faults:none

ID:        L7-1
Title:     Final state
Purpose:   Leaves one known product on board for the independent final-state check.
Covers:    REQ-ProductManager-014
Setup:     Prototype image running, link up, camera answering.
Procedure: MARK(1050); LIST_DIR(products); CAPTURE(); DUMP_SHA256(P, 1); LIST_DIR(products); MARK(1051).
Window:    Marker(id=1050) … Marker(id=1051)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  require (else UNVERIFIED): STD. check: sysTester.DirListing event 1 names no file; event productManager.ProductWritten count == 1, naming P; every productManager.ProductWritten event has severity ACTIVITY_HI; sysTester.DirListing event 2 names P and no other file; event cmdDisp.OpCodeError count == 0; event productManager.CaptureFailed count == 0; event productManager.StorageFailed count == 0; event productManager.DownlinkStalled count == 0; event productManager.FileSystemError count == 0; event productManager.ProductDiscarded count == 0; event sysTester.Started count == 0. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt; the auditor compares it with the hash of the Sha256 event.
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
| REQ-ProductManager-033 | L6-1, L6-2, L6-3, L6-4; unit test |  |
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
| REQ-ProductManager-049 | waived: UT only | observable at the component boundary; the unit-test list of docs/sdd.md covers it |

## 5 Metrics
- (none)

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): capture_twice (stimulus; L2-1); corrupt_first_product (uut-state; L2-2); corrupt_in_transfer (uut-state; L5-5); delete_other (stimulus; L2-4); downlink_existing (stimulus; L6-1); second_capture_dropped (stimulus; L5-1).

## 7 Not covered
- Every requirement marked `UT only`: verified by the unit-test list, and at system level by the project plan where it traces a system requirement.
- REQ-ProductManager-046 (name in use): the clock cannot be made to repeat a capture time on the bench without stepping the system clock of a shared machine; unit test only.
- A listing during a listing, a delete during a listing and queue overflow: timing not reachable through the ground link at 5 events per second; unit tests.
- Today's bench cannot run these tests: the camera and the ground Pi are absent.

## 8 Decision log
1. 2026-11-17 designer — the component tests run in the project's base deployment with `sysTester`; no component-only deployment.
2. 2026-11-17 designer — downlink-in-progress tests run on the flight image, where a transfer lasts long enough to command inside it.
3. 2026-11-17 designer — planted faults rewrite or insert commands only; two are `uut-state` (`corrupt_first_product`, `corrupt_in_transfer`).
4. 2026-11-17 designer, review round 1 — checks are named predicates and helpers listed per test; `OpCodeError` left the completeness block; flight-image identity test L0-2 and fault-free L6-4 added; system coverage threshold set to 55 with its reason.
