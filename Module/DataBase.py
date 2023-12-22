from utils.Config import Config
import pyodbc
import pandas as pd
import time


class DataBase():
    def __init__(self):
        self.config = Config()
        self.conn = None
        self.url = self.get_url()

    def connect(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except:
                pass
        for i in range(5):
            try:
                self.conn = pyodbc.connect(self.url)
                break
            except Exception as e:
                print("deneme: " + str(i))
                print("database bağlanamadı : " + str(e))
                self.conn = None
            time.sleep(1)
        return self.conn


    def test(self, data):
        conn = None
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
            except:
                pass
        url = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + data['db_file_path']
        for i in range(5):
            try:
                conn = pyodbc.connect(url)
                break
            except Exception as e:
                print("deneme: " + str(i))
                print("database bağlanamadı : " + str(e))
                conn = None
            time.sleep(1)
        return conn
    def get_url(self):
        return r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + self.config.database['db_file_path']

    def get_data(self, sql_query):
        columns=[]
        if self.conn is None:
            self.connect()
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [column.column_name for column in cursor.columns(table=self.config.database['table_name'])]
            cursor.close()
        except Exception as e:
            rows = None
            print("Sorgu hatası: " + str(e))

        try:
            if rows:
                time_column = self.config.database['time_column']
                df = pd.DataFrame.from_records(rows)
                df.columns=columns
                df = df[self.config.database['columns']]
                df[time_column] = pd.to_datetime(df[time_column])
                df = df.sort_values(by=time_column, ascending=False).reset_index(drop=True)
                df = df[(df[self.config.database['time_column']].isna() == False)]
                df=df.fillna(0)
                return df
        except Exception as e:
            print("dataframe cevirme hatası: " + str(e))
            return None

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            print("Database kapatılamadı: " + str(e))
