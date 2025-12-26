from datetime import datetime
import re

class Lacewing:
    
    def __init__(self):
        ## General info
        self.device = None
        self.ROWS = 78
        self.COLS = 56
        self.port = None  # the COM port to which the device is connected
        
        ## Clocks
        self.Clock = None
        
        try:
            import importlib
            lacewing_cmd = importlib.import_module('Lacewing_Cmd_Chiara')
            self.device = lacewing_cmd.Debug_Command  # creates the object
        except ImportError:
            print("Warning: Lacewing_Cmd_Chiara module not found. Some functionality may be limited.")
            
    ## Destructor
    def Disconnect(self):
        if self.device:
            self.device.close_serial()
        self.Clock = datetime.now()
        with open("OUTPUT.txt", "a") as OUTPUT:
            comm = f"Serial port {self.port} closed. Device disconnected on {self.Clock.strftime('%d/%m/%Y at %H:%M:%S')}"
            OUTPUT.write(comm + "\n")
            print(comm)
        self.port = None
        
    ## Connect
    def Connect(self, port):
        self.port = port
        if self.device:
            self.device.open_serial(port)  # it connects to the device
            self.device.set_timeout(1000000000)  # i need to extend the timeout
            self.device.execute_cmd('ttn_init 3 50')  # initialise the device
            self.Clock = datetime.now()
            with open("OUTPUT.txt", "a") as OUTPUT:
                comm = f"Serial port {port} opened. Device connected and initialised on {self.Clock.strftime('%d/%m/%Y at %H:%M:%S')}"
                OUTPUT.write(comm + "\n")
                print(comm)
                
    ## FindInfo
    def FindInfo(self):
        if not self.device:
            return [], []
        info = self.device.list_serial()  # list the serial port connected to the pc
        # it converts the py.entry in a list of strings
        name = [str(item) for item in info[0]]
        port = [str(item) for item in info[1]]
        return name, port
        
    ## CheckChip
    def CheckChip(self):
        if not self.device:
            return
        r = self.device.execute_cmd('ttn_check_status')  # 0 not available, 1 electrically active, 2 chemically active, 3 both
        with open("OUTPUT.txt", "a") as OUTPUT:
            if r == 3:
                comm = 'Chip ready'
            elif r == 2:
                comm = 'Chip not chemically active'
            elif r == 1:
                comm = 'Chip not electrically active'
            elif r == 0:
                comm = 'Chip not available'
            
            OUTPUT.write(comm + "\n")
            print(comm)
        return r
            
    ## Calibration
    def Calibration(self):
        if not self.device:
            return
        Vref = self.device.execute_cmd('ttn_sweep_search_vref')
        Vref_V = (Vref * 10 / 4095) - 5  # theoretical calculation, the real voltage can be slightly different
        with open("OUTPUT.txt", "a") as OUTPUT:
            comm = f"Chip is calibrated. Vref is {Vref_V} V"
            OUTPUT.write(comm + "\n")
            print(comm)
        return Vref_V
        
    ## PixelStatus
    def PixelStatus(self):
        if not self.device:
            return
        a = self.device.execute_cmd('ttn_eval_pixel')  # check status of each pixels (511 active, o discharge too fast, 1023 discharge too slow)
        array_status = [float(item) for item in a]
        return array_status
        
    ## Calibrated Array
    def CalibArray(self):
        if not self.device:
            return
        self.device.execute_cmd('ttn_temp_init')
        a = self.device.execute_cmd('ttn_cali_vs')
        array_calibrated = [float(item) for item in a]
        return array_calibrated




