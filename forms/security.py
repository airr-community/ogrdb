# Form definitions for user with flask-security

from flask_security import RegisterForm
from wtforms import StringField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

class ExtendedRegisterForm(RegisterForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institutional Address', [DataRequired()])

class ProfileForm(FlaskForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institutional Address', [DataRequired()])

def save_Profile(db, object, form, new=False):
    object.name = form.name.data
    object.address = form.address.data

    if new:
        db.session.add(object)

    db.session.commit()

