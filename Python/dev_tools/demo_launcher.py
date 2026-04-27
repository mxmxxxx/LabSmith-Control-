"""
Demo launcher for macOS — stubs the Windows-only uProcess_x64.pyd so the
GUI is fully interactive for customer screenshots / recordings.

Fake devices on "Connect Board":
    SPS01_1 (addr 1), SPS01_2 (addr 2), C4VM_10 (addr 10)

Hardware operations (Move, SwitchValves, Stop, Status) are stubbed to
complete instantly with success, so Run visualization actually progresses.

NOT for production. This file must not ship to the customer — it lives
in Python/dev_tools/ (a development-only directory) to keep it visibly
separated from the shipped Python/ modules. Running against real LabSmith
hardware requires the actual uProcess_x64.pyd driver.

Usage (from labsmith-repo/Python/):
    python3 dev_tools/demo_launcher.py
"""
import os
import sys
import types

# Make the parent Python/ directory importable so we can find LabsmithBoard.py
# and labsmith_gui.py from this dev_tools/ subdirectory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)


class _StubDevice:
    """Fake uProcess device. Returns deterministic names / success statuses."""

    def __init__(self, kind, addr):
        self._kind = kind  # "SPS01" | "C4VM" | "C4AM" | "C4PM" | "CEP01"
        self._addr = int(addr)
        self._name = f"{kind}_{self._addr}"

    # ---- identity ----
    def GetName(self):
        return self._name

    # ---- SPS01 setup ----
    def CmdGetDiameter(self):
        return 4.6
    def GetMaxFlowrate(self):
        return 1000.0
    def GetMinFlowrate(self):
        return 0.1
    def GetMaxVolume(self):
        return 500.0

    # ---- status ----
    def CmdGetStatus(self):
        return 0
    def IsOnline(self):
        return True
    def IsDone(self):
        return True
    def IsMoving(self):
        return False
    def IsStalled(self):
        return False
    def IsMovingIn(self):
        return False
    def IsMovingOut(self):
        return False
    def IsStuck(self):
        return False
    def CmdGetVolume(self):
        return 0.0
    def GetLastVolume(self):
        return 0.0

    # ---- SPS01 ops ----
    def CmdSetFlowrate(self, flowrate):
        return 0
    def CmdMoveToVolume(self, v):
        return 0
    def CmdStop(self):
        return 0
    def CmdSetStepDirection(self, push_out):
        return True
    def CmdMicrostep(self):
        return True
    def CmdMoveToPosition(self, pos):
        return True

    # ---- C4VM ops ----
    def CmdSetValves(self, v1, v2, v3, v4):
        return 0
    def CmdSetValveMotion(self, idx, code):
        return True
    def V1Missing(self):
        return False
    def V2Missing(self):
        return False
    def V3Missing(self):
        return False
    def V4Missing(self):
        return False
    def V1Status(self):
        return 0
    def V2Status(self):
        return 0
    def V3Status(self):
        return 0
    def V4Status(self):
        return 0

    # ---- C4AM ops ----
    def CmdGetTemps(self):
        return False


class _StubCEIB:
    """Stub for the uProcess CEIB (Equipment Interface Board)."""

    def InitConnection(self, port):
        return 0

    def CloseConnection(self):
        return 0

    def CmdCreateDeviceList(self):
        return (
            "<uProcess.CSyringe> address 1, "
            "<uProcess.CSyringe> address 2, "
            "<uProcess.C4VM> address 10"
        )

    def NewSPS01(self, addr):
        return _StubDevice("SPS01", addr)

    def New4VM(self, addr):
        return _StubDevice("C4VM", addr)

    def New4AM(self, addr):
        return _StubDevice("C4AM", addr)

    def New4PM(self, addr):
        return _StubDevice("C4PM", addr)

    def NewEP01(self, addr):
        return _StubDevice("CEP01", addr)


# Inject the stub as a module tree
_stub_mod = types.ModuleType("uProcess_x64.uProcess_x64")
_stub_mod.CEIB = _StubCEIB

_pkg = types.ModuleType("uProcess_x64")
_pkg.uProcess_x64 = _stub_mod
_pkg.__path__ = []

sys.modules["uProcess_x64"] = _pkg
sys.modules["uProcess_x64.uProcess_x64"] = _stub_mod


# ---- Launch the GUI ----
if __name__ == "__main__":
    from PyQt6 import QtWidgets, QtCore
    from labsmith_gui import MainWindow
    from LabsmithBoard import LabsmithBoard

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    def _demo_auto_connect():
        """Bypass the Connect button and inject a stub-backed board directly."""
        try:
            win._board = LabsmithBoard(port=1)
            win._populate_device_names()
            win._refresh_bus_modules_panel()
            win._sync_connection_ui()
            win._update_status_bar()
            print("[demo] auto-connected with 3 fake devices")
        except Exception as e:
            print(f"[demo] auto-connect failed: {e}")

    QtCore.QTimer.singleShot(150, _demo_auto_connect)
    sys.exit(app.exec())
