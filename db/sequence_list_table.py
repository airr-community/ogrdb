# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import url_for
from copy import deepcopy

from db.styled_table import *
from db.gene_description_db import *

class SequenceListActionCol(StyledCol):
    def td_contents(self, item, attr_list):
        fmt_string = []

        if item.viewable:
            fmt_string.append('<a href="%s">%s</a>'  % (url_for('sequence', id=item.id), item.sequence_name))
        else:
            fmt_string.append(item.submission_id)

        if item.editable:
            fmt_string.append('<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;</a>'  % (url_for('edit_sequence', id=item.id)))
            fmt_string.append('<button onclick="seq_delete(this.id)" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>' % (item.id))

        if item.draftable:
            fmt_string.append('<button onclick="seq_new_draft(this.id)" class="btn btn-xs text-warning icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-duplicate" data-toggle="tooltip" title="Create Draft"></span></button>' % (item.id))
            fmt_string.append('<button onclick="seq_imgt_name(this.id)" class="btn btn-xs text-warning icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-tag" data-toggle="tooltip" title="IMGT Name"></span></button>' % (item.id))
            fmt_string.append('<button onclick="seq_withdraw(this.id)" class="btn btn-xs text-danger icon_back" style="padding: 2px" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span></button>' % (item.id))

        if (item.editable or item.draftable) and int(item.affirmation_level) < 3:
            inf_genotypes = [x.sequence_details for x in item.inferred_sequences]

            # We allow notes to persist (but not be shown) even if the genotype ceases to be visible because the submission has been returned to draft.
            # This means that the contents of the note will still be there when the submission is re-published.
            # The loop below copes with the 'vanishing' notes when calculating whether to display an info icon

            dupe_notes = []
            for note in  item.dupe_notes:
                if note.genotype is None:           # The submission has been deleted: we may as well tidy up
                    db.session.delete(note)
                    db.session.commit()
                elif note.genotype in item.duplicate_sequences:
                    dupe_notes.append(note)

            if len(set(item.duplicate_sequences) - set(inf_genotypes) - set(item.supporting_observations)) > len(dupe_notes):
                fmt_string.append('<span class="glyphicon glyphicon-info-sign" data-toggle="tooltip" title="There are unreferenced matches to this sequence"></span>&nbsp;')

        return ''.join(fmt_string)

def setup_sequence_list_table(results, current_user):
    table = make_GeneDescription_table(results)
    for item in table.items:
        item.viewable = item.can_see(current_user)
        item.editable = item.can_edit(current_user)
        item.draftable = item.can_draft(current_user)
    table.add_column('sequence_name', SequenceListActionCol('Sequence Name'))
    table._cols.move_to_end('sequence_name', last=False)
    return table

