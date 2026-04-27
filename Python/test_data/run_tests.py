"""
Automated tests for Phase 1 features.
No Qt or hardware required — tests the serialization logic and validation rules.
"""
import json
import math
import os
import sys
import tempfile
import types

# ---- Helpers ----
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)
PASS_COUNT = 0
FAIL_COUNT = 0


def check(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  PASS: {name}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL: {name}  {detail}")


# ---- T1: Bug fix verification ----
print("\n=== T1: Bug Fix Verification ===")

# T1.1 MoveWait multi-pump dispatch. The original fix was an indentation tweak
# on `elif v4 != None and d5 == None:`. The 2026-04-19 Phase 1 terminal review
# replaced the four hand-rolled branches (1/2/3/4 pumps) with a data-driven
# pumps-list and a single unified CheckFirstDoneStopPauseWait handler, because
# the 3-pump / 4-pump listener-dispatcher branches were missing entirely and
# other paths had NameError/TypeError/missing-parentheses bugs. We now assert
# the post-rewrite contract instead of the old elif layout.
board_path = os.path.join(TEST_DIR, "..", "LabsmithBoard.py")
with open(board_path, "r", encoding="utf-8") as f:
    board_src = f.read()
check(
    "T1.1 MoveWait uses unified pumps-list dispatch",
    "pumps = [(self.FindIndexS(d), d, v) for (d, v) in pairs]" in board_src
    and "[time, pumps, t_s]" in board_src,
    "expected pumps-list construction + listener registration",
)
check(
    "T1.1 CheckFirstDoneStopPauseWait takes a single pumps list (len==3)",
    "if len(args) != 3:" in board_src,
    "dispatcher must validate arg count, not split by 5/8/10/12",
)
# Limit bug-regression checks to the MoveWait-related window (from `def MoveWait(`
# to the next `def ` at 4-space indent). The sibling functions `Move2` / `MulMove`
# / `SetValves` legitimately still carry the `elif v4 != None and d5 == None:`
# multi-device dispatch pattern — that pattern is only a bug inside MoveWait
# where the dispatcher branches were missing.
_mw_start = board_src.find("def MoveWait(")
assert _mw_start != -1, "MoveWait definition not found"
_mw_end = board_src.find("\n    def ", _mw_start + 1)
_mw_block = board_src[_mw_start:_mw_end]

check(
    "T1.1 MoveWait body no longer contains the legacy 4-pump elif branch",
    "elif v4 != None and d5 == None:" not in _mw_block,
)
check(
    "T1.1 BUG-2: no stray `difftime` identifier in MoveWait body",
    "difftime" not in _mw_block,
)
check(
    "T1.1 BUG-5: no `for j in len(` loop bug in MoveWait body",
    "for j in len(" not in _mw_block,
)
# BUG-3/4/6: these methods must always be called with (). Look for bare
# attribute references (method-name at end-of-line with no paren).
import re as _re
_bare_method_ref = _re.compile(
    r"^\s*self\.(StopBoard|PauseBoard|WaitStopBoard|UpdateBoard)\s*$",
    _re.MULTILINE,
)
_bare_hits = _bare_method_ref.findall(board_src)
check(
    "T1.1 BUG-3/4/6: no bare StopBoard/PauseBoard/WaitStopBoard/UpdateBoard references",
    not _bare_hits,
    f"unparenthesised hits: {_bare_hits}",
)

# T1.2 strftime
with open(board_path, "r", encoding="utf-8") as f:
    content = f.read()
check("T1.2 no strftime('#X')", "strftime('#X')" not in content)
check("T1.2 has strftime('%X')", "strftime('%X')" in content)

# T1.3 set(nodes)
gui_path = os.path.join(TEST_DIR, "..", "labsmith_gui.py")
with open(gui_path, "r", encoding="utf-8") as f:
    gui_content = f.read()
check("T1.3 no set(nodes)", "set(nodes)" not in gui_content)
check("T1.3 has node_id_set", "node_id_set" in gui_content)


# ---- T2: Save/Load round-trip ----
print("\n=== T2: Save/Load Round-Trip ===")

# Flow Designer round-trip
with open(os.path.join(TEST_DIR, "sample_flow.json"), "r", encoding="utf-8") as f:
    flow_data = json.load(f)

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
    json.dump(flow_data, tmp, indent=2)
    tmp_path = tmp.name

with open(tmp_path, "r", encoding="utf-8") as f:
    reloaded = json.load(f)
os.unlink(tmp_path)

check("T2.1 flow round-trip version", reloaded["version"] == 1)
check("T2.1 flow round-trip type", reloaded["type"] == "flow_designer")
check("T2.1 flow round-trip steps match", reloaded["steps"] == flow_data["steps"])
check("T2.1 flow step count", len(reloaded["steps"]) == 7)

# Flow Graph round-trip
with open(os.path.join(TEST_DIR, "sample_graph.json"), "r", encoding="utf-8") as f:
    graph_data = json.load(f)

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
    json.dump(graph_data, tmp, indent=2)
    tmp_path = tmp.name

with open(tmp_path, "r", encoding="utf-8") as f:
    reloaded = json.load(f)
os.unlink(tmp_path)

check("T2.2 graph round-trip nodes", reloaded["nodes"] == graph_data["nodes"])
check("T2.2 graph round-trip edges", reloaded["edges"] == graph_data["edges"])
check("T2.2 graph uses node IDs not indices",
      all("src_id" in e and "dst_id" in e for e in reloaded["edges"]))


# ---- T2: Error handling ----
print("\n=== T2: Error Handling ===")

# Missing fields should be skipped
with open(os.path.join(TEST_DIR, "bad_flow_missing_fields.json"), "r", encoding="utf-8") as f:
    bad_data = json.load(f)

_required = {
    "Move syringe": ("syringe", "flowrate", "volume"),
    "Wait": ("seconds",),
    "Switch valves": ("manifold", "v1", "v2", "v3", "v4"),
    "Stop board": (),
}
loaded = []
skipped = []
for i, s in enumerate(bad_data["steps"]):
    if not isinstance(s, dict) or s.get("type") not in _required:
        skipped.append(f"Step {i+1}: unknown type")
        continue
    missing = [k for k in _required[s["type"]] if k not in s]
    if missing:
        skipped.append(f"Step {i+1}: missing {missing}")
        continue
    loaded.append(s)

check("T2 bad flow: 3 valid steps loaded", len(loaded) == 3,
      f"got {len(loaded)}: {[s['type'] for s in loaded]}")
check("T2 bad flow: 3 steps skipped", len(skipped) == 3,
      f"got {len(skipped)}: {skipped}")

# Missing "steps" key
with open(os.path.join(TEST_DIR, "bad_flow_no_steps_key.json"), "r", encoding="utf-8") as f:
    no_steps = json.load(f)
check("T2 no-steps-key detected", "steps" not in no_steps)

# Broken edge reference
with open(os.path.join(TEST_DIR, "bad_graph_broken_edge.json"), "r", encoding="utf-8") as f:
    bad_graph = json.load(f)
id_set = {n["id"] for n in bad_graph["nodes"]}
broken = [e for e in bad_graph["edges"]
          if e["src_id"] not in id_set or e["dst_id"] not in id_set]
check("T2 broken edge detected", len(broken) == 1,
      f"expected 1 broken edge, got {len(broken)}")


# ---- T3: Validation logic ----
print("\n=== T3: Validation Logic ===")


def _is_valid_number(v):
    """Mirror labsmith_gui._is_valid_number: rejects bool + non-finite."""
    if isinstance(v, bool):
        return False
    if not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def validate_steps(steps):
    """Standalone reimplementation of _validate_steps_for_run (no Qt).
    Kept in sync with the production function in labsmith_gui.py.

    NOTE: this is intentionally a parallel implementation, not a call through
    to MainWindow._validate_steps_for_run (which returns (errors, warnings)
    since Phase 1.5). If you ever replace this with the real function, update
    every caller below to unpack the tuple — blindly swapping will turn
    ``len(errors)`` into ``len((errors, warnings))`` and silently break T3/T7.
    """
    errors = []
    known_types = {"Move syringe", "Switch valves", "Wait", "Stop board"}
    for i, step in enumerate(steps, start=1):
        t = step.get("type")
        tag = f"Step {i} ({t})"
        if t == "Move syringe":
            name = step.get("syringe", "")
            if not name:
                errors.append(f"{tag}: syringe empty")
            fr = step.get("flowrate", 0)
            if not _is_valid_number(fr) or fr <= 0:
                errors.append(f"{tag}: bad flowrate {fr!r}")
            vol = step.get("volume", 0)
            if not _is_valid_number(vol) or vol <= 0:
                errors.append(f"{tag}: bad volume {vol!r}")
        elif t == "Switch valves":
            name = step.get("manifold", "")
            if not name:
                errors.append(f"{tag}: manifold empty")
            for vk in ("v1", "v2", "v3", "v4"):
                v = step.get(vk, 0)
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v not in (0, 1):
                    errors.append(f"{tag}: bad {vk}={v!r}")
        elif t == "Wait":
            sec = step.get("seconds", 0)
            if not _is_valid_number(sec) or sec <= 0:
                errors.append(f"{tag}: bad seconds {sec!r}")
        elif t == "Stop board":
            pass
        else:
            errors.append(f"{tag}: unknown type {t!r}")
    return errors


# Valid steps
errs = validate_steps([
    {"type": "Move syringe", "syringe": "S1", "flowrate": 100, "volume": 50},
    {"type": "Wait", "seconds": 5.0},
    {"type": "Switch valves", "manifold": "M1", "v1": 0, "v2": 1, "v3": 0, "v4": 1},
    {"type": "Stop board"},
])
check("T3 valid steps: 0 errors", len(errs) == 0, f"got {errs}")

# NaN / Inf
errs = validate_steps([
    {"type": "Move syringe", "syringe": "S1", "flowrate": float("nan"), "volume": float("inf")},
])
check("T3 NaN flowrate rejected", any("flowrate" in e for e in errs))
check("T3 Inf volume rejected", any("volume" in e for e in errs))

errs = validate_steps([{"type": "Wait", "seconds": float("nan")}])
check("T3 NaN seconds rejected", len(errs) == 1)

errs = validate_steps([{"type": "Wait", "seconds": float("inf")}])
check("T3 Inf seconds rejected", len(errs) == 1)

# Edge cases
errs = validate_steps([
    {"type": "Move syringe", "syringe": "", "flowrate": 0, "volume": -1},
])
check("T3 empty syringe + zero flowrate + neg volume: 3 errors",
      len(errs) == 3, f"got {len(errs)}: {errs}")

errs = validate_steps([
    {"type": "Switch valves", "manifold": "M1", "v1": 0, "v2": 2, "v3": -1, "v4": 0},
])
check("T3 valve out of range: 2 errors", len(errs) == 2, f"got {len(errs)}: {errs}")

errs = validate_steps([{"type": "Wait", "seconds": 0}])
check("T3 Wait seconds=0 rejected", len(errs) == 1)

# Regression: numpy array fallback (would previously crash with
# "truth value ambiguous" when board.SPS01 is a populated np.array)
check("T3 no 'array or []' fallback in validation",
      " or []" not in gui_content.split("_validate_steps_for_run")[1].split("def ", 1)[0]
      if "_validate_steps_for_run" in gui_content else False)


# ---- T4: Visualization (code presence) ----
print("\n=== T4: Visualization (Code Presence) ===")

check("T4.1 _set_flow_row_color exists", "_set_flow_row_color" in gui_content)
check("T4.1 transparent reset before run", '"transparent"' in gui_content)
check("T4.2 graph pen reset with ACCENT", "it.setPen(QtGui.QPen(ACCENT, 2))" in gui_content)
check("T4 cyan #00a8e8 used", "#00a8e8" in gui_content)
check("T4 green #2ecc71 used", "#2ecc71" in gui_content)
check("T4 red #e74c3c used", "#e74c3c" in gui_content)


# ---- T5: Device table (code presence) ----
print("\n=== T5: Device Table (Code Presence) ===")

check("T5 device_table created", "self.device_table" in gui_content)
check("T5 _refresh_device_table exists", "def _refresh_device_table" in gui_content)
check("T5 reads SPS01", '"SPS01"' in gui_content)
check("T5 reads C4VM", '"C4VM"' in gui_content)
check("T5 prefers add_syr for address", "add_syr" in gui_content)


# ---- T7: Terminal review fixes (2026-04-19) ----
print("\n=== T7: Terminal Review Fixes (2026-04-19) ===")

# T7.1 bool穿透被拒绝
errs = validate_steps([
    {"type": "Move syringe", "syringe": "S1", "flowrate": True, "volume": 50},
])
check("T7.1 bool flowrate=True rejected",
      any("flowrate" in e for e in errs), f"got {errs}")

errs = validate_steps([{"type": "Wait", "seconds": True}])
check("T7.1 bool seconds=True rejected",
      len(errs) == 1, f"got {errs}")

errs = validate_steps([
    {"type": "Switch valves", "manifold": "M1",
     "v1": True, "v2": 0, "v3": False, "v4": 0},
])
check("T7.1 bool valve values rejected",
      len(errs) == 2, f"got {len(errs)}: {errs}")

# T7.2 unknown step type surfaced as validation error
errs = validate_steps([{"type": "Explode device"}])
check("T7.2 unknown step type raises validation error",
      any("unknown type" in e for e in errs), f"got {errs}")

# T7.3 JSON version check (source presence, not runtime — Qt not available)
check("T7.3 Flow load rejects unsupported version",
      "Unsupported flow file version" in gui_content)
check("T7.3 Graph load rejects unsupported version",
      "Unsupported graph file version" in gui_content)
check("T7.3 Both loaders tolerate missing version",
      gui_content.count("assuming v1") >= 2)

# T7.4 poll_hook / cancel_requested plumbing
check("T7.4 LabsmithBoard exposes poll_hook", "self.poll_hook = None" in board_src)
check("T7.4 LabsmithBoard exposes cancel_requested",
      "self.cancel_requested = False" in board_src)
check("T7.4 StopBoard signals cancellation",
      "self.cancel_requested = True" in board_src)
check("T7.4 GUI installs poll_hook before run",
      "_prepare_board_for_run" in gui_content
      and "poll_hook = QtWidgets.QApplication.processEvents" in gui_content)
check("T7.4 GUI checks run_cancelled in loops",
      gui_content.count("self._run_cancelled()") >= 2,
      "both _on_run_flow and _on_graph_run should check it")

# T7.5 CSyringe/CManifold raise on failure
syringe_path = os.path.join(TEST_DIR, "..", "CSyringe.py")
manifold_path = os.path.join(TEST_DIR, "..", "CManifold.py")
with open(syringe_path, "r", encoding="utf-8") as f:
    syringe_src = f.read()
with open(manifold_path, "r", encoding="utf-8") as f:
    manifold_src = f.read()
check("T7.5 CSyringe.MoveTo raises on offline",
      "is offline" in syringe_src and "raise RuntimeError" in syringe_src)
check("T7.5 CSyringe.MoveTo checks CmdSetFlowrate return value",
      "CmdSetFlowrate(" in syringe_src and "returned False" in syringe_src)
check("T7.5 CSyringe.Updating cooperates with poll_hook",
      "poll_hook" in syringe_src and "cancel_requested" in syringe_src)
check("T7.5 CSyringe.Updating has safety timeout",
      "timed out after" in syringe_src)
check("T7.5 CManifold.SwitchValves raises on offline",
      "is offline" in manifold_src and "raise RuntimeError" in manifold_src)
check("T7.5 CManifold.SwitchValves cooperates with poll_hook",
      "poll_hook" in manifold_src and "cancel_requested" in manifold_src)

# T7.6 JSON size cap
check("T7.6 MAX_FLOW_ITEMS constant present",
      "MAX_FLOW_ITEMS" in gui_content)
check("T7.6 Flow load truncates oversized files",
      "only the first" in gui_content and "will be loaded" in gui_content)

# T7.7 Graph duplicate node id handling
check("T7.7 Graph load skips duplicate node ids",
      "duplicate id" in gui_content)

# T7.8 demo_launcher.py moved to dev_tools/
_demo_src = os.path.join(TEST_DIR, "..", "demo_launcher.py")
_demo_dev = os.path.join(TEST_DIR, "..", "dev_tools", "demo_launcher.py")
check("T7.8 demo_launcher.py removed from Python/ root",
      not os.path.exists(_demo_src))
check("T7.8 demo_launcher.py placed under dev_tools/",
      os.path.exists(_demo_dev))

# T7.9 Python 3.9 compatibility (no X | None attribute annotations)
import re as _re_py39
_bad_pipe_none = _re_py39.findall(r"\|\s*None", gui_content)
check("T7.9 no `X | None` in labsmith_gui.py (Python 3.9 compat)",
      not _bad_pipe_none, f"found {len(_bad_pipe_none)} instances")

# T7.10 sync-connect escape hatch
check("T7.10 LABSMITH_SYNC_CONNECT env var honoured",
      "LABSMITH_SYNC_CONNECT" in gui_content)


# ---- T8: Phase 1.5 device mapping + diagnostics ----
print("\n=== T8: Phase 1.5 Device Mapping ===")


class _StubConnectedDevice:
    # Stub matches production attribute topology: CSyringe/CManifold both store
    # the address as self.add_syr (CManifold's __init__ parameter name was kept
    # aligned with CSyringe during Phase 1). LabsmithBoard.connected_devices()
    # uses a getattr fallback chain (add_man -> add_syr -> address) on C4VM
    # entries, so exercising the fallback here keeps the test honest.
    def __init__(self, name, addr):
        self.name = name
        self.add_syr = addr


_phase15_devices = [
    {"type": "syringe", "index": 0, "addr": 1, "name": "Pump1"},
    {"type": "syringe", "index": 1, "addr": 2, "name": "Pump2"},
    {"type": "manifold", "index": 0, "addr": 32, "name": "Manifold (Addr 32)"},
]

# LabsmithBoard imports the Windows-only uProcess_x64.pyd at module import time.
# Phase 1.5 tests only need class methods on __new__ instances, so provide a
# small import-time stub on non-Windows CI/dev machines.
if "uProcess_x64.uProcess_x64" not in sys.modules:
    _stub_u_mod = types.ModuleType("uProcess_x64.uProcess_x64")
    _stub_u_mod.CEIB = object
    _stub_u_pkg = types.ModuleType("uProcess_x64")
    _stub_u_pkg.uProcess_x64 = _stub_u_mod
    _stub_u_pkg.__path__ = []
    sys.modules["uProcess_x64"] = _stub_u_pkg
    sys.modules["uProcess_x64.uProcess_x64"] = _stub_u_mod

try:
    from device_registry import resolve_device_ref
    _device_registry_import_error = None
except Exception as e:
    resolve_device_ref = None
    _device_registry_import_error = e

check("T8.1 device_registry imports",
      resolve_device_ref is not None, f"import error: {_device_registry_import_error}")
if resolve_device_ref is not None:
    _exact = resolve_device_ref("syringe", "Pump1", _phase15_devices)
    _addr = resolve_device_ref("manifold", "32", _phase15_devices)
    _legacy_s = resolve_device_ref("syringe", "SPS01_1", _phase15_devices)
    _legacy_m = resolve_device_ref("manifold", "C4VM_10", _phase15_devices)
    _none = resolve_device_ref("syringe", "MissingPump", _phase15_devices)
    check("T8.1 exact-name match",
          _exact is not None and _exact.get("name") == "Pump1"
          and _exact.get("matched_via") == "exact", f"got {_exact}")
    check("T8.1 addr string match",
          _addr is not None and _addr.get("name") == "Manifold (Addr 32)"
          and _addr.get("matched_via") == "addr", f"got {_addr}")
    check("T8.1 syringe legacy index fallback",
          _legacy_s is not None and _legacy_s.get("name") == "Pump1"
          and _legacy_s.get("matched_via") == "legacy_index", f"got {_legacy_s}")
    check("T8.1 manifold legacy fallback maps to connected C4VM",
          _legacy_m is not None and _legacy_m.get("name") == "Manifold (Addr 32)"
          and _legacy_m.get("matched_via") == "legacy_index", f"got {_legacy_m}")
    check("T8.1 unresolved reference returns None", _none is None, f"got {_none}")
else:
    for _name in (
        "T8.1 exact-name match",
        "T8.1 addr string match",
        "T8.1 syringe legacy index fallback",
        "T8.1 manifold legacy fallback maps to connected C4VM",
        "T8.1 unresolved reference returns None",
    ):
        check(_name, False, "device_registry import failed")

try:
    from LabsmithBoard import LabsmithBoard
    _stub_board = LabsmithBoard.__new__(LabsmithBoard)
    _stub_board.SPS01 = [
        _StubConnectedDevice("Pump1", 1),
        _StubConnectedDevice("Pump2", 2),
    ]
    _stub_board.C4VM = [_StubConnectedDevice("Manifold (Addr 32)", 32)]
    _connected = _stub_board.connected_devices()
    _connected_error = None
except Exception as e:
    _connected = []
    _connected_error = e

check("T8.2 connected_devices returns 3 devices",
      len(_connected) == 3, f"got {_connected}; error={_connected_error}")
check("T8.2 connected_devices fields complete",
      bool(_connected)
      and all({"type", "index", "addr", "name"}.issubset(d.keys()) for d in _connected),
      f"got {_connected}")
check("T8.2 connected_devices keeps hardware names with spaces",
      any(d.get("name") == "Manifold (Addr 32)" for d in _connected),
      f"got {_connected}")

try:
    import labsmith_gui as _gui_mod

    class _ValidationBoard:
        def connected_devices(self):
            return list(_phase15_devices)

    _win = _gui_mod.MainWindow.__new__(_gui_mod.MainWindow)
    _win._board = _ValidationBoard()
    _legacy_errors, _legacy_warnings = _gui_mod.MainWindow._validate_device_refs(
        _win,
        [{"type": "Move syringe", "syringe": "SPS01_1"}],
        "Step",
    )
    _missing_errors, _missing_warnings = _gui_mod.MainWindow._validate_device_refs(
        _win,
        [{"type": "Switch valves", "manifold": "NonExistent"}],
        "Step",
    )
    _validation_error = None
except Exception as e:
    _legacy_errors, _legacy_warnings = [], []
    _missing_errors, _missing_warnings = [], []
    _validation_error = e

check("T8.3 _validate_device_refs legacy fallback warns without error",
      not _legacy_errors and len(_legacy_warnings) == 1,
      f"errors={_legacy_errors}, warnings={_legacy_warnings}, error={_validation_error}")
check("T8.4 _validate_device_refs missing device errors with candidates",
      len(_missing_errors) == 1
      and "NonExistent" in _missing_errors[0]
      and "Manifold (Addr 32)" in _missing_errors[0],
      f"errors={_missing_errors}, warnings={_missing_warnings}, error={_validation_error}")

try:
    from CSyringe import CSyringe

    class _SyringeMoveFalseDevice:
        def CmdSetFlowrate(self, _flowrate):
            return True

        def CmdMoveToVolume(self, _volume):
            return False

    _syr = CSyringe.__new__(CSyringe)
    _syr.device = _SyringeMoveFalseDevice()
    _syr.name = "Pump1"
    _syr.add_syr = 1
    _syr.address = 1
    _syr.FlagIsOnline = True
    _syr.FlagIsStalled = False
    _syr.FlagIsDone = True
    _syr.FlagReady = True
    # Phase 1.6: pre-check reads these; set well outside the test parameters
    # (flowrate=123, volume=25) so we still reach the CmdMoveToVolume False
    # branch that T8.5 actually wants to exercise.
    _syr.maxVolume = 1000.0
    _syr.maxFlowrate = 1000.0
    _syr.minFlowrate = 1.0
    _syr.UpdateStatus = lambda: None
    try:
        CSyringe.MoveTo(_syr, 123.0, 25.0)
        _syr_msg = ""
    except RuntimeError as e:
        _syr_msg = str(e)
except Exception as e:
    _syr_msg = f"setup failed: {e}"

_syr_expected_fields = ("name=", "addr=", "online=", "stalled=", "ready=", "flowrate=", "volume=")
check("T8.5 CSyringe.MoveTo False message includes context fields",
      all(field in _syr_msg for field in _syr_expected_fields),
      f"message={_syr_msg!r}")

try:
    from CManifold import CManifold

    class _ManifoldFalseDevice:
        def CmdSetValves(self, _v1, _v2, _v3, _v4):
            return False

    _man = CManifold.__new__(CManifold)
    _man.device = _ManifoldFalseDevice()
    _man.name = "Manifold (Addr 32)"
    _man.add_syr = 32
    _man.address = 32
    _man.FlagIsOnline = True
    _man.FlagIsStuck = False
    _man.FlagIsDone = True
    _man.FlagReady = True
    _man.UpdateStatus = lambda: None
    try:
        CManifold.SwitchValves(_man, 1, 0, 0, 1)
        _man_msg = ""
    except RuntimeError as e:
        _man_msg = str(e)
except Exception as e:
    _man_msg = f"setup failed: {e}"

_man_expected_fields = ("name=", "addr=", "online=", "ready=", "v1=", "v2=", "v3=", "v4=")
check("T8.6 CManifold.SwitchValves False message includes context fields",
      all(field in _man_msg for field in _man_expected_fields),
      f"message={_man_msg!r}")

check("T8.7 Flow Designer device inputs are editable combo boxes",
      "def _build_device_combo" in gui_content
      and "_build_device_combo(\"syringe\"" in gui_content
      and "_build_device_combo(\"manifold\"" in gui_content,
      "expected shared editable combo builder in labsmith_gui.py")
check("T8.7 dropdown refresh method exists",
      "def _refresh_device_dropdowns" in gui_content
      and "connected_devices" in gui_content,
      "expected refresh method backed by connected_devices()")
check("T8.8 runtime execution resolves legacy refs before board calls",
      "resolve_device_ref" in gui_content
      and "_resolve_runtime_device" in gui_content,
      "expected _execute_one_flow_step to resolve legacy references")


# ---- T9: Customer demo scenario files ----
print("\n=== T9: Customer Demo Scenario ===")

_demo_flow = os.path.join(TEST_DIR, "demo_scenario_flow.json")
_demo_graph = os.path.join(TEST_DIR, "demo_scenario_graph.json")
_demo_readme = os.path.join(TEST_DIR, "DEMO_README.md")

check("T9 demo_scenario_flow.json exists", os.path.exists(_demo_flow))
check("T9 demo_scenario_graph.json exists", os.path.exists(_demo_graph))
check("T9 DEMO_README.md exists", os.path.exists(_demo_readme))

with open(_demo_flow) as f:
    _flow_data = json.load(f)
check("T9 demo flow has version=1", _flow_data.get("version") == 1)
check("T9 demo flow has type=flow_designer",
      _flow_data.get("type") == "flow_designer")
check("T9 demo flow has 8 steps", len(_flow_data.get("steps", [])) == 8)
_flow_errs = validate_steps(_flow_data["steps"])
check("T9 demo flow passes standalone validation",
      len(_flow_errs) == 0, f"got {_flow_errs}")

with open(_demo_graph) as f:
    _graph_data = json.load(f)
check("T9 demo graph has version=1", _graph_data.get("version") == 1)
check("T9 demo graph has type=flow_graph",
      _graph_data.get("type") == "flow_graph")
check("T9 demo graph has 8 nodes and 7 edges",
      len(_graph_data.get("nodes", [])) == 8
      and len(_graph_data.get("edges", [])) == 7)

# Graph edges must reference existing node ids (pre-run check mirrors the GUI
# load path behaviour for broken edges).
_node_ids = {n["id"] for n in _graph_data["nodes"]}
_bad_edges = [
    e for e in _graph_data["edges"]
    if e.get("src_id") not in _node_ids or e.get("dst_id") not in _node_ids
]
check("T9 demo graph edges reference existing nodes",
      not _bad_edges, f"broken edges: {_bad_edges}")

# Single chain: every node except n7 has an outgoing edge, every node except
# n0 has an incoming edge, and the chain visits each node exactly once.
_out_counts = {n["id"]: 0 for n in _graph_data["nodes"]}
_in_counts = {n["id"]: 0 for n in _graph_data["nodes"]}
for e in _graph_data["edges"]:
    _out_counts[e["src_id"]] += 1
    _in_counts[e["dst_id"]] += 1
_roots = [nid for nid, c in _in_counts.items() if c == 0]
_leaves = [nid for nid, c in _out_counts.items() if c == 0]
check("T9 demo graph is a single chain (1 root, 1 leaf)",
      len(_roots) == 1 and len(_leaves) == 1,
      f"roots={_roots}, leaves={_leaves}")

# Demo nodes should also pass step-level validation.
_graph_errs = validate_steps(_graph_data["nodes"])
check("T9 demo graph nodes pass standalone validation",
      len(_graph_errs) == 0, f"got {_graph_errs}")


# ---- T10: Syringe range pre-checks (Phase 1.6) ----
print("\n=== T10: Syringe Range Pre-Checks ===")

# Source-grep style like T7.5 — keeps the suite importable without uProcess_x64
# on non-Windows dev machines. The pre-checks must sit *before* the driver
# calls so the operator gets a specific message instead of "returned False".
check("T10.1 MoveTo checks volume against maxVolume",
      "exceeds installed syringe capacity" in syringe_src
      and "maxVolume=" in syringe_src)
check("T10.2 MoveTo checks flowrate against maxFlowrate",
      "exceeds maxFlowrate=" in syringe_src)
check("T10.3 MoveTo checks flowrate against minFlowrate",
      "below minFlowrate=" in syringe_src)
check("T10.4 _move_context exposes maxVolume in error messages",
      "maxVolume={self.maxVolume}" in syringe_src)
check("T10.5 _move_context exposes flowrate_range in error messages",
      "flowrate_range=" in syringe_src)

# Order check: pre-check block must precede the CmdSetFlowrate call so we
# never reach the bare-False branch for out-of-range inputs.
_idx_precheck = syringe_src.find("exceeds installed syringe capacity")
_idx_setflow = syringe_src.find("CmdSetFlowrate(flowrate)")
check("T10.6 volume pre-check runs before CmdSetFlowrate",
      _idx_precheck > 0 and _idx_setflow > 0 and _idx_precheck < _idx_setflow)

# Guard: empty-list / None maxVolume (uninitialised or probe failure) must
# *not* trip the check (the vendor API returns [] as a sentinel in __init__).
check("T10.7 pre-check skips when maxVolume is unset/empty",
      "_is_positive_number" in syringe_src)


# ---- Summary ----
print(f"\n{'='*40}")
print(f"TOTAL: {PASS_COUNT} passed, {FAIL_COUNT} failed")
if FAIL_COUNT == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
