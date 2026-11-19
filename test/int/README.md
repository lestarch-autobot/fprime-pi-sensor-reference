# PiSensor system test harness

The harness of the 11 tests of `stimulus/plan.json` (approved with Gate 1). It runs on the bench workstation with
[fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness) (`fth`) v0.1.2; the ground
system is fprime-yamcs and the ground radio is the Feather M0 RFM69. Nothing here is part of the flight
deployment and there is no test component.

| Path | What it is |
|---|---|
| `stimulus/plan.json`, `stimulus/plan.md`, `stimulus/faults-menu.json`, `gen_plan.py` | the plan, revision 2 (changelog below) |
| `stimulus/planted_faults.py` | the plan's helper predicates (its metrics) and planted faults |
| `stimulus/test_pisensor.py` | the stimulus and the named checks, one function per plan test; the `--tests` directory |
| `stimulus/pisensor_record.py` | record access for the checks: ground reception time, transfers, frames, product decoder |
| `bench.json` | the bench: command lines of the ground side, the sender, the recorder, the UUT actions |
| `bench/yamcs_bench.py` | of the `piCamera` component tests: image on the Pi, fprime-yamcs and `ground/feather_bridge.py`, command sending with resend |
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
