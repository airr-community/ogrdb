from flask import Flask, render_template, request, redirect, flash, url_for
from flask_security import current_user
from flask_sqlalchemy import SQLAlchemy
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
import json

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
from db.submission_list_table import *
from db.repertoiredb import *
from db.inference_tool_db import *
from db.genotype_db import *
from db.genotype_description_db import *
from db.genotype_upload import *
from db.genotype_view_table import *
from db.inferred_sequence_db import *

admin = Admin(app, template_mode='bootstrap3')
from forms.useradmin import *
from forms.submissionform import *
from forms.repertoireform import *
from forms.security import *
from forms.submissioneditform import *
from forms.aggregate_form import *
from forms.cancel_form import *
from forms.submission_view_form import *


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
            tables['mine'] = setup_submission_list_table(results, current_user)
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
                    tables['species'][sp] = setup_submission_list_table(results, current_user)
                    tables['species'][sp].table_id = sp

    q = db.session.query(Submission).filter_by(submission_status='published')
    results = q.all()
    tables['public'] = setup_submission_list_table(results, current_user)
    tables['public'].table_id = 'public'

    return render_template('submissionlist.html', tables=tables, show_completed=show_completed)

@app.route('/new_submission', methods=['GET', 'POST'])
@login_required
def new_submission():
    form = SubmissionForm()
    species = db.session.query(Committee.species).all()
    form.species.choices = [(s[0],s[0]) for s in species]
    r = db.session.query(func.max(Submission.id)).one_or_none()
    if r is not None:
        form.submission_id.data = "S%05d" % (r[0] + 1)
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
            # to avoid a race condition, make sure the submission_id reflects the value of the record id, now that we have one
            sub_id = (int)(sub.submission_id[1:])
            if sub_id != sub.id:
                sub.submission_id = "S%05d" % sub_id
                db.session.commit()
            return redirect(url_for('edit_submission', id=sub.submission_id))

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
    (tables, form) = setup_submission_edit_forms_and_tables(sub, db)

    tag = ''
    if request.method == 'POST':
        if form.validate():
            valid = True
            route = None
            added_id = None
            # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
            # this is a little more complex than it needs to be, because there's custom validation on some of the fields
            for table in tables.values():
                (added, route, added_id) = table.check_add_item(request, db)
                if added:
                    tag = table.name
                    break
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
                if route:
                    return redirect(url_for(route, id = added_id))
                if tag:
                    return redirect(url_for('edit_submission', id=id, _anchor=tag))
                return redirect(url_for('submissions'))
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

@app.route('/delete_submission/<id>', methods=['GET', 'POST'])
@login_required
def delete_submission(id):
    sub = check_sub_edit(id)
    if sub is not None:
        db.session.delete(sub)
        db.session.commit()
    return ''


@app.route('/submission/<id>')
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not sub.can_see(current_user):
        flash('Submission not found')
        return redirect('/submissions')
    else:
        tables = setup_submission_view_forms_and_tables(sub, db, sub.can_edit(current_user))
        return render_template('submissionview.html', sub=sub, tables=tables)


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

    form = AggregateForm(InferenceToolForm(), CancelForm())

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor= 'tools'))

        if form.validate():
            save_InferenceTool(db, tool, form, new=False)
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor='tools'))
    else:
        populate_InferenceTool(db, tool, form)

    return render_template('inference_tool_edit.html', form=form, submission_id=tool.submission.submission_id, id=id)

def check_tool_view(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_see(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool


@app.route('/inference_tool/<id>', methods=['GET'])
def inference_tool(id):
    tool = check_tool_view(id)
    if tool is None:
        return redirect('/')

    table = make_InferenceTool_view(tool, tool.submission.can_edit(current_user))
    return render_template('inference_tool_view.html', table=table)


def check_genotype_description_edit(id):
    try:
        desc = db.session.query(GenotypeDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None
        elif not desc.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


@app.route('/edit_genotype_description/<id>', methods=['GET', 'POST'])
@login_required
def edit_genotype_description(id):
    desc = check_genotype_description_edit(id)
    if desc is None:
        return redirect('/')

    if len(desc.submission.inference_tools) < 1:
        flash('Please create at least one Inference Tool entry before editing a Genotype.')
        return redirect(url_for('edit_submission', id=desc.submission.submission_id))

    form = AggregateForm(GenotypeDescriptionForm(), CancelForm())
    setting_names = []
    for tool in desc.submission.inference_tools:
        setting_names.append(( str(tool.id), tool.tool_settings_name))
    form.inference_tool_id.choices = setting_names

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))

        if form.validate():
            try:
                if form.genotype_file.data:
                    form.genotype_filename.data = form.genotype_file.data.filename
                    save_GenotypeDescription(db, desc, form, new=False)
                    desc.genotype_file = form.genotype_file.data.read()
                    db.session.commit()
                    blob_to_genotype(desc, db)
                else:
                    save_GenotypeDescription(db, desc, form, new=False)

                return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))
            except ValidationError as e:
                return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)
    else:
        populate_GenotypeDescription(db, desc, form)

        if desc.inference_tool is not None:
            form.inference_tool_id.data = desc.inference_tool_id

    return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)


def check_genotype_description_view(id):
    try:
        desc = db.session.query(GenotypeDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None
        elif not desc.submission.can_see(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


@app.route('/genotype/<id>')
def genotype(id):
    desc = check_genotype_description_view(id)
    if desc is None:
        return redirect('/')

    tables = {}
    tables['desc'] = make_GenotypeDescription_view(desc, False)
    tables['desc'].items.append({"item": "Tool/Settings", "value": desc.inference_tool.tool_settings_name, "tooltip": ""})
    tables['genotype'] = setup_gv_table(desc)
    return render_template('genotype_view.html', desc=desc, tables=tables)


# AJAX - Return JSON structure listing sequence names and Genotype ids, given a GenotypeDesc id
@app.route('/get_genotype_seqnames/<id>', methods=['POST'])
@login_required
def get_genotype_seqnames(id):
    desc = check_genotype_description_edit(id)
    if desc is None:
        return []

    ret = []
    for g in desc.genotypes:
        ret.append({"id": g.id, "name": g.sequence_id})

    return json.dumps(ret)


def check_inferred_sequence_edit(id):
    try:
        desc = db.session.query(InferredSequence).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None
        elif not desc.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc

@app.route('/edit_inferred_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_inferred_sequence(id):
    seq = check_inferred_sequence_edit(id)
    if seq is None:
        return redirect('/')

    if len(seq.submission.genotype_descriptions) < 1:
        flash('Please create at least one Genotype before editing inferred sequences.')
        return redirect(url_for('edit_submission', id=seq.submission.submission_id))

    form = AggregateForm(InferredSequenceForm(), CancelForm())
    form.genotype_id.choices = [(str(desc.id), desc.genotype_name) for desc in seq.submission.genotype_descriptions]
    if seq.genotype_description is not None:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.genotype_description.genotypes]
    else:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.submission.genotype_descriptions[0].genotypes]

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor='genotype_description'))

        # Update choices for sequence_id to reflect the selected genotype, provided we have a valid genotype
        # if anything goes wrong, field validation will sort it out

        try:
            for desc in seq.submission.genotype_descriptions:
                if int(form.genotype_id.data) == desc.id:
                    form.sequence_id.choices = [(str(genotype.id), genotype.sequence_id) for genotype in desc.genotypes]
        except:
            pass

        if form.validate():
            try:
                if form.sequence_id.data == '':
                    form.sequence_id.errors.append('Please select a sequence from the genotype. Upload data to the genotype if no sequences are listed.')
                    raise ValidationError()
                save_InferredSequence(db, seq, form, new=False)
                return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor= 'inferred_sequence'))
            except ValidationError as e:
                return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id)
    else:
        populate_InferredSequence(db, seq, form)
        form.genotype_id.data = str(seq.genotype_id) if seq.genotype_id else ''
        form.sequence_id.data = str(seq.sequence_id) if seq.sequence_id else ''


    return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id)



