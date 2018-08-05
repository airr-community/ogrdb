# ORM definitions for misclellaneous non schema generated tables

from app import db

class Committee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    committee = db.Column(db.String(80), unique=True)
    species = db.Column(db.String(80), unique=True)
