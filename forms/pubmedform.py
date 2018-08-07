#Flaskform definition for PubMed form

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, SubmitField

class PubMedForm(FlaskForm):
    pubmed_id = IntegerField('PubMed Id')
    add_pubmed = SubmitField()