# FUnctions for the interface with VDJBase
import json
import os
from datetime import datetime, timedelta

from flask import url_for
from markupsafe import Markup
from sqlalchemy import and_, func

from db.misc_db import Committee
import requests
from head import app, db
from db.notes_entry_db import NotesEntry
from db.novel_vdjbase_db import NovelVdjbase, make_NovelVdjbase_table
from db.styled_table import StyledCol
from sequence_format import popup_seq_button


class DetailsCol(StyledCol):
    def td_contents(self, item, attr_list):
        value = ''
        if item.sequence:
            if 'V' in item.vdjbase_name:
                value = popup_seq_button(item.vdjbase_name, item.sequence.replace('.', ''),
                                         item.sequence).replace(
                        'btn_view_seq', 'seq_coding_view')
            else:
                value = popup_seq_button(item.vdjbase_name, item.sequence, '').replace('btn_view_seq', 'seq_coding_view')

        value += '''<a href=%s id="btn_view_notes" class="btn btn-xs text-info icon_back">
                     <span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Notes">
                     </a>
                 ''' % (url_for('vdjbase_review_detail', id=item.id))

        if item.editable:
            value += '''<button onclick="sequence_warn(%s, \'Press Create to create a sequence in OGRDB from this entry\')" 
                        type="button" class="btn btn-xs text-warning icon_back" id="%s">
                        <span class="glyphicon glyphicon-plus" data-toggle="tooltip" title="Create sequence in OGRDB">
                        </span>&nbsp;</button>''' % (item.id, item.id)


        return Markup(value)

class VdjbaseAlleleCol(StyledCol):
    def td_contents(self, item, attr_list):
        value = ''
        if item.vdjbase_name:
            value = '<a href=%sgenerep/%s/%s/%s>%s</a>' % (app.config['VDJBASE_URL'],
                                                           item.species.replace('Human_TCR', 'Human'),
                                                           item.locus,
                                                           item.vdjbase_name,
                                                           item.vdjbase_name)
        return Markup(value)


class VDJbaseError(Exception):
    def __init__(self, message):
        self.message = message


def call_vdjbase(payload):
    resp = requests.get(os.path.join(app.config['VDJBASE_API'] + payload))
    if resp.status_code != 200:
        raise VDJbaseError('Error contacting VDJbase: status code %d' % resp.status_code)
    return json.loads(resp.text)


last_run = None

def update_from_vdjbase():
    global last_run

    if last_run and datetime.now() - last_run < timedelta(hours=21):
        return('Update_from_VDJbase: frequency limit exceeded: restart to over-ride')

    last_run = datetime.now()

    # Update set of oll novels not just full-length

    update_vdjbase_ref()

    # Work out which datasets to collect from VDJbase and process
    ogrdb_sets = {}
    species = db.session.query(Committee.species, Committee.loci).all()
    for s in species:
        if s[1]:
            # fudge species/committee names
            sp = s[0] if s[0] != 'Human_TCR' else 'Human'
            if sp == 'Test':
                continue

            if sp not in ogrdb_sets:
                ogrdb_sets[sp] = []
            ogrdb_sets[sp].extend([ds.replace(' ', '') for ds in s[1].split(',')])

    try:
        vdjbase_sets = {}
        vdjbase_species = call_vdjbase('repseq/species')

        for v_s in vdjbase_species:
            if v_s in ogrdb_sets:
                vdjbase_datasets = call_vdjbase('repseq/ref_seqs/%s' % v_s)
                for ds in vdjbase_datasets:
                    if ds['dataset'] in ogrdb_sets[v_s]:
                        if v_s not in vdjbase_sets:
                            vdjbase_sets[v_s] = []
                        vdjbase_sets[v_s].append(ds['dataset'])

    except VDJbaseError as e:
        app.logger.error(e)
        return False

    # Pull the datasets back and merge results into our table

    for species, datasets in vdjbase_sets.items():
        for dataset in datasets:
            # fudge for dual Human committees
            ogrdb_species = species
            if species == "Human" and dataset in ['TRA', 'TRB', 'TRD', 'TRG']:
                ogrdb_species = "Human_TCR"

            expected_alleles = db.session.query(NovelVdjbase.vdjbase_name) \
                .filter(and_(NovelVdjbase.species == ogrdb_species, NovelVdjbase.locus == dataset)).all()
            expected_alleles = [r[0] for r in expected_alleles]

            try:
                results = call_vdjbase('repseq/novels/%s/%s' % (species, dataset))

                for allele, row in results.items():
                    db_rec = db.session.query(NovelVdjbase)\
                        .filter(and_(NovelVdjbase.species == ogrdb_species,
                                     NovelVdjbase.locus == dataset,
                                     NovelVdjbase.vdjbase_name == row['name']))\
                        .one_or_none()

                    corresp_fields = ['subject_count', 'j_haplotypes', 'd_haplotypes', 'hetero_alleleic_j_haplotypes', 'example', 'sequence']

                    if db_rec:
                        changed = []
                        db_rec.last_seen = func.now()
                        for el in corresp_fields:
                            if getattr(db_rec, el) != row[el]:
                                changed.append(el)
                                setattr(db_rec, el, row[el])

                        if db_rec.status == 'not current':
                            db_rec.status = 'not reviewed'
                            db_rec.notes_entries[0].notes_text += '\rPresent again in VDJbase at %s' % datetime.ctime(datetime.now())

                        if changed:
                            db_rec.notes_entries[0].notes_text += '\rfields changed at %s: %s\rPrevious status: %s' % (datetime.ctime(datetime.now()), ','.join(changed), db_rec.status)
                            db_rec.status = 'modified'
                    else:
                        db_rec = NovelVdjbase(
                            vdjbase_name=row['name'],
                            species=ogrdb_species,
                            locus=dataset,
                            first_seen=func.now(),
                            last_seen=func.now(),
                            status='not reviewed',
                            updated_by='',
                        )
                        for el in corresp_fields:
                            setattr(db_rec, el, row[el])

                        db_rec.notes_entries.append(NotesEntry())
                        db_rec.notes_entries[0].notes_text = ''
                        db.session.add(db_rec)

                    if row['name'] in expected_alleles:
                        expected_alleles.remove(row['name'])

                if expected_alleles:
                    for name in expected_alleles:
                        db_rec = db.session.query(NovelVdjbase)\
                                    .filter(and_(NovelVdjbase.species == ogrdb_species,
                                     NovelVdjbase.locus == dataset,
                                     NovelVdjbase.vdjbase_name == name))\
                                    .one_or_none()
                        if db_rec:
                            db_rec.status = 'not current'
                            db_rec.notes += '\rNo longer seen in VDJbase at %s' % datetime.ctime(datetime.now())

                db.session.commit()

            except VDJbaseError as e:
                app.logger.error(e)

    return 'Import complete'

def setup_vdjbase_review_tables(results, editor):
    table = make_NovelVdjbase_table(results)

    for item in table.items:
        item.editable = editor

    table._cols['id'].show = True
    table._cols['vdjbase_name'] = VdjbaseAlleleCol('VDJbase Name')
    del table._cols['sequence']     # put the full sequence at the end
    table.add_column('sequence2', DetailsCol(""))
    table.add_column('sequence', StyledCol("VDJbase sequence"))

    return table

# Functions for managing ALL VDJbase inferences (not just full-length) used to annotate genotypes and submissions
# These are kept in an in-memory structure for fast access

vdjbase_genes = {}
vdjbase_gene_update_stamp = 0


def update_vdjbase_ref():
    try:
        ret = call_vdjbase('repseq/all_novels')
    except VDJbaseError as e:
        app.logger.error(e)
        return

    if len(ret) > 0:
        with open(app.config['VDJBASE_NOVEL_FILE'], 'w') as fo:
            json.dump(ret, fo)
    else:
        app.logger.error('Zero-length novels file returned from VDJbase')


def init_vdjbase_ref():
    global vdjbase_genes, vdjbase_gene_update_stamp

    try:
        if not os.path.isfile(app.config['VDJBASE_NOVEL_FILE']):
            update_vdjbase_ref()

        if os.path.isfile(app.config['VDJBASE_NOVEL_FILE']):
            with open(app.config['VDJBASE_NOVEL_FILE'], 'r') as fi:
                ret = json.load(fi)
            if len(ret) > 0:
                vdjbase_genes = ret
                vdjbase_gene_update_stamp = os.path.getmtime(app.config['VDJBASE_NOVEL_FILE'])
            else:
                app.logger.error('Zero-length VDJbase novels file read from disk')
    except:
        app.logger.error('Error reading VDJbase novels file from disk')


def get_vdjbase_ref():
    if os.path.isfile(app.config['VDJBASE_NOVEL_FILE']) and os.path.getmtime(app.config['VDJBASE_NOVEL_FILE']) > vdjbase_gene_update_stamp:
        init_vdjbase_ref()

    return vdjbase_genes

