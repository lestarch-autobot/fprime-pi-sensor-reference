#!/usr/bin/env python3
"""Check the stimulus against the plan procedures without a bench (fth 0.1.2 has no `verify-stimulus`).

Runs the stimulus in fth's dry-run mode in a scratch directory, reads the commands it would send, in
order, and compares them test by test with the command steps of each plan procedure: same commands,
same order, same arguments. Arguments the unit under test chooses (product names) are placeholders in
the dry run and are only counted. Exit status 0 when every test matches.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

STEP = re.compile(r"^(MARK|[A-Za-z_]\w*\.\w+)\((.*)\)$")
CHOSEN = re.compile(r"^(P\d*|<P\d+>|product directory|\./DpCat|dp)$")  # named by the UUT or the configuration


def plan_steps(plan: dict, marker: str) -> dict:
    out = {}
    for t in plan["tests"]:
        steps = []
        for s in t["procedure"]:
            m = STEP.match(s.strip())
            if m:
                args = [a.strip() for a in m.group(2).split(",") if a.strip()]
                steps.append((marker if m.group(1) == "MARK" else m.group(1), args))
        out[t["id"]] = steps
    return out


def sent(run_dir: Path, deployment: str = "PiSensor") -> list:
    """Commands of the dry run, in order, by the short name the plan uses (fth prefixes the deployment)."""
    rows, lead = [], deployment + "."
    for log in sorted((run_dir / "record" / "raw" / "cmd").glob("fprime-cli-dry-*/command.log")):
        for line in log.read_text(encoding="utf-8").splitlines():
            head, raw = line.split(",[", 1)
            name = head.split(",")[2]
            rows.append((name[len(lead):] if name.startswith(lead) else name, [str(a) for a in json.loads("[" + raw)]))
    return rows


def compare(want: list, got: list) -> list:
    problems = []
    if [n for n, _ in want] != [n for n, _ in got]:
        return [f"commands differ: plan {[n for n, _ in want]}, stimulus {[n for n, _ in got]}"]
    for (name, wa), (_, ga) in zip(want, got):
        if len(wa) != len(ga) or any(a != b and not (CHOSEN.match(a) and CHOSEN.match(b)) for a, b in zip(wa, ga)):
            problems.append(f"{name}: plan arguments {wa}, stimulus {ga}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("--tests", required=True)
    ap.add_argument("--bench", required=True)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    marker = plan["markers"]["command"]
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", a.tests, "-p", "fth.pytest_plugin", "-p", "no:cacheprovider", "-q",
                            "--fth-plan", a.plan, "--fth-run-dir", tmp, "--fth-bench", a.bench, "--fth-dry-run"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-3000:], r.stderr[-1000:])
            print("verify-stimulus: the dry run failed")
            return 1
        rows = sent(Path(tmp))
    steps, bad, pos = plan_steps(plan, marker), 0, 0
    for test_id, want in steps.items():
        got = rows[pos:pos + len(want)]
        last = next((i for i in range(pos, len(rows)) if rows[i] == want[-1]), None)  # this test's closing marker
        if last is not None:
            got = rows[pos:last + 1]
            pos = last + 1
        problems = compare(want, got)
        bad += bool(problems)
        print(f"{test_id}: {'ok' if not problems else 'MISMATCH'} ({len(want)} command steps)" + "".join(f"\n    {p}" for p in problems))
    if pos != len(rows):
        bad += 1
        print(f"{len(rows) - pos} command(s) sent outside every plan test: {rows[pos:]}")
    print(f"verify-stimulus: {'ok' if not bad else 'FAILED'}: {len(steps)} tests, {len(rows)} commands in the dry run")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
