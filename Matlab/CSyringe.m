classdef CSyringe < handle    
    properties (GetAccess = 'public', SetAccess = 'public', SetObservable)
        / General info
        device = [];
        name = [];
        address = [];
        
        / Syringes info
        maxFlowrate = [];
        minFlowrate = [];
        Flowrate = [];
        diameter = [];
        maxVolume = [];
        
        / Flags
        FlagIsMoving = false;
        FlagIsDone = true;
        FlagIsOnline = false;
        FlagIsStalled = false; 
        FlagIsMovingIn = false;
        FlagIsMovingOut = false;
        FlagReady = true;
        FlagStop = false;
                
        / Clocks
        ClockStartCmd
        ClockStopCmd
        
        /Listener
        listener
        listener_stop
        
    end
    
    events
        MovingState
    end
    
     methods(Access = public)
         
        // Constructor
        function obj = CSyringe(Lboard,add_syr)
            obj.device=Lboard.eib.NewSPS01(int8(add_syr));
            obj.name=char(obj.device.GetName);
            obj.diameter=obj.device.CmdGetDiameter();
            obj.maxFlowrate=obj.device.GetMaxFlowrate();
            obj.minFlowrate=obj.device.GetMinFlowrate();
            obj.maxVolume=obj.device.GetMaxVolume();
            
            obj.listener = addlistener(obj, 'MovingState',@(src,evnt)obj.Updating()); /it listens for the obj.FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. obj.Ready = true again.
            obj.listener_stop = addlistener(obj, 'FlagStop', 'PostSet' , @(src,evnt)obj.StopSyr()); /it listens for the obj.FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. obj.Ready = true again.
            
            UpdateStatus(obj);
            
            diary on
            comment=['Syringe ' , obj.name, ' loaded.'];
            disp(comment);
            diary off
        end
        
        // UpdateStaus
        function UpdateStatus(obj)
            obj.device.CmdGetStatus();
            obj.FlagIsDone=obj.device.IsDone();
            obj.FlagIsMoving=obj.device.IsMoving();
            obj.FlagIsOnline=obj.device.IsOnline();
            obj.FlagIsStalled=obj.device.IsStalled();
            obj.FlagIsMovingIn=obj.device.IsMovingIn();
            obj.FlagIsMovingOut=obj.device.IsMovingOut();
            if obj.FlagIsStalled == true
                diary on
                obj.device.CmdStop();
                comment=['ERROR: Syringe ' , obj.name, ' is stalled.'];
                disp(comment);
                diary off
            end                    
        end
        
        // MoveTo        
        function MoveTo(obj,flowrate,volume)
            if obj.FlagIsDone == true
                obj.device.CmdSetFlowrate(flowrate);
                obj.Flowrate=flowrate;
                obj.device.CmdMoveToVolume(volume);
                obj.FlagReady = false;
                displaymovement(obj);
                if obj.FlagIsMoving == true
                    notify(obj,'MovingState');
                end
            end
        end
        
        // Display movement In and Out on cmdwindow              
        function displaymovement(obj)
            obj.ClockStartCmd=clock;
            UpdateStatus(obj);
            if obj.FlagIsMovingIn == true
                diary on
                comment=[num2str(obj.ClockStartCmd(4)) , ':' , num2str(obj.ClockStartCmd(5)) ,':' ,num2str(obj.ClockStartCmd(6)), ' Syringe ' , obj.name, ' is pulling at ',num2str(obj.Flowrate) , ' ul/min.'];                    
                disp(comment);
                diary off
            elseif obj.FlagIsMovingOut == true
                diary on
                comment=[num2str(obj.ClockStartCmd(4)) , ':' , num2str(obj.ClockStartCmd(5)) ,':' ,num2str(obj.ClockStartCmd(6)), ' Syringe ' , obj.name, ' is pushing at ',num2str(obj.Flowrate) , ' ul/min.'];                    
                disp(comment);
                diary off
            end 
        end          
             
        // Display stop movement on cmdwindow             
        function displaymovementstop(obj)
            obj.ClockStopCmd=clock;
            diary on
            comment=[num2str(obj.ClockStopCmd(4)) , ':' , num2str(obj.ClockStopCmd(5)) ,':' ,num2str(obj.ClockStopCmd(6)), ' Syringe ' , obj.name, ' is done.'];                
            disp(comment);
            diary off
            obj.FlagReady = true;
        end
        
         // Listener function
        function Updating(obj)
            if obj.FlagIsMoving == true
                while obj.FlagIsMoving == true
                    UpdateStatus(obj);
                end
                if obj.FlagIsDone == true
                    displaymovementstop(obj);
                end
            end            
        end
        
        function StopSyr(obj)
            if obj.FlagStop == true
               obj.device.CmdStop();
               obj.FlagStop = false;
            end
        end
        
         // Stop
        function Stop(obj)        
            obj.device.CmdStop();
            UpdateStatus(obj);
            obj.FlagReady = true;
        end  
        
         // Wait
        function Wait(obj,time_sec) 
            pause(time_sec)
            Stop(obj)
        end  
     end
end