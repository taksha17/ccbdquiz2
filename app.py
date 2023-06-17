import pyodbc
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime as dt
from datetime import date
from datetime import timedelta
from geopy.distance import geodesic
from math import sin, cos, sqrt, atan2
from flask import redirect
from flask import redirect, url_for
from wtforms import IntegerField



app = Flask(__name__)
app.config['SECRET_KEY'] = 'SecureSecretKey'


def connection():    
    server = 'txt6312server.database.windows.net'
    database = 'test'
    username = 'CloudSA3d95adf8'
    password = 'tiger@123TT'
    driver = '{ODBC Driver 18 for SQL Server}'
    conn = pyodbc.connect(
        'DRIVER=' + driver + ';SERVER=' + server + ';PORT=1433;DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    return conn


@app.route('/', methods=['GET', 'POST'])
def main():
    try:
        conn = connection()
        cursor = conn.cursor()
        return render_template('index.html', add_form=Add(), remove_form=Add())
    except Exception as e:
        return render_template('index.html', add_form=Remove(), remove_form=Remove(), error=e)

#Search by City


class Form1(FlaskForm):
    City = StringField(label='Enter City Name: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


@app.route('/form1', methods=['GET', 'POST'])
def form1():
    form = Form1()
    cnt = 0
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            City = (form.City.data)
            if City == '':
                return render_template('form1.html', form=form, error="Please enter a valid city name", data=0)

            cursor.execute("SELECT * FROM city where City = ?", City)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1
            return render_template('form1.html', result=result, cnt=cnt, City=City, form=form, data=1)

        except Exception as e:
            print(e)
            return render_template('form1.html', form=form, error="City Name not found", data=0)

    return render_template('form1.html', form=form)



class Form2(FlaskForm):
    lat1 = StringField(label='Enter Min latitude X1: ', validators=[DataRequired()])
    lat2 = StringField(label='Enter Max latitude X2: ', validators=[DataRequired()])
    lon1 = StringField(label='Enter min Longitude Y1: ', validators=[DataRequired()])
    lon2 = StringField(label='Enter max Longitude Y2: ', validators=[DataRequired()])
    state = StringField(label='Enter State Name: ', validators=[DataRequired()])
    min_pop = StringField(label='Enter Minimum Population: ', validators=[DataRequired()])
    max_pop = StringField(label='Enter Maximum Population: ', validators=[DataRequired()])
    inc_pop = StringField(label='Enter Population Increment: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')
@app.route('/form2', methods=['GET', 'POST'])
def form2():
    form = Form2()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            lat1 = float(form.lat1.data)
            lat2 = float(form.lat2.data)
            lon1 = float(form.lon1.data)
            lon2 = float(form.lon2.data)
            state = form.state.data
            min_pop = int(form.min_pop.data)
            max_pop = int(form.max_pop.data)
            inc_pop = int(form.inc_pop.data)
            
            cnt = 0
            R = 6373.0

            cursor.execute("SELECT * FROM city where lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?", lat1, lat2, lon1, lon2)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1
            
            # Filter cities by state name
            if state:
                result = [row for row in result if row[1] == state]

            modified_cities = []
            for row in result:
                city = row[0]
                state = row[1]
                population = row[2]
                lat = row[3]
                lon = row[4]

                if min_pop <= population <= max_pop:
                    new_population = population + inc_pop
                    modified_cities.append((city, state, new_population, lat, lon))
                    # Update the population in the database
                    cursor.execute("UPDATE city SET population = ? WHERE City = ? AND State = ?", new_population, city, state)

            conn.commit()  # Commit the changes to the database

            return render_template('form2.html', result=modified_cities, cnt=len(modified_cities), lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2, data=1)

        except Exception as e:
            print(e)
            return render_template('form2.html', form=form, error="Latitude must be in the [-90; 90] range, Latitude must be in [-180; 180], and all input must be numeric.")
    
    return render_template('form2.html', form=form, data=0)


#Search by Location


class Form3(FlaskForm):
    lat1 = StringField(label='Enter Min latitude X1: ', validators=[DataRequired()])
    lat2 = StringField(label='Enter Max latitude X2: ', validators=[DataRequired()])
    lon1 = StringField(label='Enter min Longitude Y1: ', validators=[DataRequired()])
    lon2 = StringField(label='Enter max Longitude Y2: ', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


@app.route('/form3', methods=['GET', 'POST'])
def form3():
    form = Form3()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            lat1 = float(form.lat1.data)
            lat2 = float(form.lat2.data)
            lon1 = float(form.lon1.data)
            lon2 = float(form.lon2.data)

            bounding_box = {
                'lat_min': min(lat1, lat2),
                'lat_max': max(lat1, lat2),
                'lon_min': min(lon1, lon2),
                'lon_max': max(lon1, lon2)
            }

            cursor.execute("SELECT City, State, Population, lat, lon FROM city WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?",
                           bounding_box['lat_min'], bounding_box['lat_max'], bounding_box['lon_min'], bounding_box['lon_max'])
            result = cursor.fetchall()
            cnt = len(result)

            return render_template('form3.html', result=result, cnt=cnt, lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2, data=1)

        except Exception as e:
            print(e)
            return render_template('form3.html', form=form,
                                   error="Latitude must be in the [-90; 90] range, Longitude must be in [-180; 180], and all input must be numeric.")
    
    return render_template('form3.html', form=form, data=0)



#Search by Clusters


@app.route('/form4', methods=['GET', 'POST'])
def form4():
    if request.method == 'POST':
        try:
            conn = connection()
            cursor = conn.cursor()
            clus = request.form['clus']
            cnt = 0

            cursor.execute("SELECT * FROM earthquake1 where type = ?", clus)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1
            return render_template('form4.html', result=result, cnt=cnt, clus=clus, data=1)

        except Exception as e:
            print(e)
            return render_template('form4.html', error="Range 1 and Range 2 must be numeric, Range 1 > Range 2 and Days must be integer and less then 31.", data=0)

    return render_template('form4.html', data=0)


#Does given Magnitude occur more often at night?


@app.route('/form5', methods=['GET', 'POST'])
def form5():
    cnt = 0
    tot_cnt = 0
    try:
        conn = connection()
        cursor = conn.cursor()

        cursor.execute('select * from earthquake1 where mag > 4.0')
        result = []
        while True:
            row = cursor.fetchone()
            if not row:
                break
            hour = dt.strptime(row[0], '%Y-%m-%dT%H:%M:%S.%fZ').hour
            if hour > 18 or hour < 7:
                result.append(row)
                cnt += 1
            tot_cnt += 1
        return render_template('form5.html', result=result, cnt=cnt, tot_cnt=tot_cnt, data=1)

    except Exception as e:
        print(e)
        return render_template('form5.html', error="Magnitude must be numeric.", data=0)
    

class Add(FlaskForm):
    city = StringField(label='City:', validators=[DataRequired()])
    state = StringField(label='State:', validators=[DataRequired()])
    population = IntegerField(label='Population:', validators=[DataRequired()])
    latitude = StringField(label='Latitude:', validators=[DataRequired()])
    longitude = StringField(label='Longitude:', validators=[DataRequired()])

class Remove(FlaskForm):
    city = StringField(label='City:', validators=[DataRequired()])
    state = StringField(label='State:', validators=[DataRequired()])

@app.route('/add', methods=['GET', 'POST'])
def add_form():
    try:
        conn = connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            city = request.form['city']
            state = request.form['state']
            population = int(request.form['population'])
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])

            # Insert the new city entry into the database
            cursor.execute("INSERT INTO city (City, State, Population, lat, lon) VALUES (?, ?, ?, ?, ?)",
                           city, state, population, latitude, longitude)
            conn.commit()  # Commit the changes to the database

            return redirect(url_for('add_form'))  # Redirect to the add_form() route

        # return render_template('add.html', add_form=Add(), remove_form=Remove())  # Render the add.html template for GET requests
        # return render_template('add.html', add_form=Add(), remove_form=Remove(), form=form)
        return render_template('add.html', add_form=Add(), remove_form=Remove(), form=Add())


    except Exception as e:
        return render_template('add.html', add_form=Remove(), remove_form=Remove(), error=e)




@app.route('/remove', methods=['POST'])
def remove_form():
    try:
        conn = connection()
        cursor = conn.cursor()
        city = request.form['city']
        state = request.form['state']

        # Remove the city entry from the database
        cursor.execute("DELETE FROM city WHERE City = ? AND State = ?", city, state)
        conn.commit()  # Commit the changes to the database

        return redirect(url_for('remove_form'))
    except Exception as e:
        return render_template('remove.html', remove_form_errors=str(e))




if __name__ == "__main__":
    app.run(debug=True)