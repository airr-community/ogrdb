# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#



from db.gene_description_db import *
from db.journal_entry_db import *
from db.inferred_sequence_table import MessageHeaderCol, MessageBodyCol, setup_inferred_sequence_table, setup_matching_submissions_table, setup_supporting_observation_table, setup_vdjbase_matches_table
from forms.submission_edit_form import *
from forms.attached_file_form import *
from sequence_format import *
from textile_filter import safe_textile


class GeneDescriptionNotes_table(StyledTable):
    id = Col("id", show=False)
    notes = StyledCol("Notes", tooltip="Notes")


def make_GeneDescriptionNotes_table(results, private = False, classes=()):
    t=create_table(base=GeneDescriptionNotes_table)
    ret = t(results, classes=classes)
    return ret


def setup_sequence_view_tables(db, seq, private):
    sections = {}
    sections['details'] = ["organism", "sequence_name", "imgt_name", "affirmation_level", "sequence", "coding_seq_imgt", "functional", "inference_type", "alt_names", "paralogs"]
    sections['non-coding'] = ["utr_5_prime_start", "utr_5_prime_end", "l_region_start", "l_region_end", "v_rs_start", "v_rs_end", "d_rs_3_prime_start", "d_rs_3_prime_end", "d_rs_5_prime_start", "d_rs_5_prime_end", "j_rs_start", "j_rs_end"]
    sections['extension'] = ["inferred_extension", "ext_3prime", "start_3prime_ext", "end_3prime_ext", "ext_5prime", "start_5prime_ext", "end_5prime_ext"]
    sections['meta'] = ["description_id", "author", "lab_address", "release_version", "release_date", "release_description", "locus", "sequence_type", "gene_subgroup", "subgroup_designation", "allele_designation", "codon_frame", "j_cdr3_end"]

    gv = make_GeneDescription_view(seq)
    gv_items = {}
    for item in gv.items:
        gv_items[item['field']] = item

    wanted = []

    if seq.inference_type == 'Rearranged Only':
        if gv_items['inferred_extension']['value']:
            if len(gv_items['ext_3prime']['value']) > 0:
                wanted.extend(['ext_3prime', 'start_3prime_ext', 'end_3prime_ext'])
            if len(gv_items['ext_5prime']['value']) > 0:
                wanted.extend(['ext_5prime', 'start_5prime_ext', 'end_5prime_ext'])
    else:
        wanted = ['l_region_start', 'l_region_end']

        if seq.sequence_type == 'V':
            wanted.extend(['v_rs_start', 'v_rs_end', 'utr_5_prime_start', 'utr_5_prime_end', 'ext_3prime', 'start_3prime_ext', 'end_3prime_ext', 'ext_3prime', 'start_5prime_ext', 'end_5prime_ext'])
        elif seq.sequence_type == 'D':
            wanted.extend(['d_rs_3_prime_start', 'd_rs_3_prime_end', 'd_rs_5_prime_start', 'd_rs_5_prime_end'])
        elif seq.sequence_type == 'J':
            wanted.extend(['j_rs_start', 'j_rs_end'])

    if seq.sequence_type == 'J':
        wanted.extend(['j_cdr3_end', 'codon_frame'])

    optional_fields = ['l_region_start', 'l_region_end', 'utr_5_prime_start', 'utr_5_prime_end', 'inferred_extension', 'ext_3prime', 'start_3prime_ext', 'end_3prime_ext', 'ext_5prime', 'start_5prime_ext', 'end_5prime_ext',
                  'v_rs_start', 'v_rs_end', 'd_rs_3_prime_start', 'd_rs_3_prime_end', 'd_rs_5_prime_start', 'd_rs_5_prime_end',
                  'j_rs_start', 'j_rs_end', 'j_cdr3_end', 'codon_frame']

    for field in list(gv_items.keys()):
        if field in optional_fields and field not in wanted:
            del(gv_items[field])

    if seq.sequence[-1] == '.':
        trailer_text = "A trailing . indicates IARC's opinion that the sequence\n" \
                   "is likely to contain additional 3' nucleotides for which\n" \
                   "there is insufficient evidence to make an affirmation.\n" \
                   "Please see Notes for details."
    else:
        trailer_text = ''

    for fn, field in gv_items.items():
        if fn == 'sequence':
            if field['value'] is not None and len(field['value']) > 0:
                field['value'] =  Markup('<button id="seq_view" name="seq_view" type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s" data-toggle="tooltip" title="View"><span class="glyphicon glyphicon-search"></span>&nbsp;</button>' \
                    % (format_nuc_sequence(seq.sequence, 50) + trailer_text, seq.sequence_name, format_fasta_sequence(seq.sequence_name, seq.sequence, 50)))
            else:
                field['value'] = 'None'
        elif fn == 'coding_seq_imgt':
            if field['value'] is not None and len(field['value']) > 0:
                if seq.sequence_type == 'V':
                    field['value'] = Markup(popup_seq_button(seq.sequence_name, seq.coding_seq_imgt.replace('.', ''), seq.coding_seq_imgt))
                else:
                    field['value'] = Markup(popup_seq_button(seq.sequence_name, seq.coding_seq_imgt, ''))
#                    field['value'] =  Markup('<button id="seq_coding_view" name="seq_coding_view" type="button" class="btn btn-xs text-info icon_back" data-toggle="modal" data-target="#seqModal" data-sequence="%s" data-name="%s" data-fa="%s"><span class="glyphicon glyphicon-search" data-toggle="tooltip" title="View"></span>&nbsp;</button>' \
#                        % (format_nuc_sequence(seq.sequence, 50) + trailer_text, seq.sequence_name, format_fasta_sequence(seq.sequence_name, seq.sequence, 50)))
            else:
                field['value'] = 'None'
        elif fn == 'release_description':
            if field['value'] is not None and len(field['value']) > 0:
                field['value'] = Markup(safe_textile(field['value']))

    tables = {}

    tables['description'] = {}

    for sn, fields in sections.items():
        tables['description'][sn] = GeneDescription_view([])
        for field in fields:
            if field in gv_items:
                tables['description'][sn].items.append(gv_items[field])

    if 'ext_3prime' not in gv_items and 'ext_5prime' not in gv_items:
        tables['description']['extension'] = []

    tables['inferred_sequences'] = setup_inferred_sequence_table(seq.inferred_sequences, seq, action=False)
    tables['supporting_observations'] = setup_supporting_observation_table(seq, action=False)
    tables['vdjbase_matches'] = setup_vdjbase_matches_table(seq)
    tables['matches'] = setup_matching_submissions_table(seq, add_action=False) if private else None
    tables['acknowledgements'] = make_Acknowledgements_table(seq.acknowledgements)
    tables['notes'] = make_GeneDescriptionNotes_table([{'notes': Markup(safe_textile(seq.notes)), 'id': seq.id}])
    tables['attachments'] = EditableAttachedFileTable(make_AttachedFile_table(seq.attached_files), 'attached_files', AttachedFileForm, seq.attached_files, legend='Attachments', delete=False, download_route='download_sequence_attachment')
    history = db.session.query(JournalEntry).filter_by(gene_description_id = seq.id, type = 'history').all()
    tables['history'] = []

    for entry in history:
        t = StyledTable([entry], classes=['tablefixed'])
        t.add_column('header', MessageHeaderCol("", tooltip=""))
        t._cols['header'].th_html_attrs['class'] += ' row-20'
        t.add_column('body', MessageBodyCol("", tooltip=""))
        t._cols['body'].th_html_attrs['class'] += ' row-80'
        tables['history'].append(t)

    return tables
