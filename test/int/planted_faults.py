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
    ("command_completed_within", "OpCodeCompleted of the command's opcode - its dispatch <= bound_s (FSW clock)."),
    ("product_time_within", "Capture time record of the ground file against the bench time of the CAPTURE, tol_s."),
    ("product_sample_times_present", "Each metric record of the ground file carries a sample time not later than capture time + tol_s."),
    ("downlink_duration_at_least", "CFDP transaction duration from the ground transfer record >= bound_s."),
    ("clock_offset_within", "Pi clock against bench clock from a bench action; a precondition (UNVERIFIED when not met)."),
]:
    _declare(_name, _doc)


@planted_fault("capture_twice", applies_to=["L2-3"], cls="stimulus", kind="insert",
               mechanism="piCamera.CAPTURE is sent twice in a row (inserted copy); two products are written and sent where the test expects one",
               fails={"L2-3": ["event dpWriter.FileWritten count == 1", "exactly one file arrived"]})
def capture_twice(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return [(command_name, args), (command_name, args)]
    return None


@planted_fault("append_before_xmit", applies_to=["L2-4", "L2-7"], cls="uut-state", kind="insert",
               mechanism="fileManager.AppendFile(P, P) is inserted before dpCat.BUILD_CATALOG, after fileManager.CalculateCrc: the stored product grows on board, so the file sent differs from the file checked",
               fails={"L2-4": ["CRC of record/raw/files/<P1> and <P2>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P"],
                      "L2-7": ["CRC of record/raw/files/<P>, computed by the bench with the F Prime file CRC, == value in the fileManager.CalculateCrcSucceeded event of P"]})
def append_before_xmit(test_id, command_name, args):
    if _is(command_name, "BUILD_CATALOG"):
        return [("fileManager.AppendFile", ["<last product>", "<last product>"]), (command_name, args)]
    return None
