from flask_wtf import FlaskForm
from wtforms import SubmitField

class CancelForm(FlaskForm):
    cancel = SubmitField('Cancel')