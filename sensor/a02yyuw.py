'''
  A02YYUW Ultrasonic Sensor
  a02yyuw.py
  moritz.heusinger@itemis.com
  itemis AG
'''
 
import machine
import time

# header marks beginning of data
header = b'\xff'

class A02YYUW:
    """
    Driver to listen to A02YYUW waterproof ultrasonic sensor data
    param: uart_id (default 2) e.g. 0 (tx:1/rx:3) 1 (tx:10/rx:9) 2 (tx:17/rx:16) on ESP32 WROOM 
     
    Additional information:
    TX can be used to switch between 300ms (more accuracy - PIN HIGH or not connected)
    and 100ms (more frequency - PIN LOW) readings
   
    RX: 4 Bytes of data
    1. is the header
    2. Data 1 high end of data with distance in mm
    3. Data 2 low end of data
    4. Checksum (must equal 1 + 2 + 3)
    """
    
    def __init__(self, uart_id=2):
        self.uart = machine.UART(uart_id, baudrate=9600)
        self.uart.init(9600, bits=8)
 
    """
    Read data if available
    
    Returns: None if no data available
    Else the distance in mm
    """
    def read(self):
      # if data available
      if self.uart.any():
                          
        if self.uart.read(1) == header:
          data_buffer = bytearray(4)
          data_buffer[0] = 0xff
          # read remaining 3 chars
          for i in range(1, 4):
            data_buffer[i] = self.uart.read(1)[0]
          
          checksum = sum(data_buffer[:-1]) & 0xFF
                    
          # if checksum is valid compose distance from data
          if data_buffer[3] == checksum:
            distance = (data_buffer[1] << 8) + data_buffer[2]
            return distance
        