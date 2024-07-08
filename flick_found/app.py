import os

from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import openai
from openai import OpenAI
import json

app = Flask(__name__)

# API configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
openai.api_key = OPENAI_API_KEY


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


def generate_recommendations(choices, preferences, feedback):
    print("\nProcessing request....")
    while True:
        try:
            if feedback:
                feedback = "Use this feedback in your response: ", feedback
            client = OpenAI(
                api_key=OPENAI_API_KEY,
            )
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Please give me a "
                                                  f"recommendation based on "
                                                  f"these movies here "
                                                  f"{choices} "
                                                  f"and with the preferences "
                                                  f"{preferences}."
                                                  f"{feedback}."},

                    {"role": "user",
                     "content": "You are a movie recommendation"
                                "bot that takes in similar movies and gives 10"
                                "specific movie recommendation as a "
                                "response in a "
                                "json""format with the following keys: "
                                "title, genre, rating out"
                                "of 10 from IMDB, release date. "
                                "Please do it as one"
                                "json string with the key as "
                                "recommendations with a"
                                "list of 10 movies with their "
                                "respective attributes. and"
                                "use double quotes and also please "
                                "end with a closing"
                                "curly bracket"}
                ]
            )
            # print(completion.choices[0].message.content)
            recommendations = json.loads(completion.choices[0].message.content)
            return recommendations
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
            'releaseDate': item['release date']
        })
    return processed_recommendations


def modify_database(recommendations):
    df = pd.DataFrame.from_dict(recommendations)
    engine = create_engine('sqlite:///media_recommendations.db')
    if not df.empty:
        df.to_sql('recommendations', con=engine, if_exists='replace', index=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    choices = request.form.getlist('choices')
    preferences = request.form['preferences']
    feedback = request.form['feedback']

    response = generate_recommendations(choices, preferences, feedback)
    recommendations = process_response(response)
    modify_database(recommendations)

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
