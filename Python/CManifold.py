import numpy as np
import time
from datetime import datetime

from output_log import output_txt_path


def _pyd_read(obj, attr):
    a = getattr(obj, attr, None)
    if a is None:
        return None
    return a() if callable(a) else a


class CManifold:

    def __init__(self, Lboard, add_syr):
        
        self.Lboard = Lboard
        self.add_syr = add_syr
        
        # General info
        self.device = []
        self.name = []
        self.address = []
        
        # Flags
        # self.FlagIsMoving = False
        self.FlagIsDone = True
        self.FlagIsOnline = False
        self.FlagIsMoving = False
        self.FlagIsStuck = False
        self.FlagReady = True
        self.V_missing = [False, False, False, False]
        self.V_status = [None, None, None, None]

        # Clocks
        self.ClockStartCmd = None
        self.ClockStopCmd = None

        ### Constructor
        self.device = self.Lboard.eib.New4VM(np.int8(self.add_syr))
        self.name= self.device.GetName()
        
        self.UpdateStatus()

        with open(output_txt_path(), "a") as OUTPUT:
            comment = f"Manifold {self.name} loaded."
            OUTPUT.write(comment + "\n")
            print(comment)

    ### UpdateStaus
    def UpdateStatus(self):
        self.device.CmdGetStatus()
        self.FlagIsDone = self.device.IsDone()
        self.FlagIsOnline = self.device.IsOnline()
        try:
            self.FlagIsMoving = self.device.IsMoving()
        except Exception:
            self.FlagIsMoving = False
        try:
            self.FlagIsStuck = self.device.IsStuck()
        except Exception:
            self.FlagIsStuck = False
        for i in range(1, 5):
            try:
                self.V_missing[i - 1] = bool(_pyd_read(self.device, f"V{i}Missing"))
            except Exception:
                self.V_missing[i - 1] = False
            try:
                self.V_status[i - 1] = _pyd_read(self.device, f"V{i}Status")
            except Exception:
                self.V_status[i - 1] = None

    ### Switch Valves
    def SwitchValves(self,v1,v2,v3,v4):
            """CmdSetValves: 0=no change, 1=position A, 2=closed, 3=position B (uProcess)."""
            self.device.CmdSetValves(np.int8(v1),np.int8(v2),np.int8(v3),np.int8(v4))
            self.FlagReady = False
            self.displayswitch(v1,v2,v3,v4)
            while self.FlagIsDone == False:
                self.UpdateStatus()
                time.sleep(0.01)
            if self.FlagIsDone == True:
                self.displayswitchstop()

    def SetValvesNative(self, v1, v2, v3, v4):
        """Set all four valves with native semantics (0–3); waits until done."""
        self.SwitchValves(v1, v2, v3, v4)

    def SetSingleValveMotion(self, valve_index_1_to_4: int, motion_code: int) -> bool:
        """CmdSetValveMotion: valve 1=V1…; motion uses same 0–3 scheme as CmdSetValves where applicable."""
        return bool(self.device.CmdSetValveMotion(int(valve_index_1_to_4), int(motion_code)))

    ### Display switch start
    def displayswitch(self,v1,v2,v3,v4):
        self.ClockStartCmd = datetime.now()
        self.UpdateStatus()
        with open(output_txt_path(), "a") as OUTPUT:
            comment = f"{self.ClockStartCmd.strftime('%X')} 4VM {self.name} is switching valves to {v1}, {v2}, {v3}, {v4}."
            OUTPUT.write(comment + "\n")
            print(comment)

    ### Display switch stop
    def displayswitchstop(self):
        self.ClockStopCmd = datetime.now()
        # self.UpdateStatus()
        with open(output_txt_path(), "a") as OUTPUT:
            comment = f"{self.ClockStopCmd.strftime('%X')} 4VM {self.name} is done."
            OUTPUT.write(comment + "\n")
            print(comment)
        self.FlagReady = True

