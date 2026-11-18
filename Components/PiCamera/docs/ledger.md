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
  - P5 Telemetry Table 2 and picture size 1280x960 (REQ-PiCamera-015, Table 3).
  - P6 Failure reasons of Table 1 (REQ-PiCamera-005).
- Device identity: camera model unknown until attached (after SSDD approval); a mismatch with the libcamera-supported sensors reopens requirements.
