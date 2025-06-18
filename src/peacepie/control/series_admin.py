
class SeriesAdmin:

    def __init__(self):
        self.series = {}

    def next(self, name):
        series = self.series.get(name)
        if not series:
            series = {'value': 0, 'max_value': 0}
            self.series[name] = series
        value = series.get('value')
        max_value = series.get('max_value')
        if max_value > 0:
            if value > max_value:
                value = 0
                series['value'] = value
        series['value'] = value + 1
        return value

    def set_value(self, name, value):
        series = self.series.get(name)
        if not series:
            self.series[name] = {'value': value, 'max_value': 0}
        else:
            series['value'] = value

    def set_max_value(self, name, max_value):
        series = self.series.get(name)
        if not series:
            self.series[name] = {'value': 0, 'max_value': max_value}
        else:
            series['max_value'] = max_value


instance = SeriesAdmin()
