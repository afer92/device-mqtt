#!/usr/bin/python3

import time
from datetime import datetime

import asyncio
import bleak
from bleak import BleakScanner
from bleak import BleakClient
from bleak import _logger as logger
import re


# ================= bleak ==================
_BYTE_ORDER = 'little'

_CMD_BLINK_LED = bytes([0xfd, 0xff])
_CMD_REAL_TIME_READ_INIT = bytes([0xa0, 0x1f])
_CMD_HISTORY_READ_INIT = bytes([0xa0, 0x00, 0x00])
_CMD_HISTORY_READ_SUCCESS = bytes([0xa2, 0x00, 0x00])
_CMD_HISTORY_READ_FAILED = bytes([0xa3, 0x00, 0x00])

_UUID_NAME = "00002a00-0000-1000-8000-00805f9b34fb"
_UUID_FIRM_BATT = "00001a02-0000-1000-8000-00805f9b34fb"
_UUID_TIME = "00001a12-0000-1000-8000-00805f9b34fb"
_UUID_TEMPS_REEL_ACTIVATE = "00001a00-0000-1000-8000-00805f9b34fb"
_UUID_TEMPS_REEL_DATA = "00001a01-0000-1000-8000-00805f9b34fb"

_UUID_HISTO_ACTIVATE = "00001a10-0000-1000-8000-00805f9b34fb"
_UUID_HISTO_DATA_READ = "00001a11-0000-1000-8000-00805f9b34fb"
# ================= /bleak ==================


def valid_miflora_mac(mac):

    refilter = r"(80:EA:CA)|(C4:7C:8D):[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}"
    pat = re.compile(refilter)
    """Check for valid mac adresses."""
    if not pat.match(mac.upper()):
        return False
    return True


def get_near_devices(devices, valid_mac):
    nowTime = datetime.now()

    async def scan():
        dev = await BleakScanner.discover()
        for d in dev:
            # print(d)
            if valid_mac(d.address):
                if d.address not in devices.keys():
                    devices[d.address] = {}
                    devices[d.address]['name'] = d.name
                    devices[d.address]['tview'] = nowTime
                    devices[d.address]['tinit'] = nowTime
                    devices[d.address]["rssi"] = d.rssi
                    print(d, "New")
                else:
                    devices[d.address]['tview'] = nowTime
    asyncio.run(scan())
    return devices


async def read_data(devices, address, loop):

    def disconnect_callback(client):
        print("Disconnected callback called!")
        # loop.call_soon_threadsafe(client.disconnected_event.set)

    # get event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if str(e).startswith('There is no current event loop in thread'):
            loop = asyncio.new_event_loop()
        else:
            print(e)
            return devices

    # connect to device

    try:
        client = BleakClient(address,
                             disconnect_callback=disconnect_callback,
                             loop=loop)
        x = await client.connect(timeout=10.0)

    except (bleak.exc.BleakError,
            bleak.exc.BleakDBusError,
            asyncio.exceptions.TimeoutError) as err:
        print(err)
        # loop.close()
        return

    # get infos

    value = await client.read_gatt_char(_UUID_NAME)
    print("====================")
    print("Address: {}".format(address))
    print("Name:", ''.join(map(chr, value)))

    value = await client.read_gatt_char(_UUID_FIRM_BATT)
    print("Firmware version:", ''.join(map(chr, value[2:])))
    print("Battery level:", value[0], "%")
    devices[address]['battery'] = value[0]
    devices[address]['firmware'] = ''.join(map(chr, value[2:]))

    # calcul de la valeur moyenne avant/après pour être au plus juste
    # la comparaison epch / heure système est utile ensuite
    #    pour la lecture de l'historique
    start = time.time()
    value = await client.read_gatt_char(_UUID_TIME)
    print("Seconds since boot:", int.from_bytes(value, _BYTE_ORDER))
    wall_time = (time.time() + start) / 2

    epoch_offset = int.from_bytes(value, _BYTE_ORDER)
    epoch_time = wall_time - epoch_offset

    # activation temps réel
    await client.write_gatt_char(_UUID_TEMPS_REEL_ACTIVATE,
                                 _CMD_REAL_TIME_READ_INIT,
                                 response=True)

    # lecture des données temps réel
    value = await client.read_gatt_char(_UUID_TEMPS_REEL_DATA)

    temperature = int.from_bytes(value[:2], _BYTE_ORDER) / 10.0
    light = int.from_bytes(value[3:7], _BYTE_ORDER)
    moisture = value[7]
    conductivity = int.from_bytes(value[8:10], _BYTE_ORDER)
    print("===== Real Time =====")
    print("Temperature:", temperature, "°C")
    print("Light:", light, " lux")
    print("Moisture:", moisture, "%")
    print("Fertility:", conductivity, "µS/cm")
    devices[address]['data_last'] = {}
    devices[address]['data_last']['tget'] = datetime.now()
    devices[address]['data_last']['temperature'] = temperature
    devices[address]['data_last']['light'] = light
    devices[address]['data_last']['moisture'] = moisture
    devices[address]['data_last']['conductivity'] = conductivity

    print("====================")

    await client.disconnect()

    await asyncio.sleep(0.25)

    return devices


def get_device_info(devices, address):

    # get event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if str(e).startswith('There is no current event loop in thread'):
            loop = asyncio.new_event_loop()
        else:
            print(e)
            loop.close()
            return devices

    # get infos

    try:
        loop.run_until_complete(read_data(devices, address, loop))

    except bleak.exc.BleakDBusError as err:
        print(err)
        loop.close()
        return

    time.sleep(1)
    loop.close()
    return devices


def build_msg_pl(devices, address):
    msg = {}
    msg['sensor'] = address
    msg['dtmsg'] = u'{}'.format(datetime.now())[:19].replace(' ', 'T')
    for info in ('rssi', 'battery', 'firmware', 'moisture', 'conductivity'):
        if info in devices[address].keys():
            msg[info] = devices[address][info]
    for info in ('tget', 'temperature', 'light', 'moisture', 'conductivity'):
        if info in devices[address]['data_last'].keys():
            if isinstance(devices[address]['data_last'][info], datetime):
                # u'{}'.format(devices[address]['data_last'][info])[:19].replace(' ', 'T')
                # msg[info] = devices[address]['data_last'][info]
                msg[info] = u'{}'.format(devices[address]['data_last'][info])[:19].replace(' ', 'T')
            else:
                msg[info] = devices[address]['data_last'][info]
    return msg


def get_name(address, mac2name):
    if address in mac2name.keys():
        return mac2name[address].split("@")[0]
    else:
        return address.upper().replace(":", "")


def get_unique_id(address):
    return address.lower().replace(":", "")


def get_path_discovery(address, mac2name):
    baseTopic = "homeassistant"
    topic = "{}/sensor/{}"
    name = ''
    if address in mac2name.keys():
        name = mac2name[address].lower().split("@")[0]
    else:
        name = address.lower().replace(":", "")
    topic = topic.format(baseTopic, name)
    return topic


def publish_discovery(self, address, device, mac2name, verbose):
    msg = {}
    msg["name"] = get_name(address, mac2name).lower()
    msg["unique_id"] = get_unique_id(address)
    msg["state_topic"] = "miflora/sensor/{}/state".format(msg["name"])
    msg["device"] = {}
    msg["device"]["identifiers"] = [("MiFlora" + msg["unique_id"]), ]
    msg["device"]["connections"] = [["mac", address.lower()]]
    msg["device"]["manufacturer"] = "Xiaomi"
    msg["device"]["name"] = get_name(address, mac2name)
    msg["device"]["model"] = "MiFlora Plant Sensor (HHCCJCY01)"
    msg["device"]["sw_version"] = "3.3.5"
    # msg["device"]["sw_version"] = device['firmware']
    msg["expire_after"] = "3600"

    msg_light = msg
    topic = get_path_discovery(address, mac2name) + "/light/config"
    msg_light["name"] = get_name(address, mac2name) + " Light"
    msg_light["unique_id"] = get_unique_id(address) + "-light"
    msg_light["unit_of_measurement"] = "lux"
    msg_light["device_class"] = "illuminance"
    msg_light["state_class"] = "measurement"
    msg_light["value_template"] = "{{ value_json.light }}"
    self.publish(topic, msg_light)

    msg_temp = msg
    topic = get_path_discovery(address, mac2name) + "/temperature/config"
    msg_temp["name"] = get_name(address, mac2name) + " Temperature"
    msg_temp["unique_id"] = get_unique_id(address) + "-temperature"
    msg_temp["unit_of_measurement"] = "°C"
    msg_temp["device_class"] = "temperature"
    msg_temp["state_class"] = "measurement"
    msg_temp["value_template"] = "{{ value_json.temperature }}"
    self.publish(topic, msg_temp)

    msg_moist = msg
    topic = get_path_discovery(address, mac2name) + "/moisture/config"
    msg_moist["name"] = get_name(address, mac2name) + " Moisture"
    msg_moist["unique_id"] = get_unique_id(address) + "-moisture"
    msg_moist["unit_of_measurement"] = "%"
    msg_moist["device_class"] = "humidity"
    msg_moist["state_class"] = "measurement"
    msg_moist["value_template"] = "{{ value_json.moisture }}"
    self.publish(topic, msg_moist)

    msg_conduc = msg
    topic = get_path_discovery(address, mac2name) + "/conductivity/config"
    msg_conduc["name"] = get_name(address, mac2name) + " Conductivity"
    msg_conduc["unique_id"] = get_unique_id(address) + "-conductivity"
    msg_conduc["unit_of_measurement"] = "µS/cm"
    msg_conduc["state_class"] = "measurement"
    msg_conduc["value_template"] = "{{ value_json.conductivity }}"
    self.publish(topic, msg_conduc)

    msg_battery = msg
    topic = get_path_discovery(address, mac2name) + "/battery/config"
    msg_battery["name"] = get_name(address, mac2name) + " battery"
    msg_battery["unique_id"] = get_unique_id(address) + "-battery"
    msg_battery["unit_of_measurement"] = "%"
    msg_battery["device_class"] = "battery"
    msg_battery["state_class"] = "measurement"
    msg_battery["value_template"] = "{{ value_json.battery }}"
    self.publish(topic, msg_battery)

    msg_rssi = msg
    topic = get_path_discovery(address, mac2name) + "/rssi/config"
    msg_rssi["name"] = get_name(address, mac2name) + " RSSI"
    msg_rssi["unique_id"] = get_unique_id(address) + "-rssi"
    msg_rssi["unit_of_measurement"] = "dBm"
    msg_rssi["state_class"] = "measurement"
    msg_rssi["value_template"] = "{{ value_json.rssi }}"
    self.publish(topic, msg_rssi)

    if verbose:
        print("  {}:".format(get_name(address, mac2name)))
        print("    sensors:")
        print("      brightness: sensor.{}_light".format(get_name(address, mac2name).lower()))
        print("      temperature: sensor.{}_temperature".format(get_name(address, mac2name).lower()))
        print("      moisture: sensor.{}_moisture".format(get_name(address, mac2name).lower()))
        print("      conductivity: sensor.{}_conductivity".format(get_name(address, mac2name).lower()))
        print("      battery: sensor.{}_battery".format(get_name(address, mac2name).lower()))
        print("      rssi: sensor.{}_rssi".format(get_name(address, mac2name).lower()))


def main():
    devices_bt = {}
    devices_bt = get_near_devices(devices_bt, valid_miflora_mac)
    for address, device in devices_bt.items():
        get_device_info(devices_bt, address)
        print("{}:\n{}".format(address, device))
        if 'data_last' in devices_bt[address].keys():
            msgpl = build_msg_pl(devices_bt, address)
            print(msgpl)
    return 0


if __name__ == '__main__':
    exit(main())
