# device-mqtt
Miflora devices  : Mqtt Auto discovery and publish functions
### Main
```Python
#!/usr/bin/python3

import time
from datetime import datetime
from socket import gethostname

from bleak import _logger as logger
import logging
import logging.handlers
import queue

from devicemqtt.util.config import Config
from devicemqtt.util.mqttprocess import Mqtt_process

from devicemqtt.util.bleakutil import get_near_devices
from devicemqtt.util.bleakutil import get_device_info
from devicemqtt.util.bleakutil import build_msg_pl
from devicemqtt.util.bleakutil import valid_miflora_mac
from devicemqtt.util.bleakutil import publish_discovery

devices_bt = {}
mac2name = {}


def on_old(self, address):

    if (address in self.near_devices.keys()) is False:
        return

    if (address in self._devices.keys()) is False:
        return

    self._logger.info("{}".format(self._sensors[address]))
    self._logger.info("Query {}".format(address))

    # get device info
    get_device_info(self._devices, address)

    if 'data_last' in self._devices[address].keys():
        msgpl = build_msg_pl(self._devices, address)
        msgpl['from'] = gethostname()
        dumpmsg = "\n"
        for key,val in msgpl.items():
            dumpmsg += "{}: {}\n".format(key,val)
        print(msgpl)
        topic = get_path(address)
        self._logger.info("{}:{}".format(topic, dumpmsg))
        self.publish(topic, msgpl)


def get_path(address):
    baseTopic = "miflora"
    topic = "{}/sensor/{}/state"
    address = address.upper()
    name = ''
    if address in mac2name.keys():
        name = mac2name[address].lower().split("@")[0]
    else:
        name = address.lower().replace(":", "")
    topic = topic.format(baseTopic, name)
    return topic


def publish_discovery_filter(logger, mqtt_process, address, dev, mac2name, verbose):
    if address == "80:EA:CA:89:00:8C":
        logger.info("Ignore {}...".format(address))
        return
    publish_discovery(mqtt_process, address, dev, mac2name, verbose)


def main():
    global devices_bt
    global mac2name

    # return to main

    def retur2main(listener, handler, retval=0):
        listener.stop()
        handler.flush()
        return retval

    # set logging

    loglevel = logging.INFO
    que = queue.Queue(-1)  # no limit on size
    queue_handler = logging.handlers.QueueHandler(que)
    handler = logging.StreamHandler()
    listener = logging.handlers.QueueListener(que, handler)
    logger.addHandler(queue_handler)
    prmod = ('%(asctime)s : %(threadName)s/%(name)-12s'
             ' %(levelname)-8s %(message)s')
    formatter = logging.Formatter(prmod, datefmt='%d/%m/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.setLevel(loglevel)

    # logging start

    listener.start()
    logger.info(u'start')

    # get local devices

    devices_bt = get_near_devices(devices_bt, valid_miflora_mac)
    logger.info(u'scanning ended')

    # mqtt process

    config = Config(filePath="/opt/pi/params/miflora_mqtt.yaml")
    print(config.plant)
    mac2name = config.plant
    mqtt_process = Mqtt_process(config, logger)
    mqtt_process.on_old = on_old
    mqtt_process._devices = devices_bt
    mqtt_process.near_devices = devices_bt
    maxcount = 40

    count = maxcount

    for adr, dev in devices_bt.items():
        publish_discovery_filter(logger,
                                 mqtt_process,
                                 adr, dev,
                                 mac2name, True)

    while True:
        count += -1
        if count < 0:
            devices_bt = {}
            devices_bt = get_near_devices(devices_bt, valid_miflora_mac)
            mqtt_process.near_devices = devices_bt
            count = maxcount
            for adr, dev in mqtt_process.near_devices.items():
                logger.info("{}: {} dBm".format(adr, dev['rssi']))
                publish_discovery_filter(logger,
                                         mqtt_process,
                                         adr, dev,
                                         mac2name, False)
            logger.info(u'scanning ended')
        client = mqtt_process.get_client()
        if mqtt_process.get_data() is False:
            print(mqtt_process.sensors)
            print("Stop...")
            client.loop_stop()
            logger.info(u'stop')
            return retur2main(listener, handler)
        client.loop_stop()
        mqtt_process.test_sensors()
        try:
            time.sleep(10)  # wait
        except KeyboardInterrupt as err:
            print(mqtt_process.sensors)
            print("Stop...")
            logger.info(u'stop')
            return retur2main(listener, handler)


if __name__ == '__main__':
    exit(main())
```
### Config file
```
config:
  age_max_sec: 600
  mqtt:
    broker_address: 192.168.0.5
    pass: password
    port: 1883
    topic: miflora/sensor/+/state
    user: admin
  plant:
    80:EA:CA:89:00:8C: Rosier@BalconJardin
    80:EA:CA:89:07:34: DracaenaFragrans@Salon
    80:EA:CA:89:0B:AF: CyclamenCarre@BalconRue
    80:EA:CA:89:0C:CB: DracaenaMarginata3@Salon
    C4:7C:8D:64:3F:93: Erable@BalconRue
    C4:7C:8D:64:40:77: DracaenaMarginata@Salon
    C4:7C:8D:65:B1:1D: Stephanotis@Salon
    C4:7C:8D:6B:C5:58: DypsisLutescens@Salon
    C4:7C:8D:6C:13:2D: CyclamenRue@BalconRue
```
