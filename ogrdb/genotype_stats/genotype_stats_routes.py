# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
from os import mkdir
from os.path import isdir

from flask import request, render_template, Response, flash, redirect
from flask_login import current_user, login_required

from db.misc_db import Committee
from head import db, attach_path, app

from ogrdb.genotype_stats.genotype_stats_form import GeneStatsForm, setup_gene_stats_tables

user_attach_path = attach_path + 'user/'
if not isdir(user_attach_path):
    mkdir(user_attach_path)


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

