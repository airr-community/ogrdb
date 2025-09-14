# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Gene table routes

from flask import render_template, request, jsonify, make_response
from flask_login import current_user
from head import app, db
from db.gene_description_db import GeneDescription
from db.styled_table import StyledTable, Col, LinkCol, StyledCol
from db.misc_db import Committee
from forms.gene_table_form import GeneTableForm
import io
import csv
from datetime import datetime


@app.route('/gene_table', methods=['GET', 'POST'])
def gene_table():
    form = GeneTableForm()
    
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
    
    tables = None
    selected_species = None
    selected_subgroup = None
    selected_locus = None
    
    if form.validate_on_submit():
        selected_species = form.species.data
        selected_subgroup = form.species_subgroup.data if form.species_subgroup.data else None
        selected_locus = form.locus.data
        
        # Generate gene table based on selected species, subgroup, and locus
        tables = create_gene_table(selected_species, selected_subgroup, selected_locus)
    elif request.method == 'POST':
        # Debug form validation errors
        print("Form validation failed:")
        for field_name, errors in form.errors.items():
            print(f"  {field_name}: {errors}")
    
    return render_template('gene_table.html', form=form, tables=tables,
                           selected_species=selected_species, selected_subgroup=selected_subgroup, selected_locus=selected_locus)


def get_available_species():
    """Get species that have published sequences or unpublished sequences for user's committees"""
    species_set = set()
    
    # Get species with published, non-withdrawn sequences
    published_species = db.session.query(GeneDescription.species).filter(
        GeneDescription.status == 'published'
    ).distinct().all()
    species_set.update([s[0] for s in published_species])
    
    # If user is authenticated and has committee roles, add species
    if current_user.is_authenticated:
        user_committees = [role.name for role in current_user.roles if role.name not in ('Admin', 'AdminEdit')]
        
        for committee_species in user_committees:
            species_set.add(committee_species)
    
    return sorted(list(species_set))


def get_available_loci(species, subgroup=None):
    """Get loci available for a specific species and subgroup based on sequence availability"""
    loci_set = set()
    
    # Base query filters
    base_filters = [GeneDescription.species == species]
    if subgroup:
        base_filters.append(GeneDescription.species_subgroup == subgroup)
    
    # Get loci from published sequences
    published_query = db.session.query(GeneDescription.locus).filter(
        *base_filters,
        GeneDescription.status == 'published'
    ).distinct()
    published_loci = published_query.all()
    loci_set.update([locus[0] for locus in published_loci if locus[0]])
    
    # If user has access to this species committee, include all loci for the committee
    if current_user.is_authenticated and current_user.has_role(species):
        loci = db.session.query(Committee.loci).filter(Committee.species == species).one_or_none()
        if loci and loci[0]:
            committee_loci = [l.strip() for l in loci[0].split(',') if l.strip()]
            loci_set.update(committee_loci)
    
    return sorted(list(loci_set))


def get_available_subgroups(species):
    """Get available subgroups for a species"""
    subgroups_set = set()
    
    # Get subgroups from published sequences
    published_subgroups = db.session.query(GeneDescription.species_subgroup).filter(
        GeneDescription.species == species,
        GeneDescription.status == 'published',
        GeneDescription.species_subgroup.isnot(None),
        GeneDescription.species_subgroup != '',
        GeneDescription.species_subgroup != 'none'
    ).distinct().all()
    subgroups_set.update([sg[0] for sg in published_subgroups if sg[0]])
    
    # If user has access to this species committee, include unpublished subgroups
    if current_user.is_authenticated and current_user.has_role(species):
        unpublished_subgroups = db.session.query(GeneDescription.species_subgroup).filter(
            GeneDescription.species == species,
            GeneDescription.status.in_(['draft']),
            GeneDescription.species_subgroup.isnot(None),
            GeneDescription.species_subgroup != '',
            GeneDescription.species_subgroup != 'none'
        ).distinct().all()
        subgroups_set.update([sg[0] for sg in unpublished_subgroups if sg[0]])
    
    return sorted(list(subgroups_set))


@app.route('/get_subgroups/<species>', methods=['GET'])
def get_subgroups_for_species(species):
    """AJAX endpoint to get available subgroups for a species"""
    subgroups = get_available_subgroups(species)
    return jsonify(subgroups)


@app.route('/get_loci/<species>', methods=['GET'])
def get_loci_for_species(species):
    """AJAX endpoint to get available loci for a species"""
    subgroup = None
    if 'subgroup' in request.args:
        subgroup = request.args['subgroup']
        if subgroup == 'null' or subgroup == '' or subgroup == 'undefined':
            subgroup = None
    loci = get_available_loci(species, subgroup)
    return jsonify(loci)


class InferenceTypeTickCol(StyledCol):
    """Column that displays a tick if the specified inference type is present"""
    def __init__(self, name, inference_type_term, *args, **kwargs):
        self.inference_type_term = inference_type_term
        super(InferenceTypeTickCol, self).__init__(name, *args, **kwargs)
    
    def td_contents(self, item, attr_list):
        inference_type = item.get('inference_type', '') or ''
        if self.inference_type_term.lower() in inference_type.lower():
            return '<i class="bi bi-check-circle-fill text-success"></i>'
        return ''


class InSetTickCol(StyledCol):
    """Column that displays a tick if the sequence is in a published germline set"""
    def td_contents(self, item, attr_list):
        if item.get('in_published_set', False):
            return '<i class="bi bi-check-circle-fill text-success"></i>'
        return ''


class GeneTable(StyledTable):
    """Custom table for displaying gene information"""
    gene = LinkCol('Gene', 'alignments', url_kwargs=dict(species='species', locus='locus', gene_name='gene_name'), attr='gene_name')
    allele = LinkCol('Allele', 'sequence', url_kwargs=dict(id='description_id'), attr='allele')
    affirmation_level = Col('Affirmation Level')
    unrearranged = InferenceTypeTickCol('Unrearranged', 'Unrearranged')
    rearranged = InferenceTypeTickCol('Rearranged', 'Rearranged')
    in_set = InSetTickCol('In Set')
    
    def __init__(self, items, *args, **kwargs):
        kwargs['table_id'] = 'gene_table'
        super(GeneTable, self).__init__(items, *args, **kwargs)


def create_gene_table(species, subgroup, locus):
    """Create gene table data based on selection criteria"""
    # Base query filters
    base_filters = [
        GeneDescription.species == species,
        GeneDescription.locus == locus
    ]
    
    if subgroup:
        base_filters.append(GeneDescription.species_subgroup == subgroup)
    
    # Get published sequences (always included)
    published_query = db.session.query(GeneDescription).filter(
        *base_filters,
        GeneDescription.status == 'published'
    )
    
    # Get unpublished sequences if user has committee access
    unpublished_query = None
    if current_user.is_authenticated and current_user.has_role(species):
        unpublished_query = db.session.query(GeneDescription).filter(
            *base_filters,
            GeneDescription.status.in_(['draft'])
        )
    
    # Combine queries
    all_sequences = list(published_query.all())
    if unpublished_query:
        all_sequences.extend(unpublished_query.all())
    
    # Create table data
    table_data = []
    for seq in all_sequences:
        gene_name = seq.sequence_name.split('*')[0] if seq.sequence_name else ''
        # Generate allele name: <sequence_name> with (U) suffix for unpublished
        allele_name = seq.sequence_name or ''
        if seq.status == 'draft':
            allele_name += ' (U)'
        
        # Check if sequence is in any published germline set
        in_published_set = any(gs.status == 'published' for gs in seq.germline_sets)
        
        table_data.append({
            'species': species,
            'locus': locus,
            'gene_name': gene_name,
            'allele': allele_name,
            'description_id': seq.id,  # For linking to sequence detail page
            'inference_type': seq.inference_type or '',  # For tick display in unrearranged/rearranged columns
            'affirmation_level': seq.affirmation_level or '',  # Affirmation level column
            'in_published_set': in_published_set  # For tick display in 'in set' column
        })
    
    # Sort by gene name
    table_data.sort(key=lambda x: x['gene_name'])
    
    # Create table
    table = GeneTable(table_data)
    return {'gene_table': table}


@app.route('/download_gene_table_sequences/<species>/<locus>/<format>/<affirmation>/<in_set_only>')
def download_gene_table_sequences(species, locus, format, affirmation, in_set_only):
    """Download sequences from gene table with specified filters"""
    
    # Get subgroup from query parameter
    subgroup = request.args.get('subgroup')
    subgroup = None if subgroup == 'null' or subgroup == '' or subgroup == 'None' else subgroup
    
    # Build query filters
    base_filters = [
        GeneDescription.species == species,
        GeneDescription.locus == locus
    ]
    
    if subgroup:
        base_filters.append(GeneDescription.species_subgroup == subgroup)
    
    # Get published sequences (always included)
    published_query = db.session.query(GeneDescription).filter(
        *base_filters,
        GeneDescription.status == 'published'
    )
    
    # Get unpublished sequences if user has committee access
    unpublished_query = None
    if current_user.is_authenticated and current_user.has_role(species):
        unpublished_query = db.session.query(GeneDescription).filter(
            *base_filters,
            GeneDescription.status.in_(['draft'])
        )
    
    # Combine queries
    all_sequences = list(published_query.all())
    if unpublished_query:
        all_sequences.extend(unpublished_query.all())
    
    # Apply filters
    filtered_sequences = []
    for seq in all_sequences:
        # Apply affirmation level filter
        if affirmation == 'gt0':
            if not seq.affirmation_level or seq.affirmation_level == '0':
                continue
        
        # Apply in set filter
        if in_set_only == 'yes':
            in_published_set = any(gs.status == 'published' for gs in seq.germline_sets)
            if not in_published_set:
                continue
        
        filtered_sequences.append(seq)
    
    if not filtered_sequences:
        return "No sequences match the specified criteria", 404
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"gene_table_{species}_{locus}_{timestamp}"
    if subgroup:
        base_filename = f"gene_table_{species}_{subgroup}_{locus}_{timestamp}"
    
    if format == 'fasta':
        return generate_fasta_download(filtered_sequences, base_filename)
    elif format == 'csv':
        return generate_csv_download(filtered_sequences, base_filename)
    else:
        return "Invalid format", 400


def generate_fasta_download(sequences, filename):
    """Generate FASTA format download"""
    output = io.StringIO()
    
    for seq in sequences:
        # Write FASTA header
        header = f">{seq.sequence_name or seq.description_id}"
        if seq.status == 'draft':
            header += " (Unpublished)"
        output.write(header + "\n")
        
        # Write sequence (use coding_seq_imgt or sequence field)
        sequence_data = seq.coding_seq_imgt or seq.sequence or ""
        if sequence_data:
            # Format sequence to 80 characters per line
            for i in range(0, len(sequence_data), 80):
                output.write(sequence_data[i:i+80] + "\n")
        else:
            output.write("\n")  # Empty line for sequences without data
    
    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.fasta"
    response.headers["Content-Type"] = "text/plain"
    return response


def extract_flanking_sequence(sequence, start, end):
    """Extract flanking sequence using 1-based inclusive coordinates"""
    if not sequence or start is None or end is None:
        return ""
    
    # Convert 1-based inclusive to 0-based indexing for Python
    try:
        start_idx = int(start) - 1
        end_idx = int(end)  # end is inclusive, so no -1 needed for slicing
        
        if start_idx < 0 or end_idx > len(sequence) or start_idx >= end_idx:
            return ""
        
        return sequence[start_idx:end_idx]
    except (ValueError, TypeError):
        return ""


def generate_csv_download(sequences, filename):
    """Generate CSV format download"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write comprehensive header with gapped sequence and flanking sequences
    writer.writerow([
        'Gene', 'Allele', 'Affirmation_Level', 'Inference_Type', 'In_Published_Set',
        'Sequence', 'Gapped_Sequence', 'Status',
        'UTR_5_Prime', 'UTR_5_Prime_Start', 'UTR_5_Prime_End',
        'Leader_1', 'Leader_1_Start', 'Leader_1_End',
        'Leader_2', 'Leader_2_Start', 'Leader_2_End',
        'CDR1', 'CDR1_Start', 'CDR1_End',
        'CDR2', 'CDR2_Start', 'CDR2_End',
        'CDR3', 'CDR3_Start',
        'V_RS', 'V_RS_Start', 'V_RS_End',
        'D_RS_3_Prime', 'D_RS_3_Prime_Start', 'D_RS_3_Prime_End',
        'D_RS_5_Prime', 'D_RS_5_Prime_Start', 'D_RS_5_Prime_End',
        'J_RS', 'J_RS_Start', 'J_RS_End',
        'J_Codon_Frame', 'J_CDR3_End'
    ])
    
    # Write data
    for seq in sequences:
        gene_name = seq.sequence_name.split('*')[0] if seq.sequence_name else ''
        allele_name = seq.sequence_name or ''
        if seq.status == 'draft':
            allele_name += ' (U)'
        
        in_published_set = any(gs.status == 'published' for gs in seq.germline_sets)
        sequence_data = seq.sequence or ""
        gapped_sequence = seq.coding_seq_imgt or ""
        
        # Extract flanking sequences using coordinates
        utr_5_prime = extract_flanking_sequence(sequence_data, seq.utr_5_prime_start, seq.utr_5_prime_end)
        leader_1 = extract_flanking_sequence(sequence_data, seq.leader_1_start, seq.leader_1_end)
        leader_2 = extract_flanking_sequence(sequence_data, seq.leader_2_start, seq.leader_2_end)
        cdr1 = extract_flanking_sequence(sequence_data, seq.cdr1_start, seq.cdr1_end)
        cdr2 = extract_flanking_sequence(sequence_data, seq.cdr2_start, seq.cdr2_end)
        cdr3 = extract_flanking_sequence(sequence_data, seq.cdr3_start, seq.j_cdr3_end) if seq.cdr3_start and seq.j_cdr3_end else ""
        v_rs = extract_flanking_sequence(sequence_data, seq.v_rs_start, seq.v_rs_end)
        d_rs_3_prime = extract_flanking_sequence(sequence_data, seq.d_rs_3_prime_start, seq.d_rs_3_prime_end)
        d_rs_5_prime = extract_flanking_sequence(sequence_data, seq.d_rs_5_prime_start, seq.d_rs_5_prime_end)
        j_rs = extract_flanking_sequence(sequence_data, seq.j_rs_start, seq.j_rs_end)
        
        writer.writerow([
            gene_name,
            allele_name,
            seq.affirmation_level or '',
            seq.inference_type or '',
            'Yes' if in_published_set else 'No',
            sequence_data,
            gapped_sequence,
            seq.status,
            utr_5_prime,
            seq.utr_5_prime_start or '',
            seq.utr_5_prime_end or '',
            leader_1,
            seq.leader_1_start or '',
            seq.leader_1_end or '',
            leader_2,
            seq.leader_2_start or '',
            seq.leader_2_end or '',
            cdr1,
            seq.cdr1_start or '',
            seq.cdr1_end or '',
            cdr2,
            seq.cdr2_start or '',
            seq.cdr2_end or '',
            cdr3,
            seq.cdr3_start or '',
            v_rs,
            seq.v_rs_start or '',
            seq.v_rs_end or '',
            d_rs_3_prime,
            seq.d_rs_3_prime_start or '',
            seq.d_rs_3_prime_end or '',
            d_rs_5_prime,
            seq.d_rs_5_prime_start or '',
            seq.d_rs_5_prime_end or '',
            j_rs,
            seq.j_rs_start or '',
            seq.j_rs_end or '',
            seq.j_codon_frame or '',
            seq.j_cdr3_end or ''
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
    response.headers["Content-Type"] = "text/csv"
    return response