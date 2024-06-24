import pandas
import os 
import openai
from openai import OpenAI
import pandas
import sqlalchemy

my_api_key = os.getenv('OPENAI_KEY')
openai.api_key = my_api_key

def getUserInput() -> list[str]:
    print('Please enter up to 5 choices for movies or TV shows to base the recommendations off of. ')
    choices = []
    while len(choices) <= 5:
        choices.append(input('Enter your choice here: ').strip())
    return choices