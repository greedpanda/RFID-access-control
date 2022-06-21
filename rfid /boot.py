# boot.py -- run on boot-up
from network import Bluetooth, WLAN
import json
import machine
import pycom
wlan = WLAN(mode=WLAN.STA)

pycom.heartbeat(False)

# Disable bluetooth to save power
bluetooth = Bluetooth()
bluetooth.deinit()

# Load WiFi info
with open('config.json') as f:
    config = json.load(f)

# WiFi connection
nets = wlan.scan()
for net in nets:
    if net.ssid == config['ssid']:
        print('Network found!')
        wlan.init(power_save=True)
        wlan.connect(net.ssid, auth=(net.sec, config['ssid_pass']), timeout=5000)
        while not wlan.isconnected():
            machine.idle() # save power while waiting
        print('WLAN connection succeeded!')
        break
