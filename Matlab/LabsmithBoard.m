classdef LabsmithBoard < handle    
    properties (GetAccess = 'public', SetAccess = 'public', SetObservable)
        // General info
        MaxNumDev = [];
        TotNumDev = [];
        eib = [];
        C4VM = [];
        SPS01 = [];
        
        // Flags
        isConnected = false;
        isDisconnected = true;
        Stop = false;
        Pause = false;
        Resume = false;
        flag_break_countpause = 0;
        flag_break_stop = 0;
        flag_a = 0; // flag used in listener of MoveWait function used to print just the initial target waiting time
        flag_b = 0; // flag used in listener of MoveWait function used to print just the initial target waiting time
                   
        // Clocks
        ClockStartConnection
        ClockStopConnection
        ClockStop
        ClockResume
        
        // Listener
        listener_firstdone // to check the first syringe to be done
        // listener_stop // to stop execution
        listener_firstdoneM
        listener_firstdonepause
        listener_firstdonepausewait
    end
    
    events
        FirstDone
        FirstDoneStop
        FirstDoneStopM
        FirstDoneStopPause
        FirstDoneStopPauseM
        FirstDoneStopPauseWait
    end
    
    methods(Access = public)
         
        //// Constructor
        function obj = LabsmithBoard(port) // com is the comment i show on the Output text area in the app
            py.importlib.import_module('uProcess_x64');
            obj.eib=py.uProcess_x64.CEIB();
            a=obj.eib.InitConnection(int8(port));
            if a == 0
                obj.isConnected = true;
                obj.isDisconnected = false;
                obj.ClockStartConnection = clock;
                diary OUTPUT
                comment=['Connected on ' , num2str(obj.ClockStartConnection(3)), '/' , num2str(obj.ClockStartConnection(2)), '/' , num2str(obj.ClockStartConnection(1)), ' at ', num2str(obj.ClockStartConnection(4)) , ':' , num2str(obj.ClockStartConnection(5)) ,':' ,num2str(obj.ClockStartConnection(6))];
                disp(comment);
                diary off
                Load(obj);

            else
                diary on
                comment='Not connected, check the right COM port on Device Manager';
                disp(comment)
                diary off
            end        
        end
        
         //// Destructor
        function com=Disconnect(obj)
            a=int64(obj.eib.CloseConnection());
            if a == 0
                obj.isConnected = false;
                obj.isDisconnected = true;
                obj.ClockStopConnection = clock;
                diary on
                comment=['Disconnected on ' , num2str(obj.ClockStopConnection(3)), '/' , num2str(obj.ClockStopConnection(2)), '/' , num2str(obj.ClockStopConnection(1)), ' at ', num2str(obj.ClockStopConnection(4)) , ':' , num2str(obj.ClockStopConnection(5)) ,':' ,num2str(obj.ClockStopConnection(6))];
                disp(comment);
                diary off
                com=convertCharsToStrings(comment);
                namefile=strcat('OUTPUT_',datestr(now,'yy_mm_dd_HH_MM_SS'),'.txt');
                copyfile('OUTPUT', namefile); 
                delete OUTPUT;
            else
                comment='Error, still connected';
                diary on
                disp(comment)
                diary off
                com=convertCharsToStrings(comment);
            end                          
        end
        
        //// Load
        function Load(obj)
            dev_list=char(obj.eib.CmdCreateDeviceList());
            expression = '\,'; //i first split the string into multiple strings
            splitStr = regexp(dev_list,expression,'split'); //divide all the different devices. It is a cell array. Each cell is a segment of the dev_list char vector containing info about each device
            NumDev=size(splitStr);
            obj.TotNumDev=NumDev(1,2);

            PAT_S1="[<uProcess.CSyringe>"; // at the start of dev_list
            PAT_M1="[<uProcess.C4VM>"; // at the start of dev_list
            PAT_S=" <uProcess.CSyringe>"; // in the middle of dev_list
            PAT_M=" <uProcess.C4VM>"; // in the middle of dev_list


            StrSyringe=[]; // it will concatenait all the cells of splitStr related to syringes in a char 
            StrManifold=[]; // it will concatenait all the cells of splitStr related to manifolds in a char 

            TF_S = startsWith(splitStr{1,1},PAT_S1); //checks if the first cell splitStr{1,1} is a syringe, ie if it starts with the PAT_S1. If yes it is equals to 1 otherwise 0;
            TF_M = startsWith(splitStr{1,1},PAT_M1); //checks if the first cell splitStr{1,1} is a manifold, ie if it starts with the PAT_M1. If yes it is equals to 1 otherwise 0;

            if TF_S == 1 //if the first device in dev_list is a syringe
                StrSyringe=[StrSyringe splitStr{1,1}]; // I add this cell splitStr{1,1} on StrSyringe
            elseif TF_M == 1 //if the first device in dev_list is a manifols
                StrManifold=[StrManifold splitStr{1,1}];  // I add this cell splitStr{1,1} on StrManifold
            end
            
            for i=2:obj.TotNumDev //lets check now the rest of the devices, from 2 to the last one
                TF_S = startsWith(splitStr{1,i},PAT_S); // compares now each cell with PAT_S, as we are now in the middle
                TF_M = startsWith(splitStr{1,i},PAT_M); // compares now each cell with PAT_M, as we are now in the middle
                if TF_S == 1
                    StrSyringe=[StrSyringe splitStr{1,i}]; 
                elseif TF_M == 1
                    StrManifold=[StrManifold splitStr{1,i}];
                end
            end
            //StrManifold = ' <uProcess.C4VM> named 'Manifold1' on address 35 <uProcess.C4VM> named 'Manifold2' on address 74]'
            //StrSyringe = '[<uProcess.CSyringe> named 'Pump_pH' on address 1 with last volume reading 0.000 ul <uProcess.CSyringe> named 'Pump_Na' on address 3 with last volume reading 0.000 ul <uProcess.CSyringe> named 'Pump_K' on address 8 with last volume reading 0.000 ul <uProcess.CSyringe> named 'Pump_aCSF' on address 14 with last volume reading 0.000 ul <uProcess.CSyringe> named 'Pump_Ca' on address 26 with last volume reading 0.000 ul'
            
            if ~isempty(StrManifold)
                PAT="address " + digitsPattern;
                add_man=extract(StrManifold,PAT); //add_man ={'address 35'}{'address 74'} 2×1 cell array
                PAT=digitsPattern;
                add_man=str2double(extract(add_man,PAT)); // OUTPUT 2: add_man =[35;74]. It is 2x1 vector containg the addresses of the manifolds on the board 
                obj.C4VM=cell(1,length(add_man));
                for i=1:length(add_man)
                    obj.C4VM{1,i} = CManifold(obj,add_man(i)); // it constructs a SPS01 object on the specified address. We will use this for the command
                    obj.C4VM{1,i}.address=add_man(i);
                end
            end

            if ~isempty(StrSyringe)
                PAT="address " + digitsPattern;
                add_syr=extract(StrSyringe,PAT); // add_syr = 5×1 cell array {'address 1' }{'address 3' }{'address 8' }{'address 14'}{'address 26'}
                PAT=digitsPattern;
                add_syr=str2double(extract(add_syr,PAT));// OUTPUT 4: add_syr =[1;3;8;14;26].  It is 5x1 vector containg the addresses of the syringes on the board                                
                obj.SPS01=cell(1,length(add_syr));
                for i=1:length(add_syr)
                    obj.SPS01{1,i} = CSyringe(obj,add_syr(i)); // it constructs a SPS01 object on the specified address. We will use this for the command
                    obj.SPS01{1,i}.address=add_syr(i);
                end
            end                      
        end
        
        //// Stop
        function StopBoard (obj)
            for i=1:size(obj.SPS01,2)
                obj.SPS01{1,i}.device.CmdStop();
                obj.SPS01{1,i}.FlagReady = true;
                UpdateStatus(obj.SPS01{1,i});
            end
            for i=1:size(obj.C4VM,2)
                obj.C4VM{1,i}.device.CmdStop();
                UpdateStatus(obj.C4VM{1,i});
            end
            obj.ClockStop = clock;
            comment=[num2str(obj.ClockStop(4)) , ':' , num2str(obj.ClockStop(5)) ,':' ,num2str(obj.ClockStop(6)), ' Interface stopped by the user.']; 
            diary on
            disp(comment);
            diary off
        end 
        
        //// Move
        function Move(obj,namedevice,flowrate,volume)
            k=[];
            for i=1:size(obj.SPS01,2)
                k=[k strcmp(obj.SPS01{1,i}.name,namedevice)];                
            end
            i=find(k==1);
            if ~isempty(i)
                MoveTo(obj.SPS01{1,i},flowrate,volume)
            else
                diary on
                comment='ERROR: Name syringe not correct';
                disp(comment);
                diary off
            end                
        end
        
        //// Move2
        function Move2(obj,namedevice,flowrate,volume)
            k=[];
            for i=1:size(obj.SPS01,2)
                k=[k strcmp(obj.SPS01{1,i}.name,namedevice)];                
            end
            i=find(k==1);
            if ~isempty(i)
                MoveTo(obj.SPS01{1,i},flowrate,volume)
            else
                diary on
                comment='ERROR: Name syringe not correct';
                disp(comment);
                diary off
            end                
        end
        
        //// FindIndexS (find index of Syringe from name of device)
        function out=FindIndexS(obj,n)
            k=[];
            for i=1:size(obj.SPS01,2)
                k=[k strcmp(obj.SPS01{1,i}.name,n)];                
            end
            out=find(k==1);
            if isempty(out)
               comment=['Error : ' ,n, ' does not exist. Check name again.'];
               disp(comment); 
            end
        end
        
        //// FindIndexM (find index of Manifold from name of device)
        function [out,com]=FindIndexM(obj,n)
            k=[];
            for i=1:size(obj.C4VM,2)
                k=[k strcmp(obj.C4VM{1,i}.name,n)];                
            end
            out=find(k==1);
            if isempty(out)
               diary on
               comment=['Error : ' ,n, ' does not exist. Check name again.'];
               disp(comment);
               diary off
               com=convertCharsToStrings(comment);
            end
        end
        
        
        //// Set Multiple FlowRates (at the same time)
        
        function SetFlowRate(obj,d1,f1,d2,f2,d3,f3,d4,f4,d5,f5,d6,f6,d7,f7,d8,f8)
            if rem(nargin,2) == 0
                disp('Error, missing input. Number of inputs has to be odd (interface, name of syringes and corresponding flow rates).');
            else
                if nargin == 3
                    i1=FindIndexS(obj,d1);
                    if ~isempty(i1)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);                        
                        obj.SPS01{1,i1}.Flowrate = f1;
                    end
                elseif nargin == 5
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    if ~isempty(i1) && ~isempty(i2)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2;                        
                    end
                elseif nargin == 7
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                    end
                elseif nargin == 9
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                        obj.SPS01{1,i4}.device.CmdSetFlowrate(f4);
                        obj.SPS01{1,i4}.Flowrate = f4;
                    end
                elseif nargin == 11
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                        obj.SPS01{1,i4}.device.CmdSetFlowrate(f4);
                        obj.SPS01{1,i4}.Flowrate = f4;
                        obj.SPS01{1,i5}.device.CmdSetFlowrate(f5);
                        obj.SPS01{1,i5}.Flowrate = f5;
                    end
                elseif nargin == 13
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                        obj.SPS01{1,i4}.device.CmdSetFlowrate(f4);
                        obj.SPS01{1,i4}.Flowrate = f4;
                        obj.SPS01{1,i5}.device.CmdSetFlowrate(f5);
                        obj.SPS01{1,i5}.Flowrate = f5;
                        obj.SPS01{1,i6}.device.CmdSetFlowrate(f6);
                        obj.SPS01{1,i6}.Flowrate = f6;
                    end
                elseif nargin == 15
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    i7=FindIndexS(obj,d7);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                        obj.SPS01{1,i4}.device.CmdSetFlowrate(f4);
                        obj.SPS01{1,i4}.Flowrate = f4;
                        obj.SPS01{1,i5}.device.CmdSetFlowrate(f5);
                        obj.SPS01{1,i5}.Flowrate = f5;
                        obj.SPS01{1,i6}.device.CmdSetFlowrate(f6);
                        obj.SPS01{1,i6}.Flowrate = f6;
                        obj.SPS01{1,i7}.device.CmdSetFlowrate(f7);
                        obj.SPS01{1,i7}.Flowrate = f7;
                    end
                elseif nargin == 17
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    i7=FindIndexS(obj,d7);
                    i8=FindIndexS(obj,d8);
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7) && ~isempty(i8)
                        obj.SPS01{1,i1}.device.CmdSetFlowrate(f1);
                        obj.SPS01{1,i1}.Flowrate = f1;
                        obj.SPS01{1,i2}.device.CmdSetFlowrate(f2);
                        obj.SPS01{1,i2}.Flowrate = f2; 
                        obj.SPS01{1,i3}.device.CmdSetFlowrate(f3);
                        obj.SPS01{1,i3}.Flowrate = f3;
                        obj.SPS01{1,i4}.device.CmdSetFlowrate(f4);
                        obj.SPS01{1,i4}.Flowrate = f4;
                        obj.SPS01{1,i5}.device.CmdSetFlowrate(f5);
                        obj.SPS01{1,i5}.Flowrate = f5;
                        obj.SPS01{1,i6}.device.CmdSetFlowrate(f6);
                        obj.SPS01{1,i6}.Flowrate = f6;
                        obj.SPS01{1,i7}.device.CmdSetFlowrate(f7);
                        obj.SPS01{1,i7}.Flowrate = f7;
                        obj.SPS01{1,i7}.device.CmdSetFlowrate(f8);
                        obj.SPS01{1,i7}.Flowrate = f8;
                    end
                end
            end
        end
        
        
        function MulMove(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7,d8,v8)
            if rem(nargin,2) == 0
                disp('Error, missing input. Number of inputs has to be odd (interface, name of syringes and corresponding flow rates).');
            else
                if nargin == 3 // 1 syringe as input
                    i1=FindIndexS(obj,d1);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                    if ~isempty(i1)                        
                        if obj.SPS01{1,i1}.FlagIsDone == true
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);                            
                            obj.SPS01{1,i1}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            if obj.SPS01{1,i1}.FlagIsMoving == true
                                notify(obj.SPS01{1,i1},'MovingState');
                            end
                        end
                    end
                elseif nargin == 5 // 2 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2); 
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2)
                        if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2})  
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                                notify(obj,'FirstDone');
                            end
                        end
                    end
                elseif nargin == 7 // 3 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end                    
                elseif nargin == 9 // 4 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3,i4)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        obj.SPS01{1,i4}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        displaymovement(obj.SPS01{1,i4})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end
                elseif nargin == 11 // 5 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3,i4,i5)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                        obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        obj.SPS01{1,i4}.FlagReady = false;
                        obj.SPS01{1,i5}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        displaymovement(obj.SPS01{1,i4})
                        displaymovement(obj.SPS01{1,i5})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end
                elseif nargin == 13 // 6 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3,i4,i5,i6)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                        obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                        obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        obj.SPS01{1,i4}.FlagReady = false;
                        obj.SPS01{1,i5}.FlagReady = false;
                        obj.SPS01{1,i6}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        displaymovement(obj.SPS01{1,i4})
                        displaymovement(obj.SPS01{1,i5})
                        displaymovement(obj.SPS01{1,i6})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end
                elseif nargin == 15 // 7 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    i7=FindIndexS(obj,d7);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3,i4,i5,i6,i7)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                        obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                        obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                        obj.SPS01{1,i7}.device.CmdMoveToVolume(v7);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        obj.SPS01{1,i4}.FlagReady = false;
                        obj.SPS01{1,i5}.FlagReady = false;
                        obj.SPS01{1,i6}.FlagReady = false;
                        obj.SPS01{1,i7}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        displaymovement(obj.SPS01{1,i4})
                        displaymovement(obj.SPS01{1,i5})
                        displaymovement(obj.SPS01{1,i6})
                        displaymovement(obj.SPS01{1,i7})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end
                elseif nargin == 17 // 8 syringes as input
                    i1=FindIndexS(obj,d1);
                    i2=FindIndexS(obj,d2);
                    i3=FindIndexS(obj,d3);
                    i4=FindIndexS(obj,d4);
                    i5=FindIndexS(obj,d5);
                    i6=FindIndexS(obj,d6);
                    i7=FindIndexS(obj,d7);
                    i8=FindIndexS(obj,d8);
                    obj.listener_firstdone = addlistener(obj, 'FirstDone',@(src,evnt)obj.CheckFirstDone(src,evnt,i1,i2,i3,i4,i5,i6,i7,i8)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                    if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7) && ~isempty(i8)
                        obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                        obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                        obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                        obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                        obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                        obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                        obj.SPS01{1,i7}.device.CmdMoveToVolume(v7);
                        obj.SPS01{1,i8}.device.CmdMoveToVolume(v8);
                        obj.SPS01{1,i1}.FlagReady = false;
                        obj.SPS01{1,i2}.FlagReady = false;
                        obj.SPS01{1,i3}.FlagReady = false;
                        obj.SPS01{1,i4}.FlagReady = false;
                        obj.SPS01{1,i5}.FlagReady = false;
                        obj.SPS01{1,i6}.FlagReady = false;
                        obj.SPS01{1,i7}.FlagReady = false;
                        obj.SPS01{1,i8}.FlagReady = false;
                        displaymovement(obj.SPS01{1,i1})
                        displaymovement(obj.SPS01{1,i2}) 
                        displaymovement(obj.SPS01{1,i3})
                        displaymovement(obj.SPS01{1,i4})
                        displaymovement(obj.SPS01{1,i5})
                        displaymovement(obj.SPS01{1,i6})
                        displaymovement(obj.SPS01{1,i7})
                        displaymovement(obj.SPS01{1,i8})
                        if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                            notify(obj,'FirstDone');
                        end
                    end
                end
            end
        end
            
        //// Multiple Movement with stop (at the same time. It allows the stop)
        function MulMove2(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7,d8,v8)
            if obj.Stop == false
                    if rem(nargin,2) == 0
                        disp('Error, missing input. Number of inputs has to be odd (interface, name of syringes and corresponding flow rates).');
                    else
                        if nargin == 3 // 1 syringe as input
                            i1=FindIndexS(obj,d1);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                            if ~isempty(i1)                        
                                if obj.SPS01{1,i1}.FlagIsDone == true 
                                   obj.SPS01{1,i1}.device.CmdMoveToVolume(v1); 
                                   obj.SPS01{1,i1}.FlagReady = false;
                                   displaymovement(obj.SPS01{1,i1})
                                   if obj.SPS01{1,i1}.FlagIsMoving == true 
                                        notify(obj,'FirstDoneStop');
                                   end
                                end
                            end
                        elseif nargin == 5 // 2 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2); 
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2)
                                if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true
                                    obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                    obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                    obj.SPS01{1,i1}.FlagReady = false;
                                    obj.SPS01{1,i2}.FlagReady = false;
                                    displaymovement(obj.SPS01{1,i1})
                                    displaymovement(obj.SPS01{1,i2})  
                                    if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                                        notify(obj,'FirstDoneStop');
                                    end
                                end
                            end
                        elseif nargin == 7 // 3 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end                    
                        elseif nargin == 9 // 4 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            i4=FindIndexS(obj,d4);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3,i4)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                displaymovement(obj.SPS01{1,i4})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end
                        elseif nargin == 11 // 5 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            i4=FindIndexS(obj,d4);
                            i5=FindIndexS(obj,d5);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3,i4,i5)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                obj.SPS01{1,i5}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                displaymovement(obj.SPS01{1,i4})
                                displaymovement(obj.SPS01{1,i5})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end
                        elseif nargin == 13 // 6 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            i4=FindIndexS(obj,d4);
                            i5=FindIndexS(obj,d5);
                            i6=FindIndexS(obj,d6);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3,i4,i5,i6)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                                obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                obj.SPS01{1,i5}.FlagReady = false;
                                obj.SPS01{1,i6}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                displaymovement(obj.SPS01{1,i4})
                                displaymovement(obj.SPS01{1,i5})
                                displaymovement(obj.SPS01{1,i6})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end
                        elseif nargin == 15 // 7 syringes as input
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            i4=FindIndexS(obj,d4);
                            i5=FindIndexS(obj,d5);
                            i6=FindIndexS(obj,d6);
                            i7=FindIndexS(obj,d7);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3,i4,i5,i6,i7)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                                obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                                obj.SPS01{1,i7}.device.CmdMoveToVolume(v7);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                obj.SPS01{1,i5}.FlagReady = false;
                                obj.SPS01{1,i6}.FlagReady = false;
                                obj.SPS01{1,i7}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                displaymovement(obj.SPS01{1,i4})
                                displaymovement(obj.SPS01{1,i5})
                                displaymovement(obj.SPS01{1,i6})
                                displaymovement(obj.SPS01{1,i7})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end
                        elseif nargin == 17 // 8 syringes as input (impossible - max numb of syringes is 7)
                            i1=FindIndexS(obj,d1);
                            i2=FindIndexS(obj,d2);
                            i3=FindIndexS(obj,d3);
                            i4=FindIndexS(obj,d4);
                            i5=FindIndexS(obj,d5);
                            i6=FindIndexS(obj,d6);
                            i7=FindIndexS(obj,d7);
                            i8=FindIndexS(obj,d8);
                            obj.listener_firstdone = addlistener(obj, 'FirstDoneStop',@(src,evnt)obj.CheckFirstDoneStop(src,evnt,i1,i2,i3,i4,i5,i6,i7,i8)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                            if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7) && ~isempty(i8)
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                                obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                                obj.SPS01{1,i7}.device.CmdMoveToVolume(v7);
                                obj.SPS01{1,i8}.device.CmdMoveToVolume(v8);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                obj.SPS01{1,i5}.FlagReady = false;
                                obj.SPS01{1,i6}.FlagReady = false;
                                obj.SPS01{1,i7}.FlagReady = false;
                                obj.SPS01{1,i8}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2}) 
                                displaymovement(obj.SPS01{1,i3})
                                displaymovement(obj.SPS01{1,i4})
                                displaymovement(obj.SPS01{1,i5})
                                displaymovement(obj.SPS01{1,i6})
                                displaymovement(obj.SPS01{1,i7})
                                displaymovement(obj.SPS01{1,i8})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStop');
                                end
                            end
                        end
                    end    
            end
        end
        
        //// Listener Function : Display the first device to be done (called in MulMove)
        function CheckFirstDone(obj,varargin)
            if nargin == 4 // only one syringe in motion (=numb input + obj + 2more input (source and event))   
                i1=varargin{3}; //vararging doesnt include the obj, so its size is nargin-1. The index is the last.
                if obj.SPS01{1,i1}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true
                        displaymovementstop(obj.SPS01{1,i1})
                    end
                end
            elseif nargin == 5
                    i1=varargin{3}; 
                    i2=varargin{4};
                    i=[i1 i2]; 
                    if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true 
                        while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; // a=[i2] for j=1, a=[i1] for j=2
                                    while obj.SPS01{1,a(1)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                    end                               
                                    if obj.SPS01{1,a(1)}.FlagIsDone == true
                                        displaymovementstop(obj.SPS01{1,a(1)})                                        
                                    end                                
                                    break
                                end
                            end
                        end
                    end
            elseif nargin == 6
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i=[i1 i2 i3]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true 
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true 
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; // a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)}); 
                                            end                                       
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true
                                                displaymovementstop(obj.SPS01{1,b(1)})                                               
                                            end                                        
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end
            elseif nargin == 7
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i=[i1 i2 i3 i4]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                        UpdateStatus(obj.SPS01{1,i4});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; 
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                        UpdateStatus(obj.SPS01{1,a(3)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)});
                                               UpdateStatus(obj.SPS01{1,b(2)});
                                            end
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true
                                                for p=1:size(b,2)
                                                    if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                        displaymovementstop(obj.SPS01{1,b(p)})
                                                        c=b;
                                                        c(p)=[];
                                                        while obj.SPS01{1,c(1)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                        end 
                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true
                                                            displaymovementstop(obj.SPS01{1,c(1)})
                                                        end
                                                        break
                                                    end
                                                end
                                            end
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end
            elseif nargin == 8
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i=[i1 i2 i3 i4 i5]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                        UpdateStatus(obj.SPS01{1,i4});
                        UpdateStatus(obj.SPS01{1,i5});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; 
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                        UpdateStatus(obj.SPS01{1,a(3)});
                                        UpdateStatus(obj.SPS01{1,a(4)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)});
                                               UpdateStatus(obj.SPS01{1,b(2)});
                                               UpdateStatus(obj.SPS01{1,b(3)});
                                            end
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true
                                                for p=1:size(b,2)
                                                    if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                        displaymovementstop(obj.SPS01{1,b(p)})
                                                        c=b;
                                                        c(p)=[];
                                                        while obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving
                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                        end 
                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true
                                                            for q=1:size(c,2)
                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                    d=c;
                                                                    d(q)=[];
                                                                    while obj.SPS01{1,d(1)}.FlagIsMoving
                                                                        UpdateStatus(obj.SPS01{1,d(1)});
                                                                    end 
                                                                    if obj.SPS01{1,d(1)}.FlagIsDone
                                                                       displaymovementstop(obj.SPS01{1,d(1)})
                                                                    end
                                                                    break
                                                                end
                                                            end                                                    
                                                        end
                                                        break
                                                    end
                                                end
                                            end
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end
            elseif nargin == 9
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i=[i1 i2 i3 i4 i5 i6]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                        UpdateStatus(obj.SPS01{1,i4});
                        UpdateStatus(obj.SPS01{1,i5});
                        UpdateStatus(obj.SPS01{1,i6});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; 
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                        UpdateStatus(obj.SPS01{1,a(3)});
                                        UpdateStatus(obj.SPS01{1,a(4)});
                                        UpdateStatus(obj.SPS01{1,a(5)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)});
                                               UpdateStatus(obj.SPS01{1,b(2)});
                                               UpdateStatus(obj.SPS01{1,b(3)});
                                               UpdateStatus(obj.SPS01{1,b(4)});
                                            end
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true
                                                for p=1:size(b,2)
                                                    if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                        displaymovementstop(obj.SPS01{1,b(p)})
                                                        c=b;
                                                        c(p)=[];
                                                        while obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving
                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                        end 
                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true
                                                            for q=1:size(c,2)
                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                    d=c;
                                                                    d(q)=[];
                                                                    while obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving
                                                                        UpdateStatus(obj.SPS01{1,d(1)});
                                                                        UpdateStatus(obj.SPS01{1,d(2)});
                                                                    end 
                                                                    if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone
                                                                        for r=1:size(d,2)
                                                                            if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                displaymovementstop(obj.SPS01{1,d(r)})
                                                                                e=d;
                                                                                e(r)=[];
                                                                                while obj.SPS01{1,e(1)}.FlagIsMoving 
                                                                                    UpdateStatus(obj.SPS01{1,e(1)});
                                                                                end
                                                                                if obj.SPS01{1,e(1)}.FlagIsDone
                                                                                    displaymovementstop(obj.SPS01{1,e(1)})
                                                                                end
                                                                                break
                                                                            end
                                                                        end
                                                                    end
                                                                    break
                                                                end
                                                            end                                                    
                                                        end
                                                        break
                                                    end
                                                end
                                            end
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end
            elseif nargin == 10
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i7=varargin{9};
                i=[i1 i2 i3 i4 i5 i6 i7]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                        UpdateStatus(obj.SPS01{1,i4});
                        UpdateStatus(obj.SPS01{1,i5});
                        UpdateStatus(obj.SPS01{1,i6});
                        UpdateStatus(obj.SPS01{1,i7});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true || obj.SPS01{1,i7}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; 
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true && obj.SPS01{1,a(6)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                        UpdateStatus(obj.SPS01{1,a(3)});
                                        UpdateStatus(obj.SPS01{1,a(4)});
                                        UpdateStatus(obj.SPS01{1,a(5)});
                                        UpdateStatus(obj.SPS01{1,a(6)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true || obj.SPS01{1,a(6)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true && obj.SPS01{1,b(5)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)});
                                               UpdateStatus(obj.SPS01{1,b(2)});
                                               UpdateStatus(obj.SPS01{1,b(3)});
                                               UpdateStatus(obj.SPS01{1,b(4)});
                                               UpdateStatus(obj.SPS01{1,b(5)});
                                            end
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true || obj.SPS01{1,b(5)}.FlagIsDone == true
                                                for p=1:size(b,2)
                                                    if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                        displaymovementstop(obj.SPS01{1,b(p)})
                                                        c=b;
                                                        c(p)=[];
                                                        while obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving && obj.SPS01{1,c(4)}.FlagIsMoving
                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                            UpdateStatus(obj.SPS01{1,c(4)});
                                                        end 
                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true || obj.SPS01{1,c(4)}.FlagIsDone == true
                                                            for q=1:size(c,2)
                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                    d=c;
                                                                    d(q)=[];
                                                                    while obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving && obj.SPS01{1,d(3)}.FlagIsMoving
                                                                        UpdateStatus(obj.SPS01{1,d(1)});
                                                                        UpdateStatus(obj.SPS01{1,d(2)});
                                                                        UpdateStatus(obj.SPS01{1,d(3)});
                                                                    end 
                                                                    if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone || obj.SPS01{1,d(3)}.FlagIsDone
                                                                        for r=1:size(d,2)
                                                                            if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                displaymovementstop(obj.SPS01{1,d(r)})
                                                                                e=d;
                                                                                e(r)=[];
                                                                                while obj.SPS01{1,e(1)}.FlagIsMoving && obj.SPS01{1,e(2)}.FlagIsMoving 
                                                                                    UpdateStatus(obj.SPS01{1,e(1)});
                                                                                    UpdateStatus(obj.SPS01{1,e(2)});
                                                                                end
                                                                                if obj.SPS01{1,e(1)}.FlagIsDone || obj.SPS01{1,e(2)}.FlagIsDone
                                                                                    for s=1:size(e,2)
                                                                                        if obj.SPS01{1,e(s)}.FlagIsDone == true
                                                                                            displaymovementstop(obj.SPS01{1,e(s)})
                                                                                            f=e;
                                                                                            f(s)=[];
                                                                                            while obj.SPS01{1,f(1)}.FlagIsMoving
                                                                                                UpdateStatus(obj.SPS01{1,f(1)});
                                                                                            end
                                                                                            if obj.SPS01{1,f(1)}.FlagIsDone 
                                                                                                displaymovementstop(obj.SPS01{1,f(1)})
                                                                                            end
                                                                                            break
                                                                                        end
                                                                                    end
                                                                                end
                                                                                break
                                                                            end
                                                                        end
                                                                    end
                                                                    break
                                                                end
                                                            end                                                    
                                                        end
                                                        break
                                                    end
                                                end
                                            end
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end
            elseif nargin == 11
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i7=varargin{9};
                i8=varargin{10};
                i=[i1 i2 i3 i4 i5 i6 i7 i8]; //i=varargin{3:nargin-1}
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                    while obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                        UpdateStatus(obj.SPS01{1,i1});
                        UpdateStatus(obj.SPS01{1,i2});
                        UpdateStatus(obj.SPS01{1,i3});
                        UpdateStatus(obj.SPS01{1,i4});
                        UpdateStatus(obj.SPS01{1,i5});
                        UpdateStatus(obj.SPS01{1,i6});
                        UpdateStatus(obj.SPS01{1,i7});
                        UpdateStatus(obj.SPS01{1,i8});
                    end
                    if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true || obj.SPS01{1,i7}.FlagIsDone == true || obj.SPS01{1,i8}.FlagIsDone == true
                        for j=1:size(i,2)
                            if obj.SPS01{1,i(j)}.FlagIsDone == true
                                displaymovementstop(obj.SPS01{1,i(j)})
                                a=i;
                                a(j)=[]; 
                                while obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true && obj.SPS01{1,a(6)}.FlagIsMoving == true && obj.SPS01{1,a(7)}.FlagIsMoving == true
                                        UpdateStatus(obj.SPS01{1,a(1)});
                                        UpdateStatus(obj.SPS01{1,a(2)});
                                        UpdateStatus(obj.SPS01{1,a(3)});
                                        UpdateStatus(obj.SPS01{1,a(4)});
                                        UpdateStatus(obj.SPS01{1,a(5)});
                                        UpdateStatus(obj.SPS01{1,a(6)});
                                        UpdateStatus(obj.SPS01{1,a(7)});
                                end
                                if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true || obj.SPS01{1,a(6)}.FlagIsDone == true || obj.SPS01{1,a(7)}.FlagIsDone == true
                                    for k=1:size(a,2)  
                                        if obj.SPS01{1,a(k)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(k)})
                                            b=a;
                                            b(k)=[];
                                            while obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true && obj.SPS01{1,b(5)}.FlagIsMoving == true && obj.SPS01{1,b(6)}.FlagIsMoving == true
                                               UpdateStatus(obj.SPS01{1,b(1)});
                                               UpdateStatus(obj.SPS01{1,b(2)});
                                               UpdateStatus(obj.SPS01{1,b(3)});
                                               UpdateStatus(obj.SPS01{1,b(4)});
                                               UpdateStatus(obj.SPS01{1,b(5)});
                                               UpdateStatus(obj.SPS01{1,b(6)});
                                            end
                                            if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true || obj.SPS01{1,b(5)}.FlagIsDone == true || obj.SPS01{1,b(6)}.FlagIsDone == true
                                                for p=1:size(b,2)
                                                    if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                        displaymovementstop(obj.SPS01{1,b(p)})
                                                        c=b;
                                                        c(p)=[];
                                                        while obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving && obj.SPS01{1,c(4)}.FlagIsMoving && obj.SPS01{1,c(5)}.FlagIsMoving
                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                            UpdateStatus(obj.SPS01{1,c(4)});
                                                            UpdateStatus(obj.SPS01{1,c(5)});
                                                        end 
                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true || obj.SPS01{1,c(4)}.FlagIsDone == true || obj.SPS01{1,c(5)}.FlagIsDone == true
                                                            for q=1:size(c,2)
                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                    d=c;
                                                                    d(q)=[];
                                                                    while obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving && obj.SPS01{1,d(3)}.FlagIsMoving && obj.SPS01{1,d(4)}.FlagIsMoving
                                                                        UpdateStatus(obj.SPS01{1,d(1)});
                                                                        UpdateStatus(obj.SPS01{1,d(2)});
                                                                        UpdateStatus(obj.SPS01{1,d(3)});
                                                                        UpdateStatus(obj.SPS01{1,d(4)});
                                                                    end 
                                                                    if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone || obj.SPS01{1,d(3)}.FlagIsDone || obj.SPS01{1,d(4)}.FlagIsDone
                                                                        for r=1:size(d,2)
                                                                            if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                displaymovementstop(obj.SPS01{1,d(r)})
                                                                                e=d;
                                                                                e(r)=[];
                                                                                while obj.SPS01{1,e(1)}.FlagIsMoving && obj.SPS01{1,e(2)}.FlagIsMoving && obj.SPS01{1,e(3)}.FlagIsMoving 
                                                                                    UpdateStatus(obj.SPS01{1,e(1)});
                                                                                    UpdateStatus(obj.SPS01{1,e(2)});
                                                                                    UpdateStatus(obj.SPS01{1,e(3)});
                                                                                end
                                                                                if obj.SPS01{1,e(1)}.FlagIsDone || obj.SPS01{1,e(2)}.FlagIsDone || obj.SPS01{1,e(3)}.FlagIsDone
                                                                                    for s=1:size(e,2)
                                                                                        if obj.SPS01{1,e(s)}.FlagIsDone == true
                                                                                            displaymovementstop(obj.SPS01{1,e(s)})
                                                                                            f=e;
                                                                                            f(s)=[];
                                                                                            while obj.SPS01{1,f(1)}.FlagIsMoving && obj.SPS01{1,f(2)}.FlagIsMoving
                                                                                                UpdateStatus(obj.SPS01{1,f(1)});
                                                                                                UpdateStatus(obj.SPS01{1,f(2)});
                                                                                            end
                                                                                            if obj.SPS01{1,f(1)}.FlagIsDone || obj.SPS01{1,f(2)}.FlagIsDone 
                                                                                                for t=1:size(f,2)
                                                                                                    if obj.SPS01{1,f(t)}.FlagIsDone
                                                                                                        displaymovementstop(obj.SPS01{1,f(t)})
                                                                                                        g=f;
                                                                                                        g(t)=[];
                                                                                                        while obj.SPS01{1,g(1)}.FlagIsMoving
                                                                                                            UpdateStatus(obj.SPS01{1,g(1)});
                                                                                                        end
                                                                                                        if obj.SPS01{1,g(1)}.FlagIsDone 
                                                                                                            displaymovementstop(obj.SPS01{1,g(1)})
                                                                                                        end
                                                                                                        break
                                                                                                    end
                                                                                                end
                                                                                            end
                                                                                            break
                                                                                        end
                                                                                    end
                                                                                end
                                                                                break
                                                                            end
                                                                        end
                                                                    end
                                                                    break
                                                                end
                                                            end                                                    
                                                        end
                                                        break
                                                    end
                                                end
                                            end
                                            break
                                        end
                                    end
                                end
                                break
                            end
                        end
                    end
                end 
            end
        end
                
        //// Listener Function : Display the first device to be done and Stop (called in MulMove2)
        function CheckFirstDoneStop(obj,varargin)
            if nargin == 4 // only one syringe in motion (=numb input + obj + 2more input (source and event))   
                i1=varargin{3}; //vararging doesnt include the obj, so its size is nargin-1. The index is the last.
                if obj.SPS01{1,i1}.FlagIsMoving == true                     
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for i=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true
                            displaymovementstop(obj.SPS01{1,i1})
                            break
                        end
                        pause(scan_rate)
                    end
                end
            elseif nargin == 5 // 2 syringes
                    i1=varargin{3}; 
                    i2=varargin{4};
                    i=[i1 i2]; 
                    if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true 
                        scan_rate=0.1; //the scan rate of the counter
                        target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours        
                        for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                            if obj.Stop == true
                                StopBoard(obj)
                                break // counter 1
                            elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                                UpdateStatus(obj.SPS01{1,i1});
                                UpdateStatus(obj.SPS01{1,i2});
                            end
                            if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true
                                for j=1:size(i,2) //search for first device to be done
                                    if obj.SPS01{1,i(j)}.FlagIsDone == true
                                        displaymovementstop(obj.SPS01{1,i(j)})
                                        a=i;
                                        a(j)=[];
                                        for count2=1:target
                                            if obj.Stop == true
                                                StopBoard(obj)
                                                break //counter 2
                                            elseif obj.SPS01{1,a(1)}.FlagIsMoving == true
                                                UpdateStatus(obj.SPS01{1,a(1)});
                                            end
                                            if obj.SPS01{1,a(1)}.FlagIsDone == true
                                                displaymovementstop(obj.SPS01{1,a(1)})
                                                break //counter 2
                                            end                                            
                                            pause(scan_rate)
                                        end                                            
                                        break // j search of first device to be done 
                                    end                                                                       
                                end
                                break // counter 1
                            end
                            pause(scan_rate)
                        end
                    end
            elseif nargin == 6 // 3 syringes
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i=[i1 i2 i3]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true 
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; // a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                                    for count2=1:target
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true
                                            for k=1:size(a,2)
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    for count3=1:target
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break //counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true
                                                            displaymovementstop(obj.SPS01{1,b(1)})
                                                            break //counter 3
                                                        end
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done 
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done 
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end
              
                
            elseif nargin == 7 // 4 syringes
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i=[i1 i2 i3 i4]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4}); 
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    scan_rate=0.1; //the scan rate of the counter
                                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours          
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});    
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    scan_rate=0.1; //the scan rate of the counter
                                                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours 
                                                    for count3=1:target
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    for count4=1:target
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                        end
                                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true
                                                                            displaymovementstop(obj.SPS01{1,c(1)})
                                                                            break // counter 4
                                                                        end
                                                                        pause(scan_rate)
                                                                    end
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break //counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break //counter 2
                                        end
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end                            
                                                        
            elseif nargin == 8 // 5 syringes
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i=[i1 i2 i3 i4 i5]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});                            
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});                                            
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});                                                            
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});                                                                            
                                                                        end
                                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});                                                                                            
                                                                                        end
                                                                                        if obj.SPS01{1,d(1)}.FlagIsDone
                                                                                            displaymovementstop(obj.SPS01{1,d(1)})
                                                                                            break //counter 5
                                                                                        end
                                                                                        pause(scan_rate)
                                                                                    end                                                                                    
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break // counter 4
                                                                        end                                                                        
                                                                        pause(scan_rate)
                                                                    end                                                                    
                                                                    break // p search of first device to be done
                                                                end
                                                            end 
                                                            break // counter 3
                                                        end
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end                        
                        pause(scan_rate)
                    end
                end                              
                                                                   
            elseif nargin == 9 // 6 syringes
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i=[i1 i2 i3 i4 i5 i6]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});
                            UpdateStatus(obj.SPS01{1,i6});                            
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});
                                            UpdateStatus(obj.SPS01{1,a(5)});                                            
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});
                                                            UpdateStatus(obj.SPS01{1,b(4)});                                                            
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                                            UpdateStatus(obj.SPS01{1,c(3)});                                                                            
                                                                        end
                                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});
                                                                                            UpdateStatus(obj.SPS01{1,d(2)});                                                                                            
                                                                                        end
                                                                                        if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone
                                                                                            for r=1:size(d,2)
                                                                                                if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                                    displaymovementstop(obj.SPS01{1,d(r)})
                                                                                                    e=d;
                                                                                                    e(r)=[];
                                                                                                    for count6=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                        if obj.Stop == true
                                                                                                            StopBoard(obj)
                                                                                                            break // counter 6
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsMoving
                                                                                                            UpdateStatus(obj.SPS01{1,e(1)});                                                                                                            
                                                                                                        end
                                                                                                        if obj.SPS01{1,e(1)}.FlagIsDone
                                                                                                            displaymovementstop(obj.SPS01{1,e(1)})
                                                                                                            break // counter 6
                                                                                                        end                                                                                                        
                                                                                                        pause(scan_rate)
                                                                                                    end                                                                                                    
                                                                                                    break // r search of first device to be done
                                                                                                end
                                                                                            end
                                                                                            break // counter 5
                                                                                        end
                                                                                        pause(scan_rate)
                                                                                    end 
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break //counter 4
                                                                        end                                                                        
                                                                        pause(scan_rate)
                                                                    end 
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break // Counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end                                                    
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end
                                                          
            elseif nargin == 10 //7 syringes
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i7=varargin{9};
                i=[i1 i2 i3 i4 i5 i6 i7]; 
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});
                            UpdateStatus(obj.SPS01{1,i6});
                            UpdateStatus(obj.SPS01{1,i7});
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true || obj.SPS01{1,i7}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true && obj.SPS01{1,a(6)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});
                                            UpdateStatus(obj.SPS01{1,a(5)});
                                            UpdateStatus(obj.SPS01{1,a(6)});
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true || obj.SPS01{1,a(6)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true && obj.SPS01{1,b(5)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});
                                                            UpdateStatus(obj.SPS01{1,b(4)});
                                                            UpdateStatus(obj.SPS01{1,b(5)});
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true || obj.SPS01{1,b(5)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving && obj.SPS01{1,c(4)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                                            UpdateStatus(obj.SPS01{1,c(4)});
                                                                        end
                                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true || obj.SPS01{1,c(4)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving && obj.SPS01{1,d(3)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});
                                                                                            UpdateStatus(obj.SPS01{1,d(2)});
                                                                                            UpdateStatus(obj.SPS01{1,d(3)});
                                                                                        end
                                                                                        if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone || obj.SPS01{1,d(3)}.FlagIsDone
                                                                                            for r=1:size(d,2)
                                                                                                if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                                    displaymovementstop(obj.SPS01{1,d(r)})
                                                                                                    e=d;
                                                                                                    e(r)=[];
                                                                                                    for count6=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                        if obj.Stop == true
                                                                                                            StopBoard(obj)
                                                                                                            break // counter 6
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsMoving && obj.SPS01{1,e(2)}.FlagIsMoving 
                                                                                                            UpdateStatus(obj.SPS01{1,e(1)});
                                                                                                            UpdateStatus(obj.SPS01{1,e(2)});
                                                                                                        end
                                                                                                        if obj.SPS01{1,e(1)}.FlagIsDone || obj.SPS01{1,e(2)}.FlagIsDone
                                                                                                            for s=1:size(e,2)
                                                                                                                if obj.SPS01{1,e(s)}.FlagIsDone == true
                                                                                                                    displaymovementstop(obj.SPS01{1,e(s)})
                                                                                                                    f=e;
                                                                                                                    f(s)=[];
                                                                                                                    for count7=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                                        if obj.Stop == true
                                                                                                                            StopBoard(obj)
                                                                                                                            break // counter 7
                                                                                                                        elseif obj.SPS01{1,f(1)}.FlagIsMoving
                                                                                                                            UpdateStatus(obj.SPS01{1,f(1)});
                                                                                                                        end
                                                                                                                        if obj.SPS01{1,f(1)}.FlagIsDone 
                                                                                                                            displaymovementstop(obj.SPS01{1,f(1)})
                                                                                                                            break // counter 7
                                                                                                                        end
                                                                                                                        pause(scan_rate)
                                                                                                                    end  
                                                                                                                    break // s search of first device to be done
                                                                                                                end
                                                                                                            end
                                                                                                            break // counter 6
                                                                                                        end  
                                                                                                        pause(scan_rate)
                                                                                                    end    
                                                                                                    break // r search of first device to be done
                                                                                                end
                                                                                            end
                                                                                            break // counter 5
                                                                                        end  
                                                                                        pause(scan_rate)
                                                                                    end  
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break // counter 4
                                                                        end      
                                                                        pause(scan_rate)
                                                                    end    
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break // counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end  
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end  
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end                        
                        pause(scan_rate)
                    end
                end
                          
            elseif nargin == 11 //8 syringes (impossible - max is 7)
                i1=varargin{3}; 
                i2=varargin{4};
                i3=varargin{5};
                i4=varargin{6};
                i5=varargin{7};
                i6=varargin{8};
                i7=varargin{9};
                i8=varargin{10};
                i=[i1 i2 i3 i4 i5 i6 i7 i8]; //i=varargin{3:nargin-1}
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                  scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true && obj.SPS01{1,i8}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});
                            UpdateStatus(obj.SPS01{1,i6});
                            UpdateStatus(obj.SPS01{1,i7});
                            UpdateStatus(obj.SPS01{1,i8});
                        end
                        if obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true || obj.SPS01{1,i7}.FlagIsDone == true || obj.SPS01{1,i8}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true && obj.SPS01{1,a(6)}.FlagIsMoving == true && obj.SPS01{1,a(7)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});
                                            UpdateStatus(obj.SPS01{1,a(5)});
                                            UpdateStatus(obj.SPS01{1,a(6)});
                                            UpdateStatus(obj.SPS01{1,a(7)});
                                        end
                                        if obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true || obj.SPS01{1,a(6)}.FlagIsDone == true || obj.SPS01{1,a(7)}.FlagIsDone == true
                                            for k=1:size(a,2)  
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true && obj.SPS01{1,b(5)}.FlagIsMoving == true && obj.SPS01{1,b(6)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});
                                                            UpdateStatus(obj.SPS01{1,b(4)});
                                                            UpdateStatus(obj.SPS01{1,b(5)});
                                                            UpdateStatus(obj.SPS01{1,b(6)});
                                                        end
                                                        if obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true || obj.SPS01{1,b(5)}.FlagIsDone == true || obj.SPS01{1,b(6)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving && obj.SPS01{1,c(4)}.FlagIsMoving && obj.SPS01{1,c(5)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                                            UpdateStatus(obj.SPS01{1,c(4)});
                                                                            UpdateStatus(obj.SPS01{1,c(5)});                                                                           
                                                                        end
                                                                        if obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true || obj.SPS01{1,c(4)}.FlagIsDone == true || obj.SPS01{1,c(5)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving && obj.SPS01{1,d(3)}.FlagIsMoving && obj.SPS01{1,d(4)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});
                                                                                            UpdateStatus(obj.SPS01{1,d(2)});
                                                                                            UpdateStatus(obj.SPS01{1,d(3)});
                                                                                            UpdateStatus(obj.SPS01{1,d(4)});
                                                                                        end
                                                                                        if obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone || obj.SPS01{1,d(3)}.FlagIsDone || obj.SPS01{1,d(4)}.FlagIsDone
                                                                                            for r=1:size(d,2)
                                                                                                if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                                    displaymovementstop(obj.SPS01{1,d(r)})
                                                                                                    e=d;
                                                                                                    e(r)=[];
                                                                                                    for count6=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                        if obj.Stop == true
                                                                                                            StopBoard(obj)
                                                                                                            break // counter 6
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsMoving && obj.SPS01{1,e(2)}.FlagIsMoving && obj.SPS01{1,e(3)}.FlagIsMoving 
                                                                                                            UpdateStatus(obj.SPS01{1,e(1)});
                                                                                                            UpdateStatus(obj.SPS01{1,e(2)});
                                                                                                            UpdateStatus(obj.SPS01{1,e(3)});
                                                                                                        end
                                                                                                        if obj.SPS01{1,e(1)}.FlagIsDone || obj.SPS01{1,e(2)}.FlagIsDone || obj.SPS01{1,e(3)}.FlagIsDone
                                                                                                            for s=1:size(e,2)
                                                                                                                if obj.SPS01{1,e(s)}.FlagIsDone == true
                                                                                                                    displaymovementstop(obj.SPS01{1,e(s)})
                                                                                                                    f=e;
                                                                                                                    f(s)=[];
                                                                                                                    for count7=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                                        if obj.Stop == true
                                                                                                                            StopBoard(obj)
                                                                                                                            break // counter 7
                                                                                                                        elseif obj.SPS01{1,f(1)}.FlagIsMoving && obj.SPS01{1,f(2)}.FlagIsMoving
                                                                                                                            UpdateStatus(obj.SPS01{1,f(1)});
                                                                                                                            UpdateStatus(obj.SPS01{1,f(2)});
                                                                                                                        end
                                                                                                                        if obj.SPS01{1,f(1)}.FlagIsDone || obj.SPS01{1,f(2)}.FlagIsDone 
                                                                                                                            for t=1:size(f,2)
                                                                                                                                if obj.SPS01{1,f(t)}.FlagIsDone
                                                                                                                                    displaymovementstop(obj.SPS01{1,f(t)})
                                                                                                                                    g=f;
                                                                                                                                    g(t)=[];
                                                                                                                                    for count8=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                                                        if obj.Stop == true
                                                                                                                                            StopBoard(obj)
                                                                                                                                            break // counter 8
                                                                                                                                        elseif obj.SPS01{1,g(1)}.FlagIsMoving
                                                                                                                                            UpdateStatus(obj.SPS01{1,g(1)});
                                                                                                                                        end
                                                                                                                                        if obj.SPS01{1,g(1)}.FlagIsDone 
                                                                                                                                            displaymovementstop(obj.SPS01{1,g(1)})
                                                                                                                                            break // counter 8
                                                                                                                                        end
                                                                                                                                        pause(scan_rate)
                                                                                                                                    end                                                                                                                                    
                                                                                                                                    break // t search of first device to be done
                                                                                                                                end
                                                                                                                            end
                                                                                                                            break //counter 7
                                                                                                                        end  
                                                                                                                        pause(scan_rate)
                                                                                                                    end                                                                                                                    
                                                                                                                    break // s search of first device to be done
                                                                                                                end
                                                                                                            end
                                                                                                            break // counter 6
                                                                                                        end
                                                                                                        pause(scan_rate)
                                                                                                    end  
                                                                                                    break // r search of first device to be done
                                                                                                end
                                                                                            end
                                                                                            break // counter 5
                                                                                        end
                                                                                        pause(scan_rate)
                                                                                    end
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break // counter 4
                                                                        end
                                                                        pause(scan_rate)
                                                                    end
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break //counter 3
                                                        end   
                                                        pause(scan_rate)
                                                    end  
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end      
                                        pause(scan_rate)
                                    end   
                                    break // j search of first device to be done
                                end
                            end
                            break //counter 1
                        end                        
                        pause(scan_rate)
                    end
                end
            end
        end
            

        //// Set Valves
        function SetValves(obj,d1,v11,v12,v13,v14,d2,v21,v22,v23,v24)
            if obj.Stop == false
                // if rem(nargin,2) == 1
                //     disp('Error, missing input. Number of inputs has to be even (interface, name of manifold and the four corresponding valve entries).');
                // else
                    if nargin == 6 // 1 manifold as input
                        i1=FindIndexM(obj,d1);
                        obj.listener_firstdoneM = addlistener(obj, 'FirstDoneStopM',@(src,evnt)obj.CheckFirstDoneStopM(src,evnt,i1)); //it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                        if ~isempty(i1)   
                            if obj.C4VM{1,i1}.FlagIsDone == true
                                obj.C4VM{1,i1}.device.CmdSetValves(int8(v11),int8(v12),int8(v13),int8(v14));                              
                                displayswitch(obj.C4VM{1,i1},v11,v12,v13,v14);
                                if obj.C4VM{1,i1}.FlagIsDone == false 
                                    notify(obj,'FirstDoneStopM');
                                end
                            end
                        end
                    elseif nargin == 11 // 2 manifolds as input
                        i1=FindIndexM(obj,d1);
                        i2=FindIndexM(obj,d2); 
                        obj.listener_firstdoneM = addlistener(obj, 'FirstDoneStopM',@(src,evnt)obj.CheckFirstDoneStopM(src,evnt,i1,i2)); //it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                        if ~isempty(i1) && ~isempty(i2)
                            if obj.C4VM{1,i1}.FlagIsDone == true && obj.C4VM{1,i2}.FlagIsDone == true
                                obj.C4VM{1,i1}.device.CmdSetValves(int8(v11),int8(v12),int8(v13),int8(v14));
                                obj.C4VM{1,i2}.device.CmdSetValves(int8(v21),int8(v22),int8(v23),int8(v24));
                                displayswitch(obj.C4VM{1,i1},v11,v12,v13,v14)
                                displayswitch(obj.C4VM{1,i2},v21,v22,v23,v24)  
                                if obj.C4VM{1,i1}.FlagIsDone == false && obj.C4VM{1,i2}.FlagIsDone == false
                                    notify(obj,'FirstDoneStopM');
                                end
                            end
                        end                        
                    end
//                 end
            end
        end
           
        function CheckFirstDoneStopM(obj,varargin)
            if nargin == 4 // only one manifold in motion (=numb input + obj + 2more input (source and event))  
                i1=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                if obj.C4VM{1,i1}.FlagIsDone == false  
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break
                        elseif obj.C4VM{1,i1}.FlagIsDone == false
                            UpdateStatus(obj.C4VM{1,i1});
                        end
                        if obj.C4VM{1,i1}.FlagIsDone == true
                            displayswitchstop(obj.C4VM{1,i1})
                            break
                        end
                        pause(scan_rate)
                    end
                end
            elseif nargin == 5 // only two manifolds
                i1=varargin{3}; 
                i2=varargin{4};
                i=[i1 i2]; 
                if obj.C4VM{1,i1}.FlagIsDone == false && obj.C4VM{1,i2}.FlagIsDone == false 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours        
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.C4VM{1,i1}.FlagIsDone == false && obj.C4VM{1,i2}.FlagIsDone == false
                            UpdateStatus(obj.C4VM{1,i1});
                            UpdateStatus(obj.C4VM{1,i2});
                        end
                        if obj.C4VM{1,i1}.FlagIsDone == true || obj.C4VM{1,i2}.FlagIsDone == true
                            for j=1:size(i,2) //search for first device to be done
                                if obj.C4VM{1,i(j)}.FlagIsDone == true
                                    displayswitchstop(obj.C4VM{1,i(j)})
                                    a=i;
                                    a(j)=[];
                                    for count2=1:target
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break //counter 2
                                        elseif obj.C4VM{1,a(1)}.FlagIsDone == false
                                            UpdateStatus(obj.C4VM{1,a(1)});
                                        end
                                        if obj.C4VM{1,a(1)}.FlagIsDone == true
                                            displayswitchstop(obj.C4VM{1,a(1)})
                                            break //counter 2
                                        end                                            
                                        pause(scan_rate)
                                    end                                            
                                    break // j search of first device to be done 
                                end                                                                       
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end
            end
        end
        
       
        //// Pause : same as stop but with different comment
        function PauseBoard (obj)
            for i=1:size(obj.SPS01,2)
                obj.SPS01{1,i}.device.CmdStop();
                obj.SPS01{1,i}.FlagReady = true;
//                 UpdateStatus(obj.SPS01{1,i}); // i update the status in the listener function CheckFirstDoneStopPause before i recall the MulMove3 in the pause               
            end
            for i=1:size(obj.C4VM,2)
                obj.C4VM{1,i}.device.CmdStop();
                UpdateStatus(obj.C4VM{1,i});
            end
            obj.ClockStop = clock;
            comment=[num2str(obj.ClockStop(4)) , ':' , num2str(obj.ClockStop(5)) ,':' ,num2str(obj.ClockStop(6)), ' Interface paused by the user.']; 
            diary on
            disp(comment);
            diary off
        end
        
        //// Listener Function : Display the first device to be done and Stop and Pause (called in MulMove3)
        function CheckFirstDoneStopPause(obj,varargin)
            if nargin == 6 // only one syringe in motion (=numb input + obj + 2more input (source and event))   
                i1=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                d1=varargin{4};
                v1=varargin{5};
                if obj.SPS01{1,i1}.FlagIsMoving == true  
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            com=StopBoard(obj);
                            break //counter1
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true                                                              
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off 
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    MulMove3(obj,d1,v1);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1
                        elseif obj.SPS01{1,i1}.FlagIsDone == true 
                            displaymovementstop(obj.SPS01{1,i1})
                            break //counter1
                        end
                        pause(scan_rate)
                    end
                end
            elseif nargin == 9 // 2 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i=[i1 i2];
                d={d1 d2};
                v=[v1 v2];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours        
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1                        
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true
                            for j=1:size(i,2) //search for first device to be done
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[];
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:target
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break //counter 2
                                        elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(1)})
                                            break //counter 2
                                        end                                            
                                        pause(scan_rate)
                                    end                                            
                                    break // j search of first device to be done 
                                end                                                                       
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end                
                
            elseif nargin == 12 // 3 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i3=varargin{9};
                d3=varargin{10};
                v3=varargin{11};
                i=[i1 i2 i3];
                d={d1 d2 d3};
                v=[v1 v2 v3];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1                            
                         elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2,d3,v3);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true 
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; // a=[i2 i3] for j=1, a=[i1 i3] for j=2, a=[i1 i2] for j=3
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:target
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2                                            
                                         elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1),ad{2},av(2));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end                                              
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true
                                            for k=1:size(a,2)
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:target
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break //counter 3                                                            
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    MulMove3(obj,bd{1},bv(1));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end                                                            
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true
                                                            displaymovementstop(obj.SPS01{1,b(1)})
                                                            break //counter 3
                                                        end
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done 
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done 
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end
            elseif nargin == 15 // 4 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i3=varargin{9};
                d3=varargin{10};
                v3=varargin{11};
                i4=varargin{12};
                d4=varargin{13};
                v4=varargin{14};
                i=[i1 i2 i3 i4];
                d={d1 d2 d3 d4};
                v=[v1 v2 v3 v4];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i4}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2,d3,v3,d4,v4);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end                           
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4}); 
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    scan_rate=0.1; //the scan rate of the counter
                                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours          
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                        elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////                                                    
                                                    UpdateStatus(obj.SPS01{1,a(3)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1),ad{2},av(2),ad{3},av(3));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end                                            
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});    
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    scan_rate=0.1; //the scan rate of the counter
                                                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours 
                                                    for count3=1:target
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(2)}) ////////////////////////////
                                                                    MulMove3(obj,bd{1},bv(1),bd{2},bv(2));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end    
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    cd=bd;
                                                                    cd(p)=[];
                                                                    cv=bv;
                                                                    cv(p)=[];
                                                                    for count4=1:target
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.Pause == true
                                                                            PauseBoard(obj)
                                                                            for count_pause1=1:target
                                                                                if obj.Stop == true
                                                                                    break //count_pause1
                                                                                elseif obj.Resume == true
                                                                                    obj.ClockResume = clock;
                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                    diary on
                                                                                    disp(comment);
                                                                                    diary off 
                                                                                    UpdateStatus(obj.SPS01{1,c(1)}) ////////////////////////////
                                                                                    MulMove3(obj,cd{1},cv(1));                                    
                                                                                    obj.flag_break_countpause = 1;
                                                                                    break //count_pause1
                                                                                end
                                                                                pause(scan_rate)
                                                                            end  
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                        end
                                                                        if obj.flag_break_countpause == 1
                                                                            break //counter1
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsDone == true
                                                                            displaymovementstop(obj.SPS01{1,c(1)})
                                                                            break // counter 4
                                                                        end
                                                                        pause(scan_rate)
                                                                    end
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break //counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break //counter 2
                                        end
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end 
                
            elseif nargin == 18 // 5 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i3=varargin{9};
                d3=varargin{10};
                v3=varargin{11};
                i4=varargin{12};
                d4=varargin{13};
                v4=varargin{14};
                i5=varargin{15};
                d5=varargin{16};
                v5=varargin{17};
                i=[i1 i2 i3 i4 i5]; 
                d={d1 d2 d3 d4 d5};
                v=[v1 v2 v3 v4 v5];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i4}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i5}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end   
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});                            
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2
                                       elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////                                                    
                                                    UpdateStatus(obj.SPS01{1,a(3)}) ////////////////////////////                                                   
                                                    UpdateStatus(obj.SPS01{1,a(4)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1),ad{2},av(2),ad{3},av(3),ad{4},av(4));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end    
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});                                            
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(2)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(3)}) ////////////////////////////
                                                                    MulMove3(obj,bd{1},bv(1),bd{2},bv(2),bd{3},bv(3));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end   
                                                       elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});                                                            
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    cd=bd;
                                                                    cd(p)=[];
                                                                    cv=bv;
                                                                    cv(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4
                                                                        elseif obj.Pause == true
                                                                            PauseBoard(obj)
                                                                            for count_pause1=1:target
                                                                                if obj.Stop == true
                                                                                    break //count_pause1
                                                                                elseif obj.Resume == true
                                                                                    obj.ClockResume = clock;
                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                    diary on
                                                                                    disp(comment);
                                                                                    diary off 
                                                                                    UpdateStatus(obj.SPS01{1,c(1)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(2)}) ////////////////////////////
                                                                                    MulMove3(obj,cd{1},cv(1),cd{2},cv(2));                                    
                                                                                    obj.flag_break_countpause = 1;
                                                                                    break //count_pause1
                                                                                end
                                                                                pause(scan_rate)
                                                                            end    
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});                                                                            
                                                                        end
                                                                        if obj.flag_break_countpause == 1
                                                                            break //counter1
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    dd=cd;
                                                                                    dd(q)=[];
                                                                                    dv=cv;
                                                                                    dv(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5                                                                                            
                                                                                        elseif obj.Pause == true
                                                                                            PauseBoard(obj)
                                                                                            for count_pause1=1:target
                                                                                                if obj.Stop == true
                                                                                                    break //count_pause1
                                                                                                elseif obj.Resume == true
                                                                                                    obj.ClockResume = clock;
                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                    diary on
                                                                                                    disp(comment);
                                                                                                    diary off 
                                                                                                    UpdateStatus(obj.SPS01{1,d(1)}) ////////////////////////////
                                                                                                    MulMove3(obj,dd{1},dv(1));                                    
                                                                                                    obj.flag_break_countpause = 1;
                                                                                                    break //count_pause1
                                                                                                end
                                                                                                pause(scan_rate)
                                                                                            end    
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});                                                                                            
                                                                                        end
                                                                                        if obj.flag_break_countpause == 1
                                                                                            break //counter1
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsDone
                                                                                            displaymovementstop(obj.SPS01{1,d(1)})
                                                                                            break //counter 5
                                                                                        end
                                                                                        pause(scan_rate)
                                                                                    end                                                                                    
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break // counter 4
                                                                        end                                                                        
                                                                        pause(scan_rate)
                                                                    end                                                                    
                                                                    break // p search of first device to be done
                                                                end
                                                            end 
                                                            break // counter 3
                                                        end
                                                        pause(scan_rate)
                                                    end
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end                        
                        pause(scan_rate)
                    end
                end       
                
                
            elseif nargin == 21 // 6 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i3=varargin{9};
                d3=varargin{10};
                v3=varargin{11};
                i4=varargin{12};
                d4=varargin{13};
                v4=varargin{14};
                i5=varargin{15};
                d5=varargin{16};
                v5=varargin{17};
                i6=varargin{18};
                d6=varargin{19};
                v6=varargin{20};
                i=[i1 i2 i3 i4 i5 i6]; 
                d={d1 d2 d3 d4 d5 d6};
                v=[v1 v2 v3 v4 v5 v6];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1                            
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i4}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i5}) ////////////////////////////                                    
                                    UpdateStatus(obj.SPS01{1,i6}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end  
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});
                            UpdateStatus(obj.SPS01{1,i6});                            
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2                                            
                                        elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////                                                    
                                                    UpdateStatus(obj.SPS01{1,a(3)}) ////////////////////////////                                                   
                                                    UpdateStatus(obj.SPS01{1,a(4)}) ////////////////////////////                                                  
                                                    UpdateStatus(obj.SPS01{1,a(5)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1),ad{2},av(2),ad{3},av(3),ad{4},av(4),ad{5},av(5));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end    
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});
                                            UpdateStatus(obj.SPS01{1,a(5)});                                            
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3                                                            
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(2)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(3)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(4)}) ////////////////////////////
                                                                    MulMove3(obj,bd{1},bv(1),bd{2},bv(2),bd{3},bv(3),bd{4},bv(4));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end    
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});
                                                            UpdateStatus(obj.SPS01{1,b(4)});                                                            
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    cd=bd;
                                                                    cd(p)=[];
                                                                    cv=bv;
                                                                    cv(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4                                                                            
                                                                        elseif obj.Pause == true
                                                                            PauseBoard(obj)
                                                                            for count_pause1=1:target
                                                                                if obj.Stop == true
                                                                                    break //count_pause1
                                                                                elseif obj.Resume == true
                                                                                    obj.ClockResume = clock;
                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                    diary on
                                                                                    disp(comment);
                                                                                    diary off 
                                                                                    UpdateStatus(obj.SPS01{1,c(1)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(2)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(3)}) ////////////////////////////
                                                                                    MulMove3(obj,cd{1},cv(1),cd{2},cv(2),cd{3},cv(3));                                    
                                                                                    obj.flag_break_countpause = 1;
                                                                                    break //count_pause1
                                                                                end
                                                                                pause(scan_rate)
                                                                            end   
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                                            UpdateStatus(obj.SPS01{1,c(3)});                                                                            
                                                                        end
                                                                        if obj.flag_break_countpause == 1
                                                                            break //counter1
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    dd=cd;
                                                                                    dd(q)=[];
                                                                                    dv=cv;
                                                                                    dv(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5                                                                                            
                                                                                        elseif obj.Pause == true
                                                                                            PauseBoard(obj)
                                                                                            for count_pause1=1:target
                                                                                                if obj.Stop == true
                                                                                                    break //count_pause1
                                                                                                elseif obj.Resume == true
                                                                                                    obj.ClockResume = clock;
                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                    diary on
                                                                                                    disp(comment);
                                                                                                    diary off 
                                                                                                    UpdateStatus(obj.SPS01{1,d(1)}) ////////////////////////////
                                                                                                    UpdateStatus(obj.SPS01{1,d(2)}) ////////////////////////////
                                                                                                    MulMove3(obj,dd{1},dv(1),dd{2},dv(2));                                    
                                                                                                    obj.flag_break_countpause = 1;
                                                                                                    break //count_pause1
                                                                                                end
                                                                                                pause(scan_rate)
                                                                                            end    
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});
                                                                                            UpdateStatus(obj.SPS01{1,d(2)});                                                                                            
                                                                                        end
                                                                                        if obj.flag_break_countpause == 1
                                                                                            break //counter1
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone
                                                                                            for r=1:size(d,2)
                                                                                                if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                                    displaymovementstop(obj.SPS01{1,d(r)})
                                                                                                    e=d;
                                                                                                    e(r)=[];
                                                                                                    ed=dd;
                                                                                                    ed(r)=[];
                                                                                                    ev=dv;
                                                                                                    ev(r)=[];
                                                                                                    for count6=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                        if obj.Stop == true
                                                                                                            StopBoard(obj)
                                                                                                            break // counter 6                                                                                                            
                                                                                                        elseif obj.Pause == true
                                                                                                            PauseBoard(obj)
                                                                                                            for count_pause1=1:target
                                                                                                                if obj.Stop == true
                                                                                                                    break //count_pause1
                                                                                                                elseif obj.Resume == true
                                                                                                                    obj.ClockResume = clock;
                                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                                    diary on
                                                                                                                    disp(comment);
                                                                                                                    diary off 
                                                                                                                    UpdateStatus(obj.SPS01{1,e(1)}) ////////////////////////////
                                                                                                                    MulMove3(obj,ed{1},ev(1));                                    
                                                                                                                    obj.flag_break_countpause = 1;
                                                                                                                    break //count_pause1
                                                                                                                end
                                                                                                                pause(scan_rate)
                                                                                                            end   
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsMoving
                                                                                                            UpdateStatus(obj.SPS01{1,e(1)});                                                                                                            
                                                                                                        end
                                                                                                        if obj.flag_break_countpause == 1
                                                                                                            break //counter1
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsDone
                                                                                                            displaymovementstop(obj.SPS01{1,e(1)})
                                                                                                            break // counter 6
                                                                                                        end                                                                                                        
                                                                                                        pause(scan_rate)
                                                                                                    end                                                                                                    
                                                                                                    break // r search of first device to be done
                                                                                                end
                                                                                            end
                                                                                            break // counter 5
                                                                                        end
                                                                                        pause(scan_rate)
                                                                                    end 
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break //counter 4
                                                                        end                                                                        
                                                                        pause(scan_rate)
                                                                    end 
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break // Counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end                                                    
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(scan_rate)
                    end
                end    
                
            
            elseif nargin == 24 //7 syringes
                i1=varargin{3}; 
                d1=varargin{4};
                v1=varargin{5};
                i2=varargin{6};
                d2=varargin{7};
                v2=varargin{8};
                i3=varargin{9};
                d3=varargin{10};
                v3=varargin{11};
                i4=varargin{12};
                d4=varargin{13};
                v4=varargin{14};
                i5=varargin{15};
                d5=varargin{16};
                v5=varargin{17};
                i6=varargin{18};
                d6=varargin{19};
                v6=varargin{20};
                i7=varargin{21};
                d7=varargin{22};
                v7=varargin{23};
                i=[i1 i2 i3 i4 i5 i6 i7]; 
                d={d1 d2 d3 d4 d5 d6 d7};
                v=[v1 v2 v3 v4 v5 v6 v7];
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break // counter 1                            
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i4}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i5}) ////////////////////////////                                    
                                    UpdateStatus(obj.SPS01{1,i6}) ////////////////////////////                                  
                                    UpdateStatus(obj.SPS01{1,i7}) ////////////////////////////
                                    MulMove3(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7);                                    
                                    obj.flag_break_countpause = 1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end    
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4});
                            UpdateStatus(obj.SPS01{1,i5});
                            UpdateStatus(obj.SPS01{1,i6});
                            UpdateStatus(obj.SPS01{1,i7});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true || obj.SPS01{1,i5}.FlagIsDone == true || obj.SPS01{1,i6}.FlagIsDone == true || obj.SPS01{1,i7}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    a=i;
                                    a(j)=[]; 
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:target //this is a counter clock to check if the stop_status variable has changed
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            break // counter 2                                            
                                        elseif obj.Pause == true
                                            PauseBoard(obj)
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off  
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////                                                    
                                                    UpdateStatus(obj.SPS01{1,a(3)}) ////////////////////////////                                                   
                                                    UpdateStatus(obj.SPS01{1,a(4)}) ////////////////////////////                                                  
                                                    UpdateStatus(obj.SPS01{1,a(5)}) ////////////////////////////                                                 
                                                    UpdateStatus(obj.SPS01{1,a(6)}) ////////////////////////////
                                                    MulMove3(obj,ad{1},av(1),ad{2},av(2),ad{3},av(3),ad{4},av(4),ad{5},av(5),ad{6},av(6));                                    
                                                    obj.flag_break_countpause = 1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end
                                       elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true && obj.SPS01{1,a(4)}.FlagIsMoving == true && obj.SPS01{1,a(5)}.FlagIsMoving == true && obj.SPS01{1,a(6)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});
                                            UpdateStatus(obj.SPS01{1,a(4)});
                                            UpdateStatus(obj.SPS01{1,a(5)});
                                            UpdateStatus(obj.SPS01{1,a(6)});
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true || obj.SPS01{1,a(4)}.FlagIsDone == true || obj.SPS01{1,a(5)}.FlagIsDone == true || obj.SPS01{1,a(6)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:target //this is a counter clock to check if the stop_status variable has changed
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            break // counter 3                                                            
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(2)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(3)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(4)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(5)}) ////////////////////////////
                                                                    MulMove3(obj,bd{1},bv(1),bd{2},bv(2),bd{3},bv(3),bd{4},bv(4),bd{5},bv(5));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end    
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true && obj.SPS01{1,b(3)}.FlagIsMoving == true && obj.SPS01{1,b(4)}.FlagIsMoving == true && obj.SPS01{1,b(5)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                            UpdateStatus(obj.SPS01{1,b(3)});
                                                            UpdateStatus(obj.SPS01{1,b(4)});
                                                            UpdateStatus(obj.SPS01{1,b(5)});
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true || obj.SPS01{1,b(3)}.FlagIsDone == true || obj.SPS01{1,b(4)}.FlagIsDone == true || obj.SPS01{1,b(5)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    c=b;
                                                                    c(p)=[];
                                                                    cd=bd;
                                                                    cd(p)=[];
                                                                    cv=bv;
                                                                    cv(p)=[];
                                                                    for count4=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            break // counter 4                                                                            
                                                                        elseif obj.Pause == true
                                                                            PauseBoard(obj)
                                                                            for count_pause1=1:target
                                                                                if obj.Stop == true
                                                                                    break //count_pause1
                                                                                elseif obj.Resume == true
                                                                                    obj.ClockResume = clock;
                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                    diary on
                                                                                    disp(comment);
                                                                                    diary off 
                                                                                    UpdateStatus(obj.SPS01{1,c(1)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(2)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(3)}) ////////////////////////////
                                                                                    UpdateStatus(obj.SPS01{1,c(4)}) ////////////////////////////
                                                                                    MulMove3(obj,cd{1},cv(1),cd{2},cv(2),cd{3},cv(3),cd{4},cv(4));                                    
                                                                                    obj.flag_break_countpause = 1;
                                                                                    break //count_pause1
                                                                                end
                                                                                pause(scan_rate)
                                                                            end    
                                                                         elseif obj.SPS01{1,c(1)}.FlagIsMoving == true && obj.SPS01{1,c(2)}.FlagIsMoving && obj.SPS01{1,c(3)}.FlagIsMoving && obj.SPS01{1,c(4)}.FlagIsMoving
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                            UpdateStatus(obj.SPS01{1,c(2)});
                                                                            UpdateStatus(obj.SPS01{1,c(3)});
                                                                            UpdateStatus(obj.SPS01{1,c(4)});
                                                                        end
                                                                        if obj.flag_break_countpause == 1
                                                                            break //counter1
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsDone == true || obj.SPS01{1,c(2)}.FlagIsDone == true || obj.SPS01{1,c(3)}.FlagIsDone == true || obj.SPS01{1,c(4)}.FlagIsDone == true
                                                                            for q=1:size(c,2)
                                                                                if obj.SPS01{1,c(q)}.FlagIsDone == true
                                                                                    displaymovementstop(obj.SPS01{1,c(q)})
                                                                                    d=c;
                                                                                    d(q)=[];
                                                                                    dd=cd;
                                                                                    dd(q)=[];
                                                                                    dv=cv;
                                                                                    dv(q)=[];
                                                                                    for count5=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                        if obj.Stop == true
                                                                                            StopBoard(obj)
                                                                                            break // counter 5                                                                                            
                                                                                        elseif obj.Pause == true
                                                                                            PauseBoard(obj)
                                                                                            for count_pause1=1:target
                                                                                                if obj.Stop == true
                                                                                                    break //count_pause1
                                                                                                elseif obj.Resume == true
                                                                                                    obj.ClockResume = clock;
                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                    diary on
                                                                                                    disp(comment);
                                                                                                    diary off 
                                                                                                    UpdateStatus(obj.SPS01{1,d(1)}) ////////////////////////////
                                                                                                    UpdateStatus(obj.SPS01{1,d(2)}) ////////////////////////////
                                                                                                    UpdateStatus(obj.SPS01{1,d(3)}) ////////////////////////////
                                                                                                    MulMove3(obj,dd{1},dv(1),dd{2},dv(2),dd{3},dv(3));                                    
                                                                                                    obj.flag_break_countpause = 1;
                                                                                                    break //count_pause1
                                                                                                end
                                                                                                pause(scan_rate)
                                                                                            end    
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsMoving && obj.SPS01{1,d(2)}.FlagIsMoving && obj.SPS01{1,d(3)}.FlagIsMoving
                                                                                            UpdateStatus(obj.SPS01{1,d(1)});
                                                                                            UpdateStatus(obj.SPS01{1,d(2)});
                                                                                            UpdateStatus(obj.SPS01{1,d(3)});
                                                                                        end
                                                                                        if obj.flag_break_countpause == 1
                                                                                            break //counter1
                                                                                        elseif obj.SPS01{1,d(1)}.FlagIsDone || obj.SPS01{1,d(2)}.FlagIsDone || obj.SPS01{1,d(3)}.FlagIsDone
                                                                                            for r=1:size(d,2)
                                                                                                if obj.SPS01{1,d(r)}.FlagIsDone == true
                                                                                                    displaymovementstop(obj.SPS01{1,d(r)})
                                                                                                    e=d;
                                                                                                    e(r)=[];
                                                                                                    ed=dd;
                                                                                                    ed(r)=[];
                                                                                                    ev=dv;
                                                                                                    ev(r)=[];
                                                                                                    for count6=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                        if obj.Stop == true
                                                                                                            StopBoard(obj)
                                                                                                            break // counter 6                                                                                                            
                                                                                                        elseif obj.Pause == true
                                                                                                            PauseBoard(obj)
                                                                                                            for count_pause1=1:target
                                                                                                                if obj.Stop == true
                                                                                                                    break //count_pause1
                                                                                                                elseif obj.Resume == true
                                                                                                                    obj.ClockResume = clock;
                                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                                    diary on
                                                                                                                    disp(comment);
                                                                                                                    diary off 
                                                                                                                    UpdateStatus(obj.SPS01{1,e(1)}) ////////////////////////////                                                                                                                    
                                                                                                                    UpdateStatus(obj.SPS01{1,e(2)}) ////////////////////////////
                                                                                                                    MulMove3(obj,ed{1},ev(1),ed{2},ev(2));                                    
                                                                                                                    obj.flag_break_countpause = 1;
                                                                                                                    break //count_pause1
                                                                                                                end
                                                                                                                pause(scan_rate)
                                                                                                            end    
                                                                                                            
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsMoving && obj.SPS01{1,e(2)}.FlagIsMoving 
                                                                                                            UpdateStatus(obj.SPS01{1,e(1)});
                                                                                                            UpdateStatus(obj.SPS01{1,e(2)});
                                                                                                        end
                                                                                                        if obj.flag_break_countpause == 1
                                                                                                            break //counter1
                                                                                                        elseif obj.SPS01{1,e(1)}.FlagIsDone || obj.SPS01{1,e(2)}.FlagIsDone
                                                                                                            for s=1:size(e,2)
                                                                                                                if obj.SPS01{1,e(s)}.FlagIsDone == true
                                                                                                                    displaymovementstop(obj.SPS01{1,e(s)})
                                                                                                                    f=e;
                                                                                                                    f(s)=[];
                                                                                                                    fd=ed;
                                                                                                                    fd(s)=[];
                                                                                                                    fv=ev;
                                                                                                                    fv(s)=[];
                                                                                                                    for count7=1:target //this is a counter clock to check if the stop_status variable has changed
                                                                                                                        if obj.Stop == true
                                                                                                                            StopBoard(obj)
                                                                                                                            break // counter 7                                                                                                                            
                                                                                                                        elseif obj.Pause == true
                                                                                                                            PauseBoard(obj)
                                                                                                                            for count_pause1=1:target
                                                                                                                                if obj.Stop == true
                                                                                                                                    break //count_pause1
                                                                                                                                elseif obj.Resume == true
                                                                                                                                    obj.ClockResume = clock;
                                                                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                                                                    diary on
                                                                                                                                    disp(comment);
                                                                                                                                    diary off 
                                                                                                                                    UpdateStatus(obj.SPS01{1,f(1)}) ////////////////////////////
                                                                                                                                    MulMove3(obj,fd{1},fv(1));                                    
                                                                                                                                    obj.flag_break_countpause = 1;
                                                                                                                                    break //count_pause1
                                                                                                                                end
                                                                                                                                pause(scan_rate)
                                                                                                                            end
                                                                                                                        elseif obj.SPS01{1,f(1)}.FlagIsMoving
                                                                                                                            UpdateStatus(obj.SPS01{1,f(1)});
                                                                                                                        end
                                                                                                                        if obj.flag_break_countpause == 1
                                                                                                                        break //counter1
                                                                                                                    elseif obj.SPS01{1,f(1)}.FlagIsDone 
                                                                                                                            displaymovementstop(obj.SPS01{1,f(1)})
                                                                                                                            break // counter 7
                                                                                                                        end
                                                                                                                        pause(scan_rate)
                                                                                                                    end  
                                                                                                                    break // s search of first device to be done
                                                                                                                end
                                                                                                            end
                                                                                                            break // counter 6
                                                                                                        end  
                                                                                                        pause(scan_rate)
                                                                                                    end    
                                                                                                    break // r search of first device to be done
                                                                                                end
                                                                                            end
                                                                                            break // counter 5
                                                                                        end  
                                                                                        pause(scan_rate)
                                                                                    end  
                                                                                    break // q search of first device to be done
                                                                                end
                                                                            end
                                                                            break // counter 4
                                                                        end      
                                                                        pause(scan_rate)
                                                                    end    
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break // counter 3
                                                        end                                                        
                                                        pause(scan_rate)
                                                    end  
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break // counter 2
                                        end                                        
                                        pause(scan_rate)
                                    end  
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end                        
                        pause(scan_rate)
                    end
                end    
                
                
                
            end
        end
        
        //// Multiple Movement with stop (at the same time. It allows the stop and pause)
        function MulMove3(obj,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7,d8,v8)
            obj.flag_break_countpause = 0;
            if obj.Stop == false
                if rem(nargin,2) == 0
                    comment='Error, missing input. Number of inputs has to be odd (interface, name of syringes and corresponding flow rates).';
                    diary on
                    disp(comment);
                    diary off
                else
                    if nargin == 3 // 1 syringe as input
                        i1=FindIndexS(obj,d1);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                        if ~isempty(i1)                        
                            if obj.SPS01{1,i1}.FlagIsDone == true 
                               obj.SPS01{1,i1}.device.CmdMoveToVolume(v1); 
                               obj.SPS01{1,i1}.FlagReady = false;
                               displaymovement(obj.SPS01{1,i1})
                               if obj.SPS01{1,i1}.FlagIsMoving == true 
                                    notify(obj,'FirstDoneStopPause');
                               end
                            end
                        end
                    elseif nargin == 5 // 2 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2); 
                        obj.listener_firstdonepause = addf(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2)
                            if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2})  
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStopPause');
                                end
                            end
                        end                                                
                    elseif nargin == 7 // 3 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2,i3,d3,v3)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3)
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            obj.SPS01{1,i3}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2}) 
                            displaymovement(obj.SPS01{1,i3})
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                                notify(obj,'FirstDoneStopPause');
                            end
                        end
                        
                    elseif nargin == 9 // 4 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        i4=FindIndexS(obj,d4);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4)
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                            obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            obj.SPS01{1,i3}.FlagReady = false;
                            obj.SPS01{1,i4}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2}) 
                            displaymovement(obj.SPS01{1,i3})
                            displaymovement(obj.SPS01{1,i4})
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                                notify(obj,'FirstDoneStopPause');
                            end
                        end
                        
                    elseif nargin == 11 // 5 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        i4=FindIndexS(obj,d4);
                        i5=FindIndexS(obj,d5);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5)
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                            obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                            obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            obj.SPS01{1,i3}.FlagReady = false;
                            obj.SPS01{1,i4}.FlagReady = false;
                            obj.SPS01{1,i5}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2}) 
                            displaymovement(obj.SPS01{1,i3})
                            displaymovement(obj.SPS01{1,i4})
                            displaymovement(obj.SPS01{1,i5})
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true
                                notify(obj,'FirstDoneStopPause');
                            end
                        end                       
                        
                    elseif nargin == 13 // 6 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        i4=FindIndexS(obj,d4);
                        i5=FindIndexS(obj,d5);
                        i6=FindIndexS(obj,d6);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5,i6,d6,v6)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6)
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                            obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                            obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                            obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            obj.SPS01{1,i3}.FlagReady = false;
                            obj.SPS01{1,i4}.FlagReady = false;
                            obj.SPS01{1,i5}.FlagReady = false;
                            obj.SPS01{1,i6}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2}) 
                            displaymovement(obj.SPS01{1,i3})
                            displaymovement(obj.SPS01{1,i4})
                            displaymovement(obj.SPS01{1,i5})
                            displaymovement(obj.SPS01{1,i6})
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true
                                notify(obj,'FirstDoneStopPause');
                            end
                        end    
                        
                    elseif nargin == 15 // 7 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        i4=FindIndexS(obj,d4);
                        i5=FindIndexS(obj,d5);
                        i6=FindIndexS(obj,d6);
                        i7=FindIndexS(obj,d7);
                        obj.listener_firstdonepause = addlistener(obj, 'FirstDoneStopPause',@(src,evnt)obj.CheckFirstDoneStopPause(src,evnt,i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,i5,d5,v5,i6,d6,v6,i7,d7,v7)); //it listens for the syringes FlagIsMoving == true, so it updtades continuously the states to determine the end of the commands. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4) && ~isempty(i5) && ~isempty(i6) && ~isempty(i7)
                            obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                            obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                            obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                            obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                            obj.SPS01{1,i5}.device.CmdMoveToVolume(v5);
                            obj.SPS01{1,i6}.device.CmdMoveToVolume(v6);
                            obj.SPS01{1,i7}.device.CmdMoveToVolume(v7);
                            obj.SPS01{1,i1}.FlagReady = false;
                            obj.SPS01{1,i2}.FlagReady = false;
                            obj.SPS01{1,i3}.FlagReady = false;
                            obj.SPS01{1,i4}.FlagReady = false;
                            obj.SPS01{1,i5}.FlagReady = false;
                            obj.SPS01{1,i6}.FlagReady = false;
                            obj.SPS01{1,i7}.FlagReady = false;
                            displaymovement(obj.SPS01{1,i1})
                            displaymovement(obj.SPS01{1,i2}) 
                            displaymovement(obj.SPS01{1,i3})
                            displaymovement(obj.SPS01{1,i4})
                            displaymovement(obj.SPS01{1,i5})
                            displaymovement(obj.SPS01{1,i6})
                            displaymovement(obj.SPS01{1,i7})
                            if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true && obj.SPS01{1,i5}.FlagIsMoving == true && obj.SPS01{1,i6}.FlagIsMoving == true && obj.SPS01{1,i7}.FlagIsMoving == true
                                notify(obj,'FirstDoneStopPause');
                            end
                        end 
                        
                    end
                end
            end
        end
        
        //// Display movement stopwait
       function displaymovementstopwait(obj,t)
           obj.ClockStop = clock;
           comment=[num2str(obj.ClockStop(4)) , ':' , num2str(obj.ClockStop(5)) ,':' ,num2str(obj.ClockStop(6)), ' Step done after waiting for ' , num2str(t), ' seconds.'];
           diary on
           disp(comment);
           diary off
       end 
        
        
        //// WaitStopBoard
        function WaitStopBoard (obj)
            for i=1:size(obj.SPS01,2)
                obj.SPS01{1,i}.device.CmdStop();
                obj.SPS01{1,i}.FlagReady = true;             
            end
            for i=1:size(obj.C4VM,2)
                obj.C4VM{1,i}.device.CmdStop();
                UpdateStatus(obj.C4VM{1,i});
            end

        end
        //// Update
        function UpdateBoard (obj)
            for i=1:size(obj.SPS01,2)
                obj.SPS01{1,i}.FlagReady = true;
                UpdateStatus(obj.SPS01{1,i});
            end
            for i=1:size(obj.C4VM,2)
                UpdateStatus(obj.C4VM{1,i});
            end
        end 
        
        
        //// Wait Movement

        function MoveWait(obj,time,d1,v1,d2,v2,d3,v3,d4,v4,d5,v5,d6,v6,d7,v7,d8,v8)
            t_s=tic;
            obj.flag_break_countpause = 0;
            obj.flag_break_stop = 0;
            if obj.Stop == false
                if rem(nargin,2) == 1
                    comment='Error, missing input. Number of inputs has to be odd (interface, time, name of syringes and corresponding flow rates).';
                    diary on
                    disp(comment);
                    diary off
                else
                    if nargin == 4 // 1 syringe as input
                        i1=FindIndexS(obj,d1);
                        obj.listener_firstdonepausewait = addlistener(obj, 'FirstDoneStopPauseWait',@(src,evnt)obj.CheckFirstDoneStopPauseWait(src,evnt,time,i1,d1,v1,t_s)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                        if ~isempty(i1)  
                            if obj.SPS01{1,i1}.FlagIsDone == true 
                               obj.SPS01{1,i1}.device.CmdMoveToVolume(v1); 
                               obj.SPS01{1,i1}.FlagReady = false;
                               displaymovement(obj.SPS01{1,i1})                              
                               if obj.SPS01{1,i1}.FlagIsMoving == true
                                   notify(obj,'FirstDoneStopPauseWait');
                               end                                   
                            end
                        end
                    elseif nargin == 6 // 2 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        obj.listener_firstdonepausewait = addlistener(obj, 'FirstDoneStopPauseWait',@(src,evnt)obj.CheckFirstDoneStopPauseWait(src,evnt,time,i1,d1,v1,i2,d2,v2,t_s)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2)
                            if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2})  
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStopPauseWait');
                                end                                
                            end          
                        end
                    elseif nargin == 8 // 3 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        obj.listener_firstdonepausewait = addlistener(obj, 'FirstDoneStopPauseWait',@(src,evnt)obj.CheckFirstDoneStopPauseWait(src,evnt,time,i1,d1,v1,i2,d2,v2,i3,d3,v3,t_s)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3)
                            if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true && obj.SPS01{1,i3}.FlagIsDone == true
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2})
                                displaymovement(obj.SPS01{1,i3})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStopPauseWait');
                                end                                
                            end          
                        end
                    elseif nargin == 10 // 4 syringes as input
                        i1=FindIndexS(obj,d1);
                        i2=FindIndexS(obj,d2);
                        i3=FindIndexS(obj,d3);
                        i4=FindIndexS(obj,d4);
                        obj.listener_firstdonepausewait = addlistener(obj, 'FirstDoneStopPauseWait',@(src,evnt)obj.CheckFirstDoneStopPauseWait(src,evnt,time,i1,d1,v1,i2,d2,v2,i3,d3,v3,i4,d4,v4,t_s)); //it listens for the syringe FlagIsMoving == true, so it updtades continuously the state to determine the end of the command. It results in FlagReady = true again.
                        if ~isempty(i1) && ~isempty(i2) && ~isempty(i3) && ~isempty(i4)
                            if obj.SPS01{1,i1}.FlagIsDone == true && obj.SPS01{1,i2}.FlagIsDone == true && obj.SPS01{1,i3}.FlagIsDone == true && obj.SPS01{1,i4}.FlagIsDone == true
                                obj.SPS01{1,i1}.device.CmdMoveToVolume(v1);
                                obj.SPS01{1,i2}.device.CmdMoveToVolume(v2);
                                obj.SPS01{1,i3}.device.CmdMoveToVolume(v3);
                                obj.SPS01{1,i4}.device.CmdMoveToVolume(v4);
                                obj.SPS01{1,i1}.FlagReady = false;
                                obj.SPS01{1,i2}.FlagReady = false;
                                obj.SPS01{1,i3}.FlagReady = false;
                                obj.SPS01{1,i4}.FlagReady = false;
                                displaymovement(obj.SPS01{1,i1})
                                displaymovement(obj.SPS01{1,i2})
                                displaymovement(obj.SPS01{1,i3})                                
                                displaymovement(obj.SPS01{1,i4})
                                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                                    notify(obj,'FirstDoneStopPauseWait');
                                end                                
                            end          
                        end
                        
                        
                    end
                end
            end
        end
        
        //// Listener Function : Display the first device to be done and Stop and Pause and chech the WAIT (called in MoveWait)

        function CheckFirstDoneStopPauseWait(obj,varargin)
            if nargin == 8 // only one syringe in motion (=numb input + obj + 2more input (source and event))   
                t=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                i1=varargin{4}; 
                d1=varargin{5};
                v1=varargin{6};
                ts=varargin{7};
                var_not_disp=0;
                if obj.SPS01{1,i1}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:t // it counts until the time specifiend in the wait function
                        if obj.Stop == true
                            StopBoard(obj)
                            obj.flag_break_stop = 1;
                            break //counter1
                        elseif obj.Pause == true                            
                            PauseBoard(obj)
                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                            for count_pause1=1:target
                                if obj.Stop == true 
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off 
                                    UpdateStatus(obj.SPS01{1,i1}) 
                                    obj.flag_a = obj.flag_a +1;
                                    MoveWait(obj,diff_time,d1,v1);  // I use another time target: diff_time=t- time passed                                  
                                    obj.flag_break_countpause = 1;
                                    obj.flag_b = obj.flag_b+1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1
                        elseif obj.SPS01{1,i1}.FlagIsDone == true 
                            displaymovementstop(obj.SPS01{1,i1})
                            var_not_disp=1; // if it is done I don't need to display the commnent "..done after waiting for .. seconds"
                            break //counter1
                        end
                        pause(1)
                    end
                    if obj.flag_break_stop == 0 && var_not_disp ==0 // if the user stopped the board or the board is done before waiting for the target time I don't need to stop the device and display the comment
                        WaitStopBoard(obj)
                        UpdateBoard (obj)                            
                        if  obj.flag_b == obj.flag_a //if it has never be stop flag_b=flag_a=0, if it has been stop flag_b=flag_a only at the last step that print the initial waiting time
                            displaymovementstopwait(obj,t)
                            obj.flag_a = 0; // reintialise the flag
                            obj.flag_b = 0; // reintialise the flag
                        end    
                    end
                end
                
            elseif nargin == 11 // two syringes in motion (=numb input + obj + 2more input (source and event))   
                t=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                i1=varargin{4}; 
                d1=varargin{5};
                v1=varargin{6};
                i2=varargin{7}; 
                d2=varargin{8};
                v2=varargin{9};
                i=[i1 i2];
                d={d1 d2};
                v=[v1 v2];
                ts=varargin{10};
                var_not_disp=0;
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours 
                    for count1=1:t // it counts until the time specifiend in the wait function
                        if obj.Stop == true
                            StopBoard(obj)
                            obj.flag_break_stop = 1;
                            break //counter1
                        elseif obj.Pause == true                            
                            PauseBoard(obj)
                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                            for count_pause1=1:target
                                if obj.Stop == true 
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off 
                                    UpdateStatus(obj.SPS01{1,i1})
                                    UpdateStatus(obj.SPS01{1,i2})
                                    obj.flag_a = obj.flag_a +1;
                                    MoveWait(obj,diff_time,d1,v1,d2,v2);  // I use another time target: diff_time=t- time passed                                  
                                    obj.flag_break_countpause = 1;
                                    obj.flag_b = obj.flag_b+1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1                        
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true
                            for j=1:size(i,2) //search for first device to be done
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    te=toc(ts);// I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                    t1=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                    ts=tic;  
                                    a=i;
                                    a(j)=[];
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:t1
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            obj.flag_break_stop = 1;
                                            break //counter2
                                        elseif obj.Pause == true  
                                            PauseBoard(obj)
                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off 
                                                    UpdateStatus(obj.SPS01{1,a(1)}) 
                                                    obj.flag_a = obj.flag_a +1;
                                                    MoveWait(obj,diff_time,ad{1},av(1));  // I use another time target: diff_time=t- time passed                                  
                                                    obj.flag_break_countpause = 1;
                                                    obj.flag_b = obj.flag_b+1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true
                                            displaymovementstop(obj.SPS01{1,a(1)})
                                            var_not_disp=1; // if it is done I don't need to display the commnent "..done after waiting for .. seconds"
                                            break //counter 2
                                        end 
                                        pause(1) 
                                    end
                                    break //j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(1)
                    end
                    if obj.flag_break_stop == 0 && var_not_disp ==0 // if the user stopped the board or the board is done before waiting for the target time I don't need to stop the device and display the comment
                        WaitStopBoard(obj)
                        UpdateBoard (obj)                            
                        if  obj.flag_b == obj.flag_a //if it has never be stop flag_b=flag_a=0, if it has been stop flag_b=flag_a only at the last step that print the initial waiting time
                            displaymovementstopwait(obj,t)
                            obj.flag_a = 0; // reintialise the flag
                            obj.flag_b = 0; // reintialise the flag
                        end    
                    end
                end
                
            elseif nargin == 14 // 3 syringes in motion
                t=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                i1=varargin{4}; 
                d1=varargin{5};
                v1=varargin{6};
                i2=varargin{7}; 
                d2=varargin{8};
                v2=varargin{9};
                i3=varargin{10};
                d3=varargin{11};
                v3=varargin{12};
                i=[i1 i2 i3];
                d={d1 d2 d3};
                v=[v1 v2 v3];
                ts=varargin{13};
                var_not_disp=0;
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true 
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours
                    for count1=1:t
                        if obj.Stop == true
                            StopBoard(obj)
                            obj.flag_break_stop = 1;
                            break // counter 1
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) 
                                    UpdateStatus(obj.SPS01{1,i2}) 
                                    UpdateStatus(obj.SPS01{1,i3}) 
                                    obj.flag_a = obj.flag_a +1;
                                    MoveWait(obj,diff_time,d1,v1,d2,v2,d3,v3);  // I use another time target: diff_time=t- time passed                                  
                                    obj.flag_break_countpause = 1;
                                    obj.flag_b = obj.flag_b+1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end
                        elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true 
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    te=toc(ts);// I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                    t1=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                    ts=tic;  
                                    a=i;
                                    a(j)=[];
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:t1
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            obj.flag_break_stop = 1;
                                            break //counter2
                                        elseif obj.Pause == true  
                                            PauseBoard(obj)
                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off 
                                                    UpdateStatus(obj.SPS01{1,a(1)}) 
                                                    UpdateStatus(obj.SPS01{1,a(2)})
                                                    obj.flag_a = obj.flag_a +1;
                                                    MoveWait(obj,diff_time,ad{1},av(1),ad{2},av(2));  // I use another time target: diff_time=t- time passed                                  
                                                    obj.flag_break_countpause = 1;
                                                    obj.flag_b = obj.flag_b+1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true
                                            for k=1:size(a,2)
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    te=toc(ts);// I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                                    t2=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                                    ts=tic; 
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:t2
                                                        if obj.Stop == true
                                                            StopBoard(obj)
                                                            obj.flag_break_stop = 1;
                                                            break //counter2
                                                        elseif obj.Pause == true  
                                                            PauseBoard(obj)
                                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) 
                                                                    obj.flag_a = obj.flag_a +1;
                                                                    MoveWait(obj,diff_time,bd{1},bv(1));  // I use another time target: diff_time=t- time passed                                  
                                                                    obj.flag_break_countpause = 1;
                                                                    obj.flag_b = obj.flag_b+1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true
                                                            displaymovementstop(obj.SPS01{1,b(1)})
                                                            var_not_disp=1; // if it is done I don't need to display the commnent "..done after waiting for .. seconds"                                            
                                                            break //counter 3
                                                        end
                                                        pause(1) 
                                                    end
                                                    break // k search of first device to be done 
                                                end
                                            end
                                            break // counter 2
                                        end
                                        pause(1)
                                    end
                                    break // j search of first device to be done 
                                end
                            end
                            break // counter 1
                        end
                        pause(1)
                    end
                    if obj.flag_break_stop == 0 && var_not_disp ==0 // if the user stopped the board or the board is done before waiting for the target time I don't need to stop the device and display the comment
                        WaitStopBoard(obj)
                        UpdateBoard (obj)                            
                        if  obj.flag_b == obj.flag_a //if it has never be stop flag_b=flag_a=0, if it has been stop flag_b=flag_a only at the last step that print the initial waiting time
                            displaymovementstopwait(obj,t)
                            obj.flag_a = 0; // reintialise the flag
                            obj.flag_b = 0; // reintialise the flag
                        end    
                    end
                end
            elseif nargin == 17 // 4 syringes
                t=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the last.
                i1=varargin{4}; 
                d1=varargin{5};
                v1=varargin{6};
                i2=varargin{7}; 
                d2=varargin{8};
                v2=varargin{9};
                i3=varargin{10};
                d3=varargin{11};
                v3=varargin{12};
                i4=varargin{13};
                d4=varargin{14};
                v4=varargin{15};
                i=[i1 i2 i3 i4];
                d={d1 d2 d3 d4};
                v=[v1 v2 v3 v4];
                ts=varargin{16};
                var_not_disp=0;    
                if obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:t
                        if obj.Stop == true
                            StopBoard(obj)
                            obj.flag_break_stop = 1;
                            break // counter 1 
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break //count_pause1
                                elseif obj.Resume == true
                                    obj.ClockResume = clock;
                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    UpdateStatus(obj.SPS01{1,i1}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i2}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i3}) ////////////////////////////
                                    UpdateStatus(obj.SPS01{1,i4}) ////////////////////////////
                                    obj.flag_a = obj.flag_a +1;
                                    MoveWait(obj,diff_time,d1,v1,d2,v2,d3,v3,d4,v4);  // I use another time target: diff_time=t- time passed                                  
                                    obj.flag_break_countpause = 1;
                                    obj.flag_b = obj.flag_b+1;
                                    break //count_pause1
                                end
                                pause(scan_rate)
                            end                             
                       elseif obj.SPS01{1,i1}.FlagIsMoving == true && obj.SPS01{1,i2}.FlagIsMoving == true && obj.SPS01{1,i3}.FlagIsMoving == true && obj.SPS01{1,i4}.FlagIsMoving == true
                            UpdateStatus(obj.SPS01{1,i1});
                            UpdateStatus(obj.SPS01{1,i2});
                            UpdateStatus(obj.SPS01{1,i3});
                            UpdateStatus(obj.SPS01{1,i4}); 
                        end
                        if obj.flag_break_countpause == 1
                            break //counter1  
                        elseif obj.SPS01{1,i1}.FlagIsDone == true || obj.SPS01{1,i2}.FlagIsDone == true || obj.SPS01{1,i3}.FlagIsDone == true || obj.SPS01{1,i4}.FlagIsDone == true
                            for j=1:size(i,2)
                                if obj.SPS01{1,i(j)}.FlagIsDone == true
                                    displaymovementstop(obj.SPS01{1,i(j)})
                                    te=toc(ts);// I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                    t1=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                    ts=tic;                                    
                                    a=i;
                                    a(j)=[]; 
                                    ad=d;
                                    ad(j)=[];
                                    av=v;
                                    av(j)=[];
                                    for count2=1:t1
                                        if obj.Stop == true
                                            StopBoard(obj)
                                            obj.flag_break_stop = 1;
                                            break //counter2
                                        elseif obj.Pause == true
                                            PauseBoard(obj)
                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                            for count_pause1=1:target
                                                if obj.Stop == true
                                                    break //count_pause1
                                                elseif obj.Resume == true
                                                    obj.ClockResume = clock;
                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                    diary on
                                                    disp(comment);
                                                    diary off 
                                                    UpdateStatus(obj.SPS01{1,a(1)}) ////////////////////////////
                                                    UpdateStatus(obj.SPS01{1,a(2)}) ////////////////////////////                                                    
                                                    UpdateStatus(obj.SPS01{1,a(3)}) ////////////////////////////
                                                    MoveWait(obj,diff_time,ad{1},av(1),ad{2},av(2),ad{3},av(3));  // I use another time target: diff_time=t- time passed                                  
                                                    obj.flag_break_countpause = 1;
                                                    obj.flag_b = obj.flag_b+1;
                                                    break //count_pause1
                                                end
                                                pause(scan_rate)
                                            end                                             
                                        elseif obj.SPS01{1,a(1)}.FlagIsMoving == true && obj.SPS01{1,a(2)}.FlagIsMoving == true && obj.SPS01{1,a(3)}.FlagIsMoving == true
                                            UpdateStatus(obj.SPS01{1,a(1)});
                                            UpdateStatus(obj.SPS01{1,a(2)});
                                            UpdateStatus(obj.SPS01{1,a(3)});    
                                        end
                                        if obj.flag_break_countpause == 1
                                            break //counter1  
                                        elseif obj.SPS01{1,a(1)}.FlagIsDone == true || obj.SPS01{1,a(2)}.FlagIsDone == true || obj.SPS01{1,a(3)}.FlagIsDone == true
                                            for k=1:size(a,2) 
                                                if obj.SPS01{1,a(k)}.FlagIsDone == true
                                                    displaymovementstop(obj.SPS01{1,a(k)})
                                                    te=toc(ts);// I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                                    t2=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                                    ts=tic;
                                                    b=a;
                                                    b(k)=[];
                                                    bd=ad;
                                                    bd(k)=[];
                                                    bv=av;
                                                    bv(k)=[];
                                                    for count3=1:t2
                                                        if obj.Stop == true
                                                            topBoard(obj)
                                                            obj.flag_break_stop = 1;
                                                            break //counter3
                                                        elseif obj.Pause == true
                                                            PauseBoard(obj)
                                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                                            for count_pause1=1:target
                                                                if obj.Stop == true
                                                                    break //count_pause1
                                                                elseif obj.Resume == true
                                                                    obj.ClockResume = clock;
                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                    diary on
                                                                    disp(comment);
                                                                    diary off 
                                                                    UpdateStatus(obj.SPS01{1,b(1)}) ////////////////////////////
                                                                    UpdateStatus(obj.SPS01{1,b(2)}) ////////////////////////////
                                                                    MoveWait(obj,diff_time,bd{1},bv(1),bd{2},bv(2));                                    
                                                                    obj.flag_break_countpause = 1;
                                                                    obj.flag_b = obj.flag_b+1;
                                                                    break //count_pause1
                                                                end
                                                                pause(scan_rate)
                                                            end    
                                                        elseif obj.SPS01{1,b(1)}.FlagIsMoving == true && obj.SPS01{1,b(2)}.FlagIsMoving == true
                                                            UpdateStatus(obj.SPS01{1,b(1)});
                                                            UpdateStatus(obj.SPS01{1,b(2)});
                                                        end
                                                        if obj.flag_break_countpause == 1
                                                            break //counter1  
                                                        elseif obj.SPS01{1,b(1)}.FlagIsDone == true || obj.SPS01{1,b(2)}.FlagIsDone == true
                                                            for p=1:size(b,2)
                                                                
                                                                if obj.SPS01{1,b(p)}.FlagIsDone == true
                                                                    displaymovementstop(obj.SPS01{1,b(p)})
                                                                    te=toc(ts); //I calculate how long has been since the movement has started (tic whan it started moving, toc when the first syringe is done)
                                                                    t3=(t-te); // I calculate the time difference between the initial time target t and the time passed. I add 0.5 because there is a discrepancy in time.
                                                                    ts=tic; 
                                                                    c=b;
                                                                    c(p)=[];
                                                                    cd=bd;
                                                                    cd(p)=[];
                                                                    cv=bv;
                                                                    cv(p)=[];
                                                                    for count4=1:t3
                                                                        if obj.Stop == true
                                                                            StopBoard(obj)
                                                                            obj.flag_break_stop = 1;
                                                                            break // counter 4
                                                                        elseif obj.Pause == true
                                                                            PauseBoard(obj)
                                                                            te=toc(ts); // I calculate how long has been since the movement has started (tic whan it started moving, toc when it paused)
                                                                            diff_time=t-te; // I calculate the time difference between the initial time target t and the time passed
                                                                            for count_pause1=1:target
                                                                                if obj.Stop == true
                                                                                    break //count_pause1
                                                                                elseif obj.Resume == true
                                                                                    obj.ClockResume = clock;
                                                                                    comment=[num2str(obj.ClockResume(4)) , ':' , num2str(obj.ClockResume(5)) ,':' ,num2str(obj.ClockResume(6)), ' Interface resumed by the user.']; 
                                                                                    diary on
                                                                                    disp(comment);
                                                                                    diary off 
                                                                                    UpdateStatus(obj.SPS01{1,c(1)}) ////////////////////////////
                                                                                    obj.flag_a = obj.flag_a +1;
                                                                                    MoveWait(obj,diff_time,cd{1},cv(1));                                    
                                                                                    obj.flag_break_countpause = 1;
                                                                                    obj.flag_b = obj.flag_b+1;
                                                                                    break //count_pause1
                                                                                end
                                                                                pause(scan_rate)
                                                                            end  
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsMoving == true
                                                                            UpdateStatus(obj.SPS01{1,c(1)});
                                                                        end
                                                                        if obj.flag_break_countpause == 1
                                                                            break //counter1
                                                                        elseif obj.SPS01{1,c(1)}.FlagIsDone == true
                                                                            displaymovementstop(obj.SPS01{1,c(1)})
                                                                            var_not_disp=1; // if it is done I dont need to display the commnent "..done after waiting for .. seconds"     
                                                                            break // counter 4
                                                                        end
                                                                        pause(1)
                                                                    end
                                                                    break // p search of first device to be done
                                                                end
                                                            end
                                                            break //counter 3
                                                        end                                                        
                                                        pause(1)
                                                    end
                                                    break // k search of first device to be done
                                                end
                                            end
                                            break //counter 2
                                        end
                                        pause(1)
                                    end
                                    break // j search of first device to be done
                                end
                            end
                            break // counter 1
                        end
                        pause(1)
                    end
                    if obj.flag_break_stop == 0 && var_not_disp ==0 // if the user stopped the board or the board is done before waiting for the target time I don't need to stop the device and display the comment
                        WaitStopBoard(obj)
                        UpdateBoard (obj)                            
                        if  obj.flag_b == obj.flag_a //if it has never be stop flag_b=flag_a=0, if it has been stop flag_b=flag_a only at the last step that print the initial waiting time
                            displaymovementstopwait(obj,t)
                            obj.flag_a = 0; // reintialise the flag
                            obj.flag_b = 0; // reintialise the flag
                        end    
                    end                    
                end
                
                
               
                                                                   
                                        
                            
                
                
                
                
            end
        end



        //// Set Valves2 It allows the pause too
        function SetValves2(obj,d1,v11,v12,v13,v14,d2,v21,v22,v23,v24)
            obj.flag_break_countpause = 0;
            if obj.Stop == false
                if nargin == 6 // 1 manifold as input
                    i1=FindIndexM(obj,d1);
                    obj.listener_firstdoneM = addlistener(obj, 'FirstDoneStopPauseM',@(src,evnt)obj.CheckFirstDoneStopPauseM(src,evnt,i1,d1,v11,v12,v13,v14)); //it listens for the manifold FlagIsDone, so it updtades continuously the state to determine the end of the command. 
                    if ~isempty(i1)   
                        if obj.C4VM{1,i1}.FlagIsDone == true
                            obj.C4VM{1,i1}.device.CmdSetValves(int8(v11),int8(v12),int8(v13),int8(v14));                              
                            displayswitch(obj.C4VM{1,i1},v11,v12,v13,v14);
                            if obj.C4VM{1,i1}.FlagIsDone == false 
                                notify(obj,'FirstDoneStopPauseM');
                            end
                        end
                    end
                end
            end
        end
        
        function CheckFirstDoneStopPauseM(obj,varargin)
            if nargin == 9 // only one manifold in motion (=numb input + obj + 2more input (source and event))  
                i1=varargin{3}; //vararging doesn't include the obj, so its size is nargin-1. The index is the third.
                d1=varargin{4};
                v11=varargin{5};
                v12=varargin{6};
                v13=varargin{7};
                v14=varargin{8};
                if obj.C4VM{1,i1}.FlagIsDone == false  
                    scan_rate=0.1; //the scan rate of the counter
                    target=(48)*60*60/scan_rate; //this is the final time of the counter. It is equal to max 48 hours                   
                    for count1=1:target //this is a counter clock to check if the stop_status variable has changed
                        if obj.Stop == true
                            StopBoard(obj)
                            break
                        elseif obj.Pause == true
                            PauseBoard(obj)
                            for count_pause1=1:target
                                if obj.Stop == true
                                    break
                                elseif obj.Resume == true
                                    comment=[num2str(obj.ClockStop(4)) , ':' , num2str(obj.ClockStop(5)) ,':' ,num2str(obj.ClockStop(6)), ' Interface resumed by the user.']; 
                                    diary on
                                    disp(comment);
                                    diary off  
                                    SetValves2(obj,d1,v11,v12,v13,v14);                                    
                                    obj.flag_break_countpause = 1;
                                    break
                                end
                                pause(scan_rate)
                            end
                        elseif obj.C4VM{1,i1}.FlagIsDone == false
                            UpdateStatus(obj.C4VM{1,i1});
                        end
                        if obj.flag_break_countpause == 1
                            break
                        elseif obj.C4VM{1,i1}.FlagIsDone == true
                            displayswitchstop(obj.C4VM{1,i1})
                            break
                        end
                        pause(scan_rate)
                    end
                end
            end
        end
        
        
        
    end


end