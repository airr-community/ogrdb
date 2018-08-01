from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date
from sqlalchemy.sql import func
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from flask_table import Table, Col
import logging.handlers
import datetime

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
from db.submissiondb import *

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

@app.route('/submissions', methods=['GET', 'POST'])
def submissions():
    q = db.session.query(Submission)
    results = q.all()
    table = Submission_table(results)
    return render_template('submissionlist.html', table=table)

@app.route('/new_submission', methods=['GET', 'POST'])
def new_submission():
    form = SubmissionForm()
    r = db.session.query(func.max(Submission.submission_id)).one_or_none()
    if r is not None:
        form.submission_id.data = "S%05d" % (int(r[0][-1:]) + 1)
    else:
        form.submission_id.data = 1
    form.submission_status.data = 'draft'
    form.submission_date.data = datetime.date.today()
    form.population_ethnicity.data = 'UN'

    if request.method == 'POST':
        if form.validate():
            sub = Submission()
            save_Submission(db, sub, form, True)
            return redirect('/')

    return render_template('submissioninp.html', form=form, url='new_submission')
