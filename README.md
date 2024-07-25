# Movie Recommendation Bot
[![Check Style](https://github.com/ashergarvens/recommendation_bot/actions/workflows/style.yaml/badge.svg)](https://github.com/ashergarvens/recommendation_bot/actions/workflows/style.yaml)
[![Tests](https://github.com/ashergarvens/recommendation_bot/actions/workflows/tests.yaml/badge.svg)](https://github.com/ashergarvens/recommendation_bot/actions/workflows/tests.yaml)

## Overview
We are trying to solve the problem of finding a new show or movie to watch that is personalized based 
the users preferences or preferred genre. The user would be asked questions and give a couple examples 
of previous shows or movies that they have watched.

The project interfaces with the ChatGPT API, Python, and SQL.

Bot asks questions based off preferences such as genre or media that the user already likes. 
Then, format into a prompt sent to the ChatGPT API. Get a response and process the response and get 
it back to the user. The user can decide if they want more information. Finally, the data gets 
transfered into a database where users can see the results or recall them later.


## Usefulness and Technology
* Ex users: People who want more recommendations for shows and movies and cannot get them elsewhere
* Simplest block could be: getting user input and sending it to the bot.
* Other aspects to add value: Add a ratings API to give the user more info about the recommendations.

## Project Setup & Libraries
```
pip install -r requirements.txt
```
## API key
- set your API key as an environmental variable

## Running the program
```
python3 main.py
```

## Script Details
- GetUserInput() collects up to 5 movies choices from the user
- additionalQuestion() asks for a users genre preference
- userFeedback() collects feedback from the user if they want to change anything from their recommendations
- sendApiRequest() sends a request to OpenAI API for the movie recommendations
- process_response() processes the API and formats the dictionary to go into the DataFrame
- modify_database() stores the recommendations into the SQLite databse
- queryDatabase() user inputs genre to search for in the database
- queryDatabaseWrapper() function to get user input until user stops
- menu() prints the menu

## Database Details
 - stores the movie recommendations using SQLite
 - has attributes: 'tite', 'genre' , 'rating', and 'releaseDate'


