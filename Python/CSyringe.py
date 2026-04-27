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

    def _move_context(self, flowrate, volume):
        addr = getattr(self, "add_syr", None)
        if addr is None:
            addr = getattr(self, "address", "?")
        return (
            f"name={self.name}, addr={addr}, "
            f"online={self.FlagIsOnline}, stalled={self.FlagIsStalled}, "
            f"ready={self.FlagReady}, flowrate={flowrate}, volume={volume}, "
            f"maxVolume={self.maxVolume}, "
            f"flowrate_range=[{self.minFlowrate},{self.maxFlowrate}]"
        )

    @staticmethod
    def _is_positive_number(value):
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return False

    ### MoveTo
    def MoveTo(self, flowrate, volume):
        """Send flowrate+volume commands to the pump.

        Raises RuntimeError if the pump is offline / stalled / busy at entry, or
        if a driver command returns False (uProcess convention: truthy==ok).
        Previously this silently no-op'd when FlagIsDone was False, which caused
        Flow Designer to mark the step green ("success") even when nothing ran.
        """
        try:
            self.UpdateStatus()
        except Exception as e:
            raise RuntimeError(
                f"Syringe {self.name}: UpdateStatus failed before MoveTo: {e}"
            ) from e
        if not self.FlagIsOnline:
            raise RuntimeError(f"Syringe {self.name} is offline.")
        if self.FlagIsStalled:
            raise RuntimeError(f"Syringe {self.name} is stalled.")
        if not self.FlagIsDone:
            raise RuntimeError(
                f"Syringe {self.name} is busy (FlagIsDone=False) — wait for the "
                f"previous move to finish before issuing a new one."
            )
        if not isinstance(flowrate, (int, float)) or float(flowrate) <= 0:
            raise RuntimeError(
                f"Syringe {self.name}: flowrate must be > 0 µL/min (got {flowrate!r})."
            )
        if not isinstance(volume, (int, float)) or float(volume) < 0:
            raise RuntimeError(
                f"Syringe {self.name}: volume must be >= 0 µL (got {volume!r})."
            )
        if isinstance(self.maxVolume, (int, float)) and float(volume) > float(self.maxVolume):
            raise RuntimeError(
                f"Syringe {self.name}: target volume {float(volume):.4g} µL exceeds "
                f"max stroke {float(self.maxVolume):.4g} µL."
            )

        # Range pre-checks: catch parameter-out-of-range *before* the driver
        # returns a bare False, so the operator sees a specific actionable
        # message (e.g. "reduce volume" / "change syringe") instead of a
        # generic CmdMoveToVolume failure. All three limits are populated in
        # __init__ via the vendor API (GetMaxVolume / Get{Max,Min}Flowrate).
        if self._is_positive_number(self.maxVolume) and volume > float(self.maxVolume):
            raise RuntimeError(
                f"Syringe ({self._move_context(flowrate, volume)}): requested "
                f"volume={volume} exceeds installed syringe capacity "
                f"(maxVolume={self.maxVolume}). Install a larger syringe or "
                f"reduce the step volume."
            )
        if self._is_positive_number(self.maxFlowrate) and flowrate > float(self.maxFlowrate):
            raise RuntimeError(
                f"Syringe ({self._move_context(flowrate, volume)}): requested "
                f"flowrate={flowrate} exceeds maxFlowrate={self.maxFlowrate}."
            )
        if self._is_positive_number(self.minFlowrate) and flowrate < float(self.minFlowrate):
            raise RuntimeError(
                f"Syringe ({self._move_context(flowrate, volume)}): requested "
                f"flowrate={flowrate} below minFlowrate={self.minFlowrate}."
            )

        rv = self.device.CmdSetFlowrate(flowrate)
        if rv is False:
            raise RuntimeError(
                f"Syringe ({self._move_context(flowrate, volume)}): CmdSetFlowrate({flowrate}) returned False."
            )
        self.Flowrate = flowrate
        rv = self.device.CmdMoveToVolume(volume)
        if rv is False:
            # Some firmware builds occasionally return False transiently.
            # Retry a few times with short delays before deciding failure.
            for delay_s in (0.03, 0.08, 0.15):
                try:
                    time.sleep(delay_s)
                    rv_retry = self.device.CmdMoveToVolume(volume)
                    if rv_retry is not False:
                        rv = rv_retry
                        break
                except Exception:
                    pass
        if rv is False:
            # If retry still reports False, poll status for a short window:
            # motion may start asynchronously even when the API returns False.
            moving_now = False
            target_reached = False
            current_volume = getattr(self, "volume_ul", None)
            for _ in range(6):
                try:
                    time.sleep(0.06)
                    self.UpdateStatus()
                except Exception:
                    pass
                current_volume = getattr(self, "volume_ul", None)
                target_reached = isinstance(current_volume, (int, float)) and abs(
                    float(current_volume) - float(volume)
                ) <= 0.5
                moving_now = bool(
                    getattr(self, "FlagIsMoving", False)
                    or getattr(self, "FlagIsMovingIn", False)
                    or getattr(self, "FlagIsMovingOut", False)
                )
                if moving_now or target_reached:
                    break
            if not moving_now and not target_reached:
                raise RuntimeError(
                    f"Syringe ({self._move_context(flowrate, volume)}): "
                    f"CmdMoveToVolume({volume}) returned False "
                    f"(current_volume={current_volume!r}, moving={moving_now}, target_reached={target_reached})."
                )
            # Treat as accepted/no-op and continue.
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
        """Poll hardware until the pump reports done, raises on stall/timeout.

        Cooperates with the GUI via the parent board's `poll_hook`
        (QApplication.processEvents) so the Stop button stays clickable during
        long moves, and `cancel_requested` flag so Stop can break the loop.
        """
        if self.FlagIsMoving == True:
            start = time.monotonic()
            # Safety ceiling: real LabSmith moves complete in seconds-to-minutes.
            # 2 hours is well past any realistic single move — if we hit it the
            # pump is genuinely stuck and hanging the GUI thread isn't helpful.
            timeout_seconds = 2 * 60 * 60
            while self.FlagIsMoving == True:
                if getattr(self.Lboard, "cancel_requested", False) or \
                   getattr(self.Lboard, "Stop", False):
                    break
                hook = getattr(self.Lboard, "poll_hook", None)
                if callable(hook):
                    try:
                        hook()
                    except Exception:
                        # A hook failure must not block hardware polling.
                        pass
                self.UpdateStatus()
                if self.FlagIsStalled:
                    raise RuntimeError(
                        f"Syringe {self.name} stalled during move."
                    )
                if time.monotonic() - start > timeout_seconds:
                    raise RuntimeError(
                        f"Syringe {self.name} move timed out after "
                        f"{timeout_seconds}s."
                    )
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

    def ResetRuntimeState(self):
        """Best-effort runtime reset after interrupted/drifted sessions.

        Stops motion, refreshes status, and if the reported volume is negative,
        attempts a safe recover-to-zero move so subsequent MoveTo calls are
        based on a non-negative reference.
        """
        before = getattr(self, "volume_ul", None)
        try:
            self.device.CmdStop()
        except Exception:
            pass
        self.UpdateStatus()
        before = getattr(self, "volume_ul", before)
        attempted_zero_recover = False
        if isinstance(before, (int, float)) and float(before) < 0:
            attempted_zero_recover = True
            safe_flow = 100.0
            if isinstance(self.minFlowrate, (int, float)):
                safe_flow = max(1.0, abs(float(self.minFlowrate)))
            try:
                self.device.CmdSetFlowrate(float(safe_flow))
                self.device.CmdMoveToVolume(0.0)
                for _ in range(40):
                    time.sleep(0.05)
                    self.UpdateStatus()
                    cur = getattr(self, "volume_ul", None)
                    if isinstance(cur, (int, float)) and abs(float(cur)) <= 0.5:
                        break
                    if getattr(self, "FlagIsDone", False) and not getattr(self, "FlagIsMoving", False):
                        break
            except Exception:
                pass
        self.FlagStop = False
        self.FlagReady = True
        self.UpdateStatus()
        return {
            "before_volume_ul": before,
            "after_volume_ul": getattr(self, "volume_ul", None),
            "attempted_zero_recover": attempted_zero_recover,
            "online": bool(getattr(self, "FlagIsOnline", False)),
            "stalled": bool(getattr(self, "FlagIsStalled", False)),
            "done": bool(getattr(self, "FlagIsDone", False)),
        }

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
