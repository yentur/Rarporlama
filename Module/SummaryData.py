from utils.Config import Config
import pandas as pd

class Summary:
    def __init__(self):
        self.config=Config()

    def total(self, df):
        print("------",df.columns)
        df[self.config.database['time_column']] = pd.to_datetime(df[self.config.database['time_column']])
        df = df.sort_values(by=self.config.database['time_column'])
        result = df.resample('H', on=self.config.database['time_column']).mean().sum()
        return result

    def calculate_summary_stats(self,df,index=None):
        df_without_time = df.drop(self.config.database['time_column'],axis=1)
        mean = df_without_time.mean()
        max_value = df_without_time.max()
        min_value = df_without_time.min()
        total = self.total(df)
        summary_df = pd.DataFrame({
            'Toplam': total,
            'Ortalama': mean,
            'Maksimum': max_value,
            'Minimum': min_value
        })
        return summary_df


