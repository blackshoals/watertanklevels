import network
import urequests
import os
import json
import machine
import time

class OTAUpdater:
    """ This class handles OTA updates. It connects to the Wi-Fi, checks for updates, downloads and installs them."""
    def __init__(self, ssid, password, repo_url, filename):
        self.filename = filename
        self.ssid = ssid
        self.password = password
        self.repo_url = repo_url
        if "www.github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("www.github", "raw.githubusercontent")
        elif "github.com" in self.repo_url:
            print(f"Updating {repo_url} to raw.githubusercontent")
            self.repo_url = self.repo_url.replace("github", "raw.githubusercontent")
        self.version_url = self.repo_url + 'version.json'
        print(f"version url is: {self.version_url}")
        self.firmware_url = self.repo_url + filename

        # get the current version (stored in version.json)
        if 'version.json' in os.listdir():
            with open('version.json') as f:
                self.current_version = int(json.load(f)['version'])
            print(f"Current device firmware version is '{self.current_version}'")
        else:
            self.current_version = 0
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)

    def connect_wifi(self):
        """ Connect to Wi-Fi."""
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(self.ssid, self.password)

        start_time = time.ticks_ms()

        while not sta_if.isconnected() and time.ticks_diff(time.ticks_ms(), start_time) < 20000:
            print('.', end="")
            time.sleep(0.25)

        if sta_if.isconnected():
            print(f'\nConnected to WiFi, IP is: {sta_if.ifconfig()[0]}')
            return True
        else:
            print('\nFailed to connect to WiFi within 20 seconds.')
            sta_if.active(False)
            return False

    def fetch_latest_code(self) -> bool:
        """ Fetch the latest code from the repo, returns False if not found."""
        response = urequests.get(self.firmware_url)
        if response.status_code == 200:
            print(f'Fetched latest firmware code, status: {response.status_code}, -  {response.text}')

            # Save the fetched code to memory
            self.latest_code = response.text
            return True
        elif response.status_code == 404:
            print(f'Firmware not found - {self.firmware_url}.')
            return False

    def update_no_reset(self):
        """ Update the code without resetting the device."""
        # Save the fetched code and update the version file to the latest version.
        with open('latest_code.py', 'w') as f:
            f.write(self.latest_code)

        # Update the version in memory
        self.current_version = self.latest_version

        # Save the current version
        with open('version.json', 'w') as f:
            json.dump({'version': self.current_version}, f)

        # Free up some memory
        self.latest_code = None

    def update_and_reset(self):
        """ Update the code and reset the device."""
        print(f"Updating device... (Renaming latest_code.py to {self.filename})", end="")

        # Overwrite the old code.
        os.rename('latest_code.py', self.filename)

        # Restart the device to run the new code.
        print('Restarting device...')
        machine.reset()  # Reset the device to run the new code.

    def check_for_updates(self):
        """ Check if updates are available."""
        if self.connect_wifi():
            print(f'Checking for latest version... on {self.version_url}')
            response = urequests.get(self.version_url)

            data = json.loads(response.text)

            print(f"data is: {data}, url is: {self.version_url}")
            print(f"data version is: {data['version']}")

            self.latest_version = int(data['version'])
            print(f'latest version is: {self.latest_version}')

            # Compare versions
            newer_version_available = True if self.current_version < self.latest_version else False

            print(f'Newer version available: {newer_version_available}')
            return newer_version_available
        else:
            print("Ending connection attempts")
            return False

    def download_and_install_update_if_available(self):
        """ Check for updates, download and install them."""
        if self.check_for_updates():
            if self.fetch_latest_code():
                self.update_no_reset()
                self.update_and_reset()
        else:
            print('No new updates available.')

        # Disconnect from WiFi
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(False)
