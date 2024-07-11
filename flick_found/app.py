import os
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import openai
from openai import OpenAI
import json
from flask import Flask, render_template, url_for, flash, redirect, request
from forms import RegistrationForm, LoginForm
from flask_behind_proxy import FlaskBehindProxy
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

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
            flash(f'Login successful for {form.email.data}', 'success')
            return redirect(url_for('results'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


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
def preferences():
    return render_template('preferences.html')



@app.route('/generate', methods=['POST'])
def generate():
    choices = request.form.get('choices-hidden').split('`')
    genres = request.form.get('genre-hidden').split('`')
    recommendations = process_choices_and_recommendations(choices, genres)
    if recommendations:
        modify_database(recommendations)
    else:
        print('Unable to process API Request and Convert to DB')

    return redirect(url_for('results'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        genre = request.form['genre']
        return redirect(url_for('results', genre=genre))
    return render_template('search.html')


@app.route('/results')
@app.route('/results/<genre>')
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


if __name__ == '__main__':
    app.run(debug=True)
