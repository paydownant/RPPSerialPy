
# This file should be uploaded to micropython board automatically

import select
import sys
import json
import time
from machine import PWM, Pin

# setup poll to read USB port
poll_object = select.poll()
poll_object.register(sys.stdin,1)

pwm = PWM(Pin("LED"))
pwm.freq(1000)

duty = 0
data = None
interval = 1
start = time.time()
""" Main Loop """
while True:

    if poll_object.poll(0):
        ch = sys.stdin.readline()
        str_data = str(ch.strip())
        
        data = json.loads(str_data)
        
        data_1 = data["data_1"]
        
        duty = int(data_1)
    
    
    if duty in range(0,256):
        pwm.duty_u16(257 * duty)
    else:
        pwm.duty_u16(0)
    
    
    if (time.time() >= start + interval):
        start = time.time()
        if not data is None:
            print(data)