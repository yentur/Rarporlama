from flask import Flask, render_template,request
from flask import jsonify
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pyodbc
import time
import smtplib
import json
import schedule
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import webview

conn=""
table_name=""




last_data=0
main_page_index=0
main_tablo_index=0
cols=[]


app = Flask(__name__,static_folder="./static",template_folder="./templates")





def conn_database(data=None):
    global conn,table_name
    try:
        conn.close()
    except:
        pass
    if data==None:
        config={}
        with open('config/database_config.json') as f:
                config = json.load(f)
        db_file_path=config['db_file_path']
        conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_file_path
        conn = pyodbc.connect(conn_str)
        table_name=config['table_name']
        return None
    else:
        try:
            db_file_path=data['db_file_path']
            table_name=data['table_name']
            conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_file_path
            conn = pyodbc.connect(conn_str)
            return True
        except:
            config={}
            with open('config/database_config.json') as f:
                    config = json.load(f)
            db_file_path=config['db_file_path']
            conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_file_path
            conn = pyodbc.connect(conn_str)
            table_name=config['table_name']
            return False






def read_json():
        
        with open('config/config.json') as f:
            config = json.load(f)
        sender_email = config['sender_email']
        receiver_email = config['receiver_email']
        password = config['password']
        hour = config['hour']
        minute = config['minute']
        return (sender_email,receiver_email,password,hour,minute)


def write_json(data,path="config/config.json"):
        with open(path,"w") as f:
            json.dump(data,f)
        print("file write is successful")




def send_email(sender_mail,password,receiver_email,body="None"):
    try:
        
        smtp_server = 'smtp.yandex.com'
        smtp_port = 587

        subject = 'Günlük Rapor'
        body = 'Bu bir test e-postasıdır.'

        msg = MIMEMultipart()
        msg['From'] = sender_mail
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))


        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_mail, password)

        server.sendmail(sender_mail, receiver_email, msg.as_string())
        server.quit()
        print('E-posta gönderme Basarili')


    except Exception as e:
        print('E-posta gönderme hatasi:', str(e))






def calculate_summary_stats(dataframe,index):
    df=dataframe.drop("tarih",axis=1)
    cols=df.columns[index*12:index*12+12]
    df=df[cols]
    total = df.sum()
    
    mean = df.mean()
    
    max_value = df.max()
    
    min_value = df.min()
    

    summary_df = pd.DataFrame({
        'Toplam': total,
        'Ortalama': mean,
        'Maksimum': max_value,
        'Minimum': min_value
    })
    
    summary_df = summary_df
    
    return summary_df


@app.route('/')
@app.route('/main')
def index():
    start_date=datetime.now().strftime("%Y-%m-%d")
    end_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
    df=get_data(sql_query=sql_query)
    if df.shape[1]>1:
        tablo_data=calculate_summary_stats(df,0).to_html()
    else:
        tablo_data=""
    return render_template('mainpage.html',tablo_data=tablo_data)




@app.route('/live', methods=['GET','POST'])
def live():
    global cols
    cols=["debi_1"]
    data = request.form.getlist("Debi")
    try:
        cols=str(data[0]).split(",")
    except:
        pass
    
    return render_template('livepage.html')








def run_scheduled():
    while True:
        try:
            (sender_email,receiver_email,password,hour,minute)=read_json()
            print((sender_email,receiver_email,password,hour,minute))
            current_time = datetime.now()
            if (int(current_time.hour)==int(hour)) and (int(current_time.minute) == int(minute)):
                send_email(sender_email,password,receiver_email)
            time.sleep(60)
        except Exception as e:
            print(e)






def live_data(columns,sql_query):

    df=get_data(sql_query)
    last_data=[]
    date_str = df['tarih'].dt.strftime('%Y-%m-%d %H:%M:%S')
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




def get_data(sql_query):
    cursor = conn.cursor()
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    columns = [column.column_name for column in cursor.columns(table=table_name)]
    df=pd.DataFrame.from_records(rows)
    if df.shape[1]>1:
        df.columns=columns
        df['tarih']=pd.to_datetime(df['tarih'])
        df=df.sort_values(by="tarih",ascending=False).reset_index(drop=True)
    return df


def array_to_dict(arr1,arr2):
    if len(arr1) != len(arr2):
        raise ValueError("Arraylerin uzunlukları eşit olmalıdır.")

    result = [{"name": x, "value": y} for x, y in zip(arr1, arr2)]
    return result




def get_sum(df):
    index=df.drop("tarih",axis=1).astype(float).sum().index
    values=df.drop("tarih",axis=1).astype(float).sum().values
    return (list(index),list(values))


def get_mean(df):
    index=df.drop("tarih",axis=1).astype(float).mean().index
    values=df.drop("tarih",axis=1).astype(float).mean().values
    return (list(index),list(values))





@app.route('/tablo', methods=['GET','POST'])
def tablo():
    try:
        start_date = datetime.strptime(request.form['start_date'].replace("T"," "),'%Y-%m-%d %H:%M')

        end_date = datetime.strptime(request.form['end_date'].replace("T"," "),'%Y-%m-%d %H:%M')

        col_names = request.form.getlist("Debi")
        col_names.insert(0, "tarih")
        sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
        df=get_data(sql_query=sql_query)[col_names]
        table_html = df.to_html(classes='table table-striped', index=False)
    except Exception as e:
        print(e)
        table_html=""
    return render_template('table.html',table_data=table_html)





@app.route('/graph', methods=['GET','POST'])
def graph():
    try:
        start_date = datetime.strptime(request.form['start_date'].replace("T"," "),'%Y-%m-%d %H:%M')
        end_date = datetime.strptime(request.form['end_date'].replace("T"," "),'%Y-%m-%d %H:%M')
        col_names = request.form.getlist("Debi")
        target=request.form.getlist("select")
        sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
        plot_data=live_data(col_names,sql_query=sql_query)

        col_names.insert(0, "tarih")
        df=get_data(sql_query=sql_query)[col_names]
        if target[0] =="toplama":
            target_data=get_sum(df)
        else:
            target_data=get_mean(df)
        pie_data=array_to_dict(target_data[0],target_data[1])
        bar_data={"x":target_data[0],"y":target_data[1]}
    except Exception as e:
        pie_data={}
        bar_data={}
        plot_data={}
    return render_template('graph.html',pie_data=pie_data,bar_data=bar_data,plot_data=plot_data)


@app.route('/config', methods=['GET','POST'])
def config():

    if request.method == "POST":
        if "sender_email" in request.form.keys():
            data={}
            data['sender_email']= request.form.getlist('sender_email')[0]
            data['password']= request.form.getlist('password')[0]
            data['receiver_email']= request.form.getlist('receiver_email')[0]
            data['hour']= request.form.getlist('time')[0].split(":")[0]
            data['minute']= request.form.getlist('time')[0].split(":")[1]
            write_json(data)
        else:
            data={}
            data['db_file_path']= request.form.getlist('db_file_path')[0]
            data['table_name']= request.form.getlist('table_name')[0]
            state=conn_database(data)
            if state:
                write_json(data,path="config/database_config.json")
                return render_template('config.html' , state="Başarılı")
            else:
                return render_template('config.html',state="Veri tabanı bilgileri yanlış")
    return render_template('config.html')




@app.route('/get_data', methods=['GET','POST'])
@app.route('/update_data', methods=['GET','POST'])
def update_data():
    global cols
    sql_query = "SELECT TOP 1000 * FROM veriler ORDER BY tarih DESC"
    structure = {
            "name": "",
            "type": 'line',
            "showSymbol": False,
            "data": []
        }
    if cols!=['']:
        data=live_data(cols,sql_query)
        return jsonify(data)
    return jsonify(structure)





@app.route('/update_data_main_pie', methods=['GET','POST'])
def update_data_main_pie():
    global main_page_index
    start_date=datetime.now().strftime("%Y-%m-%d")
    end_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
    df=get_data(sql_query=sql_query)
    cols=df.drop("tarih",axis=1).columns
    
    target_col=cols[main_page_index]

    target_data=df[target_col].sum()
    
    total_data=df.drop([target_col,'tarih'],axis=1).sum().sum()
    


    data=[
        {"name":target_col,"value":float(target_data)},
        {"name":"Diğerleri","value":float(total_data)}

    ]
    
    if main_page_index>=(len(cols)-1):
        main_page_index=0
    else:
        main_page_index+=1   
    print(target_col,main_page_index,len(cols))
    return jsonify(data)



@app.route('/update_data_main_bar', methods=['GET','POST'])
def update_data_main_bar():
    start_date=datetime.now().strftime("%Y-%m-%d")
    end_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
    df_sum=get_data(sql_query=sql_query).drop("tarih",axis=1).sum()
    data={
        "x":list(df_sum.index),
        "y":list(df_sum.values)
    }
    
    return jsonify(data)


@app.route('/get_info_data', methods=['GET','POST'])
def get_info_data():
    global main_tablo_index
    start_date=datetime.now().strftime("%Y-%m-%d")
    end_date=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    sql_query = f"SELECT * FROM veriler WHERE tarih BETWEEN #{start_date}# AND #{end_date}#"
    df=get_data(sql_query=sql_query)
    tablo_data=calculate_summary_stats(df,main_tablo_index).to_html()
    if main_tablo_index>=2:
        main_tablo_index=0
    else:
        main_tablo_index+=1   
    return jsonify(data=tablo_data)




webview.create_window("Raporlama",app)

if __name__ == '__main__':
    conn_database()
    # schedule_thread = threading.Thread(target=run_scheduled)
    # schedule_thread.start()
    # app.run(debug=True)
    webview.start()


