"""Helpers and planted faults for the PiSensor system test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``.

Planted faults rewrite or insert commands of components already in the deployment. The helper
predicates are the plan's metrics; they read the record through stimulus/pisensor_record.py.
"""
from fth.registry import helper, planted_fault


def _is(command_name, short):
    return command_name == short or command_name.endswith("." + short)


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pisensor_record as rec  # noqa: E402


def _capture_rows(w):
    """(CAPTURE command rows, their OpCodeDispatched rows, their OpCodeCompleted rows) of the window."""
    cmds = [c for c in w.cmds if c.short == "piCamera.CAPTURE"]
    ops = {c.opcode for c in cmds}
    of = lambda e: int(rec.OPCODE.search(e.text).group(1), 16) if rec.OPCODE.search(e.text) else None
    return (cmds, [e for e in w.events("cmdDisp.OpCodeDispatched") if of(e) in ops],
            [e for e in w.events("cmdDisp.OpCodeCompleted") if of(e) in ops])


def _products(w):
    return sorted((rec.decode_product(d) for d in rec.arrived(w).values()), key=lambda p: p["metrics"]["captureTime"]["t"])


@helper("max_ground_gap")
def max_ground_gap(ctx, channels, bound_s, min_samples):
    """Largest gap between ground reception times of each listed channel <= bound_s, window edges included."""
    t0, t1 = rec.bounds(ctx.window)
    bad, seen = [], []
    for ch in ctx.plan.packets[channels]:
        # by ground reception time, as the requirement is stated: fth cuts ctx.window.channel() on FSW time
        times = sorted(t for t in (rec.rx(r) for r in ctx.record.channels if r.short == ch) if t0 <= t <= t1)
        gap = max(b - a for a, b in zip([t0] + times, times + [t1]))
        seen.append(f"{ch}: {len(times)} samples, largest gap {gap:.3f} s")
        if len(times) < min_samples or gap > bound_s:
            bad.append(ch)
    return not bad, "; ".join(seen), [], False


@helper("event_after_command_within")
def event_after_command_within(ctx, command, event, bound_s):
    """Named event time - OpCodeDispatched time of the named command <= bound_s (FSW clock), per command."""
    cmds, disp, _ = _capture_rows(ctx.window) if command == "piCamera.CAPTURE" else ([], [], [])
    events = ctx.window.events(event)
    if not cmds:
        return False, f"no {command} in the window", [], False
    deltas = [events[k].fsw - disp[k].fsw if k < len(events) and k < len(disp) else None for k in range(len(cmds))]
    ok = all(d is not None and 0 <= d <= bound_s for d in deltas)
    return ok, "delta t per command: " + ", ".join("absent" if d is None else f"{d:.3f} s" for d in deltas), [], False


@helper("product_time_within")
def product_time_within(ctx, tol_s):
    """Capture time record of each ground file against the bench times of its CAPTURE, tol_s."""
    cmds, _, done = _capture_rows(ctx.window)
    prods = _products(ctx.window)
    if not prods or len(prods) > len(cmds) or len(prods) > len(done):
        return False, f"{len(prods)} product(s), {len(cmds)} CAPTURE sent, {len(done)} completed", [], False
    seen, ok = [], True
    for k, p in enumerate(prods):
        lo, hi, t = rec.epoch(cmds[k].sent) - tol_s, rec.rx(done[k]) + tol_s, p["metrics"]["captureTime"]["t"]
        ok = ok and lo <= t <= hi
        seen.append(f"capture {t:.3f} in [{lo:.3f}, {hi:.3f}]")
    return ok, "; ".join(seen), [], False


@helper("product_sample_times_within")
def product_sample_times_within(ctx, bound_s):
    """Each metric marked valid of each ground file carries a sample time within bound_s of the capture time record."""
    prods = _products(ctx.window)
    worst = [max([abs(p["metrics"][tkey]["t"] - p["metrics"]["captureTime"]["t"])  # REQ-PiSensor-014: metrics marked valid
                  for _, flag, _, tkey, _, _ in rec.GROUPS if p["metrics"][flag]], default=0.0)
             for p in prods]
    return bool(prods) and all(x <= bound_s for x in worst), "largest |sample - capture| per product: " + (", ".join(f"{x:.3f} s" for x in worst) or "no product"), [], False


@helper("downlink_duration_at_least")
def downlink_duration_at_least(ctx, bound_s):
    """Ground time from the first transfer start to the last transfer seen finished >= bound_s; a precondition."""
    ts = [t for t in rec.transfers(ctx.window) if t.get("finished_seen")]
    if not ts:
        return None, "no finished CFDP transaction in the window", [], True
    d = max(t["finished_seen"] for t in ts) - min(rec.epoch(t["startTime"]) for t in ts)
    return d >= bound_s, f"{len(ts)} transaction(s) over {d:.1f} s", [], d < bound_s


@helper("clock_offset_within")
def clock_offset_within(ctx, bound_s):
    """Pi clock against bench clock from the `clock` bench action; a precondition (UNVERIFIED when not met)."""
    got = [a for a in rec.actions(ctx.window, "clock") if a["rc"] == 0]
    if not got:
        return None, "no clock measurement in the window", [], True
    m = rec.json.loads(got[-1]["stdout"])
    worst = abs(m["offset_s"]) + m["uncertainty_s"]
    return worst <= bound_s, f"Pi - bench = {m['offset_s']:+.3f} s +/- {m['uncertainty_s']:.3f} s", [], worst > bound_s


_served = set()


@planted_fault("capture_before_xmit", applies_to=["L2-3", "L2-4", "L2-7"], cls="uut-state", kind="insert",
               mechanism="piCamera.CAPTURE() is inserted before the first fileManager.CalculateCrc of the test: one more product is stored than the test made, before the 30 s wait and the catalog build, so it is stored, downlinked and deleted with the others",
               fails={"L2-3": ["event dpWriter.FileWritten count == 1", "exactly one file arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1"],
                      "L2-4": ["event dpWriter.FileWritten count == 2 with different names", "exactly two files arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2"],
                      "L2-7": ["event dpWriter.FileWritten count == 2 over the whole test (Q and D)", "exactly two files arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2"]})
def capture_before_xmit(test_id, command_name, args):
    if _is(command_name, "BUILD_CATALOG"):
        _served.discard(test_id)
    if _is(command_name, "CalculateCrc") and test_id not in _served:
        _served.add(test_id)
        return [("piCamera.CAPTURE", []), (command_name, args)]
    return None


@planted_fault("extra_noop", applies_to=["L2-2", "L2-8"], cls="stimulus", kind="insert",
               mechanism="cmdDisp.CMD_NO_OP() is sent twice in a row (inserted copy): one more command is served than the test expects",
               fails={"L2-2": ["event cmdDisp.NoOpReceived count == 3"],
                      "L2-8": ["event cmdDisp.NoOpReceived count == 1 between dpCat.CatalogXmitStarted and dpCat.CatalogXmitCompleted"]})
def extra_noop(test_id, command_name, args):
    if _is(command_name, "CMD_NO_OP"):
        return [(command_name, args), (command_name, args)]
    return None
