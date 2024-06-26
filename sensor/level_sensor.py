#Water Tank Sensor V4

import time
import network
import espnow
import machine
import ustruct
from a02yyuw import A02YYUW
from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

reboot_delay = 5  # seconds
cycle_time = 60  # minutes
recharge_sleep = 1 #days
controller_mac = b'\xb0\xb2\x1c\x50\xb2\xb0'  # MAC address of peer1's wifi interface
tank_offset = 5  # space between water surface when full and sensor in cm
tank_height = 60  # total height from bottom to sensor in cm

# Initialize sensor object once
sensor = A02YYUW()
# Initialize the battery pins
adc_pin = machine.Pin(34, mode=machine.Pin.IN)
adc = machine.ADC(adc_pin)
adc.atten(machine.ADC.ATTN_11DB)

def reboot(delay=reboot_delay):
    print(f'Rebooting device in {delay} seconds (Ctrl-C to escape).')
    time.sleep(delay)
    machine.reset()

def read_tank_percentage():
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

def read_battery_voltage():
    calib_factor = 1 / 564
    raw = adc.read()
    battery_voltage = raw * calib_factor
    battery_voltage = int(((battery_voltage - 3.2) / (4.17 - 3.2)) * 100)
    return battery_voltage

def initialize_espnow():
    #establish ESP-NOW
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print('Initializing ESP-NOW :', attempt + 1, " of ", max_retries, "retries")
            sta = network.WLAN(network.STA_IF)
            sta.active(True)

            esp_now = espnow.ESPNow()
            esp_now.active(True)
            esp_now.add_peer(controller_mac)

            return esp_now
        
        except Exception as err:
            print('Error initializing ESP-NOW: %s', err)
            if attempt < max_retries - 1:
                print('Retrying in 5 seconds...')
                time.sleep(5)
            else:
                print('Failed to initialize ESP-NOW after %d attempts', max_retries)
                return None

def check_for_update():
    if machine.reset_cause() == machine.DEEPSLEEP_RESET:
        return  # Skip update check on wake from deep sleep

    print('Checking for updates...')
    firmware_url = "https://github.com/blackshoals/watertanklevels/main/sensor/"
    ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "level_sensor.py")
    ota_updater.download_and_install_update_if_available()

try:
    check_for_update()
    esp_now = initialize_espnow()
    if esp_now is None:
        reboot()

    # Initial read and send
    upper_tank_percentage = read_tank_percentage()
    battery_voltage = read_battery_voltage()

    if upper_tank_percentage is not None:
        send_message = ustruct.pack('ii', upper_tank_percentage, battery_voltage)
        esp_now.send(controller_mac, send_message, True)
        print("Sent Upper Tank:", upper_tank_percentage, "% Battery:", battery_voltage, "%")

    while True:
        # Read and send periodically
        upper_tank_percentage = read_tank_percentage()
        battery_voltage = read_battery_voltage()

        if battery_voltage < 20:
            print("Low battery voltage, sleeping...")
            machine.deepsleep(recharge_sleep * 24 * 60 * 60 * 1000)  # Sleep to recharge

        if upper_tank_percentage is not None:
            send_message = ustruct.pack('ii', upper_tank_percentage, battery_voltage)
            esp_now.send(controller_mac, send_message, True)
            print("Sent Upper Tank:", upper_tank_percentage, "% Battery:", battery_voltage, "%")

        machine.deepsleep(cycle_time * 60 * 1000)

except KeyboardInterrupt as err:
    raise err  # Use Ctrl-C to exit to MicroPython REPL
except Exception as err:
    print('Error during execution:', err)
    reboot()
