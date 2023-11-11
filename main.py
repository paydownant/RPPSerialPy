
from mpController import MPController

# Example implementation for serial connection
def blink_led():
    controller = MPController(port='/dev/ttyACM0', path='controller/main.py', baudrate=115200)
    
    while True:
        # 0 to 255
        for i in range(0, 256, 1):
            data = {
                "data_1": i,
                "data_2": i,
                "data_3": i
            }
            controller.serial_write(data)
        
        # 255 to 0
        for i in range(255, -1, -1):
            data = {
                "data_1": i,
                "data_2": i,
                "data_3": i
            }
            controller.serial_write(data)

blink_led()