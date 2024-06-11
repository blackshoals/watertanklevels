#Water Tank Sensor V5

import utime
import network
import espnow
import machine
from a02yyuw import A02YYUW
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD
 
reboot_delay = 5 #seconds
cycle_time = 15 #seconds
controller_mac = b'\xb0\xb2\x1c\x50\xb2\xb0' # MAC address of peer1's wifi interface
tank_offset = 5  #space between water surface when full and sensor in cm
tank_height = 60 # total height from bottom to sensor in cm

def reboot(delay = reboot_delay):
 #  print a message and give time for user to pre-empt reboot
 #  in case we are in a (battery consuming) boot loop
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
 #  or just machine.deepsleep(delay) or lightsleep()
    utime.sleep(delay)
    machine.reset()

def read_tank_percentage():
    sensor = A02YYUW()
    retries = 10
    while retries > 0
        try:
            distance = sensor.read()
            if distance is not None:
                distance = round(distance / 10)
                tank_percentage = round((1 - (distance - TANK_OFFSET) / TANK_HEIGHT) * 100)
                return tank_percentage
        except Exception as e:
            print('Error reading sensor:', e)
        retries -= 1
        utime.sleep_ms(50)
    return None
        
def battery_voltage(): # Battery Voltage
# Voltage Divider R1 = 6K and R2 = 22k
    calib_factor = 5.28
    adc = ADC(0)
    raw = adc.read()
    battery_voltage = raw * calib_factor / 1024
    return battery_voltage

def initialize_espnow():
       try:  
           #establish ESP-NOW
           print('Initializing...')
           sta = network.WLAN(network.STA_IF) #set station mode
           sta.active(True)
         
           e = espnow.ESPNow() # Enable ESP-NOW
           e.active(True)
           e.config(timeout_ms = (cycle_time * 1000))
           e.add_peer(controller_mac)            # add controller as a receiver
           return e
       except Exception as e:
        print('Error initializing ESP-NOW:', e)
        return None

def main():
       try:
              print ('you have 5 seconds to do Ctrl-C if you want to edit the program')
              utime.sleep(5)
              #if the machine is powered off and on check for an updated software version
              if (machine.reset_cause() == 1):
                     firmware_url = "https://github.com/blackshoals/watertanklevels/main/sensor/"
                     ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "level_sensor.py")
                     ota_updater.download_and_install_update_if_available()
                     
              esp_now = initialize_espnow()
              if esp_now is None:
                   reboot()
                                   
              while True:
                     upper_tank_percentage = read_tank_percentage() #water level sensor
                     if upper_tank_percentage is not None:
                            esp_now.send(CONTROLLER_MAC, str(tank_percentage), False)
                            print("Sent :", upper_tank_percentage, "%")
                                 
              machine.lightsleep(cycle_time * 1000)
       
       except KeyboardInterrupt as err:
           raise err #  use Ctrl-C to exit to micropython repl
       except Exception as err:
           print ('Error during execution:', err)
           reboot()

if __name__ == "__main__":
    main()