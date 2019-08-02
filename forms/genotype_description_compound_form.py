# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Obtain/display details for inferred sequence record  from NCBI

from app import db
from db.sample_name_db import *
from db.record_set_db import *
from forms.cancel_form import *
from forms.genotype_description_form import *
from forms.aggregate_form import *
from get_ncbi_details import *
from get_ena_details import *
import hashlib


class LinkedSamAccessionCol(StyledCol):
    def td_contents(self, item, attr_list):
        return self.td_format(Markup('<a href="%s">%s</a>' % (item.sam_url, item.sam_accession_no)))

class LinkedSample_table(StyledTable):
    id = Col("id", show=False)
    sam_accession_no = LinkedSamAccessionCol("Sample", tooltip="Accession number of the sample within the repository (eg SAMN06821255)")
    sam_record_title = StyledCol("Title", tooltip="Sample title in the repository")


def update_sample_details(gen, form, repo):
    if repo is None:
        form.gen_ncbi_hash.data = ''
        for rec in gen.sample_names:
            db.session.delete(rec)
        return

    # Check if ncbi related fields have changed
    hash = hashlib.md5(form.genotype_biosample_ids.data.encode('utf-8')+form.genotype_run_ids.data.encode('utf-8')).hexdigest()

    if form.gen_ncbi_hash.data == hash:
        return

    try:
        for rec in gen.sample_names:
            db.session.delete(rec)

        sam_ids = form.genotype_biosample_ids.data
        sam_ids = sam_ids.replace(',', ' ')
        sam_ids = sam_ids.replace(';', ' ')
        sam_ids = sam_ids.split()

        for sam_id in sam_ids:
            resp = get_nih_samn_details(sam_id) if repo == 'NCBI SRA' else get_ena_samn_details(sam_id)
            rec = SampleName()
            rec.sam_accession_no = sam_id
            rec.sam_record_title = resp['title']
            rec.sam_url = resp['url']
            gen.sample_names.append(rec)

    except ValueError as e:
        form.genotype_biosample_ids.errors = [e.args[0]]
        raise ValidationError()

    try:
        for rec in gen.record_set:
            db.session.delete(rec)

        run_ids = form.genotype_run_ids.data
        run_ids = run_ids.replace(',', ' ')
        run_ids = run_ids.replace(';', ' ')
        run_ids = run_ids.split()

        for run_id in run_ids:
            resp = get_nih_srr_details(run_id) if repo == 'NCBI SRA' else get_ena_srr_details(run_id)
            rec = RecordSet()
            rec.rec_accession_no = run_id
            rec.rec_record_title = resp['title']
            rec.rec_url = resp['url']
            gen.record_set.append(rec)

    except ValueError as e:
        form.genotype_run_ids.errors = [e.args[0]]
        raise ValidationError()

    db.session.commit()


    form.gen_ncbi_hash.data = hash



def setup_genotype_description_form(desc):
    form = AggregateForm(GenotypeDescriptionForm(), CancelForm())
    form.inference_tool_id.choices = [( str(tool.id), tool.tool_settings_name) for tool in desc.submission.inference_tools]
    return form

