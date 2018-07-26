from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, current_user, login_required
from flask_security.forms import RegisterForm, ConfirmRegisterForm
from wtforms import StringField, TextAreaField
from flask_wtf import FlaskForm 
from datetime import datetime
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('config.cfg')
app.config.from_pyfile('secret.cfg')

mail = Mail(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)


roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(250))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))

class ExtendRegisterForm(RegisterForm):
    name = StringField('Name')
    username = StringField('Username')

class ExtendConfirmRegisterForm(ConfirmRegisterForm):
    name = StringField('Name')
    username = StringField('Username')

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
#security = Security(app, user_datastore, register_form=ExtendRegisterForm, confirm_register_form=ExtendConfirmRegisterForm)
security = Security(app, user_datastore)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', current_user=current_user)

