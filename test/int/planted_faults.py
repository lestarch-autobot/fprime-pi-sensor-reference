"""Helpers and planted faults for the PiSensor system test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``.

Planted faults rewrite or insert commands of components already in the deployment. Helper
bodies are written in the harness phase; until then each returns UNVERIFIED, never a pass.
"""
from fth.registry import helper, planted_fault


def _is(command_name, short):
    return command_name == short or command_name.endswith("." + short)


def _declare(name, doc):
    @helper(name)
    def _h(ctx, **kwargs):
        return None, "helper body not written (design phase)", [], True
    _h.__name__ = name
    _h.__doc__ = doc


for _name, _doc in [
    ("max_ground_gap", "Largest gap between ground reception times of each listed channel <= bound_s."),
    ("event_after_command_within", "Named event time - OpCodeDispatched time of the named command <= bound_s (FSW clock), per command."),
    ("product_time_within", "Capture time record of the ground file against the bench time of the CAPTURE, tol_s."),
    ("product_sample_times_within", "Each metric record of the ground file carries a sample time within bound_s of the capture time record."),
    ("downlink_duration_at_least", "CFDP transaction duration from the ground transfer record >= bound_s."),
    ("clock_offset_within", "Pi clock against bench clock from a bench action; a precondition (UNVERIFIED when not met)."),
]:
    _declare(_name, _doc)


_served = set()


@planted_fault("capture_before_xmit", applies_to=["L2-3", "L2-4", "L2-7"], cls="uut-state", kind="insert",
               mechanism="piCamera.CAPTURE() is inserted before the first fileManager.CalculateCrc of the test: one more product is stored than the test made, before the 30 s wait and the catalog build, so it is stored, downlinked and deleted with the others",
               fails={"L2-3": ["event dpWriter.FileWritten count == 1", "exactly one file arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 1"],
                      "L2-4": ["event dpWriter.FileWritten count == 2 with different names", "exactly two files arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2"],
                      "L2-7": ["event dpWriter.FileWritten count == 2 over the whole test (Q and D)", "exactly two files arrived", "event cmdDisp.OpCodeCompleted of piCamera.CAPTURE count == 2"]})
def capture_before_xmit(test_id, command_name, args):
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
