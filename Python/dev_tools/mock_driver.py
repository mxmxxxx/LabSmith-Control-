"""Software mock of the vendor uProcess_x64 extension for macOS/Linux demos.

The real driver is a Windows-only compiled extension (.pyd). This module
registers a pure-Python stand-in into sys.modules *before* labsmith_gui /
LabsmithBoard import it, so the GUI can be started and driven through the full
demo_scenario flow with no hardware attached.

Behaviour is intentionally "happy path": every command returns True, moves
complete after a short interpolated duration based on flowrate/volume, and
device names match what real hardware reports (`Pump1`, `Pump2`,
`Manifold (Addr 32)`) so the Phase 1.5 legacy fallback (`SPS01_1` -> `Pump1`,
etc.) resolves correctly.
"""

import sys
import time
import types


# ---------- Fake devices ----------

class _FakeSyringeDevice:
    def __init__(self, addr, name, max_volume=1000.0):
        self.addr = addr
        self.name = name
        self._max_volume = float(max_volume)
        self._volume = 0.0
        self._volume_at_start = 0.0
        self._target = 0.0
        self._flowrate = 0.0
        self._move_start = None
        self._move_duration = 0.0

    def GetName(self): return self.name
    def CmdGetDiameter(self): return 4.6
    def GetMaxFlowrate(self): return 1000.0
    def GetMinFlowrate(self): return 0.1
    def GetMaxVolume(self): return self._max_volume

    def CmdGetStatus(self): return True

    def _progress(self):
        if self._move_start is None:
            return 1.0
        if self._move_duration <= 0:
            return 1.0
        t = time.monotonic() - self._move_start
        return min(1.0, t / self._move_duration)

    def IsMoving(self):
        if self._move_start is None:
            return False
        if self._progress() >= 1.0:
            # latch completion
            self._volume = self._target
            self._move_start = None
            return False
        return True

    def IsDone(self): return not self.IsMoving()
    def IsOnline(self): return True
    def IsStalled(self): return False

    def IsMovingIn(self):
        return self.IsMoving() and self._target > self._volume_at_start

    def IsMovingOut(self):
        return self.IsMoving() and self._target < self._volume_at_start

    def CmdGetVolume(self):
        if self._move_start is None:
            return self._volume
        p = self._progress()
        return self._volume_at_start + (self._target - self._volume_at_start) * p

    def GetLastVolume(self):
        return self._volume

    def CmdSetFlowrate(self, flowrate):
        self._flowrate = float(flowrate)
        return True

    def CmdMoveToVolume(self, volume):
        volume = float(volume)
        if self._flowrate <= 0:
            return False
        # real duration = |dv| / flowrate (min). Accelerate by 4x so the demo
        # feels alive but still shows a visible progress window.
        seconds = abs(volume - self._volume) / self._flowrate * 60.0 / 4.0
        self._move_duration = max(0.5, seconds)
        self._volume_at_start = self._volume
        self._target = volume
        self._move_start = time.monotonic()
        return True

    def CmdStop(self):
        if self._move_start is not None:
            # snapshot current position as the new resting volume
            self._volume = self.CmdGetVolume()
            self._move_start = None
        return True

    def CmdSetStepDirection(self, push_out): return True
    def CmdMicrostep(self): return True
    def CmdMoveToPosition(self, pos): return True


class _FakeManifoldDevice:
    def __init__(self, addr, name):
        self.addr = addr
        self.name = name
        self.v = (0, 0, 0, 0)
        self._busy_until = 0.0

    def GetName(self): return self.name
    def CmdGetStatus(self): return True
    def IsDone(self): return time.monotonic() >= self._busy_until
    def IsOnline(self): return True
    def IsMoving(self): return not self.IsDone()
    def IsStuck(self): return False

    def CmdSetValves(self, v1, v2, v3, v4):
        self.v = (v1, v2, v3, v4)
        self._busy_until = time.monotonic() + 0.4
        return True

    def CmdSetValveMotion(self, idx, motion): return True
    def CmdStop(self): return True


class _FakeStubDevice:
    """Minimal stub for C4AM / C4PM / CEP01 — not used by the demo flow but
    kept so Load() does not blow up if the device list mentions them."""

    def __init__(self, addr, name):
        self.addr = addr
        self.name = name

    def GetName(self): return self.name
    def CmdGetStatus(self): return True
    def IsDone(self): return True
    def IsOnline(self): return True
    def CmdStop(self): return True
    def CmdGetTemps(self): return True


# ---------- CEIB facade ----------

class CEIB:
    def __init__(self):
        # Two syringes + one manifold matches the demo_scenario requirements
        # and also the customer's real hardware topology ("Pump1"/"Pump2" +
        # "Manifold (Addr 32)").
        self._syringes = [
            _FakeSyringeDevice(1, "Pump1"),
            _FakeSyringeDevice(2, "Pump2"),
        ]
        self._manifolds = [_FakeManifoldDevice(32, "Manifold (Addr 32)")]

    def InitConnection(self, port):
        # Vendor convention: 0 = success
        return 0

    def CloseConnection(self):
        return 0

    def CmdCreateDeviceList(self):
        parts = []
        for s in self._syringes:
            parts.append(f"<uProcess.CSyringe> address {s.addr}")
        for m in self._manifolds:
            parts.append(f"<uProcess.C4VM> address {m.addr}")
        return ", ".join(parts)

    def NewSPS01(self, addr):
        a = int(addr)
        for s in self._syringes:
            if s.addr == a:
                return s
        s = _FakeSyringeDevice(a, f"Pump{a}")
        self._syringes.append(s)
        return s

    def New4VM(self, addr):
        a = int(addr)
        for m in self._manifolds:
            if m.addr == a:
                return m
        m = _FakeManifoldDevice(a, f"Manifold (Addr {a})")
        self._manifolds.append(m)
        return m

    def New4AM(self, addr): return _FakeStubDevice(int(addr), f"AM{int(addr)}")
    def New4PM(self, addr): return _FakeStubDevice(int(addr), f"PM{int(addr)}")
    def NewEP01(self, addr): return _FakeStubDevice(int(addr), f"EP{int(addr)}")


# ---------- Installer ----------

def install():
    """Register a fake `uProcess_x64` package + submodule in sys.modules.

    Real layout on Windows:
        uProcess_x64              -> package (directory with __init__.py)
        uProcess_x64.uProcess_x64 -> compiled submodule (.pyd) exposing CEIB

    `from uProcess_x64 import uProcess_x64` therefore pulls the submodule,
    and `uProcess_x64.CEIB()` instantiates the controller. We mirror that
    structure here so LabsmithBoard.py imports transparently.
    """
    existing = sys.modules.get("uProcess_x64")
    if existing is not None and getattr(existing, "_is_mock", False):
        return existing

    pkg = types.ModuleType("uProcess_x64")
    pkg.__path__ = []
    pkg._is_mock = True

    sub = types.ModuleType("uProcess_x64.uProcess_x64")
    sub.CEIB = CEIB
    sub._is_mock = True

    pkg.uProcess_x64 = sub
    sys.modules["uProcess_x64"] = pkg
    sys.modules["uProcess_x64.uProcess_x64"] = sub
    return pkg
