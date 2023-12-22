from utils.Config import Config


class RealTimeData:
    def __init__(self):
        self.config = Config()

    def data(self, df, columns):
        last_data = []
        date_str = df[self.config.database['time_column']].dt.strftime('%Y-%m-%d %H:%M:%S')
        values = df[columns].astype(float)
        for col in columns:
            value_data = [{"name": date, "value": [date, value]} for date, value in zip(date_str, values[col])]
            structure = {
                "name": col,
                "type": 'line',
                "showSymbol": 0,
                "data": value_data
            }
            last_data.append(structure)
        return last_data
