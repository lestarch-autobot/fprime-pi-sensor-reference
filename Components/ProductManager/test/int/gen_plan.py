#!/usr/bin/env python3
"""Generates plan.json for the ProductManager component system tests (design phase). Run from this directory."""
import json, collections
R = lambda *n: [f"REQ-ProductManager-{i:03d}" for i in n]
def W(a, b, name="W"): return {"name": name, "start_id": a, "end_id": b, "reset": False}
def H(name, text, **args): return {"helper": name, "text": text, "args": args}
T = []
def t(id, title, purpose, covers, setup, procedure, windows, metrics=(), knobs=(), evidence="", rationale=()):
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup,
              "procedure": list(procedure), "windows": windows, "metrics": list(metrics),
              "rationale": [{"pred": p, "text": x} for p, x in rationale], "knobs": list(knobs), "evidence": evidence})
NOM = "Prototype image running, link up, camera answering, product directory empty."
FLT = "Flight image running, ground Pi with RFM69 and groundRadio up, camera answering, product directory empty."
CAP30 = H("command_completed_within", "CAPTURE command completion (cmdDisp.OpCodeCompleted of its opcode) - t(productManager.CAPTURE sent) <= 30 s", command="productManager.CAPTURE", bound_s=30)
ONEERR = ("event cmdDisp.OpCodeError count == 0", "the rejected command fails by design; the window requires STD-ERR (exactly one failed command)")
SLOW = H("downlink_duration_at_least", "CFDP transaction duration of the first DOWNLINK from the ground transfer record >= 10 s (require)", bound_s=10)
NOFILE = "check: no CFDP transaction starts at the ground in the window"

t("L0-1", "Image identity and marker round-trip", "Proves the running image is the manifest's prototype image and the marker round-trips.", [],
  "Prototype image running on the Raspberry Pi 5; link up.",
  ["MARK(1000)", "VERSION(ALL)", "bracket (2 Heartbeat samples)", "MARK(0xA5A5)", "MARK(1001)"], [W(1000, 1001)],
  evidence="Version events equal the manifest describe strings; three Marker events in order, ids byte-exact.")
t("L2-1", "Capture names its product", "Proves a successful capture emits ProductWritten naming the one new product file.", R(14), NOM,
  ["MARK(1010)", "CAPTURE()", "LIST_DIR(products)", "MARK(1011)"], [W(1010, 1011)], metrics=[CAP30], knobs=["capture_twice"],
  evidence="check: event productManager.ProductWritten count == 1 (ACTIVITY_HI, names P); check: the sysTester.DirListing event names P and no other file; check: ABS.")
t("L2-2", "Second capture leaves the first product unchanged", "Proves a second capture names a new product and leaves the first unchanged.", R(14, 15), NOM,
  ["MARK(1012)", "CAPTURE()", "DUMP_SHA256(P1, 1)", "CAPTURE()", "DUMP_SHA256(P1, 2)", "LIST_DIR(products)", "MARK(1013)"], [W(1012, 1013)], knobs=["corrupt_first_product"],
  evidence="check: event productManager.ProductWritten count == 2 with different names (P1, P2); check: the two sysTester.Sha256 events of P1 are equal; check: the sysTester.DirListing event names P1 and P2 only; check: ABS.")
t("L2-3", "Captures around a delete leave the first product unchanged", "Proves captures and a delete of another product leave a stored product unchanged.", R(15, 34), NOM,
  ["MARK(1014)", "CAPTURE()", "DUMP_SHA256(P1, 1)", "CAPTURE()", "DELETE(P2)", "CAPTURE()", "DUMP_SHA256(P1, 2)", "LIST_DIR(products)", "MARK(1015)"], [W(1014, 1015)],
  evidence="check: event productManager.ProductWritten count == 3 with three different names (P1, P2, P3); check: event productManager.ProductDeleted count == 1 and names P2; check: the two sysTester.Sha256 events of P1 are equal; check: the sysTester.DirListing event names P1 and P3 only; check: ABS.")
t("L2-4", "Delete removes the named product", "Proves DELETE removes the named product and no other, before its command response.", R(34), NOM,
  ["MARK(1016)", "CAPTURE()", "CAPTURE()", "DUMP_SHA256(P2, 1)", "DELETE(P1)", "LIST_DIR(products)", "DUMP_SHA256(P2, 2)", "LIST_PRODUCTS()", "MARK(1017)"], [W(1016, 1017)], knobs=["delete_other"],
  evidence="check: event productManager.ProductDeleted count == 1 and names P1; check: the sysTester.DirListing event names P2 only; check: the two sysTester.Sha256 events of P2 are equal; check: event productManager.ProductStored count == 1 and names P2; check: event productManager.ProductsListed count == 1 with count 1; check: ABS.")
t("L5-1", "Capture during a capture", "Proves a CAPTURE during a capture is rejected and the first capture stores its product.", R(25), NOM,
  ["MARK(1020)", "CAPTURE() without waiting for completion", "CAPTURE()", "wait event productManager.ProductWritten", "LIST_DIR(products)", "MARK(1021)"], [W(1020, 1021)], metrics=[CAP30], knobs=["second_capture_dropped"],
  evidence="require (else UNVERIFIED, the race was lost): the second CAPTURE is dispatched before the ProductWritten event. check: event productManager.CommandRejected count == 1 (WARNING_LO, reason CAPTURE_IN_PROGRESS); check: event productManager.ProductWritten count == 1; check: the sysTester.DirListing event names one file, the product named by ProductWritten; check: ABS.",
  rationale=[ONEERR])
t("L5-2", "Capture after a rejected capture", "Proves a rejected CAPTURE does not disturb the capture in progress or the next one.", R(25), NOM,
  ["MARK(1022)", "CAPTURE() without waiting for completion", "CAPTURE()", "wait event productManager.ProductWritten", "CAPTURE()", "LIST_DIR(products)", "MARK(1023)"], [W(1022, 1023)],
  evidence="require (else UNVERIFIED, the race was lost): the second CAPTURE is dispatched before the first ProductWritten event. check: event productManager.CommandRejected count == 1 (reason CAPTURE_IN_PROGRESS); check: event productManager.ProductWritten count == 2 with different names; check: the sysTester.DirListing event names those two files only; check: ABS.",
  rationale=[ONEERR])
t("L5-3", "Downlink during a downlink", "Proves a DOWNLINK during a downlink is rejected and the first transfer delivers its product.", R(31), FLT,
  ["MARK(1030)", "CAPTURE()", "CAPTURE()", "DUMP_SHA256(P1, 1)", "DOWNLINK(P1) without waiting for completion", "wait event productManager.DownlinkStarted", "DOWNLINK(P2)", "wait CFDP transaction finished at the ground", "MARK(1031)"], [W(1030, 1031)], metrics=[SLOW],
  evidence="check: event productManager.CommandRejected count == 1 (WARNING_LO, reason DOWNLINK_IN_PROGRESS); check: event productManager.DownlinkStarted count == 1; check: exactly one file arrived and its name is P1; check: sha256 of record/raw/files/<P1> == hash in the sysTester.Sha256 event; check: event productManager.DownlinkComplete count == 1; check: ABS.",
  rationale=[ONEERR])
t("L5-4", "Repeated downlink of the product in transfer", "Proves a DOWNLINK naming the product in transfer is rejected without a second transfer.", R(31), FLT,
  ["MARK(1032)", "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P) without waiting for completion", "wait event productManager.DownlinkStarted", "DOWNLINK(P)", "wait CFDP transaction finished at the ground", "MARK(1033)"], [W(1032, 1033)], metrics=[SLOW],
  evidence="check: event productManager.CommandRejected count == 1 (reason DOWNLINK_IN_PROGRESS); check: exactly one CFDP transaction at the ground, finished complete; check: sha256 of record/raw/files/<P> == hash in the sysTester.Sha256 event; check: ABS.",
  rationale=[ONEERR])
t("L5-5", "Delete during the product's downlink", "Proves a DELETE of the product in transfer is rejected and the product is delivered and kept.", R(35), FLT,
  ["MARK(1034)", "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P) without waiting for completion", "wait event productManager.DownlinkStarted", "DELETE(P)", "wait CFDP transaction finished at the ground", "DUMP_SHA256(P, 2)", "LIST_DIR(products)", "MARK(1035)"], [W(1034, 1035)], metrics=[SLOW], knobs=["delete_before_downlink"],
  evidence="check: event productManager.CommandRejected count == 1 (WARNING_LO, reason PRODUCT_IN_DOWNLINK); check: event productManager.ProductDeleted count == 0; check: sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event; check: the two sysTester.Sha256 events are equal; check: the sysTester.DirListing event names P; check: ABS.",
  rationale=[ONEERR])
t("L5-6", "Delete after the product's downlink", "Proves a DELETE rejected during the downlink succeeds once the transfer has ended.", R(35, 34), FLT,
  ["MARK(1036)", "CAPTURE()", "DOWNLINK(P) without waiting for completion", "wait event productManager.DownlinkStarted", "DELETE(P)", "wait CFDP transaction finished at the ground", "wait event productManager.DownlinkComplete", "DELETE(P)", "LIST_DIR(products)", "MARK(1037)"], [W(1036, 1037)], metrics=[SLOW],
  evidence="check: event productManager.CommandRejected count == 1 (reason PRODUCT_IN_DOWNLINK) and it precedes event productManager.DownlinkComplete; check: event productManager.ProductDeleted count == 1 and it follows DownlinkComplete; check: the sysTester.DirListing event names no file; check: ABS.",
  rationale=[ONEERR])
t("L6-1", "Downlink of a missing product", "Proves a DOWNLINK naming no stored product is rejected and nothing is sent.", R(33), NOM,
  ["MARK(1040)", "CAPTURE()", "LIST_DIR(products)", "DOWNLINK(Dp_missing.fxd)", "wait 10 s", "LIST_DIR(products)", "MARK(1041)"], [W(1040, 1041)], knobs=["downlink_existing"],
  evidence="check: event productManager.ProductNotFound count == 1 (WARNING_LO, names Dp_missing.fxd); check: event productManager.DownlinkStarted count == 0; " + NOFILE + "; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.",
  rationale=[ONEERR])
t("L6-2", "Delete of a missing product", "Proves a DELETE naming no stored product is rejected and removes nothing.", R(33), NOM,
  ["MARK(1042)", "CAPTURE()", "LIST_DIR(products)", "DELETE(Dp_missing.fxd)", "LIST_DIR(products)", "MARK(1043)"], [W(1042, 1043)],
  evidence="check: event productManager.ProductNotFound count == 1 (names Dp_missing.fxd); check: event productManager.ProductDeleted count == 0; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.",
  rationale=[ONEERR])
t("L6-3", "Delete with a path as name", "Proves a DELETE whose name is a path to a stored product is rejected and removes nothing.", R(33), NOM,
  ["MARK(1044)", "CAPTURE()", "LIST_DIR(products)", "DELETE(./P)", "LIST_DIR(products)", "MARK(1045)"], [W(1044, 1045)],
  evidence="check: event productManager.ProductNotFound count == 1; check: event productManager.ProductDeleted count == 0; check: file names and count of the two sysTester.DirListing events are equal; check: ABS.",
  rationale=[ONEERR])
t("L7-1", "Final state", "Leaves one known product on board for the independent final-state check.", R(14), NOM,
  ["MARK(1050)", "CAPTURE()", "DUMP_SHA256(P, 1)", "LIST_DIR(products)", "MARK(1051)"], [W(1050, 1051)],
  evidence="check: event productManager.ProductWritten count == 1 (names P); the DirListing event names P only. After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt; the auditor compares it with the hash of the Sha256 event.")

ids = [x["id"] for x in T]; assert len(ids) == len(set(ids))
cov = collections.defaultdict(list)
for x in T:
    for r in x["covers"]: cov[r].append(x["id"])
SYS = {14: "REQ-PiSensor-011", 15: "REQ-PiSensor-005", 25: "REQ-PiSensor-030", 31: "REQ-PiSensor-033", 33: "REQ-PiSensor-032", 34: "REQ-PiSensor-014", 35: "REQ-PiSensor-041"}
req = {}
for i in range(1, 50):
    k = R(i)[0]
    if i in SYS:
        assert len(cov[k]) >= 2, (k, cov[k])
        req[k] = {"tests": cov[k], "verification": ", ".join(cov[k]) + ("" if i == 15 else "; unit test"), "note": "", "parent": SYS[i]}
    else:
        req[k] = {"tests": [], "verification": "UT only", "note": "observable at the component boundary; the unit-test list of docs/sdd.md covers it"}
STD = ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)", "event cmdDisp.OpCodeError count == 0",
       "event cmdDisp.TooManyCommands count == 0", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"]
plan = {
 "name": "ProductManager component system test plan",
 "markers": {"command": "sysTester.MARK", "event": "sysTester.Marker", "arg": "id", "reserved_min": 4294901760},
 "event_patterns": {"sysTester.Marker": "SystemTester marker (?P<id>\\d+)$"},
 "packets": {"Heartbeat": ["sysTester.UptimeS", "cmdDisp.CommandsDispatched"]},
 "std_complete": STD,
 "abs": {"ABS": ["event productManager.CaptureFailed count == 0", "event productManager.StorageFailed count == 0", "event productManager.DownlinkStalled count == 0",
                 "event productManager.FileSystemError count == 0", "event productManager.ProductDiscarded count == 0", "event sysTester.Started count == 0"],
         "STD-ERR": [("event cmdDisp.OpCodeError count == 1" if p == "event cmdDisp.OpCodeError count == 0" else p) for p in STD]},
 "helpers_module": "planted_faults.py",
 "helpers": [{"instance": "sysTester", "component": "SystemTester", "src": "SystemTester", "repo": "https://github.com/lestarch-autobot/fprime-pi-sensor-reference"}],
 "uut": "PiSensor::ProductManager (Components/ProductManager/docs/sdd.md), instance productManager",
 "deployment": "PiSensor full system deployment plus the harness component sysTester (the project's base deployment); images prototype (TCP) and flight (RFM69)",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 75},
              "not_covered_ack": ["File system error branches (FileSystemError) and the queue-overflow hooks cannot be forced on the bench without breaking test-as-you-fly: unit tests cover them.",
                                  "Time-out branches (PICTURE_TIMEOUT, WRITTEN_TIMEOUT), the camera-failure and storage-failure branches: covered by unit tests here and by the project plan's L5 tests.",
                                  "The start-up scan removing a partial product: covered by a unit test and by the project plan's L3-3 and L3-4."],
              "rationale": "Baselines of the skill, applied to Components/ProductManager only. The on-target figure counts this plan's run together with nothing else; the coverage-dump component is in the development-campaign image only."},
 "image_version": {"policy": "required"},
 "final_state": {"accepted_evidence": "bench sha256sum of the L7-1 product file, taken over ssh after the run into record/raw/final-state.txt, compared by the auditor with the hash of the sysTester.Sha256 event",
                 "rationale": "The on-board hash command runs inside the UUT process; the bench reads the file itself, outside the UUT's reporting path."},
 "requirements": req,
 "scope": ["L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, ids 1000 to 1051 (the project plan uses 10 to 231). Event rate: at most 5 events per second in any window; `LIST_PRODUCTS` emits at most 4 `ProductStored` events per second by design.",
           "- UUT: component `PiSensor::ProductManager`, instance `productManager`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.",
           "- Test deployment: the project's base deployment plus `sysTester` (SSDD decision D13), the configuration of the project plan `SystemTester/test/int/plan.json`; its scope lines on the ground system, record content, completeness and clocks apply unchanged.",
           "- This plan holds the component rows the project plan delegates (`delegated: prodmgr`): REQ-PiSensor-011, -014, -030, -032, -033, -041, and the one requirement of the component verified by integration test (REQ-ProductManager-015). Every other requirement is verified by the unit-test list of the SDD.",
           "- `sysTester` commands used: `MARK(id)`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `CORRUPT_PRODUCT(name)` (planted fault only). `CORRUPT_PRODUCT` overwrites the first two bytes of the picture record and leaves the header, so the file stays a stored product (ledger note N1).",
           "- Order: the prototype block (L0-1 to L2-4, L5-1, L5-2, L6-1 to L6-3, L7-1 last, TCP), then the flight block (L5-3 to L5-6, RFM69). L7-1 runs after the flight block on the prototype image when both blocks run in one record.",
           "- Downlink-in-progress tests run on the flight image: over RFM69 a product takes at least 60 s (project plan link budget), over TCP about a second, too short to send a second command inside the transfer. Each requires a transfer of at least 10 s, else UNVERIFIED.",
           "- Capture-in-progress tests rely on the capture taking longer than one command round trip (SSDD: a capture may take seconds); each requires the second command dispatched before `ProductWritten`, else UNVERIFIED. L0 bench confirmation measures the capture duration.",
           "- Out of scope: product content, timing of metrics, camera, storage, link and restart faults (project plan L2, L3, L5)."],
 "entry_gates": ["- Unit tests of `ProductManager` pass with line coverage at or above the plan's threshold.",
                 "- Images built from the base deployment `repo@sha` sent with the DEVELOPMENT stretch plus the component; L0-1 passes on the bench.",
                 "- Product directory on its own 64 MB file system, empty at the start of each test (bench teardown removes the products of the test; L7-1 has no teardown).",
                 "- Bench recipe: Pi Camera attached; ground Pi with RFM69 for the flight block. Sensors need not answer: metrics are marked invalid and the capture still succeeds."],
 "levels": ["L0 provenance and feasibility · L2 functional · L5 fault paths · L6 negative controls · L7 final state. No L3 test: restart behaviour of products is in the project plan (L3-1 to L3-4). No L4 endurance test: no requirement has an endurance bound."],
 "not_covered": ["- Every requirement marked `UT only`: verified by the unit-test list, and at system level by the project plan where it traces a system requirement.",
                 "- REQ-ProductManager-046 (name in use): the clock cannot be made to repeat a capture time on the bench without stepping the system clock of a shared machine; unit test only.",
                 "- A listing during a listing, a delete during a listing and queue overflow: timing not reachable through the ground link at 5 events per second; unit tests.",
                 "- Today's bench cannot run these tests: the camera and the ground Pi are absent."],
 "decision_log": ["1. 2026-11-17 designer — the component tests run in the project's base deployment with `sysTester`; no component-only deployment.",
                  "2. 2026-11-17 designer — downlink-in-progress tests run on the flight image, where a transfer lasts long enough to command inside it.",
                  "3. 2026-11-17 designer — planted faults rewrite or insert commands only; one is `uut-state` (`corrupt_first_product`)."],
 "tests": T,
}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
print(len(T), "tests")
