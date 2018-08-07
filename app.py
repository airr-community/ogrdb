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
from flask_table import Table, Col, LinkCol
import logging.handlers
import datetime
import sys

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

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submissionform import *
from forms.repertoireform import *
from forms.pubmedform import *
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

class DelCol(Col):
    def td_format(self, content):
        #return '<input type="submit" value="Del" id="pmid_del_%s" name="pmid_del_%s" >' % (content, content)
        return '<button id="pmid_del_%s" name="pmid_del_%s" type="submit" value="Del" class="btn btn-xs btn-danger"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>'  % (content, content)

def setup_sub_forms_and_tables(sub):
    if len(sub.repertoire) == 0:
        sub.repertoire.append(Repertoire())
        db.session.commit()

    submission_form = SubmissionForm(obj = sub)
    species = db.session.query(Committee.species).all()
    submission_form.species.choices = [(s[0],s[0]) for s in species]

    repertoire_form = RepertoireForm(obj = sub.repertoire)
    pubmed_form = PubMedForm()
    form = SubEditForm(submission_form, repertoire_form, pubmed_form)

    # Build a dynamic version of PubMedForm, with a delete field attribute for each id
    # Link the fields to a column in the pubmed_table

    pubmed_table = make_PubId_table(sub.repertoire[0].pub_ids, classes=['table table-bordered'])
    pubmed_table.add_column('id', DelCol(''))
    foo=pubmed_table.__html__()
    dynform = PubMedForm
    for pmid in sub.repertoire[0].pub_ids:
        setattr(dynform, 'pmid_del_%d' % pmid.id, SubmitField('Del'))

    return (pubmed_table, form)

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
    (pubmed_table, form) = setup_sub_forms_and_tables(sub)

    if request.method == 'POST':
        if form.validate_on_submit():
            if form.add_pubmed.data:
                try:
                    res = get_pmid_details(request.form['pubmed_id'])
                    p = PubId()
                    p.pub_title = res['title']
                    p.pub_authors = res['authors']
                    p.pubmed_id = request.form['pubmed_id']
                    sub.repertoire[0].pub_ids.append(p)
                    db.session.commit()
                    pubmed_table = make_PubId_table(sub.repertoire[0].pub_ids, classes=['table table-bordered'])
                except ValueError as e:
                    exc_value = sys.exc_info()[1]
                    form.pubmed_id.errors = [exc_value.args[0]]
            else:
                for field in form.pubmed_form._fields:
                    if 'pmid_del_' in field and form.pubmed_form[field].data:
                        for p in sub.repertoire[0].pub_ids:
                            if p.id == int(field.replace('pmid_del_', '')):
                                sub.repertoire[0].pub_ids.remove(p)
                                db.session.commit()
                                break

    return render_template('submissionedit.html', form = form, id=id, pubmed_table=pubmed_table)

@app.route('/submission/<id>')
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not sub.can_see(current_user):
        flash('Submission not found')
        return redirect('/submissions')
    else:
        table = make_Submission_view(sub, sub.can_edit(current_user))
        return render_template('submissionview.html', sub=sub, table=table)
