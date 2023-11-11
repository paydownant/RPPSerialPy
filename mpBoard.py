
import sys
import time
import serial

_rawdelay = None

try:
    stdout = sys.stdout.buffer
    
except AttributeError:
    # Python2 doesn't have buffer attr
    stdout = sys.stdout

def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    stdout.write(b)
    stdout.flush()

class MPBoardError(BaseException):
    pass


class MPBoard:
    def __init__(self, device, baudrate=115200, wait=0, rawdelay=0) -> None:
        global _rawdelay
        _rawdelay = rawdelay
        
        if device and device[0].isdigit() and device[-1].isdigit() and device.count('.') == 3:
            # device looks like an IP address
            exit("do not use IP address")
        else:
            delayed = False
            for attempt in range(wait + 1):
                try:
                    self._serial = serial.Serial(device, baudrate=baudrate)
                    break
                
                except(OSError, IOError):
                    if wait == 0:
                        continue
                    if attempt == 0:
                        sys.stdout.write('Waiting {} seconds for pyboard '.format(wait))
                        delayed = True
                
                time.sleep(1)
                sys.stdout.write('.')
                sys.stdout.flush()
                
            else:
                if delayed:
                    print('')
                raise MPBoardError('failed to access ' + device)
            
            if delayed:
                print('')
    
    def enter_raw_repl(self):
        # Brief delay before sending RAW MODE char if requests
        if _rawdelay > 0:
            time.sleep(_rawdelay)
        
        # ctrl-C twice: interrupt any running program
        self._serial.write(b'\r\x03')
        time.sleep(0.1)
        self._serial.write(b'\x03')
        time.sleep(0.1)
        
        # flush input (without relying on serial.flushInput())
        n = self._serial.inWaiting()
        while n > 0:
            self._serial.read(n)
            n = self._serial.inWaiting()
        
        for retry in range(0, 5):
            self._serial.write(b'\r\x01') # ctrl-A: enter raw REPL
            data = self.read_until(1, b'raw REPL; CTRL-B to exit\r\n>')
            if data.endswith(b'raw REPL; CTRL-B to exit\r\n>'):
                break
            else:
                if retry >= 4:
                    print(data)
                    raise MPBoardError('could not enter raw repl')
                time.sleep(0.2)
        self._serial.write(b'\x04') # ctrl-D: soft reset
        data = self.read_until(1, b'soft reboot\r\n')
        if not data.endswith(b'soft reboot\r\n'):
            print(data)
            raise MPBoardError('could not enter raw repl')
        time.sleep(0.5)
        self._serial.write(b'\x03')
        time.sleep(0.1)     # slight delay before second interrupt
        self._serial.write(b'\x03')
        
        data = self.read_until(1, b'raw REPL; CTRL-B to exit\r\n')
        if not data.endswith(b'raw REPL; CTRL-B to exit\r\n'):
            print(data)
            raise MPBoardError('could not enter raw repl')

    def exit_raw_repl(self):
        self._serial.write(b'\r\x02') # ctrl-B: enter friendly REPL
    
    def close(self):
        self._serial.close()
    
    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        data = self._serial.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self._serial.inWaiting() > 0:
                new_data = self._serial.read(1)
                data = data + new_data
                if data_consumer:
                    data_consumer(new_data)
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def exec_(self, command, stream_output=False):
        data_consumer = None
        if stream_output:
            data_consumer = stdout_write_bytes
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise MPBoardError('exception', ret, ret_err)
        return ret
    
    def follow(self, timeout, data_consumer=None):
        # wait for normal output
        data = self.read_until(1, b'\x04', timeout=timeout, data_consumer=data_consumer)
        if not data.endswith(b'\x04'):
            raise MPBoardError('timeout waiting for first EOF reception')
        data = data[:-1]

        # wait for error output
        data_err = self.read_until(1, b'\x04', timeout=timeout)
        if not data_err.endswith(b'\x04'):
            raise MPBoardError('timeout waiting for second EOF reception')
        data_err = data_err[:-1]

        # return normal and error output
        return data, data_err
    
    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, encoding='utf8')

        # check we have a prompt
        data = self.read_until(1, b'>')
        if not data.endswith(b'>'):
            raise MPBoardError('could not enter raw repl')

        # write command
        for i in range(0, len(command_bytes), 256):
            self._serial.write(command_bytes[i:min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self._serial.write(b'\x04')

        # check if we could exec command
        data = self._serial.read(2)
        if data != b'OK':
            raise MPBoardError('could not exec command')
    
    def exec_raw(self, command, timeout=10, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)
    
    def execfile(self, filename, stream_output=False):
        with open(filename, 'rb') as f:
            pyfile = f.read()
        return self.exec_(pyfile, stream_output=stream_output)