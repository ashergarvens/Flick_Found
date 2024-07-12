import os
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
import re

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

    genre_preferences = db.relationship('GenrePreferences', backref='user', lazy=True)
    movie_preferences = db.relationship('MoviePreferences', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"User('{self.email}')"


class RecommendedMovies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    release_date = db.Column(db.String(15), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(120), nullable=False)


class GenrePreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    genre = db.Column(db.String(20), nullable=False)  # Assuming storing genre as a string

    def __repr__(self):
        return f"Genre_Preferences(user_id={self.user_id}, genre={self.genre})"


class MoviePreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie = db.Column(db.String(100), nullable=False)  # Can be adjusted we have long*** movie titles

    def __repr__(self):
        return f"Movie_Preferences(user_id={self.user_id}, genre={self.movie})"


with app.app_context():
    db.create_all()


# @app.route("/")
# @app.route("/home")
# def home():
#     return render_template('home.html', subtitle='Home Page', text='This is the home page!')


# @app.route("/about")
# def second_page():
#     return render_template('about.html', subtitle='about', text='This is the second page!')
def save_genre_preferences(user_id: int, genres: list[str]):
    for genre in genres:
        # Added it to do lower so that it works this way
        db.session.add(GenrePreferences(user_id=user_id, genre=genre.lower()))
    db.session.commit()
    print(f'Genre preferences saved for User:{user_id}')


def save_movie_preferences(user_id, movie_choices):
    for movie in movie_choices:
        db.session.add(MoviePreferences(user_id=user_id, movie=movie))
    db.session.commit()
    print(f'Movie preferences saved for User:{user_id}')


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():  
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already taken. Please use a different email.', 'danger')
            return redirect(url_for('register'))
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.email.data}!', 'success')
        return redirect(url_for('login'))  
    return render_template('register.html', title='Register', form=form)


@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            flash(f'Login successful for {form.email.data}', 'success')
            genre_preference_count = GenrePreferences.query.filter_by(user_id=user.id).count()
            movie_preference_count = MoviePreferences.query.filter_by(user_id=user.id).count()
            if genre_preference_count == 0 or movie_preference_count == 0:
                return redirect(url_for('preferences'))
            return redirect(url_for('results'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('login'))
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


def get_matched_upcoming_movies():
    genres = {
        28: "action",
        12: "adventure",
        16: "animation",
        35: "comedy",
        80: "crime",
        99: "documentary",
        18: "drama",
        10751: "family",
        14: "fantasy",
        36: "history",
        27: "horror",
        10402: "music",
        9648: "mystery",
        10749: "romance",
        878: "scifi",
        10770: "tv movie",
        53: "thriller",
        10752: "war",
        37: "western"
    }

    def normalize_genre_name(name):
        return re.sub(r'\W+', '', name.lower())

    def convert_id_to_genre_name(genre_id):
        return genres.get(genre_id, "Unknown")

    user_preferred_genres = GenrePreferences.query.filter_by(user_id=session['user_id']).all()
    preferred_genre_names = {normalize_genre_name(genre_preference.genre) for genre_preference in user_preferred_genres}
    upcoming_results = []

    url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={TMDB_API_KEY}'
    response = requests.get(url)

    if response.status_code == 200:
        upcoming_movies_json = response.json().get('results', [])
        for movie in upcoming_movies_json:
            movie_genre_names = {convert_id_to_genre_name(genre_id) for genre_id in movie['genre_ids']}
            if preferred_genre_names & movie_genre_names:
                full_genre_list = [convert_id_to_genre_name(genre_id) for genre_id in movie['genre_ids']]
                movie_entry = {
                    'title': movie['title'],
                    'release_date': movie['release_date'],
                    'rating': movie['vote_average'],
                    'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                    'genre': ', '.join(full_genre_list)
                }
                upcoming_results.append(movie_entry)
        return upcoming_results
    else:
        print(f"Error fetching upcoming movies: {response.status_code}")
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
                                                "and gives 30 specific movie recommendations as a response in a json format "
                                                "with the following keys: title, genre, rating out of 10 from IMDB, release date. "
                                                "Please provide the recommendations as one json string with the key 'recommendations' "
                                                "containing a list of 30 movies with their respective attributes. "
                                                "Use double quotes for all strings. Here is a sample format:\n\n"
                                                "{\n"
                                                "  \"recommendations\": [\n"
                                                "    {\n"
                                                "      \"title\": \"Movie Title\",\n"
                                                "      \"genre\": \"Genre\",\n"
                                                "      \"rating\": \"8.5\",\n"
                                                "      \"release_date\": \"YYYY-MM-DD\"\n"
                                                "    },\n"
                                                "    ... 29 more movies ...\n"
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
            'release_date': item['release_date']
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
    user_id = session.get('user_id')
    if not user_id:
        print("User ID not found in session.")
        return

    try:
        for recommendation in recommendations:
            title = recommendation.get('title')
            genre = recommendation.get('genre')
            rating = recommendation.get('rating')
            release_date = recommendation.get('release_date')

            if title and genre and rating and release_date:
                recommend_movie = RecommendedMovies(
                    title=title, genre=genre, rating=rating, release_date=release_date, user_id=user_id)
                db.session.add(recommend_movie)
            else:
                print(f"Skipping invalid recommendation: {recommendation}")

        db.session.commit()
        print('Movies successfully added')
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred: {e}")


@app.route('/preferences')
@login_required
def preferences():
    return render_template('preferences.html')


@app.route('/generate', methods=['POST'])
@login_required
def generate():
    movie_choices = request.form.get('choices-hidden').split('`')
    genres = request.form.get('genre-hidden').split('`')
    save_genre_preferences(session['user_id'], genres)
    save_movie_preferences(session['user_id'], movie_choices)
    recommendations = process_choices_and_recommendations(movie_choices, genres)
    if recommendations:
        modify_database(recommendations)
    else:
        print('Unable to process API Request and Convert to DB')

    return redirect(url_for('results'))

@app.route('/results')
@login_required
def results():
    if 'user_id' not in session:
        print('ERROR')
    recommendations = RecommendedMovies.query.filter_by(user_id=session['user_id']).limit(30).all()

    for rec in recommendations:
        rec.poster = get_movie_poster(rec.title)
    upcoming_movies = get_matched_upcoming_movies()

    return render_template('results.html',
                           # recommendations is a queryObject, upcoming is a Dict
                           recommendations=recommendations, upcoming_movies=upcoming_movies)

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
    app.run(host="0.0.0.0", port=8000, debug=True)