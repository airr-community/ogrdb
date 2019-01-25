# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Obtain/display details for inferred sequence record  from NCBI

from app import db
from db.record_set_db import *
from forms.cancel_form import *
from forms.inferred_sequence_form import *
from forms.aggregate_form import *
from get_ncbi_details import *
import hashlib


class LinkedAccessionCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(Markup('<a href="%s">%s</a>' % (item.rec_url, item.rec_accession_no)))

class LinkedRecordSet_table(StyledTable):
    id = Col("id", show=False)
    rec_accession_no = LinkedAccessionCol("Select Set", tooltip="Accession number of the record set within the repository (eg SRR7663069)")
    rec_record_title = StyledCol("Title", tooltip="Title of sequence record in the repository")


def update_inf_rep_details(seq, form, ncbi):
    if not ncbi:
        form.ncbi_hash.data = ''
        form.seq_record_title.data = ''
        for rec in seq.record_set:
            db.session.delete(rec)
        return

    # Check if ncbi related fields have changed
    hash = hashlib.md5(form.seq_accession_no.data.encode('utf-8')+form.run_ids.data.encode('utf-8')).hexdigest()

    if form.ncbi_hash.data == hash:
        return

    try:
        resp = get_nih_nuc_details(form.seq_accession_no.data)
        form.seq_record_title.data = resp['title']
    except ValueError as e:
        form.seq_accession_no.errors = [e.args[0]]
        raise ValidationError()

    try:
        for rec in seq.record_set:
            db.session.delete(rec)

        run_ids = form.run_ids.data
        run_ids = run_ids.replace(',', ' ')
        run_ids = run_ids.replace(';', ' ')
        run_ids = run_ids.split()

        for run_id in run_ids:
            resp = get_nih_srr_details(run_id)
            rec = RecordSet()
            rec.rec_accession_no = run_id
            rec.rec_record_title = resp['title']
            rec.rec_url = resp['url']
            seq.record_set.append(rec)

        db.session.commit()

    except ValueError as e:
        form.run_ids.errors = [e.args[0]]
        raise ValidationError()

    form.ncbi_hash.data = hash



def setup_inferred_sequence_form(seq):
    form = AggregateForm(InferredSequenceForm(), CancelForm())
    form.genotype_id.choices = [(str(desc.id), desc.genotype_name) for desc in seq.submission.genotype_descriptions]
    if seq.genotype_description is not None:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.genotype_description.genotypes]
    else:
        form.sequence_id.choices = [('', 'Select a sequence')] + [(str(genotype.id), genotype.sequence_id) for genotype in seq.submission.genotype_descriptions[0].genotypes]
    form.seq_record_title.data = seq.seq_record_title

    return form

