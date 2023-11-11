
import os
import threading
import time
import serial
import json

from mpBoard import MPBoard

class MPController:

    def __init__(self, port:str='/dev/ttyACM0', path:str='controller/main.py', baudrate:int=115200) -> None:
        
        self._board = None
        
        self._port = port
        self._path = path
        self._baudrate = baudrate
        
        self._board_running = False
        self._process = None
        self._thread_board = None
        
        self._serial = None
        self._serial_connected = False
        
        self.__start_board()
        self.__connect_board()
    
    def serial_write(self, data):
        if (self._serial_connected):
            
            str_data = json.dumps(data) + '\n'
            bytesdata = str_data.encode('utf-8')
            
            try:
                self._serial.write(bytesdata)
                self._serial.flush()
            
            except:
                print("Connection to subprocess board lost")
                self._serial_connected = False
                # Try reset the board
                self._board.exit_raw_repl()
    
    def __start_board(self) -> None:
        print(f"Initiating subprocess: {self._path} on board at port: {self._port}")

        if (not (os.path.exists(self._port))):
            exit("Board not detected make sure port is correct: " + self._port)    
            
        try:
            if (not (os.path.exists(self._path))):
                exit(f"process not found in the specified path: {self._path}")
            # Starting scripts on board on separate thread
            self._thread_board = threading.Thread(target=self.__run_controller_board, daemon=True)
            self._thread_board.start()
            # Wait for the thread
            while (not self._thread_board.is_alive()): time.sleep(1)
            time.sleep(3) # if this wait is too small serial connection might fail without messages
            self._board_running = True
            print("Subprocess Running")
            
        except:
            print("Failed to run subprocess")

    def __connect_board(self) -> None:
        print(f"Connecting to the subprocess board in port: {self._port}")
        if not ((os.path.exists(self._port)) and (self._board_running)):
            exit("Error: Board may not be running")
            
        try:
            self._serial = serial.Serial(port=self._port, baudrate=self._baudrate)
            self._serial_connected = True
            print("Connection OK")
            
        except:
            exit("Error: Could not establish connection")            

    def __run_controller_board(self, wait_output=True, stream_output=True):
        print("Starting subprocess on the board...")
        self._board = MPBoard(device=self._port, baudrate=self._baudrate)
        self._board.enter_raw_repl()
        out = None
        if stream_output:
            self._board.execfile(self._path, stream_output=True)
            
        elif wait_output:
            # Run the file and wait for output to return.
            out = self._board.execfile(self._path)
        
        else:
            # Read the file and run it using lower level pyboard functions that
            # won't wait for it to finish or return output.
            with open(self._path, "rb") as infile:
                self._board.exec_raw_no_follow(infile.read())
        
        self._board.exit_raw_repl()
        
        if out is not None:
            print(out.decode("utf-8"), end="")
        
        return out