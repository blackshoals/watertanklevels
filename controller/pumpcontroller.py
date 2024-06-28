#Pump Controller V5

import time
import asyncio
import network
import espnow
import machine
import ustruct
from a02yyuw import A02YYUW
import ahtx0
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

reboot_delay = 5  # seconds
display_mac = b'\x3c\x84\x27\xc0\xfa\x58'
sensor_mac = b'\xb0\xb2\x1c\x50\xad\x20'
display_awake_interval = 3 #match to sleep time on display
sensor_send_interval = 15  # seconds
pump_check_interval = 60 # minutes
pump_run_time = 20 #minutes per cycle
max_continuous_run_time = 30 #minutes
pump_cooldown_time = 15 #minutes
pump_daily_cycles = 2 #how many time cycles can run in 24 hours
pump_cycle_limiter = time.time()
pump_cycle_count = 0
pump_state = False #pump status
tank_offset = 5  # space between water surface when full and sensor in cm
tank_height = 40  # total height from bottom to sensor in cm
lower_tank_percentage = 0 #initialize before receiving an ESP-NOW message
lower_tank_min = 40 # the percentage to stop pumping from the lower tank
upper_tank_percentage = 0 #initialize before receiving an ESP-NOW message
upper_tank_min = 80 # the value to start pumping from the lower tank
battery_voltage = 0 #initialize before receiving an ESP-NOW message
sensor_signal = 0  #initialize before receiving an ESP-NOW message
temperature = 0 #initialize before receiving an ESP-NOW message
humidity = 0 #initialize before receiving an ESP-NOW message
upper_tank_receive_timestamp = time.time() # track how old the last sensor reading is
last_temperature_update = time.time()  # track the last temperature update time

#set up the AHT20 temp sensor and power it with Pin 23
pin_aht20power = machine.Pin(23, mode=machine.Pin.OUT, value=1)
i2c = machine.SoftI2C(scl=machine.Pin(21), sda=machine.Pin(22))
aht20 = ahtx0.AHT20(i2c)

# Water pump Relay
pump_relay = machine.Pin(5, mode=machine.Pin.OUT)

def reboot(delay = reboot_delay):
 #  print a message and give time for user to pre-empt reboot
 #  in case we are in a (battery consuming) boot loop
    print (f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
    time.sleep(delay)
    machine.reset()
    
async def update_temperature_data():
    #update temperature and humidity periodically
    global temperature, humidity
    while True:
        temperature = round(aht20.temperature, 1) - 3  # calibrate for temp
        humidity = round(aht20.relative_humidity)
        await asyncio.sleep(10)

def read_tank_percentage():
    # Read the local tank sensor
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

async def send_tanks_info():
    # send tank information to the display unit
    while True:
        for i in range((display_awake_interval*60)/sensor_send_interval):
            
            print(upper_tank_percentage, lower_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state, temperature, humidity) 
            outgoing_msg_processing()
            await asyncio.sleep(sensor_send_interval)
             
def get_sensor_signal():
    # get sensor signal strength from the remote sensor
    peers = esp_now.peers_table
    if sensor_mac in peers and peers[sensor_mac]:
        return peers[sensor_mac][0]
    return 0

def turn_on_pump():
    # Turn the pump relay on
    global pump_state
    pump_state = True
    pump_relay.value(1)  

def turn_off_pump():
    # Turn the pump relay off
    global pump_state
    pump_state = False
    pump_relay.value(0)  

def get_pump_status():
    # Get the current pump status
    return pump_state
            
async def check_pump():
    #run the pump a set # of intervals per 24 hours if: auto flag is On, the temperature is above 5 deg
    global pump_cycle_count, pump_cycle_limiter, lower_tank_percentage, last_pump_start_time, last_pump_stop_time
    
    while True:      
        current_time = time.time()
        
        # Reset daily cycle counter
        if (current_time - pump_cycle_limiter) >= (24 * 60 * 60):
            pump_cycle_count = 0
            pump_cycle_limiter = current_time
        
        if pump_auto_flag:
            print("Pump auto mode is on")
            print("Checking pump conditions")
            
            if ((current_time - upper_tank_receive_timestamp) <= (3 * 60 * 60)
                and (pump_cycle_count < pump_daily_cycles)
                and (temperature >= 5)
                and (current_time - last_pump_stop_time) >= (pump_cooldown_time * 60):
                
                lower_tank_percentage = read_tank_percentage()
                
                if ((upper_tank_percentage < upper_tank_min)
                    and (upper_tank_percentage != 0)
                    and (lower_tank_percentage > lower_tank_min)):

                    print("Starting pump")           
                    turn_on_pump()
                    last_pump_start_time = current_time
                    outgoing_msg_processing()
                    print("Pump Relay On")
                    
                    # Run pump with safety checks
                    while (current_time - last_pump_start_time) < (pump_run_time * 60):
                        await asyncio.sleep(60)  # Check every minute
                        current_time = time.time()
                        if (current_time - last_pump_start_time) >= (max_continuous_run_time * 60):
                            print("Maximum continuous run time reached. Stopping pump.")
                            break
                        
                        # Recheck conditions
                        lower_tank_percentage = read_tank_percentage()
                        if lower_tank_percentage <= lower_tank_min:
                            print("Lower tank level too low. Stopping pump.")
                            break
                    
                    turn_off_pump()
                    last_pump_stop_time = time.time()
                    outgoing_msg_processing()
                    print("Pump Relay Off")
                    pump_cycle_count += 1
                    print("Pump_cycle_count ", pump_cycle_count)
                       
            else:
                print(f"Pump not started. Cycles: {pump_cycle_count}, Temperature: {temperature}")
        else:
            print("Pump Auto Mode is off")
            
        await asyncio.sleep(pump_check_interval * 60)
        
async def recv_cb(esp_now):
    # Callback function to handle incoming ESP-NOW messages- keep short
    while True:  # Process all messages in the buffer
        mac, msg = esp_now.irecv(0)  # Non-blocking read   
        if mac is not None:
            asyncio.create_task(incoming_msg_processing(mac, msg))
        await asyncio.sleep(0.1)  # Yield to other tasks

def outgoing_msg_processing():
    # Process and send outgoing messages
    global lower_tank_percentage, upper_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state
    
    lower_tank_percentage = read_tank_percentage() # read connected water level sensor
    pump_state = get_pump_status()
    sensor_signal = get_sensor_signal()
                
    send_message = bytearray(ustruct.pack('iiiibb',lower_tank_percentage, upper_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state ))
    esp_now.send(display_mac, send_message, True)

async def incoming_msg_processing(mac,msg):
    # Process incoming messages
    global upper_tank_percentage, battery_voltage, pump_auto_flag
                                
    if mac == sensor_mac:
        upper_tank_percentage, battery_voltage = ustruct.unpack('ii', msg)
        print("Message from remote sensor ")
        
    elif mac == display_mac:
        msg =msg.split(b'\x00')[0].decode('utf-8')
        print("Message display ", msg)
        if msg == "get_sensors":
           asyncio.create_task(send_tanks_info())                      
        elif msg == "pump_on":
            turn_on_pump()
            outgoing_msg_processing()
        elif msg == "pump_off":
            turn_off_pump()
            outgoing_msg_processing()
        elif msg == "auto_on":
            pump_auto_flag = True
            f = open('auto_flag.txt', 'w') #store the auto_flag value
            f.write('True')
            f.close()
            outgoing_msg_processing()
        elif msg == "auto_off":
            pump_auto_flag = False
            f = open('auto_flag.txt', 'w') #store the auto_flag value
            f.write('False')
            f.close()
            outgoing_msg_processing()

def check_for_update():
    #check for updated firmware from Github
    if machine.reset_cause() == machine.DEEPSLEEP_RESET:
        return  # Skip update check on wake from deep sleep

    print('Checking for updates...')
    firmware_url = "https://github.com/blackshoals/watertanklevels/main/controller/"
    ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "pumpcontroller.py")
    ota_updater.download_and_install_update_if_available()

def initialize_espnow():
    #establish ESP-NOW
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print('Initializing ESP-NOW (attempt %d/%d)...', attempt + 1, max_retries)
            sta = network.WLAN(network.STA_IF)
            sta.active(True)

            esp_now = espnow.ESPNow()
            esp_now.active(True)
            esp_now.add_peer(display_mac)

            return esp_now
        
        except Exception as err:
            print('Error initializing ESP-NOW: %s', err)
            if attempt < max_retries - 1:
                print('Retrying in 5 seconds...')
                time.sleep(5)
            else:
                print('Failed to initialize ESP-NOW after %d attempts', max_retries)
                return None

async def feed_watchdog():
   # reset the system if it become unresponsive with a watchdog
    watchdog = WDT(timeout=600000)  # 10 minutes timeout
    while True:
        watchdog.feed()
        await asyncio.sleep(60)  # Feed every minute

async def main():
    # main program body    
    try:
        # Create tasks for asynchronous functions
        update_temp_task = asyncio.create_task(update_temperature_data())
        check_pump_task = asyncio.create_task(check_pump())
        watchdog_task = asyncio.create_task(feed_watchdog())

        # Run the event loop
        await asyncio.gather(update_temp_task, check_pump_task, watchdog_task)

    except KeyboardInterrupt as err:
        raise err #  use Ctrl-C to exit to micropython repl

    except Exception as err:
        print ('Error during execution:', err)
        reboot()

# Run the main coroutine
try:
    with open('auto_flag.txt', 'r') as f:
        content = f.read().strip()
    pump_auto_flag = content == 'True'
except Exception as err:
    print("Error reading auto_flag.txt:", err)
    pump_auto_flag = False

#make sure the pump turns off on a reboot            
turn_off_pump() 

#if the machine is powered off and on check for an updated software version
check_for_update()
    
esp_now = initialize_espnow()
if esp_now is None:
       reboot()

# Register the ESP-Now callback
asyncio.create_task(recv_cb(esp_now))

asyncio.run(main())


