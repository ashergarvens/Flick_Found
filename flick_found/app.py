import os
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import openai
from openai import OpenAI
import json
from flask import Flask, render_template, url_for, flash, redirect, request, session
from forms import RegistrationForm, LoginForm
from flask_behind_proxy import FlaskBehindProxy
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps

# Google API imports
import datetime
from datetime import datetime
from tzlocal import get_localzone
import os.path
import urllib3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events']

app = Flask(__name__)
proxied = FlaskBehindProxy(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"User('{self.email}')"


with app.app_context():
    db.create_all()


# @app.route("/")
# @app.route("/home")
# def home():
#     return render_template('home.html', subtitle='Home Page', text='This is the home page!')


# @app.route("/about")
# def second_page():
#     return render_template('about.html', subtitle='about', text='This is the second page!')


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():  # checks if entries are valid
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.email.data}!', 'success')
        return redirect(url_for('preferences'))  # if so - send to home page
    return render_template('register.html', title='Register', form=form)


@app.route('/')
@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash(f'Login successful for {form.email.data}', 'success')
            return redirect(url_for('results'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# API configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
openai.api_key = OPENAI_API_KEY


def get_upcoming_movies(tmbd_api_key):
    # calls to get upcoming movies -> we can process them to get chatgpt recommendations 
    url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    else:
        return []

    # response = requests.get(url, headers=headers) not sure what this does... its unreachable


def get_movie_poster(title):
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': title
    }
    response = requests.get(search_url, params=params)
    data = response.json()
    if data['results']:
        poster_path = data['results'][0].get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"
    return None


def generate_recommendations(movie_choices, preferences):
    print("\nProcessing request....")
    while True:
        try:
            client = OpenAI(
                api_key=OPENAI_API_KEY,
            )
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Please give me a "
                                                  f"recommendation based on "
                                                  f"these movies here "
                                                  f"{movie_choices} "
                                                  f"and with the genres: "
                                                  f"{preferences}."},

                    {"role": "user", "content": "You are a movie recommendation bot that takes in similar movies "
                                                "and gives 10 specific movie recommendations as a response in a json format "
                                                "with the following keys: title, genre, rating out of 10 from IMDB, release date. "
                                                "Please provide the recommendations as one json string with the key 'recommendations' "
                                                "containing a list of 10 movies with their respective attributes. "
                                                "Use double quotes for all strings. Here is a sample format:\n\n"
                                                "{\n"
                                                "  \"recommendations\": [\n"
                                                "    {\n"
                                                "      \"title\": \"Movie Title\",\n"
                                                "      \"genre\": \"Genre\",\n"
                                                "      \"rating\": \"8.5\",\n"
                                                "      \"release_date\": \"YYYY-MM-DD\"\n"
                                                "    },\n"
                                                "    ... 9 more movies ...\n"
                                                "  ]\n"
                                                "}.\n"
                                                "Please end with a closing curly bracket."
                     }
                ]
            )
            return json.loads(completion.choices[0].message.content)
        except json.JSONDecodeError:
            print("There is a json decode error")


def process_response(response):
    recommendations = response['recommendations']
    processed_recommendations = []
    for item in recommendations:
        processed_recommendations.append({
            'title': item['title'],
            'genre': item['genre'],
            'rating': item['rating'],
            'releaseDate': item['release_date']
        })
    return processed_recommendations


def process_choices_and_recommendations(movie_choices, recommendations):
    while True:
        count = 0
        try:
            processed_recommendations = process_response(generate_recommendations(movie_choices, recommendations))
            return processed_recommendations
        except KeyError:
            count += 1
            print(
                'There was a key error when converting the response to the proper dictionary. Retrying GPT request...')
            if count > 3:
                return ''


def modify_database(recommendations):
    df = pd.DataFrame.from_dict(recommendations)
    engine = create_engine('sqlite:///media_recommendations.db')
    if not df.empty:
        df.to_sql('recommendations', con=engine, if_exists='replace', index=False)


@app.route('/preferences')
@login_required
def preferences():
    return render_template('preferences.html')



@app.route('/generate', methods=['POST'])
@login_required
def generate():
    choices = request.form.get('choices-hidden').split('`')
    genres = request.form.get('genre-hidden').split('`')
    recommendations = process_choices_and_recommendations(choices, genres)
    if recommendations:
        modify_database(recommendations)
    else:
        print('Unable to process API Request and Convert to DB')

    return redirect(url_for('results'))

@app.route('/results')
@app.route('/results/<genre>')
@login_required
def results(genre=None):
    engine = create_engine('sqlite:///media_recommendations.db')
    query = "SELECT * FROM recommendations"
    if genre:
        query += f" WHERE genre LIKE '%{genre}%'"

    with engine.connect() as connection:
        result = connection.execute(text(query)).fetchall()
        df = pd.DataFrame(result, columns=['title', 'genre', 'rating', 'releaseDate'])

    recommendations = df.to_dict(orient='records')
    for rec in recommendations:
        rec['poster'] = get_movie_poster(rec['title'])

    return render_template('results.html', recommendations=recommendations)

@app.route('/watchlist', methods=['GET', 'POST'])
@login_required
def watchlist():
    # TO-DO: Add watchlist functionality
    if request.method == 'POST':
        genre = request.form['genre']
        return redirect(url_for('results', genre=genre))
    return render_template('search.html')

@app.route('/reminder', methods=['POST'])
@login_required
def reminder():
    # Set up connection to GCal and authenticate
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            # Specify a fixed port here
            creds = flow.run_local_server(port=8080)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service = build("calendar", "v3", credentials=creds)
    except Exception:
        # Name of the file to be deleted
        filename = "token.json"
        # Delete the file
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} has been reloaded.")
        else:
            print(f"{filename} does not exist.")
        

    # Create Google Calendar event
    movie_reminders_list = request.form.get('reminder-hidden').split('`')
    movie = movie_reminders_list[-1]
    movie_dict = json.loads(movie)
    timeZone = get_localzone()

    reminder_dict = {
        "summary": movie_dict['title'],
        "description": movie_dict['genre'] + movie_dict['rating'],
        "start": {
            "dateTime": movie_dict['releaseDate'] + "T12:00:00-13:00",
            "timeZone": timeZone
        },
        "end": {
            "dateTime": movie_dict['releaseDate'] + "T14:00:00-07:00",
            "timeZone": timeZone
        },
        "reminders": {
            "useDefault": True
        }
        }
    
    insert_event = service.events().insert(
            calendarId='primary',
            body=reminder_dict).execute()

    return redirect(url_for('results'))


if __name__ == '__main__':
    app.run(debug=True)
