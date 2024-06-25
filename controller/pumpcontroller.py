#Pump Controller V2

from a02yyuw import A02YYUW
import time
import _thread
import network
import espnow
import machine
import ustruct
import ahtx0
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

reboot_delay = 5  # seconds
display_mac = b'\x3c\x84\x27\xc0\xfa\x58'
sensor_mac = b'\xb0\xb2\x1c\x50\xad\x20'
display_awake_interval = 5 #match to sleep time on display
sensor_send_interval = 10  # seconds
pump_check_interval = 1 # minutes
pump_run_time = 1 #minutes per cycle
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
upper_tank_receive_timestamp = time.time()

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
 #  or just machine.deepsleep(delay) or lightsleep()
    time.sleep(delay)
    machine.reset()
    
def update_temperature_data():
    global temperature, humidity
    temperature = round(aht20.temperature, 1) - 3 #calibrate for temp
    humidity = round(aht20.relative_humidity)

def read_tank_percentage():  # Read the local tank sensor
    try:
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
    except Exception as err:
        print('Error reading the tank:', err)
        return None

# Start a new thread for sending tank info every 15 seconds for 5 minutes
def send_tanks_info():
        
        try:
            for i in range((display_awake_interval*60)/sensor_send_interval):
                
                print(upper_tank_percentage, lower_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state, temperature, humidity) 
                outgoing_msg_processing()
                time.sleep(sensor_send_interval)
                                
        except Exception as err:
            print('Error sending data:', err)
            return None
         
def get_sensor_signal():
    peers = esp_now.peers_table
    if sensor_mac in peers and peers[sensor_mac]:
        return peers[sensor_mac][0]
    return 0

def turn_on_pump():
    global pump_state
    pump_state = True
    pump_relay.value(1)  # Turn the pump relay on

def turn_off_pump():
    global pump_state
    pump_state = False
    pump_relay.value(0)  # Turn the pump relay off

def get_pump_status():
    return pump_state
            
def check_pump():            # Check the temperature and tank levels and start the pump if necessary
        
    global pump_cycle_count
    
    try:           
        if (time.time() - pump_cycle_limiter) >= (24 * 60 * 60): #reset the pump cycle counter every 24 hours
            pump_cycle_count = 0
        else:
            pass
               
        while True:
                
            if pump_auto_flag:
                print("Pump auto mode is on")
                print("Checking the pump conditions")
                
                if ((time.time() - upper_tank_receive_timestamp) <= (2 * 60 * 60)
                and (pump_cycle_count < pump_daily_cycles)
                and (temperature >= 5)):
                    
                    lower_tank_percentage = read_tank_percentage() # read connected water level sensor
                
                    if ((upper_tank_percentage < upper_tank_min)
                    and (upper_tank_percentage != 0)
                    and (lower_tank_percentage > lower_tank_min)):

                       #start the pump at a certain interval
                       #check that the tank reading is less < 2 hours old
                       # limit pumping to 4 cycles per 24 hours

                        print("Starting pump")           
                        turn_on_pump()
                        outgoing_msg_processing()
                        print("Pump Relay On")
                        time.sleep(pump_run_time*60)
                        turn_off_pump()
                        outgoing_msg_processing()
                        print("Pump Relay Off")
                        pump_cycle_count += 1
                        print("Pump_cycle_count ",pump_cycle_count)
                       
                    else:
                        pass
                else:
                    pass
            else:
                 print("Pump Auto Mode is off")
            
            time.sleep(pump_check_interval*60)
            
    except Exception as err:
        print('Error checking the pump:', err)
        return None
        
def recv_cb(esp_now):  # Callback function to handle incoming ESP-NOW messages- keep short

    while True:  # Process all messages in the buffer
        mac, msg = esp_now.irecv(0)  # Non-blocking read
    
        if mac is None:
            return
        # Assuming the message contains the new sensor value       
        else:
            incoming_msg_processing(mac,msg)

def outgoing_msg_processing():
    
        global lower_tank_percentage, upper_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state
        
        lower_tank_percentage = read_tank_percentage() # read connected water level sensor
        pump_state = get_pump_status()
        sensor_signal = get_sensor_signal()
                    
        send_message = bytearray(ustruct.pack('iiiibb',lower_tank_percentage, upper_tank_percentage, battery_voltage, sensor_signal, pump_auto_flag, pump_state ))
        esp_now.send(display_mac, send_message, True)

def incoming_msg_processing(mac,msg):
    
        global upper_tank_percentage
        global battery_voltage
        global pump_auto_flag
                                    
        if mac == sensor_mac:
            upper_tank_percentage, battery_voltage = ustruct.unpack('ii', msg)
            print("Message from remote sensor ")
            
        elif mac == display_mac:
            msg =msg.split(b'\x00')[0].decode('utf-8')
            print("Message display ", msg)
            if msg == "get_sensors":
                 _thread.start_new_thread(send_tanks_info, ())                       
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
            else:
                pass 
        else:
            pass
           
def initialize_espnow():
    try:
        #establish ESP-NOW
        print('Initializing...')
        sta = network.WLAN(network.STA_IF) #set station mode
        sta.active(True)

        esp_now = espnow.ESPNow()
        esp_now.active(True)
        esp_now.add_peer(display_mac)

        return esp_now
    
    except Exception as err:
        print('Error initializing ESP-NOW:', err)
        return None

#main program body    
try:
    
    f = open('auto_flag.txt') #read the stored state of the pump_auto_flag
    content= f.read().strip()   
    f.close()
    # Convert content to boolean
    if content == 'True':
        pump_auto_flag = True
    else:
        pump_auto_flag = False
                
    turn_off_pump() #make sure the pump turns off on a reboot
    
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
        
    #start a thread that checks the pump
    _thread.start_new_thread(check_pump, ())

    while True:
        update_temperature_data()
            
except KeyboardInterrupt as err:
    raise err #  use Ctrl-C to exit to micropython repl
except Exception as err:
    print ('Error during execution:', err)
    reboot()
