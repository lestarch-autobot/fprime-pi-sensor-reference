# PiSensor system test harness

The harness of the 11 tests of `plan.json` (approved with Gate 1). It runs on the bench workstation with
[fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness) (`fth`) v0.1.2; the ground
system is fprime-yamcs and the ground radio is the Feather M0 RFM69. Nothing here is part of the flight
deployment and there is no test component.

| Path | What it is |
|---|---|
| `plan.json`, `plan.md`, `faults-menu.json`, `gen_plan.py` | the approved plan (baseline; not changed by the harness) |
| `planted_faults.py` | the plan's helper predicates (its metrics) and planted faults |
| `stimulus/test_pisensor.py` | the stimulus and the named checks, one function per plan test; the `--tests` directory |
| `stimulus/pisensor_record.py` | record access for the checks: ground reception time, transfers, frames, product decoder |
| `bench.json` | the bench: command lines of the ground side, the sender, the recorder, the UUT actions |
| `bench/ground.py` | starts and stops fprime-yamcs and `ground/feather_bridge.py` |
| `bench/yamcs_send.py` | sends one command through the YAMCS HTTP API, writes the sender log fth reads |
| `bench/yamcs_recorder.py` | records events, telemetry, transfers, frames and received files from YAMCS |
| `bench/uut.py` | the Pi over ssh: install and start the image, read it back, the bench actions |
| `bench/verify_stimulus.py` | stimulus against the plan procedures, from a dry run |
| `kat/` | known-answer tests of all of the above over a synthetic record (`run_kat.py`, `sim.py`) |

## Offline checks (no bench)

```
fth verify-plan test/int/plan.json --tests test/int/stimulus --bench test/int/bench.json
python -B test/int/bench/verify_stimulus.py test/int/plan.json --tests test/int/stimulus --bench test/int/bench.json
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

## To settle at the bench

`bench.json` `serial` and `dictionary`; `BENCH_POSITION` in the stimulus (surveyed latitude and longitude:
until set, "sensor readings plausible" fails); the event order of the marker (item 6); `gen_offset` against
`timetags.jsonl`; YAMCS client calls of the sender and recorder (written from the fprime-yamcs 0.2.5 and
yamcs-client sources, never run against a server); the format of the `version` events; `piCamera` names
and the product layout once the component is wired (taken from its SDD); the character-device list.
