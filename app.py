# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import io
from os.path import isdir
from os import mkdir

from flask import Blueprint
from flask_security.utils import hash_password
from flask_security import SQLAlchemyUserDatastore, login_required, logout_user
from sqlalchemy import or_

import head

head.create_app()
from head import app, mail, security


# Check log file can be opened for writing, default otherwise

try:
    with(open(app.config["LOGPATH"], 'w')) as fp:
        pass
except:
    app.config["LOGPATH"] = 'app.log'

ncbi_api_key = app.config['NCBI_API_KEY']
head.ncbi_api_key = app.config['NCBI_API_KEY']


# Make the attachment directory, if it doesn't exist

attach_path = app.config['ATTACHPATH'] + '/'
head.attach_path = attach_path
if not isdir(attach_path):
    mkdir(attach_path)

user_attach_path = attach_path + 'user/'
if not isdir(user_attach_path):
    mkdir(user_attach_path)

from db.sequence_list_table import *
from ogrdb.submission.genotype_view_table import *
from db.germline_set_list_table import *
from db.inferred_sequence_table import *
from db.germline_set_table import *
from db.dupe_gene_note_db import *
from db.vdjbase import *

from forms.useradmin import *
from forms.security import *
from forms.journal_entry_form import *
from forms.sequence_new_form import *
from forms.germline_set_new_form import *
from forms.germline_set_gene_form import *
from forms.gene_description_form import *
from forms.gene_description_notes_form import *
from forms.germline_set_form import *
from forms.sequence_view_form import *
from forms.germline_set_view_form import *
from forms.genotype_stats_form import *
from forms.sequences_species_form import *

from genotype_stats import *
from to_airr import *


from custom_logging import init_logging
init_logging(app, mail)

# Read IMGT germline reference sets

from imgt.imgt_ref import init_imgt_ref, init_igpdb_ref, get_imgt_reference_genes
from db.vdjbase import init_vdjbase_ref

init_imgt_ref()
init_igpdb_ref()
init_vdjbase_ref()

# Initialise REST API

from api.restplus import api
from api.sequence.sequence import ns as sequence
from api.sequence.germline import ns as germline

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = security.init_app(app, user_datastore, confirm_register_form=ExtendedRegisterForm)

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

from ogrdb.submission.submission_routes import *
from ogrdb.submission.submission_view_form import HiddenReturnForm
from ogrdb.submission.inference_tool_routes import *
from ogrdb.submission.genotype_description_routes import *
from ogrdb.submission.inferred_sequence_routes import *


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

from ogrdb.submission.primer_set_routes import *


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
        dl = json.dumps(germline_set_to_airr(germline_set), default=str, indent=4)
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

from ogrdb.vdjbase.vdjbase_routes import *

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


