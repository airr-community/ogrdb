# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Form definitions for user with flask-security

from flask_security import RegisterForm
from wtforms import StringField, BooleanField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm


class ExtendedRegisterForm(RegisterForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institution and Postal Address', [DataRequired()])
    accepted_terms = BooleanField('I accept the <a href="/render_page/privacy_statement.html" target="_blank">Privacy</a> and <a href="/render_page/licensing_statement.html" target="_blank">Licensing</a> statements')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institution and Postal Address', [DataRequired()])
    reduce_emails = BooleanField('Only send mail directly relating to my submissions')
    active = BooleanField('Account is active (uncheck to deactivate)')


def save_Profile(db, object, form, new=False):
    object.name = form.name.data
    object.address = form.address.data

    if new:
        db.session.add(object)

    db.session.commit()


class FirstAccountForm(FlaskForm):
    name = StringField('Full Name', [DataRequired()])
    email = EmailField('Email', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
