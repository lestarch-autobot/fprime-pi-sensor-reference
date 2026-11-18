"""Helpers and planted faults for the ProductManager component system test plan (design phase).

Loaded by ``fth`` through ``plan.json: helpers_module``. Planted faults rewrite or insert commands
that pass through ``send()``; a fault sees ``(test_id, command_name, args)`` only. ``fails`` names,
verbatim, the checks of the test's evidence line (``checks.json``) that the fault must break; the
stimulus tests declare the same names (``fth verify-plan --tests`` refuses drift). Helper bodies are
written in the harness phase against the record layout of the project plan; until then each returns
UNVERIFIED, never a pass.
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
    ("version_matches_manifest", "Svc.Version payloads in the window equal the describe strings of the named manifest image."),
    ("only_failed_command", "Exactly one cmdDisp.OpCodeError in the window, its opcode that of `command`; every other dispatched command has its OpCodeCompleted."),
    ("dir_listing_equals", "The index-th sysTester.DirListing event of the window names exactly the files `names` (symbols bound to the names of ProductWritten events in order)."),
    ("dir_listings_equal", "The a-th and b-th sysTester.DirListing events of the window carry the same file names and count."),
    ("event_severity", "Every event of the given name in the window has the given severity (severity column of the exported event row)."),
    ("event_names", "The event occurs `count` times and its `name` arguments are, in order, `prefix` followed by the products bound to `names`; different symbols are different names."),
    ("sha_events_equal", "The two sysTester.Sha256 events of the product (pass 1 and 2) carry the same hash; fewer than two events fails."),
    ("ground_file_hash_equals", "sha256 of the ground copy record/raw/files/<product> equals the hash of the first sysTester.Sha256 event of the product."),
    ("ground_cfdp_transactions", "Count, file name and outcome of the CFDP transactions of the window in record/raw/cfdp.json."),
    ("dispatched_before_event_by", "Precondition: the command after `after_command` is dispatched at least margin_s before the event (FSW clock)."),
    ("dispatched_inside_transfer", "Precondition: the command after the first DOWNLINK is dispatched after DownlinkStarted and margin_s before the ground end time of the transaction."),
    ("ground_cfdp_service_up", "Precondition: record/raw/cfdp.json covers the whole window (the ground CFDP service was up)."),
]:
    _declare(_name, _doc)

ABS_DISCARD = "event productManager.ProductDiscarded count == 0"
NOERR = "event cmdDisp.OpCodeError count == 0"
_seen = {}


@planted_fault("capture_twice", applies_to=["L2-1"], cls="stimulus", kind="insert",
               mechanism="CAPTURE is sent twice in a row, each awaited to completion as `send()` does for every command it emits; two products are written where the test expects one",
               fails={"L2-1": ["event productManager.ProductWritten count == 1, naming P",
                               "sysTester.DirListing event 2 names P and no other file"]})
def capture_twice(test_id, command_name, args):
    if _is(command_name, "CAPTURE"):
        return [(command_name, args), (command_name, args)]
    return None


@planted_fault("corrupt_first_product", applies_to=["L2-2"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(P1) is inserted before the second DUMP_SHA256 of P1: the first two bytes of its picture record are overwritten on board, as an overwriting second capture would; the teardown removes the product",
               fails={"L2-2": ["the two sysTester.Sha256 events of P1 carry the same hash"]})
def corrupt_first_product(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256") and len(args) > 1 and str(args[1]) == "2":
        return [("sysTester.CORRUPT_PRODUCT", [args[0]]), (command_name, args)]
    return None


@planted_fault("delete_other", applies_to=["L2-4"], cls="stimulus", kind="rewrite",
               mechanism="DELETE(P1) is sent as DELETE(P2), the product named by the preceding DUMP_SHA256; the wrong product is removed, and the second DUMP_SHA256 of P2 fails on a missing file",
               fails={"L2-4": ["event productManager.ProductDeleted count == 1, naming P1",
                               "sysTester.DirListing event 2 names P2 only",
                               "the two sysTester.Sha256 events of P2 carry the same hash",
                               "event productManager.ProductStored count == 1, naming P2",
                               NOERR]})
def delete_other(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256"):
        _seen[test_id] = args[0]
    if _is(command_name, "DELETE") and test_id in _seen:
        return [_seen[test_id]]
    return None


@planted_fault("second_capture_dropped", applies_to=["L5-1"], cls="stimulus", kind="insert",
               mechanism="LIST_PRODUCTS (accepted during a capture) is sent in place of the second CAPTURE; no command is rejected",
               fails={"L5-1": ["event productManager.CommandRejected(reason=CAPTURE_IN_PROGRESS) count == 1",
                               "exactly one command fails (cmdDisp.OpCodeError) and it is the rejected CAPTURE; every other command completes"]})
def second_capture_dropped(test_id, command_name, args):
    if _is(command_name, "LIST_DIR"):
        _seen[(test_id, "cap")] = 0  # every test starts with LIST_DIR: a repeated pass starts its count again
    if _is(command_name, "CAPTURE"):
        n = _seen.get((test_id, "cap"), 0) + 1
        _seen[(test_id, "cap")] = n
        if n == 2:
            return [("productManager.LIST_PRODUCTS", [])]
    return None


@planted_fault("corrupt_in_transfer", applies_to=["L5-5"], cls="uut-state", kind="insert",
               mechanism="sysTester.CORRUPT_PRODUCT(P) is inserted before DOWNLINK(P), after the first DUMP_SHA256: the product sent and kept differs from the product hashed; the transfer still runs, so the test's preconditions hold",
               fails={"L5-5": ["sha256 of record/raw/files/<P> == hash in the first sysTester.Sha256 event of P",
                               "the two sysTester.Sha256 events of P carry the same hash"]})
def corrupt_in_transfer(test_id, command_name, args):
    if _is(command_name, "DOWNLINK"):
        return [("sysTester.CORRUPT_PRODUCT", list(args)), (command_name, args)]
    return None


@planted_fault("downlink_existing", applies_to=["L6-1"], cls="stimulus", kind="rewrite",
               mechanism="DOWNLINK(Dp_missing.fxd) is sent with the name of the test's own product, taken from the preceding DUMP_SHA256 command; the product is sent",
               fails={"L6-1": ["event productManager.ProductNotFound(name=Dp_missing.fxd) count == 1",
                               "exactly one command fails (cmdDisp.OpCodeError) and it is the rejected DOWNLINK; every other command completes",
                               "event productManager.DownlinkStarted count == 0",
                               "ground CFDP transactions in the window: none"]})
def downlink_existing(test_id, command_name, args):
    if _is(command_name, "DUMP_SHA256"):
        _seen[(test_id, "p")] = args[0]
    if _is(command_name, "DOWNLINK") and (test_id, "p") in _seen:
        return [_seen[(test_id, "p")]]
    return None
