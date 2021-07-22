import yaml


class e:
    def __init__(self, label, influxdb_meas):
        self.label = label
        self.influxdb_meas = influxdb_meas


class eg:
    def __init__(self, label, formula):
        self.label = label
        self.formula = formula


class Config:

    def __init__(self):
        with open('config.yaml') as stream:
            self._config = yaml.safe_load(stream)

        self.e = {}
        for item in self._config['electricity']:
            self.e[item['tag']] = e(
                label=item['label'],
                influxdb_meas=item['influxdb_meas'])

        self.eg = {}
        for item in self._config['electricity_groups']:
            self.eg[item['tag']] = eg(
                label=item['label'],
                formula=item['formula'])

    def electricity_label_choices(self):
        choices = []
        for item in self.e:
            choices.append((item, self.e[item].label))
        choices.append(('----------', '──────────'))
        for item in self.eg:
            choices.append((item, self.eg[item].label))
        return choices

    def influxdb(self):
        return self._config['influxdb']
