# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import sys
from traceback import format_exc

from flask import request, render_template, Response, flash, url_for, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import redirect

from head import app, db, attach_path
from db.genotype_description_db import make_GenotypeDescription_view
from ogrdb.submission.genotype_view_options_form import GenotypeViewOptionsForm
from ogrdb.submission.genotype_view_table import setup_gv_table, setup_gv_fasta
from ogrdb.submission.genotype_description_compound_form import LinkedSample_table
from ogrdb.submission.genotype_description_routes import check_genotype_description_view, check_genotype_description_edit
from ogrdb.submission.inferred_sequence_compound_form import LinkedRecordSet_table


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


@app.route('/delete_genotype/<id>', methods=['POST'])
@login_required
def delete_genotype(id):
    desc = check_genotype_description_edit(id)
    if desc is not None:
        desc.delete_dependencies(db)
        db.session.delete(desc)
        db.session.commit()
    return ''