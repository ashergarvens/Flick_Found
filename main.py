import pandas as pd
import os 
import openai
from openai import OpenAI
import json
import sqlalchemy as db

my_api_key = os.getenv('OPENAI_KEY')
openai.api_key = my_api_key

def getUserInput() -> list[str]:
    print('Please enter up to 5 choices for movies or TV shows to base the recommendations off of. ')
    choices = []
    while len(choices) < 5:
        choices.append(input('Enter your choice here: ').strip())
    return choices

def sendApiRequest (choices):
    client = OpenAI(
        api_key=my_api_key,
    )
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": f"Please give me a recommendation based on these shows here {choices}"},
        {"role": "user", "content": "You are a movie and show recommendation bot that takes in similar tv shows or movies and give 10 specifc movie or tv show recommendation as a response in a json format with the following keys: title, genre, rating out of 10 from IMDB, description, release date. Please do it as one json string with the key as recommendations with a list of 10 movies with their respective attributes. and use double quotes"}]
    )
    # print(completion.choices[0].message.content)
    formatted = json.loads(completion.choices[0].message.content)
    # print(formatted)
    return formatted

def process_response(formatted_data):
    recommendations = []
    for item in formatted_data['recommendations']:
        data = {
            'title' : item['title'],
            'genre' : item['genre'],
            'rating' : item['rating'],
            'description' : item['description'],
            'releaseDate' : item['release date']
        }
        recommendations.append(data)
    return recommendations

def modify_database(recommendations):
    df = pd.DataFrame.from_dict(recommendations)
    engine = db.create_engine('sqlite:///media_recommendations.db')
    if not df.empty:
        df.to_sql(
            'recommendations', con=engine, if_exists='replace', index=False
        )
        with engine.connect() as connection:
            result = connection.execute(
                db.text("SELECT * from recommendations;")
            ).fetchall()
            print(pd.DataFrame(result))

# choices = getUserInput()
choices = ["Spiderman: Far from home", "Ironman", "Thor", "Hulk", "Black Widow"]
formatted_response = sendApiRequest(choices)
response = process_response(formatted_response)
modify_database(response)
