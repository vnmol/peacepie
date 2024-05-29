
class SeriesAdmin:

    def __init__(self):
        self.series = {}

    def next(self, name):
        res = self.series.get(name)
        if not res:
            res = 0
            self.series[name] = res
        self.series[name] = res + 1
        return res


instance = SeriesAdmin()
