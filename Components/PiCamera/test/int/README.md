# PiCamera component bench tests

Bench tests of `piCamera` in the PiSensor deployment as flown: no test
component. The plan is `plan.json` (`plan.md` is rendered from it), the
stimulus and its named checks are `test_picam.py`, the planted faults are
`planted_faults.py` (`faults-menu.json` is generated from it).

The tests run with [fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness)
(`fth`) from the ground workstation. `bench.json` describes the bench: the
image is copied to the Raspberry Pi over ssh and started there, the ground
system is fprime-yamcs behind the RFM69 bridge. Every bench command line calls
`test/int/bench/yamcs_bench.py` of this repository; set `vars` in `bench.json`
to where it and the ground tools are installed.

C-1, and the second capture of C-2 and C-3, need a GPS fix. Without one the
capture fails at `LOCATION` and the test fails.

## Check the plan and the stimulus (no bench)

```bash
PYTHONDONTWRITEBYTECODE=1 fth verify-plan plan.json --tests . --bench bench.json
fth render-plan plan.json -o plan.md
fth planted-faults-menu plan.json -o faults-menu.json --max-count 1
```

## Dry run of the whole plan on the bench

```bash
fth manifest ...            # pins the repository, plan, tests, bench.json and the image
fth run --unsealed --run-dir runs/dry-1 --manifest manifest.json --bench bench.json \
    --plan plan.json --tests .
fth audit --tests . runs/dry-1
```

A dry run is labelled as such and is not a record.

## One test

```bash
fth run --unsealed ... --fth-allow-partial -k test_C_2   # same arguments as above, then pytest arguments
```

## Release the bench

```bash
python test/int/bench/yamcs_bench.py stop
```

`fth run` stops the ground system it started. The image on the Pi keeps
running until the next run or this command.
