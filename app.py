from flask import Flask, render_template, request
from flask import jsonify
from utils.Config import Config
from Module.DataBase import DataBase
from datetime import *
from Module.SummaryData import Summary
from Module.RealTimeData import RealTimeData
import pandas as pd
from utils.ConfigWrite import *
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import os
import time
import matplotlib.pyplot as plt
import glob

app = Flask(__name__, static_folder="./static", template_folder="./templates")

config = Config()
database = DataBase()
database.connect()
realTimeDate = RealTimeData()
table_name = config.database['table_name']
time_column = config.database['time_column']
summary = Summary()

main_page_index = 0
main_tablo_index = 0
cols = 0


@app.route('/')
@app.route('/main')
def index():
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM {table_name} WHERE {time_column} BETWEEN #{start_date}# AND #{end_date}#"
    df = database.get_data(sql_query=sql_query)
    tablo_data = summary.calculate_summary_stats(df=df).to_html()
    return render_template('mainpage.html', tablo_data=tablo_data)


@app.route('/get_info_data', methods=['GET', 'POST'])
def get_info_data():
    global main_tablo_index
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM {table_name} WHERE {time_column} BETWEEN #{start_date}# AND #{end_date}#"
    df = database.get_data(sql_query=sql_query)
    columns = list(df.columns[main_tablo_index * 12:main_tablo_index * 12 + 12])
    if not config.database['time_column'] in columns:
        columns.append(config.database['time_column'])
    tablo_data = summary.calculate_summary_stats(df=df[columns]).to_html()
    if main_tablo_index >= 2:
        main_tablo_index = 0
    else:
        main_tablo_index += 1
    return jsonify(data=tablo_data)


@app.route('/get_data', methods=['GET', 'POST'])
@app.route('/update_data', methods=['GET', 'POST'])
def update_data():
    global cols
    sql_query = f"SELECT TOP 1000 * FROM {table_name} ORDER BY {time_column} DESC"
    structure = {
        "name": "",
        "type": 'line',
        "showSymbol": False,
        "data": []
    }
    if cols:
        df = database.get_data(sql_query)
        data = realTimeDate.data(df, cols)
        return jsonify(data)
    return jsonify(structure)


@app.route('/update_data_main_bar', methods=['GET', 'POST'])
def update_data_main_bar():
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM {table_name} WHERE {config.database['time_column']} BETWEEN #{start_date}# AND #{end_date}#"
    df_mean = database.get_data(sql_query=sql_query).drop(config.database['time_column'], axis=1).mean()
    data = {
        "x": list(df_mean.index),
        "y": list(df_mean.values)
    }

    return jsonify(data)


@app.route('/update_data_main_pie', methods=['GET', 'POST'])
def update_data_main_pie():
    global main_page_index
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM {table_name} WHERE {config.database['time_column']} BETWEEN #{start_date}# AND #{end_date}#"
    df = database.get_data(sql_query=sql_query)
    cols = df.drop(config.database['time_column'], axis=1).columns

    target_col = cols[main_page_index]

    target_data = df[target_col].sum()

    total_data = df.drop([target_col, config.database['time_column']], axis=1).sum().sum()

    data = [
        {"name": target_col, "value": float(target_data)},
        {"name": "Diğerleri", "value": float(total_data)}

    ]

    if main_page_index >= (len(cols) - 1):
        main_page_index = 0
    else:
        main_page_index += 1
    return jsonify(data)


@app.route('/live', methods=['GET', 'POST'])
def live():
    global cols
    cols = ["debi_1"]
    data = request.form.getlist("Debi")
    try:
        cols = str(data[0]).split(",")
    except:
        pass

    return render_template('livepage.html')


@app.route('/tablo', methods=['GET', 'POST'])
def tablo():
    try:
        start_date = datetime.strptime(request.form['start_date'].replace("T", " "), '%Y-%m-%d %H:%M')

        end_date = datetime.strptime(request.form['end_date'].replace("T", " "), '%Y-%m-%d %H:%M')

        col_names = request.form.getlist("Debi")
        col_names.insert(0, time_column)
        sql_query = f"SELECT * FROM {table_name} WHERE {time_column} BETWEEN #{start_date}# AND #{end_date}#"
        df = database.get_data(sql_query=sql_query)[col_names]
        table_html = df.to_html(classes='table table-striped', index=False)
    except Exception as e:
        print(e)
        table_html = ""
    return render_template('table.html', table_data=table_html)


def get_mean(df):
    index = df.drop(config.database['time_column'], axis=1).astype(float).mean().index
    values = df.drop(config.database['time_column'], axis=1).astype(float).mean().values
    return (list(index), list(values))


def total(df):
    df[config.database['time_column']] = pd.to_datetime(df[config.database['time_column']])
    df = df.sort_values(by=config.database['time_column'])
    result = df.resample('H', on=config.database['time_column']).mean().sum()
    return result


def get_sum(df):
    index = total(df).index
    values = total(df).values
    return (list(index), list(values))


def array_to_dict(arr1, arr2):
    if len(arr1) != len(arr2):
        raise ValueError("Arraylerin uzunlukları eşit olmalıdır.")

    result = [{"name": x, "value": y} for x, y in zip(arr1, arr2)]
    return result


@app.route('/graph', methods=['GET', 'POST'])
def graph():
    try:
        start_date = datetime.strptime(request.form['start_date'].replace("T", " "), '%Y-%m-%d %H:%M')
        end_date = datetime.strptime(request.form['end_date'].replace("T", " "), '%Y-%m-%d %H:%M')
        col_names = request.form.getlist("Debi")
        target = request.form.getlist("select")
        sql_query = f"SELECT * FROM {table_name} WHERE {time_column} BETWEEN #{start_date}# AND #{end_date}#"
        df = database.get_data(sql_query=sql_query)
        plot_data = realTimeDate.data(df, col_names)
        col_names.insert(0, config.database['time_column'])
        df = df[col_names]
        if target[0] == "toplam":
            print("*" * 100)
            target_data = get_sum(df)
        else:
            target_data = get_mean(df)

        pie_data = array_to_dict(target_data[0], target_data[1])
        bar_data = {"x": target_data[0], "y": target_data[1]}
    except Exception as e:
        pie_data = {}
        bar_data = {}
        plot_data = {}
    return render_template('graph.html', pie_data=pie_data, bar_data=bar_data, plot_data=plot_data)


@app.route('/conf', methods=['GET', 'POST'])
def config_data():
    if request.method == "POST":
        if "sender_email" in request.form.keys():
            data = {}
            data['sender_email'] = request.form.getlist('sender_email')[0]
            data['password'] = request.form.getlist('password')[0]
            data['receiver_email'] = request.form.getlist('receiver_email')[0]
            data['hour'] = request.form.getlist('time')[0].split(":")[0]
            data['minute'] = request.form.getlist('time')[0].split(":")[1]
            exist_data = config.data_config
            exist_data.update(data)
            write_json(exist_data)
        else:
            data = {}
            data['db_file_path'] = request.form.getlist('db_file_path')[0]
            data['table_name'] = request.form.getlist('table_name')[0]
            state = database.test(data)
            if state:
                exist_data = config.database
                exist_data.update(data)
                write_json(exist_data, path="config/database_config.json")
                return render_template('config.html', state="Başarılı")
            else:
                return render_template('config.html', state="Veri tabanı bilgileri yanlış")
    return render_template('config.html')


def create_pdf(df, date):
    table_data = [df.columns.tolist()] + df.values.tolist()
    if not os.path.exists("./Rapor"):
        os.mkdir("Rapor")
    pdf_filename = f'./Rapor/Rapor{str(date)}.pdf'
    pdf = SimpleDocTemplate(pdf_filename, pagesize=letter)
    table = Table(table_data)

    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])

    table.setStyle(style)
    elements = [table]
    pdf.build(elements)
    return pdf_filename


def send_email(sender_mail, password, receiver_email):
    try:
        smtp_server = 'smtp.yandex.com'
        smtp_port = 587
        subject = 'Günlük Rapor'
        msg = MIMEMultipart()
        msg['From'] = sender_mail
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEBase('application', 'octet-stream'))
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        sql_query = f"SELECT * FROM {table_name} WHERE {time_column} BETWEEN #{start_date}# AND #{end_date}#"
        df2 = database.get_data(sql_query=sql_query)
        df = summary.calculate_summary_stats(df2)
        pdf_filename = create_pdf(df, start_date)
        info_graph(df2,start_date)
        with open(pdf_filename, 'rb') as pdf_file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((pdf_file).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {pdf_filename}")
            msg.attach(part)

        try:
            for i in glob.glob(f"./Rapor/{start_date}/*"):
                with open(i, 'rb') as file:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload((file).read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename= {i}")
                    msg.attach(part)
        except Exception as e:
            print(e)
        body = f""" 
Sayın , 

   {str(start_date)} - {str(end_date)} Günlük raporu içeren PDF dosyasını ekte bulabilirsiniz. \n\n

    {info_txt(df2)}
"""

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_mail, password)
        server.sendmail(sender_mail, receiver_email, msg.as_string())
        server.quit()

        print('E-posta gönderme Basarili')

    except Exception as e:
        print('E-posta gönderme hatasi:', str(e))


def run_scheduled():
    temp = True
    while True:
        try:
            if temp:
                temp = False
                (sender_email, receiver_email, password, hour, minute) = config.mail
                current_time = datetime.now()
                if (int(current_time.hour) == int(hour)) and (int(current_time.minute) == int(minute)):
                    send_email(sender_email, password, receiver_email)
                time.sleep(60)
            temp = True
        except Exception as e:
            print(e)


def info_txt(df):
    result = ""
    try:

        df = df.sort_values(by=config.database['time_column'])
        ortalama = df.resample('H', on=config.database['time_column']).mean()
        result += "--" * 30
        result += "\nGün içinde Saatlik ortalama: \n"
        for i in ortalama:
            result += f"{i}: {ortalama[i]} \n"
        result += "--" * 30
        result += "\nGün içinde ortalama : \n"
        for i in ortalama:
            result += f"\n{i}: {ortalama[i].mean()} \n"
        result += "--" * 30
        result += "\nGün içinde toplam : \n"
        for i in ortalama:
            result += f"\n{i}: {ortalama[i].sum()} \n"
    except:
        pass
    return result


def info_graph(df,date):
    try:
        df = df.sort_values(by=config.database['time_column'])
        ortalama = df.resample('H', on=config.database['time_column']).mean()
        path=f"./Rapor/{str(date)}"
        if not os.path.exists(path):
            os.mkdir(path)
        for i in ortalama.columns:
            try:
                plt.figure(figsize=(20, 10))
                plt.plot(ortalama[i],linewidth=2)
                plt.plot(ortalama[i], "o",c="r")
                plt.title(f"{i} Günlük ve Saatlik Ortalama")
                plt.savefig(f"{path}/mean_hour_{i}.png")
                plt.cla()
            except:
                pass
        try:
            plt.figure(figsize=(20, 6))
            plt.bar(ortalama.mean().index,ortalama.mean().values)
            plt.title(f"Günlük Ortalama")
            plt.savefig(f"{path}/daily_mean.png")
            plt.cla()
        except Exception as e:
            print(e)

        try:
            plt.figure(figsize=(20, 6))
            plt.bar(ortalama.sum().index,ortalama.sum().values)
            plt.title(f"Günlük Toplam")
            plt.savefig(f"{path}/daily_sum.png")
            plt.cla()
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)

schedule_thread = threading.Thread(target=run_scheduled)
schedule_thread.daemon = True
if __name__ == '__main__':
    schedule_thread.start()
    app.run(debug=True, port=8002)
