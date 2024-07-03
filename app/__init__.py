from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# config files import here and is used to actually form the app
# with all the attachments such as sql and Config

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app
