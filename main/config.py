import yaml


class Config:

    def __init__(self):
        with open('config.yaml') as stream:
            self._config = yaml.safe_load(stream)

    def electricity(self):
        return self._config['electricity']

    def electricity_name_choices(self):
        choices = []
        for item in self._config['electricity']:
            choices.append((item['influxdb_meas'], item['name']))
        return choices
