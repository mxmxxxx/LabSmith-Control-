import numpy as np
from datetime import datetime
import time

from output_log import output_txt_path

class CSyringe:

    def __init__(self, Lboard, add_syr):
        self.Lboard = Lboard
        self.add_syr = add_syr
        
        # General info
        self.device = []
        self.name = []
        self.address = []
        
        # Syringes info
        self.maxFlowrate = []
        self.minFlowrate = []
        self.Flowrate = []
        self.diameter = []
        self.maxVolume = []
        self.volume_ul = None

        # Flags
        self.FlagIsMoving = False
        self.FlagIsDone = True
        self.FlagIsOnline = False
        self.FlagIsStalled = False
        self.FlagIsMovingIn = False
        self.FlagIsMovingOut = False
        self.FlagReady = True
        self.FlagStop = False
                
        # Clocks
        self.ClockStartCmd = None
        self.ClockStopCmd = None

        ### Constructor
        self.device = self.Lboard.eib.NewSPS01(np.int8(add_syr))
        self.name = self.device.GetName()
        self.diameter = self.device.CmdGetDiameter()
        self.maxFlowrate = self.device.GetMaxFlowrate()
        self.minFlowrate = self.device.GetMinFlowrate()
        self.maxVolume = self.device.GetMaxVolume()
        

        self.UpdateStatus()
        
        with open(output_txt_path(), "a") as OUTPUT:
            comment = f"Syringe {self.name} loaded."
            OUTPUT.write(comment + "\n")
            print(comment)


        ## Events
        self._listeners = {event: dict() for event in ["MovingState", "FlagStop"]}

        self.addlistener('MovingState', 'listener', self.Updating, []) #it listens for the self.FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. self.Ready = true again.
        self.addlistener('FlagStop', 'listener_stop', self.StopSyr, []) #it listens for the self.FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. self.Ready = true again.
        
        
        
    ## Add Listeners to Events
    def addlistener(self, event, listener, callback, args):
        if callable(callback):
            self._listeners[event][listener] = [callback, args]

    ## Trigger Events
    def notify(self, event):
        for listener, [callback, args] in self._listeners[event].items():
            callback(*args)

    ### UpdateStaus
    def UpdateStatus(self):
        self.device.CmdGetStatus()
        self.FlagIsDone = self.device.IsDone()
        self.FlagIsMoving = self.device.IsMoving()
        self.FlagIsOnline = self.device.IsOnline()
        self.FlagIsStalled = self.device.IsStalled()
        self.FlagIsMovingIn = self.device.IsMovingIn()
        self.FlagIsMovingOut = self.device.IsMovingOut()
        try:
            self.volume_ul = float(self.device.CmdGetVolume())
        except Exception:
            try:
                self.volume_ul = float(self.device.GetLastVolume())
            except Exception:
                self.volume_ul = None
        if self.FlagIsStalled == True:
            with open(output_txt_path(), "a") as OUTPUT:
                comment = f"ERROR: Syringe {self.name} is stalled."
                OUTPUT.write(comment + "\n")
                print(comment)

    ### MoveTo        
    def MoveTo(self,flowrate,volume):
        if self.FlagIsDone == True:
            self.device.CmdSetFlowrate(flowrate)
            self.Flowrate = flowrate
            self.device.CmdMoveToVolume(volume)
            self.FlagReady = False
            self.displaymovement()
            if self.FlagIsMoving == True:
                self.notify('MovingState')

    ### Display movement In and Out on cmdwindow              
    def displaymovement(self):
        self.ClockStartCmd = datetime.now()
        self.UpdateStatus()
        if self.FlagIsMovingIn == True:
            with open(output_txt_path(), "a") as OUTPUT:
                comment = f"{self.ClockStartCmd.strftime('%X')} Syringe {self.name} is pulling at {self.Flowrate} ul/min."
                OUTPUT.write(comment + "\n")
                print(comment)
        elif self.FlagIsMovingOut == True:
            with open(output_txt_path(), "a") as OUTPUT:
                comment = f"{self.ClockStartCmd.strftime('%X')} Syringe {self.name} is pushing at {self.Flowrate} ul/min."
                OUTPUT.write(comment + "\n")
                print(comment)
            
    ### Display stop movement on cmdwindow             
    def displaymovementstop(self):
        self.ClockStopCmd = datetime.now()
        with open(output_txt_path(), "a") as OUTPUT:
                comment = f"{self.ClockStopCmd.strftime('%X')} Syringe {self.name} is done."
                OUTPUT.write(comment + "\n")
                print(comment)
        self.FlagReady = True
    
    ### Listener function
    def Updating(self):
        if self.FlagIsMoving == True:
            while self.FlagIsMoving == True:
                self.UpdateStatus()
                time.sleep(0.01)
            if self.FlagIsDone == True:
                self.displaymovementstop()

    def StopSyr(self):
        if self.FlagStop == True:
            self.device.CmdStop()
            self.FlagStop = False

    ### Stop
    def Stop(self):
        self.device.CmdStop()
        self.UpdateStatus()
        self.FlagReady = True

    ### Manual microstepping (uProcess: CmdSetStepDirection + CmdMicrostep; end with Stop)
    def BeginManualMicrostep(self, push_out: bool) -> bool:
        """push_out=True: each microstep pushes fluid out; False: pulls in."""
        return bool(self.device.CmdSetStepDirection(bool(push_out)))

    def MicrostepOnce(self) -> bool:
        return bool(self.device.CmdMicrostep())

    def MicrostepRepeat(self, count: int, delay_sec: float = 0.002) -> int:
        """Run CmdMicrostep count times; returns number of successful steps reported."""
        n = max(0, int(count))
        ok = 0
        for _ in range(n):
            if self.MicrostepOnce():
                ok += 1
            if delay_sec > 0:
                time.sleep(delay_sec)
        return ok

    def MoveToPosition16(self, position: int) -> bool:
        """Move to 16-bit motor position (uProcess CmdMoveToPosition), not µL volume."""
        pos = int(position) & 0xFFFF
        return bool(self.device.CmdMoveToPosition(pos))

    ### Wait
    def Wait(self,time_sec):
        time.sleep(time_sec)
        self.Stop()
