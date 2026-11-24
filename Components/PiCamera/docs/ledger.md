# Campaign ledger — picam (child of project run fvp-2026-11-17-1, node comp_design_child)

- 2026-11-17 setup [V]: skills source lestarch-autobot/fprime@system-campaign-skills sha aa3ab031a6c67d40652e8047a2e1f9a8a8c2b26c (head of nasa/fprime#6388, state open), checkout ~/picam/skills. Read: development-campaign SKILL, contract §0–§9, phase-review-loop, fprime-development.agent, component-development, component-requirements, component-design-fpp, component-unit-test, checklist-design. To read at their phase: system-test-design, requirements-review.
- Tooling pin (contract §8): fprime-testing-harness v0.1.2 (855dd4f).
- Approver: project-campaign (contract §9.2). Stretch: DESIGN lane only, stop at Approve SDD. Review bound 3 (source: default). LOCAL ONLY.
- UUT: lestarch-autobot/fprime-pi-sensor-reference, branch design/picam cut from design/ssdd@ba498d76c87b83b2394523de6496df6cfd0e10e9. No pre-commit hooks in the repository [V].
- Allocated system requirements: REQ-PiSensor-004, 005, 006, 007, 008, 010, 028, 029, 040.
- Bench: not touched in this lane (parent instruction). Camera device identity unknown until the camera is attached after SSDD approval; parent's read-only probe [V, project ledger]: `rpicam-still --list-cameras` -> "No cameras available!", rpicam-apps installed on soakee.
- Goals (verbatim): "a functional component with respect to the request, proven in system tests on the real hardware". Human: "My expectation is that the PI camera be rewritten using standard PI libraries that are easy to install rather than using the OpenCV camera setup from fprime-examples as that is complex and overkill."
- 2026-11-17 requirements draft [V]: 18 rows REQ-PiCamera-001..018 + Tables 1–3. Trace: PiSensor-004 → 001, 002; 005 → 001, 004, 005; 006 → 003; 007/008 → 003 (acquisition time is the reference the product manager compares sample times with); 010 → 008; 028 → 005, 009, 011, 014; 029 → 009, 010; 040 → 016, 017.
- Writer proposals (status `proposed`, for the approver at gate 1):
  - P1 `CaptureFailed` is `WARNING_LO` with a reason: the system plan (L5-11) counts exactly one `WARNING_HI` `productManager.CaptureFailed` for REQ-PiSensor-028, so the camera's own report must not be a second `WARNING_HI` (REQ-PiCamera-011).
  - P2 `CaptureStarted` severity `ACTIVITY_LO` (REQ-PiCamera-007).
  - P3 `CAPTURE_TIMEOUT_TICKS` = 10 ticks of a 1 Hz `run` port, inside the 30 s of REQ-PiSensor-010 (REQ-PiCamera-008). Needs a `run` port the sketch does not show.
  - P4 A request during a capture gets `BUSY` and does not disturb it (REQ-PiCamera-012, 013); the system owner of REQ-PiSensor-030 is `productManager`, this is the component's own guard.
  - P5 Telemetry Table 2 and picture size 640x480 (REQ-PiCamera-015, Table 3).
  - P6 Failure reasons of Table 1 (REQ-PiCamera-005).
- Device identity: camera model unknown until attached (after SSDD approval); a mismatch with the libcamera-supported sensors reopens requirements.
- Requirements review loop started, bound 3 (source: default). Round 1 reviewer: child session 1a2514060578497289718f98b131436e (requirements-review.agent.md), artifact commit a84dc87. Records land in `Components/PiCamera/docs/review/`.
- Design draft in progress (not yet under review) [V]: `PiCamera.fpp` passes `fpp-check` and builds (`Components_PiCamera`, model only) against nasa/fprime v4.4.2 with fprime-fpp 3.4.0 in a scratch project outside the repository (`~/picam/build-model.sh`).
- Design decisions pending in the requirements (to apply at round-1 close):
  - No `run` port: the SSDD threading table gives piCamera its own thread and no rate group; the capture limit is a bounded wait `CAPTURE_TIMEOUT_MS` = 10000 in the component thread (replaces P3 ticks).
  - `BUSY` = request queue full (overflow `hook` replies), requests served one at a time in arrival order (replaces "during a capture").
  - Port change to report to the parent: `imageOut` type `Fw.BufferSend` -> `PiSensor.CaptureReply(context, status, acquired: Fw.Time, picture: Fw.Buffer)`; reason: `Fw.BufferSend` carries neither the acquisition time (REQ-PiSensor-006; SSDD element line "one JPEG and its acquisition time") nor a failure status (REQ-PiSensor-028). Port names unchanged. `CaptureRequest` and `CaptureReply` are defined with the component.
  - Picture 640x480 (D5 minimum; smallest file for the RFM69 link), buffer 262144 bytes; libraries `libcamera` + `libjpeg-turbo` (both Raspberry Pi OS packages).
- 2026-11-17 requirements review round 1 [V]: must fix 15, could fix 7, disagreements 0 (local record `~/picam/review-local/review-requirements-round-1.md`, not in the repository). Closed in the artifact: all 22 except `req-unclear:Introduction/device-identity` (cannot close before the camera is attached; residual for gate 1).
  - Rewrites taken as the reviewer wrote them: 001, 003, 005, 007, 008, 010, 011, 012, 013, 014, 015; 002 points at `PICTURE_WIDTH` x `PICTURE_HEIGHT`; Table 1 `CAMERA_ERROR`, `TIMEOUT`.
  - New rows: 019 (restart during a capture; source: plan L3-3/L3-4, REQ-PiSensor-029), 020 and 021 (returned buffer not delivered or returned twice; fault scenario of the picture-return interface).
  - Trace additions: 006 ← fault scenario "reply to an earlier or refused request" (the requester pairs each reply, `BUSY` included, with its request); 015 ← request "The sensors should stream telemetry" (the camera is sensor 3 of the request; SSDD Table 1 names no camera metric, so the channels are proposal P5); 018 ← REQ-PiSensor-029 and the buffer fault scenario (a picture buffer never released ends captures with `NO_BUFFER`).
  - 017 [V]: `libcamera-dev` 0.8.0+rpt20261104-1 read from the public Raspberry Pi OS trixie archive index (archive.raspberrypi.com), not from the bench; the version installed on `soakee` is confirmed at DEVELOPMENT start, a difference reopens 017.
- Decisions revised at round-1 close (supersede the "pending" list above):
  - Timeout stays a tick count (requirements skill directive): `CAPTURE_TIMEOUT_TICKS` = 10 on a `run` port wired to `rateGroup1Hz`. Port addition to report to the parent (sketch has no `run`).
  - `BUSY` = an earlier request has no reply yet (state, plus queue overflow).
  - One delivered picture outstanding at a time: a request before the last picture is returned gets `NO_BUFFER` (P7, proposed) — makes 020 checkable with one remembered buffer.
  - Picture size 640x480 (P5 revised).
- 2026-11-17 requirements review round 2 [V]: must fix 1, could fix 0, disagreements 0, no new findings. Loop stopped after round 2 of 3: the one open finding `req-unclear:Introduction/device-identity` cannot be closed by the writer (camera not attached, no model named) — residual carried to gate 1.
- Design [V]: `PiCamera.fpp` builds (model only, v4.4.2, fpp 3.4.0). Sketch changes for the parent: `imageOut` type `PiSensor.CaptureReply`; new async `run: Svc.Sched` port wired to `rateGroup1Hz`; `imageReturnIn` and `captureIn` carry queue-overflow hooks; new event `ReturnRejected`; constants `FRAME_DEADLINE_TICKS` = 8 (a frame arriving later is not encoded, so the reply meets 008), `SETTLE_FRAMES` = 10, `PICTURE_BUFFER_SIZE` = 262144 (design values, tuned on the bench in DEVELOPMENT).
- 2026-11-17 design review round 1 started on 62ce7b4: design-review 7db602b2c00042cfb3e7015e576533de, architecture-review 93251c0b6c254208b2c9c157073e0ea8, design-principles-review 9d8515085a3645b2b710ab9fddb828f4.
- 2026-11-17 test design [V]: `test/int/plan.json` (9 tests, `fth verify-plan` ok with fprime-testing-harness v0.1.2), `plan.md`, `faults-menu.json` (4 planted faults, max 2), SDD §8 table rendered by `fth render-sdd-tests`, unit-test list of 20 tests. L0 desk-checked; bench confirmation pending. Needs from the project harness: `sysTester.BENCH_LINE(CAMERA, state)` and the piCamera channels in the heartbeat packet.
- 2026-11-17 design review round 1 [V]: architecture 3 must / 2 could / 2 suggestions; design-review 6 must (one routed `design-needs-human-adjudication:PiCamera`) / 7 could; design-principles 5 must / 9 could. No disagreements raised by reviewers.
- Design revision 2 (answers round 1):
  - `captureIn`, `imageReturnIn`, `run` are guarded ports; overflow hooks removed (no queue on those paths). The timeout is counted on the rate-group thread from receipt and replies while the component thread is inside a camera call.
  - Buffer allocated only at encoding, under the guard; `FRAME_DEADLINE_TICKS` removed.
  - `CaptureFailed` gains `step` and `code`; Table 1 gains `PICTURE_OUTSTANDING` (splits `NO_BUFFER`); new REQ-PiCamera-022, -023, -024 and channels `CameraPresent`, `PictureOutstanding`, events `CameraFound`, `CameraNotFound` — writer proposals P8 (camera presence at start), P9 (failure step and code), P10 (channels at start), raised by the design-principles review (DR-4.11.6.1, DR-4.11.6.2, DR-4.4.6.4, DR-4.11.2.1).
  - `CaptureStatus`, `CaptureRequest`, `CaptureReply` moved to `Components/CapturePorts`.
  - `pingIn`/`pingOut` added; camera closed after every capture; libjpeg-turbo named; buffer provider, start state, wrap, thread table stated.
  - Model builds [V] (v4.4.2, fpp 3.4.0). Plan regenerated, `fth verify-plan` ok.
- Disagreement D-1 `jpl:DR-4.9.3.1:constants` (timeout and settle count as in-flight parameters): writer keeps compile-time constants — trial system whose update path is a redeploy over ssh, the timeout is bound by the system's 30 s command limit, and parameters add a command surface the request does not ask for. Routed to the approver.
- 2026-11-17 design review round 2 [V]: architecture 1 must (new: camera teardown after timeout) / 1 could / 1 suggestion; design-review 2 must (new: teardown, `frameDone` stops before its check) / 7 could, 1 routed; design-principles 1 must (D-1, open disagreement) / 2 could.
- Design revision 3 (answers round 2): internal port `abort` sent by `run` with the `TIMEOUT` reply closes the camera; `acquire` first closes a camera left open; `frameDone` checks its capture number before touching the camera; guard hold bound 100 ms stated, measured in DEVELOPMENT; pattern named; explicit `id` clauses removed; `PICAMERA_NO_CAMERA` CMake option replaces the silent fallback; ping limit note; reason and step pair wording. Stack 1 MiB is a design value without measurement: measured JPEG size, encode time and stack use are recorded here at DEVELOPMENT. Model builds [V].
- Requirements changed by the design phase (rows 015, 022, 023, 024, Table 1 `PICTURE_OUTSTANDING`, Table 2 `CameraPresent`, `PictureOutstanding`): sent to the requirements reviewer as its round 3 on those rows.
- 2026-11-17 design review round 3 [V], loop closed at the bound: architecture 0 must / 0 could; design-review 0 must / 1 could (diagram form — fixed after the round, unverified) plus the routed `design-needs-human-adjudication:PiCamera`; design-principles 1 must = D-1 (open disagreement, approver).
- 2026-11-17 requirements review round 3 (rows changed by the design) [V]: 7 must / 4 could, 0 disagreements. All eleven applied after the round and not re-verified (bound reached): 022, 023, 024 reworded with instant, severity and source; Table 4 (failure steps) moved into §2; 015 "whenever its value changes"; Table 1 order sentence; `LastPictureSize` 0 before the first; libjpeg-turbo archive named and 016 names JPEG libraries. Device identity stays open.
- Trace: 022 ← SSDD fault "Camera absent or failed" (REQ-PiSensor-028), absent before any capture; P8. 023 ← same fault, which camera step failed; P9. 024 ← request "The sensors should stream telemetry" (as 015); P10.
- 2026-11-17 16:32 parent update (redesign pass 1 of 3) [V]: base deployment `deploy/base`@383a9ce1aa7a79ef6f50cef5eba261863e62b2af supersedes `design/ssdd`@ba498d7 for SSDD and sketch; `PiSensor.cfdpManager`, `PiSensor.fileManager`, `PiSensor.prmDb` replace the `FileHandlingCfdp.*` instances; rate groups `rateGroup10Hz`, `rateGroup1Hz`; ground fprime-yamcs f6f0e19. Checked: no file of this campaign names a `FileHandlingCfdp` instance; the `piCamera` instance line and its connections in the sketch are unchanged; `run` stays on `rateGroup1Hz`. No requirement, port type or test changed. `design/picam` stays cut from `design/ssdd` (not merged with `deploy/base`); the DEVELOPMENT stretch starts from the `repo@sha` the parent sends.
- 2026-11-17 test-design review round 1 (Mode A) [V]: 8 must (TD-1..8) / 6 could (TD-9..14), 0 disagreements. All applied: planted faults rewritten so the planted run stays complete and lists every broken predicate (`capture_twice`, `corrupt_picture` by occurrence, `capture_after_restart_dropped`, `camera_kept_absent` with teardown); `picture_is_jfif` is a full decode by an independent decoder; restart windows split at `sysTester.Started`; L5-2 holder confirmed alive; feasibility entries L0-3, L0-4, L0-5; L5 checks on `CaptureStarted` and `CameraPresent`; `CameraFound` checked on the bench in L3; L0-2 judges the resolved runtime library and covers 016; unit-test list traces corrected. `fth verify-plan` ok (12 tests).
- 2026-11-17 test-design review round 2 [V]: round-1 findings all closed; new 1 must (TD-15) / 5 could (TD-16..20), 0 disagreements. All applied: `capture_twice_after_restart` (insert) replaces the dropped capture; L0-4 terms on the Pi clock; one run per process stated (decision 7); `corrupt_picture` `fails` narrowed; libcamera upstream version compared; REQ-PiCamera-016 redundancy waiver recorded (second verification = inspection of the build inputs).
- 2026-11-17 test-design review round 3 [V]: passing, 0 must / 0 could open, 0 disagreements; 20 findings raised over three rounds, all closed. Reviewer notes for the gate: L0-3 to L0-5 decide on the bench whether L5-1, L3-1/L3-2 and L5-2 can be judged; three planted-fault predictions rest on `productManager` behaviour and are confirmed in the harness dry run.
- 2026-11-17 checklist, design stage [V]: `docs/checklist.md` created with fprime-auto-checklist 0.2.2 (e819e7c); rows 1.1–1.6 YES by review; hand-off "Nothing to review at the design stage". Totals: YES 21, NO 2, N/A 6, UNCHECKED 39, REVIEW 5 (deferred). The two NO rows are 2.5 (no handlers: no implementation in this lane) and 5.3 (no hardware run in this lane). clang-tidy plugin not built: static-analysis rows stay UNCHECKED until DEVELOPMENT.
- DESIGN lane stops here, at the delegated Approve SDD gate.
- 2026-11-17 16:47 Approve SDD gate by project-campaign against 6165d8f [V]: NOT PASSED on check 1 (the SDD requirement rows named no REQ-PiSensor id). Rulings recorded:
  - D-1 `jpl:DR-4.9.3.1:constants`: WAIVER — `CAPTURE_TIMEOUT_TICKS` and `SETTLE_FRAMES` stay compile-time constants. Approver's reason: "the ask names no in-flight tuning and each parameter adds a command surface. The human may overturn it at Approve SSDD." Reviewer's position (round 3): "The rule as written is not met: a detection threshold and a tuning value need a rebuild to change, and the request says tuning is expected. The writer's facts are correct and the SDD states the limit in §7, so a recorded approver waiver is an acceptable outcome for this trial. If the approver wants a middle course, `SETTLE_FRAMES` alone as a parameter covers the value most likely to change once the camera model is known. I do not close the finding myself: it needs an interface change or a ruling."
  - Camera identity: accepted as open until the camera is attached (after Approve SSDD); stated in the SDD Introduction.
  - Sketch changes, library choice, `CaptureFailed` as `WARNING_LO`: accepted; harness needs noted for the system harness lane.
- Gate fix [V]: SDD §2 gains the column `Traces to`. PiSensor-004 → 001, 002; 005 → 001, 004, 005, 006; 006, 007, 008 → 003; 010 → 008; 028 → 005, 009, 011, 014; 029 → 007, 009, 010, 019; 040 → 016, 017. Proposal rows: 012, 013, 015, 018, 020–024. No allocated system requirement is without a row. Changes against the earlier ledger trace: 006 now traces to PiSensor-005 (the requester pairs the reply with its request to build the one product), 007 and 019 to PiSensor-029 (interrupted capture; system tests L3-3, L3-4 trigger on `CaptureStarted`), and 018, 022, 023 are listed as proposals as reported at the gate. No requirement text changed. The requirements review bound (3 rounds) is spent, so this column has no reviewer round behind it.
- 2026-11-17 checklist re-run after the trace column [V]: rows 1.1–1.6 re-decided YES against 9116958; hand-off empty.

## Redesign (scope change of 2026-11-18)

- 2026-11-18 17:37 scope change from project-campaign [V]: the human rejected the system design at Approve SSDD. `productManager` and `sensorMonitor` no longer exist; `piCamera` is the only bespoke component: capture command, picture, readings from the telemetry store (`CdhCore.tlmSend.TlmGet`), one product container through `DataProducts.Subtopology`. Allocated: REQ-PiSensor-004 (component), 005, 006, 007, 014 (set). Fault and warning behaviour is owned by the component. Framework pin nasa/fprime `devel@83221ba`; SSDD on `deploy/base@217eb87`. Everything above this heading describes the superseded design; its SDD is replaced, `Components/CapturePorts` and `Components/PiCamera/test/int` (plan built on `sysTester` and `productManager`) are removed.
- Human rulings binding the SDD (verbatim): "Decsisions DO NOT belong in the SSDD.   don't change inherited components, just note the defect (e.g. missing UTs)." "Do NOT add a test component when we are doing system testing, adapt and use existing components, or pivot to other tests." "Downlink should be done via standard data products, so use the catalog and DP subtopology. Don't build a separate component". Decisions are kept here, not in the SDD body.
- Facts read at the pins [V]: `Fw.TlmGet(id, ref timeTag, ref val) -> Fw.TlmValid`, value size 0 when the channel was never written; `Svc.TlmChan.TlmGet` is guarded. Readings: `Bmp280.Bmp280Data` (pressure, temperature °C, altitude), `MpuImu.ImuData` (acceleration, rotation, temperature), `NmeaGps.GpsData` (latitude, longitude, altitude; no fix flag) at fprime-sensors `e5d83d1`. `DataProducts.Subtopology` exports `productGetIn` (sync), `productRequestIn` (async), `productSendIn`, `productResponseOut`; its default buffer size is 10000 bytes (`DataProductsConfig.BuffMgr.dpBufferStoreSize`). `Svc.DpWriter` owns `FileWritten`, `FileOpenError`, `FileWriteError`; a client gets no reply to a sent container. `FwSizeStoreType` is `FwSizeType`, so a `U8 array` record holds the picture.

Decisions (author's, for the gate):

- R-1 Product buffer by `product get port` (synchronous `Fw.DpGet` to `DataProducts.Subtopology.productGetIn`) instead of the request and response ports the SSDD wiring table names. Reason: the JPEG size is known before the buffer is asked; a synchronous get needs no waiting state, no timeout tick and no rate-group port, and a response arriving after a timeout would carry a buffer the component has no port to give back. Changes the SSDD sketch: `productRequestOut`, `productRecvIn` and the wire from `productResponseOut` go; `piCamera.productGetOut -> DataProducts.Subtopology.productGetIn` is added.
- R-2 A reading that is missing, stale (more than `METRIC_MAX_AGE_MS` = 2000 ms from the capture time, either side) or out of range fails the command and stores no product. Reason: REQ-PiSensor-014 allows no product with a metric outside 2 s. Consequence: with no GPS fix (indoor bench) every capture fails at `LOCATION`.
- R-3 `CAPTURE` is a guarded command: a second command during a capture is answered `BUSY` at once from the dispatcher thread; only the busy flag is shared. An async command would queue it, and a full queue asserts or drops the command without a response.
- R-4 The capture runs on the component thread in one handler; the only wait is the frame wait, bounded by `FRAME_TIMEOUT_MS` inside the camera interface. Another camera call that hangs is caught by the health ping, not by the component.
- R-5 Channel identifiers come through `configure()`, so the component does not name other instances.
- R-6 Compile-time constants, as ruled for D-1 of the superseded design (waiver, human may overturn).
- R-7 No camera detection at start and no `run` port: the camera is opened per capture; the camera identification is recorded from the bench (`rpicam-still --list-cameras`) in DEVELOPMENT.
- R-8 Capture time is read by the component thread when the frame wait returns. Severities: `CaptureFailed` `WARNING_HI` (the component owns the warning now), `CaptureCompleted` `ACTIVITY_HI`.
- R-9 No component-level bench plan: REQ-PiCamera-001, 002 are judged by the project system tests L2-3 to L2-6 (the picture record of the downlinked product); no test component is added.
- Trace: PiSensor-004 → 001, 002, 003; 005 → 004, 005, 006, 012, 013; 006 → 007, 008; 007 → 009; 014 → 010, 011, 013. `Component` rows (fault, warning, reporting): 014–022.
- Model builds against `devel@83221ba` with fprime-fpp 4.0.0a2 [V] (scratch project outside the repository).
- 2026-11-18 redo requirements review round 1 [V]: 6 must / 6 could, 0 disagreements. Applied: Table 4 (constants); 009 is now the response bound `CAPTURE_MAX_MS` = 15000 ms (Integration Test) and 023 the frame wait (Unit Test); frame in error or incomplete is `CAMERA_ERROR`; 019 also Integration Test; 006 tolerance and axes; Table 1 order stated; Table 2 absence before the first capture stated; 024 (restart during a capture); 020 split (025). Not applied: merging 016 and 017 (each names its conditions). Device identity stays open. 019 and 024 need bench captures the project system plan does not hold yet: reported to the parent.
- 2026-11-18 redo design review round 1 [V]: architecture 1 must / 3 could / 1 suggestion; design-review 2 must / 6 could plus the routed `design-needs-human-adjudication:PiCamera`. Applied: ping entry limits (warning 20, fatal 30 cycles) above `CAPTURE_MAX_MS`; `BUSY` counts in `CapturesFailed`, counts and `m_busy` change in one guarded section; `m_busy` cleared before the response; camera library thread listed; `acquire` no longer `drop` (a full queue asserts); `JPEG_QUALITY` and pixel format named; FPP annotations.
- Differences to the SSDD sketch, for the parent: (1) R-1 `product get port` replaces the request and receive ports; (2) `pingIn`/`pingOut` added, with a health ping entry; (3) instance stack 1048576 instead of 65536; (4) `configure()` call with the three channel identifiers; (5) `DataProductsConfig.BuffMgr.dpBufferStoreSize` raised above `PICTURE_MAX_SIZE` plus records and overhead (configuration of an inherited subtopology, no source change).
- Stack 1 MiB, `PICTURE_MAX_SIZE` and `JPEG_QUALITY` 90 are design values without measurement: JPEG size, encode time, capture duration (against `CAPTURE_MAX_MS`) and stack use are measured in DEVELOPMENT and recorded here.
- 2026-11-18 redo design-principles review round 1 [V]: 0 must / 7 could, 0 disagreements (D-1 noted once, not reopened). Applied: ping limits (as above); `m_busy` order and guard wording (as above); `CaptureFailed.code` carries the sample age in ms for `SENSOR_STALE`; channels published once at start by `configure`; frame wait on a monotonic clock; argument annotations.
- 2026-11-18 redo review round 2 [V]: architecture 0 / 0, open list empty; design-review 0 must / 2 could plus the routed adjudication; design-principles 0 must / 2 could; requirements 2 must (device identity, held for the gate; 023 wording) / 3 could. No disagreement. Applied: 023 states what the unit test observes; 016 and 019 `Integration Test, Unit Test`; the `SENSOR_STALE` age is limited to the I32 range, 0 for another time base; `acquire` carries opcode and sequence number, so a command accepted after the busy flag clears cannot change the ended capture's response; the channels are published by the component thread at its start (the topology connects ports after `configure`).
- 2026-11-18 redo review round 3 [V], loops closed at the bound: requirements 1 must (device identity: cannot close before the camera is attached; reviewer asks for conditional approval) / 0 could; architecture closed in round 2 with an empty open list; design-review 0 must / 1 could (#11, low confidence: which hook publishes the channels at thread start; left for DEVELOPMENT) plus the routed `design-needs-human-adjudication:PiCamera`; design-principles 0 / 0. No open disagreement.
- 2026-11-18 checklist, design stage, regenerated for the redesign [V]: rows 1.1–1.6 YES by review; hand-off "Nothing to review at the design stage". After the tool's findings: Table 3 column renamed `Source`, container table with default priority 10 (the catalog sends lower numbers first; one container type, so the value orders nothing here), requirement references added in section 3. Rows left NO: 2.5, 2.6 (no implementation in this lane), 3.12 (container priority not commandable: one container type, no parameter added), 5.3 (no hardware run). clang-tidy plugin not built: static-analysis rows UNCHECKED until DEVELOPMENT.

## Development (2026-11-18, branch `comp/picam` from `deploy/base`@c7953c9)

- Skills source unchanged: `lestarch-autobot/fprime` `system-campaign-skills`@aa3ab03. Test configuration: nasa/fprime@83221ba, fprime-sensors@e5d83d1. Single pass (no iterative-development loop was approved).
- Implementation [V]: `PiCamera.{hpp,cpp}`, camera interface `Camera.hpp`, `LibcameraCamera.cpp` (libcamera 0.7.2, YUV420 640x480, libjpeg62-turbo raw-data compression; compiled as C++17 because libcamera's API needs it), `NoCamera.cpp` (`PICAMERA_NO_CAMERA`), topology wiring, `PiSensor/project/config/DataProductsConfig.fpp` (`dpBufferStoreSize` 264192; a project configuration override, no inherited source changed).
- Differences to the approved SDD, reported to the parent: `Camera::encode` in the interface (unit tests substitute the JPEG step); `configure` takes the camera interface as first argument; three channel members instead of `m_channels`; the sensors' `CHANNELID_READING` enumerators are protected, so the topology passes local identifier 0 as the constant `SENSOR_READING_CHANNEL`. SDD errata applied at 0d92871: camera identity (Camera Module 3, `imx708`), libcamera 0.7.2, the interface list, `configure` and the channel members.
- Unit tests [V]: the 20 tests of SDD §8 pass; `PiCamera.cpp` line coverage 99% (197 of 199) before the review fixes.
- Defect found by the unit tests [V]: camera error codes were lost because the code argument and the camera call were evaluated in one argument list; fixed.
- Bench smoke over the RFM69 [V], image sha256 31a70108…bf1f487 (32b0c2d): `CAPTURE` → `CaptureCompleted` 24480 bytes, `dpWriter.FileWritten` 24639 bytes, picture decodes as JPEG 640x480; response in 0.85 s (bound `CAPTURE_MAX_MS` 15000). With `rpicam-hello` holding the camera: `CaptureFailed(CAMERA_ERROR, OPEN, -16)`, `EXECUTION_ERROR`; after release the next capture succeeds (24158 bytes). Measured JPEG size is about 9% of `PICTURE_MAX_SIZE`.
- Development review, single pass, local, 32b0c2d [V]: 7 must fix / 10 suggestion / 16 could fix / 0 future work / 5 ruled. All ten lenses ran in one reviewer context.

| Finding | Agent tag | Disposition | Reason | Who ruled |
|---|---|---|---|---|
| COR-1 exact-size JPEG fails `TOO_LARGE` | must fix | fixed e3b7217 | destination spills into a scratch area; overflow only when the scratch receives a byte | writer |
| TQ-1 tautological assertion | must fix | fixed e3b7217 | compares component counters with responses | writer |
| TQ-2 response order untested | must fix | fixed e3b7217 | `CAPTURE` sent from inside the `OK` response | writer |
| DES-1 age checked before decode | must fix | fixed e3b7217, test 0d92871 | decode first, as SDD §3.5 step 4 | writer |
| DES-2 `NO_CAMERA` at `OPEN` | must fix | fixed e3b7217 | `open` returns `ERROR` with `-ENODEV` | writer |
| DOC-1 SDD interface list | must fix | fixed 0d92871 | SDD erratum, reported to the parent | writer |
| DOC-2 SDD camera identity | must fix | fixed 0d92871 | SDD erratum, closes the open item | writer |
| COR-2, CPP-B, CPP-C, CPP-D, CPP-E, CPP-F, DES-4, MNT-2 | suggestion | fixed e3b7217, 0d92871 | applied as proposed | writer |
| DES-5 no check of the store size against `PICTURE_MAX_SIZE` | suggestion | not applied | the record sizes are protected members of the generated base; the configuration comment names the dependency | writer |
| TQ-3 adapter encoder has no unit test | suggestion | not applied | needs the camera libraries on the unit-test host; the adapter is exercised on the bench | writer |
| TQ-5 record count per identifier | could fix | fixed 0d92871 | one Metrics and one Picture record asserted | writer |
| other could fix (15) | could fix | not applied | single pass | writer |
- Unit-test coverage after the review fixes [V]: 21 tests pass (the 20 of SDD §8 plus `NoCameraBuild`, added so the `PICAMERA_NO_CAMERA` interface is run); lines 99.1% (227 of 229) over `PiCamera.cpp`, `NoCamera.cpp`, `Camera.hpp`; the project minimum is 95%. `LibcameraCamera.cpp` is not in the unit-test build (finding TQ-3); it runs on the bench.
- 2026-11-18 checklist, implementation stage [V]: hand-off empty. NO rows: 3.12 (container priority not commandable, as at design), 3.33 (the `CaptureMetrics` members carry units in annotations, not in names; approved model), 5.3 (hardware run record, written at close-out). 3.21 and 3.23 N/A (no interrupts). 4.2 audited YES (`TestUtils` is header-only, no CMake module). 38 rows UNCHECKED: the clang-tidy plugin is not installed on the development host (needs root).

## Bench harness (2026-11-18)

- Harness: `Components/PiCamera/test/int/` (plan C-1 to C-3, stimulus and named checks, three planted faults, bench recipe) and the bench adapter `test/int/bench/yamcs_bench.py`. No test component; marker `cmdDisp.CMD_NO_OP_STRING`.
- Tool gaps of fth v0.1.2 [V]: no `verify-stimulus` subcommand; `verify-plan --sdd` rejects the heading `## 2. Requirements`; `require()` cannot expand a helper predicate of `std_complete`; `fth dev-campaign` and so `fth deliver` need a run with in-image `DUMP_COVERAGE` windows, which this Linux deployment as flown does not have.
- `commands_sent == count(event cmdDisp.OpCodeDispatched)` is not usable with this marker [V]: the dispatch of the START marker carries the time tag of the marker event and can sort outside the window. The tests require instead that every command but the markers was dispatched.
- The RFM69 uplink lost 2 of 17 command frames in one dry run [V]. The adapter sends a command again, at most twice, when the unit does not report its dispatch within 6 s, and logs each resend.
- `require(...)` is judged on the live record at the time of the call [V]: the tests call it after the stimulus and a 3 s wait for the recorder.

System-test review, Mode B, single pass (child session bd306eb3, `comp/picam`@53eda05): 10 must fix, 7 could fix, 1 ruled.

| Finding | Disposition |
|---|---|
| M-1 arguments logged as strings | Fixed: decimal arguments are logged as numbers. |
| M-2 `CaptureFailed` pattern | Fixed. |
| M-3 REQ-PiCamera-009 unjudged | Fixed: dispatcher event patterns added; check function `every CAPTURE answered within CAPTURE_MAX_MS` fails when its operands are absent. |
| M-4 `delta(CapturesCompleted)` in C-1 | Fixed: check removed. |
| M-5 pacing of C-2 under its planted fault | Fixed: bracket before the camera is freed; the reason check is a function on the first failure and is out of `fails`. |
| M-6 stale process id files | Fixed: a recorded process is signalled only while `/proc/<pid>/exe` is the program the adapter started. |
| M-7 absolute paths in `bench.json` | Fixed for the adapter, bridge and interpreters (relative to the campaign root). Open: the YAMCS configuration directory is built by hand per `ground/README.md`, not by a pinned step. |
| M-8 lost downlink frame not seen | Partly: the two overflow predicates are preconditions and the YAMCS link events are kept in `record/raw/ground-events.log`. Open: no precondition on a frame gap, because fth hands a check no raw ground data. |
| M-9 REQ-PiCamera-024 | Plan states it is not verified as written on the bench (restart after a completed capture); unit test `RecoveryAfterFailure`. |
| M-10 one `CaptureStarted` per command | Fixed. |
| C-1 to C-7 | Applied: response timed, not the event; no start-up between failure and success; process confirmed after start and hold; clashing names reported in `record/raw/name-clash.log`; `checks_kat.py`; second restart witness. |
| R-1 run-start markers read from `*.Marker` events only | Ruled (marker is binding). Tool gap to watch at unseal. |

Dry runs on the bench [V], image sha256 `b1980c96…809cf` (flight sources of 53eda05):

- Run of 21:34: C-2 PASS, C-3 PASS; C-1 UNVERIFIED from the recorder timing above; the record replays as three PASS.
- Run of 21:40: invalid. The MPU6050 stopped answering (`imuManager.I2cError`, `I2C_WRITE_ERR` on address 104) 55 s after the image start and stayed silent after a restart of the process. Bench fault reported to the project; not cleared here (no power-cycling, no sudo).

## Bench harness, second day (2026-11-19)

- Tooling: fprime-testing-harness branch `linux-host-coverage`@a37aa1b0062a7ae2f2c85e795db345891c000a8a (v0.1.2 plus one commit) replaces v0.1.2 on the workstation. It accepts coverage counts copied off a Linux target (`--gcda-dir`), per the ruling on the coverage evidence.
- Coverage on the target: an image built with `--coverage` is started with `GCOV_PREFIX` by the adapter (`flash --gcov`, `bench-coverage.json`); the counts are written when the image ends on `SIGTERM` and are copied off with `collect-gcda`. No test code is in the image.
- Correction to the note above: `require(...)` is judged when the window closes, not at the call.
- Channel samples reach the ground record about 36 s after events of the same unit time, and the lag grew by about 0.13 s per second over 12 s [V]; `comQueue` depth read 0, the place of the queue is not located. A window shorter than the lag closed with no bracket samples. The tests wait, before the END marker, until the bracket channel has a sample as new as the newest event (240 s at most). Reported to the project as a system finding.
- Clean dry run [V], `comp/picam`@fe0a442, image sha256 `b1980c96…809cf`: C-1, C-2, C-3 PASS (record `d68bc46b…`).
- Planted-fault dry runs of the same morning: invalid. The MPU6050 fault returned (two `I2cError` during the clean run with no bench action, then `lost arbitration` and `SDA stuck at low` in the kernel log about 35 s after the next image start). Reported to the project.

## Design change: capture without the MPU6050 (2026-11-19)

- Ruling of the Captain, 2026-11-19 10:50 PST, verbatim: "You are just going to have to continue without it.  Put placeholder values in the data product and move on". Passed on by the project (project ledger, `deploy/base`@d3c1359) after the MPU6050 of the bench failed a third time. It is the authority for this change to the SDD approved at gate 1.
- Change: a missing, undecodable or stale acceleration reading no longer fails a capture. The `Metrics` record gets `attitudeValid` (false), roll and pitch NaN and `attitudeTime` zero; the component emits `AttitudeUnavailable` (`WARNING_LO`) with the reason and the code a failure would have carried. New REQ-PiCamera-026; REQ-PiCamera-010 and 011 now name the temperature and the location only; REQ-PiCamera-006 holds when the reading is usable.
- Unchanged: no GPS fix, a stale GPS reading and a missing or stale BMP280 reading fail the capture and store nothing.
- Decision: an acceleration that is present and fresh but not finite or of magnitude 0 still fails with `METRIC_INVALID` at `ATTITUDE`. The ruling names a sensor that is absent; a present sensor that reports nonsense is a different fault and is not hidden behind a placeholder.
- Decision: `attitudeTime` is zero when the flag is false, also for a stale reading, so that no field of an invalid attitude looks usable. The age of a stale reading is in the event.
- Decision: the warning is `WARNING_LO`, because the command succeeds; `CaptureFailed` stays `WARNING_HI`.
- No MPU6050 data is substituted on the bench, in the image or in the harness.
- System level: REQ-PiSensor-014 as written fails a capture for any stale metric; the exception for the attitude is the project's to record.
- Unit tests: 22 pass (new `AttitudeUnavailable`; `StaleReading`, `MissingReading`, `RecoveryAfterFailure` and `RandomSequences` adapted). Coverage after the review fixes: lines 99.2% (242 of 244), branches 84.3% (323 of 383), functions 93.8% (30 of 32).
- Checklist, implementation stage, re-stamped: YES 30, N/A 3, UNCHECKED 37 (no clang-tidy plugin), NO 3 (3.12, 3.33, 5.3).
- Bench plan: the bracket channel is `bmpManager.Reading`; REQ-PiCamera-026 is covered by C-1 to C-3 only where the record is conclusive (see the review item below), because recorded channel samples have gaps the unit did not have (21 of 34 expected MPU6050 samples in one window of the run of 2026-11-18 21:34, during which every capture read a fresh acceleration).
- Review: one focused pass of this change (development review of commit 18c7f70, child session f9824ceb), as the project instructed; no further rounds. Result: 0 must fix, 3 suggestions, 4 could fix; all seven applied.
  - S-1: `AttitudeUnavailable` is emitted once the three readings are complete, so a capture that fails at `LOCATION` does not claim a stored NaN.
  - S-2, S-3: the bench check `attitude warning agrees with the MPU6050 telemetry` expects no warning only with a fresh sample before both `CaptureStarted` and `CaptureCompleted`, and expects the warning when the window holds no MPU6050 sample at all; anything between is not judged.
  - C-1, C-2: the unit test asserts seconds and microseconds 0, and no warning when the capture fails.
  - C-3, C-4: `readAttitude` itself decides what is unavailable; its declaration sits with `readMetrics`.
  - The reviewer challenges the `METRIC_INVALID` decision above: an MPU6050 that still answers with zeros would fail every capture. Left as decided and reported to the project for the Captain.

## Release (2026-11-19)

Written after the freeze; the package pins `comp/picam`@3e2290f729784914e1d9d598b85d7be1de217d20, the commit before this section.

- Images, built on the workstation by `test/int/bench/build_image.sh` [V]: pure sha256 `4610f6d97f1680557823f0d7c875903a22479af2b8165ad970b01c5f1c7e7aa6`; built for coverage sha256 `a0ad4b71e275e8580ba09ccf5b21036ad63dd37321de7060105cd0cac39287ca`; dictionary sha256 `366969e5945592c34107d847cb20920b3387e83c66d7c39eb4ae00270aa8ef69`. `fth deliver` rebuilt the pure image and the dictionary from the pinned trees to the same hashes.
- Bench runs, MPU6050 silent throughout (every capture stored its product with `AttitudeUnavailable(SENSOR_NO_DATA, 0)`) [V]:

| Run | Image | Planted fault | C-1 | C-2 | C-3 | Record |
|---|---|---|---|---|---|---|
| dry-1 | pure | none | PASS | PASS | PASS | `2131628e…` |
| dry-2 | pure | `c1_second_capture` | FAIL, its 3 declared checks | PASS | PASS | `2c8c29f7…` |
| dry-3 | pure | `c2_capture_before_hold` | PASS | FAIL, its 2 declared checks | PASS | `35cea039…` |
| dry-4 | pure | `c3_capture_after_restart` | PASS | PASS | FAIL, its 3 declared checks | `8857deaf…` |
| cov-1 | coverage | none | PASS | PASS | PASS | `f4a64f38…` |

- `fth audit --unsealed --tests` on dry-1 to dry-4: runner and replay agree on every test. One step fails in each audit: `run-start markers … no manifest run-start marker for this manifest/run id`. fth reads run-start markers only from events named `*.Marker`; the marker of this project is `cmdDisp.NoOpStringReceived` (finding R-1 of the harness review).
- Coverage: unit tests, lines 99.2% (242 of 244); on the target, over `Components/PiCamera/` of the coverage image, 284 count files copied off the Pi after a clean stop: lines 77.0% (415 of 539), functions 82.2% (37 of 45), branches 58.9% (308 of 523). Plan minimum: 95 and 75.
- `fth dev-campaign --gcda-dir`: clean, no finding.
- `fth deliver`: OK, 0 findings. `rfr-input.zip` sha256 `51ea1caa69fd7d550d02f7d221cd5803acdafd5d5fe9393a3907c11cd41430a2`, manifest sha256 `9a04d111facec33c1761b2de339ebf821a1cf870ed35110dfb481eb5f7d3b19e`, 33 pinned files.
- Seed-free rehearsal `fth rfr rfr-input.zip --dry-run`: REFUSED on one preflight check of 30: `running fth is the pinned harness checkout: fth imports from …/campaign/harness, manifest pins harness at uut — run the pinned fth`. The other form, `--harness` = the fprime-testing-harness checkout, is refused by `fth deliver`: `VERSION: inputs/PiSensor.bin: describe string of ['harness'] not found in the image`. The tool expects the harness repository to be both the tree fth runs from and a tree whose version is built into the image; here the bench tests live in the project repository and the image holds no test code. Not worked around; reported to the project. No seed was requested and no run for record was made.
- Hardware run for checklist row 5.3: not recorded as `docs/hardware-run.md`; the runs above are the evidence (Raspberry Pi 5 `soakee`, deployment `PiSensor`, commit 3e2290f, 2026-11-19).

## Release, second delivery (2026-11-19)

- Tooling: fprime-testing-harness `linux-host-coverage`@8dd2a5e007132f88719c53a367f1190216cf8b99 (the project's change for the two refusals above), checked out at `harness/` of the campaign root and installed from there.
- `fth deliver --harness uut --tool harness`: OK, 0 findings. `rfr-input.zip` sha256 `0c5d5d3d6f647ed002bf0da8decdf850be6feadfd808cc9ac713f90105a22a2c`, manifest sha256 `0365b61603576970da27acd53f90bd8f25d8e93ba0e14ff2b4e2327a702fdd83`, 33 pinned files. Same UUT commit 3e2290f, images and dictionary as the first delivery; the manifest gains a `tool` pin (`harness`, 8dd2a5e, `v0.1.2-2-g8dd2a5e`, clean). This delivery supersedes the first.
- Seed-free rehearsal `fth rfr rfr-input.zip --dry-run`: OK. 39 preflight checks, 12 command lines rendered, 47 path tokens checked; `rfr.log` sha256 `6aee4505a8f7927c864ad6451fb06a082080110444bdff917e35530c203e7ac9`. No seed was requested and no run for record was made.
- Unsealed `fth audit` of dry-1 with 8dd2a5e: the run-start marker step still fails (`no manifest run-start marker for this manifest/run id`). The record does hold the markers (4294901761 followed by 3745703664 = 0xdf42e6f0, the manifest of the run), but the exported event has two arguments, `{"text": "Received a NO-OP string=4294901761", "nums": [4294901761]}`, and the tool reads the event only when it has one argument that is a decimal string. Reported to the project; the record was not changed.

## Release, third delivery (2026-11-19)

- Tooling: fprime-testing-harness `linux-host-coverage`@f57cce6182422e5dc2b8870cd85d80c748696f7f (marker events of `cmdDisp.NoOpStringReceived` are read), at `harness/` of the campaign root.
- `fth deliver --harness uut --tool harness`: OK, 0 findings. `rfr-input.zip` sha256 `9905f78df4173826f629855319850ace68ce8059377073a534beefac8445573e`, manifest sha256 `7a2404010d5a52da24500b3cf65b0d299e90a637f4aaa495d1a74912a6c52154`, 33 pinned files; tool pin f57cce6 (`v0.1.2-3-gf57cce6`, clean). UUT commit 3e2290f, images and dictionary unchanged. This delivery supersedes the first two.
- Seed-free rehearsal `fth rfr rfr-input.zip --dry-run`: OK, 39 preflight checks, 12 command lines, 47 path tokens; `rfr.log` sha256 `206a68908c8b0c8ac3b5b41058e9b4e3ccfe84d4aa463367a7f1f720b734e512`.
- `fth audit --unsealed --tests` of dry-1: ok, all 16 steps, the run-start marker step included.
- No seed was requested and no run for record was made. The bench was not used after the coverage run.

## Design change: capture without any sensor reading (2026-11-20)

- Ruling of Michael Starch, 2026-11-20 10:51 PST, verbatim: "I cannot.  Please update the design to allow for missing data across all sensors and the GET THIS RUN DONE". Passed on by the project: the GPS receiver has no fix and cannot be given sky, so every capture was refused at `LOCATION`. It is the authority for this change to the SDD.
- Change: the rule of 2026-11-19 for the attitude now holds for the three readings. A missing, undecodable or stale temperature, acceleration or location reading does not fail a capture: its values are stored as NaN, its sample time as zero, its flag false (`temperatureValid`, `attitudeValid`, `locationValid`), and one warning is emitted per unavailable reading. The picture is always stored. REQ-PiCamera-026 is rewritten for the three readings; REQ-PiCamera-010 and 011 now define stale and missing; REQ-PiCamera-005, 008, 012 and 015 are reworded to match.
- Record layout: `locationValid` follows `locationTime` and `temperatureValid` follows `temperatureTime`, so each flag sits with its values, as `attitudeValid` does. Members after `locationTime` move by one byte against the delivery of 2026-11-19.
- Decision: sibling events `TemperatureUnavailable` and `LocationUnavailable` beside `AttitudeUnavailable`, not one general event, so the existing event keeps its name, identifier and text.
- Decision: a reading that is present and fresh but invalid (non-finite temperature, latitude or longitude out of range, zero or non-finite acceleration) still fails with `METRIC_INVALID`. The rule is the same for the three readings, so the design is consistent; the ruling names missing data. `SENSOR_NO_DATA` and `SENSOR_STALE` remain in `FailReason` as warning reasons and no longer occur in `CaptureFailed`.
- Unchanged: camera failures, `TOO_LARGE`, `NO_CONTAINER` and `BUSY` fail the capture. No sensor data is substituted anywhere.
- System level: REQ-PiSensor-014 as written fails a capture for any stale metric; the exception is the project's to record.
- Unit tests: 22 pass (`AttitudeUnavailable` became `ReadingUnavailable`; `StaleReading`, `MissingReading`, `FailureResponse`, `RecoveryAfterFailure`, `RandomSequences` adapted). Coverage: lines 99.3% (266 of 268), branches 84.8% (368 of 434), functions 94.1% (32 of 34).
- Checklist, implementation stage, re-stamped: YES 30, N/A 3, UNCHECKED 37 (no clang-tidy plugin), NO 3 (3.12, 3.33, 5.3).
- Bench plan: one check per sensor, `<sensor> warning agrees with the sensor telemetry`: the warning is expected when the window holds no sample of the sensor, no warning when samples are fresh before the start and the end of the capture, and nothing is judged between.
- Review: none for this change; the project asked for speed and the change repeats the reviewed pattern of 2026-11-19 for two more readings.

## Release, fourth delivery (2026-11-20)

Written after the freeze; the package pins `comp/picam`@c2b6adbe50652d6f152face3f7a8dc094e4e4cb3, the commit before this section. It supersedes the deliveries of 2026-11-19.

- Images, built from scratch on the workstation [V]: pure sha256 `cc287e1d0cbae1dc8efe89491e017e848c326a5b561aff7a679c5a5342d867f9`; built for coverage `a51e1b2420c1b7244189a76d731bb279f32f5ec1fd6fb5e8fbe35bc97e907b8b`; dictionary `3d6bc63bfc51715de1f19b52100433694f91791a805c00f4ca9b1e6a488cd472`. `fth deliver` rebuilt the pure image and the dictionary to the same hashes.
- Sensors on the day [V]: BMP280 answering (no `TemperatureUnavailable` in any run); GPS without a fix (`LocationUnavailable(SENSOR_NO_DATA, 0)` in every capture); MPU6050 failed again about 15 s after the first image start (`imuManager.I2cError`), so every capture carried `AttitudeUnavailable`. A valid attitude was not seen on the bench.
- A first clean run at 62ca8b0 failed the response-time check of C-1 and C-2 in the harness: `CaptureStarted` and the dispatch event of `CAPTURE` were 1 ms apart and the check matched equal time tags. Fixed in c2b6adb (50 ms); the unit was not at fault.

| Run | Image | Planted fault | C-1 | C-2 | C-3 | Record |
|---|---|---|---|---|---|---|
| dry-1 | pure | none | PASS | PASS | PASS | `c88e696e…` |
| dry-2 | pure | `c1_second_capture` | FAIL, its 3 declared checks | PASS | PASS | `9b32c188…` |
| dry-3 | pure | `c2_capture_before_hold` | PASS | FAIL, its 2 declared checks | PASS | `56caa615…` |
| dry-4 | pure | `c3_capture_after_restart` | PASS | PASS | FAIL, its 3 declared checks | `ab2dfa21…` |
| cov-1 | coverage | none | PASS | PASS | PASS | `f554007f…` |

- `fth audit --unsealed --tests`: dry-1 ok, every step (15 OK lines, the run-start markers among them; the "16 steps" of the third delivery was a miscount of the same 15). dry-2 to dry-4: runner and replay agree on every test; the two failing steps are the ones a planted development run must fail (plant present, the planted command not replayed).
- Coverage: unit tests, lines 99.3% (266 of 268); on the target, `Components/PiCamera/`, 284 count files: lines 76.1% (429 of 564), functions 83.0% (39 of 47), branches 56.8% (319 of 562). Plan minimum 95 and 75. `fth dev-campaign --gcda-dir`: clean.
- `fth deliver --harness uut --tool harness` (fth f57cce6): OK, 0 findings. `rfr-input.zip` sha256 `77bf3d450b4ca54742dbb46fe5cd5ec7532b26c47f631bc7a8a88aa7d8103127`, manifest sha256 `34191a02a361ee8d062fd7fcb826c7187d7f2f9d6f017fb5801cc577975cea69`, 33 pinned files.
- Seed-free rehearsal `fth rfr rfr-input.zip --dry-run`: OK, 39 preflight checks, 12 command lines, 47 path tokens; `rfr.log` sha256 `c2b412e93b152346404d667218aed689f5bd2bb71020028055b703577a33d9d4`.
- No seed was requested and no run for record was made.

## Picture size for the downlink (2026-11-20)

- Instruction of the project, 2026-11-20 11:39 PST: the link carries 128 file bytes per second and the pictures were 60 to 127 kB, 10 to 16 minutes each; reduce a typical bench picture to about 20 kB, under 32 kB as design target.
- Change: `JPEG_QUALITY` 90 to 20. Nothing else: the resolution stays 640 x 480, because the approved scope and REQ-PiCamera-002 say at least 640 x 480; the project's suggestion of 640 x 360 was not taken for that reason and the project was told.
- Basis for 20 [V]: `rpicam-still` at 640 x 480 on the bench scene gave 21.9 kB at quality 90 and 7.2 kB at quality 30, a factor of 0.33; the target needs about 0.25 of the sizes seen at 90. Measured sizes of the component are in the release section below.
- `PICTURE_MAX_SIZE` (262144) is unchanged: it is the bound that fails a capture, not the typical size.
- The runs and the delivery of this morning are superseded.

## Release, fifth delivery (2026-11-20)

Written after the freeze; the package pins `comp/picam`@4a10a1a1c66c0b8d773db5136890cd9516fd8932, the commit before this section. It supersedes every earlier delivery.

- Images, built from scratch on the workstation [V]: pure sha256 `05d483517031a537010372a96d339cc3a1297f9789222bd4c4c4d23960f8a7d1`; built for coverage `50140d61b353350476c5b0443738e483271d445b1500a43e8c60f3ae64438782`; dictionary `bd66b80e75c91baf121d5ba7dc6ca98b129cd23fd6e19aca970cdee8d9a89a80`. `fth deliver` rebuilt the pure image and the dictionary to the same hashes.
- Picture size at `JPEG_QUALITY` 20 [V]: 9 491 to 11 666 bytes over the 22 captures of the five runs. One stored picture was read back from its product file and decodes as a 640 x 480 picture of the bench scene, a textured surface with little detail; a scene with more detail will be larger.
- Sensors: BMP280 answering (no `TemperatureUnavailable`); GPS without a fix and MPU6050 silent, so every capture carried `LocationUnavailable` and `AttitudeUnavailable`.

| Run | Image | Planted fault | C-1 | C-2 | C-3 | Record |
|---|---|---|---|---|---|---|
| dry-1 | pure | none | PASS | PASS | PASS | `d7987c5d…` |
| dry-2 | pure | `c1_second_capture` | FAIL, its 3 declared checks | PASS | PASS | `74d01e04…` |
| dry-3 | pure | `c2_capture_before_hold` | PASS | FAIL, its 2 declared checks | PASS | `e0c8e00a…` |
| dry-4 | pure | `c3_capture_after_restart` | PASS | PASS | FAIL, its 3 declared checks | `2f1f83db…` |
| cov-1 | coverage | none | PASS | PASS | PASS | `eef38518…` |

- `fth audit --unsealed --tests`: dry-1 ok, every step; dry-2 to dry-4: runner and replay agree on every test, and only the two steps a planted development run must fail are failed.
- Coverage: unit tests, lines 99.3% (266 of 268), report at `ut-coverage/` of the campaign root and `inputs/coverage/ut/` of the package; on the target, lines 76.1% (429 of 564), functions 83.0%, branches 56.8%. `fth dev-campaign --gcda-dir`: clean.
- `fth deliver --harness uut --tool harness` (fth f57cce6): OK, 0 findings. `rfr-input.zip` sha256 `33f7f126f693d20104d18634f02c851e07a8a83e78b96dcf3a07502b5ca553a9`, manifest sha256 `b63e0625535abff90fb249b27b41d01707e3e2e1db5072bf785aac4f8c05e6b5`, 33 pinned files.
- Seed-free rehearsal: OK, 39 preflight checks; `rfr.log` sha256 `0dc39b6aff07694150f34ddc3eaac64b4d06d6df1e384438fb73393c1146f531`.
- No seed was requested and no run for record was made.

## Link changed to TCP (2026-11-23)

- Ruling of Michael Starch, 2026-11-23 13:18 PST, relayed by the project: "Ok, please switch to TCP, and continue development w/o the radio" and "Yes, close this out." The flight RFM69 of the bench failed, so the fifth delivery, whose runs went over the radio, cannot be run for record.
- `comp/picam` was fast-forwarded from 57c31ec to `deploy/base`@c7c1e96 (the deployment with `PISENSOR_COM=TCP` as default) by instruction of the project; the bench changes are on top. The UUT pin moves from 4a10a1a to the head of this branch because the image must be built from a tree that has the TCP topology.
- The component did not change: `git diff --stat 4a10a1a c7c1e96 -- Components/PiCamera` lists `Components/PiCamera/docs/ledger.md` only. Unit tests and their coverage were not rerun.
- Bench files taken by path from `sys/harness`@aed818d, as instructed (`git checkout aed818d -- <path>`): `test/int/bench/tcp_bridge.py` and `test/int/bench/yamcs_bench.py`. Nothing else of the system harness or plan was taken.
- Bench description (`bench.json`, `bench-coverage.json`): the bridge is `test/int/bench/tcp_bridge.py` on TCP port 50000, the image is started with `-a 192.168.10.1 -p 50000`, and `flash` copies `inputs/PrmDb.dat` as the system bench does, so the image runs with the project parameters.
- Tool: fth `linux-host-coverage`@3c4ab8e. `fth verify-plan --tests` passes with both bench files (31 named checks); the 4 known-answer checks pass; the replay of the last radio clean-run record passes 3 of 3.
- Texts that named the radio, corrected; not reviewed:

| File | Old | New |
|---|---|---|
| `plan.json`, `plan.md`, setup of C-1 | "camera free, GPS fix, RFM69 link up." | "camera free, TCP link to the ground workstation up." |
| `README.md` | "fprime-yamcs behind the RFM69 bridge" | "fprime-yamcs behind the TCP bridge `test/int/bench/tcp_bridge.py`, which the image connects to" |
| `README.md` | "The radio uplink has no retransmission. The sender sends a command again, ..." | "The link is TCP and loses no command. The sender still sends a command again, ..." |
| `README.md` | "`python3` (with `yamcs-client` and `pyserial`)" | "`python3` (with `yamcs-client`)" |
| `README.md` | "`inputs/`: the image and its dictionary." | adds `PrmDb.dat` and how it is built |
| `bench.json`, `bench-coverage.json`, notes | "soakee behind the RFM69 link; ground is fprime-yamcs on the workstation." | "soakee on a TCP link: the image connects to the bench bridge on the workstation, which passes its frames to fprime-yamcs; ..." |

- Left as written: the SDD rationale of `JPEG_QUALITY` speaks of "the radio link" and 128 file bytes per second. The constant is unchanged and the project said not to change the component; the sentence describes why the value was chosen.
- The setup text of C-1 also said "GPS fix", untrue since the ruling of 2026-11-20; it is removed with the radio wording.

## Bench recipes made to pass the rehearsal on a TCP bench (2026-11-23)

- The project reported four refusals `fth rfr` gives a TCP bench at 3c4ab8e. Checked against `fth/rfr.py` and the two bench files: two apply here.
  - Applies: the preflight requires a serial device. Both bench files now declare `"vars": {"uart": null}`, the syntax of fth `linux-host-coverage`@ecbd11f; no recipe line uses `{uart}`.
  - Applies: `flash --prm inputs/PrmDb.dat` names a path outside the package roots. `test/int/bench/PrmDb.dat` is taken by path from `sys/harness`@8432b44 (sha256 `a31359bad537b7ce62b055d72068068884d39c63f1d775df32ca27e575f47527`, the same bytes the hub built from `PiSensor/project/config/PrmDb.json` and the dictionary of d50ceb1), and `flash` names it as `uut/test/int/bench/PrmDb.dat`.
  - Does not apply: no recipe line passes `--pi-dir` (the adapter default `pisensor-campaign/fth-uut` is used), and the recorder line has no `--root`.
- `test/int/bench/yamcs_bench.py` stays as taken from aed818d; the later change on `sys/harness` only moves the default Pi directory to that of the system campaign.
- Runs made at d50ceb1 with fth 3c4ab8e before this change, for information only and superseded: clean run 3 of 3 PASS (record `84b7b0f2…`); planted `c1_second_capture`, C-1 FAIL as declared (`ac8a39a1…`); planted `c2_capture_before_hold`, C-2 FAIL on its 2 declared checks (`c1715a4f…`). First runs over TCP: the image, the bridge and the recorder work together.
- Tool from here: fth `linux-host-coverage`@ecbd11f.


## Release over TCP (2026-11-23)

- UUT pin `comp/picam`@45b005904b1f1e323eea0ce16f6086cd00154abc; tool fth `linux-host-coverage`@ecbd11f. Hub builds from scratch; pure image `b5a7133c886c7eece5e13edf16ac53277a19137e9d20e02954223d4ab9d360e0`, coverage image `e4adb3909356beb1451f5ee002b1e7e68b3f37f5a69ca741127d01763d10a548`, dictionary `c2e5c7e6d876d2a8c16a88a2f43dc818eb18372fba1b02ae2648e83a860b009f`. The coverage image is not reproduced bit for bit by a second build (an earlier build of the same commit gave `3324c26b…`); the pure image is.

| Run | Image | Planted fault | C-1 | C-2 | C-3 | Record |
|---|---|---|---|---|---|---|
| dry-1 | pure | none | PASS | PASS | PASS | `801a34a6…` |
| dry-2 | pure | `c1_second_capture` | FAIL, its 3 declared checks | PASS | PASS | `f6d6f375…` |
| dry-3 | pure | `c2_capture_before_hold` | PASS | FAIL, its 2 declared checks | PASS | `a71d26fd…` |
| dry-4 | pure | `c3_capture_after_restart` | PASS | PASS | FAIL, 2 of its 3 declared checks | `6d513c29…` |
| cov-1 | coverage | none | PASS | PASS | PASS | `483dc724…` |

- dry-4: the declared check `last(piCamera.CapturesCompleted) == 1` did not fail. The image of `deploy/base` sends this channel every 5 s; the sample inside the window fell between the two captures and read 1, and the sample reading 2 came 0.33 s after the end marker. The planted fault is caught by the two event counts. Not corrected in this delivery: the predicate depends on the telemetry period.
- Link: every command was sent once (no resend); the only sequence count jumps on the ground are the two of the restart of C-3 in each run (new count 0).
- Sensors: no `TemperatureUnavailable`; `AttitudeUnavailable` and `LocationUnavailable` in every capture (MPU6050 `I2cError` 61 to 100 per run, GPS without fix). Pictures 5 501 to 5 514 bytes over 22 captures; none was decoded.
- `fth dev-campaign --gcda-dir`: CLEAN; on the target lines 76.1% (429 of 564), functions 83.0% (39 of 47), branches 56.8% (319 of 562), 289 `.gcda` files. Unit tests rerun at this commit on the development machine: 22 pass, lines 99.3% (266 of 268); the report in the package (`inputs/coverage/ut/`) is still the one produced at 89357e5.
- `fth deliver --harness uut --tool harness`: OK, 33 pinned files; `rfr-input.zip` sha256 `1536efff513bcb9c0c86c0d7033404d6d54d72c7dac8ed15f0a65ea93eedbf3c`, manifest sha256 `29ec9c0fec6b972adf4bc5b8c27905057a6caa5f85a59e09bc42fecb7bd9a2b6`.
- `fth rfr --dry-run`: rehearsal OK, 37 preflight checks, the three serial checks "not applicable: bench declares no serial device"; `rfr.log` sha256 `f6cf93246e69d2f6190a1b9a04ff2ec5fd0c42f28c6481f01256e7f9b93fa093`.
- `fth audit --unsealed --tests`: dry-1 ok, 15 steps; dry-2 to dry-4: runner and replay agree on every test, and only the two steps a planted development run must fail are failed.
- No seed was requested and no run for record was made.
