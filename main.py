import pandas as pd
import os
import openai
from openai import OpenAI
import json
import sqlalchemy as db

my_api_key = os.getenv('OPENAI_KEY')
openai.api_key = my_api_key


def getUserInput() -> list[str]:
    print('\nPlease enter up to 5 choices for movies',
          'to base the recommendations off of. ')
    choices = []
    while len(choices) < 5:
        choice = input('Enter your choices here or type S to stop: ')
        if choice == 'S':
            if len(choices) == 0:
                print("You must enter at least one choice before quitting.")
            else:
                break
        elif not choice:
            print("Choice cannot be empty. Please enter a valid movie. ")
        else:
            choices.append(choice)
    return choices


def additionalQuestion():
    print("\nIs there a specific genre you prefer for the recommendations?")

    preferences = input("Enter your preferences here or enter None: ")

    if preferences.lower() == "none":
        return ""
    return preferences


def userFeedback():
    print("Sorry to hear that, please give me some",
          "feedback so I can improve your recommendations")
    feedback = input("Enter your feedback here: ")
    return feedback


def sendApiRequest(choices, preferences, feedback):
    print("\nProcessing request....")
    while True:
        try:
            if feedback:
                feedback = "Use this feedback in your response: ", feedback
            client = OpenAI(
                api_key=my_api_key,
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
            formatted = json.loads(completion.choices[0].message.content)
            return formatted
        except json.JSONDecodeError:
            print("There is a json decode error")


def process_response(formatted_data):
    recommendations = []
    for item in formatted_data['recommendations']:
        data = {
            'title': item['title'],
            'genre': item['genre'],
            'rating': item['rating'],
            'releaseDate': item['release date']
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


def menu(c, p):
    choices, preferences = c, p
    feedback = None
    while True:
        print("Menu Options:")
        print("1. Add recommendations")
        print("2. Change genre preference")
        print("3. Update feedback")
        print("4. Regenerate new recommendations")
        print("5. Quit")
        choice = input("Enter your choice: ")
        if choice == '1':
            choices = getUserInput()
        elif choice == '2':
            preferences = additionalQuestion()
        elif choice == '3':
            feedback = userFeedback()
            if not feedback:
                print("Thank you for using Movie Recommendations Bot!")
                return
        elif choice == '4':
            response = process_response(
                sendApiRequest(choices, preferences, feedback))
            modify_database(response)
        elif choice == '5':
            print("Thank you for using Movie Recommendations Bot!")
            return
        else:
            continue


if __name__ == '__main__':
    # choices = getUserInput()
    # choices = ["Spiderman: Far from home", "Ironman", "Thor",
    # "Hulk", "Black Widow"]
    choices = getUserInput()
    preferences = additionalQuestion()
    formatted_response = sendApiRequest(choices, preferences, "")
    response = process_response(formatted_response)
    modify_database(response)
    print("\nDo you like your recommendations? type Y or N")
    answer = input("Enter your choice here: ")

    if answer == 'Y':
        print("Thank you for using Movie Recommendations Bot!")
    elif answer == 'N':
        menu(choices, preferences)
