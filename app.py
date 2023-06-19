import pyodbc
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms import IntegerField
from wtforms.validators import DataRequired
from geopy.distance import geodesic

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
        return render_template('index.html', add_form=AddForm(), remove_form=RemoveForm())
    except Exception as e:
        return render_template('index.html', add_form=RemoveForm(), remove_form=RemoveForm(), error=e)


# Search by City
class Form1(FlaskForm):
    City = StringField(label='Enter City Name:', validators=[DataRequired()])
    submit = SubmitField(label='Submit')

@app.route('/form1', methods=['GET', 'POST'])
def form1():
    form = Form1()
    cnt = 0
    additional_cities = []
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            city = form.City.data.strip()
            if city == '':
                return render_template('form1.html', form=form, error="Please enter a valid city name", data=0)

            cursor.execute("SELECT * FROM city WHERE City = ?", city)
            result = []
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                result.append(row)
                cnt += 1

            # Find additional cities within 100 km
            lat = result[0][3]
            lon = result[0][4]
            cursor.execute("SELECT * FROM city")
            all_cities = cursor.fetchall()
            for c in all_cities:
                dist = geodesic((lat, lon), (c[3], c[4])).km
                if dist <= 100:
                    additional_cities.append(c)

            return render_template('form1.html', result=result, cnt=cnt, City=city, form=form, data=1, additional_cities=additional_cities)

        except Exception as e:
            print(e)
            return render_template('form1.html', form=form, error="City Name not found", data=0)

    return render_template('form1.html', form=form)



# Search Cities by bound
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

class Form2(Form3):
    state = StringField(label='Enter State Name:', validators=[DataRequired()])
    min_pop = IntegerField(label='Enter Minimum Population:', validators=[DataRequired()])
    max_pop = IntegerField(label='Enter Maximum Population:', validators=[DataRequired()])
    inc_pop = IntegerField(label='Enter Population Increment:', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(Form2, self).__init__(*args, **kwargs)

@app.route('/form2', methods=['GET', 'POST'])
def form2():
    form = Form2()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            bounding_box = form.bounding_box.data.strip()
            state = form.state.data.strip()
            min_pop = int(form.min_pop.data)
            max_pop = int(form.max_pop.data)
            inc_pop = int(form.inc_pop.data)

            where_clause = ""
            if bounding_box:
                lat1, lon1, lat2, lon2 = map(float, bounding_box.split(','))
                where_clause += f"lat BETWEEN {lat1} AND {lat2} AND lon BETWEEN {lon1} AND {lon2}"
            if state:
                where_clause += f"State = '{state}'"

            if not where_clause:
                return render_template('form3.html', form=form,
                                       error="Please provide a bounding box or state name")

            cursor.execute(f"SELECT * FROM city WHERE {where_clause}")
            result = cursor.fetchall()
            cnt = len(result)

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
                    cursor.execute("UPDATE city SET Population = ? WHERE City = ? AND State = ?",
                                   new_population, city, state)

            conn.commit()

            return render_template('form2.html', result=modified_cities, cnt=len(modified_cities), data=1)

        except Exception as e:
            print(e)
            return render_template('form2.html', form=form,
                                   error="An error occurred while updating population")

    return render_template('form2.html', form=form, data=0)


# Add and Remove City
class AddForm(FlaskForm):
    city = StringField(label='City:', validators=[DataRequired()])
    state = StringField(label='State:', validators=[DataRequired()])
    population = IntegerField(label='Population:', validators=[DataRequired()])
    latitude = StringField(label='Latitude:', validators=[DataRequired()])
    longitude = StringField(label='Longitude:', validators=[DataRequired()])

@app.route('/add', methods=['GET', 'POST'])
def add_form():
    form = AddForm()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            city = form.city.data.strip()
            state = form.state.data.strip()
            population = form.population.data
            latitude = float(form.latitude.data)
            longitude = float(form.longitude.data)

            cursor.execute("INSERT INTO city (City, State, Population, lat, lon) VALUES (?, ?, ?, ?, ?)",
                           city, state, population, latitude, longitude)
            conn.commit()

            return redirect(url_for('add_form'))

        except Exception as e:
            print(e)
            return render_template('add.html', add_form=form, remove_form=RemoveForm(), error="An error occurred while adding the city")

    # return render_template('add.html', add_form=form, remove_form=RemoveForm())
    return render_template('add.html', add_form=form, remove_form=RemoveForm(), form=form)

class RemoveForm(FlaskForm):
    city = StringField(label='City:', validators=[DataRequired()])
    state = StringField(label='State:', validators=[DataRequired()])

@app.route('/remove', methods=['GET', 'POST'])
def remove_form():
    form = RemoveForm()
    if form.validate_on_submit():
        try:
            conn = connection()
            cursor = conn.cursor()
            city = form.city.data.strip()
            state = form.state.data.strip()

            cursor.execute("DELETE FROM city WHERE City = ? AND State = ?", city, state)
            conn.commit()

            return redirect(url_for('remove_form'))

        except Exception as e:
            print(e)
            return render_template('remove.html', add_form=AddForm(), remove_form=form, error="An error occurred while removing the city")

    # return render_template('remove.html', add_form=AddForm(), remove_form=form)
    return render_template('remove.html', form=form)



if __name__ == "__main__":
    app.run(debug=True,port = 8080)

