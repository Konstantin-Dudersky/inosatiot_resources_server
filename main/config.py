import yaml


class e:
    def __init__(self, label, influxdb_meas):
        self.label = label
        self.influxdb_meas = influxdb_meas


class Config:

    def __init__(self):
        with open('config.yaml') as stream:
            self._config = yaml.safe_load(stream)

        self.electricity = {}
        for item in self._config['electricity']:
            self.electricity[item['tag']] = e(label=item['label'], influxdb_meas=item['influxdb_meas'])

    def electricity_label_choices(self):
        choices = []
        for item in self._config['electricity']:
            choices.append((item['tag'], item['label']))
        choices.append(('----------', '──────────'))
        return choices

    def influxdb(self):
        return self._config['influxdb']
