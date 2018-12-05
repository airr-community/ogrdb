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
import sys
from sqlalchemy.exc import OperationalError

def blob_to_genotype(desc, db):
    line = 2
    try:
        fi = StringIO(desc.genotype_file.decode('UTF-8'))
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



