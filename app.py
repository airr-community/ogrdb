from flask import Flask, render_template, request, redirect, flash, url_for
from flask_security import current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date
from sqlalchemy.sql import func
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from wtforms import SubmitField, IntegerField
from flask_table import Table, Col, LinkCol
import logging.handlers
import datetime
import sys
from copy import deepcopy

from get_pmid_details import get_pmid_details

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
from db.submissiondb import *
from db.repertoiredb import *
from db.inference_tool_db import *

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submissionform import *
from forms.repertoireform import *
from forms.security import *
from forms.submissioneditform import *


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
            tables['mine'].table_id = 'mine'

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
                    tables['species'][sp].table_id = sp

    q = db.session.query(Submission).filter_by(submission_status='published')
    results = q.all()
    tables['public'] = make_Submission_table(results)
    tables['public'].table_id = 'public'

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
    form.submitter_email.data = current_user.email
    form.submitter_name.data = current_user.name
    form.submitter_address.data = current_user.address
    form.submitter_phone.data = current_user.phone

    if request.method == 'POST':
        if form.validate():
            sub = Submission()
            sub.owner = current_user
            save_Submission(db, sub, form, True)
            return redirect('/')

    return render_template('submissionnew.html', form=form, url='new_submission')

def check_sub_edit(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None:
        flash('Submission not found')
        return None
    elif not sub.can_edit(current_user):
        flash('You do not have rights to edit that submission')
        return None
    return sub


@app.route('/edit_submission/<id>', methods=['GET', 'POST'])
@login_required
def edit_submission(id):
    sub = check_sub_edit(id)
    if sub is None:
        return redirect('/submissions')
    (tables, form) = setup_sub_forms_and_tables(sub, db)

    tag = ''
    if request.method == 'POST':
        if form.validate():
            valid = True
            # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
            # this is a little more complex than it needs to be, because there's custom validation on some of the fields
            for table in tables.values():
                if table.check_add_item(request):
                    db.session.commit()
                    tag = table.name
                if table.process_deletes(db):
                    db.session.commit()
                    tag = table.name
                for field in table.form:
                    if len(field.errors) > 0:
                        tag = table.name
                        valid = False

            save_Submission(db, sub, form, False)
            save_Repertoire(db, sub.repertoire[0], form, False)
            if valid:
                return redirect(url_for('edit_submission', id=id, _anchor=tag if tag else ''))
            else:
                return render_template('submissionedit.html', form = form, id=id, tables=tables, jump = '#' + tag if tag else None)

        # Jump to the table section wirh an error, if any
        for table in tables.values():
            for field in table.form:
                if len(field.errors) > 0:
                    tag = table.name
    else:
        populate_Submission(db, sub, form)
        populate_Repertoire(db, sub.repertoire[0], form)

    return render_template('submissionedit.html', form = form, id=id, tables=tables, jump = '#' + tag if tag else None)

@app.route('/submission/<id>')
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not sub.can_see(current_user):
        flash('Submission not found')
        return redirect('/submissions')
    else:
        table = make_Submission_view(sub, sub.can_edit(current_user))
        return render_template('submissionview.html', sub=sub, table=table)


def check_tool_edit(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool

@app.route('/edit_tool/<id>', methods=['GET', 'POST'])
@login_required
def edit_tool(id):
    tool = check_tool_edit(id)
    if tool is None:
        return redirect('/')

    form = InferenceToolForm()

    if request.method == 'POST':
        if form.validate():
            save_InferenceTool(db, tool, form, new=False)
    else:
        populate_InferenceTool(db, tool, form)

    return render_template('inference_tool_edit.html', form=form, submission_id=tool.submission.submission_id, id=id)
