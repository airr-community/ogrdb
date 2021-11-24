# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import Flask, render_template, request, redirect, Response, Blueprint, jsonify
from flask_security import current_user
from flask_security.utils import hash_password
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore, login_required, logout_user
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from sqlalchemy import and_, or_
from sqlalchemy.sql.expression import func


import json
from Bio import SeqIO
import io
from os.path import isdir
from os import mkdir, remove
from operator import attrgetter



app = Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_pyfile('config.cfg')
app.config.from_pyfile('secret.cfg')

# Check log file can be opened for writing, default otherwise

from traceback import format_exc

try:
    with(open(app.config["LOGPATH"], 'w')) as fp:
        pass
except:
    app.config["LOGPATH"] = 'app.log'

ncbi_api_key = app.config['NCBI_API_KEY']

admin_obj = Admin(app, template_mode='bootstrap3')

# Make the attachment directory, if it doesn't exist

attach_path = app.config['ATTACHPATH'] + '/'
if not isdir(attach_path):
    mkdir(attach_path)

user_attach_path = attach_path + 'user/'
if not isdir(user_attach_path):
    mkdir(user_attach_path)

db = SQLAlchemy(app)
# At the moment files are stored MEME encoded, so this needs to be at least 2 or 3 times max file size
#db.session.execute('SET @@GLOBAL.max_allowed_packet=134217728')

mail = Mail(app)
from mail import send_mail


from textile_filter import *
from journal import *
from db.userdb import User
from db.submission_db import *
from db.submission_list_table import *
from db.sequence_list_table import *
from db.repertoire_db import *
from db.inference_tool_db import *
from db.genotype_db import *
from db.genotype_description_db import *
from db.genotype_upload import *
from db.genotype_view_table import *
from db.inferred_sequence_db import *
from db.journal_entry_db import *
from db.notes_entry_db import *
from db.germline_set_db import *
from db.germline_set_list_table import *
from db.gene_description_db import *
from db.inferred_sequence_table import *
from db.germline_set_table import *
from db.primer_set_db import *
from db.primer_db import *
from db.record_set_db import *
from db.sample_name_db import *
from db.attached_file_db import *
from db.dupe_gene_note_db import *
from db.sequence_identifier_db import *

import db_events

from forms.useradmin import *
from forms.submission_form import *
from forms.repertoire_form import *
from forms.security import *
from forms.submission_edit_form import *
from forms.aggregate_form import *
from forms.cancel_form import *
from forms.submission_view_form import *
from forms.journal_entry_form import *
from forms.sequence_new_form import *
from forms.germline_set_new_form import *
from forms.germline_set_gene_form import *
from forms.gene_description_form import *
from forms.gene_description_notes_form import *
from forms.germline_set_form import *
from forms.sequence_view_form import *
from forms.germline_set_view_form import *
from forms.primer_set_edit_form import *
from forms.genotype_stats_form import *
from forms.genotype_view_options_form import *
from forms.inferred_sequence_compound_form import *
from forms.genotype_description_compound_form import *
from forms.sequences_species_form import *

from genotype_stats import *
from get_ncbi_details import *
from to_airr import *

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
migrate = Migrate(app, db)

security = Security(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

from custom_logging import init_logging

init_logging(app, mail)

# Read IMGT germline reference sets

from imgt.imgt_ref import init_imgt_ref, init_igpdb_ref, init_vdjbase_ref, get_imgt_reference_genes

init_imgt_ref()
init_igpdb_ref()
init_vdjbase_ref()

# Initialise REST API

from api.restplus import api
from api.sequence.sequence import ns as sequence
from api.sequence.germline import ns as germline

blueprint = Blueprint('api', __name__, url_prefix='/api')
api.init_app(blueprint)
api.add_namespace(sequence)
api.add_namespace(germline)
app.register_blueprint(blueprint)


@app.route('/', methods=['GET', 'POST'])
def index():
    # Add the admin user, if we don't have one yet

    if user_datastore.find_role('Admin') is None:
        return redirect(url_for('create_user'))

    # Add the test role if we are in UAT

    if 'UAT' in app.config and app.config['UAT']:
        if not user_datastore.find_role('Test'):
            user_datastore.create_role(name = 'Test')
        tc = db.session.query(Committee).filter(Committee.species == 'Test').count()
        if tc < 1:
            test_ctee = Committee()
            test_ctee.species = 'Test'
            test_ctee.committee = 'Test Committee'
            db.session.add(test_ctee)
            db.session.commit()
        if current_user.is_authenticated and not current_user.has_role('Test'):
            user_datastore.add_role_to_user(current_user, 'Test')
            db.session.commit()

    # Get news from Wordpress

    news_items = []

    try:
        cat_url = None
        wp_url = app.config['WORDPRESS_NEWS_URL'] + app.config['WORDPRESS_REST']
        r = requests.get(wp_url + 'categories')
        if r.status_code == 200:
            resp = r.content.decode("utf-8")
            resp = json.loads(resp)

            for rec in resp:
                if rec['slug'] == 'ogrdb_news':
                    cat_url = '%sposts?categories=%s' % (wp_url, rec['id'])

        if cat_url:
            r = requests.get(cat_url + '&per_page=5')
            if r.status_code == 200:
                resp = r.content.decode("utf-8")
                resp = json.loads(resp)

                for item in resp:
                    news_items.append({
                    'date': item['date'].split('T')[0],
                    'title': item['title']['rendered'],
                    'excerpt': item['excerpt']['rendered'],
                    'link': item['link'],
                })
    except:
        pass


    return render_template('index.html', current_user=current_user, news_items=news_items)


@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if user_datastore.find_role('Admin') is not None:
        return redirect('/')

    form = FirstAccountForm()

    if request.method == 'POST':
        if form.validate():
            user = user_datastore.create_user(email=form.email.data, password=hash_password(form.password.data), name=form.name.data, confirmed_at='2018-11-14')
            db.session.commit()
            user_datastore.create_role(name='Admin')
            user_datastore.add_role_to_user(user, 'Admin')
            db.session.commit()
            flash("User created")
            return redirect('/')

    return render_template('security/first_account.html', form=form)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj = current_user)
    form.email = ''
    if request.method == 'POST':
        if form.validate():
            if 'disable_btn' in request.form:
                current_user.active = False
                save_Profile(db, current_user, form)
                flash('Account disabled.')
                logout_user()
                return redirect('/')
            else:
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
        tables['mine'] = setup_submission_list_table(results, current_user)
        tables['mine'].table_id = 'mine'

        delegated_species = {}
        for sub in current_user.delegated_submissions:
            delegated_species[sub.species] = True

        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp) or sp in delegated_species:
                if 'completed' in request.args and request.args['completed'] == 'yes':
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing', 'complete', 'withdrawn']))
                    show_completed = True
                else:
                    q = db.session.query(Submission).filter(Submission.species==sp).filter(Submission.submission_status.in_(['reviewing']))
                    show_completed = False
                results = q.all()

                if 'species' not in tables:
                    tables['species'] = {}
                tables['species'][sp] = setup_submission_list_table(results, current_user)
                tables['species'][sp].table_id = sp

    q = db.session.query(Submission).filter_by(public=1)
    results = q.all()
    tables['public'] = setup_submission_list_table(results, current_user)
    tables['public'].table_id = 'public'

    return render_template('submission_list.html', tables=tables, show_completed=show_completed)


@app.route('/new_submission', methods=['GET', 'POST'])
@login_required
def new_submission():
    form = SubmissionForm()
    species = db.session.query(Committee.species).all()
    form.species.choices = [(s[0],s[0]) for s in species]
    form.submission_status.data = 'draft'
    form.submission_date.data = datetime.date.today()
    form.population_ethnicity.data = 'UN'
    form.submitter_email.data = current_user.email
    form.submitter_name.data = current_user.name
    form.submitter_address.data = current_user.address

    if request.method == 'POST':
        if form.validate():
            sub = Submission()
            sub.owner = current_user
            sub.submission_status = 'draft'
            save_Submission(db, sub, form, True)
            sub.submission_id = "S%05d" % sub.id
            db.session.commit()
            return redirect(url_for('edit_submission', id=sub.submission_id))

    return render_template('submission_new.html', form=form, url='new_submission')


def check_sub_edit(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None:
        flash('Submission not found')
        return None
    elif not sub.can_edit(current_user):
        flash('You do not have rights to edit that submission')
        return None
    return sub


def check_sub_view(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None:
        flash('Submission not found')
        return None
    elif not sub.can_see(current_user):
        flash('You do not have rights to view that submission')
        return None
    return sub

def check_sub_attachment_edit(id):
    af = db.session.query(AttachedFile).filter_by(i =id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    sub = af.notes_entry.submission
    if not sub.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_sub_attachment_view(id):
    af = db.session.query(AttachedFile).filter_by(id = id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    sub = af.notes_entry.submission
    if not sub.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af

@app.route('/edit_submission/<id>', methods=['GET', 'POST'])
@login_required
def edit_submission(id):
    sub = check_sub_edit(id)
    if sub is None:
        return redirect('/submissions')

    (tables, form) = setup_submission_edit_forms_and_tables(sub, db)

    if request.method == 'GET':
        populate_Submission(db, sub, form)
        populate_Repertoire(db, sub.repertoire[0], form)
        form.repository_select.data = sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else 'Other'
        return render_template('submission_edit.html', form=form, id=id, tables=tables, attachment=len(sub.notes_entries[0].attached_files) > 0)

    missing_sequence_error = False
    validation_result = ValidationResult()
    try:
        if 'save_btn' in request.form or 'save_close_btn' or 'submit_btn' in request.form:
            if not form.validate():
                if 'submit_btn' in request.form:
                    raise ValidationError()

                # Overlook empty field errors when saving to draft
                nonblank_errors = False
                for field in form._fields:
                    if len(form._fields[field].errors) > 0:
                        if len(form._fields[field].data) == 0:
                            form._fields[field].errors = []
                        else:
                            nonblank_errors = True
                if nonblank_errors:
                    raise ValidationError()

        # Check if this is an NCBI related repertoire, and, if so, validate accession number and update related fields

        choice = form.repository_select.data
        update_sra_rep_details(form)

        # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
        validation_result = process_table_updates(tables, request, db)
        if not validation_result.valid:
            raise ValidationError()

        if 'submit_btn' in request.form:
            # Check we have at least one inferred sequence
            if len(sub.inferred_sequences) == 0:
                missing_sequence_error = True
                validation_result.tag = 'inferred_sequence'
                raise ValidationError()

            sub.submission_status = 'reviewing'
            add_history(current_user, 'Submission submitted to IARC %s Committee for review' % sub.species, sub, db)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [current_user.email], 'user_submission_submitted', user=current_user, submission=sub)
            send_mail('Submission %s submitted to IARC %s Committee for review' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_received', user=current_user, submission=sub)
            db.session.commit()
            flash('Submission %s has been submitted to IARC for review.' % id)
            return redirect(url_for('submissions'))

        # We've gone too far off-piste to use form initialisation or process() to push field values into the object
        # The main problem is that not all object attributes are represented in the form, for example submission_id
        # if these were present as hidden fields, maybe we could use process()

        if ('save_btn' in request.form or 'save_close_btn' or 'submit_btn' in request.form or 'upload_btn' in request.form):
            for (k, v) in request.form.items():
                if hasattr(sub, k):
                    setattr(sub, k, v)
                elif hasattr(sub.repertoire[0], k):
                    setattr(sub.repertoire[0], k, v)

            # update fields that may have been fetched from NCBI

            sub.repertoire[0].repository_name = form.repository_name.data
            sub.repertoire[0].dataset_url = form.dataset_url.data
            sub.repertoire[0].rep_title = form.rep_title.data

            db.session.commit()

            if 'notes_attachment' in request.files:
                for file in form.notes_attachment.data:
                    af = None
                    for at in sub.notes_entries[0].attached_files:
                        if at.filename == file.filename:
                            af = at
                            break
                    if af is None:
                        af = AttachedFile()
                    af.notes_entry = sub.notes_entries[0]
                    af.filename = file.filename
                    db.session.add(af)
                    db.session.commit()
                    dirname = attach_path + sub.submission_id

                    try:
                        if not isdir(dirname):
                            mkdir(dirname)
                        with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                            fo.write(file.stream.read())
                    except:
                        info = sys.exc_info()
                        flash('Error saving attachment: %s' % (info[1]))
                        app.logger.error(format_exc())
                        return redirect(url_for('edit_submission', id=sub.submission_id))

            if 'notes_text' in request.form:
                sub.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')

            db.session.commit()
            form.repository_select.data = sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else 'Other'

        if validation_result.route:
            return redirect(url_for(validation_result.route, id = validation_result.id))
        if validation_result.tag:
            return redirect(url_for('edit_submission', id=id, _anchor=validation_result.tag))

        if 'save_btn' in request.form or 'upload_btn' in request.form:
            tag = request.form['current_tab'].split('#')[1] if '#' in request.form['current_tab'] else '#sub'
            return redirect(url_for('edit_submission', id=id, _anchor=tag))
        else:
            return redirect(url_for('submissions'))

    except ValidationError as e:
        # If we don't have a tag, find an error to jump to
        if not validation_result.tag:
            repform = type(RepertoireForm())
            for subform in form.subforms:
                if type(subform) is repform:
                    for field in subform:
                        if len(field.errors) > 0:
                            validation_result.tag = 'rep'
                            break
                    break

        if not validation_result.tag:
            for table in tables.values():
                for field in table.form:
                    if len(field.errors) > 0:
                        validation_result.tag = table.name
                        break

        return render_template('submission_edit.html', form=form, id=id, tables=tables, jump = validation_result.tag, missing_sequence_error=missing_sequence_error)


@app.route('/download_submission_attachment/<id>')
def download_submission_attachment(id):
    att = check_sub_attachment_view(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + sub.submission_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_submission_attachment/<id>', methods=['POST'])
def delete_submission_attachment(id):
    att = check_sub_attachment_edit(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + sub.submission_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/delete_submission/<id>', methods=['GET', 'POST'])
@login_required
def delete_submission(id):
    sub = check_sub_edit(id)
    if sub is not None:
        repo = sub.repertoire[0].repository_name if sub.repertoire[0] else ''
        acc = sub.repertoire[0].rep_accession_no if sub.repertoire[0] else ''
        app.logger.info('User %s deleted submission: species %s, repository %s, accession %s' % (current_user.email, sub.species, repo, acc))

        sub.delete_dependencies(db)
        db.session.delete(sub)
        db.session.commit()
    return ''


@app.route('/submission/<id>', methods=['GET', 'POST'])
def submission(id):
    sub = db.session.query(Submission).filter_by(submission_id = id).one_or_none()
    if sub is None or not (sub.can_see(current_user) or current_user.has_role('Admin')):
        flash('Submission not found')
        return redirect('/submissions')

    (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))
    reviewer = (current_user.has_role(sub.species) or current_user in sub.delegates)

    if request.method == 'GET':
        return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump="", status=sub.submission_status, attachment=len(sub.notes_entries[0].attached_files) > 0)
    else:
        if not reviewer:
            flash('Submission not found')
            return redirect('/submissions')

        # Check for additions/deletions to editable tables, and any errors flagged up by validation in check_add_item
        editable_tables = {'delegate_table': tables['delegate_table']}
        validation_result = process_table_updates(editable_tables, request, db)
        if validation_result.tag:
            if validation_result.valid:     # rebuild tables if something has changed
                (form, tables) = setup_submission_view_forms_and_tables(sub, db, sub.can_see_private(current_user))
            return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)

        if form.validate():
            if form.action.data == 'draft':
                add_note(current_user, form.title.data, safe_textile('Submission returned to Submitter with the following message:\r\n\r\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission returned to Submitter', sub, db)
                send_mail('Submission %s returned to you from the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s returned to Submitter by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_returned', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'draft'
                db.session.commit()
                flash('Submission returned to Submitter')
                return redirect('/submissions')
            elif form.action.data == 'complete':
                add_note(current_user, form.title.data, safe_textile('Submission completed with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission completed', sub, db)
                send_mail('Submission %s completed review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s completed review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_completed', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'complete'
                db.session.commit()
                flash('Submission marked as complete')
                return redirect('/submissions')
            elif form.action.data == 'withdraw':
                referenced_gds = []
                for inf in sub.inferred_sequences:
                    for gd in inf.gene_descriptions:
                        if gd.status not in ('superceded', 'withdrawn'):
                            referenced_gds.append(gd.description_id)
                if len(referenced_gds) > 0:
                    flash('Please remove references to this submission in sequence(s) %s first.' % ','.join(referenced_gds))
                    return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)
                add_note(current_user, form.title.data, safe_textile('Submission withdrawn with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission withdrawn', sub, db)
                send_mail('Submission %s has been marked as withdrawn by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_withdrawn', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s has been marked as withdrawn by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_withdrawn', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'withdrawn'
                db.session.commit()
                flash('Submission marked as withdrawn')
                return redirect('/submissions')
            elif form.action.data == 'review':
                add_note(current_user, form.title.data, safe_textile('Submission returned to IARC Review with the following message to the Submitter:\n\n' + form.body.data), sub, db)
                add_history(current_user, 'Submission returned to Review', sub, db)
                send_mail('Submission %s returned to review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.submitter_email], 'user_submission_re_review', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                send_mail('Submission %s returned to review by the IARC %s Committee' % (sub.submission_id, sub.species), [sub.species], 'iarc_submission_re_review', reviewer=current_user, user_name=sub.submitter_name, submission=sub, comment=form.body.data)
                sub.submission_status = 'reviewing'
                db.session.commit()
                flash('Submission returned to Review')
                return redirect('/submissions')
            elif form.action.data == 'note':
                add_note(current_user, form.title.data, form.body.data, sub, db)
                db.session.commit()
                flash('Note Added')
                return redirect(url_for('submission', id=id, _anchor='review'))
            elif form.type.data == 'note':      #reply to thread
                head = db.session.query(JournalEntry).filter_by(submission_id = sub.id, type = 'note', id = int(form.action.data)).one_or_none()
                add_note(current_user, head.title, form.body.data, sub, db, parent_id=int(form.action.data))
                db.session.commit()
                flash('Note Added')
                return redirect(url_for('submission', id=id, _anchor='review'))
            else:
                return redirect('/submissions')

        else:
           return render_template('submission_view.html', sub=sub, tables=tables, form=form, reviewer=reviewer, id=id, jump = validation_result.tag, status=sub.submission_status)


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


# AJAX - delete tool and associated data
@app.route('/delete_tool/<id>', methods=['POST'])
@login_required
def delete_tool(id):
    tool = check_tool_edit(id)
    if tool is not None:
        tool.delete_dependencies(db)
        db.session.delete(tool)
        db.session.commit()
    return ''



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

    for item in table.items:
        if (item['item'] == 'Starting Database' or item['item'] == 'Settings') and len(item['value']) > 0 :
            item['value'] = Markup(safe_textile(item['value']))

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

    form = setup_genotype_description_form(desc)
    form.locus.choices = [(x,x) for x in db.session.query(Committee).filter(Committee.species==desc.submission.species).one_or_none().loci.replace(' ', '').split(',')]
    form.sequence_type.choices = [(x,x) for x in db.session.query(Committee).filter(Committee.species==desc.submission.species).one_or_none().sequence_types.replace(' ', '').split(',')]
    sam_table = LinkedSample_table(desc.sample_names)
    srr_table = LinkedRecordSet_table(desc.record_set)
    repo = desc.submission.repertoire[0].repository_name if desc.submission.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))

        if form.validate():
            try:
                if form.genotype_name.data != desc.genotype_name and form.genotype_name.data in [d.genotype_name for d in desc.submission.genotype_descriptions]:
                    form.genotype_name.errors.append('There is already a genotype description with that name.')
                    raise ValidationError()

                update_sample_details(desc, form, repo)
                sam_table = LinkedSample_table(desc.sample_names)
                srr_table = LinkedRecordSet_table(desc.record_set)

                if form.genotype_file.data:
                    form.genotype_filename.data = form.genotype_file.data.filename
                    save_GenotypeDescription(db, desc, form, new=False)

                    dirname = attach_path + desc.submission.submission_id

                    try:
                        if not isdir(dirname):
                            mkdir(dirname)
                        with open(dirname + '/genotype_%s.csv' % desc.id, 'w', newline='') as fo:
                            fo.write(form.genotype_file.data.read().decode("utf-8"))
                    except:
                        info = sys.exc_info()
                        flash('Error saving genotype file: %s' % (info[1]))
                        app.logger.error(format_exc())
                        return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id)

                    for g in desc.genotypes:
                        db.session.delete(g)
                    db.session.commit()
                    file_to_genotype(dirname + '/genotype_%s.csv' % desc.id, desc, db)
                else:
                    form.genotype_filename.data = desc.genotype_filename       # doesn't get passed back in request as the field is read-only
                    save_GenotypeDescription(db, desc, form, new=False)

                if 'save_close_genotype' in request.form:
                    return redirect(url_for('edit_submission', id=desc.submission.submission_id, _anchor= 'genotype_description'))
            except ValidationError as e:
                return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id, ncbi=(repo is not None), sam_table=sam_table, srr_table=srr_table)
    else:
        populate_GenotypeDescription(db, desc, form)
        if desc.inference_tool is not None:
            form.inference_tool_id.data = str(desc.inference_tool_id)
            form.inference_tool_id.default = str(desc.inference_tool_id)

    return render_template('genotype_description_edit.html', form=form, submission_id=desc.submission.submission_id, id=id, ncbi=(repo is not None), sam_table=sam_table, srr_table=srr_table)


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

@app.route('/genotype_e/<id>', methods=['GET', 'POST'])
def genotype_e(id):
    return genotype(id, True)

# 'editable' parameter indicates whether links back to the submission should be editable or not
@app.route('/genotype/<id>', methods=['GET', 'POST'])
def genotype(id, editable=False):
    desc = check_genotype_description_view(id)
    if desc is None:
        return redirect('/')
    sub = desc.submission
    reviewer = (current_user.has_role(sub.species) or current_user in sub.delegates)

    sam_table = LinkedSample_table(desc.sample_names)
    srr_table = LinkedRecordSet_table(desc.record_set)
    srr_table.rec_accession_no.name = 'Record Set'
    ncbi = desc.submission.repertoire[0].repository_name in ('NCBI SRA', 'ENA')

    form = GenotypeViewOptionsForm()
    tables = {}
    tables['desc'] = make_GenotypeDescription_view(desc, False)

    if ncbi:
        for item in list(tables['desc'].items):
            if item['item'] == 'Sample IDs' or item['item'] == 'Sequence Sets':
                tables['desc'].items.remove(item)

    tables['desc'].items.append({"item": "Tool/Settings", "value": desc.inference_tool.tool_settings_name, "tooltip": ""})
    (tables['genotype'], tables['inferred']) = setup_gv_table(desc)
    fasta = setup_gv_fasta(desc)
    submission_link = 'edit_submission' if editable else 'submission'
    this_link = 'genotype_e' if editable else 'genotype'
    title = "Genotype '%s' (Submission %s)" % (desc.genotype_name, sub.submission_id)

    if request.method == 'POST':
        if form.validate():
            new_items = []
            for item in tables['genotype'].items:
                if form.sub_only.data:
                    if len(item.inferred_sequences) == 0:
                        continue
                if (form.occ_threshold.data > 0 and (item.sequences is None or item.sequences < form.occ_threshold.data)):
                    continue
                if (form.freq_threshold.data > 0 and (item.unmutated_frequency is None or item.unmutated_frequency < form.freq_threshold.data)):
                    continue
                new_items.append(item)
            tables['genotype'].items = new_items

    return render_template('genotype_view.html', form=form, desc=desc, tables=tables, id=id, fasta=fasta, reviewer=reviewer, sub_id=sub.submission_id, submission_link=submission_link, this_link=this_link, srr_table=srr_table, sam_table=sam_table, ncbi=ncbi, title=title)

@app.route('/download_genotype/<id>')
def download_genotype(id):
    desc = check_genotype_description_view(id)
    if desc is None:
        return redirect('/')

    try:
        dirname = attach_path + desc.submission.submission_id
        with open(dirname + '/genotype_%s.csv' % desc.id) as fi:
            return Response(fi.read(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=%s" % desc.genotype_filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving genotype file: %s' % (info[1]))
        app.logger.error(format_exc())
        return redirect(url_for('genotype', id=desc.id))

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

    return jsonify(ret)

# AJAX - delete genotype and associated data
@app.route('/delete_genotype/<id>', methods=['POST'])
@login_required
def delete_genotype(id):
    desc = check_genotype_description_edit(id)
    if desc is not None:
        desc.delete_dependencies(db)
        db.session.delete(desc)
        db.session.commit()
    return ''

@app.route('/inferred_sequence/<id>', methods=['GET'])
def inferred_sequence(id):
    seq = db.session.query(InferredSequence).filter_by(id = id).one_or_none()
    if seq is None:
        flash('Record not found')
        return redirect('/')
    elif not seq.submission.can_see(current_user):
        flash('You do not have rights to view that entry')
        return redirect('/')

    sub = seq.submission
    repo =  sub.repertoire[0].repository_name if sub.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    table = make_InferredSequence_view(seq)
    srr_table = LinkedRecordSet_table(seq.record_set)

    for i in range(len(table.items)-1, -1, -1):
        if table.items[i]['value'] is None or table.items[i]['item'] == 'Extension?' or (table.items[i]['item'] == 'Select sets' and repo):
            del(table.items[i])
        elif table.items[i]['item'] == 'Accession Number' and repo == 'NCBI SRA':
            table.items[i]['value'] = Markup('<a href="https://www.ncbi.nlm.nih.gov/nuccore/%s">%s</a>' % (table.items[i]['value'], table.items[i]['value']))
        elif table.items[i]['item'] == 'Accession Number' and repo == 'ENA':
            table.items[i]['value'] = Markup('<a href="https://www.ebi.ac.uk/ena/data/view/%s">%s</a>' % (table.items[i]['value'], table.items[i]['value']))

    return render_template('inferred_sequence_view.html', table=table, sub_id=sub.submission_id, seq_id=seq.sequence_details.sequence_id, srr_table = srr_table, ncbi=(repo is not None))


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

def validate_ext(c_seq, c_start, c_end):
    if c_seq.data or c_start.data or c_end.data:
        for control in [c_seq, c_start, c_end]:
            if control.data is None:
                control.errors.append('Field cannot be empty.')
                raise ValidationError()
        for control in [c_start, c_end]:
            if int(control.data) < 1 or int(control.data) > 1100:
                control.errors.append('co-ordinate is implausible.')
                raise ValidationError()
        if int(c_start.data) > int(c_end.data):
            c_end.errors.append('End co-ordinate must be greater than or equal to start co-ordinate')
            raise ValidationError()
        if len(c_seq.data) != int(c_end.data) - int(c_start.data) + 1:
            c_seq.errors.append('Co-ordinates do not match sequence length.')
            raise ValidationError()


@app.route('/edit_inferred_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_inferred_sequence(id):
    seq = check_inferred_sequence_edit(id)
    if seq is None:
        return redirect('/')

    if len(seq.submission.genotype_descriptions) < 1:
        flash('Please create at least one Genotype before editing inferred sequences.')
        return redirect(url_for('edit_submission', id=seq.submission.submission_id))

    form = setup_inferred_sequence_form(seq)
    srr_table = LinkedRecordSet_table(seq.record_set)
    repo = seq.submission.repertoire[0].repository_name if seq.submission.repertoire[0].repository_name in ('NCBI SRA', 'ENA') else None

    if repo is None:
        form.seq_record_title.type = 'HiddenField'

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor='inferred_sequence'))

        # Update choices for sequence_id to reflect the selected genotype, provided we have a valid genotype
        # if anything goes wrong, field validation will sort it out

        try:
            for desc in seq.submission.genotype_descriptions:
                if int(form.genotype_id.data) == desc.id:
                    form.sequence_id.choices = [(str(genotype.id), genotype.sequence_id) for genotype in desc.genotypes]
        except:
            pass

        # Clean out the extension fields if we are not using them, so they can't fail validation
        if not form.inferred_extension.data:
            for control in [form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext, form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext]:
                control.data = None

        if form.validate():
            try:
                if form.sequence_id.data == '':
                    form.sequence_id.errors.append('Please select a sequence from the genotype. Upload data to the genotype if no sequences are listed.')
                    raise ValidationError()

                for sequence in seq.submission.inferred_sequences:
                    if sequence is not seq and str(sequence.sequence_id) == form.sequence_id.data and str(sequence.genotype_id) == form.genotype_id.data:
                        form.sequence_id.errors.append('That inferred sequence is already listed in the submission.')
                        raise ValidationError()

                if form.inferred_extension.data:
                    validate_ext(form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext)
                    validate_ext(form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext)
                    if not(form.ext_3prime.data or form.ext_5prime.data):
                        form.inferred_extension.errors.append('Please specify an extension at at least one end')
                        raise ValidationError()

                update_inf_rep_details(seq, form, repo)
                save_InferredSequence(db, seq, form, new=False)
                srr_table = LinkedRecordSet_table(seq.record_set)

                if 'save_close_sequence' in request.form:
                    return redirect(url_for('edit_submission', id=seq.submission.submission_id, _anchor= 'inferred_sequence'))
            except ValidationError as e:
                return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id, ncbi=repo is not None, srr_table=srr_table)
    else:
        populate_InferredSequence(db, seq, form)
        form.genotype_id.data = str(seq.genotype_id) if seq.genotype_id else ''
        form.sequence_id.data = str(seq.sequence_id) if seq.sequence_id else ''

    return render_template('inferred_sequence_edit.html', form=form, submission_id=seq.submission.submission_id, id=id, ncbi=repo is not None, srr_table=srr_table)


@app.route('/render_page/<page>')
def render_page(page):
    return render_template('static/%s' % page)

def check_seq_view(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id=id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_see(current_user):
            flash('You do not have rights to view that sequence.')

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

def check_seq_edit(seq_id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id=seq_id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_edit(current_user):
            flash('You do not have rights to edit that sequence.')
            return None

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_seq_see_notes(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if not desc.can_see_notes(current_user):
            flash('You do not have rights to view notes.')
            return None

        return desc

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

def check_seq_attachment_edit(id):
    af = db.session.query(AttachedFile).filter_by(id = id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    seq = af.gene_description
    if not seq.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_seq_attachment_view(id):
    af = db.session.query(AttachedFile).filter_by(id = id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    seq = af.gene_description
    if not seq.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af


def check_seq_draft(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if desc.status != 'published':
            flash('Only published sequences can be cloned.')
            return None

        clones = db.session.query(GeneDescription).filter_by(sequence_name = desc.sequence_name).all()
        for clone in clones:
            if clone.status == 'draft':
                flash('There is already a draft of that sequence')
                return None

        if not desc.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc

def check_seq_withdraw(id):
    try:
        desc = db.session.query(GeneDescription).filter_by(id = id).one_or_none()
        if desc is None:
            flash('Record not found')
            return None

        if desc.status != 'published':
            flash('Only published sequences can be withdrawn.')
            return None

        if not desc.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return desc


@app.route('/sequences/<sp>', methods=['GET', 'POST'])
def sequences(sp):
    tables = {}
    show_withdrawn = False

    species = [s[0] for s in db.session.query(Committee.species).all()]

    if sp not in species:
        return redirect('/')

    if current_user.is_authenticated:
        if current_user.has_role(sp):
            if 'species' not in tables:
                tables['species'] = {}
            tables['species'][sp] = {}

            if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
                q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft', 'withdrawn']))
                show_withdrawn = True
            else:
                q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft']))
                show_withdrawn = False
            results = q.all()

            tables['species'][sp]['draft'] = setup_sequence_list_table(results, current_user)
            tables['species'][sp]['draft'].table_id = sp + '_draft'

            q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level == '0')
            results = q.all()
            tables['species'][sp]['level_0'] = setup_sequence_list_table(results, current_user)
            tables['species'][sp]['level_0'].table_id = sp + '_level_0'

    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level != '0')
    results = q.all()
    tables['affirmed'] = setup_sequence_list_table(results, current_user)
    tables['affirmed'].table_id = 'affirmed'

    if len(db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.affirmation_level != '0', GeneDescription.species == sp).all()) >= 1:
        form = SpeciesForm()
        form.species.choices = [sp]
    else:
        form = None

    return render_template('sequence_list.html', tables=tables, show_withdrawn=show_withdrawn, form=form)

# Copy submitter and acknowledgements from sequence submission to gene_description



def copy_acknowledgements(seq, gene_description):
    def add_acknowledgement_to_gd(name, institution_name, orcid_id, gene_description):
        for ack in gene_description.acknowledgements:
            if ack.ack_name == name and ack.ack_institution_name == institution_name:
                return

        a = Acknowledgements()
        a.ack_name = name
        a.ack_institution_name = institution_name
        a.ack_ORCID_id = orcid_id
        gene_description.acknowledgements.append(a)

    add_acknowledgement_to_gd(seq.submission.submitter_name, seq.submission.submitter_address, '', gene_description)

    # Copy acknowledgements across

    for ack in seq.submission.acknowledgements:
        add_acknowledgement_to_gd(ack.ack_name, ack.ack_institution_name, ack.ack_ORCID_id, gene_description)


@app.route('/new_sequence/<species>', methods=['GET', 'POST'])
@login_required
def new_sequence(species):
    if not current_user.has_role(species):
        return redirect('/')

    form = NewSequenceForm()
    subs = db.session.query(Submission).filter(Submission.species==species).filter(Submission.submission_status.in_(['reviewing', 'complete', 'published'])).all()
    form.submission_id.choices = [('', 'Select Submission')] +  [(s.submission_id, '%s (%s)' % (s.submission_id, s.submitter_name)) for s in subs]
    form.sequence_name.choices = [(0, 'Select Sequence')]

    if request.method == 'POST':        # Don't use form validation because the selects are dynamically updated
        if form.cancel.data:
            return redirect(url_for('sequences', sp=species))

        if form.upload_file.data:
            return upload_sequences(form, species)

        try:
            if form.new_name.data is None or len(form.new_name.data) < 1:
                form.new_name.errors = ['Name cannot be blank.']
                raise ValidationError()

            if db.session.query(GeneDescription).filter(
                    and_(GeneDescription.species == species,
                         GeneDescription.sequence_name == form.new_name.data,
                         GeneDescription.species_subgroup == form.new_name.data,
                         ~GeneDescription.status.in_(['withdrawn', 'superceded']))).count() > 0:
                form.new_name.errors = ['A sequence already exists with that name.']
                raise ValidationError()

            record_type = request.form['record_type']
            if record_type == 'submission':
                if form.submission_id.data == '0' or form.submission_id.data == '' or form.submission_id.data == 'None':
                    form.submission_id.errors = ['Please select a submission.']
                    raise ValidationError()

                if form.sequence_name.data == '0' or form.sequence_name.data == '' or form.sequence_name.data == 'None':
                    form.sequence_name.errors = ['Please select a sequence.']
                    raise ValidationError()

                sub = db.session.query(Submission).filter_by(submission_id = form.submission_id.data).one_or_none()
                if sub.species != species or sub.submission_status not in ('reviewing', 'published', 'complete'):
                    return redirect(url_for('sequences', sp=species))

                seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

                if seq is None or seq not in sub.inferred_sequences:
                    return redirect(url_for('sequences', sp=species))

            gene_description = GeneDescription()
            gene_description.sequence_name = form.new_name.data
            gene_description.species = species
            gene_description.species_subgroup = form.species_subgroup.data
            gene_description.status = 'draft'
            gene_description.maintainer = current_user.name
            gene_description.lab_address = current_user.address
            gene_description.functional = True
            gene_description.inference_type = 'Rearranged Only' if record_type == 'submission' else 'Unrearranged Only'
            gene_description.release_version = 1
            gene_description.affirmation_level = 0

            if record_type == 'submission':
                gene_description.inferred_sequences.append(seq)
                gene_description.inferred_extension = seq.inferred_extension
                gene_description.ext_3prime = seq.ext_3prime
                gene_description.start_3prime_ext = seq.start_3prime_ext
                gene_description.end_3prime_ext = seq.end_3prime_ext
                gene_description.ext_5prime = seq.ext_5prime
                gene_description.start_5prime_ext = seq.start_5prime_ext
                gene_description.end_5prime_ext = seq.end_5prime_ext
                gene_description.sequence = seq.sequence_details.nt_sequence
                gene_description.locus = seq.genotype_description.locus
                gene_description.sequence_type = seq.genotype_description.sequence_type
                gene_description.coding_seq_imgt = seq.sequence_details.nt_sequence_gapped if gene_description.sequence_type == 'V' else seq.sequence_details.nt_sequence
                copy_acknowledgements(seq, gene_description)
            else:
                gene_description.inferred_extension = False
                gene_description.ext_3prime = None
                gene_description.start_3prime_ext = None
                gene_description.end_3prime_ext = None
                gene_description.ext_5prime = None
                gene_description.start_5prime_ext = None
                gene_description.end_5prime_ext = None
                gene_description.sequence = ''
                gene_description.locus = ''
                gene_description.sequence_type = 'V'
                gene_description.coding_seq_imgt = ''


            # Parse the name, if it's tractable

            try:
                sn = gene_description.sequence_name
                if sn[:2] == 'IG' or sn[:2] == 'TR':
                    if record_type == 'genomic':
                        gene_description.locus = sn[:3]
                        gene_description.sequence_type = sn[3]
                    if '-' in sn:
                        if '*' in sn:
                            snq = sn.split('*')
                            gene_description.allele_designation = snq[1]
                            sn = snq[0]
                        else:
                            gene_description.allele_designation = ''
                        snq = sn.split('-')
                        gene_description.subgroup_designation = snq[len(snq)-1]
                        del(snq[len(snq)-1])
                        gene_description.gene_subgroup = '-'.join(snq)[4:]
                    elif '*' in sn:
                        snq = sn.split('*')
                        gene_description.gene_subgroup = snq[0][4:]
                        gene_description.allele_designation = snq[1]
                    else:
                        gene_description.gene_subgroup = sn[4:]
            except:
                pass

            db.session.add(gene_description)
            db.session.commit()
            gene_description.description_id = "A%05d" % gene_description.id
            db.session.commit()
            if record_type == 'submission':
                gene_description.build_duplicate_list(db, seq.sequence_details.nt_sequence)
            return redirect(url_for('sequences', sp=species))

        except ValidationError as e:
            return render_template('sequence_new.html', form=form, species=species)


    return render_template('sequence_new.html', form=form, species=species)


def upload_sequences(form, species):
    # check file
    errors = []
    fi = io.StringIO(form.upload_file.data.read().decode("utf-8"))
    reader = csv.DictReader(fi)
    required_headers = ['gene_label', 'imgt', 'functional', 'type', 'inference_type', 'sequence', 'sequence_gapped', 'species_subgroup', 'subgroup_type', 'alt_names', 'affirmation']
    headers = None
    row_count = 2
    for row in reader:
        if headers is None:
            headers = row.keys()
            missing_headers = set(required_headers) - set(headers)
            if len(missing_headers) > 0:
                errors.append('Missing column headers: %s' % ','.join(list(missing_headers)))
                break
        if not row['gene_label']:
            errors.append('row %d: no gene label' % row_count)
        elif db.session.query(GeneDescription).filter(
                and_(GeneDescription.species == species,
                     GeneDescription.sequence_name == row['gene_label'],
                     GeneDescription.species_subgroup == row['species_subgroup'],
                     ~GeneDescription.status.in_(['withdrawn', 'superceded']))).count() > 0:
            errors.append('row %d: a gene with the name %s and subgroup %s is already in the database' % (row_count, row['gene_label'], row['species_subgroup']))
        if row['functional'] not in ['Y', 'N']:
            errors.append('row %d: functional must be Y or N' % row_count)
        if row['type'][:3] not in ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG']:
            errors.append('row %d: locus in type must be one of %s' % (row_count, ','.join(['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG'])))
        if row['type'][3:] not in ['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader']:
            errors.append('row %d: sequence_type in type must be one of %s' % (row_count, ','.join(['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader'])))
        if not row['sequence']:
            errors.append('row %d: no sequence' % row_count)
        if not row['sequence_gapped']:
            errors.append('row %d: no sequence_gapped' % row_count)

        try:
            level = int(row['affirmation'])
            if level < 0 or level > 3:
                errors.append('row %d: affirmation level must be an integer between 0 and 3' % row_count)
        except:
            errors.append('row %d: affirmation level must be an integer between 0 and 3' % row_count)

        if len(errors) >= 5:
            errors.append('(Only showing first few errors)')
            break

        row_count += 1

    if len(errors) > 0:
        errors.append('Sequences not uploaded: please fix errors and try again')
        form.upload_file.errors = errors
        return render_template('sequence_new.html', form=form, species=species)

    fi.seek(0)
    reader = csv.DictReader(fi)
    for row in reader:
        gene_description = GeneDescription()
        gene_description.sequence_name = row['gene_label']
        gene_description.imgt_name = row['imgt']
        gene_description.alt_names = row['alt_names']
        gene_description.species = species
        gene_description.species_subgroup = row['species_subgroup']
        gene_description.species_subgroup_type = row['subgroup_type']
        gene_description.status = 'draft'
        gene_description.maintainer = current_user.name
        gene_description.lab_address = current_user.address
        gene_description.functional = row['functional'] == 'Y'
        gene_description.inference_type = row['inference_type']
        gene_description.release_version = 1
        gene_description.affirmation_level = int(row['affirmation'])
        gene_description.inferred_extension = False
        gene_description.ext_3prime = None
        gene_description.start_3prime_ext = None
        gene_description.end_3prime_ext = None
        gene_description.ext_5prime = None
        gene_description.start_5prime_ext = None
        gene_description.end_5prime_ext = None
        gene_description.sequence = row['sequence']
        gene_description.locus = row['type'][0:3]
        gene_description.sequence_type = row['type'][3:]
        gene_description.coding_seq_imgt = row['sequence_gapped']

        notes = ['Imported to OGRDB with the following notes:']
        for field in row.keys():
            if field not in required_headers and len(row[field]):
                notes.append('%s: %s' % (field, row[field]))

        if len(notes) > 1:
            gene_description.notes = '\r\n'.join(notes)

        db.session.add(gene_description)
        db.session.commit()
        gene_description.description_id = "A%05d" % gene_description.id
        db.session.commit()

    return redirect(url_for('sequences', sp=species))

@app.route('/get_sequences/<id>', methods=['GET'])
@login_required
def get_sequences(id):
    sub = check_sub_view(id)
    if sub is None:
        return ('')

    seqs = []
    for seq in sub.inferred_sequences:
        if seq.gene_descriptions.count() == 0:
            seqs.append((seq.id, "Gen: %s  |  Subj: %s  |  Seq: %s" % (seq.genotype_description.genotype_name, seq.genotype_description.genotype_subject_id, seq.sequence_details.sequence_id)))
        else:
            add = True
            for desc in seq.gene_descriptions:
                if desc.status in ['published', 'draft']:
                    add = False
                    break

            if add:
                seqs.append((seq.id, "Gen: %s  |  Subj: %s  |  Seq: %s" % (seq.genotype_description.genotype_name, seq.genotype_description.genotype_subject_id, seq.sequence_details.sequence_id)))

    return json.dumps(seqs)


@app.route('/seq_add_inference/<id>', methods=['GET', 'POST'])
@login_required
def seq_add_inference(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    form = NewSequenceForm()
    subs = db.session.query(Submission).filter(Submission.species==seq.species).filter(Submission.submission_status.in_(['reviewing', 'complete', 'published'])).all()
    form.create.label.text = "Add"
    form.submission_id.choices = [('', 'Select Submission')] +  [(s.submission_id, '%s (%s)' % (s.submission_id, s.submitter_name)) for s in subs]
    form.sequence_name.choices = [(0, 'Select Sequence')]

    if request.method == 'POST':        # Don't use form validation because the selects are dynamically updated
        if form.cancel.data:
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

        try:
            if form.submission_id.data == '0' or form.submission_id.data == None or form.submission_id.data == 'None':
                form.submission_id.errors = ['Please select a submission.']
                raise ValidationError()

            if form.sequence_name.data == '0' or form.sequence_name.data == None or form.sequence_name.data == 'None':
                form.sequence_name.errors = ['Please select a sequence.']
                raise ValidationError()
        except ValidationError as e:
            return render_template('sequence_add.html', form=form, name=seq.sequence_name, id=id)

        sub = db.session.query(Submission).filter_by(submission_id = form.submission_id.data).one_or_none()
        if sub.species != seq.species or sub.submission_status not in ('reviewing', 'published', 'complete'):
            flash('Submission is for the wrong species, or still in draft.')
            return redirect('/')

        inferred_seq = db.session.query(InferredSequence).filter_by(id = int(form.sequence_name.data)).one_or_none()

        if inferred_seq is None or inferred_seq not in sub.inferred_sequences:
            flash('Inferred sequence cannot be found in that submission.')
            return redirect('/')

        seq.inferred_sequences.append(inferred_seq)
        copy_acknowledgements(inferred_seq, seq)

        db.session.commit()
        return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

    return render_template('sequence_add.html', form=form, name=seq.sequence_name, id=id)


@app.route('/seq_add_genomic/<id>', methods=['GET', 'POST'])
@login_required
def seq_add_genomic(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    form = GenomicSupportForm()

    if request.method == 'POST':
        if form.validate():
            if 'cancel' in request.form:
                return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

            support = None
            append = True
            if request.form['support_id'] != "":
                for s in seq.genomic_accessions:
                    if s.id == int(request.form['support_id']):
                        support = s
                        append = False
                        break

            if support is None:
                support = GenomicSupport()

            save_GenomicSupport(db, support, form, False)

            if append:
                db.session.add(support)
                seq.genomic_accessions.append(support)

            db.session.commit()
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

    return render_template('sequence_add_genomic.html', form=form, name=seq.sequence_name, id=id, support_id="", action="Add")


@app.route('/seq_edit_genomic/<seq_id>/<support_id>', methods=['GET', 'POST'])
@login_required
def seq_edit_genomic(seq_id, support_id):
    seq = check_seq_edit(seq_id)
    if seq is None:
        return redirect('/')

    support = db.session.query(GenomicSupport).filter_by(id=support_id).one_or_none()
    if support is None:
        return redirect(url_for('edit_sequence', id=seq_id, _anchor='inf'))

    form = GenomicSupportForm()
    if request.method == 'GET':
        populate_GenomicSupport(db, support, form)
        return render_template('sequence_add_genomic.html', form=form, name=seq.sequence_name, id=seq_id, action="Save", support_id=support_id)

    # POST goes back to seq_add_genomic

@app.route('/sequence/<id>', methods=['GET'])
def sequence(id):
    seq = check_seq_view(id)
    if seq is None:
        return redirect('/')

    form = FlaskForm()
    tables = setup_sequence_view_tables(db, seq, current_user.has_role(seq.species))
    versions = db.session.query(GeneDescription).filter(GeneDescription.species == seq.species)\
        .filter(GeneDescription.description_id == seq.description_id)\
        .filter(GeneDescription.status.in_(['published', 'superceded']))\
        .all()
    tables['versions'] = setup_sequence_version_table(versions, None)
    del tables['versions']._cols['sequence']
    del tables['versions']._cols['coding_seq_imgt']
    return render_template('sequence_view.html', form=form, tables=tables, sequence_name=seq.sequence_name)


@app.route('/edit_sequence/<id>', methods=['GET', 'POST'])
@login_required
def edit_sequence(id):
    seq = check_seq_edit(id)
    if seq is None:
        return redirect('/')

    tables = setup_sequence_edit_tables(db, seq)
    desc_form = GeneDescriptionForm(obj=seq)
    notes_form = GeneDescriptionNotesForm(obj=seq)
    hidden_return_form = HiddenReturnForm()
    history_form = JournalEntryForm()
    form = AggregateForm(desc_form, notes_form, history_form, hidden_return_form, tables['ack'].form)

    if request.method == 'POST':
        form.sequence.data = "".join(form.sequence.data.split())
        form.coding_seq_imgt.data = "".join(form.coding_seq_imgt.data.split())

        # Clean out the extension fields if we are not using them, so they can't fail validation
        if not form.inferred_extension.data:
            for control in [form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext, form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext]:
                control.data = None

        form.validate()
        valid = True

        for field in form._fields:
            if len(form[field].errors) > 0:
                if field in history_form._fields and 'history_btn' not in request.form:
                    form[field].errors = []
                else:
                    valid = False

        if form.action.data == 'published':
            for inferred_sequence in seq.inferred_sequences:
                if inferred_sequence.submission.submission_status == 'draft':
                    inferred_sequence.submission.submission_status = 'published'
                    valid = False
                if inferred_sequence.submission.submission_status == 'withdrawn':
                    flash("Can't publish this sequence: submission %s is withdrawn." % inferred_sequence.submission.submission_id)
                    valid = False

        if valid:
            try:
                validation_result = process_table_updates({'ack': tables['ack']}, request, db)
                if not validation_result.valid:
                    raise ValidationError()

                if form.inferred_extension.data:
                    validate_ext(form.ext_3prime, form.start_3prime_ext, form.end_3prime_ext)
                    validate_ext(form.ext_5prime, form.start_5prime_ext, form.end_5prime_ext)
                    if not(form.ext_3prime.data or form.ext_5prime.data):
                        form.inferred_extension.errors.append('Please specify an extension at at least one end')
                        raise ValidationError()

                if 'notes_attachment' in request.files:
                    for file in form.notes_attachment.data:
                        af = None
                        for at in seq.attached_files:
                            if at.filename == file.filename:
                                af = at
                                break
                        if af is None:
                            af = AttachedFile()
                        af.gene_description = seq
                        af.filename = file.filename
                        db.session.add(af)
                        db.session.commit()
                        dirname = attach_path + seq.description_id

                        try:
                            if not isdir(dirname):
                                mkdir(dirname)
                            with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                fo.write(file.stream.read())
                        except:
                            info = sys.exc_info()
                            flash('Error saving attachment: %s' % (info[1]))
                            app.logger.error(format_exc())
                            return redirect(url_for('edit_submission', id=seq.id))

                seq.notes = form.notes.data      # this was left out of the form definition in the schema so it could go on its own tab

                rearranged = len(seq.inferred_sequences) > 0
                genomic = len(seq.genomic_accessions) > 0
                if rearranged and genomic:
                    seq.inference_type = 'Genomic and rearranged'
                elif rearranged:
                    seq.inference_type = 'Rearranged'
                elif genomic:
                    seq.inference_type = 'Genomic'

                save_GeneDescription(db, seq, form)

                if 'add_inference_btn' in request.form:
                    return redirect(url_for('seq_add_inference', id=id))

                if 'upload_btn' in request.form:
                    return redirect(url_for('edit_sequence', id=id, _anchor='note'))

                if 'add_genomic_btn' in request.form:
                    return redirect(url_for('seq_add_genomic', id=id))

                if form.action.data == 'published':
                    publish_sequence(seq, form.body.data, True)
                    flash('Sequence published')
                    return redirect(url_for('sequences', sp=seq.species))

            except ValidationError:
                return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump=validation_result.tag, version=seq.release_version, attachment=len(seq.attached_files) > 0)

            if validation_result.tag:
                return redirect(url_for('edit_sequence', id=id, _anchor=validation_result.tag))
            else:
                return redirect(url_for('sequences', sp=seq.species))

        else:
            for field in tables['ack'].form:
                if len(field.errors) > 0:
                    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, jump='ack', version=seq.release_version, attachment=len(seq.attached_files) > 0)

    return render_template('sequence_edit.html', form=form, sequence_name=seq.sequence_name, id=id, tables=tables, version=seq.release_version, attachment=len(seq.attached_files) > 0)


def publish_sequence(seq, notes, email):
    old_seq = db.session.query(GeneDescription).filter_by(description_id=seq.description_id,
                                                          status='published').one_or_none()
    if old_seq:
        old_seq.status = 'superceded'
        old_seq.duplicate_sequences = list()
        seq.release_version = old_seq.release_version + 1
    else:
        seq.release_version = 1
    # Mark any referenced submissions as public
    for inferred_sequence in seq.inferred_sequences:
        sub = inferred_sequence.submission
        if not inferred_sequence.submission.public:
            inferred_sequence.submission.public = True
            db.session.commit()
            add_history(current_user, 'Submission published', sub, db)
            send_mail(
                'Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species),
                [sub.submitter_email], 'user_submission_published', reviewer=current_user, user_name=sub.submitter_name,
                submission=sub, sequence=seq)
            send_mail(
                'Submission %s accepted and published by the IARC %s Committee' % (sub.submission_id, sub.species),
                [sub.species], 'iarc_submission_published', reviewer=current_user, user_name=sub.submitter_name,
                submission=sub, sequence=seq)

        # Make a note in submission history if we haven't already
        title = 'Sequence %s listed in affirmation' % inferred_sequence.sequence_details.sequence_id
        entry = db.session.query(JournalEntry).filter_by(type='note', submission=sub, title=title).all()
        if not entry:
            add_note(current_user, title, safe_textile(
                '* Sequence: %s\n* Genotype: %s\n* Subject ID: %s\nis referenced in affirmation %s (sequence name %s)' %
                (inferred_sequence.sequence_details.sequence_id, inferred_sequence.genotype_description.genotype_name,
                 inferred_sequence.genotype_description.genotype_subject_id, seq.description_id, seq.sequence_name)),
                     sub, db)
    seq.release_date = datetime.date.today()
    add_history(current_user, 'Version %s published' % seq.release_version, seq, db, body=notes)

    if email:
        send_mail('Sequence %s version %d published by the IARC %s Committee' % (

    seq.description_id, seq.release_version, seq.species), [seq.species], 'iarc_sequence_released',
              reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment=notes)
    seq.release_description = notes
    seq.status = 'published'
    db.session.commit()


@app.route('/download_sequence_attachment/<id>')
def download_sequence_attachment(id):
    att = check_seq_attachment_view(id)
    if att is None:
        return redirect('/')

    seq = att.gene_description

    try:
        dirname = attach_path + seq.description_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_sequence_attachment/<id>', methods=['POST'])
def delete_sequence_attachment(id):
    att = check_seq_attachment_edit(id)
    if att is None:
        return redirect('/')

    seq = att.gene_description

    try:
        dirname = attach_path + seq.description_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/delete_sequence/<id>', methods=['POST'])
@login_required
def delete_sequence(id):
    seq = check_seq_edit(id)
    if seq is not None:
        seq.delete_dependencies(db)
        db.session.delete(seq)
        db.session.commit()
    return ''


@app.route('/add_inferred_sequence', methods=['POST'])
@login_required
def add_inferred_sequence():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        inferred_seq = db.session.query(InferredSequence).filter(InferredSequence.id==request.form['inf']).one_or_none()
        if inferred_seq is not None and inferred_seq not in seq.inferred_sequences:
            seq.inferred_sequences.append(inferred_seq)
            copy_acknowledgements(inferred_seq, seq)
            db.session.commit()

    return ''


@app.route('/delete_inferred_sequence', methods=['POST'])
@login_required
def delete_inferred_sequence():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        inferred_seq = db.session.query(InferredSequence).filter(InferredSequence.id==request.form['inf']).one_or_none()
        if inferred_seq is not None and inferred_seq in seq.inferred_sequences:
            seq.inferred_sequences.remove(inferred_seq)
            db.session.commit()

    return ''


@app.route('/add_supporting_observation', methods=['POST'])
@login_required
def add_supporting_observation():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        genotype = db.session.query(Genotype).filter(Genotype.id==request.form['gid']).one_or_none()
        if genotype is not None and genotype not in seq.supporting_observations:
            seq.supporting_observations.append(genotype)
            copy_acknowledgements(genotype.genotype_description, seq)
            db.session.commit()

    return ''


@app.route('/delete_supporting_observation', methods=['POST'])
@login_required
def delete_supporting_observation():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        genotype = db.session.query(Genotype).filter(Genotype.id==request.form['gid']).one_or_none()
        if genotype is not None and genotype in seq.supporting_observations:
            seq.supporting_observations.remove(genotype)
            db.session.commit()

    return ''

@app.route('/delete_genomic_support', methods=['POST'])
@login_required
def delete_genomic_support():
    seq = check_seq_edit(request.form['id'])
    if seq is not None:
        for ga in seq.genomic_accessions:
            if ga.id == int(request.form['gen']):
                seq.genomic_accessions.remove(ga)
                db.session.commit()

    return ''


@app.route('/draft_sequence/<id>', methods=['POST'])
@login_required
def draft_sequence(id):
    seq = check_seq_draft(id)
    if seq is not None:
        new_seq = GeneDescription()
        db.session.add(new_seq)
        db.session.commit()

        copy_GeneDescription(seq, new_seq)
        new_seq.description_id = seq.description_id
        new_seq.status = 'draft'

        for inferred_sequence in seq.inferred_sequences:
            new_seq.inferred_sequences.append(inferred_sequence)

        for gen in seq.supporting_observations:
            new_seq.supporting_observations.append(gen)

        for acc in seq.genomic_accessions:
            new_seq.genomic_accessions.append(acc)

        for journal_entry in seq.journal_entries:
            new_entry = JournalEntry()
            copy_JournalEntry(journal_entry, new_entry)
            new_seq.journal_entries.append(new_entry)

        db.session.commit()
    return ''

@app.route('/sequence_imgt_name', methods=['POST'])
@login_required
def sequence_imgt_name():
    if request.is_json:
        content = request.get_json()
        seq = check_seq_draft(content['id'])
        if seq is not None:
            seq.imgt_name = content['imgt_name']
            add_history(current_user, 'IMGT Name updated to %s' % seq.imgt_name, seq, db, body='IMGT Name updated.')
            send_mail('Sequence %s version %d: IMGT name updated to %s by the IARC %s Committee' % (seq.description_id, seq.release_version, seq.imgt_name, seq.species), [seq.species], 'iarc_sequence_released', reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment='IMGT Name updated to %s' % seq.imgt_name)
            db.session.commit()
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
    return ''


@app.route('/withdraw_sequence/<id>', methods=['POST'])
@login_required
def withdraw_sequence(id):
    seq = check_seq_withdraw(id)
    if seq is not None:
        add_history(current_user, 'Published version %s withdrawn' % seq.release_version, seq, db, body = '')
        send_mail('Sequence %s version %d withdrawn by the IARC %s Committee' % (seq.description_id, seq.release_version, seq.species), [seq.species], 'iarc_sequence_withdrawn', reviewer=current_user, user_name=seq.maintainer, sequence=seq, comment='')
        seq.status = 'withdrawn'
        db.session.commit()
        seq.duplicate_sequences = list()
        flash('Sequence %s withdrawn' % seq.sequence_name)

        related_subs = []
        for inf in seq.inferred_sequences:
            related_subs.append(inf.submission)

        # un-publish any related submissions that now don't have published sequences

        published_seqs = db.session.query(GeneDescription).filter_by(species=seq.species, status='published').all()

        for related_sub in related_subs:
            other_published = False
            for ps in published_seqs:
                for inf in ps.inferred_sequences:
                    if inf.submission == related_sub:
                        other_published = True
                        break

            if not other_published:
                related_sub.submission_status = 'reviewing'
                related_sub.public = False
                add_history(current_user, 'Status changed from published to reviewing as submission %s was withdrawn.' % seq.description_id, related_sub, db, body = '')

        db.session.commit()

    return ''


@app.route('/add_sequence_dup_note/<seq_id>/<gen_id>/<text>', methods=['POST'])
@login_required
def add_sequence_dup_note(seq_id, gen_id, text):
    seq = check_seq_see_notes(seq_id)

    try:
        gen_id = int(gen_id)
    except:
        return('error')

    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    db.session.delete(note)

        if len(text) > 0:
            note = DupeGeneNote(gene_description = seq, genotype = gen)
            note.author = current_user.name
            note.body = text
            note.date = datetime.datetime.now()
            db.session.add(note)

        db.session.commit()
    return ''

@app.route('/delete_sequence_dup_note/<seq_id>/<gen_id>', methods=['POST'])
@login_required
def delete_sequence_dup_note(seq_id, gen_id):
    try:
        gen_id = int(gen_id)
    except:
        return('error')

    seq = check_seq_see_notes(seq_id)
    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    db.session.delete(note)
            db.session.commit()
    return ''


@app.route('/get_sequence_dup_note/<seq_id>/<gen_id>', methods=['POST'])
@login_required
def get_sequence_dup_note(seq_id, gen_id):
    try:
        gen_id = int(gen_id)
    except:
        return('error')

    seq = check_seq_see_notes(seq_id)
    if seq is not None:
        gen = db.session.query(Genotype).filter_by(id = gen_id).one_or_none()
        if gen is not None and gen in seq.duplicate_sequences:
            for note in seq.dupe_notes:
                if note.genotype_id == gen_id:
                    return json.dumps({'author': note.author, 'timestamp': note.date.strftime("%d/%m/%y %H:%M"), 'body': note.body})
        return ''
    else:
        return 'error'

def check_primer_set_edit(id):
    try:
        set = db.session.query(PrimerSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return (None, None)

        sub = set.repertoire.submission
        if not sub.can_edit(current_user):
            flash('You do not have rights to edit that primer set.')

        return (sub, set)

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return (None, None)


@app.route('/primer_sets/<id>', methods=['GET', 'POST'])
@login_required
def primer_sets(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    form = PrimerSetForm()

    if request.method == 'GET':
        populate_PrimerSet(db, set, form)
        return render_template('primer_set_edit.html', form=form, name=set.primer_set_name, id=id)
    else:
        if 'cancel_btn' in request.form:
            if len(set.primer_set_name) == 0:         # this is a new primer set, since you can't save a blank name
                db.session.delete(set)
                db.session.commit()
            return redirect(url_for('edit_submission', id=sub.submission_id, _anchor='primer_sets'))

        valid = form.validate()

        if valid:
            set.primer_set_name = form.primer_set_name.data
            set.primer_set_notes = form.primer_set_notes.data
            db.session.commit()

            if 'edit_btn' in request.form:
                return redirect(url_for('edit_primers', id=id, _anchor='primer_sets'))
            elif 'submit_btn' in request.form:
                return redirect(url_for('edit_submission', id=sub.submission_id, _anchor='primer_sets'))

        return render_template('primer_set_edit.html', form=form, name=set.primer_set_name, id=id)


@app.route('/edit_primers/<id>', methods=['GET', 'POST'])
@login_required
def edit_primers(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    (form, tables) = setup_primer_set_forms_and_tables(db, set)

    if request.method == 'GET':
        return render_template('primers_edit.html', tables=tables, form=form, name=set.primer_set_name, id=id)
    else:
        if 'close_btn' in request.form:
            return redirect(url_for('primer_sets', id=id))

        valid = form.validate()

        if valid:
            validation_result = process_table_updates({'primers': tables['primers']}, request, db)
            if validation_result.tag:
                if validation_result.valid:     # rebuild tables if something has changed
                    (form, tables) = setup_primer_set_forms_and_tables(db, set)

        return render_template('primers_edit.html', tables=tables, form=form, name=set.primer_set_name, id=id)


@app.route('/upload_primers/<id>', methods=['POST'])
@login_required
def upload_primer(id):
    (sub, set) = check_primer_set_edit(id)
    if set is None:
        return redirect('/submissions')

    if 'file' not in request.files:
        flash('Nothing uploaded.')
    else:
        content = io.StringIO(request.files['file'].read().decode("utf-8"))
        seq_count = 0

        for seq_record in SeqIO.parse(content, 'fasta'):
            seq_count += 1

            p = Primer()
            p.primer_name = seq_record.id
            p.primer_seq = str(seq_record.seq)
            db.session.add(p)
            set.primers.append(p)

        if seq_count > 0:
            flash('Added %d primer records' % seq_count)
            db.session.commit()
        else:
            flash('No valid FASTA records found in file.')

    return ''

# Unpublished route that will remove all sequences and submissions published by the selenium test account
@app.route('/remove_test', methods=['GET'])
@login_required
def remove_test():
    if not current_user.has_role('Admin'):
        return redirect('/')

    test_user = 'fred tester'

    seqs = db.session.query(GeneDescription).filter(GeneDescription.maintainer == test_user).all()
    for seq in seqs:
        seq.delete_dependencies(db)
        db.session.delete(seq)
    db.session.commit()

    subs = db.session.query(Submission).filter(Submission.submitter_name == test_user).all()
    for sub in subs:
        sub.delete_dependencies(db)
        db.session.delete(sub)
    db.session.commit()

    flash("Test records removed.")
    return redirect('/')


# Permanent maintenance route to rebuild duplicate links
@app.route('/rebuild_duplicates', methods=['GET'])
@login_required
def rebuild_duplicates():
    if not current_user.has_role('Admin'):
        return redirect('/')

    # gene description

    descs = db.session.query(GeneDescription).all()

    for desc in descs:
        desc.duplicate_sequences = list()
        if desc.status in ['published', 'draft']:
            desc.build_duplicate_list(db, desc.sequence)

    db.session.commit()

    return('Gene description links rebuilt')


@app.route('/germline_sets', methods=['GET', 'POST'])
def germline_sets():
    tables = {}
    show_withdrawn = False

    if current_user.is_authenticated:
        species = [s[0] for s in db.session.query(Committee.species).all()]
        for sp in species:
            if current_user.has_role(sp):
                if 'species' not in tables:
                    tables['species'] = {}
                tables['species'][sp] = {}

                if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
                    q = db.session.query(GermlineSet).filter(GermlineSet.species == sp).filter(GermlineSet.status.in_(['draft', 'withdrawn']))
                    show_withdrawn = True
                else:
                    q = db.session.query(GermlineSet).filter(GermlineSet.species == sp).filter(GermlineSet.status.in_(['draft']))
                    show_withdrawn = False
                results = q.all()

                tables['species'][sp]['draft'] = setup_germline_set_list_table(results, current_user)
                tables['species'][sp]['draft'].table_id = sp + '_draft'

    q = db.session.query(GermlineSet).filter(GermlineSet.status == 'published')
    results = q.all()
    affirmed = setup_published_germline_set_list_info(results, current_user)

    return render_template('germline_set_list.html', tables=tables, affirmed=affirmed, show_withdrawn=show_withdrawn, any_published=(len(affirmed) > 0))


@app.route('/new_germline_set/<species>', methods=['GET', 'POST'])
@login_required
def new_germline_set(species):
    if not current_user.has_role(species):
        return redirect('/')

    form = NewGermlineSetForm()
    form.locus.choices = ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRG', 'TRD']

    if request.method == 'POST':
        if form.cancel.data:
            return redirect('/germline_sets')

        if form.validate():
            try:
                if db.session.query(GermlineSet).filter(and_(GermlineSet.species == species, GermlineSet.germline_set_name == form.name.data, ~GermlineSet.status.in_(['withdrawn', 'superceded']))).count() > 0:
                    form.new_name.errors = ['A germline set already exists with that name.']
                    raise ValidationError()

                germline_set = GermlineSet()
                germline_set.species = species
                germline_set.status = 'draft'
                germline_set.author = current_user.name
                germline_set.lab_address = current_user.address
                germline_set.release_version = 0
                germline_set.locus = form.locus.data
                germline_set.germline_set_name = form.name.data

                db.session.add(germline_set)
                db.session.commit()
                germline_set.germline_set_id = "G%05d" % germline_set.id
                add_history(current_user, '%s germline set %s (%s) created' % (germline_set.species, germline_set.germline_set_id, germline_set.germline_set_name), germline_set, db)
                db.session.commit()

                return redirect('/germline_sets')

            except ValidationError as e:
                return render_template('germline_set_new.html', form=form, species=species)

    return render_template('germline_set_new.html', form=form, species=species)


@app.route('/edit_germline_set/<id>', methods=['GET', 'POST'])
@login_required
def edit_germline_set(id):
    germline_set = check_set_edit(id)
    if germline_set is None:
        return redirect('/germline_sets')

    if len(germline_set.notes_entries) == 0:
        germline_set.notes_entries.append(NotesEntry())
        db.session.commit()

    update_germline_set_seqs(germline_set)
    db.session.commit()

    tables = setup_germline_set_edit_tables(db, germline_set)
    tables['genes'].table_id = "genetable"
    tables['genes'].html_attrs = {'style': 'width: 100%'}
    germline_set_form = GermlineSetForm(obj=germline_set)
    notes_entry_form = NotesEntryForm(obj=germline_set.notes_entries[0])
    history_form = JournalEntryForm()
    hidden_return_form = HiddenReturnForm()
    changes = list_germline_set_changes(germline_set)
    form = AggregateForm(germline_set_form, notes_entry_form, history_form, hidden_return_form, tables['ack'].form, tables['pubmed_table'].form)

    if request.method == 'POST':
        form.validate()
        valid = True

        for field in form._fields:
            if len(form[field].errors) > 0:
                if field in history_form._fields and 'history_btn' not in request.form:
                    form[field].errors = []
                else:
                    valid = False

        if form.action.data == 'published':
            if len(germline_set.gene_descriptions) < 1:
                flash("Please add at least one gene to the set!")
                form.action.data = ''
                valid = False

            for gene_description in germline_set.gene_descriptions:
                if gene_description.status == 'draft':
                    publish_sequence(gene_description, form.body.data, False)
                if gene_description.status == 'published' and gene_description.affirmation_level == 0:
                    flash("Can't publish this set while gene %s is at affirmation level 0." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False
                if gene_description.status == 'withdrawn':
                    flash("Can't publish this set while gene %s is withdrawn." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False
                if gene_description.species_subgroup != germline_set.species_subgroup or gene_description.species_subgroup_type != germline_set.species_subgroup_type:
                    flash("Can't publish this set while gene %s species subgroup/subgroup type disagreees with the germline set values." % gene_description.sequence_name)
                    form.action.data = ''
                    valid = False

        if valid:
            try:
                validation_result = process_table_updates({'ack': tables['ack'], 'pubmed_table': tables['pubmed_table']}, request, db)
                if not validation_result.valid:
                    raise ValidationError()

                save_GermlineSet(db, germline_set, form)

                if 'add_gene_btn' in request.form:
                    return redirect(url_for('add_gene_to_set', id=id))

                if form.action.data == 'published':
                    old_set = db.session.query(GermlineSet).filter_by(germline_set_id=germline_set.germline_set_id, status='published').one_or_none()
                    if old_set:
                        old_set.status = 'superceded'

                    max_version = db.session.query(func.max(GermlineSet.release_version))\
                        .filter(GermlineSet.germline_set_id == germline_set.germline_set_id)\
                        .filter(or_(GermlineSet.status == 'withdrawn', GermlineSet.status == 'superceded'))\
                        .one_or_none()

                    germline_set.release_version = max_version[0] + 1 if max_version[0] else 1
                    germline_set.release_date = datetime.date.today()

                    hist_notes = form.body.data
                    changes = list_germline_set_changes(germline_set)   # to get updated versions
                    if changes != '':
                        hist_notes += Markup('<br>') + changes

                    add_history(current_user, 'Version %s published' % (germline_set.release_version), germline_set, db, body=hist_notes)
                    send_mail('Sequence %s version %d published by the IARC %s Committee' % (germline_set.germline_set_id, germline_set.release_version, germline_set.species), [germline_set.species], 'iarc_germline_set_released', reviewer=current_user, user_name=germline_set.author, germline_set=germline_set, comment=form.body.data)

                    germline_set.status = 'published'
                    db.session.commit()
                    flash('Germline set published')
                    return redirect('/germline_sets')

                if 'notes_attachment' in request.files:
                    for file in form.notes_attachment.data:
                        if file.filename != '':
                            af = None
                            for at in germline_set.notes_entries[0].attached_files:
                                if at.filename == file.filename:
                                    af = at
                                    break
                            if af is None:
                                af = AttachedFile()
                            af.notes_entry = germline_set.notes_entries[0]
                            af.filename = file.filename
                            db.session.add(af)
                            db.session.commit()
                            dirname = attach_path + germline_set.germline_set_id

                            try:
                                if not isdir(dirname):
                                    mkdir(dirname)
                                with open(dirname + '/multi_attachment_%s' % af.id, 'wb') as fo:
                                    fo.write(file.stream.read())
                            except:
                                info = sys.exc_info()
                                flash('Error saving attachment: %s' % (info[1]))
                                app.logger.error(format_exc())
                                return redirect(url_for('edit_submission', id=germline_set.germline_set_id))
                            db.session.commit()
                            validation_result.tag = 'notes'

                if 'notes_text' in request.form and germline_set.notes_entries[0].notes_text is None or germline_set.notes_entries[0].notes_text != request.form['notes_text'].encode('utf-8'):
                    germline_set.notes_entries[0].notes_text = request.form['notes_text'].encode('utf-8')
                    db.session.commit()

            except ValidationError:
                return render_template('germline_set_edit.html',
                                       form=form,
                                       germline_set_name=germline_set.germline_set_name,
                                       id=id,
                                       set_id=germline_set.germline_set_id,
                                       tables=tables,
                                       changes=changes,
                                       jump=validation_result.tag,
                                       version=germline_set.release_version)

            if validation_result.tag:
                return redirect(url_for('edit_germline_set', id=id, _anchor=validation_result.tag))
            else:
                return redirect(url_for('germline_sets'))

        else:
            for field in tables['ack'].form:
                if len(field.errors) > 0:
                    return render_template('germline_set_edit.html',
                                           form=form,
                                           germline_set_name=germline_set.germline_set_name,
                                           id=id,
                                           set_id=germline_set.germline_set_id,
                                           tables=tables,
                                           changes=changes,
                                           jump='ack',
                                           version=germline_set.release_version)

    return render_template('germline_set_edit.html',
                           form=form,
                           germline_set_name=germline_set.germline_set_name,
                           id=id,
                           set_id=germline_set.germline_set_id,
                           tables=tables,
                           version=germline_set.release_version,
                           changes=changes,
                           )


def check_set_view(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id=id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if not set.can_see(current_user):
            flash('You do not have rights to view that sequence.')

        return set

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


def check_set_edit(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if not set.can_edit(current_user):
            flash('You do not have rights to edit that sequence.')
            return None

        return set

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None


@app.route('/delete_germline_set/<id>', methods=['POST'])
@login_required
def delete_germline_set(id):
    set = check_set_edit(id)
    if set is not None:
        set.delete_dependencies(db)
        db.session.delete(set)
        db.session.commit()
    return ''


@app.route('/download_germline_set_attachment/<id>')
def download_germline_set_attachment(id):
    att = check_germline_set_attachment_view(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.germline_set

    try:
        dirname = attach_path + germline_set.germline_set_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_germline_set_attachment/<id>', methods=['POST'])
def delete_germline_set_attachment(id):
    att = check_germline_set_attachment_edit(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.submission

    try:
        dirname = attach_path + germline_set.germline_set_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


def check_set_draft(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id = id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if set.status != 'published':
            flash('Only published sequences can be cloned.')
            return None

        clones = db.session.query(GermlineSet).filter_by(germline_set_name=set.germline_set_name).all()
        for clone in clones:
            if clone.status == 'draft':
                flash('There is already a draft of that germline set')
                return None

        if not set.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return set


@app.route('/draft_germline_set/<id>', methods=['POST'])
@login_required
def draft_germline_set(id):
    set = check_set_draft(id)
    if set is not None:
        new_set = GermlineSet()
        db.session.add(new_set)
        db.session.commit()

        copy_GermlineSet(set, new_set)
        new_set.status = 'draft'
        new_set.release_version = 0

        for gene_description in set.gene_descriptions:
            new_set.gene_descriptions.append(gene_description)

        new_set.notes_entries.append(NotesEntry())
        new_set.notes_entries[0].notes_text = set.notes_entries[0].notes_text

        for af in set.notes_entries[0].attached_files:
            new_af = AttachedFile()
            new_af.notes_entry = new_set.notes_entries[0]
            new_af.filename = af.filename
            db.session.add(af)

        for journal_entry in set.journal_entries:
            new_entry = JournalEntry()
            copy_JournalEntry(journal_entry, new_entry)
            new_set.journal_entries.append(new_entry)

        update_germline_set_seqs(new_set)

        db.session.commit()
    return ''


def check_set_withdraw(id):
    try:
        set = db.session.query(GermlineSet).filter_by(id=id).one_or_none()
        if set is None:
            flash('Record not found')
            return None

        if set.status != 'published':
            flash('Only published sequences can be withdrawn.')
            return None

        if not set.can_draft(current_user):
            flash('You do not have rights to edit that entry')
            return None

    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return set


def update_germline_set_seqs(germline_set):
    for desc in list(germline_set.gene_descriptions):
        gd = db.session.query(GeneDescription).filter(GeneDescription.description_id == desc.description_id, GeneDescription.status == 'draft').one_or_none()
        if gd is None:
            gd = db.session.query(GeneDescription).filter(GeneDescription.description_id == desc.description_id, GeneDescription.status == 'published').one_or_none()
        if gd and gd != desc:
            germline_set.gene_descriptions.remove(desc)
            germline_set.gene_descriptions.append(gd)


@app.route('/withdraw_germline_set/<id>', methods=['POST'])
@login_required
def withdraw_germline_set(id):
    set = check_set_withdraw(id)
    if set is not None:
        add_history(current_user, 'Published version %s withdrawn' % set.release_version, set, db, body='')
        send_mail('Germline set %s version %d withdrawn by the IARC %s Committee' % (set.germline_set_id, set.release_version, set.species), [set.species], 'iarc_germline_set_withdrawn', reviewer=current_user, user_name=set.author, germline_set=set, comment='')
        set.status = 'withdrawn'
        db.session.commit()
        flash('Germline set %s withdrawn' % set.germline_set_name)

        db.session.commit()

    return ''


@app.route('/delete_gene_from_set', methods=['POST'])
@login_required
def delete_gene_from_set():
    germline_set = check_set_edit(request.form['set_id'])
    if germline_set is not None:
        gene_description = db.session.query(GeneDescription).filter(GeneDescription.id == request.form['gene_id']).one_or_none()
        if gene_description is not None and gene_description in germline_set.gene_descriptions:
            germline_set.gene_descriptions.remove(gene_description)
            db.session.commit()

    return ''


@app.route('/add_gene_to_set/<id>', methods=['GET', 'POST'])
@login_required
def add_gene_to_set(id):
    germline_set = check_set_edit(id)
    if germline_set is None:
        return redirect('/germline_sets')

    form = NewGermlineSetGeneForm()
    gene_descriptions = db.session.query(GeneDescription).filter(GeneDescription.species == germline_set.species)\
        .filter(GeneDescription.status.in_(['published', 'draft'])).all()
    gene_descriptions = [g for g in gene_descriptions if g not in germline_set.gene_descriptions]
    gene_descriptions = [g for g in gene_descriptions if germline_set.locus == g.locus]
    gene_descriptions.sort(key=attrgetter('sequence_name'))
    form.create.label.text = "Add"

    gene_table = setup_sequence_list_table(gene_descriptions, current_user, edit=False)
    gene_table.table_id = "genetable"
    gene_table.html_attrs = {'style': 'width: 100%'}

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_sequence', id=id, _anchor='inf'))

        if form.validate():
            selected = form.results.data.split(',')
            selected_ids = []

            for sel in selected:
                if "/sequence/" in sel:
                    try:
                        selected_ids.append(int(sel.split("/sequence/")[1].split('">')[0]))
                    except:
                        pass

            for gid in selected_ids:
                gene_description = db.session.query(GeneDescription).filter(GeneDescription.id == gid).one_or_none()

                if gene_description and gene_description not in germline_set.gene_descriptions:
                    germline_set.gene_descriptions.append(gene_description)

            db.session.commit()
        return redirect(url_for('edit_germline_set', id=id, _anchor='genes'))

    return render_template('germline_set_add_gene.html', form=form, name=germline_set.germline_set_name, gene_table=gene_table, id=id)


def check_germline_set_attachment_edit(af_id):
    af = db.session.query(AttachedFile).filter_by(id=af_id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    germline_set = af.notes_entry.germline_set
    if not germline_set.can_edit(current_user):
        flash('You do not have rights to delete that attachment')
        return None
    return af


def check_germline_set_attachment_view(af_id):
    af = db.session.query(AttachedFile).filter_by(id=af_id).one_or_none()
    if af is None:
        flash('Attachment not found')
        return None
    germline_set = af.notes_entry.germline_set
    if not germline_set.can_see(current_user):
        flash('You do not have rights to download that attachment')
        return None
    return af


@app.route('/download_germline_set_attachment/<id>')
def download_germline_set_attachment_view(id):
    att = check_germline_set_attachment_view(id)
    if att is None:
        return redirect('/')

    germline_set = att.notes_entry.germline_set

    try:
        dirname = attach_path + germline_set.germline_set_id
        with open(dirname + '/multi_attachment_%s' % att.id, 'rb') as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % att.filename})
    except:
        info = sys.exc_info()
        flash('Error retrieving attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    return redirect('/')


@app.route('/delete_submission_attachment/<id>', methods=['POST'])
def delete_set_attachment(id):
    att = check_germline_set_attachment_edit(id)
    if att is None:
        return redirect('/')

    sub = att.notes_entry.submission

    try:
        dirname = attach_path + germline_set.germline_set_id
        remove(dirname + '/multi_attachment_%s' % att.id)
    except:
        info = sys.exc_info()
        flash('Error deleting attachment: %s' % (info[1]))
        app.logger.error(format_exc())

    db.session.delete(att)
    db.session.commit()
    return ''


@app.route('/germline_set/<id>', methods=['GET'])
def germline_set(id):
    germline_set = check_set_view(id)
    if germline_set is None:
        return redirect('/germline_sets')

    if len(germline_set.notes_entries) == 0:
        germline_set.notes_entries.append(NotesEntry())
        db.session.commit()

    form = FlaskForm()
    tables = setup_germline_set_view_tables(db, germline_set, current_user.has_role(germline_set.species))
    tables['genes'].table_id = "genetable"
    tables['genes'].html_attrs = {'style': 'width: 100%'}
    versions = db.session.query(GermlineSet).filter(GermlineSet.species == germline_set.species)\
        .filter(GermlineSet.germline_set_name == germline_set.germline_set_name)\
        .filter(GermlineSet.status.in_(['published', 'superceded']))\
        .all()
    tables['versions'] = setup_germline_set_list_table(versions, None)
    supplementary_files = len(tables['attachments'].table.items) > 0

    notes = safe_textile(germline_set.notes_entries[0].notes_text)
    return render_template('germline_set_view.html', form=form, tables=tables, name=germline_set.germline_set_name, supplementary_files=supplementary_files, notes=notes, id=id)


@app.route('/genotype_statistics', methods=['GET', 'POST'])
def genotype_statistics():
    form = GeneStatsForm()
    species = db.session.query(Committee.species).all()
    form.species.choices = [(s[0],s[0]) for s in species]

    if request.method == 'POST':
        if form.validate():
            tables = setup_gene_stats_tables(form)
            if current_user.is_authenticated and tables['count'] > 0:
                with open(user_attach_path + '%05d' % current_user.id, 'w', newline='') as fo:
                    fo.write(tables['raw'])
                tables['raw'] = ''
            return render_template('genotype_statistics.html', form=form, tables=tables, logged_in=current_user.is_authenticated)

    return render_template('genotype_statistics.html', form=form, tables=None)


@app.route('/download_userfile/<filename>')
@login_required
def download_userfile(filename):
    try:
        with open(user_attach_path + '%05d' % current_user.id) as fi:
            return Response(fi.read(), mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})
    except:
        flash('File not found')

    return redirect('/')


@app.route('/download_germline_set/<set_id>/<format>')
def download_germline_set(set_id, format):
    if format not in ['gapped', 'ungapped', 'airr']:
        flash('Invalid format')
        return redirect('/')

    germline_set = check_set_view(set_id)
    if not germline_set:
        flash('Germline set not found')
        return redirect('/')

    if len(germline_set.gene_descriptions) < 1:
        flash('No sequences to download')
        return redirect('/')

    if format == 'airr':
        dl = json.dumps(germline_set, default=str, indent=4)
        filename = '%s_%s_rev_%d.json' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version)
    else:
        dl = descs_to_fasta(germline_set.gene_descriptions, format)
        filename = '%s_%s_rev_%d_%s.fasta' % (germline_set.species, germline_set.germline_set_name, germline_set.release_version, format)

    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


def descs_to_fasta(descs, format):
    ret = ''
    for desc in descs:
        name = desc.sequence_name
        if desc.imgt_name != '':
            name += '|IMGT=' + desc.imgt_name
        if format == 'gapped':
            ret += format_fasta_sequence(name, desc.coding_seq_imgt, 60)
        else:
            seq = desc.coding_seq_imgt.replace('.','')
            seq = seq.replace('-','')
            ret += format_fasta_sequence(name, seq, 60)
    return ret


@app.route('/download_sequences/<species>/<format>/<exc>')
def download_sequences(species, format, exc):
    if format not in ['gapped','ungapped','airr']:
        flash('Invalid format')
        return redirect('/')

    all_species = db.session.query(Committee.species).all()
    all_species = [s[0] for s in all_species]
    if species not in all_species:
        flash('Invalid species')
        return redirect('/')

    q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.affirmation_level != '0', GeneDescription.species == species)
    results = q.all()

    imgt_ref = get_imgt_reference_genes()
    if species in imgt_ref and exc == 'non':
        descs = []
        for result in results:
            if result.imgt_name == '':
                descs.append(result)
        results = descs

    if len(results) < 1:
        flash('No sequences to download')
        return redirect('/')

    if format == 'airr':
        ad = []
        for desc in results:
            ad.append(vars(AIRRAlleleDescription(desc)))

        dl = json.dumps(ad, default=str, indent=4)
        ext = 'json'
    else:
        dl = descs_to_fasta(results, format)
        ext = 'fa'

    filename = 'affirmed_germlines_%s_%s.%s' % (species, format, ext)
    return Response(dl, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


@app.route('/genomic_support/<id>', methods=['GET'])
def genomic_support(id):
    genomic_support = db.session.query(GenomicSupport).filter(GenomicSupport.id == id).one_or_none()

    if genomic_support is None or not genomic_support.gene_description.can_see(current_user):
        return redirect('/')

    table = make_GenomicSupport_view(genomic_support, genomic_support.gene_description.can_edit(current_user))

    for item in table.items:
        if item['item'] == 'URL':
            item['value'] = Markup('<a href="%s">%s</a>' % (item['value'], item['value']))

    return render_template('genomic_support_view.html', table=table, name=genomic_support.gene_description.sequence_name)



from imgt.imgt_ref import gap_sequence

# Temp route to change Genomic to Unrearranged in GeneDescription
@app.route('/upgrade_db', methods=['GET'])
@login_required
def add_gapped():
    if not current_user.has_role('Admin'):
        return redirect('/')

    descs = db.session.query(GeneDescription).all()
    if descs is None:
        flash('Gene descriptions not found')
        return None

    report = ''

    for desc in descs:
        if desc.sequence_name:
            report += 'Processing sequence ' + desc.sequence_name + '<br>'

        if 'Genomic' in desc.inference_type:
            desc.inference_type = desc.inference_type.replace('Genomic', 'Unrearranged')

        db.session.commit()

    return report


