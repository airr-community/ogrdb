# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Create genotype records from BLOB in database

from io import StringIO, BytesIO
import csv
from db.genotype_db import *
from flask import flash
from wtforms import ValidationError
from sqlalchemy.exc import OperationalError
from db.genotype_tables import *
from imgt.imgt_ref import gap_sequence
from imgt.imgt_ref import get_imgt_gapped_reference_genes

light_loci = ['IGK', 'IGL', 'TRA', 'TRG']

def file_to_genotype(name, desc, db):
    refs = get_imgt_gapped_reference_genes()
    line = 2
    try:
        fi = open(name, 'r')
        reader = csv.DictReader(fi, lineterminator = '\n')
        first = True
        imported = []
        for row in reader:
            # support former field name 'haplotyping_locus' -> 'haplotyping_gene'
            if 'haplotyping_locus' in row and 'haplotyping_gene' not in row:
                row['haplotyping_gene'] = row['haplotyping_locus']
                del(row['haplotyping_locus'])
            rec = Genotype()
            if first:
                unsupported = []
                for field in reader.fieldnames:
                    if field != 'haplotyping_locus':
                        if not hasattr(rec, field):
                            unsupported.append(field)
                        else:
                            imported.append(field)
                if len(unsupported) > 0:
                    flash("Unrecognised field(s) '%s' have not been imported" % ','.join(unsupported))

                if desc.sequence_type in ['V', 'J']:
                    chain = desc.sequence_type + ('L' if desc.locus in light_loci else 'H')
                elif desc.sequence_type == 'D':
                    chain = 'D'
                else:
                    chain = desc.sequence_type

                missing = []
                if chain in reqd_gen_fields:
                    for field in reqd_gen_fields[chain]:
                        if field not in reader.fieldnames:
                            missing.append(field)

                    if len(missing) > 0:
                        raise ValidationError('Required column(s) %s are missing' % ', '.join(missing))

                first = False

            has_data = False
            for field in imported:
                if field in row and row[field] is not None:
                    f = row[field].strip()
                    if len(f) > 0:
                        setattr(rec, field, row[field])
                        has_data = True

            if has_data:
                rec.description_id = desc.id

                # For the time being, we'll gap V records that don't have a gapped sequence provided.
                # We can phase this out after a few months, once we're confident that everyone is using an ogrdbstats script which provides gapped sequences

                if desc.sequence_type == 'V' and not rec.nt_sequence_gapped:
                    if rec.sequence_id in refs[desc.submission.species]:
                        rec.nt_sequence_gapped = gap_sequence(rec.nt_sequence, refs[desc.submission.species][rec.sequence_id].upper())
                    else:
                        rec.nt_sequence_gapped = gap_sequence(rec.nt_sequence, refs[desc.submission.species][rec.closest_reference].upper())

                db.session.add(rec)
                db.session.commit()

            line += 1

    except Exception as e:
        db.session.rollback()

        if type(e) is OperationalError:
            msg = e.orig.args[1]
            p = msg.find('at row')
            if p > 0:
                msg = msg[:p]
        else:
            msg = e.args[0]

        flash('Import error at line %d:  %s' % (line, msg), 'error')
        raise ValidationError(e.args[0])



