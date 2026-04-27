classdef Lacewing < handle
    properties (GetAccess = 'public', SetAccess = 'public', SetObservable)
        device = [];
        ROWS = 78;
        COLS = 56;
        port = []; %the COM port to which the device is connected
        

        % Clocks
        Clock
    end

    events
    end

     methods(Access = public)

         %% Constructor
        function obj = Lacewing
            py.importlib.import_module('Lacewing_Cmd_Chiara');
            obj.device=py.Lacewing_Cmd_Chiara.Debug_Command; % creates the object             
        end

        %% Distructor
        function Disconnect(obj)
            obj.device.close_serial
            diary on
            comm =['Serial port ', convertStringsToChars(obj.port), ' closed. Device disconnected on ' , num2str(obj.Clock(3)), '/' , num2str(obj.Clock(2)), '/' , num2str(obj.Clock(1)), ' at ', num2str(obj.Clock(4)) , ':' , num2str(obj.Clock(5)) ,':' ,num2str(obj.Clock(6))];
            disp(comm)
            diary off
            obj.port = [];
        end


        %% Connect
        function Connect(obj,port)
            obj.port = port;
            obj.device.open_serial(port); %it connects to the device
            obj.device.set_timeout(1000000000); % i need to extend the timeout
            obj.device.execute_cmd('ttn_init 3 50'); %initailise th device 
            obj.Clock = clock;
            diary OUTPUT
            comm =['Serial port ', convertStringsToChars(obj.port), ' opened. Device connected and initialised on ' , num2str(obj.Clock(3)), '/' , num2str(obj.Clock(2)), '/' , num2str(obj.Clock(1)), ' at ', num2str(obj.Clock(4)) , ':' , num2str(obj.Clock(5)) ,':' ,num2str(obj.Clock(6))];
            disp(comm)
            diary off
        end

        %% FindInfo
        function [name,port] = FindInfo(obj)
            info=obj.device.list_serial; %list the serial port connected to the pc
            name = cellfun(@string,cell(info{1})); %it converts the py.entry in a string
            port = cellfun(@string,cell(info{2})); %it converts the py.entry in a string
        end

        %% CheckChip
        function r=CheckChip(obj)
            r=obj.device.execute_cmd('ttn_check_status'); % 0 not available, 1 electrically active, 2, chemically active,  3 both
            if r == 3
                diary on
                disp ('Chip ready')
                diary off
            elseif r == 2
                diary on
                disp ('Chip not chemically active')
                diary off
            elseif r == 1
                diary on 
                disp ('Chip not electrically active')
                diary off
            elseif r == 0
                diary on
                disp('Chip not available')
                diary off
            end
        end

        %% RefCalibration
        function Vref_V = Calibration(obj)
            Vref=obj.device.execute_cmd('ttn_sweep_search_vref');
            Vref_V = (Vref * 10 / 4095) - 5;  % heoritial calculation, the real voltage can be slightly different
            diary on
            disp (['Chip is calibrated. Vref is ' , num2str(Vref_V), ' V'])
            diary off
        end

        %% PixelStatus

        function array_status = PixelStatus(obj)
            a = obj.device.execute_cmd('ttn_eval_pixel'); % check status of each pixels (511 active, o discharge too fast, 1023 doscharge too slow)
            array_status = cellfun(@double,cell(a));
        end

        %% Calibrated Array

        function array_calibrated = CalibArray(obj)
            obj.device.execute_cmd('ttn_temp_init');
            a = obj.device.execute_cmd('ttn_cali_vs');
            array_calibrated = cellfun(@double,cell(a));
%             figure(2)
%             surf(flipud(reshape(array_calibrated,obj.ROWS,obj.COLS))); view(2);
%             axis tight
%             title('Array calibrated');
%             xlabel('COLS')
%             ylabel('ROWS')
        end

        %% RunOut % modify to add listner for stop and add plot in the window interface

%         function RunOut(obj,time,time_unit)
%             if time_unit == 'sec'
%                 t=time;
%             elseif time_unit == 'min'
%                 t=time*60;
%             elseif time_unit == 'hour'
%                 t=time*60*60;
%             elseif time_unit == 'day'
%                 t=time*60*60*24;                
%             end
%             obj.device.execute_cmd('ttn_temp_init');
%             RunWait(obj,t)
%         end
% 
%         function RunWait(obj,time_sec)
%             t_stamp=0;
%             t=[];
%             avg_px=[];
%             tstart=tic;
%             while t_stamp < time_sec
%                 readout=obj.device.execute_cmd('ttn_readout_vs');
%                 if ~isempty(readout)
%                     t_stamp=toc(tstart);
%                     t=[t t_stamp];
%                     c_readout=cell(readout);
%                     A_readout = cellfun(@double,c_readout);
%                     figure(3)
%                     surf(flipud(reshape(A_readout,obj.ROWS,obj.COLS))); view(2);
%                     axis tight
%                     title(['Array at timebut I frame t = ',num2str(t_stamp), ' sec']);
%                     xlabel('COLS')
%                     ylabel('ROWS')
%                     figure(5)
%                     avg_px=[avg_px mean(A_readout)];
%                     plot(t,avg_px)
%                 end
%                 readout=[];  
%             end
%         end



    
     end

end