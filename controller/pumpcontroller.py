#Pump Controller V1

from a02yyuw import A02YYUW
import time
import network
import espnow
import machine
import ujson
import bmp280
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

cycle_time = 65  # seconds
sensor_send_interval = 15  # seconds
pump_check_interval = 30 # minutes
pump_run_time = 20 #minutes
reboot_delay = 5  # seconds
display_mac = b'\x3c\x84\x27\xc0\xfa\x58'
sensor_mac = b'\xb0\xb2\x1c\x50\xad\x20'
tank_offset = 5  # space between water surface when full and sensor in cm
tank_height = 40  # total height from bottom to sensor in cm
lower_tank_percentage = 0 #initialize before receiving an ESP-NOW message
upper_tank_percentage = 0 #initialize before receiving an ESP-NOW message
battery_voltage = 0 #initialize before receiving an ESP-NOW message
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

def send_tanks_info(esp_now):
            global lower_tank_percentage
            global upper_tank_percentage
            global battery_voltage
    
            lower_tank_percentage = read_tank_percentage() # read connected water level sensor
                              
            send_message = ({"lower_tank_percentage":lower_tank_percentage,"upper_tank_percentage":upper_tank_percentage,"battery_voltage":battery_voltage})           
            esp_now.send(display_mac,ujson.dumps(send_message), True)
                
            print("Upper :", send_message["upper_tank_percentage"]," %")
            print("Lower :", send_message["lower_tank_percentage"]," %")
            print("Battery :", send_message["battery_voltage"]," %")


def recv_cb(esp_now):  # Callback function to handle incoming ESP-NOW messages
    global upper_tank_percentage
    global battery_voltage
    while True:  # Process all messages in the buffer
        mac, msg = esp_now.irecv(0)  # Non-blocking read
        if mac is None:
            return
        # Assuming the message contains the new sensor value
        message = ujson.loads(msg)
        upper_tank_percentage = message['upper_tank_percentage']
        battery_voltage = message['battery_voltage']                    
            
def initialize_espnow():
    try:
        #establish ESP-NOW
        print('Initializing...')
        sta = network.WLAN(network.STA_IF) #set station mode
        sta.active(True)

        esp_now = espnow.ESPNow()
        esp_now.active(True)
        esp_now.config(timeout_ms=cycle_time * 1000)
        esp_now.add_peer(display_mac)


        return esp_now
    
    except Exception as err:
        print('Error initializing ESP-NOW:', err)
        return None


#main program body
try:
        #if the machine is powered off and on check for an updated software version
    if (machine.reset_cause() == 1):
        print ('you have 5 seconds to do Ctrl-C if you want to edit the program')
        time.sleep(5)
        #if the machine is powered off and on check for an updated software version
        firmware_url = "https://github.com/blackshoals/watertanklevels/main/controller/"
        ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "pumpcontroller.py")
        ota_updater.download_and_install_update_if_available()
    else:
           pass
        
    esp_now = initialize_espnow()
    if esp_now is None:
           reboot()
    else:
        pass

    # Register the callback
    esp_now.irq(recv_cb)

    while True:
        
        #Compile the tank sensor reading and send them to the display at the send interval
        if time.ticks_diff(time.ticks_ms(), sensor_timer_zero) >= (sensor_send_interval * 1000):# if time has reached the send interval
            send_tanks_info(esp_now)                    
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
