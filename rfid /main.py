from lib.mqtt import MQTTClient
from lib.mfrc522 import MFRC522
from machine import Pin
import hashlib
import json
import pycom
import time
import ubinascii

open_door = Pin('P10', mode = Pin.OUT)

with open('config.json') as f:
    config = json.load(f)

# Admin is the only one authorized.
authorized = '0x03536fad'
logger = {}

# Status for each access attempt
# 0 = LOGOUT, 1 = LOGIN, 2 = UNAUTHORIZED
def status(uid):
    pycom.heartbeat(False)
    # insert uid if not present
    if uid not in logger:
        logger[uid] = 0

    if uid != authorized:
        print("Access denied, sending alert...")
        pycom.rgbled(0xff0000)
        logger[uid] = 2
    else:
        print("Authorized access of", uid)
        pycom.rgbled(0x00ff00)
        # open door signal lasts 1s according to lock specs
        open_door.value(1)
        time.sleep(1)
        open_door.value(0)
        if logger[uid] == 1:
            logger[uid] = 0
        else:
            logger[uid] = 1


# Set status and send uid:status to MQTT broker
def send_value(uid):
    status(uid)

    try:
        c.publish(topic_pub,'{"uid":'+ str(int(uid, 16)) +',"status":' + str(logger[uid]) +'}')
    except Exception as e:
        print('Failed to send! ', e)

# RFID reader
def do_read():

    # MFRC522(SCK, MOSI, MISO, RST, SDA)
    rdr = MFRC522('P23', 'P11', 'P14', 'P22', 'P9')

    try:
        while True:

            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:

                (stat, raw_uid) = rdr.anticoll()
                # Get UID
                uid = ("0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))

                if stat == rdr.OK:
                    print("Card detected - uid:", uid)
                    if rdr.select_tag(raw_uid) == rdr.OK:
                        key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                        if rdr.auth(rdr.AUTHENT1A, 8, key, raw_uid) == rdr.OK:
                            send_value(uid)
                            if logger[uid] == 2:
                                # 5sec timout for unauthorized attempt
                                time.sleep(5)
                            else:
                                time.sleep(1)
                            pycom.heartbeat(False)
                        else:
                            print("Authentication error")
                    else:
                        print("Failed to select tag")
                rdr.stop_crypto1()
    except KeyboardInterrupt:
        print("Bye")

# Placeholder function for needed callback
def sub_cb(topic, msg):
    print((topic, msg))

# MQTTServer topic declaration
topic_pub = 'access-control/'
topic_sub = 'access-control/log'
broker_url = config['hostname_mqtt']
client_name = ubinascii.hexlify(hashlib.md5(machine.unique_id()).digest()) # create a md5 hash of the pycom WLAN mac

c = MQTTClient(client_name,broker_url,user=config['user_mqtt'],password=config['pass_mqtt'], keepalive=3600)
c.connect()
c.set_callback(sub_cb)
c.subscribe(topic_sub)
do_read()
