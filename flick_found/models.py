from app import db

class PreferredGenre(db.Model):
    id = db.Column(db.Integer, primary_key=True)