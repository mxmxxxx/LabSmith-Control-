"""Thin wrappers for uProcess device types beyond CSyringe / C4VM (C4AM, C4PM, CEP01)."""

import numpy as np

from output_log import output_txt_path


class C4AnalogModule:
    """4-channel analog / sensor module (uProcess C4AM)."""

    def __init__(self, Lboard, addr):
        self.Lboard = Lboard
        self.address = int(addr)
        self.device = Lboard.eib.New4AM(np.int8(addr))
        self.name = self.device.GetName()
        self.FlagIsDone = True
        self.FlagIsOnline = False
        self.UpdateStatus()
        with open(output_txt_path(), "a") as f:
            line = f"C4AM {self.name} (Addr {self.address}) loaded.\n"
            f.write(line)
            print(line.strip())

    def UpdateStatus(self):
        self.device.CmdGetStatus()
        self.FlagIsDone = self.device.IsDone()
        self.FlagIsOnline = self.device.IsOnline()

    def Stop(self):
        self.device.CmdStop()
        self.UpdateStatus()

    def ReadTemps(self) -> bool:
        """Trigger temperature / compensation read (see uProcess CmdGetTemps)."""
        return bool(self.device.CmdGetTemps())


class C4PowerModule:
    """4-channel power module (uProcess C4PM)."""

    def __init__(self, Lboard, addr):
        self.Lboard = Lboard
        self.address = int(addr)
        self.device = Lboard.eib.New4PM(np.int8(addr))
        self.name = self.device.GetName()
        self.FlagIsDone = True
        self.FlagIsOnline = False
        self.UpdateStatus()
        with open(output_txt_path(), "a") as f:
            line = f"C4PM {self.name} (Addr {self.address}) loaded.\n"
            f.write(line)
            print(line.strip())

    def UpdateStatus(self):
        self.device.CmdGetStatus()
        self.FlagIsDone = self.device.IsDone()
        self.FlagIsOnline = self.device.IsOnline()

    def Stop(self):
        self.device.CmdStop()
        self.UpdateStatus()


class CEP01Board:
    """EP01-style power / timer module (uProcess CEP01)."""

    def __init__(self, Lboard, addr):
        self.Lboard = Lboard
        self.address = int(addr)
        self.device = Lboard.eib.NewEP01(np.int8(addr))
        self.name = self.device.GetName()
        self.FlagIsDone = True
        self.FlagIsOnline = False
        self.UpdateStatus()
        with open(output_txt_path(), "a") as f:
            line = f"CEP01 {self.name} (Addr {self.address}) loaded.\n"
            f.write(line)
            print(line.strip())

    def UpdateStatus(self):
        self.device.CmdGetStatus()
        self.FlagIsDone = self.device.IsDone()
        self.FlagIsOnline = self.device.IsOnline()

    def Stop(self):
        self.device.CmdStop()
        self.UpdateStatus()
