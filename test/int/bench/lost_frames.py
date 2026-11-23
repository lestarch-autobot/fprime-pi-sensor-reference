#!/usr/bin/env python3
"""Lost TM frames of a run, per test window, from the check outcomes in its junit.xml.

    lost_frames.py <run directory> [--write]

Prints one line per window that lost a frame. With --write it puts the table into README.md of the run directory:
fth's own report tables list failed checks only, so the note of the human ruling of 2026-11-23 ("indicate that that
specific test report may be erroneous") is written there. Nothing under record/ is touched.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NOTE = "this test's report may be erroneous: lost frames"


def lost(junit):
    """[(test id, window, frames, lost, value seen)] for every frame precondition outcome in the junit."""
    rows = []
    for case in ET.parse(str(junit)).getroot().iter("testcase"):
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        for o in json.loads(props.get("fth_checks") or "[]"):
            m = re.match(r"(\d+) frames, (\d+) lost in \d+ gap", o.get("seen") or "")
            if m:
                rows.append((props.get("fth_test_id") or case.get("name"), o.get("window", ""), int(m.group(1)), int(m.group(2)), o["seen"]))
    return rows


def table(run, rows):
    L = [f"# Run `{run.name}`: lost TM frames", "",
         "Human ruling, Michael Starch, 2026-11-23 12:42 PST: \"Just run the test.  If it drops a frame, not it, and then "
         "indicate that that specific test report may be erroneous.\"", "",
         "| test | window | frames received | frames lost | note |", "|---|---|---|---|---|"]
    L += [f"| {t} | {w} | {n} | {k} | {NOTE if k else ''} |" for t, w, n, k, _ in rows]
    flagged = sorted({t for t, _, _, k, _ in rows if k})
    L += ["", f"Tests whose report may be erroneous because of lost frames: {', '.join(flagged) if flagged else 'none'}.",
          "A test with no row was not judged up to its frame precondition.", ""]
    return "\n".join(L)


def main(argv):
    run = Path(argv[1])
    junit = next(p for p in (run / "record" / "junit.xml", run / "runner" / "junit.xml") if p.is_file())
    rows = lost(junit)
    for t, w, n, k, seen in rows:
        if k:
            print(f"{t} {w}: {seen}")
    print(f"{sum(k for *_, k, _ in rows)} lost frame(s) in {sum(1 for *_, k, _ in rows if k)} of {len(rows)} window(s)")
    if "--write" in argv:
        (run / "README.md").write_text(table(run, rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
