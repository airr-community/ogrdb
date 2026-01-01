# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import url_for
from copy import deepcopy

from flask_table import DateCol

import ogrdb.submission.genotype_routes
from imgt.imgt_ref import get_imgt_config
from db.styled_table import *
from db.gene_description_db import *

class SequenceListActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []

        if item.viewable:
            fmt_string.append('<a href="%s">%s</a>' % (url_for('sequence', id=item.id), item.sequence_name))
        else:
            fmt_string.append(item.sequence_name)

        if item.editable:
            fmt_string.append('<a href="%s" class="btn btn-xs text-ogrdb-warning icon_back" style="padding: 2px"><i class="bi bi-pencil-fill" data-bs-toggle="tooltip" title="Edit"></i>&nbsp;</a>'  % (url_for('edit_sequence', id=item.id)))
            fmt_string.append('<button onclick="seq_delete(this.id)" class="btn btn-xs text-ogrdb-danger icon_back" style="padding: 2px" id="%s"><i class="bi bi-trash-fill" data-bs-toggle="tooltip" title="Delete"></i>&nbsp;</button>' % (item.id))

        if item.draftable:
            fmt_string.append('<button onclick="seq_new_draft(this.id)" class="btn btn-xs text-ogrdb-warning icon_back" style="padding: 2px" id="%s"><i class="bi bi-files" data-bs-toggle="tooltip" title="Create Draft"></i></button>' % (item.id))
            fmt_string.append('<button onclick="seq_imgt_name(this.id)" class="btn btn-xs text-ogrdb-warning icon_back" style="padding: 2px" id="%s"><i class="bi bi-tag-fill" data-bs-toggle="tooltip" title="IMGT Name"></i></button>' % (item.id))

        if item.draftable and not item.editable:
            fmt_string.append('<button onclick="seq_withdraw(this.id)" class="btn btn-xs text-ogrdb-danger icon_back" style="padding: 2px" id="%s"><i class="bi bi-trash-fill" data-bs-toggle="tooltip" title="Delete"></i></button>' % (item.id))

        if (item.editable or item.draftable) and int(item.affirmation_level) < 3:
            inf_genotypes = [x.sequence_details for x in item.inferred_sequences]

            # We allow notes to persist (but not be shown) even if the genotype ceases to be visible because the submission has been returned to draft.
            # This means that the contents of the note will still be there when the submission is re-published.
            # The loop below copes with the 'vanishing' notes when calculating whether to display an info icon

            dupe_notes = []
            for note in item.dupe_notes:
                if ogrdb.submission.genotype_routes.genotype is None:           # The submission has been deleted: we may as well tidy up
                    db.session.delete(note)
                    db.session.commit()
                elif ogrdb.submission.genotype_routes.genotype in item.duplicate_sequences:
                    dupe_notes.append(note)

            if len(set(item.duplicate_sequences) - set(inf_genotypes) - set(item.supporting_observations)) > len(dupe_notes):
                fmt_string.append('<i class="bi bi-info-circle-fill" data-bs-toggle="tooltip" title="There are unreferenced matches to this sequence"></i>&nbsp;')

        return ''.join(fmt_string)


class SequenceListIMGTCol(StyledCol):
    def td_contents(self, item, attr_list):
        if item.imgt_name:
            imgt_config = get_imgt_config()
            # imgt_species = {v['alias']: k for k, v in imgt_config['species'].items()}
            imgt_species = {}
            for k,v in imgt_config['species'].items():
                aliases = v['alias'].split(',')
                for alias in aliases:
                    imgt_species[alias] = k
            fmt_string = '<a href="http://www.imgt.org/IMGTrepertoire/Proteins/alleles/index.php?species=%s&group=%s%s&gene=%s">%s</a>' % (imgt_species[item.species], item.locus, item.sequence_type, item.imgt_name.split('*')[0], item.imgt_name)
            # fmt_string = '<a href="http://www.imgt.org/genedb/GENElect?query=2+%s&species=%s">%s</a>' % (item.imgt_name.split('*')[0], imgt_species[item.species], item.imgt_name)
        else:
            fmt_string = ''

        return fmt_string


def add_feature_to_table(table, feature_name, col_name=None):
    if not col_name:
        col_name = feature_name

    # Derive start and end attribute names from feature_name
    start_attr = f"{feature_name}_start"
    end_attr = f"{feature_name}_end"

    class FeatureCol(StyledCol):
        def td_contents(self, item, attr_list):
            # Try to extract sequence from start/end coordinates
            start = getattr(item, start_attr, None)
            end = getattr(item, end_attr, None)
            
            if start is not None and end is not None:
                # Convert 1-based to 0-based for Python slicing
                seq = item.sequence[start - 1:end]
                if seq:
                    return seq
            
            # If no coordinates, check for feature presence/absence
            feature = getattr(item, feature_name, None)
            if feature:
                return '<i class="bi bi-check-lg text-ogrdb-success" data-bs-toggle="tooltip" title="%s present"></i>' % (feature_name.replace('_', ' ').capitalize())
            else:
                return '<i class="bi bi-x-lg text-ogrdb-danger" data-bs-toggle="tooltip" title="%s absent"></i>' % (feature_name.replace('_', ' ').capitalize())

    table.add_column(col_name, FeatureCol(feature_name.capitalize(), tooltip=f"{feature_name.replace('_', ' ').capitalize()} presence"))


def setup_sequence_list_table(results, current_user, edit=True):
    table = make_GeneDescription_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user) if edit else False
        item.draftable = item.can_draft(current_user)  if edit else False

    del table._cols['imgt_name']
    table.add_column('imgt_name', SequenceListIMGTCol('IMGT Name'))
    table._cols.move_to_end('imgt_name', last=False)

    table.add_column('sequence_name', SequenceListActionCol('Sequence Name'))
    table._cols.move_to_end('sequence_name', last=False)

    add_feature_to_table(table, 'utr_5_prime')
    add_feature_to_table(table, 'utr_3_prime')
    add_feature_to_table(table, 'leader_1')
    add_feature_to_table(table, 'leader_2')
    add_feature_to_table(table, 'v_rs')
    add_feature_to_table(table, 'd_rs_5_prime')
    add_feature_to_table(table, 'd_rs_3_prime')
    add_feature_to_table(table, 'j_rs')
    add_feature_to_table(table, 'c_exon_1')
    add_feature_to_table(table, 'c_exon_2')
    add_feature_to_table(table, 'c_exon_3')
    add_feature_to_table(table, 'c_exon_4')
    add_feature_to_table(table, 'c_exon_5')
    add_feature_to_table(table, 'c_exon_6')
    add_feature_to_table(table, 'c_exon_7')
    add_feature_to_table(table, 'c_exon_8')
    add_feature_to_table(table, 'c_exon_9')
    return table


def setup_sequence_version_table(results, current_user):
    table = setup_sequence_list_table(results, current_user)

    for k in list(table._cols.keys()):
        if k not in ['sequence_name', 'imgt_name']:
            del table._cols[k]

    table.add_column('release_version', StyledCol("Version", tooltip="Release version"))
    table._cols.move_to_end('release_version')
    table.add_column('release_date', StyledDateCol("Date", tooltip="Release date"))
    table._cols.move_to_end('release_date')
    return table
