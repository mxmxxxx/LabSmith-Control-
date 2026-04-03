import numpy as np
import time
from uProcess_x64 import uProcess_x64
from datetime import datetime
import os
import shutil
import re
from CManifold import CManifold
from CSyringe import CSyringe
from extra_board_devices import C4AnalogModule, C4PowerModule, CEP01Board
from output_log import log_directory, output_txt_path


class LabsmithBoard:    
    
    def __init__(self, port): # # com is the comment i show on the Output text area in the app
        ## General info
        self.MaxNumDev = []
        self.TotNumDev = [] 
        self.eib = [] 
        self.C4VM = []
        self.SPS01 = []
        self.C4AM = np.empty(0, dtype=object)
        self.C4PM = np.empty(0, dtype=object)
        self.CEP01 = np.empty(0, dtype=object)

        self.eib=uProcess_x64.CEIB()
        self.port = port

        ## Flags
        self.isConnected = False 
        self.isDisconnected = True 
        self.Stop = False 
        self.Pause = False 
        self.Resume = False 
        self.flag_break_countpause = 0 
        self.flag_break_stop = 0 
        self.flag_a = 0   # # flag used in listener of MoveWait function used to print just the initial target waiting time
        self.flag_b = 0   # # flag used in listener of MoveWait function used to print just the initial target waiting time
                   
        ## Clocks
        self.ClockStartConnection = None
        self.ClockStopConnection = None
        self.ClockStop = None
        self.ClockResume = None
        
        
        ## Events
        self._listeners = {event: dict() for event in [
            "FirstDone",
            "FirstDoneStop",
            "FirstDoneStopM",
            "FirstDoneStopPause",
            "FirstDoneStopPauseM",
            "FirstDoneStopPauseWait"]}
        
        self.Constructor()
        

    ## Add Listeners to Events
    def addlistener(self, event, listener, callback, args):
        if callable(callback):
            self._listeners[event][listener] = [callback, args]

    ## Trigger Events
    def notify(self, event):
        for listener, [callback, args] in self._listeners[event].items():
            callback(*args)

    ### Constructor
    def Constructor(self):
        a=self.eib.InitConnection(np.int8(self.port))
        with open(output_txt_path(), "a") as OUTPUT:
            if a == 0:
                self.isConnected = True
                self.isDisconnected = False
                self.ClockStartConnection = datetime.now()
                comment=f"Connected on {self.ClockStartConnection}"
                self.Load()
            else:
                comment='Not connected, check the right COM port on Device Manager'
        
            OUTPUT.write(comment + "\n")
            print(comment)


    ### Destructor
    def Disconnect(self):
        a=np.int64(self.eib.CloseConnection())
        with open(output_txt_path(), "a") as OUTPUT:
            if a == 0:
                self.isConnected = False
                self.isDisconnected = True
                self.ClockStopConnection = datetime.now()
                com= f"Disconnected on {self.ClockStopConnection}"
                stamp = self.ClockStartConnection or self.ClockStopConnection
                namefile = os.path.join(
                    log_directory(),
                    f"OUTPUT_{stamp.strftime('%y_%m_%d_%H_%M_%S')}.txt",
                )
                shutil.copy(output_txt_path(), namefile)
            else:
                com='Error, still connected'

            OUTPUT.write(com + "\n")
        print(com)
        return com
        
    ### Load
    def Load(self):
        dev_list=str(self.eib.CmdCreateDeviceList())
        expression = ', ' ##i first split the string into multiple strings
        splitStr = dev_list.split(expression)##divide all the different devices. It is a cell array. Each cell is a segment of the dev_list char vector containing info about each device
        NumDev=len(splitStr)
        self.TotNumDev=NumDev

        PAT_S="<uProcess.CSyringe>"
        PAT_M="<uProcess.C4VM>"
        PAT_AM="<uProcess.C4AM>"
        PAT_PM="<uProcess.C4PM>"
        PAT_EP="<uProcess.CEP01>"

        StrSyringe= [syringe for syringe in splitStr if PAT_S in syringe]
        StrManifold= [manifold for manifold in splitStr if PAT_M in manifold]
        StrAM = [x for x in splitStr if PAT_AM in x]
        StrPM = [x for x in splitStr if PAT_PM in x]
        StrEP = [x for x in splitStr if PAT_EP in x]

        self.C4AM = np.empty(0, dtype=object)
        self.C4PM = np.empty(0, dtype=object)
        self.CEP01 = np.empty(0, dtype=object)

        if StrManifold:
            PAT = r"address (\d+)"
            add_man = []
            for Manifold in StrManifold:
                add_man.extend(re.findall(PAT, Manifold))
            self.C4VM = np.empty(len(add_man), dtype=object)
            for i, add in enumerate(add_man):
                self.C4VM[i] = CManifold(self, int(add)) ## it constructs a SPS01 selfect on the specified address. We will use this for the command
                self.C4VM[i].address=int(add)

        if StrSyringe:
            PAT = r"address (\d+)"
            add_syr = []
            for Syringe in StrSyringe:
                add_syr.extend(re.findall(PAT, Syringe))
            self.SPS01 = np.empty(len(add_syr), dtype=object)
            for i, add in enumerate(add_syr):
                self.SPS01[i] = CSyringe(self, int(add)) ## it constructs a SPS01 selfect on the specified address. We will use this for the command
                self.SPS01[i].address=int(add)

        addr_pat = re.compile(r"address (\d+)")
        if StrAM:
            add_am = [int(x) for x in addr_pat.findall(" ".join(StrAM))]
            self.C4AM = np.empty(len(add_am), dtype=object)
            for i, add in enumerate(add_am):
                self.C4AM[i] = C4AnalogModule(self, add)
                self.C4AM[i].address = int(add)
        if StrPM:
            add_pm = [int(x) for x in addr_pat.findall(" ".join(StrPM))]
            self.C4PM = np.empty(len(add_pm), dtype=object)
            for i, add in enumerate(add_pm):
                self.C4PM[i] = C4PowerModule(self, add)
                self.C4PM[i].address = int(add)
        if StrEP:
            add_ep = [int(x) for x in addr_pat.findall(" ".join(StrEP))]
            self.CEP01 = np.empty(len(add_ep), dtype=object)
            for i, add in enumerate(add_ep):
                self.CEP01[i] = CEP01Board(self, add)
                self.CEP01[i].address = int(add)

    ### Stop
    def StopBoard(self):
        for i in range(len(self.SPS01)):
            self.SPS01[i].device.CmdStop()
            self.SPS01[i].FlagReady = True
            self.SPS01[i].UpdateStatus()
        for i in range(len(self.C4VM)):
            self.C4VM[i].device.CmdStop()
            self.C4VM[i].UpdateStatus()
        for i in range(len(self.C4AM)):
            self.C4AM[i].Stop()
        for i in range(len(self.C4PM)):
            self.C4PM[i].Stop()
        for i in range(len(self.CEP01)):
            self.CEP01[i].Stop()
        self.ClockStop = datetime.now()
        comment = f"{self.ClockStop.strftime('%X')} Interface stopped by the user."
        with open(output_txt_path(), "a") as OUTPUT:
            OUTPUT.write(comment + "\n")
            print(comment)

    ### Move
    def Move(self, namedevice, flowrate, volume):
        for i in range(len(self.SPS01)):
            if self.SPS01[i].name == namedevice:
                self.SPS01[i].MoveTo(flowrate,volume)
                return
        with open(output_txt_path(), "a") as OUTPUT:
            comment='ERROR: Name syringe not correct'
            OUTPUT.write(comment + "\n")
            print(comment)

    ### Move2
    def Move2(self, namedevice, flowrate, volume):
        for i in range(len(self.SPS01)):
            if self.SPS01[i].name == namedevice:
                self.SPS01[i].MoveTo(flowrate,volume)
                return
        with open(output_txt_path(), "a") as OUTPUT:
            comment='ERROR: Name syringe not correct'
            OUTPUT.write(comment + "\n")
            print(comment)
    
    ### FindIndexS (find index of Syringe from name of device)
    def FindIndexS(self, n):
        k = [self.SPS01[i].name == n for i in range(len(self.SPS01))]
        if not any(k):
            comment = f"Error : {n} does not exist. Check name again."
            with open(output_txt_path(), "a") as OUTPUT:
                OUTPUT.write(comment + "\n")
                print(comment)
            raise ValueError(comment)
        return int(np.nonzero(k)[0][0])

    ### FindIndexM (find index of Manifold from name of device)
    def FindIndexM(self, n):
        k = [self.C4VM[i].name == n for i in range(len(self.C4VM))]
        if not any(k):
            comment = f"Error : {n} does not exist. Check name again."
            with open(output_txt_path(), "a") as OUTPUT:
                OUTPUT.write(comment + "\n")
                print(comment)
            raise ValueError(comment)
        return int(np.nonzero(k)[0][0])

    ### Set Multiple FlowRates (at the same time)
    def SetFlowRate(self, d1 = None, f1 = None, d2 = None, f2 = None, d3 = None, f3 = None, d4 = None, f4 = None, d5 = None, f5 = None, d6 = None, f6 = None, d7 = None, f7 = None, d8 = None, f8 = None):
        if [d1, f1, d2, f2, d3, f3, d4, f4, d5, f5, d6, f6, d7, f7, d8, f8].count(None)%2 !=0:
                print('Error, missing input. Number of inputs has to be even (name of syringes and corresponding flow rates).')
        else:
            if f1 != None and d2 == None:
                i1=self.FindIndexS(d1)
                if len(self.SPS01) == 1:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)                        
                    self.SPS01[i1].Flowrate = f1
            elif f2 != None and d3 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                if len(self.SPS01) == 2:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2                        
            elif f3 != None and d4 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                if len(self.SPS01) == 3:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
            elif f4 != None and d5 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                i4=self.FindIndexS(d4)
                if len(self.SPS01) == 4:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
                    self.SPS01[i4].device.CmdSetFlowrate(f4)
                    self.SPS01[i4].Flowrate = f4
            elif f5 != None and d6 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                i4=self.FindIndexS(d4)
                i5=self.FindIndexS(d5)
                if len(self.SPS01) == 5:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
                    self.SPS01[i4].device.CmdSetFlowrate(f4)
                    self.SPS01[i4].Flowrate = f4
                    self.SPS01[i5].device.CmdSetFlowrate(f5)
                    self.SPS01[i5].Flowrate = f5
            elif f6 != None and d7 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                i4=self.FindIndexS(d4)
                i5=self.FindIndexS(d5)
                i6=self.FindIndexS(d6)
                if len(self.SPS01) == 6:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
                    self.SPS01[i4].device.CmdSetFlowrate(f4)
                    self.SPS01[i4].Flowrate = f4
                    self.SPS01[i5].device.CmdSetFlowrate(f5)
                    self.SPS01[i5].Flowrate = f5
                    self.SPS01[i6].device.CmdSetFlowrate(f6)
                    self.SPS01[i6].Flowrate = f6
            elif f7 != None and d8 == None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                i4=self.FindIndexS(d4)
                i5=self.FindIndexS(d5)
                i6=self.FindIndexS(d6)
                i7=self.FindIndexS(d7)
                if len(self.SPS01) == 7:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
                    self.SPS01[i4].device.CmdSetFlowrate(f4)
                    self.SPS01[i4].Flowrate = f4
                    self.SPS01[i5].device.CmdSetFlowrate(f5)
                    self.SPS01[i5].Flowrate = f5
                    self.SPS01[i6].device.CmdSetFlowrate(f6)
                    self.SPS01[i6].Flowrate = f6
                    self.SPS01[i7].device.CmdSetFlowrate(f7)
                    self.SPS01[i7].Flowrate = f7
            elif f8 != None:
                i1=self.FindIndexS(d1)
                i2=self.FindIndexS(d2)
                i3=self.FindIndexS(d3)
                i4=self.FindIndexS(d4)
                i5=self.FindIndexS(d5)
                i6=self.FindIndexS(d6)
                i7=self.FindIndexS(d7)
                i8=self.FindIndexS(d8)
                if len(self.SPS01) == 8:
                    self.SPS01[i1].device.CmdSetFlowrate(f1)
                    self.SPS01[i1].Flowrate = f1
                    self.SPS01[i2].device.CmdSetFlowrate(f2)
                    self.SPS01[i2].Flowrate = f2 
                    self.SPS01[i3].device.CmdSetFlowrate(f3)
                    self.SPS01[i3].Flowrate = f3
                    self.SPS01[i4].device.CmdSetFlowrate(f4)
                    self.SPS01[i4].Flowrate = f4
                    self.SPS01[i5].device.CmdSetFlowrate(f5)
                    self.SPS01[i5].Flowrate = f5
                    self.SPS01[i6].device.CmdSetFlowrate(f6)
                    self.SPS01[i6].Flowrate = f6
                    self.SPS01[i7].device.CmdSetFlowrate(f7)
                    self.SPS01[i7].Flowrate = f7
                    self.SPS01[i8].device.CmdSetFlowrate(f8)
                    self.SPS01[i8].Flowrate = f8
            else:
                print('Error, wrong number of inputs.')


    ### Multiple Movement (at the same time)
    def MulMove(self, d1 = None, v1 = None, d2  = None, v2 = None, d3 = None, v3 = None, d4 = None, v4 = None, d5 = None, v5 = None, d6 = None, v6 = None, d7 = None, v7 = None, d8 = None, v8 = None):
        if [d1, v1, d2, v2, d3, v3, d4, v4, d5, v5, d6, v6, d7, v7, d8, v8].count(None)%2 !=0:
            print('Error, missing input. Number of inputs has to be even (name of syringes and corresponding flow rates).')
        else:
            if v1 != None and d2 == None:  # # 1 syringe as input
                i1=self.FindIndexS(d1) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1])   # #it listens for the syringe FlagIsMoving == True, so it updtades continuously the state to determine the end of the command. It results in FlagReady = True again.
                if len(self.SPS01) == 1:
                    if self.SPS01[i1].FlagIsDone == True:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)                             
                        self.SPS01[i1].FlagReady = False 
                        self.SPS01[i1].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True:
                            self.SPS01[i1].notify('MovingState') 
            elif v2 != None and d3 == None:  # # 2 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2)  
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 2:
                    if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i1].FlagReady = False 
                        self.SPS01[i2].FlagReady = False 
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement()  
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                            self.notify('FirstDone') 

            elif v3 != None and d4 == None:  # # 3 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 3:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                        self.notify('FirstDone')               
            elif v4 != None and d5 == None:  # # 4 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                i4=self.FindIndexS(d4) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3,i4])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 4:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i4].device.CmdMoveToVolume(v4) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i4].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    self.SPS01[i4].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                        self.notify('FirstDone') 
            elif v5 != None and d6 == None:  # # 5 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                i4=self.FindIndexS(d4) 
                i5=self.FindIndexS(d5) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3,i4,i5])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 5:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i4].device.CmdMoveToVolume(v4) 
                    self.SPS01[i5].device.CmdMoveToVolume(v5) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i4].FlagReady = False 
                    self.SPS01[i5].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    self.SPS01[i4].displaymovement()
                    self.SPS01[i5].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                        self.notify('FirstDone') 
            elif v6 != None and d7 == None:  # # 6 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                i4=self.FindIndexS(d4) 
                i5=self.FindIndexS(d5) 
                i6=self.FindIndexS(d6) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3,i4,i5,i6])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 6:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i4].device.CmdMoveToVolume(v4) 
                    self.SPS01[i5].device.CmdMoveToVolume(v5) 
                    self.SPS01[i6].device.CmdMoveToVolume(v6) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i4].FlagReady = False 
                    self.SPS01[i5].FlagReady = False 
                    self.SPS01[i6].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    self.SPS01[i4].displaymovement()
                    self.SPS01[i5].displaymovement()
                    self.SPS01[i6].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                        self.notify('FirstDone') 
            elif v7 != None and d8 == None:  # # 7 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                i4=self.FindIndexS(d4) 
                i5=self.FindIndexS(d5) 
                i6=self.FindIndexS(d6) 
                i7=self.FindIndexS(d7) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3,i4,i5,i6,i7])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 7:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i4].device.CmdMoveToVolume(v4) 
                    self.SPS01[i5].device.CmdMoveToVolume(v5) 
                    self.SPS01[i6].device.CmdMoveToVolume(v6) 
                    self.SPS01[i7].device.CmdMoveToVolume(v7) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i4].FlagReady = False 
                    self.SPS01[i5].FlagReady = False 
                    self.SPS01[i6].FlagReady = False 
                    self.SPS01[i7].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    self.SPS01[i4].displaymovement()
                    self.SPS01[i5].displaymovement()
                    self.SPS01[i6].displaymovement()
                    self.SPS01[i7].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                        self.notify('FirstDone') 
            elif v8 != None:  # # 8 syringes as input
                i1=self.FindIndexS(d1) 
                i2=self.FindIndexS(d2) 
                i3=self.FindIndexS(d3) 
                i4=self.FindIndexS(d4) 
                i5=self.FindIndexS(d5) 
                i6=self.FindIndexS(d6) 
                i7=self.FindIndexS(d7) 
                i8=self.FindIndexS(d8) 
                self.addlistener('FirstDone', "listener_firstdone", self.CheckFirstDone, [i1,i2,i3,i4,i5,i6,i7,i8])   # #it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                if len(self.SPS01) == 8:
                    self.SPS01[i1].device.CmdMoveToVolume(v1) 
                    self.SPS01[i2].device.CmdMoveToVolume(v2) 
                    self.SPS01[i3].device.CmdMoveToVolume(v3) 
                    self.SPS01[i4].device.CmdMoveToVolume(v4) 
                    self.SPS01[i5].device.CmdMoveToVolume(v5) 
                    self.SPS01[i6].device.CmdMoveToVolume(v6) 
                    self.SPS01[i7].device.CmdMoveToVolume(v7) 
                    self.SPS01[i8].device.CmdMoveToVolume(v8) 
                    self.SPS01[i1].FlagReady = False 
                    self.SPS01[i2].FlagReady = False 
                    self.SPS01[i3].FlagReady = False 
                    self.SPS01[i4].FlagReady = False 
                    self.SPS01[i5].FlagReady = False 
                    self.SPS01[i6].FlagReady = False 
                    self.SPS01[i7].FlagReady = False 
                    self.SPS01[i8].FlagReady = False 
                    self.SPS01[i1].displaymovement()
                    self.SPS01[i2].displaymovement() 
                    self.SPS01[i3].displaymovement()
                    self.SPS01[i4].displaymovement()
                    self.SPS01[i5].displaymovement()
                    self.SPS01[i6].displaymovement()
                    self.SPS01[i7].displaymovement()
                    self.SPS01[i8].displaymovement()
                    if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                        self.notify('FirstDone')
            else:
                print('Error, wrong number of inputs.')

    ## Multiple Movement with stop (at the same time. It allows the stop)
    def MulMove2(self, d1 = None, v1= None, d2= None, v2= None, d3= None, v3= None, d4= None, v4= None, d5= None, v5= None, d6= None, v6= None, d7= None, v7= None, d8= None, v8= None):
        if self.Stop == False:
            if [d1, v1, d2, v2, d3, v3, d4, v4, d5, v5, d6, v6, d7, v7, d8, v8].count(None)%2 !=0:
                print('Error, missing input. Number of inputs has to be even (name of syringes and corresponding flow rates).')
            else:
                if v1 != None and d2 == None: ## 1 syringe as input
                    i1=self.FindIndexS(d1)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1])   ##it listens for the syringe FlagIsMoving == True, so it updtades continuously the state to determine the end of the command. It results in FlagReady = True again.
                    if len(self.SPS01) == 1:
                        if self.SPS01[i1].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1) 
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            if self.SPS01[i1].FlagIsMoving == True:
                                self.notify('FirstDoneStop')
                elif v2 != None and d3 == None: ## 2 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.  
                    if len(self.SPS01) == 2:
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1) 
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            self.SPS01[i2].device.CmdMoveToVolume(v2) 
                            self.SPS01[i2].FlagReady = False
                            self.SPS01[i2].displaymovement() 
                            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                                self.notify('FirstDoneStop')
                elif v3 != None and d4 == None: ## 3 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 3:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True:
                            self.notify('FirstDoneStop')                   
                elif v4 != None and d5 == None: ## 4 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3, i4]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 4:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].device.CmdMoveToVolume(v4) 
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i4].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                            self.notify('FirstDoneStop')
                elif v5 != None and d6 == None: ## 5 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3, i4, i5]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 5:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].device.CmdMoveToVolume(v4) 
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].device.CmdMoveToVolume(v5) 
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i5].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                            self.notify('FirstDoneStop')
                elif v6 != None and d7 == None: ## 6 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    i6=self.FindIndexS(d6)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3, i4, i5, i6]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 6:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].device.CmdMoveToVolume(v4) 
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].device.CmdMoveToVolume(v5) 
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i5].displaymovement()
                        self.SPS01[i6].device.CmdMoveToVolume(v6) 
                        self.SPS01[i6].FlagReady = False
                        self.SPS01[i6].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                            self.notify('FirstDoneStop')
                elif v7 != None and d8 == None: ## 7 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    i6=self.FindIndexS(d6)
                    i7=self.FindIndexS(d7)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3, i4, i5, i6, i7]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 7:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].device.CmdMoveToVolume(v4) 
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].device.CmdMoveToVolume(v5) 
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i5].displaymovement()
                        self.SPS01[i6].device.CmdMoveToVolume(v6) 
                        self.SPS01[i6].FlagReady = False
                        self.SPS01[i6].displaymovement()
                        self.SPS01[i7].device.CmdMoveToVolume(v7) 
                        self.SPS01[i7].FlagReady = False
                        self.SPS01[i7].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                            self.notify('FirstDoneStop')
                elif v7 != None: ## 8 syringes as input (impossible - max numb of syringes is 7)
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    i6=self.FindIndexS(d6)
                    i7=self.FindIndexS(d7)
                    i8=self.FindIndexS(d8)
                    self.addlistener('FirstDoneStop', "listener_firstdone", self.CheckFirstDoneStop, [i1, i2, i3, i4, i5, i6, i7, i8]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 8:
                        self.SPS01[i1].device.CmdMoveToVolume(v1) 
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].device.CmdMoveToVolume(v2) 
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i2].displaymovement()
                        self.SPS01[i3].device.CmdMoveToVolume(v3) 
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].device.CmdMoveToVolume(v4) 
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].device.CmdMoveToVolume(v5) 
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i5].displaymovement()
                        self.SPS01[i6].device.CmdMoveToVolume(v6) 
                        self.SPS01[i6].FlagReady = False
                        self.SPS01[i6].displaymovement()
                        self.SPS01[i7].device.CmdMoveToVolume(v7) 
                        self.SPS01[i7].FlagReady = False
                        self.SPS01[i7].displaymovement()
                        self.SPS01[i8].device.CmdMoveToVolume(v8) 
                        self.SPS01[i8].FlagReady = False
                        self.SPS01[i8].displaymovement()
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                            self.notify('FirstDoneStop')
                else:
                    print('Error, wrong number of inputs.')

    ### Listener Function : Display the first device to be done (called in MulMove)
    def CheckFirstDone(self, *args):
        if len(args) == 1:  # # only one syringe in motion 
            i1=args[0]   # #argsg doesnt include the self, so its size is len(args)-1. The index is the last.
            if self.SPS01[i1].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True:
                    self.SPS01[i1].displaymovementstop()
        elif len(args) == 2:
            i1=args[0]  
            i2=args[1] 
            i=[i1, i2]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True :
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus()
                    self.SPS01[i2].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[ i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]   # # a=[i2] for j=1, a=[i1] for j=2
                            while self.SPS01[a[0]].FlagIsMoving == True:
                                self.SPS01[a[0]].UpdateStatus()                            
                                time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True:
                                self.SPS01[a[0]].displaymovementstop()                               
                            break
        elif len(args) == 3:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i=[i1, i2, i3]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True: 
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]   # # a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus() 
                                    self.SPS01[a[1]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True:
                                            self.SPS01[b[0]].displaymovementstop()                     
                                        break
                            break
        elif len(args) == 4:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i4=args[3] 
            i=[i1, i2, i3, i4]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus() 
                    self.SPS01[i4].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]  
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus() 
                                    self.SPS01[a[1]].UpdateStatus() 
                                    self.SPS01[a[2]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus() 
                                            self.SPS01[b[1]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True:
                                            for p in range(b[0]):
                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                    self.SPS01[b[p]].displaymovementstop()
                                                    c=b 
                                                    c[p]=[] 
                                                    while self.SPS01[c[0]].FlagIsMoving == True:
                                                        self.SPS01[c[0]].UpdateStatus()
                                                        time.sleep(0.01)
                                                    if self.SPS01[c[0]].FlagIsDone == True:
                                                        self.SPS01[c[0]].displaymovementstop()
                                                    break
                                        break
                            break
        elif len(args) == 5:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i4=args[3] 
            i5=args[4] 
            i=[i1, i2, i3, i4, i5]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus() 
                    self.SPS01[i4].UpdateStatus() 
                    self.SPS01[i5].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]  
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus()
                                    self.SPS01[a[1]].UpdateStatus()
                                    self.SPS01[a[2]].UpdateStatus()
                                    self.SPS01[a[3]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus()
                                            self.SPS01[b[1]].UpdateStatus()
                                            self.SPS01[b[2]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True:
                                            for p in range(b[0]):
                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                    self.SPS01[b[p]].displaymovementstop()
                                                    c=b 
                                                    c[p]=[] 
                                                    while self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving:
                                                        self.SPS01[c[0]].UpdateStatus()
                                                        self.SPS01[c[1]].UpdateStatus()
                                                        time.sleep(0.01)
                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True:
                                                        for q in range(c[0]):
                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                self.SPS01[c[q]].displaymovementstop()
                                                                d=c 
                                                                d[q]=[] 
                                                                while self.SPS01[d[0]].FlagIsMoving:
                                                                    self.SPS01[d[0]].UpdateStatus()
                                                                    time.sleep(0.01)
                                                                if self.SPS01[d[0]].FlagIsDone:
                                                                    self.SPS01[d[0]].displaymovementstop()
                                                                break
                                                    break
                                        break
                            break
        elif len(args) == 6:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i4=args[3] 
            i5=args[4] 
            i6=args[5] 
            i=[i1, i2, i3, i4, i5, i6]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus() 
                    self.SPS01[i4].UpdateStatus() 
                    self.SPS01[i5].UpdateStatus() 
                    self.SPS01[i6].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i
                            a[j]=[]
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus()
                                    self.SPS01[a[1]].UpdateStatus()
                                    self.SPS01[a[2]].UpdateStatus()
                                    self.SPS01[a[3]].UpdateStatus()
                                    self.SPS01[a[4]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus()
                                            self.SPS01[b[1]].UpdateStatus()
                                            self.SPS01[b[2]].UpdateStatus()
                                            self.SPS01[b[3]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True:
                                            for p in range(b[0]):
                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                    self.SPS01[b[p]].displaymovementstop()
                                                    c=b 
                                                    c[p]=[] 
                                                    while self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving:
                                                        self.SPS01[c[0]].UpdateStatus()
                                                        self.SPS01[c[1]].UpdateStatus()
                                                        self.SPS01[c[2]].UpdateStatus()
                                                        time.sleep(0.01)
                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True:
                                                        for q in range(c[0]):
                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                self.SPS01[c[q]].displaymovementstop()
                                                                d=c 
                                                                d[q]=[] 
                                                                while self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving:
                                                                    self.SPS01[d[0]].UpdateStatus()
                                                                    self.SPS01[d[1]].UpdateStatus()
                                                                    time.sleep(0.01)
                                                                if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone:
                                                                    for r in range(d[0]):
                                                                        if self.SPS01[d[r]].FlagIsDone == True:
                                                                            self.SPS01[d[r]].displaymovementstop()
                                                                            e=d
                                                                            e[r]=[]
                                                                            while self.SPS01[e[0]].FlagIsMoving:
                                                                                self.SPS01[e[0]].UpdateStatus()
                                                                                time.sleep(0.01)
                                                                            if self.SPS01[e[0]].FlagIsDone:
                                                                                self.SPS01[e[0]].displaymovementstop()
                                                                            break
                                                                break
                                                    break
                                        break
                            break
        elif len(args) == 7:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i4=args[3] 
            i5=args[4] 
            i6=args[5] 
            i7=args[6] 
            i=[i1, i2, i3, i4, i5, i6, i7]  
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus() 
                    self.SPS01[i4].UpdateStatus() 
                    self.SPS01[i5].UpdateStatus() 
                    self.SPS01[i6].UpdateStatus() 
                    self.SPS01[i7].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True or self.SPS01[i7].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]  
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True and self.SPS01[a[5]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus() 
                                    self.SPS01[a[1]].UpdateStatus() 
                                    self.SPS01[a[2]].UpdateStatus() 
                                    self.SPS01[a[3]].UpdateStatus() 
                                    self.SPS01[a[4]].UpdateStatus() 
                                    self.SPS01[a[5]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True or self.SPS01[a[5]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus() 
                                            self.SPS01[b[1]].UpdateStatus() 
                                            self.SPS01[b[2]].UpdateStatus() 
                                            self.SPS01[b[3]].UpdateStatus() 
                                            self.SPS01[b[4]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True or self.SPS01[b[4]].FlagIsDone == True:
                                            for p in range(b[0]):
                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                    self.SPS01[b[p]].displaymovementstop()
                                                    c=b 
                                                    c[p]=[] 
                                                    while self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving and self.SPS01[c[3]].FlagIsMoving:
                                                        self.SPS01[c[0]].UpdateStatus() 
                                                        self.SPS01[c[1]].UpdateStatus() 
                                                        self.SPS01[c[2]].UpdateStatus() 
                                                        self.SPS01[c[3]].UpdateStatus()
                                                        time.sleep(0.01)
                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True or self.SPS01[c[3]].FlagIsDone == True:
                                                        for q in range(c[0]):
                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                self.SPS01[c[q]].displaymovementstop()
                                                                d=c 
                                                                d[q]=[] 
                                                                while self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving and self.SPS01[d[2]].FlagIsMoving:
                                                                    self.SPS01[d[0]].UpdateStatus() 
                                                                    self.SPS01[d[1]].UpdateStatus() 
                                                                    self.SPS01[d[2]].UpdateStatus()
                                                                    time.sleep(0.01)
                                                                if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone or self.SPS01[d[2]].FlagIsDone:
                                                                    for r in range(d[0]):
                                                                        if self.SPS01[d[r]].FlagIsDone == True:
                                                                            self.SPS01[d[r]].displaymovementstop()
                                                                            e=d 
                                                                            e[r]=[] 
                                                                            while self.SPS01[e[0]].FlagIsMoving and self.SPS01[e[1]].FlagIsMoving:
                                                                                self.SPS01[e[0]].UpdateStatus()
                                                                                self.SPS01[e[1]].UpdateStatus()
                                                                                time.sleep(0.01)
                                                                            if self.SPS01[e[0]].FlagIsDone or self.SPS01[e[1]].FlagIsDone:
                                                                                for s in range(e[0]):
                                                                                    if self.SPS01[e[s]].FlagIsDone == True:
                                                                                        self.SPS01[e[s]].displaymovementstop()
                                                                                        f=e 
                                                                                        f[s]=[] 
                                                                                        while self.SPS01[f[0]].FlagIsMoving:
                                                                                            self.SPS01[f[0]].UpdateStatus()
                                                                                            time.sleep(0.01)
                                                                                        if self.SPS01[f[0]].FlagIsDone:
                                                                                            self.SPS01[f[0]].displaymovementstop()
                                                                                        break
                                                                break
                                                    break
                                        break
                            break
        elif len(args) == 8:
            i1=args[0]  
            i2=args[1] 
            i3=args[2] 
            i4=args[3] 
            i5=args[4] 
            i6=args[5] 
            i7=args[6] 
            i8=args[7] 
            i=[i1, i2, i3, i4, i5, i6, i7, i8]   # #i=args[2:len(args)-2]
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                while self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                    self.SPS01[i1].UpdateStatus() 
                    self.SPS01[i2].UpdateStatus() 
                    self.SPS01[i3].UpdateStatus() 
                    self.SPS01[i4].UpdateStatus() 
                    self.SPS01[i5].UpdateStatus() 
                    self.SPS01[i6].UpdateStatus() 
                    self.SPS01[i7].UpdateStatus() 
                    self.SPS01[i8].UpdateStatus()
                    time.sleep(0.01)
                if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True or self.SPS01[i7].FlagIsDone == True or self.SPS01[i8].FlagIsDone == True:
                    for j in range(i[0]):
                        if self.SPS01[i[j]].FlagIsDone == True:
                            self.SPS01[i[j]].displaymovementstop()
                            a=i 
                            a[j]=[]  
                            while self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True and self.SPS01[a[5]].FlagIsMoving == True and self.SPS01[a[6]].FlagIsMoving == True:
                                    self.SPS01[a[0]].UpdateStatus() 
                                    self.SPS01[a[1]].UpdateStatus() 
                                    self.SPS01[a[2]].UpdateStatus() 
                                    self.SPS01[a[3]].UpdateStatus() 
                                    self.SPS01[a[4]].UpdateStatus() 
                                    self.SPS01[a[5]].UpdateStatus() 
                                    self.SPS01[a[6]].UpdateStatus()
                                    time.sleep(0.01)
                            if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True or self.SPS01[a[5]].FlagIsDone == True or self.SPS01[a[6]].FlagIsDone == True:
                                for k in range(a[0]):
                                    if self.SPS01[a[k]].FlagIsDone == True:
                                        self.SPS01[a[k]].displaymovementstop()
                                        b=a 
                                        b[k]=[] 
                                        while self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True and self.SPS01[b[5]].FlagIsMoving == True:
                                            self.SPS01[b[0]].UpdateStatus() 
                                            self.SPS01[b[1]].UpdateStatus() 
                                            self.SPS01[b[2]].UpdateStatus() 
                                            self.SPS01[b[3]].UpdateStatus() 
                                            self.SPS01[b[4]].UpdateStatus() 
                                            self.SPS01[b[5]].UpdateStatus()
                                            time.sleep(0.01)
                                        if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True or self.SPS01[b[4]].FlagIsDone == True or self.SPS01[b[5]].FlagIsDone == True:
                                            for p in range(b[0]):
                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                    self.SPS01[b[p]].displaymovementstop()
                                                    c=b 
                                                    c[p]=[] 
                                                    while self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving and self.SPS01[c[3]].FlagIsMoving and self.SPS01[c[4]].FlagIsMoving:
                                                        self.SPS01[c[0]].UpdateStatus() 
                                                        self.SPS01[c[1]].UpdateStatus() 
                                                        self.SPS01[c[2]].UpdateStatus() 
                                                        self.SPS01[c[3]].UpdateStatus() 
                                                        self.SPS01[c[4]].UpdateStatus()
                                                        time.sleep(0.01)
                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True or self.SPS01[c[3]].FlagIsDone == True or self.SPS01[c[4]].FlagIsDone == True:
                                                        for q in range(c[0]):
                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                self.SPS01[c[q]].displaymovementstop()
                                                                d=c 
                                                                d[q]=[] 
                                                                while self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving and self.SPS01[d[2]].FlagIsMoving and self.SPS01[d[3]].FlagIsMoving:
                                                                    self.SPS01[d[0]].UpdateStatus() 
                                                                    self.SPS01[d[1]].UpdateStatus() 
                                                                    self.SPS01[d[2]].UpdateStatus() 
                                                                    self.SPS01[d[3]].UpdateStatus()
                                                                    time.sleep(0.01)
                                                                if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone or self.SPS01[d[2]].FlagIsDone or self.SPS01[d[3]].FlagIsDone:
                                                                    for r in range(d[0]):
                                                                        if self.SPS01[d[r]].FlagIsDone == True:
                                                                            self.SPS01[d[r]].displaymovementstop()
                                                                            e=d 
                                                                            e[r]=[] 
                                                                            while self.SPS01[e[0]].FlagIsMoving and self.SPS01[e[1]].FlagIsMoving and self.SPS01[e[2]].FlagIsMoving:
                                                                                self.SPS01[e[0]].UpdateStatus() 
                                                                                self.SPS01[e[1]].UpdateStatus() 
                                                                                self.SPS01[e[2]].UpdateStatus()
                                                                                time.sleep(0.01)
                                                                            if self.SPS01[e[0]].FlagIsDone or self.SPS01[e[1]].FlagIsDone or self.SPS01[e[2]].FlagIsDone:
                                                                                for s in range(e[0]):
                                                                                    if self.SPS01[e[s]].FlagIsDone == True:
                                                                                        self.SPS01[e[s]].displaymovementstop()
                                                                                        f=e 
                                                                                        f[s]=[] 
                                                                                        while self.SPS01[f[0]].FlagIsMoving and self.SPS01[f[1]].FlagIsMoving:
                                                                                            self.SPS01[f[0]].UpdateStatus() 
                                                                                            self.SPS01[f[1]].UpdateStatus()
                                                                                            time.sleep(0.01)
                                                                                        if self.SPS01[f[0]].FlagIsDone or self.SPS01[f[1]].FlagIsDone:
                                                                                            for t in range(f[0]):
                                                                                                if self.SPS01[f[t]].FlagIsDone:
                                                                                                    self.SPS01[f[t]].displaymovementstop()
                                                                                                    g=f 
                                                                                                    g[t]=[] 
                                                                                                    while self.SPS01[g[0]].FlagIsMoving:
                                                                                                        self.SPS01[g[0]].UpdateStatus()
                                                                                                        time.sleep(0.01)
                                                                                                    if self.SPS01[g[0]].FlagIsDone:
                                                                                                        self.SPS01[g[0]].displaymovementstop()
                                                                                                    break
                                                                                        break
                                                                            break
                                                                break
                                                    break
                                        break
                            break


    ## Listener Function : Display the first device to be done and Stop (called in MulMove2)
    def CheckFirstDoneStop(self,*args):
        if len(args) == 1: ## only one syringe in motion (=numb input + self + 2more input (source and event))   
            i1=args[0] ##argsg doesnt include the self, so its size is len(args)-1. The index is the last.
            if self.SPS01[i1].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for i in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break
                    elif self.SPS01[i1].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                    if self.SPS01[i1].FlagIsDone == True:
                        self.SPS01[i1].displaymovementstop()
                        break
                    time.sleep(scan_rate)
        elif len(args) == 2: ## 2 syringes
                i1=args[0] 
                i2=args[1]
                i=[i1, i2] 
                if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                    scan_rate=0.1 ##the scan rate of the counter
                    target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours        
                    for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                        if self.Stop == True:
                            self.StopBoard()
                            break ## counter 1
                        elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                            self.SPS01[i1].UpdateStatus()
                            self.SPS01[i2].UpdateStatus()
                        if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True:
                            for j in range(i[0]): ##search for first device to be done
                                if self.SPS01[i[j]].FlagIsDone == True:
                                    self.SPS01[i[j]].displaymovementstop()
                                    a=i
                                    a[j]=[]
                                    for count2 in range(target):
                                        if self.Stop == True:
                                            self.StopBoard()
                                            break ##counter 2
                                        elif self.SPS01[a[0]].FlagIsMoving == True:
                                            self.SPS01[a[0]].UpdateStatus()
                                        if self.SPS01[a[0]].FlagIsDone == True:
                                            self.SPS01[a[0]].displaymovementstop()
                                            break ##counter 2
                                        time.sleep(scan_rate)
                                    break ## j search of first device to be done 
                            break ## counter 1
                        time.sleep(scan_rate)
        elif len(args) == 3: ## 3 syringes
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i=[i1, i2, i3] 
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] ## a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                                for count2 in range(target):
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                for count3 in range(target):
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ##counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                    if self.SPS01[b[0]].FlagIsDone == True:
                                                        self.SPS01[b[0]].displaymovementstop()
                                                        break ##counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done 
                                        break ## counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done 
                        break ## counter 1
                    time.sleep(scan_rate)
            
            
        elif len(args) == 4: ## 4 syringes
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i4=args[3]
            i=[i1, i2, i3, i4] 
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus() 
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] 
                                scan_rate=0.1 ##the scan rate of the counter
                                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours          
                                for count2 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                        self.SPS01[a[2]].UpdateStatus()    
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                scan_rate=0.1 ##the scan rate of the counter
                                                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours 
                                                for count3 in range(target):
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ## counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                    if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True:
                                                        for p in range(b[0]):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                for count4 in range(target):
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break ## counter 4
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                    if self.SPS01[c[0]].FlagIsDone == True:
                                                                        self.SPS01[c[0]].displaymovementstop()
                                                                        break ## counter 4
                                                                    time.sleep(scan_rate)
                                                                break ## p search of first device to be done
                                                        break ##counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done
                                        break ##counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done
                        break ## counter 1
                    time.sleep(scan_rate)
                                                    
        elif len(args) == 5: ## 5 syringes
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i4=args[3]
            i5=args[4]
            i=[i1, i2, i3, i4, i5] 
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus()
                        self.SPS01[i5].UpdateStatus()                            
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] 
                                for count2 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True:
                                        self.SPS01[a(0)].UpdateStatus()
                                        self.SPS01[a(1)].UpdateStatus()
                                        self.SPS01[a(2)].UpdateStatus()
                                        self.SPS01[a(3)].UpdateStatus()                                            
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                for count3 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ## counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                        self.SPS01[b[2]].UpdateStatus()                                                            
                                                    if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[1,b[2]].FlagIsDone == True:
                                                        for p in range(b[0]):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                for count4 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break ## counter 4
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                        self.SPS01[c[1]].UpdateStatus()                                                                            
                                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True:
                                                                        for q in range(c[0]):
                                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                                self.SPS01[c[q]].displaymovementstop()
                                                                                d=c
                                                                                d[q]=[]
                                                                                for count5 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                    if self.Stop == True:
                                                                                        self.StopBoard()
                                                                                        break ## counter 5
                                                                                    elif self.SPS01[d[0]].FlagIsMoving:
                                                                                        self.SPS01[d[0]].UpdateStatus()                                                                                            
                                                                                    if self.SPS01[d[0]].FlagIsDone:
                                                                                        self.SPS01[d[0]].displaymovementstop()
                                                                                        break ##counter 5
                                                                                    time.sleep(scan_rate)
                                                                                break ## q search of first device to be done
                                                                        break ## counter 4
                                                                    time.sleep(scan_rate)
                                                                break ## p search of first device to be done
                                                        break ## counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done
                                        break ## counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done
                        break ## counter 1
                    time.sleep(scan_rate)
                                                                
        elif len(args) == 6: ## 6 syringes
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i4=args[3]
            i5=args[4]
            i6=args[5]
            i=[i1, i2, i3, i4, i5, i6] 
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus()
                        self.SPS01[i5].UpdateStatus()
                        self.SPS01[i6].UpdateStatus()                            
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] 
                                for count2 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                        self.SPS01[a[2]].UpdateStatus()
                                        self.SPS01[a[3]].UpdateStatus()
                                        self.SPS01[a[4]].UpdateStatus()                                            
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                for count3 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ## counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                        self.SPS01[b[2]].UpdateStatus()
                                                        self.SPS01[b[3]].UpdateStatus()                                                            
                                                    if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True:
                                                        for p in range(b[0]):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                for count4 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break ## counter 4
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                        self.SPS01[c[1]].UpdateStatus()
                                                                        self.SPS01[c[2]].UpdateStatus()                                                                            
                                                                    if self.SPS01[c(1)].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True:
                                                                        for q in range(c[0]):
                                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                                self.SPS01[1,c(q)].displaymovementstop()
                                                                                d=c
                                                                                d[q]=[]
                                                                                for count5 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                    if self.Stop == True:
                                                                                        self.StopBoard()
                                                                                        break ## counter 5
                                                                                    elif self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving:
                                                                                        self.SPS01[d[0]].UpdateStatus()
                                                                                        self.SPS01[d[1]].UpdateStatus()                                                                                            
                                                                                    if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone:
                                                                                        for r in range(d[0]):
                                                                                            if self.SPS01[d[r]].FlagIsDone == True:
                                                                                                self.SPS01[d[r]].displaymovementstop()
                                                                                                e=d
                                                                                                e[r]=[]
                                                                                                for count6 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                    if self.Stop == True:
                                                                                                        self.StopBoard()
                                                                                                        break ## counter 6
                                                                                                    elif self.SPS01[e[0]].FlagIsMoving:
                                                                                                        self.SPS01[e[0]].UpdateStatus()                                                                                                            
                                                                                                    if self.SPS01[e[0]].FlagIsDone:
                                                                                                        self.SPS01[e[0]].displaymovementstop()
                                                                                                        break ## counter 6
                                                                                                    time.sleep(scan_rate)
                                                                                                break ## r search of first device to be done
                                                                                        break ## counter 5
                                                                                    time.sleep(scan_rate)
                                                                                break ## q search of first device to be done
                                                                        break ##counter 4
                                                                    time.sleep(scan_rate)
                                                                break ## p search of first device to be done
                                                        break ## Counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done
                                        break ## counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done
                        break ## counter 1
                    time.sleep(scan_rate)
                                                        
        elif len(args) == 7: ##7 syringes
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i4=args[3]
            i5=args[4]
            i6=args[5]
            i7=args[6]
            i=[i1, i2, i3, i4, i5, i6, i7] 
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus()
                        self.SPS01[i5].UpdateStatus()
                        self.SPS01[i6].UpdateStatus()
                        self.SPS01[i7].UpdateStatus()
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True or self.SPS01[i7].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] 
                                for count2 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True and self.SPS01[a[5]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                        self.SPS01[a[2]].UpdateStatus()
                                        self.SPS01[a[3]].UpdateStatus()
                                        self.SPS01[a[4]].UpdateStatus()
                                        self.SPS01[a[5]].UpdateStatus()
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True or self.SPS01[a[5]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                for count3 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ## counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                        self.SPS01[b[2]].UpdateStatus()
                                                        self.SPS01[b[3]].UpdateStatus()
                                                        self.SPS01[b[4]].UpdateStatus()
                                                    if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True or self.SPS01[b[4]].FlagIsDone == True:
                                                        for p in range(b[0]):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                for count4 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break ## counter 4
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving and self.SPS01[c[3]].FlagIsMoving:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                        self.SPS01[c[1]].UpdateStatus()
                                                                        self.SPS01[c[2]].UpdateStatus()
                                                                        self.SPS01[c[3]].UpdateStatus()
                                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True or self.SPS01[c[3]].FlagIsDone == True:
                                                                        for q in range(c[0]):
                                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                                self.SPS01[c[q]].displaymovementstop()
                                                                                d=c
                                                                                d[q]=[]
                                                                                for count5 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                    if self.Stop == True:
                                                                                        self.StopBoard()
                                                                                        break ## counter 5
                                                                                    elif self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving and self.SPS01[d[2]].FlagIsMoving:
                                                                                        self.SPS01[d[0]].UpdateStatus()
                                                                                        self.SPS01[d[1]].UpdateStatus()
                                                                                        self.SPS01[d[2]].UpdateStatus()
                                                                                    if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone or self.SPS01[d[2]].FlagIsDone:
                                                                                        for r in range(d[0]):
                                                                                            if self.SPS01[d[r]].FlagIsDone == True:
                                                                                                self.SPS01[d[r]].displaymovementstop()
                                                                                                e=d
                                                                                                e[r]=[]
                                                                                                for count6 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                    if self.Stop == True:
                                                                                                        self.StopBoard()
                                                                                                        break ## counter 6
                                                                                                    elif self.SPS01[e[0]].FlagIsMoving and self.SPS01[e[1]].FlagIsMoving:
                                                                                                        self.SPS01[e[0]].UpdateStatus()
                                                                                                        self.SPS01[e[1]].UpdateStatus()
                                                                                                    if self.SPS01[e[0]].FlagIsDone or self.SPS01[e[1]].FlagIsDone:
                                                                                                        for s in range(e[0]):
                                                                                                            if self.SPS01[e[s]].FlagIsDone == True:
                                                                                                                self.SPS01[e[s]].displaymovementstop()
                                                                                                                f=e
                                                                                                                f[s]=[]
                                                                                                                for count7 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                                    if self.Stop == True:
                                                                                                                        self.StopBoard()
                                                                                                                        break ## counter 7
                                                                                                                    elif self.SPS01[f[0]].FlagIsMoving:
                                                                                                                        self.SPS01[f[0]].UpdateStatus()
                                                                                                                    if self.SPS01[f[0]].FlagIsDone:
                                                                                                                        self.SPS01[f[0]].displaymovementstop()
                                                                                                                        break ## counter 7
                                                                                                                    time.sleep(scan_rate)
                                                                                                                break ## s search of first device to be done
                                                                                                        break ## counter 6
                                                                                                    time.sleep(scan_rate)
                                                                                                break ## r search of first device to be done
                                                                                        break ## counter 5
                                                                                    time.sleep(scan_rate)
                                                                                break ## q search of first device to be done
                                                                        break ## counter 4
                                                                    time.sleep(scan_rate)
                                                                break ## p search of first device to be done
                                                        break ## counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done
                                        break ## counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done
                        break ## counter 1
                    time.sleep(scan_rate)
                        
        elif len(args) == 8: ##8 syringes (impossible - max is 7)
            i1=args[0] 
            i2=args[1]
            i3=args[2]
            i4=args[3]
            i5=args[4]
            i6=args[5]
            i7=args[6]
            i8=args[7]
            i=[i1, i2, i3, i4, i5, i6, i7, i8] ##i=args[3:len(args)-1]
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break ## counter 1
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True and self.SPS01[i8].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus()
                        self.SPS01[i5].UpdateStatus()
                        self.SPS01[i6].UpdateStatus()
                        self.SPS01[i7].UpdateStatus()
                        self.SPS01[i8].UpdateStatus()
                    if self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True or self.SPS01[i7].FlagIsDone == True or self.SPS01[i8].FlagIsDone == True:
                        for j in range(i[0]):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[] 
                                for count2 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break ## counter 2
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True and self.SPS01[a[5]].FlagIsMoving == True and self.SPS01[a[6]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                        self.SPS01[a[2]].UpdateStatus()
                                        self.SPS01[a[3]].UpdateStatus()
                                        self.SPS01[a[4]].UpdateStatus()
                                        self.SPS01[a[5]].UpdateStatus()
                                        self.SPS01[a[6]].UpdateStatus()
                                    if self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True or self.SPS01[a[5]].FlagIsDone == True or self.SPS01[a[6]].FlagIsDone == True:
                                        for k in range(a[0]):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                for count3 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break ## counter 3
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True and self.SPS01[b[5]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                        self.SPS01[b[2]].UpdateStatus()
                                                        self.SPS01[b[3]].UpdateStatus()
                                                        self.SPS01[b[4]].UpdateStatus()
                                                        self.SPS01[b[5]].UpdateStatus()
                                                    if self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True or self.SPS01[b[4]].FlagIsDone == True or self.SPS01[b[5]].FlagIsDone == True:
                                                        for p in range(b[0]):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                for count4 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break ## counter 4
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving and self.SPS01[c[3]].FlagIsMoving and self.SPS01[c[4]].FlagIsMoving:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                        self.SPS01[c[1]].UpdateStatus()
                                                                        self.SPS01[c[2]].UpdateStatus()
                                                                        self.SPS01[c[3]].UpdateStatus()
                                                                        self.SPS01[c[4]].UpdateStatus()                                                                           
                                                                    if self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True or self.SPS01[c[3]].FlagIsDone == True or self.SPS01[c[4]].FlagIsDone == True:
                                                                        for q in range(c[0]):
                                                                            if self.SPS01[c[q]].FlagIsDone == True:
                                                                                self.SPS01[c[q]].displaymovementstop()
                                                                                d=c
                                                                                d[q]=[]
                                                                                for count5 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                    if self.Stop == True:
                                                                                        self.StopBoard()
                                                                                        break ## counter 5
                                                                                    elif self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving and self.SPS01[d[2]].FlagIsMoving and self.SPS01[d[3]].FlagIsMoving:
                                                                                        self.SPS01[d[0]].UpdateStatus()
                                                                                        self.SPS01[d[1]].UpdateStatus()
                                                                                        self.SPS01[d[2]].UpdateStatus()
                                                                                        self.SPS01[d[3]].UpdateStatus()
                                                                                    if self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone or self.SPS01[d[2]].FlagIsDone or self.SPS01[d[3]].FlagIsDone:
                                                                                        for r in range(d[0]):
                                                                                            if self.SPS01[d[r]].FlagIsDone == True:
                                                                                                self.SPS01[d[r]].displaymovementstop()
                                                                                                e=d
                                                                                                e[r]=[]
                                                                                                for count6 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                    if self.Stop == True:
                                                                                                        self.StopBoard()
                                                                                                        break ## counter 6
                                                                                                    elif self.SPS01[e[0]].FlagIsMoving and self.SPS01[e[1]].FlagIsMoving and self.SPS01[e[2]].FlagIsMoving:
                                                                                                        self.SPS01[e[0]].UpdateStatus()
                                                                                                        self.SPS01[e[1]].UpdateStatus()
                                                                                                        self.SPS01[e[2]].UpdateStatus()
                                                                                                    if self.SPS01[e[0]].FlagIsDone or self.SPS01[e[1]].FlagIsDone or self.SPS01[e[2]].FlagIsDone:
                                                                                                        for s in range(e[0]):
                                                                                                            if self.SPS01[e[s]].FlagIsDone == True:
                                                                                                                self.SPS01[e[s]].displaymovementstop()
                                                                                                                f=e
                                                                                                                f[s]=[]
                                                                                                                for count7 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                                    if self.Stop == True:
                                                                                                                        self.StopBoard()
                                                                                                                        break ## counter 7
                                                                                                                    elif self.SPS01[f[0]].FlagIsMoving and self.SPS01[f[1]].FlagIsMoving:
                                                                                                                        self.SPS01[f[0]].UpdateStatus()
                                                                                                                        self.SPS01[f[1]].UpdateStatus()
                                                                                                                    if self.SPS01[f[0]].FlagIsDone or self.SPS01[f[1]].FlagIsDone:
                                                                                                                        for t in range(f[0]):
                                                                                                                            if self.SPS01[f[t]].FlagIsDone:
                                                                                                                                self.SPS01[f[t]].displaymovementstop()
                                                                                                                                g=f
                                                                                                                                g[t]=[]
                                                                                                                                for count8 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                                                                                                                                    if self.Stop == True:
                                                                                                                                        self.StopBoard()
                                                                                                                                        break ## counter 8
                                                                                                                                    elif self.SPS01[g(0)].FlagIsMoving:
                                                                                                                                        self.SPS01[g[0]].UpdateStatus()
                                                                                                                                    if self.SPS01[g[0]].FlagIsDone:
                                                                                                                                        self.SPS01[g[0]].displaymovementstop()
                                                                                                                                        break ## counter 8
                                                                                                                                    time.sleep(scan_rate)
                                                                                                                                break ## t search of first device to be done
                                                                                                                        break ##counter 7
                                                                                                                    time.sleep(scan_rate)
                                                                                                                break ## s search of first device to be done
                                                                                                        break ## counter 6
                                                                                                    time.sleep(scan_rate)
                                                                                                break ## r search of first device to be done
                                                                                        break ## counter 5
                                                                                    time.sleep(scan_rate)
                                                                                break ## q search of first device to be done
                                                                        break ## counter 4
                                                                    time.sleep(scan_rate)
                                                                break ## p search of first device to be done
                                                        break ##counter 3
                                                    time.sleep(scan_rate)
                                                break ## k search of first device to be done
                                        break ## counter 2
                                    time.sleep(scan_rate)
                                break ## j search of first device to be done
                        break ##counter 1
                    time.sleep(scan_rate)

    ##  Set Valves
    def SetValves(self, d1 = None,v11 = None,v12 = None,v13 = None, v14 = None, d2 = None, v21 = None, v22 = None, v23 = None, v24 = None): 
        if self.Stop == False:
            if [d1,v11,v12,v13,v14,d2,v21,v22,v23,v24].count(None)%2 ==0:
                print('Error, missing input. Number of inputs has to be odd (name of manifold and the four corresponding valve entries).')
            else:
                if v14 != None and d2 == None: ## 1 manifold as input
                    i1=self.FindIndexM(d1)
                    self.addlistener('FirstDoneStopM', "listener_firstdoneM", self.CheckFirstDoneStopM, [i1]) ##it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                    if len(self.C4VM) == 1:
                        if self.C4VM[i1].FlagIsDone == True:
                            self.C4VM[i1].device.CmdSetValves(np.int8(v11),np.int8(v12),np.int8(v13),np.int8(v14))                              
                            self.C4VM[i1].displayswitch(v11,v12,v13,v14)
                            if self.C4VM[i1].FlagIsDone == False: 
                                self.notify('FirstDoneStopM')
                elif  v24 != None: ## 2 manifolds as input
                    i1=self.FindIndexM(d1)
                    i2=self.FindIndexM(d2) 
                    self.addlistener('FirstDoneStopM', "listener_firstdoneM", self.CheckFirstDoneStopM, [i1, i2]) ##it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                    if len(self.C4VM) == 2:
                        if self.C4VM[i1].FlagIsDone == True and self.C4VM[i2].FlagIsDone == True:
                            self.C4VM[i1].device.CmdSetValves(np.int8(v11),np.int8(v12),np.int8(v13),np.int8(v14))
                            self.C4VM[i2].device.CmdSetValves(np.int8(v21),np.int8(v22),np.int8(v23),np.int8(v24))
                            self.C4VM[i1].displayswitch(v11,v12,v13,v14)
                            self.C4VM[i2].displayswitch(v21,v22,v23,v24)  
                            if self.C4VM[i1].FlagIsDone == False and self.C4VM[i2].FlagIsDone == False:
                                self.notify('FirstDoneStopM')
                else:
                    print("Error, wrong number of inputs.")

    ## Check First Done Stop M
    def CheckFirstDoneStopM(self, *args):
        if len(args) == 1: ## only one manifold in motion (=numb input + self + 2more input (source and event))  
            i1=args[0] ## The index is the last.
            if self.C4VM[i1].FlagIsDone == False:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break
                    elif self.C4VM[i1].FlagIsDone == False:
                        self.C4VM[i1].UpdateStatus()
                    if self.C4VM[i1].FlagIsDone == True:
                        self.C4VM[i1].displayswitchstop()
                        break
                    time.sleep(scan_rate)
            elif len(args) == 2: ## only two manifolds
                i1=args[0]
                i2=args[1]
                i=[i1, i2] 
                if self.C4VM[i1].FlagIsDone == False and self.C4VM[i2].FlagIsDone == False:
                    scan_rate=0.1 ##the scan rate of the counter
                    target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours        
                    for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                        if self.Stop == True:
                            self.StopBoard()
                            break ## counter 1
                        elif self.C4VM[i1].FlagIsDone == False and self.C4VM[i2].FlagIsDone == False:
                            self.C4VM[i1].UpdateStatus()
                            self.C4V[i2].UpdateStatus()
                        if self.C4VM[i1].FlagIsDone == True or self.C4VM[i2].FlagIsDone == True:
                            for j in range(len(i)): ##search for first device to be done
                                if self.C4VM[i[j]].FlagIsDone == True:
                                    self.C4VM[i[j]].displayswitchstop()
                                    a=i
                                    a[j]=[]
                                    for count2 in range(target):
                                        if self.Stop == True:
                                            self.StopBoard()
                                            break ##counter 2
                                        elif self.C4VM[a[1]].FlagIsDone == False:
                                            self.C4VM[a[1]].UpdateStatus()
                                        if self.C4VM[a[1]].FlagIsDone == True:
                                            self.C4VM[a[1]].displayswitchstop()
                                            break ##counter 2
                                        time.sleep(scan_rate)
                                    break ## j search of first device to be done 
                            break ## counter 1
                        time.sleep(scan_rate)

    ## Pause : same as stop but with different comment
    def PauseBoard (self):
        for i in range(len(self.SPS01)):
            self.SPS01[i].device.CmdStop()
            self.SPS01[i].FlagReady = True
            # UpdateStatus(self.SPS01{1,i}) ## i update the status in the listener function CheckFirstDoneStopPause before i recall the MulMove3 in the pause               
        for i in range(len(self.C4VM)):
            self.C4VM[i].device.CmdStop()
            self.C4VM[i].UpdateStatus()
        for i in range(len(self.C4AM)):
            self.C4AM[i].Stop()
        for i in range(len(self.C4PM)):
            self.C4PM[i].Stop()
        for i in range(len(self.CEP01)):
            self.CEP01[i].Stop()
        self.ClockStop = datetime.now()
        comment=f"{self.ClockStop.strftime('%X')} Interface paused by the user."
        with open(output_txt_path(), "a") as OUTPUT:
            OUTPUT.write(comment + "\n")
            print(comment)

    ## Listener Function : Display the first device to be done and Stop and Pause (called in MulMove3)
    def CheckFirstDoneStopPause(self,*args):
        if len(args) == 3: #only one syringe in motion (=numb input + obj + 2more input (source and event))   
            i1=args[0] #vararging doesn't include the obj, so its size is nargin-1. The index is the last.
            d1=args[1]
            v1=args[2]
            if self.SPS01[i1].FlagIsMoving == True:  
                scan_rate=0.1 #the scan rate of the counter
                target=(48)*60*60 #/scan_rate; #this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): #this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        com=self.StopBoard()
                        break #counter1
                    elif self.Pause == True:
                        self.PauseBoard()
                        for count_pause1 in range(target):
                            if self.Stop == True:                                                              
                                break #count_pause1
                            elif self.Resume == True:
                                self.ClockResume = datetime.now()
                                comment=f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                with open(output_txt_path(),"a") as OUTPUT:
                                    OUTPUT.write(comment +"\n")
                                    print(comment) 
                                self.SPS01[i1].UpdateStatus()
                                self.MulMove3(d1,v1)                               
                                self.flag_break_countpause = 1
                                break #count_pause1
                            time.sleep(scan_rate)
                    elif self.SPS01[i1].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break #counter1
                    elif self.SPS01[i1].FlagIsDone == True: 
                        self.SPS01[i1].displaymovementstop()
                        break #counter1
                    time.sleep(scan_rate)
        elif len(args) == 6: # 2 syringes
            i1=args[0] 
            d1=args[1]
            v1=args[2]
            i2=args[3]
            d2=args[4]
            v2=args[5]
            i=[i1, i2]
            d=[d1, d2]
            v=[v1, v2]
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True: 
                scan_rate=0.1 #the scan rate of the counter
                target=(48)*60*60 #scan_rate; //this is the final time of the counter. It is equal to max 48 hours        
                for count1 in range (target): #this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break # counter 1
                    elif self.Pause == True:
                        self.PauseBoard()
                        for count_pause1 in range (target):
                            if self.Stop == True:
                                break #count_pause1
                            elif self.Resume == True:
                                self.ClockResume = datetime.now
                                comment=f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                with open(output_txt_path(),"a") as OUTPUT:
                                    OUTPUT.write(comment + "\n")
                                print(comment)
                                self.SPS01[i1].UpdateStatus() #////////////////////////////
                                self.SPS01[i2].UpdateStatus() #////////////////////////////
                                self.MulMove3(d1,v1,d2,v2)                              
                                self.flag_break_countpause = 1
                                break #count_pause1
                            time.sleep(scan_rate)
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break #counter1                        
                    elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True:
                        for j in range(len(i[0])): #search for first device to be done
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[]
                                ad=d
                                ad[j]=[]
                                av=v
                                av[j]=[]
                                for count2 in range (target):
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break #counter 2
                                    elif self.Pause == True:
                                        self.PauseBoard()
                                        for count_pause1 in range (target):
                                            if self.Stop == True:
                                                break #count_pause1
                                            elif self.Resume == True:
                                                self.ClockResume = datetime.now()
                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                with open(output_txt_path(), "a") as OUTPUT:
                                                    OUTPUT.write(comment + "\n")
                                                print(comment)
                                                self.SPS01[a(0)].UpdateStatus() #////////////////////////////
                                                self.MulMove3(ad[0],av[0])                                    
                                                self.flag_break_countpause = 1
                                                break #count_pause1
                                            time.sleep(scan_rate)
                                    elif self.SPS01[a(0)].FlagIsMoving == True:
                                        self.SPS01[a(0)].UpdateStatus()
                                    if self.flag_break_countpause == 1:
                                        break #counter1  
                                    elif self.SPS01[a(0)].FlagIsDone == True:
                                        self.SPS01[a(0)].displaymovementstop()
                                        break #/counter 2                                          
                                    time.sleep(scan_rate)                                          
                                break # j search of first device to be done                                                                        
                        break # counter 1
                    time.sleep(scan_rate)            
                    
        elif len(args) == 9: # 3 syringes
            i1=args[0] 
            d1=args[1]
            v1=args[2]
            i2=args[3]
            d2=args[4]
            v2=args[5]
            i3=args[6]
            d3=args[7]
            v3=args[8]
            i=[i1, i2, i3]
            d=[d1, d2, d3]
            v=[v1, v2, v3]
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True: 
                scan_rate=0.1; #the scan rate of the counter
                target=(48)*60*60 #scan_rate; //this is the final time of the counter. It is equal to max 48 hours
                for count1 in range(target): #this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break # counter 1                            
                    elif self.Pause == True:
                        self.PauseBoard()
                        for count_pause1 in range(target):
                            if self.Stop == True:
                                break #count_pause1
                            elif self.Resume == True:
                                self.ClockResume = datetime.now()
                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                with open(output_txt_path(), "a") as OUTPUT:
                                    OUTPUT.write(comment + "\n")
                                print(comment) 
                                self.SPS01[i1].UpdateStatus() #////////////////////////////
                                self.SPS01[i2].UpdateStatus() #////////////////////////////
                                self.SPS01[i3].UpdateStatus() #////////////////////////////
                                self.MulMove3(d1,v1,d2,v2,d3,v3)                                  
                                self.flag_break_countpause = 1
                                break #count_pause1
                            time.sleep(scan_rate)
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break #counter1  
                    elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True:
                        for j in range(len(i[0])):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[]; # a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                                ad=d
                                ad[j]=[]
                                av=v
                                av[j]=[]
                                for count2 in range (target):
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break # counter 2                                            
                                    elif self.Pause == True:
                                        self.PauseBoard()
                                        for count_pause1 in range (target):
                                            if self.Stop == True:
                                                break #count_pause1
                                            elif self.Resume == True:
                                                self.ClockResume = datetime.now()
                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                with open(output_txt_path(), "a") as OUTPUT:
                                                    OUTPUT.write(comment + "\n")
                                                print(comment)
                                                self.SPS01[a[0]].UpdateStatus() #////////////////////////////
                                                self.SPS01[a[1]].UpdateStatus() #////////////////////////////
                                                self.MulMove3(ad[1],av[1],ad[2],av[2])                            
                                                self.flag_break_countpause = 1
                                                break #count_pause1
                                            time.sleep(scan_rate)                                             
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[1,a[1]].UpdateStatus()
                                    if self.flag_break_countpause == 1:
                                        break #counter1  
                                    elif self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True:
                                        for k in range(len(a[0])):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                bd=ad
                                                bd[k]=[]
                                                bv=av
                                                bv[k]=[]
                                                for count3 in range(target):
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break #counter 3                                                            
                                                    elif self.Pause == True:
                                                        self.PauseBoard()
                                                        for count_pause1 in range(target):
                                                            if self.Stop == True:
                                                                break #count_pause1
                                                            elif self.Resume == True:
                                                                self.ClockResume = datetime.now()
                                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                with open(output_txt_path(), "a") as OUTPUT:
                                                                    OUTPUT.write(comment + "\n")
                                                                print(comment)
                                                                self.SPS01[b[0]].UpdateStatus() #////////////////////////////
                                                                self.MulMove3[bd[1],bv[1]]                                  
                                                                self.flag_break_countpause = 1
                                                                break #count_pause1
                                                            time.sleep(scan_rate)                                                           
                                                    elif self.SPS01[b[0]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                    if self.flag_break_countpause == 1:
                                                        break #counter1  
                                                    elif self.SPS01[b[0]].FlagIsDone == True:
                                                        self.SPS01[b[0]].displaymovementstop()
                                                        break #counter 3
                                                    time.sleep(scan_rate)
                                                break # k search of first device to be done 
                                        break # counter 2                                      
                                    time.sleep(scan_rate)
                                break # j search of first device to be done 
                        break # counter 1
                    time.sleep(scan_rate)


        elif len(args) == 12: # 4 syringes
            i1=args[0]
            d1=args[1]
            v1=args[2]
            i2=args[3]
            d2=args[4]
            v2=args[5]
            i3=args[6]
            d3=args[7]
            v3=args[8]
            i4=args[9]
            d4=args[10]
            v4=args[11]
            i=[i1, i2, i3, i4]
            d=[d1, d2, d3, d4]
            v=[v1, v2, v3, v4]
            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                scan_rate=0.1 #the scan rate of the counter
                target=(48)*60*60 #scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): #this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break # counter 
                    elif self.Pause == True:
                        self.PauseBoard()
                        for count_pause1 in range(target):
                            if self.Stop == True:
                                break #count_pause1
                            elif self.Resume == True:
                                self.ClockResume = datetime.now()
                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                with open(output_txt_path(), "a") as OUTPUT:
                                    OUTPUT.write(comment + "\n")
                                print(comment)
                                self.SPS01[i1].UpdateStatus() #////////////////////////////
                                self.SPS01[i2].UpdateStatus() #////////////////////////////
                                self.SPS01[i3].UpdateStatus() #////////////////////////////
                                self.SPS01[i4].UpdateStatus() #////////////////////////////
                                self.MulMove3(d1,v1,d2,v2,d3,v3,d4,v4)                                
                                self.flag_break_countpause = 1
                                break #count_pause1
                            time.sleep(scan_rate)                         
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                        self.SPS01[i3].UpdateStatus()
                        self.SPS01[i4].UpdateStatus() 
                    if self.flag_break_countpause == 1:
                        break #counter1  
                    elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True:
                        for j in range(len(i[0])):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                a=i
                                a[j]=[]
                                ad=d
                                ad[j]=[]
                                av=v
                                av[j]=[]
                                scan_rate=0.1 #the scan rate of the counter
                                target=(48)*60*60 #/scan_rate; //this is the final time of the counter. It is equal to max 48 hours          
                                for count2 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                    if self.Stop == True:
                                        self.StopBoard()
                                        break # counter 2
                                    elif self.Pause == True:
                                        self.PauseBoard()
                                        for count_pause1 in range (target):
                                            if self.Stop == True:
                                                break #count_pause1
                                            elif self.Resume == True:
                                                self.ClockResume = datetime.now()
                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                with open(output_txt_path(), "a") as OUTPUT:
                                                    OUTPUT.write(comment + "\n")
                                                print(comment)
                                                self.SPS01[a[0]].UpdateStatus() #////////////////////////////
                                                self.SPS01[a[1]].UpdateStatus() #////////////////////////////                                                    
                                                self.SPS01[a[2]].UpdateStatus() #////////////////////////////
                                                self.MulMove3(ad[1],av[1],ad[2],av[2],ad[3],av[3])                                   
                                                self.flag_break_countpause = 1
                                                break #count_pause1
                                            time.sleep(scan_rate)                                           
                                    elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True:
                                        self.SPS01[a[0]].UpdateStatus()
                                        self.SPS01[a[1]].UpdateStatus()
                                        self.SPS01[a[2]].UpdateStatus()    
                                    if self.flag_break_countpause == 1:
                                        break #counter1  
                                    elif self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True:
                                        for k in range(len(a[0])):
                                            if self.SPS01[a[k]].FlagIsDone == True:
                                                self.SPS01[a[k]].displaymovementstop()
                                                b=a
                                                b[k]=[]
                                                bd=ad
                                                bd[k]=[]
                                                bv=av
                                                bv[k]=[]
                                                scan_rate=0.1; #the scan rate of the counter
                                                target=(48)*60*60 #/scan_rate; //this is the final time of the counter. It is equal to max 48 hours 
                                                for count3 in range (target):
                                                    if self.Stop == True:
                                                        self.StopBoard()
                                                        break # counter 3
                                                    elif self.Pause == True:
                                                        self.PauseBoard()
                                                        for count_pause1 in range(target):
                                                            if self.Stop == True:
                                                                break #count_pause1
                                                            elif self.Resume == True:
                                                                self.ClockResume = datetime.now()
                                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                with open(output_txt_path(), "a") as OUTPUT:
                                                                    OUTPUT.write(comment + "\n")
                                                                print(comment)
                                                                self.SPS01[b[0]].UpdateStatus() #////////////////////////////
                                                                self.SPS01[b[1]].UpdateStatus() #////////////////////////////
                                                                self.MulMove3(bd[1],bv[1],bd[2],bv[2])                                  
                                                                self.flag_break_countpause = 1
                                                                break #count_pause1
                                                            time.sleep(scan_rate)  
                                                    elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True:
                                                        self.SPS01[b[0]].UpdateStatus()
                                                        self.SPS01[b[1]].UpdateStatus()
                                                    if self.flag_break_countpause == 1:
                                                        break #counter1  
                                                    elif self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True:
                                                        for p in range(len(b[0])):
                                                            if self.SPS01[b[p]].FlagIsDone == True:
                                                                self.SPS01[b[p]].displaymovementstop()
                                                                c=b
                                                                c[p]=[]
                                                                cd=bd
                                                                cd[p]=[]
                                                                cv=bv
                                                                cv[p]=[]
                                                                for count4 in range (target):
                                                                    if self.Stop == True:
                                                                        self.StopBoard()
                                                                        break # counter 4
                                                                    elif self.Pause == True:
                                                                        self.PauseBoard()
                                                                        for count_pause1 in range(target):
                                                                            if self.Stop == True:
                                                                                break #count_pause1
                                                                            elif self.Resume == True:
                                                                                self.ClockResume = datetime.now()
                                                                                comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                with open(output_txt_path(), "a") as OUTPUT:
                                                                                    OUTPUT.write(comment + "\n")
                                                                                print(comment)
                                                                                self.SPS01[c[0]].UpdateStatus() #////////////////////////////
                                                                                self.MulMove3(cd[1],cv[1])                                    
                                                                                self.flag_break_countpause = 1
                                                                                break #count_pause1
                                                                            time.sleep(scan_rate)  
                                                                    elif self.SPS01[c[0]].FlagIsMoving == True:
                                                                        self.SPS01[c[0]].UpdateStatus()
                                                                    if self.flag_break_countpause == 1:
                                                                        break #counter1
                                                                    elif self.SPS01[c[0]].FlagIsDone == True:
                                                                        self.SPS01[c[0]].displaymovementstop()
                                                                        break # counter 4
                                                                    time.sleep(scan_rate)
                                                                break # p search of first device to be done
                                                        break #counter 3                                                       
                                                    time.sleep(scan_rate)
                                                break # k search of first device to be done
                                        break #counter 2
                                    time.sleep(scan_rate)
                                break # j search of first device to be done
                        break # counter 1
                    time.sleep(scan_rate)
                    

            elif len(args) == 15: # 5 syringes
                i1=args[0] 
                d1=args[1]
                v1=args[2]
                i2=args[3]
                d2=args[4]
                v2=args[5]
                i3=args[6]
                d3=args[7]
                v3=args[8]
                i4=args[9]
                d4=args[10]
                v4=args[11]
                i5=args[12]
                d5=args[13]
                v5=args[14]
                i=[i1, i2, i3, i4, i5]
                d=[d1, d2, d3, d4, d5]
                v=[v1, v2, v3, v4, v5]
                if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                    scan_rate=0.1 #the scan rate of the counter
                    target=(48)*60*60 #/scan_rate //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1 in range (target): #//this is a counter clock to check if the stop_status variable has changed
                        if self.Stop == True:
                            self.StopBoard()
                            break # counter 1
                        elif self.Pause == True:
                            self.PauseBoard()
                            for count_pause1 in range(target):
                                if self.Stop == True:
                                    break #count_pause1
                                elif self.Resume == True:
                                    self.ClockResume = datetime.now()
                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                    with open(output_txt_path(), "a") as OUTPUT:
                                        OUTPUT.write(comment + "\n")
                                    print(comment)
                                    self.SPS01[i1].UpdateStatus() #////////////////////////////
                                    self.SPS01[i2].UpdateStatus() # ////////////////////////////
                                    self.SPS01[i3].UpdateStatus() #////////////////////////////
                                    self.SPS01[i4].UpdateStatus() #////////////////////////////
                                    self.SPS01[i5].UpdateStatus() #////////////////////////////
                                    self.MulMove3(d1,v1,d2,v2,d3,v3,d4,v4,d5,v5)                                  
                                    self.flag_break_countpause = 1
                                    break #count_pause1
                                time.sleep(scan_rate)
                        elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                            self.SPS01[i1].UpdateStatus()
                            self.SPS01[i2].UpdateStatus()
                            self.SPS01[i3].UpdateStatus()
                            self.SPS01[i4].UpdateStatus()
                            self.SPS01[i5].UpdateStatus()                           
                        if self.flag_break_countpause == 1:
                            break #counter1  
                        elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True:
                            for j in range(len(i[0])):
                                if self.SPS01[i[j]].FlagIsDone == True:
                                    self.SPS01[i[j]].displaymovementstop()
                                    a=i
                                    a[j]=[]
                                    ad=d
                                    ad[j]=[]
                                    av=v
                                    av[j]=[]
                                    for count2 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                        if self.Stop == True:
                                            self.StopBoard()
                                            break # counter 2
                                        elif self.Pause == True:
                                            self.PauseBoard()
                                            for count_pause1 in range(target):
                                                if self.Stop == True:
                                                    break #count_pause1
                                                elif self.Resume == True:
                                                    self.ClockResume = datetime.now()
                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                        OUTPUT.write(comment + "\n")
                                                    print(comment)
                                                    self.SPS01[a[0]].UpdateStatus() #////////////////////////////
                                                    self.SPS01[a[1]].UpdateStatus() #////////////////////////////                                                    
                                                    self.SPS01[a[2]].UpdateStatus() #////////////////////////////                                                   
                                                    self.SPS01[a[3]].UpdateStatus() #////////////////////////////
                                                    self.MulMove3(ad[1],av[1],ad[2],av[2],ad[3],av[3],ad[4],av[4])                                   
                                                    self.flag_break_countpause = 1
                                                    break #count_pause1
                                                time.sleep(scan_rate)   
                                        elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True:
                                            self.SPS01[a[0]].UpdateStatus()
                                            self.SPS01[a[1]].UpdateStatus()
                                            self.SPS01[a[2]].UpdateStatus()
                                            self.SPS01[a[3]].UpdateStatus()                                            
                                        if self.flag_break_countpause == 1:
                                            break #counter1  
                                        elif self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True:
                                            for k in range(len(a[0])):
                                                if self.SPS01[a[k]].FlagIsDone == True:
                                                    self.SPS01[a[k]].displaymovementstop()
                                                    b=a
                                                    b[k]=[]
                                                    bd=ad
                                                    bd[k]=[]
                                                    bv=av
                                                    bv[k]=[]
                                                    for count3 in range(target): #//this is a counter clock to check if the stop_status variable has changed
                                                        if self.Stop == True:
                                                            self.StopBoard()
                                                            break # counter 3
                                                        elif self.Pause == True:
                                                            self.PauseBoard()
                                                            for count_pause1 in range(target):
                                                                if self.Stop == True:
                                                                    break #count_pause1
                                                                elif self.Resume == True:
                                                                    self.ClockResume = datetime.now()
                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                        OUTPUT.write(comment + "\n")
                                                                    print(comment)
                                                                    self.SPS01[b[0]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[1]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[2]].UpdateStatus() #////////////////////////////
                                                                    self.MulMove3(bd[1],bv[1],bd[2],bv[2],bd[3],bv[3])                                   
                                                                    self.flag_break_countpause = 1
                                                                    break #count_pause1
                                                                time.sleep(scan_rate)
                                                        elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True:
                                                            self.SPS01[b[0]].UpdateStatus()
                                                            self.SPS01[b[1]].UpdateStatus()
                                                            self.SPS01[b[2]].UpdateStatus()                                                           
                                                        if self.flag_break_countpause == 1:
                                                            break #counter1  
                                                        elif self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True:
                                                            for p in range(len(b[0])):
                                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                                    self.SPS01[b[p]].displaymovementstop()
                                                                    c=b
                                                                    c[p]=[]
                                                                    cd=bd
                                                                    cd[p]=[]
                                                                    cv=bv
                                                                    cv[p]=[]
                                                                    for count4 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                        if self.Stop == True:
                                                                            self.StopBoard()
                                                                            break # counter 4
                                                                        elif self.Pause == True:
                                                                            self.PauseBoard()
                                                                            for count_pause1 in range(target):
                                                                                if self.Stop == True:
                                                                                    break #count_pause1
                                                                                elif self.Resume == True:
                                                                                    self.ClockResume = datetime.now()
                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                        OUTPUT.write(comment + "\n")
                                                                                    print(comment)
                                                                                    self.SPS01[c[0]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[1]].UpdateStatus() #////////////////////////////
                                                                                    self.MulMove3(cd[1],cv[1],cd[2],cv[2])                                 
                                                                                    self.flag_break_countpause = 1
                                                                                    break #count_pause1
                                                                                time.sleep(scan_rate)    
                                                                        elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving:
                                                                            self.SPS01[c[0]].UpdateStatus()
                                                                            self.SPS01[c[1]].UpdateStatus()                                                                            
                                                                        if self.flag_break_countpause == 1:
                                                                            break #counter1
                                                                        elif self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True:
                                                                            for q in range(len(c[0])):
                                                                                if self.SPS01[c[q]].FlagIsDone == True:
                                                                                    self.SPS01[1,c[q]].displaymovementstop()
                                                                                    d=c
                                                                                    d[q]=[]
                                                                                    dd=cd
                                                                                    dd[q]=[]
                                                                                    dv=cv
                                                                                    dv[q]=[]
                                                                                    for count5 in range(target): #//this is a counter clock to check if the stop_status variable has changed
                                                                                        if self.Stop == True:
                                                                                            self.StopBoard()
                                                                                            break # counter 5                                                                                            
                                                                                        elif self.Pause == True:
                                                                                            self.PauseBoard()
                                                                                            for count_pause1 in range(target):
                                                                                                if self.Stop == True:
                                                                                                    break #count_pause1
                                                                                                elif self.Resume == True:
                                                                                                    self.ClockResume = datetime.now()
                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                    print(comment)
                                                                                                    self.SPS01[d[0]].UpdateStatus() #////////////////////////////
                                                                                                    self.MulMove3(dd[1],dv[1])                                    
                                                                                                    self.flag_break_countpause = 1
                                                                                                    break #count_pause1
                                                                                                time.sleep(scan_rate)   
                                                                                        elif self.SPS01[d[0]].FlagIsMoving:
                                                                                            self.SPS01[d[0]].UpdateStatus()                                                                                         
                                                                                        if self.flag_break_countpause == 1:
                                                                                            break #counter1
                                                                                        elif self.SPS01[d[0]].FlagIsDone:
                                                                                            self.SPS01[d[0]].displaymovementstop()
                                                                                            break #counter 5
                                                                                        time.sleep(scan_rate)                                                                                   
                                                                                    break # q search of first device to be done
                                                                            break # counter 4                                                                       
                                                                        time.sleep(scan_rate)                                                                 
                                                                    break # p search of first device to be done
                                                            break # counter 3
                                                        time.sleep(scan_rate)
                                                    break # k search of first device to be done
                                            break # counter 2
                                        time.sleep(scan_rate)
                                    break # j search of first device to be done
                            break # counter 1                      
                        time.sleep(scan_rate)      
                                
            elif len(args) == 18: # 6 syringes
                i1=args[0] 
                d1=args[1]
                v1=args[2]
                i2=args[3]
                d2=args[4]
                v2=args[5]
                i3=args[6]
                d3=args[7]
                v3=args[8]
                i4=args[9]
                d4=args[10]
                v4=args[11]
                i5=args[12]
                d5=args[13]
                v5=args[14]
                i6=args[15]
                d6=args[16]
                v6=args[17]
                i=[i1, i2, i3, i4, i5, i6]
                d=[d1, d2, d3, d4, d5, d6]
                v=[v1, v2, v3, v4, v5, v6]
                if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                    scan_rate=0.1 # //the scan rate of the counter
                    target=(48)*60*60 #/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1 in range(target): #this is a counter clock to check if the stop_status variable has changed
                        if self.Stop == True:
                            self.StopBoard()
                            break # counter 1                            
                        elif self.Pause == True:
                            self.PauseBoard()
                            for count_pause1 in range(target):
                                if self.Stop == True:
                                    break #count_pause1
                                elif self.Resume == True:
                                    self.ClockResume = datetime.now()
                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                    with open(output_txt_path(), "a") as OUTPUT:
                                        OUTPUT.write(comment + "\n")
                                    print(comment)
                                    self.SPS01[i1].UpdateStatus() #////////////////////////////
                                    self.SPS01[i2].UpdateStatus() #////////////////////////////
                                    self.SPS01[i3].UpdateStatus() #////////////////////////////
                                    self.SPS01[i4].UpdateStatus() #////////////////////////////
                                    self.SPS01[i5].UpdateStatus() #////////////////////////////                                    
                                    self.SPS01[i6].UpdateStatus() #////////////////////////////
                                    self.MulMove3(d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6)                                   
                                    self.flag_break_countpause = 1
                                    break #count_pause1
                                time.sleep(scan_rate)  
                        elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                            self.SPS01[i1].UpdateStatus()
                            self.SPS01[i2].UpdateStatus()
                            self.SPS01[i3].UpdateStatus()
                            self.SPS01[i4].UpdateStatus()
                            self.SPS01[i5].UpdateStatus()
                            self.SPS01[i6].UpdateStatus()                            
                        if self.flag_break_countpause == 1:
                            break #counter1  
                        elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True:
                            for j in range(len(i[0])):
                                if self.SPS01[i[j]].FlagIsDone == True:
                                    self.SPS01[i[j]].displaymovementstop()
                                    a=i
                                    a[j]=[]
                                    ad=d
                                    ad[j]=[]
                                    av=v
                                    av[j]=[]
                                    for count2 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                        if self.Stop == True:
                                            self.StopBoard()
                                            break # counter 2                                            
                                        elif self.Pause == True:
                                            self.PauseBoard()
                                            for count_pause1 in range(target):
                                                if self.Stop == True:
                                                    break #count_pause1
                                                elif self.Resume == True:
                                                    self.ClockResume = datetime.now()
                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                        OUTPUT.write(comment + "\n")
                                                    print(comment)
                                                    self.SPS01[a[0]].UpdateStatus() #////////////////////////////
                                                    self.SPS01[a[1]].UpdateStatus() #////////////////////////////                                                    
                                                    self.SPS01[a[2]].UpdateStatus() #////////////////////////////                                                   
                                                    self.SPS01[a[3]].UpdateStatus() #////////////////////////////                                                  
                                                    self.SPS01[a[4]].UpdateStatus() #////////////////////////////
                                                    self.MulMove3(ad[1],av[1],ad[2],av[2],ad[3],av[3],ad[4],av[4],ad[5],av[5])                                    
                                                    self.flag_break_countpause = 1
                                                    break #count_pause1
                                                time.sleep(scan_rate)  
                                        elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True:
                                            self.SPS01[a[0]].UpdateStatus()
                                            self.SPS01[a[1]].UpdateStatus()
                                            self.SPS01[a[2]].UpdateStatus()
                                            self.SPS01[a[3]].UpdateStatus()
                                            self.SPS01[a[4]].UpdateStatus()                                            
                                        if self.flag_break_countpause == 1:
                                            break #counter1  
                                        elif self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True:
                                            for k in range(len(a[0])): 
                                                if self.SPS01[a[k]].FlagIsDone == True:
                                                    self.SPS01[a[k]].displaymovementstop()
                                                    b=a
                                                    b[k]=[]
                                                    bd=ad
                                                    bd[k]=[]
                                                    bv=av
                                                    bv[k]=[]
                                                    for count3 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                        if self.Stop == True:
                                                            self.StopBoard()
                                                            break # counter 3                                                            
                                                        elif self.Pause == True:
                                                            self.PauseBoard()
                                                            for count_pause1 in range(target):
                                                                if self.Stop == True:
                                                                    break #count_pause1
                                                                elif self.Resume == True:
                                                                    self.ClockResume = datetime.now()
                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                        OUTPUT.write(comment + "\n")
                                                                    print(comment)
                                                                    self.SPS01[b[0]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[1]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[2]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[3]].UpdateStatus() #////////////////////////////
                                                                    self.MulMove3(bd[1],bv[1],bd[2],bv[2],bd[3],bv[3],bd[4],bv[4])  #CHECK THIS                                  
                                                                    self.flag_break_countpause = 1
                                                                    break #count_pause1
                                                                time.sleep(scan_rate) 
                                                        elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[3]].FlagIsMoving == True:
                                                            self.SPS01[b[0]].UpdateStatus()
                                                            self.SPS01[b[1]].UpdateStatus()
                                                            self.SPS01[b[2]].UpdateStatus()
                                                            self.SPS01[b[3]].UpdateStatus()                                                            
                                                        if self.flag_break_countpause == 1:
                                                            break #counter1  
                                                        elif self.SPS01[b[0]].FlagIsDone == True or self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True:
                                                            for p in range(len(b[0])):
                                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                                    self.SPS01[b[p]].displaymovementstop()
                                                                    c=b
                                                                    c[p]=[]
                                                                    cd=bd
                                                                    cd[p]=[]
                                                                    cv=bv
                                                                    cv[p]=[]
                                                                    for count4 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                        if self.Stop == True:
                                                                            self.StopBoard()
                                                                            break # counter 4                                                                            
                                                                        elif self.Pause == True:
                                                                            self.PauseBoard()
                                                                            for count_pause1 in range(target):
                                                                                if self.Stop == True:
                                                                                    break #count_pause1
                                                                                elif self.Resume == True:
                                                                                    self.ClockResume = datetime.now()
                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                        OUTPUT.write(comment + "\n")
                                                                                    print(comment)
                                                                                    self.SPS01[c[0]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[1]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[2]].UpdateStatus() #////////////////////////////
                                                                                    self.MulMove3(cd[1],cv[1],cd[2],cv[2],cd[3],cv[3])                                 
                                                                                    self.flag_break_countpause = 1
                                                                                    break #count_pause1
                                                                                time.sleep(scan_rate)  
                                                                        elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving:
                                                                            self.SPS01[c[0]].UpdateStatus()
                                                                            self.SPS01[c[1]].UpdateStatus()
                                                                            self.SPS01[c[2]].UpdateStatus()                                                                            
                                                                        if self.flag_break_countpause == 1:
                                                                            break #counter1
                                                                        elif self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True:
                                                                            for q in range(len(c[0])):
                                                                                if self.SPS01[c[q]].FlagIsDone == True:
                                                                                    self.SPS01[c[q]].displaymovementstop()
                                                                                    d=c
                                                                                    d[q]=[]
                                                                                    dd=cd
                                                                                    dd[q]=[]
                                                                                    dv=cv
                                                                                    dv[q]=[]
                                                                                    for count5 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                                        if self.Stop == True:
                                                                                            self.StopBoard()
                                                                                            break # counter 5                                                                                            
                                                                                        elif self.Pause == True:
                                                                                            self.PauseBoard()
                                                                                            for count_pause1 in range(target):
                                                                                                if self.Stop == True:
                                                                                                    break #count_pause1
                                                                                                elif self.Resume == True:
                                                                                                    self.ClockResume = datetime.now()
                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                    print(comment)
                                                                                                    self.SPS01[d[0]].UpdateStatus() #////////////////////////////
                                                                                                    self.SPS01[d[1]].UpdateStatus() #////////////////////////////
                                                                                                    self.MulMove3(dd[1],dv[1],dd[2],dv[2])                                    
                                                                                                    self.flag_break_countpause = 1
                                                                                                    break #count_pause1
                                                                                                time.sleep(scan_rate)   
                                                                                        elif self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving:
                                                                                            self.SPS01[d[0]].UpdateStatus()
                                                                                            self.SPS01[d[1]].UpdateStatus()                                                                                            
                                                                                        if self.flag_break_countpause == 1:
                                                                                            break #counter1
                                                                                        elif self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone:
                                                                                            for r in range(len(d[0])):
                                                                                                if self.SPS01[d[r]].FlagIsDone == True:
                                                                                                    self.SPS01[d[r]].displaymovementstop()
                                                                                                    e=d
                                                                                                    e[r]=[]
                                                                                                    ed=dd
                                                                                                    ed[r]=[]
                                                                                                    ev=dv
                                                                                                    ev[r]=[]
                                                                                                    for count6 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                                                        if self.Stop == True:
                                                                                                            self.StopBoard()
                                                                                                            break # counter 6                                                                                                            
                                                                                                        elif self.Pause == True:
                                                                                                            self.PauseBoard()
                                                                                                            for count_pause1 in range(target):
                                                                                                                if self.Stop == True:
                                                                                                                    break #count_pause1
                                                                                                                elif self.Resume == True:
                                                                                                                    self.ClockResume = datetime.now()
                                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                                    print(comment)
                                                                                                                    self.SPS01[e[0]].UpdateStatus() #////////////////////////////
                                                                                                                    self.MulMove3(ed[1],ev[1])                                   
                                                                                                                    self.flag_break_countpause = 1
                                                                                                                    break #count_pause1
                                                                                                                time.sleep(scan_rate)  
                                                                                                        elif self.SPS01[e[0]].FlagIsMoving:
                                                                                                            self.SPS01[e[0]].UpdateStatus()
                                                                                                        if self.flag_break_countpause == 1:
                                                                                                            break #counter1
                                                                                                        elif self.SPS01[e[0]].FlagIsDone:
                                                                                                            self.SPS01[e[0]].displaymovementstop()
                                                                                                            break # counter 6                                                                                                       
                                                                                                        time.sleep(scan_rate)                                                                                                   
                                                                                                    break # r search of first device to be done
                                                                                            break # counter 5
                                                                                        time.sleep(scan_rate)
                                                                                    break # q search of first device to be done
                                                                            break #counter 4                                                                       
                                                                        time.sleep(scan_rate)
                                                                    break # p search of first device to be done
                                                            break # Counter 3                                                        
                                                        time.sleep(scan_rate)                                                   
                                                    break # k search of first device to be done
                                            break # counter 2                                       
                                        time.sleep(scan_rate)
                                    break # j search of first device to be done
                            break # counter 1
                        time.sleep(scan_rate)  

            elif len(args) == 21: #7 syringes
                i1=args[0]
                d1=args[1]
                v1=args[2]
                i2=args[3]
                d2=args[4]
                v2=args[5]
                i3=args[6]
                d3=args[7]
                v3=args[8]
                i4=args[9]
                d4=args[10]
                v4=args[11]
                i5=args[12]
                d5=args[13]
                v5=args[14]
                i6=args[15]
                d6=args[16]
                v6=args[17]
                i7=args[18]
                d7=args[19]
                v7=args[20]
                i=[i1, i2, i3, i4, i5, i6, i7]
                d=[d1, d2, d3, d4, d5, d6, d7]
                v=[v1, v2, v3, v4, v5, v6, v7]
                if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                    scan_rate=0.1 #the scan rate of the counter
                    target=(48)*60*60 #/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1 in range(target): #this is a counter clock to check if the stop_status variable has changed
                        if self.Stop == True:
                            self.StopBoard()
                            break # counter 1                            
                        elif self.Pause == True:
                            self.PauseBoard()
                            for count_pause1 in range(target):
                                if self.Stop == True:
                                    break #count_pause1
                                elif self.Resume == True:
                                    self.ClockResume = datetime.now()
                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                    with open(output_txt_path(), "a") as OUTPUT:
                                        OUTPUT.write(comment + "\n")
                                    print(comment)
                                    self.SPS01[i1].UpdateStatus() #////////////////////////////
                                    self.SPS01[i2].UpdateStatus() #////////////////////////////
                                    self.SPS01[i3].UpdateStatus() #////////////////////////////
                                    self.SPS01[i4].UpdateStatus() #////////////////////////////
                                    self.SPS01[i5].UpdateStatus() #////////////////////////////                                    
                                    self.SPS01[i6].UpdateStatus() #////////////////////////////                                  
                                    self.SPS01[i7].UpdateStatus() #////////////////////////////
                                    self.MulMove3(d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7)                                   
                                    self.flag_break_countpause = 1
                                    break #count_pause1
                                time.sleep(scan_rate)   
                        elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                            self.SPS01[i1].UpdateStatus()
                            self.SPS01[i2].UpdateStatus()
                            self.SPS01[i3].UpdateStatus()
                            self.SPS01[i4].UpdateStatus()
                            self.SPS01[i5].UpdateStatus()
                            self.SPS01[i6].UpdateStatus()
                            self.SPS01[i7].UpdateStatus()
                        if self.flag_break_countpause == 1:
                            break #counter1  
                        elif self.SPS01[i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True or self.SPS01[i3].FlagIsDone == True or self.SPS01[i4].FlagIsDone == True or self.SPS01[i5].FlagIsDone == True or self.SPS01[i6].FlagIsDone == True or self.SPS01[i7].FlagIsDone == True:
                            for j in range(len(i[0])):
                                if self.SPS01[i[j]].FlagIsDone == True:
                                    self.SPS01[i[j]].displaymovementstop()
                                    a=i
                                    a[j]=[]
                                    ad=d
                                    ad[j]=[]
                                    av=v
                                    av[j]=[]
                                    for count2 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                        if self.Stop == True:
                                            self.StopBoard()
                                            break # counter 2                                            
                                        elif self.Pause == True:
                                            self.PauseBoard()
                                            for count_pause1 in range(target):
                                                if self.Stop == True:
                                                    break #count_pause1
                                                elif self.Resume == True:
                                                    self.ClockResume = datetime.now()
                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                        OUTPUT.write(comment + "\n")
                                                    print(comment)
                                                    self.SPS01[a[0]].UpdateStatus() #////////////////////////////
                                                    self.SPS01[a[1]].UpdateStatus() #////////////////////////////                                                    
                                                    self.SPS01[a[2]].UpdateStatus() #////////////////////////////                                                   
                                                    self.SPS01[a[3]].UpdateStatus() #////////////////////////////                                                  
                                                    self.SPS01[a[4]].UpdateStatus() #////////////////////////////                                                 
                                                    self.SPS01[a[5]].UpdateStatus() #////////////////////////////
                                                    self.MulMove3(ad[1],av[1],ad[2],av[2],ad[3],av[3],ad[4],av[4],ad[5],av[5],ad[6],av[6])                                    
                                                    self.flag_break_countpause = 1
                                                    break #count_pause1
                                                time.sleep(scan_rate)
                                        elif self.SPS01[a[0]].FlagIsMoving == True and self.SPS01[a[1]].FlagIsMoving == True and self.SPS01[a[2]].FlagIsMoving == True and self.SPS01[a[3]].FlagIsMoving == True and self.SPS01[a[4]].FlagIsMoving == True and self.SPS01[a[5]].FlagIsMoving == True:
                                            self.SPS01[a[0]].UpdateStatus()
                                            self.SPS01[a[1]].UpdateStatus()
                                            self.SPS01[a[2]].UpdateStatus()
                                            self.SPS01[a[3]].UpdateStatus()
                                            self.SPS01[a[4]].UpdateStatus()
                                            self.SPS01[a[5]].UpdateStatus()
                                        if self.flag_break_countpause == 1:
                                            break #counter1  
                                        elif self.SPS01[a[0]].FlagIsDone == True or self.SPS01[a[1]].FlagIsDone == True or self.SPS01[a[2]].FlagIsDone == True or self.SPS01[a[3]].FlagIsDone == True or self.SPS01[a[4]].FlagIsDone == True or self.SPS01[a[5]].FlagIsDone == True:
                                            for k in range(len(a[0])):
                                                if self.SPS01[a[k]].FlagIsDone == True:
                                                    self.SPS01[a[0]].displaymovementstop()
                                                    b=a
                                                    b[k]=[]
                                                    bd=ad
                                                    bd[k]=[]
                                                    bv=av
                                                    bv[k]=[]
                                                    for count3 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                        if self.Stop == True:
                                                            self.StopBoard()
                                                            break # counter 3                                                            
                                                        elif self.Pause == True:
                                                            self.PauseBoard()
                                                            for count_pause1 in range(target):
                                                                if self.Stop == True:
                                                                    break #count_pause1
                                                                elif self.Resume == True:
                                                                    self.ClockResume = datetime.now()
                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                        comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                        OUTPUT.write(comment + "\n")
                                                                        print(comment)
                                                                    self.SPS01[b[0]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[1]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[2]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[3]].UpdateStatus() #////////////////////////////
                                                                    self.SPS01[b[4]].UpdateStatus() #////////////////////////////
                                                                    self.MulMove3(bd[1],bv[1],bd[2],bv[2],bd[3],bv[3],bd[4],bv[4],bd[5],bv[5])                                    
                                                                    self.flag_break_countpause = 1
                                                                    break #count_pause1
                                                                time.sleep(scan_rate)    
                                                        elif self.SPS01[b[0]].FlagIsMoving == True and self.SPS01[b[1]].FlagIsMoving == True and self.SPS01[b[2]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True and self.SPS01[b[4]].FlagIsMoving == True:
                                                            self.SPS01[b[0]].UpdateStatus()
                                                            self.SPS01[b[1]].UpdateStatus()
                                                            self.SPS01[b[2]].UpdateStatus()
                                                            self.SPS01[b[3]].UpdateStatus()
                                                            self.SPS01[b[4]].UpdateStatus()
                                                        if self.flag_break_countpause == 1:
                                                            break #counter1  
                                                        elif self.SPS01[b[1]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[2]].FlagIsDone == True or self.SPS01[b[3]].FlagIsDone == True or self.SPS01[b[4]].FlagIsDone == True:
                                                            for p in range(len(b[0])):
                                                                if self.SPS01[b[p]].FlagIsDone == True:
                                                                    self.SPS01[b[p]].displaymovementstop()
                                                                    c=b
                                                                    c[p]=[]
                                                                    cd=bd
                                                                    cd[p]=[]
                                                                    cv=bv
                                                                    cv[p]=[]
                                                                    for count4 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                        if self.Stop == True:
                                                                            self.StopBoard()
                                                                            break # counter 4                                                                            
                                                                        elif self.Pause == True:
                                                                            self.PauseBoard()
                                                                            for count_pause1 in range(target):
                                                                                if self.Stop == True:
                                                                                    break #count_pause1
                                                                                elif self.Resume == True:
                                                                                    self.ClockResume = datetime.now()
                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                        OUTPUT.write(comment + "\n")
                                                                                    print(comment)
                                                                                    self.SPS01[c[0]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[1]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[2]].UpdateStatus() #////////////////////////////
                                                                                    self.SPS01[c[3]].UpdateStatus() #////////////////////////////
                                                                                    self.MulMove3(cd[1],cv[1],cd[2],cv[2],cd[3],cv[3],cd[4],cv[4])                                    
                                                                                    self.flag_break_countpause = 1
                                                                                    break #count_pause1
                                                                                time.sleep(scan_rate)   
                                                                        elif self.SPS01[c[0]].FlagIsMoving == True and self.SPS01[c[1]].FlagIsMoving and self.SPS01[c[2]].FlagIsMoving and self.SPS01[c[3]].FlagIsMoving:
                                                                            self.SPS01[c[0]].UpdateStatus()
                                                                            self.SPS01[c[1]].UpdateStatus()
                                                                            self.SPS01[c[2]].UpdateStatus()
                                                                            self.SPS01[c[3]].UpdateStatus()
                                                                        if self.flag_break_countpause == 1:
                                                                            break #counter1
                                                                        elif self.SPS01[c[0]].FlagIsDone == True or self.SPS01[c[1]].FlagIsDone == True or self.SPS01[c[2]].FlagIsDone == True or self.SPS01[c[3]].FlagIsDone == True:
                                                                            for q in range(len(c[0])):
                                                                                if self.SPS01[c[q]].FlagIsDone == True:
                                                                                    self.SPS01[c[q]].displaymovementstop()
                                                                                    d=c
                                                                                    d[q]=[]
                                                                                    dd=cd
                                                                                    dd[q]=[]
                                                                                    dv=cv
                                                                                    dv[q]=[]
                                                                                    for count5 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                                        if self.Stop == True:
                                                                                            self.StopBoard()
                                                                                            break # counter 5                                                                                            
                                                                                        elif self.Pause == True:
                                                                                            self.PauseBoard()
                                                                                            for count_pause1 in range(target):
                                                                                                if self.Stop == True:
                                                                                                    break #count_pause1
                                                                                                elif self.Resume == True:
                                                                                                    self.ClockResume = datetime.now()
                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                    print(comment)
                                                                                                    self.SPS01[d[0]].UpdateStatus() #////////////////////////////
                                                                                                    self.SPS01[d[1]].UpdateStatus() #////////////////////////////
                                                                                                    self.SPS01[d[2]].UpdateStatus() #////////////////////////////
                                                                                                    self.MulMove3(dd[1],dv[1],dd[2],dv[2],dd[3],dv[3])                                   
                                                                                                    self.flag_break_countpause = 1
                                                                                                    break #count_pause1
                                                                                                time.sleep(scan_rate)   
                                                                                        elif self.SPS01[d[0]].FlagIsMoving and self.SPS01[d[1]].FlagIsMoving and self.SPS01[d[2]].FlagIsMoving:
                                                                                            self.SPS01[d[0]].UpdateStatus()
                                                                                            self.SPS01[d[1]].UpdateStatus()
                                                                                            self.SPS01[d[2]].UpdateStatus()
                                                                                        if self.flag_break_countpause == 1:
                                                                                            break #counter1
                                                                                        elif self.SPS01[d[0]].FlagIsDone or self.SPS01[d[1]].FlagIsDone or self.SPS01[d[2]].FlagIsDone:
                                                                                            for r in range(len(d[0])):
                                                                                                if self.SPS01[d[r]].FlagIsDone == True:
                                                                                                    self.SPS01[d[r]].displaymovementstop()
                                                                                                    e=d
                                                                                                    e[r]=[]
                                                                                                    ed=dd
                                                                                                    ed[r]=[]
                                                                                                    ev=dv
                                                                                                    ev[r]=[]
                                                                                                    for count6 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                                                        if self.Stop == True:
                                                                                                            self.StopBoard()
                                                                                                            break # counter 6                                                                                                            
                                                                                                        elif self.Pause == True:
                                                                                                            self.PauseBoard()
                                                                                                            for count_pause1 in range(target):
                                                                                                                if self.Stop == True:
                                                                                                                    break #count_pause1
                                                                                                                elif self.Resume == True:
                                                                                                                    self.ClockResume = datetime.now()
                                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                                    print(comment)
                                                                                                                    self.SPS01[e[0]].UpdateStatus() #////////////////////////////                                                                                                                    
                                                                                                                    self.SPS01[e[1]].UpdateStatus() #////////////////////////////
                                                                                                                    self.MulMove3(ed[1],ev(1),ed[2],ev[2])                                    
                                                                                                                    self.flag_break_countpause = 1
                                                                                                                    break #count_pause1
                                                                                                                time.sleep(scan_rate)   
                                                                                                                    
                                                                                                        elif self.SPS01[e[0]].FlagIsMoving and self.SPS01[e[1]].FlagIsMoving: 
                                                                                                            self.SPS01[e[0]].UpdateStatus()
                                                                                                            self.SPS01[e[1]].UpdateStatus()
                                                                                                        if self.flag_break_countpause == 1:
                                                                                                            break #counter1
                                                                                                        elif self.SPS01[e[0]].FlagIsDone or self.SPS01[e[1]].FlagIsDone:
                                                                                                            for s in range(len(e[0])):
                                                                                                                if self.SPS01[e[s]].FlagIsDone == True:
                                                                                                                    self.SPS01[e[s]].displaymovementstop()
                                                                                                                    f=e
                                                                                                                    f[s]=[]
                                                                                                                    fd=ed
                                                                                                                    fd[s]=[]
                                                                                                                    fv=ev
                                                                                                                    fv[s]=[]
                                                                                                                    for count7 in range(target): #this is a counter clock to check if the stop_status variable has changed
                                                                                                                        if self.Stop == True:
                                                                                                                            self.StopBoard()
                                                                                                                            break # counter 7                                                                                                                            
                                                                                                                        elif self.Pause == True:
                                                                                                                            self.PauseBoard()
                                                                                                                            for count_pause1 in range(target):
                                                                                                                                if self.Stop == True:
                                                                                                                                    break #count_pause1
                                                                                                                                elif self.Resume == True:
                                                                                                                                    self.ClockResume = datetime.now()
                                                                                                                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                                                                                                                    with open(output_txt_path(), "a") as OUTPUT:
                                                                                                                                        OUTPUT.write(comment + "\n")
                                                                                                                                    print(comment)
                                                                                                                                    self.SPS01[f[0]].UpdateStatus() #////////////////////////////
                                                                                                                                    self.MulMove3(fd[1],fv[1]);                                    
                                                                                                                                    self.flag_break_countpause = 1
                                                                                                                                    break #count_pause1
                                                                                                                                time.sleep(scan_rate)
                                                                                                                        elif self.SPS01[f[0]].FlagIsMoving:
                                                                                                                            self.SPS01[f[0]].UpdateStatus()
                                                                                                                        if self.flag_break_countpause == 1:
                                                                                                                            break #counter1
                                                                                                                        elif self.SPS01[f[0]].FlagIsDone: 
                                                                                                                            self.SPS01[f[0]].displaymovementstop()
                                                                                                                            break # counter 7
                                                                                                                        time.sleep(scan_rate)
                                                                                                                    break # s search of first device to be done
                                                                                                            break # counter 6
                                                                                                        time.sleep(scan_rate)  
                                                                                                    break # r search of first device to be done9999999999sa
                                                                                            break # counter 5
                                                                                        time.sleep(scan_rate)
                                                                                    break # q search of first device to be done
                                                                            break # counter 4
                                                                        time.sleep(scan_rate) 
                                                                    break # p search of first device to be done
                                                            break # counter 3                                                 
                                                        time.sleep(scan_rate)
                                                    break # k search of first device to be done
                                            break # counter 2                                   
                                        time.sleep(scan_rate)
                                    break # j search of first device to be done
                            break # counter 1                   
                        time.sleep(scan_rate)
            pass
        ## TODO ##

    ## Multiple Movement with stop (at the same time. It allows the stop and pause)
    def MulMove3(self, d1 = None, v1 = None, d2 = None, v2 = None, d3 = None, v3 = None, d4 = None, v4 = None, d5 = None, v5 = None, d6 = None, v6 = None, d7 = None, v7 = None, d8 = None, v8 = None):
        self.flag_break_countpause = 0
        if self.Stop == False:
            if [d1, v1, d2, v2, d3, v3, d4, v4, d5, v5, d6, v6, d7, v7, d8, v8].count(None)%2 !=0:
                comment='Error, missing input. Number of inputs has to be even (name of syringes and corresponding flow rates).'
                with open(output_txt_path(), "a") as OUTPUT:
                    OUTPUT.write(comment + "\n")
                    print(comment)
            else:
                if v1 != None and d2 == None: ## 1 syringe as input
                    i1=self.FindIndexS(d1)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1]) ##it listens for the syringe FlagIsMoving == True, so it updtades continuously the state to determine the end of the command. It results in FlagReady = True again.
                    if len(self.SPS01) == 1:
                        if self.SPS01[i1].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1) 
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            if self.SPS01[i1].FlagIsMoving == True:
                                self.notify('FirstDoneStopPause')
                elif v2 != None and d3 == None: ## 2 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2) 
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 2:
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1)
                            self.SPS01[i2].device.CmdMoveToVolume(v2)
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i2].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            self.SPS01[i2].displaymovement()  
                            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                                self.notify('FirstDoneStopPause')                                              
                elif v3 != None and d4 == None: ## 3 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2,i3,d3,v3]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 3:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)
                        self.SPS01[i2].device.CmdMoveToVolume(v2)
                        self.SPS01[i3].device.CmdMoveToVolume(v3)
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement() 
                        self.SPS01[i3].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                            self.notify('FirstDoneStopPause')
                elif v4 != None and d5 == None: ## 4 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 4:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)
                        self.SPS01[i2].device.CmdMoveToVolume(v2)
                        self.SPS01[i3].device.CmdMoveToVolume(v3)
                        self.SPS01[i4].device.CmdMoveToVolume(v4)
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement() 
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                            self.notify('FirstDoneStopPause')
                elif v5 != None and d6 == None: ## 5 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 5:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)
                        self.SPS01[i2].device.CmdMoveToVolume(v2)
                        self.SPS01[i3].device.CmdMoveToVolume(v3)
                        self.SPS01[i4].device.CmdMoveToVolume(v4)
                        self.SPS01[i5].device.CmdMoveToVolume(v5)
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement() 
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True:
                            self.notify('FirstDoneStopPause')
                elif v6 != None and d7 == None: ## 6 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    i6=self.FindIndexS(d6)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5,i6,d6,v6]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 6:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)
                        self.SPS01[i2].device.CmdMoveToVolume(v2)
                        self.SPS01[i3].device.CmdMoveToVolume(v3)
                        self.SPS01[i4].device.CmdMoveToVolume(v4)
                        self.SPS01[i5].device.CmdMoveToVolume(v5)
                        self.SPS01[i6].device.CmdMoveToVolume(v6)
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i6].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement() 
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].displaymovement()
                        self.SPS01[i6].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True:
                            self.notify('FirstDoneStopPause')
                elif v7 != None and d8 == None: ## 7 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    i5=self.FindIndexS(d5)
                    i6=self.FindIndexS(d6)
                    i7=self.FindIndexS(d7)
                    self.addlistener('FirstDoneStopPause', "listener_firstdonepause", self.CheckFirstDoneStopPause, [i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5,i6,d6,v6,i7,d7,v7]) ##it listens for the syringes FlagIsMoving == True, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = True again.
                    if len(self.SPS01) == 7:
                        self.SPS01[i1].device.CmdMoveToVolume(v1)
                        self.SPS01[i2].device.CmdMoveToVolume(v2)
                        self.SPS01[i3].device.CmdMoveToVolume(v3)
                        self.SPS01[i4].device.CmdMoveToVolume(v4)
                        self.SPS01[i5].device.CmdMoveToVolume(v5)
                        self.SPS01[i6].device.CmdMoveToVolume(v6)
                        self.SPS01[i7].device.CmdMoveToVolume(v7)
                        self.SPS01[i1].FlagReady = False
                        self.SPS01[i2].FlagReady = False
                        self.SPS01[i3].FlagReady = False
                        self.SPS01[i4].FlagReady = False
                        self.SPS01[i5].FlagReady = False
                        self.SPS01[i6].FlagReady = False
                        self.SPS01[i7].FlagReady = False
                        self.SPS01[i1].displaymovement()
                        self.SPS01[i2].displaymovement() 
                        self.SPS01[i3].displaymovement()
                        self.SPS01[i4].displaymovement()
                        self.SPS01[i5].displaymovement()
                        self.SPS01[i6].displaymovement()
                        self.SPS01[i7].displaymovement()
                        if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True and self.SPS01[i5].FlagIsMoving == True and self.SPS01[i6].FlagIsMoving == True and self.SPS01[i7].FlagIsMoving == True:
                            self.notify('FirstDoneStopPause')

    ## Display movement stopwait
    def displaymovementstopwait(self,t):
        self.ClockStop = datetime.now()
        with open(output_txt_path(), "a") as OUTPUT:
            comment = f"{self.ClockStop.strftime('%X')} Step done after waiting for {t} seconds."
            OUTPUT.write(comment + "\n")
            print(comment)

    ## WaitStopBoard
    def WaitStopBoard(self):
        for i in range(len(self.SPS01)):
            self.SPS01[i].device.CmdStop()
            self.SPS01[i].FlagReady = True           
        for i in range(len(self.C4VM)):
            self.C4VM[i].device.CmdStop()
            self.C4VM[i].UpdateStatus()
        for i in range(len(self.C4AM)):
            self.C4AM[i].Stop()
        for i in range(len(self.C4PM)):
            self.C4PM[i].Stop()
        for i in range(len(self.CEP01)):
            self.CEP01[i].Stop()

    ## Update
    def UpdateBoard(self):
        for i in range(len(self.SPS01)):
            self.SPS01[i].FlagReady = True
            self.SPS01[i].UpdateStatus()
        for i in range(len(self.C4VM)):
            self.C4VM[i].UpdateStatus()
        for i in range(len(self.C4AM)):
            self.C4AM[i].UpdateStatus()
        for i in range(len(self.C4PM)):
            self.C4PM[i].UpdateStatus()
        for i in range(len(self.CEP01)):
            self.CEP01[i].UpdateStatus()

    ## Wait Movement
    def MoveWait(self,time,d1 = None, v1 = None, d2 = None, v2 = None, d3 = None, v3 = None, d4 = None, v4 = None, d5 = None, v5 = None, d6 = None, v6 = None, d7 = None, v7 = None, d8 = None, v8 = None):
        t_s=datetime.now()
        self.flag_break_countpause = 0
        self.flag_break_stop = 0
        if self.Stop == False:
            if [d1, v1, d2, v2, d3, v3, d4, v4, d5, v5, d6, v6, d7, v7, d8, v8].count(None)%2 != 0:
                comment="Error, missing input. Number of inputs has to be even (time, name of syringes and corresponding flow rates)."
                with open(output_txt_path(),"a") as OUTPUT:
                    OUTPUT.write(comment +"\n")
                    print(comment) 
            else:
                if v1 != None and d2 == None: ## 1 syringe as input
                    i1=self.FindIndexS(d1)
                    self.addlistener('FirstDoneStopPauseWait', "listener_firstdonepausewait", self.CheckFirstDoneStopPauseWait, [time, i1,d1,v1,t_s]) ##it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                    if len(self.SPS01) == 1:
                        if self.SPS01[i1].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1) 
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i1].displaymovement()                              
                            if self.SPS01[i1].FlagIsMoving == True:
                                self.notify('FirstDoneStopPauseWait')
                elif v2 != None and d3 == None: ## 2 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    self.addlistener('FirstDoneStopPauseWait', "listener_firstdonepausewait", self.CheckFirstDoneStopPauseWait, [time,i1,d1,v1,i2,d2,v2,t_s]) ##it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                    if len(self.SPS01) == 2:
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1)
                            self.SPS01[i2].device.CmdMoveToVolume(v2)
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i2].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            self.SPS01[i2].displaymovement()  
                            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True:
                                self.notify('FirstDoneStopPauseWait')
                elif v3 != None and d4 == None: ## 3 syringes as input
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    self.addlistener('FirstDoneStopPauseWait', "listener_firstdonepausewait", self.CheckFirstDoneStopPauseWait, [time,i1,d1,v1,i2,d2,v2,d3,v3,t_s]) ##it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                    if len(self.SPS01) == 3:
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1)
                            self.SPS01[i2].device.CmdMoveToVolume(v2)
                            self.SPS01[i3].device.CmdMoveToVolume(v3)
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i2].FlagReady = False
                            self.SPS01[i3].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            self.SPS01[i2].displaymovement()
                            self.SPS01[i3].displaymovement()
                            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True:
                                self.notify('FirstDoneStopPauseWait')
        elif v4 != None and d5 == None: ## 4 syringes as input:
                    i1=self.FindIndexS(d1)
                    i2=self.FindIndexS(d2)
                    i3=self.FindIndexS(d3)
                    i4=self.FindIndexS(d4)
                    self.addlistener('FirstDoneStopPauseWait', "listener_firstdonepausewait", self.CheckFirstDoneStopPauseWait, [time,i1,d1,v1,i2,d2,v2,d3,v3,d4,v4,t_s]) ##it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                    if len(self.SPS01) == 4:
                        if self.SPS01[i1].FlagIsDone == True and self.SPS01[i2].FlagIsDone == True and self.SPS01[i3].FlagIsDone == True and self.SPS01[i4].FlagIsDone == True:
                            self.SPS01[i1].device.CmdMoveToVolume(v1)
                            self.SPS01[i2].device.CmdMoveToVolume(v2)
                            self.SPS01[i3].device.CmdMoveToVolume(v3)
                            self.SPS01[i4].device.CmdMoveToVolume(v4)
                            self.SPS01[i1].FlagReady = False
                            self.SPS01[i2].FlagReady = False
                            self.SPS01[i3].FlagReady = False
                            self.SPS01[i4].FlagReady = False
                            self.SPS01[i1].displaymovement()
                            self.SPS01[i2].displaymovement()
                            self.SPS01[i3].displaymovement()                                
                            self.SPS01[i4].displaymovement()
                            if self.SPS01[i1].FlagIsMoving == True and self.SPS01[i2].FlagIsMoving == True and self.SPS01[i3].FlagIsMoving == True and self.SPS01[i4].FlagIsMoving == True:
                                self.notify('FirstDoneStopPauseWait')

    ## Listener Function : Display the first device to be done and Stop and Pause and chech the WAIT (called in MoveWait)
    def CheckFirstDoneStopPauseWait(self,*args):
        if len(args) == 5:
            t=args[0]
            i1=args[1]
            d1=args[2]
            v1=args[3]
            ts=args[4]
            var_not_disp=0
            if self.SPS01[i1].FlagIsMoving == True:
                scan_rate=0.1
                target=(48)*60*60#scan_rate
                for count1 in range(t):
                    if self.Stop == True:
                        self.StopBoard()
                        self.flag_break_stop = 1
                        break
                    elif self.Pause == True:
                        self.PauseBoard()
                        te = datetime.now()
                        te = te - ts
                        difftime = t - te
                        for count_pause1 in range(target):
                            if self.Stop == True:
                                break
                            elif self.Resume == True:
                                self.ClockResume = datetime.now()
                                with open(output_txt_path(), "a") as OUTPUT:
                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                    OUTPUT.write(comment + "\n")
                                    print(comment)
                                self.SPS01[i1].UpdateStatus()
                                self.flag_a +=1
                                self.MoveWait(diff_time, d1, v1)
                                self.flag_break_countpause = 1
                                self.flag_b +=1
                                break
                            time.sleep(scan_rate)
                    elif self.SPS01[i1].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break
                    elif self.SPS01[i1].FlagIsDone == True:
                        self.SPS01[i1].displaymovementstop()
                        var_not_disp = 1
                        break
                    time.sleep(0)
                if self.flag_break_stop == 0 and var_not_disp == 0:
                    self.WaitStopBoard
                    self.UpdateBoard
                    if self.flag_b == self.flag_a:
                        self.displaymovementstopwait(t)
                        self.flag_a = 0
                        self.flag_b = 0

        elif len(args) == 8:
            t=args[0]
            i1=args[1]
            d1=args[2]
            v1=args[3]
            i2=args[4]
            d2=args[5]
            v2=args[6]
            i=[i1, i2]
            d=[d1, d2]
            v=[v1, v2]
            ts=args[7]
            var_not_disp = 0
            if self.SPS01[ i1].FlagIsMoving == True and self.SPS01[ i2].FlagIsMoving == True:
                scan_rate=0.1
                target=(48)*60*60#scan_rate
                for count1 in range(t):
                    if self.Stop == True:
                        self.StopBoard
                        self.flag_break_stop = 1
                        break
                    elif self.Pause == True:
                        self.PauseBoard
                        te = datetime.now()
                        te=te - ts
                        diff_time=t-te
                        for count_pause1 in range(target):
                            if self.Stop == True:
                                break
                            elif self.Resume == True:
                                self.ClockResume = datetime.now()
                                with open(output_txt_path(), "a") as OUTPUT:
                                    comment = f"{self.ClockResume.strftime('%X')} Interface resumed by the user."
                                    OUTPUT.write(comment + "\n")
                                    print(comment)
                                self.SPS01[i1].UpdateStatus()
                                self.SPS01[i2].UpdateStatus()
                                self.flag_a +=1 
                                self.MoveWait(diff_time, d1, v1, d2, v2)
                                self.flag_break_countpause = 1
                                self.flag_b += 1
                                break
                            time.sleep(scan_rate)
                    elif self.SPS01[i1].FlagIsMoving == True and self.SPS01[ i2].FlagIsMoving == True:
                        self.SPS01[i1].UpdateStatus()
                        self.SPS01[i2].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break
                    elif self.SPS01[ i1].FlagIsDone == True or self.SPS01[i2].FlagIsDone == True:
                        for j in len(i):
                            if self.SPS01[i[j]].FlagIsDone == True:
                                self.SPS01[i[j]].displaymovementstop()
                                te = datetime.now()
                                te = te - ts
                                t1=(t-te)
                                ts=datetime.now()
                                a=i
                                a[j]=[]
                                ad=d
                                ad[j]=[]
                                av=v
                                av[j]=[]
                                for count2 in range(t1):
                                    if self.Stop == True:
                                        self.StopBoard
                                        self.flag_break_stop = 1
                                        break
                                    elif self.Pause == True:
                                        self.PauseBoard
                                        te = datetime.now()
                                        te = te - ts
                                        diff_time=t-te
                                        for count_pause1 in range(target):
                                            if self.Stop == True:
                                                break
                                            elif self.Resume == True:
                                                self.ClockResume = datetime.now()
                                            
    ## Set Valves2 It allows the pause too
    def SetValves2(self, d1 = None,v11 = None,v12 = None,v13 = None, v14 = None, d2 = None, v21 = None, v22 = None, v23 = None, v24 = None):
        self.flag_break_countpause = 0
        if self.Stop == False:
            if v14 != None and d2 == None:## 1 manifold as input
                i1=self.FindIndexM(d1)
                self.addlistener('FirstDoneStopPauseM', "listener_firstdoneM", self.CheckFirstDoneStopPauseM, [i1,d1,v11,v12,v13,v14]) ##it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                if len(self.C4VM) == 1:
                    if self.C4VM[i1].FlagIsDone == True:
                        self.C4VM[i1].device.CmdSetValves(np.int8(v11),np.int8(v12),np.int8(v13),np.int8(v14))                              
                        self.C4VM[i1].displayswitch(v11,v12,v13,v14)
                        if self.C4VM[i1].FlagIsDone == False:
                            self.notify('FirstDoneStopPauseM')
            if v24 != None:## 2 manifold as input
                i1=self.FindIndexM(d1)
                i2 = self.FindIndexM(d2)
                self.addlistener('FirstDoneStopPauseM', "listener_firstdoneM", self.CheckFirstDoneStopPauseM, [i1,d1,v11,v12,v13,v14]) ##it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                if len(self.C4VM) == 2:
                    if self.C4VM[i1].FlagIsDone == True:
                        self.C4VM[i1].device.CmdSetValves(np.int8(v11),np.int8(v12),np.int8(v13),np.int8(v14))                              
                        self.C4VM[i1].displayswitch(v11,v12,v13,v14)
                        if self.C4VM[i1].FlagIsDone == False:
                            self.notify('FirstDoneStopPauseM')
                    if self.C4VM[i2].FlagIsDone == True:
                        self.C4VM[i2].device.CmdSetValves(np.int8(v21),np.int8(v22),np.int8(v23),np.int8(v24))                              
                        self.C4VM[i2].displayswitch(v21,v22,v23,v24)
                        if self.C4VM[i2].FlagIsDone == False:
                            self.notify('FirstDoneStopPauseM')

    ## Check First Done Stop Pause M
    def CheckFirstDoneStopPauseM(self, *args):
        if len(args) == 6: ## only one manifold in motion (=numb input + self + 2more input (source and event))  
            i1=args[0] ##vararging doesn't include the self, so its size is nargin-1. The index is the third.
            d1=args[1]
            v11=args[2]
            v12=args[3]
            v13=args[4]
            v14=args[5]
            if self.C4VM[i1].FlagIsDone == False:
                scan_rate=0.1 ##the scan rate of the counter
                target=(48)*60*60#scan_rate ##this is the final time of the counter. It is equal to max 48 hours                   
                for count1 in range(target): ##this is a counter clock to check if the stop_status variable has changed
                    if self.Stop == True:
                        self.StopBoard()
                        break
                    elif self.Pause == True:
                        self.PauseBoard()
                        for count_pause1 in range(target):
                            if self.Stop == True:
                                break
                            elif self.Resume == True:
                                with open(output_txt_path(), "a") as OUTPUT:
                                    comment = f"{self.ClockStop.strftime('#X')}  Interface resumed by the user."
                                    OUTPUT.write(comment + "\n")
                                    print(comment)
                                self.SetValves2(d1,v11,v12,v13,v14)                                    
                                self.flag_break_countpause = 1
                                break
                            time.sleep(scan_rate)
                    elif self.C4VM[i1].FlagIsDone == False:
                        self.C4VM[i1].UpdateStatus()
                    if self.flag_break_countpause == 1:
                        break
                    elif self.C4VM[i1].FlagIsDone == True:
                        self.C4VM[i1].displayswitchstop()
                        break
                    time.sleep(scan_rate)
