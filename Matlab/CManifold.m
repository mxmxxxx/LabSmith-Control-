classdef CManifold < handle    
    properties (GetAccess = 'public', SetAccess = 'public', SetObservable)
        // General info
        device = [];
        name = [];
        address = [];
        
        // Flags
//         FlagIsMoving = false;
        FlagIsDone = true;
        FlagIsOnline = false; 
        FlagReady = true;
        
        // Clocks
        ClockStartCmd
        ClockStopCmd
    end
    
     methods(Access = public)
         
        // Constructor
        function obj = CManifold(Lboard,add_syr)
            obj.device=Lboard.eib.New4VM(int8(add_syr));
            obj.name=char(obj.device.GetName);
            
            UpdateStatus(obj);
            
            diary on
            comment=['Manifold ' , obj.name, ' loaded.'];
            disp(comment);  
            diary off
        end
        
        // UpdateStaus
        function UpdateStatus(obj)
            obj.device.CmdGetStatus();
            obj.FlagIsDone=obj.device.IsDone();
            obj.FlagIsOnline=obj.device.IsOnline();                  
        end
        
                // Switch Valves
        function SwitchValves(obj,v1,v2,v3,v4)
            obj.device.CmdSetValves(int8(v1),int8(v2),int8(v3),int8(v4));
            obj.FlagReady = false;
            displayswitch(obj,v1,v2,v3,v4);
            while obj.FlagIsDone == false
                UpdateStatus(obj);
            end
            if obj.FlagIsDone == true
                displayswitchstop(obj)
            end
        end
        
        // Display switch start
        function displayswitch(obj,v1,v2,v3,v4)
            obj.ClockStartCmd=clock;
            UpdateStatus(obj);
            diary on
            comment=[num2str(obj.ClockStartCmd(4)) , ':' , num2str(obj.ClockStartCmd(5)) ,':' ,num2str(obj.ClockStartCmd(6)), ' 4VM ' , obj.name, ' is switching valves to ',num2str(v1) , ', ',num2str(v2) , ', ',num2str(v3) , ', ',num2str(v4) , '.'];  
            disp(comment);
            diary off
        end
        
        // Display switch stop
        function displayswitchstop(obj)
            obj.ClockStopCmd=clock;
/             UpdateStatus(obj);
            diary on
            comment=[num2str(obj.ClockStopCmd(4)) , ':' , num2str(obj.ClockStopCmd(5)) ,':' ,num2str(obj.ClockStopCmd(6)), ' 4VM ' , obj.name, ' is done.']; 
            disp(comment);
            diary off
            obj.FlagReady = true;
        end
     end
end