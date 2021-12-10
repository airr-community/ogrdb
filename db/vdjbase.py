# FUnctions for the interface with VDJBase
import json
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func

from db.misc_db import Committee
import requests
from app import app, db
from db.novel_vdjbase_db import NovelVdjbase, make_NovelVdjbase_table


class VDJbaseError(Exception):
    def __init__(self, message):
        self.message = message


def call_vdjbase(payload):
    resp = requests.get(app.config['VDJBASE_URL'] + payload)
    if resp.status_code != 200:
        raise VDJbaseError('Error contacting VDJbase: status code %d' % resp.status_code)
    return json.loads(resp.text)


last_run = None

def update_from_vdjbase():
    global last_run
    # Need a check here to update just once a day

    if last_run and datetime.now() - last_run < timedelta(hours=21):
        return('Frequency limit exceeded: restart to over-ride')

    last_run = datetime.now()

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
                            db_rec.notes += '\rPresent again in VDJbase at %s' % datetime.ctime(datetime.now())

                        if changed:
                            db_rec.notes += '\rfields changed at %s: %s\rPrevious status: %s' % (datetime.ctime(datetime.now()), ','.join(changed), db_rec.status)
                            db_rec.status = 'modified'
                    else:
                        db_rec = NovelVdjbase(
                            vdjbase_name = row['name'],
                            species = ogrdb_species,
                            locus = dataset,
                            first_seen = func.now(),
                            last_seen = func.now(),
                            status = 'not reviewed',
                            updated_by = '',
                            notes = ''
                        )
                        for el in corresp_fields:
                            setattr(db_rec, el, row[el])
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


def setup_vdjbase_review_tables(results):
    table = make_NovelVdjbase_table(results)
    return table
