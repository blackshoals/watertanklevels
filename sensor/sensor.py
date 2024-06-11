#Water Tank Sensor

from a02yyuw import A02YYUW
import utime
import network
import espnow
import machine

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
    while True:
        distance = sensor.read()
        utime.sleep(0.5)
        if distance is not None: #take readings until one is found
            distance = round(distance/10)          # tank measurement in cm
            tank_percentage = round((1-(distance-tank_offset)/tank_height) *100)
            return tank_percentage
            break
        else:
            pass
        
def battery_voltage(): # Battery Voltage
# Voltage Divider R1 = 6K and R2 = 22k
    calib_factor = 5.28
    adc = ADC(0)
    raw = adc.read()
    battery_voltage = raw * calib_factor / 1024
    return battery_voltage)


# establish ESP-NOW
try:
    print ('you have 5 seconds to do Ctrl-C if you want to edit the program')
    utime.sleep(5)
    
    sta = network.WLAN(network.STA_IF)    # Enable station mode for ESP

    e = espnow.ESPNow() # Enable ESP-NOW
    e.active(True)
    e.config(timeout_ms = (cycle_time * 1000))
    e.add_peer(controller_mac)            # add controller as a reeiver
    
except KeyboardInterrupt as err:
    raise err #  use Ctrl-C to exit to micropython repl
except Exception as err:
    print ('Error initialising espnow:', err)
    reboot()

try:
    while True:
        upper_tank_percentage = read_tank_percentage() #water level sensor
        utime.sleep(0.5)
        if upper_tank_percentage is not None:
            sta.active(True)
            e.send(controller_mac,str(upper_tank_percentage), True)     # send commands to the pump controller
            print("Sent :", upper_tank_percentage, "%")
            sta.active(False)
            

        machine.lightsleep(cycle_time * 1000)

except KeyboardInterrupt as err:
    raise err #  use Ctrl-C to exit to micropython repl
except Exception as err:
    print ('Error during execution:', err)
    reboot()

