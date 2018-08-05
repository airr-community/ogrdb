from flask import Flask, render_template, request, redirect, flash
from flask_security import current_user
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
from db.userdb import User

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submissionform import *
from db.submissiondb import *
from forms.security import *

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

migrate = Migrate(app, db)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj = current_user)
    form.email = ''
    if request.method == 'POST':
        if form.validate():
            save_Profile(db, current_user, form)
            flash('Profile updated.')

    return render_template('profile.html', form=form, current_user=current_user, url='profile')

@app.route('/submissions', methods=['GET', 'POST'])
def submissions():
    tables = {}
    show_completed = False

    if current_user.is_authenticated:
        q = db.session.query(Submission).join(Submission.owner).filter(User.email==current_user.email)
        results = q.all()
        if len(results) > 0:
            tables['mine'] = make_Submission_table(results)

        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp):
                if 'completed' in request.args and request.args['completed'] == 'yes':
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing', 'complete']))
                    show_completed = True
                else:
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing']))
                    show_completed = False
                results = q.all()
                if len(results) > 0:
                    if 'species' not in tables:
                        tables['species'] = {}
                    tables['species'][sp] = make_Submission_table(results)

    q = db.session.query(Submission).filter_by(submission_status='published')
    results = q.all()
    tables['public'] = make_Submission_table(results)

    return render_template('submissionlist.html', tables=tables, show_completed=show_completed)

@app.route('/new_submission', methods=['GET', 'POST'])
@login_required
def new_submission():
    form = SubmissionForm()
    species = db.session.query(Committee.species).all()
    form.species.choices = [(s[0],s[0]) for s in species]
    r = db.session.query(func.max(Submission.submission_id)).one_or_none()
    if r is not None:
        form.submission_id.data = "S%05d" % (int(r[0][1:]) + 1)
    else:
        form.submission_id.data = 1
    form.submission_status.data = 'draft'
    form.submission_date.data = datetime.date.today()
    form.population_ethnicity.data = 'UN'
    form.submitter_name.data = current_user.name
    form.submitter_address.data = current_user.address
    form.submitter_phone.data = current_user.phone

    if request.method == 'POST':
        if form.validate():
            sub = Submission()
            sub.owner = current_user
            save_Submission(db, sub, form, True)
            return redirect('/')

    return render_template('submissioninp.html', form=form, url='new_submission')

@app.route('/submission/<id>')
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not sub.can_see(current_user):
        flash('Submission not found')
        return redirect('/submissions')
    else:
        table = make_Submission_view(sub, sub.can_edit(current_user))
        return render_template('submissionview.html', sub=sub, table=table)
