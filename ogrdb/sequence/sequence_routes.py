# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE

import csv
import datetime
import io
import json
import os
import sys
from os import mkdir, remove
from os.path import isdir
from traceback import format_exc
import shutil

from flask import current_app, flash, redirect, request, render_template, url_for, Response, jsonify
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from markupsafe import Markup
from sqlalchemy import and_, or_
from wtforms import ValidationError
from receptor_utils import simple_bio_seq as simple
from receptor_utils.sequence_alignment import create_alignment
from receptor_utils.number_v import gap_align

from head import db, app, attach_path


from db.attached_file_db import AttachedFile
from db.dupe_gene_note_db import DupeGeneNote
from db.gene_description_db import GeneDescription, GenomicSupport, save_GenomicSupport, populate_GenomicSupport, save_GeneDescription, copy_GeneDescription, \
    make_GenomicSupport_view, copy_GenomicSupport
from db.genotype_db import Genotype
from db.inferred_sequence_db import InferredSequence
from db.journal_entry_db import JournalEntry, copy_JournalEntry
from db.misc_db import Committee
from db.repertoire_db import Acknowledgements
from db.submission_db import Submission
from db.novel_vdjbase_db import NovelVdjbase
from db.species_lookup_db import SpeciesLookup
from db.germline_set_db import GermlineSet

from forms.aggregate_form import AggregateForm
from forms.gene_description_form import GeneDescriptionForm
from forms.gene_description_notes_form import GeneDescriptionNotesForm
from forms.genomic_support_form import GenomicSupportForm
from forms.journal_entry_form import JournalEntryForm
from forms.sequence_new_form import NewSequenceForm
from forms.sequence_table_form import SequenceTableForm
from forms.alignment_form import AlignmentForm
from ogrdb.sequence.gene_table import get_available_species, get_available_subgroups, get_available_loci
from imgt.imgt_ref import get_imgt_reference_genes
from ogrdb.germline_set.descs_to_fasta import descs_to_fasta

from ogrdb.submission.inferred_sequence_routes import validate_ext
from ogrdb.submission.submission_edit_form import process_table_updates
from ogrdb.submission.submission_routes import check_sub_view
from ogrdb.submission.submission_view_form import HiddenReturnForm

from forms.sequence_view_form import setup_sequence_view_tables
from ogrdb.sequence.inferred_sequence_table import setup_sequence_edit_tables
from ogrdb.sequence.sequence_list_table import setup_sequence_list_table, setup_sequence_version_table


from textile_filter import safe_textile
from journal import add_history, add_note
from mail import send_mail
from ogrdb.germline_set.to_airr import AIRRAlleleDescription


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
    af = db.session.query(AttachedFile).filter_by(id=id).one_or_none()
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


@app.route('/sequences', methods=['GET', 'POST'])
def sequences():
    form = SequenceTableForm()
    
    # Get available species based on published sequences and user committee membership
    available_species = get_available_species()
    form.species.choices = [(sp, sp) for sp in available_species]
    
    # Set up form choices before validation
    if form.species.choices:
        # Determine which species to use for setting up choices
        if request.method == 'POST' and form.species.data:
            current_species = form.species.data
        elif form.species.choices:
            current_species = form.species.choices[0][0]
        else:
            current_species = None
            
        if current_species:
            # Set subgroup choices
            available_subgroups = get_available_subgroups(current_species)
            form.species_subgroup.choices = [('', 'All')] + [(sg, sg) for sg in available_subgroups]
            
            # Determine subgroup for loci choices
            if request.method == 'POST' and form.species_subgroup.data:
                current_subgroup = form.species_subgroup.data if form.species_subgroup.data != '' else None
            else:
                current_subgroup = None
                
            # Set locus choices
            available_loci = get_available_loci(current_species, current_subgroup)
            form.locus.choices = [(locus, locus) for locus in available_loci]
    
    tables = {}
    selected_species = None
    selected_subgroup = None
    selected_locus = None
    show_withdrawn = False
    
    if form.validate_on_submit():
        selected_species = form.species.data
        selected_subgroup = form.species_subgroup.data if form.species_subgroup.data else None
        selected_locus = form.locus.data
        
        # Generate sequence tables based on selected species, subgroup, and locus
        tables = create_sequence_tables(selected_species, selected_subgroup, selected_locus)
        
        # Check for withdrawn parameter
        show_withdrawn = 'withdrawn' in request.args and request.args['withdrawn'] == 'yes'
    elif request.method == 'POST':
        # Debug form validation errors
        print("Form validation failed:")
        for field_name, errors in form.errors.items():
            print(f"  {field_name}: {errors}")

    return render_template('sequence_list.html', form=form, tables=tables,
                           selected_species=selected_species, selected_subgroup=selected_subgroup,
                           selected_locus=selected_locus, show_withdrawn=show_withdrawn)


@app.route('/alignments', methods=['GET', 'POST'])
@app.route('/alignments/<species>/<locus>/<gene_name>', methods=['GET', 'POST'])
def alignments(species=None, locus=None, gene_name=None):
    form = AlignmentForm()
    
    # Get available species based on published sequences and user committee membership
    available_species = get_available_species()
    form.species.choices = [(sp, sp) for sp in available_species]
    
    # If URL parameters are provided, pre-populate form
    if form.species.data is None and species and species in [s[0] for s in form.species.choices]:
        form.species.data = species
    
    # Set up form choices before validation
    if form.species.choices:
        # Determine which species to use for setting up choices
        current_species = form.species.data

        if current_species:
            # Set locus choices
            available_loci = get_available_loci(current_species)
            form.locus.choices = [(locus, locus) for locus in available_loci]
            
            # Pre-populate locus if provided in URL
            if form.locus.data is None and locus and locus in [l[0] for l in form.locus.choices]:
                form.locus.data = locus

            current_locus = form.locus.data
            
            # Set gene name choices
            if current_locus:
                available_gene_names = get_available_gene_names(current_species, current_locus)
                form.gene_name.choices = [(gene, gene) for gene in available_gene_names]
                
                # Pre-populate gene name if provided in URL
                if form.gene_name.data is None and gene_name and gene_name in [g[0] for g in form.gene_name.choices]:
                    form.gene_name.data = gene_name
    
    selected_species = None
    selected_locus = None
    selected_gene_name = None
    alignment_data = None
    codons_per_line = 20  # Default value
    include_evidence = False  # Default value
    is_form_submission = request.method == 'POST'  # Flag to distinguish form submissions from URL access
    
    if form.validate_on_submit():
        selected_species = form.species.data
        selected_locus = form.locus.data
        selected_gene_name = form.gene_name.data
        
        # Capture additional form data
        codons_per_line = int(request.form.get('codons_per_line', 20))
        include_evidence = 'include_evidence' in request.form
        
        # Generate alignment data based on selection
        # TODO - need to work out codon positions of the CDRs in the gapped sequence from the CDR start/end coords in the ungapped sequence
        alignment_data = create_alignment_data(selected_species, selected_locus, selected_gene_name, codons_per_line, include_evidence)
        
    elif request.method == 'POST':
        # Even if form validation fails, preserve the additional form data
        codons_per_line = int(request.form.get('codons_per_line', 20))
        include_evidence = 'include_evidence' in request.form
        
        # Debug form validation errors
        print("Form validation failed:")
        for field_name, errors in form.errors.items():
            print(f"  {field_name}: {errors}")
    
    return render_template('alignments.html', form=form, 
                           selected_species=selected_species, 
                           selected_locus=selected_locus,
                           selected_gene_name=selected_gene_name,
                           alignment_data=alignment_data,
                           codons_per_line=codons_per_line,
                           include_evidence=include_evidence,
                           is_form_submission=is_form_submission)


def get_available_gene_names(species, locus):
    """Get available gene names for a specific species and locus"""
    gene_names_set = set()
    
    # Base query filters
    base_filters = [
        GeneDescription.species == species,
        GeneDescription.locus == locus,
        GeneDescription.sequence_name.isnot(None)
    ]
    
    # Get gene names from published sequences
    published_query = db.session.query(GeneDescription.sequence_name).filter(
        *base_filters,
        GeneDescription.status == 'published'
    ).distinct()
    
    published_genes = published_query.all()
    for gene_tuple in published_genes:
        gene_name = gene_tuple[0]
        if gene_name and '*' in gene_name:
            # Extract gene name without allele designation
            base_gene = gene_name.split('*')[0]
            gene_names_set.add(base_gene)
        elif gene_name:
            gene_names_set.add(gene_name)
    
    # If user has access to this species committee, include unpublished gene names
    if current_user.is_authenticated and current_user.has_role(species):
        unpublished_query = db.session.query(GeneDescription.sequence_name).filter(
            *base_filters,
            GeneDescription.status.in_(['draft'])
        ).distinct()
        
        unpublished_genes = unpublished_query.all()
        for gene_tuple in unpublished_genes:
            gene_name = gene_tuple[0]
            if gene_name and '*' in gene_name:
                # Extract gene name without allele designation
                base_gene = gene_name.split('*')[0]
                gene_names_set.add(base_gene)
            elif gene_name:
                gene_names_set.add(gene_name)
    
    return sorted(list(gene_names_set))


@app.route('/get_gene_names/<species>/<locus>', methods=['GET'])
def get_gene_names_for_species_locus(species, locus):
    """AJAX endpoint to get available gene names for a species and locus"""
    gene_names = get_available_gene_names(species, locus)
    return jsonify(gene_names)


def create_alignment_data(species, locus, gene_name, codons_per_line=20, include_evidence=False):
    """Create alignment data for all alleles of a specific gene"""
    try:
        # Base query filters to find all alleles of the specified gene
        base_filters = [
            GeneDescription.species == species,
            GeneDescription.locus == locus,
            or_(GeneDescription.sequence_name.like(f'{gene_name}*%'), GeneDescription.sequence_name == gene_name),
            GeneDescription.coding_seq_imgt.isnot(None),
            GeneDescription.coding_seq_imgt != ''
        ]
        
        # Get published sequences (always included)
        published_query = db.session.query(GeneDescription).filter(
            *base_filters,
            GeneDescription.status == 'published'
        ).order_by(GeneDescription.sequence_name)
        
        published_alleles = published_query.all()
        
        # If user has access to this species committee, include unpublished alleles
        unpublished_alleles = []
        if current_user.is_authenticated and current_user.has_role(species):
            unpublished_query = db.session.query(GeneDescription).filter(
                *base_filters,
                GeneDescription.status.in_(['draft'])
            ).order_by(GeneDescription.sequence_name)
            
            unpublished_alleles = unpublished_query.all()

        # if include evidence is selected, include genomic_evidence records for all alleles
        published_evidence = {}
        if include_evidence and published_alleles:
            published_evidence_query = db.session.query(GenomicSupport, GeneDescription.sequence_name).join(GeneDescription).filter(
                GeneDescription.species == species,
                GeneDescription.locus == locus,
                or_(GeneDescription.sequence_name.like(f'{gene_name}*%'), GeneDescription.sequence_name == gene_name),
                GeneDescription.status == 'published'
            )

            published_recs = published_evidence_query.all()
            if published_recs:
                for rec, seq_name in published_recs:
                    try:
                        seq = rec.sequence[rec.gene_start - 1 - rec.sequence_start + 1:rec.gene_end - rec.sequence_start + 1]
                        seq = gap_align(seq, published_alleles[0].coding_seq_imgt)  # Align to first published allele
                        label = f'{seq_name} {rec.accession}'
                        published_evidence[label] = seq
                    except:
                        continue

        unpublished_evidence = {}
        if current_user.is_authenticated and current_user.has_role(species):
            if include_evidence and (published_alleles or unpublished_alleles):
                unpublished_evidence_query = db.session.query(GenomicSupport, GeneDescription.sequence_name).join(GeneDescription).filter(
                    GeneDescription.species == species,
                    GeneDescription.locus == locus,
                    or_(GeneDescription.sequence_name.like(f'{gene_name}*%'), GeneDescription.sequence_name == gene_name),
                    GeneDescription.status == 'draft'
                )

                unpublished_recs = unpublished_evidence_query.all()
                if unpublished_recs:
                    for rec, seq_name in unpublished_recs:
                        try:
                            seq = rec.sequence[rec.gene_start - 1 - rec.sequence_start + 1:rec.gene_end - rec.sequence_start + 1]
                            ref = published_alleles[0] if published_alleles else unpublished_alleles[0]
                            seq = gap_align(seq, ref.coding_seq_imgt)  # Align to reference allele
                            label = f'{seq_name} {rec.accession} (U)'
                            unpublished_evidence[label] = seq
                        except:
                            continue

        # Calculate codon positions for CDRs in the gapped sequence
        ref = published_alleles[0] if published_alleles else unpublished_alleles[0]
        sequence_type = ref.sequence_type

        v_coords = None
        if sequence_type == 'V':
            try:
                seq_gapped = ref.coding_seq_imgt
                # build a mapping of ungapped to gapped positions
                ungapped_to_gapped = {}
                ungapped_index = 0                    

                for gapped_index in range(len(seq_gapped)):
                    if seq_gapped[gapped_index] != '.':
                        ungapped_to_gapped[ungapped_index] = gapped_index
                        ungapped_index += 1

                cdr1_codon_start = int(1 + (ungapped_to_gapped[ref.cdr1_start - ref.gene_start])/3)
                cdr1_codon_end = int(1 + (ungapped_to_gapped[ref.cdr1_end - ref.gene_start - 2])/3)
                cdr2_codon_start = int(1 + (ungapped_to_gapped[ref.cdr2_start - ref.gene_start])/3)
                cdr2_codon_end = int(1 + (ungapped_to_gapped[ref.cdr2_end - ref.gene_start - 2])/3)
                cdr3_codon_start = int(1 + (ungapped_to_gapped[ref.cdr3_start - ref.gene_start])/3)
                v_coords = (cdr1_codon_start, cdr1_codon_end, cdr2_codon_start, cdr2_codon_end, cdr3_codon_start)
                print(v_coords)
            except:
                print('error calculating v_coords')
                v_coords = None

        # Combine all alleles
        all_alleles = list(published_alleles) + unpublished_alleles
        
        if not all_alleles:
            return {
                'error': f'No sequences found for {species} {locus} {gene_name}',
                'alignment': None,
                'sequences': []
            }
        
        # Prepare sequences for alignment
        sequences = {}
        suffixes = False
        
        j_codon_frame = None
        for allele in all_alleles:
            coding_seq = allele.coding_seq_imgt
            if coding_seq:  # Only include non-empty sequences
                # Add status indicator for unpublished sequences
                name = allele.sequence_name
                suffix = ''
                if allele.status == 'draft':
                    suffix += 'U'
                # Add status if sequence is not in a published germline set
                sets = db.session.query(GermlineSet).filter(
                    GermlineSet.gene_descriptions.any(id=allele.id),

                ).all()

                published = False
                for s in sets:
                    if s.status == 'published':
                        published = True
                        break

                if not published:
                    suffix += 'N'

                if suffix:
                    name += f' ({suffix})'
                    suffixes = True

                prefix = ''
                if sequence_type == 'J' and allele.j_codon_frame and j_codon_frame is None:
                    try:
                        j_codon_frame = int(allele.j_codon_frame)
                    except:
                        j_codon_frame = None
                sequences.update({name: prefix + allele.coding_seq_imgt})

        sequences.update(published_evidence)
        sequences.update(unpublished_evidence)

        if sequence_type == 'J' and j_codon_frame is not None:
            prefix = '.' * ((4 - int(j_codon_frame)) % 3)
            for name, sequence in sequences.items():
                sequences[name] = prefix + sequence

        if not sequences:
            return {
                'error': f'No valid coding sequences found for {species} {locus} {gene_name}',
                'alignment': None,
                'sequences': [],
                'suffixes': False,
            }
        
        # Create alignment using receptor_utils
        try:
            alignment_result = create_alignment(sequences, sequence_type, codon_wrap=codons_per_line, v_coords=v_coords)
            
            return {
                'error': None,
                'alignment': alignment_result,
                'sequences': list(sequences.keys()),
                'count': len(sequences),
                'suffixes': suffixes
            }
        except Exception as e:
            return {
                'error': f'Error creating alignment: {str(e)}',
                'alignment': None,
                'sequences': list(sequences.keys()),
                'suffixes': False
            }
            
    except Exception as e:
        return {
            'error': f'Error retrieving sequences: {str(e)}',
            'alignment': None,
            'sequences': [],
            'suffixes': False
        }


def create_sequence_tables(species, subgroup, locus):
    """Create sequence tables based on selection criteria"""
    tables = {}
    
    # Base query filters
    base_filters = [
        GeneDescription.species == species,
        GeneDescription.locus == locus
    ]
    
    if subgroup:
        base_filters.append(GeneDescription.species_subgroup == subgroup)
    
    # Check if user has committee access for this species
    has_committee_access = current_user.is_authenticated and current_user.has_role(species)
    
    # Create draft sequences table (only for committee members)
    if has_committee_access:
        if 'species' not in tables:
            tables['species'] = {}
        tables['species'][species] = {}
        
        # Draft sequences
        draft_query = db.session.query(GeneDescription).filter(
            *base_filters,
            GeneDescription.status.in_(['draft'])
        )
        draft_results = draft_query.all()
        tables['species'][species]['draft'] = setup_sequence_list_table(draft_results, current_user)
        tables['species'][species]['draft'].table_id = species.replace(' ', '_') + '_draft'
        
        # Level 0 sequences
        level_0_query = db.session.query(GeneDescription).filter(
            *base_filters,
            GeneDescription.status == 'published',
            GeneDescription.affirmation_level == '0'
        )
        level_0_results = level_0_query.all()
        tables['species'][species]['level_0'] = setup_sequence_list_table(level_0_results, current_user)
        tables['species'][species]['level_0'].table_id = species.replace(' ', '_') + '_level_0'
    
    # Affirmed sequences (available to all users)
    affirmed_query = db.session.query(GeneDescription).filter(
        *base_filters,
        GeneDescription.status == 'published',
        GeneDescription.affirmation_level != '0'
    )
    affirmed_results = affirmed_query.all()
    tables['affirmed'] = setup_sequence_list_table(affirmed_results, current_user)
    tables['affirmed'].table_id = 'affirmed'
    
    return tables


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


@app.route('/sequences_aa_alignment/<sp>/<category>', methods=['GET', 'POST'])
def sequences_aa_alignment(sp, category):
    species = [s[0] for s in db.session.query(Committee.species).all()]
    if sp not in species:
        flash(f'Species {sp} not found')
        return redirect('/')
    
    if category != "affirmed":
        if not current_user.is_authenticated or not current_user.has_role(sp):
            return redirect('/')
        
    if category == "affirmed":
        q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level != '0')
    elif category == "draft":
        if 'withdrawn' in request.args and request.args['withdrawn'] == 'yes':
            q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft', 'withdrawn']))
        else:
            q = db.session.query(GeneDescription).filter(GeneDescription.species == sp).filter(GeneDescription.status.in_(['draft']))
    elif category == "level_0":
        q = db.session.query(GeneDescription).filter(GeneDescription.status == 'published', GeneDescription.species == sp, GeneDescription.affirmation_level == '0')
    else:
        flash(f'Invalid category {category}')
        return redirect('/')

    results = q.all()

    ret = ""
    for seq in sorted(results, key=lambda x: x.sequence_name):
        if 'V' in seq.sequence_type:
            ret += f'{seq.sequence_name.ljust(20)}  {simple.translate(seq.coding_seq_imgt)}  {simple.translate(seq.sequence[seq.cdr1_start-1:seq.cdr1_end])}  {simple.translate(seq.sequence[seq.cdr2_start-1:seq.cdr2_end])}  {simple.translate(seq.sequence[seq.cdr3_start-1:])}\r\n'

    if len(ret) == 0:
        return redirect(url_for('sequences', sp=sp))
    
    filename = f'{sp}_{category}_aa_alignment.txt'
    return Response(ret, mimetype="application/octet-stream", headers={"Content-disposition": "attachment; filename=%s" % filename})


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

        if form.evidence_file.data:
            return upload_evidence(form, species)

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

                sub = db.session.query(Submission).filter_by(submission_id=form.submission_id.data).one_or_none()
                if sub.species != species or sub.submission_status not in ('reviewing', 'published', 'complete'):
                    return redirect(url_for('sequences', sp=species))

                seq = db.session.query(InferredSequence).filter_by(id=int(form.sequence_name.data)).one_or_none()

                if seq is None or seq not in sub.inferred_sequences:
                    return redirect(url_for('sequences', sp=species))

            gene_description = GeneDescription()
            gene_description.sequence_name = form.new_name.data
            gene_description.species = species
            gene_description.species_subgroup = form.species_subgroup.data
            gene_description.status = 'draft'
            gene_description.maintainer = current_user.name
            gene_description.lab_address = current_user.address
            gene_description.functionalionality = 'F'
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

                parse_name_to_gene_description(gene_description)

            db.session.add(gene_description)
            db.session.commit()
            gene_description.description_id = "A%05d" % gene_description.id
            db.session.commit()
            if record_type == 'submission':
                gene_description.build_duplicate_list(db, seq.sequence_details.nt_sequence)
            return redirect(url_for('sequences', sp=species))

        except ValidationError as e:
            return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))

    # default 1-based CDR coords

    form.gapped_cdr1_start.data = default_imgt_cdr1[0] + 1
    form.gapped_cdr1_end.data = default_imgt_cdr1[1]
    form.gapped_cdr2_start.data = default_imgt_cdr2[0] + 1
    form.gapped_cdr2_end.data = default_imgt_cdr2[1]
    form.gapped_cdr3_start.data = default_imgt_fr3[1] + 1

    return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))


# Parse the name, if it's tractable
def parse_name_to_gene_description(gene_description):
    try:
        sn = gene_description.sequence_name
        if sn[:2] == 'IG' or sn[:2] == 'TR':
            gene_description.locus = sn[:3]
            # handle names of the form TRB1J1
            if sn[3] in ['V', 'D', 'J', 'C']:
                gene_description.sequence_type = sn[3]
            elif sn[4] in ['V', 'D', 'J', 'C']:
                gene_description.sequence_type = sn[4]

            if '-' in sn:
                if '*' in sn:
                    snq = sn.split('*')
                    gene_description.allele_designation = snq[1]
                    sn = snq[0]
                else:
                    gene_description.allele_designation = ''
                snq = sn.split('-')
                gene_description.subgroup_designation = snq[-1:][0]
                gene_description.gene_subgroup = '-'.join(snq[:-1])[4:]
            elif '*' in sn:
                snq = sn.split('*')
                gene_description.gene_subgroup = snq[0][4:]
                gene_description.allele_designation = snq[1]
            else:
                gene_description.gene_subgroup = sn[4:]
    except:
        pass


def get_opt_int(row, key, default=None):  # get an optional integer value from a row
    if key not in row or not row[key]:
        return default
    try:
        return int(row[key])
    except ValueError:
        return default

def get_opt_text(row, key, default=None):  # get an optional text value from a row
    if key not in row or not row[key]:
        return default
    return row[key]

def get_opt_bool(row, key, default=None):  # get an optional bool value from a row
    if key not in row or not row[key]:
        return default
    return bool(row[key])


def upload_sequences(form, species):
    errors = []

    last_coord = 0
    for coord in (form.gapped_cdr1_start.data, form.gapped_cdr1_end.data, form.gapped_cdr2_start.data, form.gapped_cdr2_end.data, form.gapped_cdr3_start.data):
        if coord is None:
            errors.append('All gapped CDR coordinates must be specified.')
            break
        if coord < last_coord:
            errors.append('Gapped CDR coordinates must be in ascending order')
            break
        last_coord = coord

    if len(errors) > 0:
        errors.append('Sequences not uploaded: please fix errors and try again')
        form.upload_file.errors = errors
        return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))

    # check file
    fi = io.StringIO(form.upload_file.data.read().decode("utf-8"))
    reader = csv.DictReader(fi)

    if form.merge_data.data and current_user.has_role('AdminEdit'):
        errors = custom_merge(reader, species, form)
        if errors:
            form.upload_file.errors = errors
            return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))
        return redirect(url_for('sequences', sp=species))

    required_headers = ['gene_label', 'imgt', 'functionality', 'type', 'inference_type', 'sequence', 'sequence_gapped', 'species_subgroup', 'subgroup_type', 
                        'alt_names', 'affirmation', 'j_codon_frame', 'j_cdr3_end', 'gene_start', 'gene_end']
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
        if row['functionality'] not in ['F', 'ORF', 'P']:
            errors.append('row %d: functionality must be F, ORF or P' % row_count)
        if row['type'][:3] not in ['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG']:
            errors.append('row %d: locus in type must be one of %s' % (row_count, ','.join(['IGH', 'IGK', 'IGL', 'TRA', 'TRB', 'TRD', 'TRG'])))
        if row['type'][3:] not in ['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader']:
            errors.append('row %d: sequence_type in type must be one of %s' % (row_count, ','.join(['V', 'D', 'J', 'CH1', 'CH2', 'CH3', 'CH4', 'Leader'])))
        if not row['sequence']:
            errors.append('row %d: no sequence' % row_count)
        if row['type'][3:] == 'V':
            if not row['sequence_gapped']:
                errors.append('row %d: no sequence_gapped' % row_count)
#            else:
#                v_seq = row['sequence_gapped'].replace('.', '').upper()
#                if v_seq not in row['sequence'].upper():
#                    errors.append('row %d: gapped sequence not found in full sequence' % row_count)
        if row['type'][3:] == 'J' and not row['j_codon_frame']:
            errors.append('row %d: no j_codon_frame' % row_count)
        if row['type'][3:] == 'J' and not row['j_cdr3_end']:
            errors.append('row %d: no j_cdr3_end' % row_count)

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
        return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))
    
    # construct zero-based feature ranges from CDR coordinates

    imgt_fr1 = (0, form.gapped_cdr1_start.data - 1)
    imgt_cdr1 = (form.gapped_cdr1_start.data - 1, form.gapped_cdr1_end.data)
    imgt_fr2 = (form.gapped_cdr1_end.data, form.gapped_cdr2_start.data - 1)
    imgt_cdr2 = (form.gapped_cdr2_start.data - 1, form.gapped_cdr2_end.data)
    imgt_fr3 = (form.gapped_cdr2_end.data, form.gapped_cdr3_start.data - 1)
    imgt_features = [imgt_fr1, imgt_cdr1, imgt_fr2, imgt_cdr2, imgt_fr3]

    fi.seek(0)
    reader = csv.DictReader(fi)

    gene_descriptions_to_add = []
    errors = []

    for row in reader:
        row['sequence'] = row['sequence'].upper()
        if not row['sequence_gapped']:
            row['sequence_gapped'] = row['sequence']
        else:
            row['sequence_gapped'] = row['sequence_gapped'].upper()
        gene_description = GeneDescription()

        existing_entry = db.session.query(GeneDescription).filter(
                and_(
                    GeneDescription.species == species,
                     or_(
                        GeneDescription.sequence_name == row['gene_label'],
                        GeneDescription.sequence_name == row['imgt'],
                        GeneDescription.imgt_name == row['gene_label'],
                        and_(GeneDescription.imgt_name == row['imgt'], row['imgt'] != '')
                        ),
                     or_(   
                        GeneDescription.species_subgroup == row['species_subgroup'],
                        GeneDescription.species_subgroup == None,
                        GeneDescription.species_subgroup == 'none',
                        ),
                     ~GeneDescription.status.in_(['withdrawn', 'superceded'])
                     )
                ).all()

        if existing_entry:
            existing_entry = existing_entry[0]

            merge_errors = merge_sequence_upload(existing_entry, row, gene_description)
            if merge_errors:
                errors.extend(merge_errors)
                continue
        else:
            gene_description.release_version = 1
            gene_description.notes = ''
            gene_description.sequence_name = row['gene_label']
            gene_description.inferred_extension = not (not get_opt_text(row, 'ext_3_prime')) and (not get_opt_text(row, 'ext_5_prime'))
            gene_description.ext_3prime = get_opt_text(row, 'ext_3_prime')
            gene_description.start_3prime_ext = None
            gene_description.end_3prime_ext = None
            gene_description.ext_5prime = get_opt_text(row, 'ext_5_prime')
            gene_description.start_5prime_ext = None
            gene_description.end_5prime_ext = None
            gene_description.sequence = row['sequence']
            gene_description.coding_seq_imgt = row['sequence_gapped']
            gene_description.paralogs = get_opt_text(row, 'paralogs')       

        gene_description.imgt_name = row['imgt']
        gene_description.alt_names = row['alt_names']
        gene_description.species = species
        gene_description.species_subgroup = row['species_subgroup']
        gene_description.species_subgroup_type = row['subgroup_type']
        gene_description.status = 'draft'
        gene_description.maintainer = current_user.name
        gene_description.lab_address = current_user.address
        gene_description.functionality = row['functionality']
        gene_description.inference_type = row['inference_type']
        gene_description.affirmation_level = int(row['affirmation'])
        gene_description.chromosome = get_opt_int(row, 'chromosome')
        gene_description.mapped = get_opt_text(row, 'mapped') == 'Y'
        gene_description.paralog_rep = get_opt_text(row, 'varb_rep') == 'Y'
        gene_description.curational_tags = get_opt_text(row, 'curational_tags')     
        gene_description.gene_start = get_opt_int(row, 'gene_start')
        gene_description.gene_end = get_opt_int(row, 'gene_end')

        parse_name_to_gene_description(gene_description)
        gene_description.locus = row['type'][0:3]
        gene_description.sequence_type = row['type'][3:]

        if gene_description.sequence_type == 'V':
            gene_description.utr_5_prime_start = get_opt_int(row, 'utr_5_prime_start')
            gene_description.utr_5_prime_end = get_opt_int(row, 'utr_5_prime_end')
            gene_description.leader_1_start = get_opt_int(row, 'leader_1_start')
            gene_description.leader_1_end = get_opt_int(row, 'leader_1_end')
            gene_description.leader_2_start = get_opt_int(row, 'leader_2_start')
            gene_description.leader_2_end = get_opt_int(row, 'leader_2_end')
            gene_description.v_rs_start = get_opt_int(row, 'v_rs_start')
            gene_description.v_rs_end = get_opt_int(row, 'v_rs_end')
            feats = delineate_v_gene(gene_description.coding_seq_imgt, imgt_features)
            gene_description.cdr1_start = feats['cdr1_start'] + gene_description.gene_start - 1 if feats['cdr1_start'] else None
            gene_description.cdr1_end = feats['cdr1_end'] + gene_description.gene_start - 1 if feats['cdr1_end'] else None
            gene_description.cdr2_start = feats['cdr2_start'] + gene_description.gene_start - 1 if feats['cdr2_start'] else None
            gene_description.cdr2_end = feats['cdr2_end'] + gene_description.gene_start - 1 if feats['cdr2_end'] else None
            gene_description.cdr3_start = feats['cdr3_start'] + gene_description.gene_start - 1 if feats['cdr3_start'] else None
        elif gene_description.sequence_type == 'D':
            gene_description.d_rs_3_prime_start = get_opt_int(row, 'd_rs_3_prime_start')
            gene_description.d_rs_3_prime_end = get_opt_int(row, 'd_rs_3_prime_end')
            gene_description.d_rs_5_prime_start = get_opt_int(row, 'd_rs_5_prime_start')
            gene_description.d_rs_5_prime_end = get_opt_int(row, 'd_rs_5_prime_end')
        elif gene_description.sequence_type == 'J':
            gene_description.j_rs_start = get_opt_int(row, 'j_rs_start')
            gene_description.j_rs_end = get_opt_int(row, 'j_rs_end')
            gene_description.j_codon_frame = row['j_codon_frame']
            gene_description.j_cdr3_end = row['j_cdr3_end']

        notes = []
        if 'notes' in row:
            notes.extend([x.strip() for x in row['notes'].split(',')])

        if len(notes):
            withnotes = ' with the following notes:'
        else:
            withnotes = '.'

        if len(gene_description.notes):
            additional = 'Additional information'
        else:
            additional = 'Information'

        add_notes = [f"{additional} for this sequence was imported into OGRDB via bulk update{withnotes}"]
        add_notes.extend(notes)

        if gene_description.notes:
            gene_description.notes += '\r\n\r\n'
        gene_description.notes += '\r\n'.join(add_notes)

        gene_descriptions_to_add.append(gene_description)

    if errors:
        db.session.rollback()
        errors.append('Sequences not uploaded: please fix errors and try again')
        form.upload_file.errors = errors
        return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))
    else:
        for gene_description in gene_descriptions_to_add:
            db.session.add(gene_description)
            db.session.commit()

            if not gene_description.description_id:
                gene_description.description_id = "A%05d" % gene_description.id
                db.session.commit()

    return redirect(url_for('sequences', sp=species))


def merge_sequence_upload(existing_entry, row, gene_description):
    errors = []
    # only update if the existing record is an inference - we only want to merge if there's an IARC record in OGRDB that pre-dates the germline set
    if existing_entry.inference_type != 'Rearranged Only' and existing_entry.inference_type != 'Rearranged':
        errors.append(f"Cannot merge {existing_entry.sequence_name} as there is an existing record which is not simply an inference")

    # don't update if there's an existing draft
    if existing_entry.status == 'draft':
        errors.append(f"Cannot merge {existing_entry.sequence_name} as there is an existing draft")

    existing_ungapped = existing_entry.coding_seq_imgt.replace('.', '').upper()
    new_ungapped = row['sequence_gapped'].replace('.', '').upper()

    # Check that sequences match
    if existing_ungapped not in new_ungapped:
        errors.append(f"Cannot merge {row['gene_label']}->{existing_entry.sequence_name}: core sequences do not match")

    if errors:
        return errors
    
    # Replace extensions with info from the new record
    gene_description.ext_3prime = ''
    gene_description.start_3prime_ext = None
    gene_description.end_3prime_ext = None
    gene_description.ext_5prime = ''
    gene_description.start_5prime_ext = None
    gene_description.end_5prime_ext = None
    gene_description.inferred_extension = False

    if existing_ungapped == new_ungapped:
        gene_description.ext_3prime = get_opt_text(row, 'ext_3_prime')
        gene_description.ext_5prime = get_opt_text(row, 'ext_5_prime')
    else:
        # Retain the existing coding_sequence_imgt. Adjust extensions if necessary
        pos = new_ungapped.find(existing_ungapped)

        if pos > 0:
            gene_description.ext_5prime = get_opt_text(row, 'ext_5_prime')
            gene_description.ext_5prime += new_ungapped.coding_seq_imgt[:pos]
        if len(new_ungapped) > pos + len(existing_ungapped):
            gene_description.ext_3prime = get_opt_text(row, 'ext_3_prime')
            gene_description.ext_3prime += new_ungapped[pos + len(existing_ungapped):]

    if gene_description.ext_3prime or gene_description.ext_5prime:        
        gene_description.inferred_extension = True

    # If IARC thought the sequence should be extended, did we find an extension?

    iarc_ext_length = 0
    while existing_entry.coding_seq_imgt[0 - iarc_ext_length - 1] == '.':
        iarc_ext_length += 1

    if iarc_ext_length > 0 and not gene_description.ext_3prime or len(gene_description.ext_3prime) != iarc_ext_length:
        errors.append(f"Cannot merge {row['gene_label']}->{existing_entry.sequence_name}: IARC extension length is {iarc_ext_length} but supplied ext_3prime length is {len(gene_description.ext_3prime)}")

    gene_description.coding_seq_imgt = existing_entry.coding_seq_imgt.upper()
    gene_description.sequence = row['sequence']
    gene_description.sequence_name = row['gene_label']
    gene_description.imgt_name = row['imgt'] if row['imgt'] else existing_entry.imgt_name

    alt_names = existing_entry.alt_names.split(',') if existing_entry.alt_names else []
    for an in row['alt_names'].split(','):
        if an not in alt_names:
            alt_names.append(an)

    if existing_entry.sequence_name != gene_description.sequence_name and existing_entry.sequence_name not in alt_names:
        alt_names.append(existing_entry.sequence_name)

    gene_description.alt_names = ','.join(alt_names)

    gene_description.release_version = existing_entry.release_version + 1

    # Capture any existing paralogs

    new_paralogs = []
    if 'paralogs' in row:
        new_paralogs = [x.strip() for x in row['paralogs'].split(',') if x.strip()]

    if existing_entry.paralogs:
        for x in existing_entry.paralogs.split(','):
            x = x.strip()
            if x and x not in new_paralogs:
                new_paralogs.append(x)

    gene_description.paralogs = ','.join(new_paralogs)

    # Merge observations and journal entries
    
    gene_description.description_id = existing_entry.description_id
    gene_description.notes = existing_entry.notes
 
    for inferred_sequence in existing_entry.inferred_sequences:
        gene_description.inferred_sequences.append(inferred_sequence)

    for gen in existing_entry.supporting_observations:
        gene_description.supporting_observations.append(gen)

    for acc in existing_entry.genomic_accessions:
        gene_description.genomic_accessions.append(acc)

    for journal_entry in existing_entry.journal_entries:
        new_entry = JournalEntry()
        copy_JournalEntry(journal_entry, new_entry)
        gene_description.journal_entries.append(new_entry)

    return errors


# A custom merge where we can write code for whatever merge is needed

def custom_merge(reader, species, form):
    mandatory_headers = ['gene_label', 'species', 'species_subgroup']

    errors = []

    for h in mandatory_headers:
        if h not in reader.fieldnames:
            errors.append(f'Column {h} not found')
            return errors

    for row in reader:
        if row['species'] != species:
            errors.append(f'Species {row["species"]} does not match {species}: sequence not merged')
            continue

        existing_entries = db.session.query(GeneDescription).filter(
                and_(
                    GeneDescription.species == species,
                     or_(
                        GeneDescription.sequence_name == row['gene_label'],
                        ),
                     or_(   
                        GeneDescription.species_subgroup == row['species_subgroup'],
                        GeneDescription.species_subgroup == None,
                        GeneDescription.species_subgroup == 'none',
                        ),
                     ~GeneDescription.status.in_(['withdrawn', 'superceded'])
                     )
                ).all()

        if existing_entries:
            error = False
            for entry in existing_entries:
                if entry.status == 'draft':
                    errors.append(f'Draft already exists for {row["gene_label"]}: sequence not merged')
                    error = True
                    break

            if not error and len(existing_entries) > 1:
                errors.append(f'Multiple sequences found for {row["gene_label"]}: sequence not merged')
                error = True

            if not error and len(existing_entries) == 0 or existing_entries[0].status != 'published':
                errors.append(f'Published sequence not found for {row["gene_label"]}: sequence not merged')
                error = True

            if not error:
                entry = existing_entries[0]
                seq = clone_seq(entry)

                # Make the required changes here

                # Fixes for J gene metadata

                if 'J' not in row['gene_label']:
                    errors.append(f'{row["gene_label"]}: is not a J: data not merged')
                else:
                    seq.j_cdr3_end = int(row['J CDR3 End'])
                    seq.j_codon_frame = row['Codon Frame']
                    notes = "J gene metadata updated to conform to MiAIRR standards"
                    print(f'{row["gene_label"]}: J gene metadata updated to conform to MiAIRR standards')

                    # publish the sequence
                    publish_sequence(seq, notes, False)
        else:
            errors.append(f'No existing sequence found for {row["gene_label"]}: sequence not merged')

    return errors
        


def upload_evidence(form, species):
    # check file
    errors = []
    fi = io.StringIO(form.evidence_file.data.read().decode("utf-8"))
    reader = csv.DictReader(fi)
    required_headers = ['gene_label', 'sequence', 'repository', 'accession', 'patch', 'start', 'end', 'sense', 'notes', 'species_subgroup', 'subgroup_type']
    headers = None
    row_count = 2
    missing_drafts = False

    gene_descriptions_to_update = {}

    for row in reader:
        if headers is None:
            headers = row.keys()
            missing_headers = set(required_headers) - set(headers)
            if len(missing_headers) > 0:
                errors.append('Missing column headers: %s' % ','.join(list(missing_headers)))
                break

        missing_fields = []
        nonblank_fields = ['gene_label', 'sequence', 'repository', 'accession', 'start', 'end', 'sense']
        for field in nonblank_fields:
            if not row[field]:
                missing_fields.append(field)

        if missing_fields:
            errors.append('row %s: missing fields: %s' % (row_count, ','.join(missing_fields)))

        try:
            row['start'] = int(row['start'])
            row['end'] = int(row['end'])
        except ValueError:
            errors.append('row %s: start and end must be integers' % row_count)

        if row['gene_label'] not in gene_descriptions_to_update:
            gene_description = db.session.query(GeneDescription).filter(
                    and_(
                        GeneDescription.species == species,
                        GeneDescription.sequence_name == row['gene_label'],
                        or_(   
                            GeneDescription.species_subgroup == row['species_subgroup'],
                            GeneDescription.species_subgroup == None,
                            GeneDescription.species_subgroup == 'none',
                            ),
                        GeneDescription.status == 'draft')
                    ).one_or_none()

            if gene_description is None:
                errors.append('row %s: no draft sequence found for %s' % (row_count, row['gene_label']))
                missing_drafts = True
                continue
            else:
                gene_descriptions_to_update[row['gene_label']] = {'gene_description': gene_description, 'rows': [row]}
        else:
            gene_descriptions_to_update[row['gene_label']]['rows'].append(row)

        if len(errors) >= 5:
            if missing_drafts:
                errors.append('Please ensure that a draft sequence has been created for each sequence in the evidence file.')
            errors.append('(Only showing first few errors)')
            break

        row_count += 1

    fi.seek(0)
    reader = csv.DictReader(fi)

    if errors:
        errors.append('Sequences not uploaded: please fix errors and try again')
        form.evidence_file.errors = errors
        return render_template('sequence_new.html', form=form, species=species, adminedit=current_user.has_role('AdminEdit'))
    
    # remove existing evidence matching the uploaded evidence

    for gd in gene_descriptions_to_update.values():
        gene_description = gd['gene_description']
        for row in gd['rows']:
            for genomic_accession in gene_description.genomic_accessions:
                if genomic_accession.accession == row['accession']:
                    db.session.delete(genomic_accession)
            for inferred_sequence in gene_description.inferred_sequences:
                if inferred_sequence.seq_accession_no == row['accession']:
                    db.session.delete(inferred_sequence)

    db.session.commit()

    for gd in gene_descriptions_to_update.values():
        gene_description = gd['gene_description']
        existing_accessions = []
        for genomic_accession in gene_description.genomic_accessions:
            existing_accessions.append(genomic_accession.accession)
        for inferred_sequence in gene_description.inferred_sequences:
            existing_accessions.append(inferred_sequence.seq_accession_no)
        for row in gd['rows']:
            if row['accession'] not in existing_accessions:
                genomic_support = GenomicSupport()
                genomic_support.sequence = row['sequence']
                genomic_support.sequence_type = row['sequence_type']
                genomic_support.repository = row['repository']
                genomic_support.accession = row['accession']
                genomic_support.patch_no = row['patch']
                genomic_support.sequence_start = int(row['start'])
                genomic_support.sequence_end = int(row['end'])
                genomic_support.sense = 'forward' if row['sense'] == '+' else 'reverse'

                if gene_description.sequence_type == 'V':
                    genomic_support.utr_5_prime_start = get_opt_int(row, 'utr_5_prime_start') 
                    genomic_support.utr_5_prime_end = get_opt_int(row, 'utr_5_prime_end') 
                    genomic_support.leader_1_start = get_opt_int(row, 'leader_1_start') 
                    genomic_support.leader_1_end = get_opt_int(row, 'leader_1_end') 
                    genomic_support.leader_2_start = get_opt_int(row, 'leader_2_start') 
                    genomic_support.leader_2_end = get_opt_int(row, 'leader_2_end') 
                    genomic_support.v_rs_start = get_opt_int(row, 'v_rs_start') 
                    genomic_support.v_rs_end = get_opt_int(row, 'v_rs_end') 
                elif gene_description.sequence_type == 'D':
                    genomic_support.d_rs_3_prime_start = get_opt_int(row, 'd_rs_3_prime_start')  
                    genomic_support.d_rs_3_prime_end = get_opt_int(row, 'd_rs_3_prime_end')  
                    genomic_support.d_rs_5_prime_start = get_opt_int(row, 'd_rs_5_prime_start')  
                    genomic_support.d_rs_5_prime_end = get_opt_int(row, 'd_rs_5_prime_end')  
                elif gene_description.sequence_type == 'J':
                    genomic_support.j_rs_start = get_opt_int(row, 'j_rs_start')  
                    genomic_support.j_rs_end = get_opt_int(row, 'j_rs_end')  
                    genomic_support.j_codon_frame = get_opt_int(row, 'j_codon_frame')
                    genomic_support.j_cdr3_end = get_opt_int(row, 'j_cdr3_end')

                gene_description.genomic_accessions.append(genomic_support)
                existing_accessions.append(row['accession'])

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

    binomial_to_common = {}
    for sp in db.session.query(SpeciesLookup.common, SpeciesLookup.binomial).all():
        binomial_to_common[sp[1]] = sp[0]

    vdjbase_species = seq.species

    if vdjbase_species in binomial_to_common:
        vdjbase_species = binomial_to_common[vdjbase_species]

    vdjbase_link = Markup('<a href="%sgenerep/%s/%s/%s">here</a>' % (app.config['VDJBASE_URL'],
                                                           vdjbase_species,
                                                           seq.locus,
                                                           seq.sequence_name))

    return render_template('sequence_view.html', form=form, tables=tables, sequence_name=seq.sequence_name, vdjbase_link=vdjbase_link)


# Python-based ranges of default IMGT elements and consequent ranges
# <---------------------------------- FR1-IMGT -------------------------------->______________ CDR1-IMGT ___________<-------------------- FR2-IMGT ------------------->___________ CDR2-IMGT ________<----------------------------------------------------- FR3-IMGT ----------------------------------------------------> CDR3-IMGT
default_imgt_fr1 = (0, 78)
default_imgt_cdr1 = (78, 114)
default_imgt_fr2 = (114, 165)
default_imgt_cdr2 = (165, 195)
default_imgt_fr3 = (195, 312)

# determine coordinates in the ungapped sequence, given gapped coordinates and the gapped sequence
def delineate_v_gene(seq, feature_ranges=[default_imgt_fr1, default_imgt_cdr1, default_imgt_fr2, default_imgt_cdr2, default_imgt_fr3]):
    coords = {}
    imgt_fr1, imgt_cdr1, imgt_fr2, imgt_cdr2, imgt_fr3 = feature_ranges

    #if seq[0] == '.':
    #    coords['fwr1_start'] = None     # FWR start
    #    coords['fwr1_end'] = None     # FWR1 stop
    #    coords['cdr1_start'] = None      # CDR1 start
    #    coords['cdr1_end'] = None      # CDR1 end
    #    coords['fwr2_start'] = None     # FWR2 start
    #    coords['fwr2_end'] = None     # FWR2 end
    #    coords['cdr2_start'] = None    # CDR2 start
    #    coords['cdr2_end'] = None     # CDR2 end
    #    coords['fwr3_start'] = None     # FWR3 start
    #    coords['fwr3_end'] = None     # FWR3 end
    #    coords['cdr3_start'] = None     # CDR3 start
    #    return coords       # not going to guess about 5' incomplete sequences
                            # can revisit if this ever becomes an issue
                                
    pos = 1
    coords['fwr1_start'] = pos     # FWR start
    pos += len(seq[slice(*imgt_fr1)].replace('.', '')) - 1
    coords['fwr1_end'] = pos     # FWR1 stop
    pos += 1
    coords['cdr1_start'] = pos      # CDR1 start
    pos += len(seq[slice(*imgt_cdr1)].replace('.', '')) - 1
    coords['cdr1_end'] = pos      # CDR1 end
    pos += 1
    coords['fwr2_start'] = pos     # FWR2 start
    pos += len(seq[slice(*imgt_fr2)].replace('.', '')) - 1
    coords['fwr2_end'] = pos      # FWR2 end
    pos += 1
    coords['cdr2_start'] = pos     # CDR2 start
    pos += len(seq[slice(*imgt_cdr2)].replace('.', '')) - 1
    coords['cdr2_end'] = pos     # CDR2 end
    pos += 1
    coords['fwr3_start'] = pos     # FWR3 start
    pos += len(seq[slice(*imgt_fr3)].replace('.', '')) - 1
    coords['fwr3_end'] = pos     # FWR3 end
    pos += 1
    coords['cdr3_start'] = pos     # CDR3 start

    # fix up for any coords that are incomplete at the 5' end

    for feat in 'fwr1_start', 'fwr1_end', 'cdr1_start', 'cdr1_end', 'fwr2_start', 'fwr2_end', 'cdr2_start', 'cdr2_end', 'fwr3_start', 'fwr3_end', 'cdr3_start':
        if coords[feat] < 1:
            coords[feat] = None

    return coords


# Copy submitter and acknowledgements from sequence submission to gene_description


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
                        if file.filename != '':
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
                    seq.inference_type = 'Rearranged Only'
                elif genomic:
                    seq.inference_type = 'Genomic Only'

                save_GeneDescription(db, seq, form)

                # Check that the coding sequence is contained in the full sequence and calculate the gene start and gene end

                if not seq.sequence:
                    form.sequence.errors.append('Sequence is required')
                    raise ValidationError()
                
                if not seq.coding_seq_imgt:
                    form.coding_seq_imgt.errors.append('Coding sequence is required')
                    raise ValidationError()
                
                seq.sequence = seq.sequence.upper()
                seq.coding_seq_imgt = seq.coding_seq_imgt.upper()
            
                pos = seq.sequence.find(seq.coding_seq_imgt.replace('.', ''))

                if pos < 0:
                    form.coding_seq_imgt.errors.append('Coding sequence not found in sequence')
                    raise ValidationError()
                else:
                    seq.gene_start = pos + 1
                    seq.gene_end = pos + len(seq.coding_seq_imgt.replace('.', ''))  # i.e. start + len - 1
                    db.session.commit()

                # if we have a V-gapped sequence but no cdr coordinates, assume IMTG standard numbering
                    
                no_cdr_coords = not form.cdr1_start.data and not form.cdr1_end.data and not form.cdr2_start.data and not form.cdr2_end.data and not form.cdr3_start.data 
                
                if seq.sequence_type == 'V' and seq.sequence and seq.coding_seq_imgt and no_cdr_coords:
                    coding_ungapped = seq.coding_seq_imgt.replace('.', '')
                    coding_start = seq.sequence.find(coding_ungapped)

                    if coding_start < 0:
                        flash('Coding sequence not found in sequence')
                        raise ValidationError()

                    uc = delineate_v_gene(seq.coding_seq_imgt)
                    seq.cdr1_start = uc['cdr1_start'] + coding_start if uc['cdr1_start'] else None
                    seq.cdr1_end = uc['cdr1_end'] + coding_start if uc['cdr1_end'] else None
                    seq.cdr2_start = uc['cdr2_start'] + coding_start if uc['cdr2_start'] else None
                    seq.cdr2_end = uc['cdr2_end'] + coding_start if uc['cdr2_end'] else None
                    seq.cdr3_start = uc['fwr3_end'] + 1 + coding_start if uc['fwr3_end'] else None
                    db.session.commit()
                    flash('IMGT standard numbering assumed for CDR delineation')
                elif seq.sequence_type == 'V':
                    cdr_coord_errors = False
                    if not form.cdr1_end.data:
                        form.cdr1_end.errors.append('Please specify the end coordinate')
                        cdr_coord_errors = True
                    elif not form.cdr1_start.data:
                        form.cdr1_start.errors.append('Please specify the start coordinate')
                        cdr_coord_errors = True
                    else:
                        if form.cdr1_start.data >= form.cdr1_end.data:
                            form.cdr1_end.errors.append('End coordinate must be greater than start coordinate')
                            cdr_coord_errors = True
                        if (form.cdr1_start.data - seq.gene_start) % 3 != 0:
                            form.cdr1_start.errors.append('CDR must start on a codon boundary')
                            cdr_coord_errors = True
                        if (form.cdr1_end.data - seq.gene_start) % 3 != 2:
                            form.cdr1_end.errors.append('CDR must end on a codon boundary')
                            cdr_coord_errors = True
                        if form.cdr1_start.data < seq.gene_start or form.cdr1_start.data > seq.gene_end:
                            form.cdr1_start.errors.append('CDR must lie between gene start and gene end')
                            cdr_coord_errors = True
                        if form.cdr1_end.data < seq.gene_start or form.cdr1_end.data > seq.gene_end:
                            form.cdr1_start.errors.append('CDR must lie between gene start and gene end')
                            cdr_coord_errors = True

                    if not form.cdr2_end.data:
                        form.cdr2_end.errors.append('Please specify the end coordinate')
                        cdr_coord_errors = True
                    elif not form.cdr2_start.data:
                        form.cdr2_start.errors.append('Please specify the start coordinate')
                        cdr_coord_errors = True
                    else:
                        if form.cdr2_start.data >= form.cdr2_end.data:
                            form.cdr2_end.errors.append('End coordinate must be greater than start coordinate')
                            cdr_coord_errors = True
                        if (form.cdr2_start.data - seq.gene_start) % 3 != 0:
                            form.cdr2_start.errors.append('CDR must start on a codon boundary')
                            cdr_coord_errors = True
                        if (form.cdr2_end.data - seq.gene_start) % 3 != 2:
                            form.cdr2_end.errors.append('CDR must end on a codon boundary')
                            cdr_coord_errors = True
                        if form.cdr2_start.data < seq.gene_start or form.cdr2_start.data > seq.gene_end:
                            form.cdr2_start.errors.append('CDR must lie between gene start and gene end')
                            cdr_coord_errors = True
                        if form.cdr1_end.data < seq.gene_start or form.cdr1_end.data > seq.gene_end:
                            form.cdr1_start.errors.append('CDR must lie between gene start and gene end')
                            cdr_coord_errors = True

                    if not form.cdr3_start.data:
                        form.cdr3_start.errors.append('Please specify the start coordinate')
                        cdr_coord_errors = True
                    else:
                        if (form.cdr3_start.data - seq.gene_start) % 3 != 0:
                            form.cdr3_start.errors.append('CDR must start on a codon boundary')
                            cdr_coord_errors = True
                        if form.cdr3_start.data < seq.gene_start or form.cdr2_start.data > seq.gene_end:
                            form.cdr3_start.errors.append('CDR must lie between gene start and gene end')
                            cdr_coord_errors = True

                    if cdr_coord_errors:
                        raise ValidationError()
                    


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
                flash('Please correct the errors below.')
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

    seq.sequence_name, seq.release_version, seq.species), [seq.species], 'iarc_sequence_released',
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


@app.route('/delete_sequences', methods=['POST'])
def delete_sequences():
    for id in request.form['ids'].split(','):
        seq = check_seq_edit(id)
        if seq is not None:
            seq.delete_dependencies(db)
            db.session.delete(seq)
            db.session.commit()
    return ''


@app.route('/publish_sequences', methods=['POST'])
def publish_sequences():
    for id in request.form['ids'].split(','):
        seq = check_seq_edit(id)
        if seq is not None:
            publish_sequence(seq, request.form['note'], False)
    flash('Sequences published')
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
        clone_seq(seq)
    return ''


def clone_seq(seq):
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

    for dupe in seq.duplicate_sequences:
        new_seq.duplicate_sequences.append(dupe)

    for acc in seq.genomic_accessions:
        new_acc = GenomicSupport()
        copy_GenomicSupport(acc, new_acc)
        new_seq.genomic_accessions.append(new_acc)

    for journal_entry in seq.journal_entries:
        new_entry = JournalEntry()
        copy_JournalEntry(journal_entry, new_entry)
        new_seq.journal_entries.append(new_entry)

    db.session.commit()
    return new_seq

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
        taxonomy = db.session.query(SpeciesLookup.ncbi_taxon_id).filter(SpeciesLookup.binomial == species).one_or_none()
        taxonomy = taxonomy[0] if taxonomy else 0

        for desc in results:
            ad.append(vars(AIRRAlleleDescription(desc, extend=False, fake_allele=False, taxonomy=taxonomy)))

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

    if genomic_support is None or genomic_support.gene_description is None or not genomic_support.gene_description.can_see(current_user):
        return redirect('/')

    table = make_GenomicSupport_view(genomic_support, genomic_support.gene_description.can_edit(current_user))

    # Import the sequence formatting functions
    from ogrdb.sequence.sequence_formatting import pretty_sequence_item, create_genomic_support_view_items

    # Create view items for genomic support coordinates
    gv_items = create_genomic_support_view_items(genomic_support)
    
    # Calculate coordinate offset for genomic support
    coordinate_offset = genomic_support.sequence_start if genomic_support.sequence_start else 0
    
    # Determine trailer text
    if genomic_support.sequence and len(genomic_support.sequence) > 0 and genomic_support.sequence[-1] == '.':
        trailer_text = "A trailing . indicates IARC's opinion that the sequence\n" \
                       "is likely to contain additional 3' nucleotides for which\n" \
                       "there is insufficient evidence to make an affirmation.\n" \
                       "Please see Notes for details."
    else:
        trailer_text = ''

    seq_pos = 0
    ind = 0
    for item in table.items:
        if item['item'] == 'URL':
            item['value'] = Markup('<a href="%s">%s</a>' % (item['value'], item['value']))
        elif item['field'] == 'sequence':
            # Apply sequence formatting with coordinate adjustment
            item['value'] = pretty_sequence_item('sequence', item['value'], genomic_support, trailer_text, gv_items, coordinate_offset)
            seq_pos = ind
        ind += 1

    try:
        coding_seq = genomic_support.sequence[genomic_support.gene_start - genomic_support.sequence_start:genomic_support.gene_end - genomic_support.sequence_start + 1]
    except:
        coding_seq = ''

    table.items.insert(seq_pos + 1, {
        'item': 'Coding sequence',
        'field': 'coding_seq_imgt',
        'value': pretty_sequence_item('genomic_coding_seq', coding_seq, genomic_support, trailer_text, gv_items, coordinate_offset),
        'tooltip': 'The portion of the genomic sequence that corresponds to the coding sequence of the gene.'
        })

    return render_template('genomic_support_view.html', table=table, name=genomic_support.gene_description.sequence_name)


@app.route('/sequence_from_vdjbase/<id>', methods=['GET', 'POST'])
@login_required
def sequence_from_vdjbase(id):
    novel_rec = db.session.query(NovelVdjbase).filter(NovelVdjbase.id == id).one_or_none()

    if not novel_rec:
        flash('VDJbase sequence not found')
        return redirect(url_for('vdjbase_review'))

    if not current_user.has_role(novel_rec.species):
        flash('You do not have rights to create the sequence')
        return redirect(url_for('vdjbase_review'))

    if db.session.query(GeneDescription).filter(and_(
            GeneDescription.species == novel_rec.species,
            GeneDescription.locus == novel_rec.locus,
            GeneDescription.sequence_name == novel_rec.vdjbase_name
            )).count():
        flash('A sequence with that name already exists in OGRDB')
        return redirect(url_for('vdjbase_review'))

    gene_description = GeneDescription()
    gene_description.sequence_name = novel_rec.vdjbase_name
    gene_description.species = novel_rec.species
    parse_name_to_gene_description(gene_description)
    gene_description.status = 'draft'
    gene_description.maintainer = current_user.name
    gene_description.lab_address = current_user.address
    gene_description.functionality = 'F'
    gene_description.inference_type = 'Rearranged Only'
    gene_description.release_version = 1
    gene_description.affirmation_level = 0
    gene_description.inferred_extension = False
    gene_description.ext_3prime = None
    gene_description.start_3prime_ext = None
    gene_description.end_3prime_ext = None
    gene_description.ext_5prime = None
    gene_description.start_5prime_ext = None
    gene_description.end_5prime_ext = None
    gene_description.sequence = novel_rec.sequence.replace('.', '')
    gene_description.locus = novel_rec.locus
    gene_description.coding_seq_imgt = novel_rec.sequence
    db.session.add(gene_description)
    db.session.commit()
    gene_description.description_id = "A%05d" % gene_description.id
    db.session.commit()

    if novel_rec.notes_entries:
        notes = ['Imported to OGRDB from VDJbase with the following notes:']
        notes.append(novel_rec.notes_entries[0].notes_text)
    else:
        notes = ['Imported to OGRDB from VDJbase']

    gene_description.notes = '\r\n'.join(notes)

    if novel_rec.notes_entries and novel_rec.notes_entries[0].attached_files:
        for vdjbase_af in novel_rec.notes_entries[0].attached_files:
            af = AttachedFile()
            af.gene_description = gene_description
            af.filename = vdjbase_af.filename
            db.session.add(af)
            db.session.commit()
            vdjbase_dirname = attach_path + 'V%5d' % novel_rec.id
            dirname = attach_path + gene_description.description_id

            try:
                if not isdir(dirname):
                    mkdir(dirname)
                vdjbase_fn = 'multi_attachment_%s' % vdjbase_af.id
                fn = 'multi_attachment_%s' % af.id
                full_path = os.path.join(dirname, fn)
                shutil.copyfile(os.path.join(vdjbase_dirname, vdjbase_fn), full_path)
            except:
                flash('Error saving attachment: %s' % vdjbase_af.filename)
                app.logger.error(format_exc())

    db.session.commit()
    return redirect(url_for('edit_sequence', id=gene_description.id))

