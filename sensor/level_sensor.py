#Water Tank Sensor V7

import time
import network
import espnow
import machine
import ustruct
from a02yyuw import A02YYUW
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD
 
reboot_delay = 5 #seconds
cycle_time = 60 #seconds
controller_mac = b'\xb0\xb2\x1c\x50\xb2\xb0' # MAC address of peer1's wifi interface
tank_offset = 5  #space between water surface when full and sensor in cm
tank_height = 60 # total height from bottom to sensor in cm

def reboot(delay = reboot_delay):
 #  print a message and give time for user to pre-empt reboot
 #  in case we are in a (battery consuming) boot loop
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
 #  or just machine.deepsleep(delay) or lightsleep()
    time.sleep(delay)
    machine.reset()

def read_tank_percentage():
    sensor = A02YYUW()
    retries = 10
    while retries > 0:
        try:
            distance = sensor.read()
            if distance is not None:
                distance = round(distance / 10)
                tank_percentage = round((1 - (distance - tank_offset) / tank_height) * 100)
                return tank_percentage
        except Exception as err:
            print('Error reading sensor:', err)
        retries -= 1
        time.sleep_ms(50)
    return None
        
def read_battery_voltage(): # Battery Voltage
# # Voltage Divider R1 = 6K and R2 = 22k
#     calib_factor = 5.28
#     adc = ADC(0)
#     raw = adc.read()
#     battery_voltage = raw * calib_factor / 1024
     battery_voltage = 75
     return battery_voltage

def initialize_espnow():
       try:  
           #establish ESP-NOW
           print('Initializing...')
           sta = network.WLAN(network.STA_IF) #set station mode
           sta.active(True)

           # Enable ESP-NOW
           e = espnow.ESPNow()
           e.active(True)
           e.add_peer(controller_mac)            # add controller as a receiver
           return e
       except Exception as err:
        print('Error initializing ESP-NOW:', err)
        return None


try:    
      #if the machine is powered off and on check for an updated software version
      if (machine.reset_cause() == 1):
          
             print ('you have 5 seconds to do Ctrl-C if you want to edit the program')
             time.sleep(5)
              
             firmware_url = "https://github.com/blackshoals/watertanklevels/main/sensor/"
             ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "level_sensor.py")
             ota_updater.download_and_install_update_if_available()
      else:
          pass
             
      esp_now = initialize_espnow()
      if esp_now is None:
           reboot()
      else:
          pass
                           
      while True:
            upper_tank_percentage = read_tank_percentage() #water level sensor
            battery_voltage = read_battery_voltage()

            if upper_tank_percentage is not None:
                 send_message = ustruct.pack('ii', upper_tank_percentage, battery_voltage)
                 esp_now.send(controller_mac, send_message, True)
                 print("Sent Upper Tank:", upper_tank_percentage, "% Battery: ",battery_voltage, " %")
            else:
                 pass
                                         
            machine.deepsleep(cycle_time * 1000)

except KeyboardInterrupt as err:
   raise err #  use Ctrl-C to exit to micropython repl
except Exception as err:
   print ('Error during execution:', err)
   reboot()
