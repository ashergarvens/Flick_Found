import os


# created config file in case we need to use more api keys in future
# basically our app inherits all this when created

class Config:
    API_KEY = os.getenv('OPENAI_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
