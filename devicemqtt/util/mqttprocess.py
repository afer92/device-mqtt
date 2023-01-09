#!/usr/bin/python3

import paho.mqtt.client as mqtt
import time
import json
from datetime import datetime
import time
from dateutil.parser import parse

import logging
import logging.handlers
import queue

from bleak import _logger as logger

# from config.config import Config
from devicemqtt.util.config import Config


DEBUG = False


class Mqtt_process:

    def _on_old_base(address):
        self._logger.info("{}".format(self._sensors[address]))

    def __init__(self, config, logger):
        self._config = config
        self._client = None
        self._sensors = {}
        self._client_id = 'python-mqtt-{random.randint(0, 1000)}'
        self._logger = logger
        self._on_old = self._on_old_base
        self._devices = {}
        self._near_devices = {}

    def on_message(client, self, message):
        strmsg = str(message.payload.decode("utf-8"))
        topics = message.topic.split("/")
        infos = json.loads(strmsg)
        if 'dtmsg' not in infos.keys():
            return
        if 'sensor' in infos.keys():
            age = self.get_age(infos['dtmsg'])
            infos['agesec'] = age
            infos['name'] = topics[2]
            if infos['sensor'] in self._sensors.keys():
                olddata = self._sensors[infos['sensor']]
                if 'dtmsg' in olddata.keys():
                    ageold = self.get_age(olddata['dtmsg'])
                    if age < ageold:
                        self._logger.info("msg received: {}\t{} old: {}sec".format(topics[2], age, ageold))
                        if DEBUG:
                            print(olddata)
                            print(infos)
                            print("Age old : {} Age new : {}".format(ageold, age))
                        self._sensors[infos['sensor']] = infos
                    else:
                        self._sensors[infos['sensor']]['agesec'] = ageold
            else:
                self._sensors[infos['sensor']] = infos

    def test_sensors(self):
        for address, sensor in self._sensors.items():
            if DEBUG:
                print(address, 'agesec', sensor['agesec'])
            if sensor['agesec'] > self._config.age_max_sec:
                self._on_old(self, address)
                # self._logger.info("{}".format(sensor))

    def get_client(self, on_message=on_message):
        # print("creating new instance")
        self._client = mqtt.Client(self._client_id)  # create new instance
        self._client.username_pw_set(self._config.mqtt_user,
                                     self._config.mqtt_pass)
        self._client.user_data_set(self)
        self._client.on_message = on_message  # attach function to callback
        if DEBUG:
            print("connecting to broker")
        self._client.connect(self._config.broker_address,
                             port=self._config.mqtt_port,
                             keepalive=60)  # connect to broker
        self._logger.debug("creating new instance")
        self._client.loop_start()  # start the loop
        return self._client

    def get_age(self, dtmsgstr: str):
        age = datetime.now() - parse(dtmsgstr)
        if DEBUG:
            print("{} <--> {}  {} sec".format(datetime.now(),
                                              parse(dtmsgstr),
                                              age.seconds))
        return age.seconds

    def get_data(self):
        self._logger.debug("Subscribing to topic {}".format(self._config.mqtt_topic))
        self._client.unsubscribe(self._config.mqtt_topic)
        self._client.subscribe(self._config.mqtt_topic)
        try:
            time.sleep(10)
        except KeyboardInterrupt as err:
            return False
        return True

    def publish(self, topic, payload):
        self._client = mqtt.Client(self._client_id)
        self._client.username_pw_set(self._config.mqtt_user,
                                     self._config.mqtt_pass)
        self._client.connect(self._config.broker_address,
                             port=self._config.mqtt_port,
                             keepalive=60)  # connect to broker
        pl = json.dumps(payload)
        # result = client.publish(topic, '{}'.format(payload).replace("'", '"'))
        result = self._client.publish(topic, pl, qos=0, retain=True)
        time.sleep(0.5)  # some slack for the publish roundtrip and callback function
        # result: [0, 1]
        status = result[0]
        if status == 0:
            pass
            # print("Send `{payload}` to topic `{topic}`".format(payload=payload, topic=topic))
        else:
            print("Failed to send message to topic {topic}".format(topic=topic))

    @property
    def on_old(self):
        return self._on_old

    @on_old.setter
    def on_old(self, value):
        self._on_old = value

    @property
    def sensors(self):
        return self._sensors

    @property
    def client(self):
        self._client = mqtt.Client(self._client_id)
        return self._client

    @property
    def near_devices(self):
        return self._near_devices

    @near_devices.setter
    def near_devices(self, value):
        self._near_devices = value


def on_old(self, address):
    self._logger.info("on_old")
    return


def main():

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

    config = Config()
    print(config.mqtt)
    mqtt_process = Mqtt_process(config, logger)
    while True:
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
