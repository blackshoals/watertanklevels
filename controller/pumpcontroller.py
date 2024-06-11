#Pump Controller V2

from a02yyuw import A02YYUW
import time
import network
import espnow
import machine
import bmp280
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD


#if the machine is powered off and on check for an updated software version
if (machine.reset_cause() == 1):
       firmware_url = "https://github.com/blackshoals/watertanklevels/main/controller/"
       ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "pumpcontroller.py")
       ota_updater.download_and_install_update_if_available()
else:
       pass

cycle_time = 65  # seconds
sensor_send_interval = 5  # seconds
pump_check_interval = 30 # minutes
pump_run_time = 20 #minutes
reboot_delay = 5  # seconds
display_mac = b'\x3c\x84\x27\xc0\xfa\x58'
sensor_mac = b'\xb0\xb2\x1c\x50\xad\x20'
tank_offset = 5  # space between water surface when full and sensor in cm
tank_height = 40  # total height from bottom to sensor in cm
upper_tank_message = 0 #initialize before receiving an ESP-NOW message
sensor_timer_zero = time.ticks_ms() #initiate the interval timer for performing tasks
pump_timer_zero = time.ticks_ms()
upper_tank_receive_timestamp = time.ticks_ms()
pump_cycle_limiter = time.ticks_ms()
pump_cycle_count = 0
       
# ESP32 - Pin assignment for BMP280
# bus = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=10000)
# bmp = BMP280(bus)
# bmp.use_case(BMP280_CASE_WEATHER)

# Water pump Relay
#pump_relay = Pin(32, mode=Pin.OUT)

def reboot(delay = reboot_delay):
 #  print a message and give time for user to pre-empt reboot
 #  in case we are in a (battery consuming) boot loop
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
 #  or just machine.deepsleep(delay) or lightsleep()
    time.sleep(delay)
    machine.reset()

def read_tank_percentage():  # Read the local tank sensor
    sensor = A02YYUW()
    while True:
        distance = sensor.read()
        time.sleep_ms(50)
        if distance is not None: #take readings until one is found
            distance = round(distance/10)          # tank measurement in cm
            tank_percentage = round((1-(distance-tank_offset)/tank_height) *100)
            return tank_percentage
            break
        else:
            pass

def recv_cb(e):  # Callback function to handle incoming ESP-NOW messages
    global upper_tank_message
    while True:  # Process all messages in the buffer
        mac, msg = e.irecv(0)  # Non-blocking read
        if mac is None:
            return
        # Assuming the message contains the new sensor value
        upper_tank_message = msg.decode('utf-8')


#main program body
try:
    print ('you have 5 seconds to do Ctrl-C if you want to edit the program')
    time.sleep(5)

    #establish ESP-NOW
    print('Initializing...')
    ap = network.WLAN(network.AP_IF) #turn off the AP
    ap.active(False)
    sta = network.WLAN(network.STA_IF) #set station mode
    sta.active(True)

    e = espnow.ESPNow()
    e.active(True)
    e.config(timeout_ms=cycle_time * 1000)
    e.add_peer(display_mac)

    # Register the callback
    e.irq(recv_cb)
    
    while True:
        
        #Compile the tank sensor reading and send them to the display at the send interval
        if time.ticks_diff(time.ticks_ms(), sensor_timer_zero) >= (sensor_send_interval * 1000):# if time has reached the send interval
            lower_tank_percentage = ("L"+str(read_tank_percentage())) # read connected water level sensor
            upper_tank_percentage = ("U"+str(upper_tank_message)) # convert received message

            print ("Upper Tank: ",upper_tank_percentage, " %")
            print ("Lower Tank: ",lower_tank_percentage, " %")
            
            e.send(display_mac, upper_tank_percentage, False)
            time.sleep_ms(50)
            e.send(display_mac, lower_tank_percentage, False)
            
            sensor_timer_zero = time.ticks_ms()  # Reset the interval timer
        else:
            pass
        
        if time.ticks_diff(time.ticks_ms(), pump_cycle_limiter) >= (24 * 60 * 60 *1000): #reset the pump cycle counter every 24 hours
            pump_cycle_count = 0
        else:
            pass

           
        # Check the temperature and tank levels and start the pump if necessary
#         if ((time.ticks_diff(time.ticks_ms(), pump_timer_zero) >= (pump_check_interval * 60 *1000))
#            and (time.ticks_diff(time.ticks_ms(), upper_tank_receive_timestamp) <= (2 * 60 * 60 *1000))
#            and (pump_cycle_count <= 4)):
#                #start the pump at a certain interval
#                #check that the tank reading is less < 2 hours old
#                # limit pumping to 4 cycles per 24 hours
#   
#             print("Checking to start pump")
#             if bmp.temperature >=5: #check the BMP280 to make sure it is warm enough to start the pump
#                 print(" Temperature is above 5 degrees ")
#                 if ((int(upper_tank_percentage[1:]) < 80 and int(upper_tank_percentage[1:]) != 0)
#                 and (int(lower_tank_percentage[1:]) > 40)):
#                         pump_relay.on()
#                         print("Pump Relay On")
#                         time.sleep(pump_run_time*60)
#                         pump_relay.off()
#                         print("Pump Relay Off")
#                         pump_cycle_count += 1
#                         pump_timer_zero = 0 #reset the pump timer
#                 else:
#                     pass
#                       
#             else:
#                 pass
#           
#         else:
#             pass
                                     
            
        # Small delay to prevent CPU overload
        time.sleep_ms(50)
        
except KeyboardInterrupt as err:
    raise err #  use Ctrl-C to exit to micropython repl
except Exception as err:
    print ('Error during execution:', err)
    reboot()
