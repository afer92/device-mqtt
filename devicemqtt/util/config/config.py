#!/usr/bin/python3

from pathlib import Path
import yaml


class Config:

    def __init__(self, filePath=None):
        if filePath is None:
            pgmpath = Path(__file__).parent.absolute()
            filePath = "{}/{}.yaml".format(pgmpath, Path(__file__).stem)
        configf = open(filePath, 'r')
        self._config = yaml.load(configf, Loader=yaml.FullLoader)
        configf.close()
        self._update = False
        if (self._config is None) or (self._config['config'] is None):
            self._update = True
            self._config = {}
            self._config['config'] = {}
            self._config['config']['mqtt'] = {}
        if ('config' in self._config.keys()) is False:
            self._update = True
            self._config = {}
            self._config['config'] = {}
            self._config['config']['mqtt'] = {}
        if ('mqtt' in self._config['config'].keys()) is False:
            self._update = True
            self._config['config']['mqtt'] = {}
        if ('topic' in self._config['config']['mqtt'].keys()) is False:
            self._update = True
            self._config['config']['mqtt']['topic'] = "miflora/sensor/+/state"
        if ('broker_address' in self._config['config']['mqtt'].keys()) is False:
            self._update = True
            self._config['config']['mqtt']['broker_address'] = "192.168.0.5"
        if ('port' in self._config['config']['mqtt'].keys()) is False:
            self._update = True
            self._config['config']['mqtt']['port'] = 1883
        if ('mqtt_user' in self._config['config']['mqtt'].keys()) is False:
            self._update = True
            self._config['config']['mqtt']['user'] = "admin"
        if ('mqtt_pass' in self._config['config']['mqtt'].keys()) is False:
            self._update = True
            self._config['config']['mqtt']['pass'] = "password"
        if ('age_max_sec' in self._config['config'].keys()) is False:
            self._update = True
            self._config['config']['age_max_sec'] = 600
        if self._update:
            configf = open(filePath, 'w')
            yaml.dump(self._config, configf)
            configf.close()

    @property
    def config(self):
        return self._config

    @property
    def mqtt(self):
        return self._config['config']['mqtt']

    @property
    def plant(self):
        return self._config['config']['plant']

    @property
    def age_max_sec(self):
        return self._config['config']['age_max_sec']

    @property
    def broker_address(self):
        return self._config['config']['mqtt']['broker_address']

    @property
    def mqtt_user(self):
        return self._config['config']['mqtt']['user']

    @property
    def mqtt_pass(self):
        return self._config['config']['mqtt']['pass']

    @property
    def mqtt_port(self):
        return self._config['config']['mqtt']['port']

    @property
    def mqtt_topic(self):
        return self._config['config']['mqtt']['topic']


def main():
    config = Config()
    print(config.mqtt)
    mqtt_process = Mqtt_process(config)


if __name__ == '__main__':
    exit(main())
