"""Helpers and planted faults for the ProductManager component system test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``. Planted faults rewrite or insert commands
that pass through ``send()``. ``fails`` names the checks each fault must break; the names are those
of the plan's evidence lines and are replaced by the names declared in the stimulus module in the
harness phase (``fth verify-plan --tests`` then refuses any name no test declares). Helper bodies
are written in the harness phase; until then each returns UNVERIFIED, never a pass.
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
    ("command_completed_within", "OpCodeCompleted of the command's opcode - its dispatch <= bound_s (FSW clock)."),
    ("downlink_duration_at_least", "CFDP transaction duration from the ground transfer record >= bound_s; a precondition (UNVERIFIED when not met)."),
]:
    _declare(_name, _doc)

_seen = {}


@planted_fault("capture_twice", applies_to=["L2-1"], cls="stimulus", kind="insert",
               mechanism="CAPTURE is sent twice in a row; two products are written where the test expects one",
               fails={"L2-1": ["event productManager.ProductWritten count == 1", "the sysTester.DirListing event names P and no other file"]})
def capture_twice(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return [(command_name, args), (command_name, args)]
    return None


@planted_fault("corrupt_first_product", applies_to=["L2-2"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(P1) is inserted before the second DUMP_SHA256 of P1: the first two bytes of its picture record are overwritten on board, as an overwriting second capture would; the test removes its products at teardown",
               fails={"L2-2": ["the two sysTester.Sha256 events of P1 are equal"]})
def corrupt_first_product(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256") and len(args) > 1 and str(args[1]) == "2":
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None


@planted_fault("delete_other", applies_to=["L2-4"], cls="stimulus", kind="rewrite",
               mechanism="DELETE(P1) is sent as DELETE(P2), the product hashed by the preceding DUMP_SHA256; the wrong product is removed",
               fails={"L2-4": ["event productManager.ProductDeleted count == 1 and names P1", "the sysTester.DirListing event names P2 only",
                               "event productManager.ProductStored count == 1 and names P2"]})
def delete_other(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256"):
        _seen[test_id] = args[0]
    if _is(command_name, "DELETE") and test_id in _seen:
        return [(command_name, [_seen[test_id]])]
    return None


@planted_fault("second_capture_dropped", applies_to=["L5-1"], cls="stimulus", kind="rewrite",
               mechanism="the second CAPTURE is sent as cmdDisp.CMD_NO_OP; no command is rejected",
               fails={"L5-1": ["event productManager.CommandRejected count == 1"]})
def second_capture_dropped(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        n = _seen.get((test_id, "cap"), 0) + 1
        _seen[(test_id, "cap")] = n
        if n == 2:
            return [("cmdDisp.CMD_NO_OP", [])]
    return None


@planted_fault("delete_before_downlink", applies_to=["L5-5"], cls="uut-state", kind="insert",
               mechanism="DELETE(P) is inserted before DOWNLINK(P): the product is removed on board, so nothing is delivered and the later DELETE names no stored product",
               fails={"L5-5": ["event productManager.CommandRejected count == 1", "event productManager.ProductDeleted count == 0",
                               "sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event",
                               "the two sysTester.Sha256 events are equal", "the sysTester.DirListing event names P"]})
def delete_before_downlink(test_id, command_name, args):
    if _is(command_name, "DOWNLINK"):
        return [("productManager.DELETE", list(args)), (command_name, args)]
    return None


@planted_fault("downlink_existing", applies_to=["L6-1"], cls="stimulus", kind="rewrite",
               mechanism="DOWNLINK(Dp_missing.fxd) is sent with the name of the product the test captured (read from the preceding ProductWritten event); the product is sent",
               fails={"L6-1": ["event productManager.ProductNotFound count == 1", "event productManager.DownlinkStarted count == 0",
                               "no CFDP transaction starts at the ground in the window"]})
def downlink_existing(test_id, command_name, args):
    if _is(command_name, "DOWNLINK"):
        return [(command_name, ["<P>"])]
    return None
