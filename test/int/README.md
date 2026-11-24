# PiSensor system test harness

The harness of the 11 tests of `stimulus/plan.json` (approved with Gate 1). It runs on the bench workstation with
[fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness) (`fth`) v0.1.2; the ground
system is fprime-yamcs. Since 2026-11-23 the link is TCP (`bench/tcp_bridge.py`); before that it was the RFM69
with the Feather M0 ground radio (section "TCP link" below). Nothing here is part of the flight
deployment and there is no test component.

| Path | What it is |
|---|---|
| `stimulus/plan.json`, `stimulus/plan.md`, `stimulus/faults-menu.json`, `gen_plan.py` | the plan, revision 4 (changelogs below) |
| `stimulus/planted_faults.py` | the plan's helper predicates (its metrics) and planted faults |
| `stimulus/test_pisensor.py` | the stimulus and the named checks, one function per plan test; the `--tests` directory |
| `stimulus/pisensor_record.py` | record access for the checks: ground reception time, transfers, frames, product decoder |
| `bench.json` | the bench: command lines of the ground side, the sender, the recorder, the UUT actions |
| `bench/yamcs_bench.py` | of the `piCamera` component tests: image on the Pi, fprime-yamcs and the bench bridge, command sending with resend |
| `bench/tcp_bridge.py` | bench bridge: TCP server for the deployment, TM and TC frames to and from the fprime-yamcs UDP links, frame log |
| `bench/yamcs_recorder.py` | records events, telemetry, transfers, frames and received files from YAMCS |
| `bench/uut.py` | the bench actions on the Pi over ssh |
| `bench/verify_stimulus.py` | stimulus against the plan procedures, from a dry run |
| `kat/` | known-answer tests of all of the above over a synthetic record (`run_kat.py`, `sim.py`) |

## Offline checks (no bench)

```
fth verify-plan test/int/stimulus/plan.json --tests test/int/stimulus --bench test/int/bench.json
python -B test/int/bench/verify_stimulus.py test/int/stimulus/plan.json --tests test/int/stimulus --bench test/int/bench.json
python -B test/int/kat/run_kat.py        # needs Pillow
```

`--tests` is `test/int/stimulus`, not `test/int`: fth lints every Python file under the tests directory
and refuses `gen_plan.py` there. Run Python with `-B`: a `__pycache__` under the stimulus changes its pin.

## The record

`record/raw` of a run, beside what fth writes itself:

| File | Content | Written by |
|---|---|---|
| `fprime-cli-yamcs/event.log`, `channel.log` | every event and telemetry sample in fth's line format: FSW time, and the ground reception time as `rx=<UTC epoch s>` | recorder |
| `cmd/fprime-cli-yamcs-*/command.log` | every command: bench UTC time sent, YAMCS command id, name, opcode, arguments | sender |
| `yamcs/events.jsonl`, `channels.jsonl`, `timetags.jsonl`, `links.jsonl`, `events-archive.json`, `commands.json` | the YAMCS data as received, the F Prime time tag of each event packet, link counters, YAMCS's own archive at stop | recorder |
| `cfdp.json` | YAMCS transfer records (class, state, sizes, start time) with the ground time each was first seen and seen finished | recorder |
| `frames.json` | every TM frame handed to YAMCS (time, virtual channel, frame counts) from `bridge.log`, and the YAMCS TM link counters | recorder |
| `files/<transfer id>-<name>` | each file received by CFDP, copied from the YAMCS bucket, sha256 in `cfdp.json` | recorder |
| `bench-actions.log`, `actions/<n>-<name>.json` | each bench action: command line, start, end, exit status, output | fth, `uut.py` |
| `final-state.txt` | `sha256sum` of the product files left on the Pi after L7-1 (the plan's final-state evidence) | `uut.py` |
| `dictionary.json`, `bridge.log`, `yamcs.out`, `yamcs-data/` | the dictionary of the run, the bridge and YAMCS logs and archive | recorder, `ground.py` |

FSW time of a row is the YAMCS generation time minus `gen_offset` (bench.json, 1.0 s): fprime-yamcs stamps
a packet with its F Prime time tag plus 38 s and YAMCS renders that with 37 leap seconds. `timetags.jsonl`
holds the raw tag beside the YAMCS time so the offset is checked on the record, not assumed.

## What fth 0.1.2 lacks here

Each is worked around in this directory; fth is not modified.

1. No `verify-stimulus` command: `bench/verify_stimulus.py`.
2. The sender, the recorder and the export read fprime-gds / fprime-cli logs; there is no YAMCS path:
   `bench/yamcs_send.py`, `bench/yamcs_recorder.py` write those log formats from YAMCS.
3. Rows carry no ground reception time, and the record has no notion of file transfers, frames or received
   files: the `rx=` field and `stimulus/pisensor_record.py`.
4. A plan metric given as a helper is not evaluated by the test plugin (it parses the metric text with the
   predicate grammar and fails): `metrics()` in the stimulus declares each by its plan text.
5. A plan metric has no window: fth files it under the first window. `metrics()` takes the window the text
   names (`... in D`).
6. A window is cut at the START marker event. The marker here is `cmdDisp.CMD_NO_OP_STRING`, an
   asynchronous command of the dispatcher itself, so its `OpCodeDispatched` precedes the marker event and
   falls outside the cut; `commands_sent == count(event cmdDisp.OpCodeDispatched)` is then one short, or
   equal only because the next window's START was counted. `every_command_dispatched()` counts the right one.
7. The grammar has no `severity FATAL count == 0` and no prose completeness items: declared with functions.
8. `Bench.action` records the command line and a 1 s time stamp, not the output or the end time:
   `uut.py` writes `actions/*.json`.
9. The blind lint applies to every Python file under `--tests`, to words inside strings too: the stimulus
   has its own directory and no check name holds a linted word.
10. Flash, read-back and serial number assume a debug probe: `uut.py` installs over ssh and prints the Pi
    serial as `Serial# = ...`. There is no hook to stop the flight software after a run (`uut.py stop`).
11. No hook after the run for the final-state evidence: taken at the end of L7-1, after its window closed.

## Plan revision 2 (2026-11-19, harness builder; not yet reviewed)

Revision 1 is the plan approved with Gate 1 (`c7953c9`). Pass rules stay as strict as the requirements.

1. Telemetry period metric: one per channel (`bmpManager.Reading`, `imuManager.Reading`, `gpsManager.Reading`)
   instead of one for all three, in L2-1, L2-2, L2-7 and L2-8; same bound and sample count. A silent sensor
   fails its own metric only. Samples are selected by ground reception time between the two markers.
2. Heartbeat is `bmpManager.Reading`, not `imuManager.Reading` (Captain's MPU6050 ruling: no window gate on it).
3. STD no longer holds `commands_sent == count(event cmdDisp.OpCodeDispatched)`. Every window requires instead:
   commands sent, marker commands apart, equal the dispatch events of other opcodes. The dispatch event of a
   marker can sort outside the window. With r resends logged by the bench in the window (`cmd/resend.log`,
   at most two per command, sent when no dispatch is reported within 6 s) the count may be up to r higher.
4. L0-1 procedure: the clock action is a step (its metric needed it).
5. L0-1 check wording: "character devices held by the process are a subset of the list in Scope".
6. L2-1, L2-2: the MPU6050 bounds are stated in the units of the channel, 0.82 to 1.22 g and 28.6 deg/s
   (the same 8 to 12 m/s^2 and 0.5 rad/s). The plausibility check is two checks: BMP280 and GPS; MPU6050.
7. Products: new check "roll and pitch of each ground file are marked valid" (L2-3, L2-4, L2-5, L7-1). The
   sample time bound applies to metrics marked valid (REQ-PiSensor-014 as amended). The L2-5 comparison with
   telemetry is two checks: temperature, latitude and longitude; roll and pitch.
8. Every window ends with a wait until the telemetry sampled up to that moment has reached the ground
   (telemetry age, below); no bound changes.
9. Scope, not-covered and decision log entries for the above. Not changed: tests, windows, commands, bounds,
   planted faults. The metrics of L2-7 and L2-8 still name window D in their text (fth gap 5).

## Plan revision 3 (2026-11-20, harness builder; Mode B review closed at one round)

Follows REQ-PiSensor-005 as amended by the human ruling of 2026-11-20 (`docs/ledger.md`): a capture stores its
product whether or not a sensor answers, with that sensor's metrics as placeholders marked not valid. Interface
read from `comp/picam@89357e5` (`Components/PiCamera/PiCamera.fpp`): `locationValid` and `temperatureValid`
beside `attitudeValid`; events `piCamera.TemperatureUnavailable`, `AttitudeUnavailable`, `LocationUnavailable`.
No bound of a requirement changed. The plan has 12 tests.

1. Product validity, in L2-3, L2-4, L2-5 and L7-1.
   Old: `roll and pitch of each ground file are marked valid`.
   New: `each metric of each ground file is a finite value marked valid, or a placeholder marked not valid whose
   sensor was silent`. For temperature, latitude and longitude, roll and pitch: marked valid (flag byte
   0xFF), the values are finite and the record holds a telemetry sample of that sensor within 1 s (0.1 s until the first live products, see below) of the stated
   sample time; marked not valid (flag byte 0x00), the values are NaN, the sample time is zero, and the record holds no telemetry
   sample of that sensor (`bmpManager.Reading`, `gpsManager.Reading`, `imuManager.Reading`) with a unit time in
   the 2 s up to the capture time record; in the window, the events of that sensor are as many as the ground
   files with that metric not valid. The samples are taken from the whole record, not only the window.
2. Sample times (REQ-PiSensor-014), in L2-3, L2-4 and L2-5. Text unchanged: `... |sample time - capture time
   record| <= 2 s for each metric marked valid`. The helper now leaves out every metric marked not valid; before,
   only roll and pitch could be left out.
3. Agreement with the telemetry, in L2-5. Text of the two checks unchanged (`temperature, latitude and longitude
   of the product ...`, `roll and pitch of the product ...`). A metric marked not valid is not compared; check 1
   judges it. Before, every metric was compared.
4. New in every window of every test: `each piCamera event that reports a sensor unavailable has no telemetry
   sample of that sensor in the 2 s before its capture`. The capture time is the time in the name of the product
   written next in the window; the event time where none follows. The plan had no precondition on warning events (only `severity
   FATAL count == 0` and `event piCamera.CaptureFailed count == 0`, both unchanged), so the events trip nothing
   when the sensor is silent, and this check fails when it was answering.
5. GPS during a downlink. Old: `for gpsManager.Reading in D: samples >= 3, and the largest gap ... <= 10 s` in
   window D of L2-7 and L2-8. New: the same metric, helper and bound in window D of the new test L2-9 (one
   capture, one catalog downlink, REQ-PiSensor-012), with `event dpWriter.FileWritten count == 1`, `exactly one
   file arrived` and the precondition `CFDP transaction duration in D >= 30 s`. L2-7 and L2-8 keep the
   `bmpManager.Reading` and `imuManager.Reading` items. Without a fix the GPS checks fail in L2-1, L2-2
   (REQ-PiSensor-003) and L2-9 only.
7. Plausibility, in L2-1 and L2-2. Old: `BMP280 and GPS readings plausible for a bench at rest`. New: two checks
   with the same bounds, `BMP280 readings plausible for a bench at rest` and `GPS readings plausible for a bench
   at rest`, so that a GPS failure declared as known cannot cover a BMP280 failure. Made after the review.
6. Unchanged: both planted faults and their `fails` lists, the coverage minimum, every GPS period and
   plausibility check, `event piCamera.CaptureFailed count == 0`.

Review of 2026-11-20 (Mode B, one round, of `7a83d34`): not accepted on one must-fix (the flag bytes), logic
otherwise sound. The must-fix and the four could-fix items were edited in `466c827`; the edit was read by the
project anchor and not reviewed again. All taken: a flag byte is 0xFF for true and 0x00 for false as F Prime
writes a `bool` (`FW_SERIALIZE_TRUE_VALUE`), any other value is refused; a metric marked valid needs its telemetry
sample (0.1 s then, 1 s since the first live products, see below); the
unavailable event is judged at the capture time; wrong-record cases for each metric group. The frame count
precondition was already in every window, so none was added; what it does not cover is in the plan's not-covered
list, with the other limits of this revision. Since 2026-11-23 that precondition counts lost frames and no longer
refuses them, see "Lost frames" below.

Known-answer cases (`kat/run_kat.py`, list `BROKEN` and the `gps_silent` replay; records made by `kat/sim.py`):
GPS silent over the run with placeholders and the event (only L2-1, L2-2 and L2-9 fail); marked valid with a
sample 5 s old (`stale_sample`); a flag byte of 0x01 (`flag_one`); for each of location, temperature and attitude:
marked not valid while the sensor answers (`false_invalid`), placeholder without the event (`no_warning`), marked
valid without a telemetry sample at the sample time (`valid_absent`); for location also values that are not NaN
(`bad_placeholder`), a sample time that is not zero (`placeholder_time`), the event with a product marked valid
(`stray_warning`).

### After the first live products (2026-11-20, run `clean-3`; ordered by the project anchor, not reviewed)

The first record with products showed four faults of the harness. The changes below were made after the Mode B
review closed and were not reviewed.

1. File CRC helper. `fileManager.CalculateCrc` reports the CRC-32 without the final inversion (0x67b852b1 on
   board, 0x9847ad4e from zlib, for the same file). The helper now compares that value. No check text changed.
2. A metric marked valid. Old: a telemetry sample of its sensor within 0.1 s of the stated sample time. New:
   within 1 s. A sample on the ground carries the time of its packet (one a second), the product carries the
   sensor's own sample time; they were 0.10 to 0.40 s apart over 10 products. The not-covered note of the plan
   that assumed packet time equals sample time is corrected.
3. L2-8. Old: `event cmdDisp.NoOpReceived count == 1 between dpCat.CatalogXmitStarted and dpCat.CatalogXmitCompleted`.
   New: `event cmdDisp.NoOpReceived count == 1 between dpCat.CatalogXmitRangeStarted and dpCat.CatalogXmitCompleted`
   (also the `fails` text of `extra_noop`). `dpCat` emits `CatalogXmitRangeStarted` only.
4. L7-1. Old: `the directory listing names P only`. New: `the directory listing names P and DpState.dat only`.
   `DpState.dat` is the state file `dpCat` keeps in the product directory.
5. `known_failures` (fth `linux-host-coverage@3c4ab8e`): besides the GPS checks of L2-1, L2-2 and L2-9, the
   MPU6050 checks are declared: the `imuManager.Reading` period check and `MPU6050 readings plausible for a bench
   at rest` in L2-1 and L2-2, the `imuManager.Reading` item of window D in L2-7 and L2-8. The ruling string
   carries the three rulings of the human verbatim.

### Lost frames (2026-11-23; human ruling, not reviewed)

Rulings of the human, verbatim, in the order given:

- Michael Starch, 2026-11-20, in answer to the project anchor's question:
  "A. Tolerate 1 lost frame per test window; report the count and state the residual in the RDD"
- Michael Starch, 2026-11-23 12:42 PST, superseding it:
  "Just run the test.  If it drops a frame, not it, and then indicate that that specific test report may be erroneous."
  ("not it" is read as "note it".)

The change below follows the second ruling. It was made after the Mode B review closed and was not reviewed.

1. Precondition of every window. Old: `no gap, modulo 256, in the virtual channel frame count received by YAMCS
   between the markers (record/raw/frames.json)`. New: `TM frames received by YAMCS between the markers; the frames
   lost, modulo 256, in the virtual channel frame count are counted and noted on the test, never refused
   (record/raw/frames.json)`. It holds when any frame arrived. A lost frame no longer leaves a window unverified,
   whatever the count; the test is judged on what arrived. No run is repeated for lost frames.
2. The note. With one or more frames lost in a window, the value seen of that precondition reads
   `<n> frames, <k> lost in <g> gap(s). THIS TEST'S REPORT MAY BE ERRONEOUS: lost frames (...)`.
   - It appears in `record/junit.xml` (property `fth_checks` of the test) and in section 4, "Rule verdict", of the
     auditor's quick-look page of the test.
   - It does not appear in `runner/report.md`, `runner/verdicts.json`, or the tables of `fth dev-campaign`,
     `fth deliver` and `fth rfr`: fth lists failed checks only there and has no note field. fth was not changed.
   - `bench/lost_frames.py <run directory> --write` therefore writes the count and the note per test window into
     `README.md` of the run directory, from the junit.
3. Residual, also in the not-covered list of the plan: a lost frame can hide about 1 s of telemetry or an event,
   so a `count == 0` check can pass with the event in the lost frame, and a count or period check can fail on a
   correct unit. Nothing bounds how many frames a judged window may have lost.
4. Known-answer tests: a record with lost frames is judged, every test passes, and exactly the tests with a lost
   frame carry the count and the note.

### TCP link, plan revision 4 (2026-11-23; human ruling, not reviewed)

The flight RFM69 on `soakee` stays in transmit mode and takes neither a mode write nor a reset pulse
(`docs/ledger.md`). Ruling of the human, verbatim, Michael Starch, 2026-11-23 13:18 PST: "Ok, please switch to
TCP, and continue development w/o the radio". The project anchor ordered the changes below; none is reviewed.

- **Link.** The image (`PISENSOR_COM=TCP`, the default) is the TCP client: `Drv.TcpClient` connects to
  `192.168.10.1:50000` on the ground host, given as `PiSensor -a 192.168.10.1 -p 50000` (`bench.json`,
  `--image-args`). `bench/tcp_bridge.py` listens there, cuts the downlink stream into 255-byte TM frames for
  the fprime-yamcs TM link (UDP 51000) and writes each TC frame of the TC link (UDP 51001) to the connection.
  It writes the frame log (`bridge.log`) in the format of `ground/feather_bridge.py`, so `frames.json` and
  the lost-frame count are made as before. `ground/feather_bridge.py` is not used.
- **REQ-PiSensor-010 is not verified** by any test (plan, Not covered). It is out of the `covers` of L0-1,
  L2-7 and L2-8. Checks removed, with nothing in their place:

| Test | Removed check |
|---|---|
| L0-1 | `the process holds no TCP or UDP socket` |
| L2-7, L2-8 | `rfm69Manager.PacketsTransmitted and PacketsReceived rise in D; TM frames received <= PacketsTransmitted rise + 2` |

- **How the plan says it.** fth has one form for a requirement without a test and prints it as "waived"
  (`1 waived requirements`, `waived: Not verified: ...` in `plan.md`). Nobody waived the requirement: it is
  not verified.
- **Known-answer cases removed** with those checks: `extra_socket`, `tcp_frames`.
- **Texts corrected** (old, new):

| Where | Old | New |
|---|---|---|
| L0-1 purpose | Proves the image is the manifest's, on a Pi 5, reached only by RFM69. | Proves the image is the manifest's, on a Pi 5. |
| L0-1 setup | Deployment running on the Raspberry Pi 5; RFM69 link up. | Deployment running on the Raspberry Pi 5; TCP link up. |
| Setup of the other tests | ... RFM69 link up through the bench ground radio to fprime-yamcs ... | ... TCP link up through the bench bridge to fprime-yamcs ... |
| Scope, link | Link budget [I]: RFM69 at the catalog default data rate 19200 bit/s carries about 2400 byte/s; ... | Link (revision 4): TCP between the Pi and the ground host; the link budget of the RFM69 does not apply and the downlink time of a product over TCP is measured, not budgeted. |
| Scope, ground system | ... joined to the RFM69 link by the bench ground radio ... | ... joined to the TCP connection of the deployment by the bench bridge `test/int/bench/tcp_bridge.py` ... |
| Scope, telemetry gaps | ... margin for radio delay. | ... margin for link delay. |
| Scope, devices | the SPI devices of the RFM69 and the BMP280 | the SPI device of the BMP280 |
| Bench recipe | RFM69 ground radio joined to fprime-yamcs on the ground host (supplied with the bench) | the Pi 5 and the ground host on one Ethernet network, the deployment started with the address and TCP port of the bench bridge on the ground host |
| Not covered | Radio interference and range: the RFM69 link is tested at bench range only. | the REQ-PiSensor-010 entry |

- **Unchanged:** every other check, the 11 known failures, the lost-frame rule and its precondition (no lost
  frame is expected over TCP), the 75 % coverage minimum.
- **Not true any more, left as history:** "Settled at the bench" and "Flight configuration of 2026-11-19"
  below describe the radio link (telemetry age, link counters, downlink rate).

## Settled at the bench (2026-11-19)

- YAMCS generation time is the unit time tag + 1.000 s (`timetags.jsonl`): `gen_offset` 1.0 stands. The
  recorder of `yamcs_bench.py` does not subtract it; this harness uses `yamcs_recorder.py`.
- Image, ground system and command sending are those of `yamcs_bench.py` (proven by the component runs);
  it logs the sending time as local time without a zone, so a record is judged in the time zone of its bench.
- `bench.json` serial and dictionary; bench position 34.130442, -118.058840.
- Telemetry age grows by about 0.1 s per second of run: `Rfm69Manager` holds 0.5 s after each frame
  (1.6 frames/s) and idle telemetry needs a little more. See `docs/ledger.md`.
- The blind lint of fth refuses the word for the sending program in stimulus prose; it is not used there.
- fth pins and replays the tests directory and wants the plan and its helper module in it, and its lint
  refuses other Python there: the plan, its menu and `planted_faults.py` moved from `test/int/` to
  `test/int/stimulus/` (content unchanged by the move). `fth run` passes no partial selection to pytest, so
  L0 is the first two tests of a full run.
- The recorder logs the channels of the dictionary only. YAMCS also publishes packet fields
  (`CCSDS_Packet_*`, `FPrimeTime`, `FPrimeFilePacket*`) whose generation time is no unit time; with them in
  the record fth reads a restart and its windows hold no channel row.
- YAMCS takes a bool argument as `True` or `False`. Parameter commands are in the dictionary with an
  upper-case name (`FILEINDEFAULTKEEP_PRM_SET`); `yamcs_bench.py send` matches them without case and logs
  the name as the plan writes it.
- `final_state` accepts an empty product directory.
- Link findings of the first live runs (flight configuration, not harness; numbers in `docs/ledger.md`):
  a command frame above 67 bytes does not arrive whole, so `fileManager.CalculateCrc` of a product path
  (44 characters) ends in `FORMAT_ERROR`; a picture downlink does not complete; one telemetry sample was lost
  on board in the second run; telemetry stops for minutes while a file is sent.

## Flight configuration of 2026-11-19 (`fix/link-budget`, `docs/link-budget.md`)

- Product directory is `dp` (`DP_DIR`, the `clean_products` and `final_state` actions).
- `flash --prm uut/test/int/bench/PrmDb.dat` copies the parameter file into the working directory of the image
  before it starts. The file is committed (`test/int/bench/PrmDb.dat`, sha256 `a31359ba...f47527`, the file of
  every run since 2026-11-19), because `fth rfr` accepts only paths in the package or the pinned checkouts.
  Rebuild it after a change of `PiSensor/project/config/PrmDb.json` with `fprime-prm-write dat
  PiSensor/project/config/PrmDb.json --dictionary <dictionary of the image> -o test/int/bench/PrmDb.dat`.
- The directory on the Pi is `pisensor-campaign/<NAME>` of `yamcs_bench.py --pi-run NAME` (no `/` in NAME). The
  default `sys-run` is also the default of `uut.py --remote-dir`; the PiCamera recipes pass `--pi-run=fth-uut`,
  because `flash` deletes `run/` in its directory. The recorder takes the YAMCS space system without its leading `/`
  (`--root PiSensor_PiSensor`): `fth rfr --dry-run` refuses both spellings in a recipe as host paths.
- `"vars": {"uart": null}` in both recipes declares to fth that this bench has no serial device (the link is
  TCP); without it `fth rfr` refuses a recipe that names no UART.
- The bench YAMCS configuration carries the CFDP timers of `docs/link-budget.md` (bench set-up, not in this
  repository).
- A test waits 600 s for each product it downlinks (and for one more where a planted capture can add one):
  128 file bytes a second, pictures at JPEG quality 20 of 9.5 to 11.7 kB (75 to 95 s), design target 32 kB
  (250 s), doubled for a busier scene and PDUs sent again, plus 100 s for the CFDP exchange.
  `wait_cfdp` waits 600 s.
- The wait at the end of a window stays, with a limit of 60 s instead of 900 s: telemetry is one to two seconds
  behind, and fth judges a window right after its END marker, so the samples of the last second would be missing.
- Link counters (`rfm69Manager.PacketsTransmitted`, `PacketsReceived`) arrive every 5 s. The one check that
  reads them needs two samples in a downlink window of minutes; unchanged.
- A command is sent again 6.4 s after it was sent, not 6.0 s: the unit sends a telemetry frame every second and
  hears nothing while it sends (half duplex), so a resend a whole number of seconds later meets the same frame.
  Seen on the first run: three sends of one marker command at the start of the unit's frame, none received.
- `Svc.TlmPacketizer` gives a packet the time of the last write to one of its channels. A packet of seldom
  written channels (`version.*`, sent every 300 s) so arrives minutes behind the others, and fth reads a step
  back of more than 5 s in unit time as a restart: the windows after it held no channel row. The recorder
  writes a row more than 4 s behind the newest unit time to `fprime-cli-yamcs/channel-late.log`, which is in
  the record and which fth does not read. A sensor sample that late is then missing from its window and the
  2 s rule fails, as it should.
