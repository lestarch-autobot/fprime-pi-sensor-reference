#!/usr/bin/env python3
"""Generates plan.json for the ProductManager component system tests (design phase). Run from this directory."""
import json, collections
R = lambda *n: [f"REQ-ProductManager-{i:03d}" for i in n]
def W(a, b, name="W"): return {"name": name, "start_id": a, "end_id": b, "reset": False}
def H(name, text, **args): return {"helper": name, "text": text, "args": args}
T = []
# A check or precondition is either a predicate of the plan grammar (a string) or a registered helper
# (H(...)); its text is the name the stimulus test declares (`check(name)` / `require(name)`) and the name
# a planted fault's `fails` list repeats verbatim.
def name(c): return c if isinstance(c, str) else c["text"]
ALLC = collections.OrderedDict()   # test id -> {"require": [...], "check": [...]}
def t(id, title, purpose, covers, setup, procedure, windows, checks=(), requires=(), knobs=(), rationale=(), note=""):
    ALLC[id] = {"require": list(requires), "check": list(checks)}
    ev = ("require (else UNVERIFIED): STD; " + "; ".join(name(c) for c in requires) + ". " if requires else "require (else UNVERIFIED): STD. ")
    ev += "check: " + "; ".join(name(c) for c in checks) + "." + (" " + note if note else "")
    T.append({"id": id, "title": title, "purpose": purpose, "covers": covers, "setup": setup,
              "procedure": list(procedure), "windows": windows, "metrics": [],
              "rationale": [{"pred": p, "text": x} for p, x in rationale], "knobs": list(knobs), "evidence": ev})
NOM = "Prototype image running, link up, camera answering."
FLT = "Flight image running, ground Pi with RFM69 and groundRadio up, camera answering."
PM = "productManager."
ABS = ["event productManager.CaptureFailed count == 0", "event productManager.StorageFailed count == 0", "event productManager.DownlinkStalled count == 0",
       "event productManager.FileSystemError count == 0", "event productManager.ProductDiscarded count == 0", "event sysTester.Started count == 0"]
NOERR = "event cmdDisp.OpCodeError count == 0"
def one_err(cmd): return H("only_failed_command", f"exactly one command fails (cmdDisp.OpCodeError) and it is the rejected {cmd}; every other command completes", command=cmd)
def listing(k, names, text): return H("dir_listing_equals", f"sysTester.DirListing event {k} names {text}", index=k, names=names)
def sev(ev, s): return H("event_severity", f"every {PM}{ev} event has severity {s}", event=PM + ev, severity=s)
def named(ev, n, names, text): return H("event_names", f"event {PM}{ev} count == {n}, naming {text}", event=PM + ev, count=n, names=names)
def sha_eq(p): return H("sha_events_equal", f"the two sysTester.Sha256 events of {p} carry the same hash", product=p)
def ground_eq(p): return H("ground_file_hash_equals", f"sha256 of record/raw/files/<{p}> == hash in the first sysTester.Sha256 event of {p}", product=p)
def cfdp(n, text): return H("ground_cfdp_transactions", f"ground CFDP transactions in the window: {text}", count=n)
EMPTY = listing(1, [], "no file")
MARGIN = H("dispatched_before_event_by", "the command sent after the first CAPTURE is dispatched at least 1 s (one run tick) before event productManager.ProductWritten", after_command=PM + "CAPTURE", event=PM + "ProductWritten", margin_s=1)
INSIDE = H("dispatched_inside_transfer", "the command sent after the first DOWNLINK is dispatched after event productManager.DownlinkStarted and at least 2 s before the ground end time of that CFDP transaction", margin_s=2)
GROUND = H("ground_cfdp_service_up", "the ground CFDP service is up for the whole window (record/raw/cfdp.json covers it)")
REJ = lambda r: f"event productManager.CommandRejected(reason={r}) count == 1"
WAITW = "wait event productManager.ProductWritten (at most 30 s, REQ-PiSensor-010; on time-out continue to END)"
WAITS = "wait event productManager.DownlinkStarted (at most 10 s; on time-out continue to END)"
WAITC = "wait CFDP transaction finished at the ground (at most 600 s; on time-out continue to END)"
WAITD = "wait event productManager.DownlinkComplete (at most 30 s; on time-out continue to END)"
TEAR = "action: teardown, remove the product files of this test over ssh"
LD = "LIST_DIR(products)"
def ident(id, title, image, setup, a, b):
    t(id, title, f"Proves the running image is the manifest's {image} image and the marker round-trips.", [], setup,
      [f"MARK({a})", "VERSION(ALL)", "bracket (2 Heartbeat samples)", "MARK(0xA5A5)", f"MARK({b})"], [W(a, b)],
      checks=[H("version_matches_manifest", f"Svc.Version events equal the describe strings of the manifest's {image} image", image=image),
              "event sysTester.Marker(id=42405) count == 1", NOERR])
ident("L0-1", "Image identity and marker round-trip, prototype image", "prototype", "Prototype image running on the Raspberry Pi 5; link up over TCP.", 1000, 1001)
ident("L0-2", "Image identity and marker round-trip, flight image", "flight", "Flight image running; ground Pi with RFM69 and groundRadio up.", 1002, 1003)
t("L2-1", "Capture names its product", "Proves a successful capture emits ProductWritten naming the one new product file.", R(14), NOM,
  ["MARK(1010)", LD, "CAPTURE()", LD, TEAR, "MARK(1011)"], [W(1010, 1011)], knobs=["capture_twice"],
  checks=[EMPTY, named("ProductWritten", 1, ["P"], "P"), sev("ProductWritten", "ACTIVITY_HI"), listing(2, ["P"], "P and no other file"), NOERR] + ABS)
t("L2-2", "Second capture leaves the first product unchanged", "Proves a second capture names a new product and leaves the first unchanged.", R(14, 15), NOM,
  ["MARK(1012)", LD, "CAPTURE()", "DUMP_SHA256(P1, 1)", "CAPTURE()", "DUMP_SHA256(P1, 2)", LD, TEAR, "MARK(1013)"], [W(1012, 1013)], knobs=["corrupt_first_product"],
  checks=[EMPTY, named("ProductWritten", 2, ["P1", "P2"], "P1 and P2, different"), sev("ProductWritten", "ACTIVITY_HI"), sha_eq("P1"), listing(2, ["P1", "P2"], "P1 and P2 only"), NOERR] + ABS)
t("L2-3", "A third capture leaves both stored products unchanged", "Proves a capture leaves every stored product unchanged, and DELETE then removes one.", R(15, 34), NOM,
  ["MARK(1014)", LD, "CAPTURE()", "CAPTURE()", "DUMP_SHA256(P1, 1)", "DUMP_SHA256(P2, 1)", "CAPTURE()", "DUMP_SHA256(P1, 2)", "DUMP_SHA256(P2, 2)", "DELETE(P2)", LD, TEAR, "MARK(1015)"], [W(1014, 1015)],
  checks=[EMPTY, named("ProductWritten", 3, ["P1", "P2", "P3"], "P1, P2 and P3, all different"), sha_eq("P1"), sha_eq("P2"),
          named("ProductDeleted", 1, ["P2"], "P2"), listing(2, ["P1", "P3"], "P1 and P3 only"), NOERR] + ABS)
t("L2-4", "Delete removes the named product", "Proves DELETE removes the named product and no other, before its command response.", R(34), NOM,
  ["MARK(1016)", LD, "CAPTURE()", "CAPTURE()", "DUMP_SHA256(P2, 1)", "DELETE(P1)", LD, "DUMP_SHA256(P2, 2)", "LIST_PRODUCTS()", TEAR, "MARK(1017)"], [W(1016, 1017)], knobs=["delete_other"],
  checks=[EMPTY, named("ProductDeleted", 1, ["P1"], "P1"), listing(2, ["P2"], "P2 only"), sha_eq("P2"), named("ProductStored", 1, ["P2"], "P2"),
          "event productManager.ProductsListed(count=1) count == 1", NOERR] + ABS)
t("L5-1", "Capture during a capture", "Proves a CAPTURE during a capture is rejected and the first capture stores its product.", R(25), NOM,
  ["MARK(1020)", LD, "CAPTURE() without waiting for completion", "CAPTURE()", WAITW, LD, TEAR, "MARK(1021)"], [W(1020, 1021)], knobs=["second_capture_dropped"],
  requires=[MARGIN],
  checks=[EMPTY, REJ("CAPTURE_IN_PROGRESS"), sev("CommandRejected", "WARNING_LO"), one_err("CAPTURE"), named("ProductWritten", 1, ["P"], "P"), listing(2, ["P"], "P and no other file")] + ABS)
t("L5-2", "Capture after a rejected capture", "Proves a rejected CAPTURE does not disturb the capture in progress or the next one.", R(25), NOM,
  ["MARK(1022)", LD, "CAPTURE() without waiting for completion", "CAPTURE()", WAITW, "CAPTURE()", LD, TEAR, "MARK(1023)"], [W(1022, 1023)],
  requires=[MARGIN],
  checks=[EMPTY, REJ("CAPTURE_IN_PROGRESS"), sev("CommandRejected", "WARNING_LO"), one_err("CAPTURE"), named("ProductWritten", 2, ["P1", "P2"], "P1 and P2, different"), listing(2, ["P1", "P2"], "P1 and P2 only")] + ABS)
DL = [GROUND, INSIDE]
t("L5-3", "Downlink during a downlink", "Proves a DOWNLINK during a downlink is rejected and the first transfer delivers its product.", R(31), FLT,
  ["MARK(1030)", LD, "CAPTURE()", "CAPTURE()", "DUMP_SHA256(P1, 1)", "DOWNLINK(P1) without waiting for completion", WAITS, "DOWNLINK(P2)", WAITC, WAITD, TEAR, "MARK(1031)"], [W(1030, 1031)],
  requires=DL,
  checks=[EMPTY, REJ("DOWNLINK_IN_PROGRESS"), sev("CommandRejected", "WARNING_LO"), one_err("DOWNLINK"), named("DownlinkStarted", 1, ["P1"], "P1"), named("DownlinkComplete", 1, ["P1"], "P1"),
          cfdp(1, "exactly one, of file P1, finished complete"), ground_eq("P1")] + ABS)
t("L5-4", "Repeated downlink of the product in transfer", "Proves a DOWNLINK naming the product in transfer is rejected without a second transfer.", R(31), FLT,
  ["MARK(1032)", LD, "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P) without waiting for completion", WAITS, "DOWNLINK(P)", WAITC, WAITD, TEAR, "MARK(1033)"], [W(1032, 1033)],
  requires=DL,
  checks=[EMPTY, REJ("DOWNLINK_IN_PROGRESS"), sev("CommandRejected", "WARNING_LO"), one_err("DOWNLINK"), named("DownlinkStarted", 1, ["P"], "P"), named("DownlinkComplete", 1, ["P"], "P"),
          cfdp(1, "exactly one, of file P, finished complete"), ground_eq("P")] + ABS)
t("L5-5", "Delete during the product's downlink", "Proves a DELETE of the product in transfer is rejected; the product is delivered, kept.", R(35), FLT,
  ["MARK(1034)", LD, "CAPTURE()", "DUMP_SHA256(P, 1)", "DOWNLINK(P) without waiting for completion", WAITS, "DELETE(P)", WAITC, WAITD, "DUMP_SHA256(P, 2)", LD, TEAR, "MARK(1035)"], [W(1034, 1035)], knobs=["corrupt_in_transfer"],
  requires=DL,
  checks=[EMPTY, REJ("PRODUCT_IN_DOWNLINK"), sev("CommandRejected", "WARNING_LO"), one_err("DELETE"), "event productManager.ProductDeleted count == 0",
          named("DownlinkStarted", 1, ["P"], "P"), named("DownlinkComplete", 1, ["P"], "P"), ground_eq("P"), sha_eq("P"), listing(2, ["P"], "P and no other file")] + ABS)
t("L5-6", "Delete after the product's downlink", "Proves a DELETE rejected during the downlink succeeds once the transfer has ended.", R(35, 34), FLT,
  ["MARK(1036)", LD, "CAPTURE()", "DOWNLINK(P) without waiting for completion", WAITS, "DELETE(P)", WAITC, WAITD, "DELETE(P)", LD, TEAR, "MARK(1037)"], [W(1036, 1037)],
  requires=DL,
  checks=[EMPTY, REJ("PRODUCT_IN_DOWNLINK"), sev("CommandRejected", "WARNING_LO"), one_err("DELETE"), named("DownlinkStarted", 1, ["P"], "P"), named("DownlinkComplete", 1, ["P"], "P"),
          "event productManager.CommandRejected precedes event productManager.DownlinkComplete", "event productManager.DownlinkComplete precedes event productManager.ProductDeleted",
          named("ProductDeleted", 1, ["P"], "P"), listing(2, [], "no file")] + ABS)
NF = lambda n: f"event productManager.ProductNotFound(name={n}) count == 1"
SAME = H("dir_listings_equal", "sysTester.DirListing events 2 and 3 carry the same file names and count", a=2, b=3)
t("L6-1", "Downlink of a missing product", "Proves a DOWNLINK naming no stored product is rejected and nothing is sent.", R(33), NOM,
  ["MARK(1040)", LD, "CAPTURE()", "DUMP_SHA256(P, 1)", LD, "DOWNLINK(Dp_missing.fxd)", "wait 10 s (twice the time in which DownlinkStarted or a ground transaction follows an accepted DOWNLINK over TCP)", "DUMP_SHA256(P, 2)", LD, TEAR, "MARK(1041)"], [W(1040, 1041)], knobs=["downlink_existing"],
  requires=[GROUND],
  checks=[EMPTY, NF("Dp_missing.fxd"), sev("ProductNotFound", "WARNING_LO"), one_err("DOWNLINK"), "event productManager.DownlinkStarted count == 0", cfdp(0, "none"), sha_eq("P"), SAME] + ABS)
t("L6-2", "Delete of a missing product", "Proves a DELETE naming no stored product is rejected and removes nothing.", R(33), NOM,
  ["MARK(1042)", LD, "CAPTURE()", LD, "DELETE(Dp_missing.fxd)", LD, TEAR, "MARK(1043)"], [W(1042, 1043)],
  checks=[EMPTY, NF("Dp_missing.fxd"), sev("ProductNotFound", "WARNING_LO"), one_err("DELETE"), "event productManager.ProductDeleted count == 0", SAME] + ABS)
t("L6-3", "Delete with a path as name", "Proves a DELETE naming a path to a stored product is rejected, removing nothing.", R(33), NOM,
  ["MARK(1044)", LD, "CAPTURE()", LD, "DELETE(./P)", LD, TEAR, "MARK(1045)"], [W(1044, 1045)],
  checks=[EMPTY, named("ProductNotFound", 1, ["./P"], "./P"), sev("ProductNotFound", "WARNING_LO"), one_err("DELETE"), "event productManager.ProductDeleted count == 0", SAME] + ABS)
t("L6-4", "Downlink with a path as name", "Proves a DOWNLINK naming a path to a stored product is rejected, sending nothing.", R(33), NOM,
  ["MARK(1046)", LD, "CAPTURE()", LD, "DOWNLINK(./P)", "wait 10 s (as L6-1)", LD, TEAR, "MARK(1047)"], [W(1046, 1047)],
  requires=[GROUND],
  checks=[EMPTY, named("ProductNotFound", 1, ["./P"], "./P"), sev("ProductNotFound", "WARNING_LO"), one_err("DOWNLINK"), "event productManager.DownlinkStarted count == 0", cfdp(0, "none"), SAME] + ABS)
t("L7-1", "Final state", "Leaves one known product on board for the independent final-state check.", R(14), NOM,
  ["MARK(1050)", LD, "CAPTURE()", "DUMP_SHA256(P, 1)", LD, "MARK(1051)"], [W(1050, 1051)],
  checks=[EMPTY, named("ProductWritten", 1, ["P"], "P"), sev("ProductWritten", "ACTIVITY_HI"), listing(2, ["P"], "P and no other file"), NOERR] + ABS,
  note="After the run the bench runs sha256sum on the product file over ssh into record/raw/final-state.txt; the auditor compares it with the hash of the Sha256 event.")

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
STD = ["both markers present", "commands_sent == count(event cmdDisp.OpCodeDispatched)",
       "event cmdDisp.TooManyCommands count == 0", "event comQueue.QueueOverflow count == 0", "Heartbeat samples >= 2"]
plan = {
 "name": "ProductManager component system test plan",
 "markers": {"command": "sysTester.MARK", "event": "sysTester.Marker", "arg": "id", "reserved_min": 4294901760},
 "event_patterns": {"sysTester.Marker": "^Marker (?P<id>\\d+)$",
                    "productManager.ProductWritten": "^Product (?P<name>\\S+) written, (?P<size>\\d+) bytes$",
                    "productManager.CommandRejected": "^Command rejected: (?P<reason>\\w+)$",
                    "productManager.ProductNotFound": "^No stored product (?P<name>\\S+)$",
                    "productManager.ProductDeleted": "^Product (?P<name>\\S+) deleted$",
                    "productManager.DownlinkStarted": "^Downlink of (?P<name>\\S+) started$",
                    "productManager.DownlinkComplete": "^Downlink of (?P<name>\\S+) complete$",
                    "productManager.ProductStored": "^Product (?P<name>\\S+), (?P<size>\\d+) bytes$",
                    "productManager.ProductsListed": "^(?P<count>\\d+) products stored$"},
 "packets": {"Heartbeat": ["sysTester.UptimeS", "cmdDisp.CommandsDispatched"]},
 "std_complete": STD,
 "abs": {"ABS": ABS},
 "helpers_module": "planted_faults.py",
 "helpers": [{"instance": "sysTester", "component": "SystemTester", "src": "SystemTester", "repo": "https://github.com/lestarch-autobot/fprime-pi-sensor-reference"}],
 "uut": "PiSensor::ProductManager (Components/ProductManager/docs/sdd.md), instance productManager",
 "deployment": "PiSensor full system deployment plus the harness component sysTester (the project's base deployment); images prototype (TCP) and flight (RFM69)",
 "coverage": {"ut": {"lines_min": 95}, "system": {"lines_min": 55},
              "not_covered_ack": ["File system error branches (FileSystemError) and the queue-overflow hooks cannot be forced on the bench without breaking test-as-you-fly: unit tests cover them.",
                                  "Time-out branches (PICTURE_TIMEOUT, WRITTEN_TIMEOUT), the camera-failure and storage-failure branches: covered by unit tests here and by the project plan's L5 tests.",
                                  "The start-up scan removing a partial product: covered by a unit test and by the project plan's L3-3 and L3-4."],
              "rationale": "UT: baseline of the skill, applied to Components/ProductManager only. System: 55, below the 75 baseline, because this plan's run alone reaches the nominal capture, downlink, delete and listing paths and the four rejections, but none of the time-out, camera-failure, storage-failure, file-system-error, discard, stalled or refused-downlink, overflow-hook and partial-product branches, which by the SDD's handler list are about 40 % of the component (estimate from SDD 3.5 and the event table: 9 of 16 events are not reachable here). The project plan's L3 and L5 tests reach most of them; their run is reported beside this figure, not counted in it. The coverage-dump component is in the development-campaign image only."},
 "image_version": {"policy": "required"},
 "final_state": {"accepted_evidence": "bench sha256sum of the L7-1 product file, taken over ssh after the run into record/raw/final-state.txt, compared by the auditor with the hash of the sysTester.Sha256 event",
                 "rationale": "The on-board hash command runs inside the UUT process; the bench reads the file itself, outside the UUT's reporting path."},
 "requirements": req,
 "scope": ["L0: desk-checked; bench confirmation pending. Marker `sysTester.MARK(U32)` -> event `sysTester.Marker(id)`, ids 1000 to 1051 (the project plan uses 10 to 231). Event rate: at most 5 events per second in any window; `LIST_PRODUCTS` emits at most 4 `ProductStored` events per second by design.",
           "- UUT: component `PiSensor::ProductManager`, instance `productManager`, in the PiSensor deployment on the Raspberry Pi 5 `soakee`, 64-bit Raspberry Pi OS 13.",
           "- Test deployment: the project's base deployment plus `sysTester` (SSDD decision D13), the configuration of the project plan `SystemTester/test/int/plan.json`; its scope lines on the ground system, record content, completeness and clocks apply unchanged.",
           "- This plan holds the component rows the project plan delegates (`delegated: prodmgr`): REQ-PiSensor-011, -014, -030, -032, -033, -041, and the one requirement of the component verified by integration test (REQ-ProductManager-015). Every other requirement is verified by the unit-test list of the SDD.",
           "- `sysTester` commands used: `MARK(id)`, `LIST_DIR(dir)`, `DUMP_SHA256(name, pass)`, `CORRUPT_PRODUCT(name)` (planted fault only). `CORRUPT_PRODUCT` overwrites the first two bytes of the picture record and leaves the header, so the file stays a stored product (ledger note N1). Dependency on the project's harness lane: `LIST_DIR`, `DUMP_SHA256`, `CORRUPT_PRODUCT` and the events `DirListing` and `Sha256` are not in `sysTester` at `deploy/base`@383a9ce; their formats are fixed there, and the helpers `dir_listing_equals`, `dir_listings_equal`, `sha_events_equal`, `ground_file_hash_equals` and the event patterns for the two events are written against them at the stage-2 refresh. `DUMP_SHA256` of a missing file must fail its command and emit no `Sha256` event.",
           "- Pass rules: every check and precondition of a test is listed by name in its evidence line; a name is a predicate of the plan grammar or the text of a registered helper (`planted_faults.py`), and is the name the stimulus test declares. Event arguments are read with `event_patterns`, taken from the formats of `ProductManager.fpp`. STD holds no UUT fact: a failed command is judged by the check `event cmdDisp.OpCodeError count == 0` (nominal tests) or by the helper `only_failed_command` (rejection tests), never by a precondition.",
           "- Flight block budget [I]: project plan link budget, RFM69 at 19200 bit/s carries 2400 byte/s; events of this plan during a transfer are at most 3 in 10 s (under 100 byte/s) beside 1 Hz telemetry, so markers and rejection events fit while CFDP uses the rest. L0-2 confirms the marker round-trip on the flight image; the bench check replaces the estimate.",
           "- Teardown is a bench action inside the window (`action: teardown`, files removed over ssh, logged in bench-actions.log); every test starts with `LIST_DIR(products)` and the check that it names no file.",
           "- Order: the flight block (L0-2, L5-3 to L5-6, RFM69), then the prototype block (L0-1, L2-1 to L2-4, L5-1, L5-2, L6-1 to L6-4, TCP), L7-1 last.",
           "- Downlink-in-progress tests run on the flight image: over RFM69 a product takes at least 60 s (project plan link budget), over TCP about a second, too short to send a second command inside the transfer. Each requires the second command dispatched inside the transfer by the ground transfer record, else UNVERIFIED.",
           "- Capture-in-progress tests rely on the capture taking longer than one command round trip (SSDD: a capture may take seconds); each requires the second command dispatched at least 1 s (one `run` tick, SDD 3.4) before `ProductWritten`, else UNVERIFIED. L0 bench confirmation measures the capture duration.",
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
                  "3. 2026-11-17 designer — planted faults rewrite or insert commands only; two are `uut-state` (`corrupt_first_product`, `corrupt_in_transfer`).",
                  "4. 2026-11-17 designer, review round 1 — checks are named predicates and helpers listed per test; `OpCodeError` left the completeness block; flight-image identity test L0-2 and fault-free L6-4 added; system coverage threshold set to 55 with its reason."],
 "tests": T,
}
json.dump(plan, open("plan.json", "w"), indent=1, ensure_ascii=False)
json.dump(ALLC, open("checks.json", "w"), indent=1, ensure_ascii=False)
# parse check: the same plan with every check and precondition as a metric, for `fth verify-plan`
import copy
pc = copy.deepcopy(plan)
for x in pc["tests"]: x["metrics"] = ALLC[x["id"]]["require"] + ALLC[x["id"]]["check"]
if "--parse-check" in __import__("sys").argv: json.dump(pc, open(".plan-parse-check.json", "w"), indent=1, ensure_ascii=False)
print(len(T), "tests")
