# PiCamera component bench tests

Bench tests of `piCamera` in the PiSensor deployment as flown: no test
component. The plan is `plan.json` (`plan.md` is rendered from it), the
stimulus and its named checks are `test_picam.py`, the planted faults are
`planted_faults.py` (`faults-menu.json` is generated from it).

The tests run with [fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness)
(`fth`) from the ground workstation. `bench.json` describes the bench: the
image is copied to the Raspberry Pi over ssh and started there, the ground
system is fprime-yamcs behind the TCP bridge `test/int/bench/tcp_bridge.py`,
which the image connects to. Every bench command line calls
`test/int/bench/yamcs_bench.py` of this repository.

Run `fth` from a campaign root on the workstation that holds:

- `uut/`: the checkout of this repository;
- `yamcs-config/`: the YAMCS configuration directory of `ground/README.md`;
- `inputs/`: the image, its dictionary and `PrmDb.dat` (`fprime-prm-write dat PiSensor/project/config/PrmDb.json --dictionary <dictionary> -o inputs/PrmDb.dat`).

`python3` (with `yamcs-client`) and `fprime-yamcs` are on `PATH`.
The Pi is the ssh host `pi`.

The link is TCP and loses no command. The sender still sends a command again, at
most twice, when the unit does not report its dispatch within 6 s, and writes
each resend to `record/raw/cmd/resend.log`. Ground link events of YAMCS are
kept in `record/raw/ground-events.log`.

The bracket channel is `bmpManager.Reading`. No sensor reading is needed for a capture:
without the BMP280, the MPU6050 or a GPS fix a capture completes with the warning of that
reading (`TemperatureUnavailable`, `AttitudeUnavailable`, `LocationUnavailable`).

## Check the plan and the stimulus (no bench)

```bash
python -m pytest checks_kat.py     # known answers of the check functions
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

## Coverage on the target

The image as flown has no coverage dump command. An image built with
`--coverage` writes its counts when it ends:

```bash
sh test/int/bench/build_image.sh -DCMAKE_C_FLAGS=--coverage -DCMAKE_CXX_FLAGS=--coverage \
    -DCMAKE_EXE_LINKER_FLAGS=--coverage      # keep this build tree: it holds the .gcno files
fth run --unsealed ... --bench bench-coverage.json   # flash --gcov: counts stay on the Pi under gcda/
python3 uut/test/int/bench/yamcs_bench.py stop       # the image ends and writes the counts
python3 uut/test/int/bench/yamcs_bench.py collect-gcda <dir>
fth dev-campaign ... --gcda-dir <dir> --gcno-root <build tree> --gcov gcov
```
