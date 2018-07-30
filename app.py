from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap
from flask_admin import Admin
import logging.handlers

app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('config.cfg')
app.config.from_pyfile('secret.cfg')

handler = logging.handlers.RotatingFileHandler('app.log', maxBytes=1024 * 1024)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)

mail = Mail(app)

db = SQLAlchemy(app)
from db.userdb import *

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submissionform import *
from db.submissiondb import Submission, save_Submission

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

migrate = Migrate(app, db)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', current_user=current_user)

@app.route('/submission', methods=['GET', 'POST'])
def submission():
    form = SubmissionForm()
    return render_template('submissioninp.html', form=form)

@app.route('/new_submission', methods=['GET', 'POST'])
def new_submission():
    form = SubmissionForm()

    if request.method == 'POST' and form.validate():
        sub = Submission()

    save_Submission(db,sub, form, True)

    return render_template('submissioninp.html', form=form)
