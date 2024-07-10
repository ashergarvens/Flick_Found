import os
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import openai
from openai import OpenAI
import json
from bs4 import BeautifulSoup

app = Flask(__name__)

# API configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
openai.api_key = OPENAI_API_KEY

def ul_to_py_list(html_file):
    with open(html_file, 'r', encoding='utf-8') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract choices list
    choices_ul = soup.find('ul', id='choices-list')
    choices_list = [li.text.strip() for li in choices_ul.find_all('li')] if choices_ul else []

    # Extract genre list
    genre_ul = soup.find('ul', id='genre-list')
    genre_list = [li.text.strip() for li in genre_ul.find_all('li')] if genre_ul else []

    return choices_list, genre_list

def get_upcoming_movies(tmbd_api_key):
    # calls to get upcoming movies -> we can process them to get chatgpt recommendations 
    url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={tmdb_api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['results']
    else:
        return []

    response = requests.get(url, headers=headers)

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
            'releaseDate': item['release_date']
        })
    return processed_recommendations
        

def process_choices_and_recommendations(movie_choices, recommendations):
    while True:
        try:
            recommendtaions = generate_recommendations(movie_choices, recommendations)
            processed_recommendations = process_response(recommendations)
            return processed_recommendations
        except KeyError:
            print('There was a key error when converting the response to the proper dictionary. Retrying GPT request...')


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
    choices, genres = ul_to_py_list('index.html')
    # choices = request.form.getlist('choices-list') # todo MUST FIX AFTER index.html UPDATED
    # preferences = request.form['preferences']

    recommendations = process_choices_and_recommendations(choices, genres)
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
