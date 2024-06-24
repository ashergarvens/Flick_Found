## README file
### Project Pitch
1. Show and Movie Recommendation Bot
2. We are trying to solve the problem of finding a new show or movie to watch that is personalized based 
   the users preferences or preferred genre. The user would be asked questions and give a couple examples 
   of previous shows or movies that they have watched.
3. The project interfaces with the ChatGPT API, a user, the terminal, Python, and SQL.
4. The inputs are the questions that the bot asks you and the user inputs.
5. The outputs are the recommendations that the bot outputs like TV shows or movies that are then 
   saved into the database.
6. Bot asks questions based off preferences such as genre or media that the user already likes. 
   Then, format into a prompt sent to the ChatGPT API. Get a response and process the response and get 
   it back to the user. The user can decide if they want more information. Finally, the data gets 
   transfered into a database where users can see the results or recall them later.
7. Bot giving bad or inaccurate information. Or the user giving bad requests to the AI.
8. When we get good recommendations from the bot and we have no errors in the code.

### Usefulness and Technology
* Ex users: People who want more recommendations for shows and movies and cannot get them elsewhere
* Simplest block could be: getting user input and sending it to the bot.
* Other aspects to add value: Add a ratings API to give the user more info about the recommendations.

#### Program Architecture
* Ideas:
* Make files with different parts of the process ie one module with all SQL stuff, one with all prompt stuff, one with main entry point
* Make functions for most of the work to make it modular in case we want to expand.
