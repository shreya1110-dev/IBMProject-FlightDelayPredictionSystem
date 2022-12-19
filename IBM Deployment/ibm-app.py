import flask
import joblib
import MySQLdb.cursors
import requests
import re
import pandas as pd
from flask import request, render_template, Flask, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_cors import CORS
import datetime

# NOTE: you must manually set API_KEY below using information retrieved from your IBM Cloud account.
API_KEY = "tCzEer0P5KjeQ_Tu6f8W9HK24TQ1Ds_Wi311f1_mS5UI"
token_response = requests.post('https://iam.cloud.ibm.com/identity/token', data={"apikey":
 API_KEY, "grant_type": 'urn:ibm:params:oauth:grant-type:apikey'})
mltoken = token_response.json()["access_token"]

header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}


# setting a new instance of Flask
app = flask.Flask(__name__, static_url_path="")
CORS(app)

# creating secret key for the app
app.secret_key = 'helloworld'

with open('secret.txt', 'r') as f:
    line = f.readline().split(',')
    user = line[0]
    password = line[1]

#reading airport details
df = pd.read_csv("flightdata.csv")
origin_airports = df['ORIGIN'].unique()
destination_airports = df['DEST'].unique()

# setting config values
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = user
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = 'flights'

# get details from the dataset
def get_details_from_csv(orig_airport, dest_airport, fl_num, tail_num):
    op = df[(df['ORIGIN']==orig_airport) & (df['DEST']==dest_airport) & (df['FL_NUM']==fl_num) & (df['TAIL_NUM']==tail_num)]
    if len(op)==0:
        return 0
    return [op['CRS_ARR_TIME'].tolist(), op['CRS_DEP_TIME'].tolist()]

# creating instance of MySql
mysql = MySQL(app)

# home page route
@app.route('/', methods=["GET"])
def sendHome():
    return render_template('index.html', active_page="home", title="Welcome to FDP System!", msg="Welcome Onboard!")

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    # to display on the website
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form:
        name = request.form['name']
        password = request.form['password']

        # connect to MYSQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE name = % s AND password= % s', (name, password))
        account = cursor.fetchone()

        # if account exists
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['name'] = account['name']
            msg = 'Logged in successfully! Head out to Predict!'
            # if predict was selected before
            if 'pending' in session.keys():
                redirect(url_for('predict'))
                session.pop('pending', None)
                return render_template('details.html', msg='Hi, '+session['name'], active_page='details', title="Flight Details", origin_airports=origin_airports, dest_airports=destination_airports)
            redirect(url_for('sendHome'))
            return render_template('index.html', msg=msg, active_page='home', title="Welcome to FDP System!")
        else:
            msg = 'Incorrect username/password. Please try again'
    redirect(url_for('login'))
    return render_template('login.html', msg=msg, active_page='login', title="Login")

# logout   
@app.route('/logout')
def logout():
    if 'loggedin' not in session.keys():
        return render_template('login.html', msg='You need to login!!', active_page='login', title="Login") 
    session.pop('id', None)
    session.pop('name', None)
    session.pop('loggedin', None)
    msg = 'Thank you, See you again!'
    redirect(url_for('sendHome'))
    return render_template('index.html', msg=msg, active_page='home', title="Welcome to FDP System!")

# register
@app.route('/register', methods = ['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form:

        # get details from form 
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']

        # mysql connection and retreival
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE name = % s', (name, ))
        account = cursor.fetchone()

        # check statements
        if account:
            msg = 'Account already exists'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', name):
            msg = 'Username must contain only characters and numbers !'
        elif not name or not password or not email:
            msg = 'Please fill out the form !'
        else:
            # insert into table
            cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', (name, password, email, ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
            redirect(url_for('login'))
            return render_template('login.html', msg = msg, active_page='login', title="Log In")

    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    redirect(url_for('register'))
    return render_template('register.html', msg = msg, active_page='register', title="Signup")

#details page
@app.route('/details', methods=["GET"])
def details():
    msg = 'Please log in or signup to continue!'
    if 'loggedin' in session.keys():
        redirect(url_for('details'))
        return render_template("details.html", active_page='details', title="Details", msg='Hi, '+session['name'], origin_airports=origin_airports, dest_airports=destination_airports)
    session['pending'] = True
    redirect(url_for('login'))
    return render_template('login.html', msg=msg, active_page='login', title="Login")

# predicting the labels
@app.route('/predict', methods=["POST"])
def predict():

    # departure date
    format_date = "%Y-%m-%d"
    dep_date = datetime.datetime.strptime(request.form['dep_date'], format_date)
    month = int(dep_date.date().month)
    day_of_month = int(dep_date.date().day)

    # actual dep time
    format_time = "%H:%M"
    dep_time = datetime.datetime.strptime(request.form['dep_time'], format_time)
    dep_hour = dep_time.time().hour
    dep_minute = dep_time.time().minute
    departure_time = dep_hour*100+dep_minute

    # fl num
    fl_num = int(request.form['fl_num'])

    # tail num
    tail_num = request.form['tail_num']

    # orig airport
    orig_airport = str(request.form.get('orig-airp'))

    # dest airport
    dest_airport = str(request.form.get('dest-airp'))
    crs_time = get_details_from_csv(orig_airport,dest_airport,fl_num,tail_num)
    if crs_time==0:
        return render_template('details.html', msg='Enter correct Flight details!', active_page='details', title="Details", origin_airports=origin_airports, dest_airports=destination_airports)

    format_time = "%H%M"
    crs_departure_time = crs_time[1][0]
    crs_dep = datetime.datetime.strptime(str(crs_departure_time), format_time)
    crs_dep_hour = crs_dep.time().hour
    crs_dep_minute = crs_dep.time().minute
    
    crs_arrival_time = crs_time[0][0]

    departure_delay = (dep_minute-crs_dep_minute)+ 60*(dep_hour-crs_dep_hour)
    if(departure_delay>15):
        dep_del15 = 1
    else:
        dep_del15 = 0

    X = [[crs_departure_time, departure_time, departure_delay, 
         dep_del15, crs_arrival_time]]

    payload_scoring = {"input_data": [{"field": [['crs_departure_time', 'departure_time', 'departure_delay', 
         'dep_del15', 'crs_arrival_time']], "values": X}]}

    response_scoring = requests.post('https://us-south.ml.cloud.ibm.com/ml/v4/deployments/478f707e-8eb4-4413-a744-ad5931a4dc03/predictions?version=2022-11-17', json=payload_scoring,
    headers={'Authorization': 'Bearer ' + mltoken})
    predictions = response_scoring.json()
    predicted = predictions['predictions'][0]['values'][0][0]
    redirect(url_for('details'))
    return render_template("details.html", active_page='details', title="Details", predict=predicted, origin_airports=origin_airports, dest_airports=destination_airports)

if __name__ == '__main__':
    app.run(debug=True)