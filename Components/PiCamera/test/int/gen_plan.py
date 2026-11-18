#!/usr/bin/env python3
"""Generates plan.json for the PiCamera component test plan (design phase). Run from this directory."""
import json
R = lambda *n: [f"REQ-PiCamera-{i:03d}" for i in n]
def W(a, b, reset=False): return [{"name": "W", "start_id": a, "end_id": b, "reset": reset}]
def H(name, text, **args): return {"helper": name, "text": text, "args": args}
T = []
def t(id, title, purpose, covers, setup, procedure, windows, metrics=(), knobs=(), evidence="", rationale=()):
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup,
              "procedure": list(procedure), "windows": windows, "metrics": list(metrics),
              "rationale": [{"pred": p, "text": x} for p, x in rationale], "knobs": list(knobs), "evidence": evidence})
NOM = "Prototype image running, link up, camera attached and free, product directory empty."
def jfif(p): return H("picture_is_jfif", f"picture record of {p} is JFIF, SOI to EOI, 640 x 480", product=p, width=640, height=480)
def ptime(p, which="CAPTURE"): return H("picture_time_between", f"bench time of {which} sent - 2 s <= capture time record of {p} <= its completion + 2 s", product=p, tol_s=2)
OKC = "check: event piCamera.CaptureStarted count == 1; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 1; check: delta(piCamera.CapturesFailed) == 0; "
L0 = "Feasibility entry: covers no requirement, takes no planted fault; a `require` that does not hold makes the tests named UNVERIFIED. "

t("L0-1", "Image identity", "Proves the running image is the manifest's image.", [], "Prototype image running; link up.",
  ["MARK(10)", "VERSION(ALL)", "bracket (2 Heartbeat samples)", "MARK(11)"], W(10, 11),
  evidence="require: Version events equal the manifest describe strings.")
t("L0-2", "Camera library identity", "Proves the image runs the packaged libcamera of the pinned version and links no OpenCV.", R(16, 17),
  "Prototype image running; link up.",
  ["MARK(12)", "action: log `ldd` of the deployment binary and `dpkg -S` plus `dpkg-query -W` of the package owning each resolved libcamera and libjpeg library, over ssh, into bench-actions.log", "bracket (2 Heartbeat samples)", "MARK(13)"], W(12, 13),
  metrics=[H("library_identity", "package owning the resolved libcamera.so has version 0.8.0; every resolved library belongs to a Raspberry Pi OS package; ldd lists no opencv library", version="0.8.0")],
  evidence="The bench log lines; evidence outside the UUT's reporting path. REQ-PiCamera-016 is also inspected (build inputs).")
t("L0-3", "Camera line off and on", "Proves the bench can make the camera unavailable and available without a process restart.", [], NOM,
  ["MARK(14)", "bracket (2 Heartbeat samples)", "BENCH_LINE(CAMERA, OFF)", "action: log `rpicam-still --list-cameras` into bench-actions.log", "BENCH_LINE(CAMERA, ON)", "action: log `rpicam-still --list-cameras` into bench-actions.log", "bracket (2 Heartbeat samples)", "MARK(15)"], W(14, 15),
  evidence=L0 + "require (L5-1): first listing names no camera, second names the camera of the SDD Introduction; check: event sysTester.Started count == 0.")
t("L0-4", "Capture duration against trigger latency", "Proves a capture lasts long enough for the bench to act between CaptureStarted and the reply.", [], NOM,
  ["MARK(16)", "bracket (2 Heartbeat samples)", "CAPTURE()", "action: log the bench time CaptureStarted was received and a no-op action triggered on it, into bench-actions.log", "bracket (2 Heartbeat samples)", "MARK(17)"], W(16, 17),
  metrics=[H("trigger_margin", "t(event productManager.ProductWritten) - t(event piCamera.CaptureStarted) >= 2 x (bench time of the triggered action - t(event piCamera.CaptureStarted)) (require, L3-1 and L3-2)", factor=2)],
  evidence=L0 + "The measured capture duration and trigger latency are recorded in the ledger.")
t("L0-5", "Camera holder acquisition", "Proves the bench holder process owns the camera within the settle time the fault test uses.", [], NOM,
  ["MARK(18)", "bracket (2 Heartbeat samples)", "action: start `rpicam-hello -t 0 --nopreview` on the Pi; log its pid and the time of its first frame line into bench-actions.log", "action: stop rpicam-hello; log its exit into bench-actions.log", "bracket (2 Heartbeat samples)", "MARK(19)"], W(18, 19),
  metrics=[H("holder_acquired_within", "first frame line of the holder - its start <= 5 s (require, L5-2)", bound_s=5)],
  evidence=L0 + "The measured acquisition time is the settle time of L5-2.")
t("L2-1", "One capture delivers one picture", "Proves a capture request delivers one 640x480 JFIF picture acquired after the request.", R(1, 2, 17), NOM,
  ["MARK(20)", "bracket (2 Heartbeat samples)", "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", "bracket (2 Heartbeat samples)", "MARK(21)"], W(20, 21),
  metrics=[jfif("P1"), ptime("P1")], knobs=["capture_twice"],
  evidence=OKC + "check: last(piCamera.LastPictureSize) == size of the picture record of the ground file of the last product written.",
  rationale=[("delta(piCamera.CapturesCompleted) == 1", "counter counts from process start; only its change in the window is judged")])
t("L2-2", "Two captures deliver two different pictures", "Proves each capture delivers a newly acquired 640x480 JFIF picture.", R(1, 2, 17), NOM,
  ["MARK(22)", "bracket (2 Heartbeat samples)", "CAPTURE()", "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", "DOWNLINK(P2)", "wait CFDP transaction finished at the ground", "bracket (2 Heartbeat samples)", "MARK(23)"], W(22, 23),
  metrics=[jfif("P1"), jfif("P2"), H("pictures_differ", "sha256 of the picture records of P1 and P2 differ", a="P1", b="P2"), ptime("P2", "the second CAPTURE"),
           H("picture_time_after", "capture time record of P2 > capture time record of P1", a="P1", b="P2")], knobs=["corrupt_picture"],
  evidence="check: event piCamera.CaptureStarted count == 2; check: event piCamera.CaptureFailed count == 0; check: delta(piCamera.CapturesCompleted) == 2; check: delta(piCamera.CapturesFailed) == 0.",
  rationale=[("sha256 of the picture records of P1 and P2 differ", "sensor noise makes two frames of one scene differ; equal bytes mean a frame was reused")])
RST = ("The window is split at its single sysTester.Started row: part A is the rows before it, part B the rows after it. "
       "require (else UNVERIFIED, the race was lost): A: event piCamera.CaptureStarted count == 1; A: event productManager.ProductWritten count == 0. "
       "check: event sysTester.Started count == 1; check: B: event piCamera.CameraFound count == 1, its camera argument equal to the identification of the SDD Introduction; "
       "check: B: event piCamera.CaptureStarted count == 1; check: B: event piCamera.CaptureFailed count == 0; check: B: event productManager.ProductWritten count == 1; "
       "require: B: event cmdDisp.OpCodeError count == 0; require: B: commands sent after the restart == count(event cmdDisp.OpCodeDispatched).")
for i, (tid, how, a) in enumerate([("L3-1", "a process kill", "kill the deployment process (SIGKILL), triggered by the CaptureStarted event"),
                                   ("L3-2", "a service restart", "restart the deployment service (systemctl restart), triggered by the CaptureStarted event")]):
    t(tid, f"Capture after {how} during a capture", f"Proves the first capture after {how} during a capture succeeds.", R(19), NOM,
      [f"MARK({30+2*i})", "CAPTURE() without waiting for completion", "wait event piCamera.CaptureStarted", f"action: {a}", "wait first Heartbeat samples at the ground",
       "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", f"MARK({31+2*i})"], W(30+2*i, 31+2*i),
      metrics=[jfif("P1")], knobs=["capture_after_restart_dropped"] if i == 0 else [], evidence=RST,
      rationale=[("commands_sent == count(event cmdDisp.OpCodeDispatched)", "the first CAPTURE has no completion; the window requires STD-RST and the part B command predicates of the evidence line")])
FLT = ("The window requires STD-NOERR; the command error count is a check. check: event cmdDisp.OpCodeError count == 1; check: first CAPTURE completes with error; "
       "check: event piCamera.CaptureFailed(reason={r}, step={st}) count == 1; check: event piCamera.CaptureFailed count == 1; check: event piCamera.CaptureStarted count == 2; "
       "check: delta(piCamera.CapturesFailed) == 1; check: second CAPTURE completes; check: delta(piCamera.CapturesCompleted) == 1; check: event sysTester.Started count == 0.")
t("L5-1", "Camera absent, then back", "Proves an absent camera gives NO_CAMERA and the next capture succeeds without a restart.", R(14), NOM,
  ["MARK(40)", "bracket (2 Heartbeat samples)", "BENCH_LINE(CAMERA, OFF)", "CAPTURE()", "bracket (2 Heartbeat samples)", "BENCH_LINE(CAMERA, ON)", "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", "bracket (2 Heartbeat samples)", "MARK(41)",
   "teardown: action: bind the camera driver over ssh (not a command, outside the planted path); log `rpicam-still --list-cameras`"], W(40, 41),
  metrics=[jfif("P1")], knobs=["camera_kept_absent"],
  evidence=FLT.format(r="NO_CAMERA", st="DETECT") + " check: piCamera.CameraPresent == false in the bracket after the first CAPTURE; check: last(piCamera.CameraPresent) == true.",
  rationale=[("event cmdDisp.OpCodeError count == 0", "the first CAPTURE is expected to fail; exactly one command error is a named check")])
t("L5-2", "Camera held by another process, then free", "Proves a camera in use elsewhere gives CAMERA_ERROR and the next capture succeeds without a restart.", R(14), NOM,
  ["MARK(42)", "bracket (2 Heartbeat samples)", "action: start `rpicam-hello -t 0 --nopreview` on the Pi (holds the camera); wait the L0-5 settle time; log its pid", "CAPTURE()", "action: log that the holder pid is alive; stop rpicam-hello; log its exit", "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", "bracket (2 Heartbeat samples)", "MARK(43)",
   "teardown: action: stop any rpicam-hello over ssh"], W(42, 43),
  metrics=[jfif("P1")],
  evidence="require: bench-actions.log shows the holder alive at the first CAPTURE send and after its completion. " + FLT.format(r="CAMERA_ERROR", st="OPEN"),
  rationale=[("event cmdDisp.OpCodeError count == 0", "the first CAPTURE is expected to fail; exactly one command error is a named check")])
t("L7-1", "Final picture for independent verification", "Leaves the final-state record: the last picture on board is the 640x480 JFIF picture received at the ground.", R(1, 2), NOM,
  ["MARK(50)", "bracket (2 Heartbeat samples)", "CAPTURE()", "DOWNLINK(P1)", "wait CFDP transaction finished at the ground", "bracket (2 Heartbeat samples)", "MARK(51)"], W(50, 51),
  metrics=[jfif("P1"), H("final_sha256_matches", "bench sha256 of the product file on board == sha256 of the ground file", product="P1")],
  evidence=OKC + "No teardown: the product stays for the bench `sha256sum` taken over ssh after the run. The hash equality is transport evidence; the picture predicates are the component's.")

req = {}
for x in T:
    for r in x["covers"]: req.setdefault(r, {"tests": [], "verification": "Integration Test", "note": ""})["tests"].append(x["id"])
UT = "Unit Test (unit-test list, SDD section 8)"
for n in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 18, 20, 21, 22, 23, 24): req[R(n)[0]] = {"tests": [], "verification": UT, "note": "needs the camera substitute and the port tester of the unit-test build"}
req[R(16)[0]].update(verification="Inspection and Integration Test", note="inspection of the build inputs; L0-2 records the linked libraries")
STD = ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)", "event cmdDisp.OpCodeError count == 0", "event cmdDisp.TooManyCommands count == 0", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"]
plan = {
 "name": "PiCamera component test plan",
 "markers": {"command": "sysTester.MARK", "event": "sysTester.Marker", "arg": "id", "reserved_min": 4294901760},
 "event_patterns": {"sysTester.Marker": "SystemTester marker (?P<id>\\d+)$",
                    "piCamera.CaptureStarted": "Capture (?P<context>\\d+) started$",
                    "piCamera.CaptureFailed": "Capture (?P<context>\\d+) failed: (?P<reason>\\w+) at (?P<step>\\w+) code (?P<code>-?\\d+)$"},
 "packets": {"Heartbeat": ["sysTester.UptimeS", "cmdDisp.CommandsDispatched", "piCamera.CapturesCompleted", "piCamera.CapturesFailed", "piCamera.LastPictureSize", "piCamera.CameraPresent", "piCamera.PictureOutstanding"]},
 "std_complete": STD,
 "abs": {"STD-RST": ["both markers present", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"],
         "STD-NOERR": [p for p in STD if "OpCodeError" not in p]},
 "helpers_module": "planted_faults.py",
 "helpers": [{"instance": "sysTester", "component": "SystemTester", "src": "SystemTester", "repo": "https://github.com/lestarch-autobot/fprime-pi-sensor-reference"}],
 "uut": "PiSensor::PiCamera (Components/PiCamera/docs/sdd.md) as instance piCamera",
 "deployment": "PiSensor full system deployment plus the harness component sysTester, prototype image (TCP); the test deployment of the project plan (SSDD decision D13)",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 75},
              "not_covered_ack": ["Library error returns of the libcamera implementation of the camera interface (configure, allocate, queue request) that the bench cannot force: the unit tests force each through the camera substitute at the component boundary.",
                                  "Refusals `BUSY` and `PICTURE_OUTSTANDING` and a dropped `acquire`: not reachable on the bench with one requester; unit tests cover them."],
              "rationale": "Baselines of the skill. Unit-test lines are measured on the component with the camera substitute; the libcamera implementation of the camera interface is measured on target only."},
 "image_version": {"policy": "required"},
 "final_state": {"accepted_evidence": "bench sha256sum of the L7-1 product file, taken over ssh after the run into record/raw/final-state.txt, compared by the auditor with the sha256 of the ground file in record/raw/files/",
                 "rationale": "The bench reads the file itself, outside the UUT's reporting path."},
 "requirements": dict(sorted(req.items())),
 "scope": ["L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)` as in the project plan. Event rate [I]: at most 2 events per second in any window (one capture gives CaptureStarted, ProductWritten and two command events over about 2 s; measured at L0-4). The piCamera channels are added to the heartbeat set so each window brackets them.",
           "- UUT: `piCamera` in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13; ground system fprime-yamcs over TCP.",
           "- The picture is judged on the ground copy of the data product (picture record), delivered by `productManager` and CFDP; `CAPTURE`, `DOWNLINK` are `productManager` commands, `BENCH_LINE`, `MARK` are `sysTester` commands.",
           "- Out of scope: the data product's other records, the RFM69 link, picture content."],
 "entry_gates": ["- Unit tests of PiCamera pass with line coverage at or above the plan's threshold.",
                 "- Camera attached; its model and `rpicam-still --list-cameras` reply recorded in the SDD Introduction (a module libcamera does not support reopens the requirements).",
                 "- `dpkg-query -W libcamera-dev` on the target read once; a version other than 0.8.0 reopens REQ-PiCamera-017 before any run.",
                 "- Bench line CAMERA of `sysTester.BENCH_LINE` makes the camera unavailable and available without a process restart (driver unbind and bind, as project test L5-11); L0-3 passes.",
                 "- Image built from the manifest SHAs; L0-1 to L0-5 pass; product directory empty at the start of each test (teardown removes the products; L7-1 has no teardown)."],
 "levels": ["L0 provenance and feasibility · L2 functional · L3 restart · L5 fault paths · L7 final state. No L4: no requirement has an endurance bound. No L6: the component has no command to reject; refusals at its ports (`BUSY`, `PICTURE_OUTSTANDING`, rejected return) are unit tests."],
 "not_covered": ["- REQ-PiCamera-003 to -013, -015, -018, -020 to -024: unit tests; the requester (`productManager`) sends one request at a time and returns every picture, so `BUSY`, `TIMEOUT`, `NO_BUFFER`, `PICTURE_OUTSTANDING`, `TOO_LARGE` and a rejected return cannot be forced on the bench.",
                 "- REQ-PiCamera-016: the build inputs are inspected; L0-2 judges the linked libraries only.",
                 "- A camera that stops answering during a capture (`TIMEOUT`) and a frame the library marks bad: not plantable on the bench without touching the ribbon cable under power.",
                 "- Picture content (exposure, focus)."],
 "decision_log": ["1. 2026-11-17 designer — the component is tested in the project's test deployment (full deployment + `sysTester`), not a reduced one.",
                  "2. 2026-11-17 designer — REQ-PiCamera-001 'acquired after its request' is judged by two captures giving different picture bytes and by the capture time record against bench time (tolerance 2 s, project decision D12).",
                  "3. 2026-11-17 designer — max planted faults per draw 2; menu covers L2-1, L2-2, L3-1, L5-1.",
                  "5. 2026-11-17 designer — `picture_is_jfif` decodes the picture record on the bench with Pillow 11 (`Image.load()`), an independent decoder: bytes 0-1 FFD8, APP0 `JFIF`, last two bytes FFD9 with nothing after, full decode without error or warning, 640 x 480.",
                  "6. 2026-11-17 designer — a restart window is split at its `sysTester.Started` row; the Pi clock is wall time, so a restart gives no clock backstep to split on.",
                  "4. 2026-11-17 designer — `BENCH_LINE(CAMERA, state)` is a bench line this plan needs from `sysTester`; reported to the parent campaign."],
 "tests": T}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
