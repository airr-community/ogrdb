
# ORM definitions for InferredSequence
# This file is automatically generated from the schema by schema/build_from_schema.py

from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol

class InferredSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('genotype.id'))
    sequence_details = db.relationship('Genotype', backref = 'inferred_sequences')
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'inferred_sequences')
    genotype_id = db.Column(db.Integer, db.ForeignKey('genotype_description.id'))
    genotype_description = db.relationship('GenotypeDescription', backref = 'inferred_sequences')
    seq_accession_no = db.Column(db.String(255))
    deposited_version = db.Column(db.String(255))
    run_ids = db.Column(db.String(255))


def save_InferredSequence(db, object, form, new=False):   
    object.sequence_id = form.sequence_id.data
    object.genotype_id = form.genotype_id.data
    object.seq_accession_no = form.seq_accession_no.data
    object.deposited_version = form.deposited_version.data
    object.run_ids = form.run_ids.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_InferredSequence(db, object, form):   
    form.seq_accession_no.data = object.seq_accession_no
    form.deposited_version.data = object.deposited_version
    form.run_ids.data = object.run_ids



class InferredSequence_table(StyledTable):
    id = Col("id", show=False)


def make_InferredSequence_table(results, private = False, classes=()):
    t=create_table(base=InferredSequence_table)
    ret = t(results, classes=classes)
    return ret

class InferredSequence_view(Table):
    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_InferredSequence_view(sub, private = False):
    ret = InferredSequence_view([])
    ret.items.append({"item": "Accession Number", "value": sub.seq_accession_no, "tooltip": "Accession number of the inferred allele within the repository"})
    ret.items.append({"item": "Version", "value": sub.deposited_version, "tooltip": "Version number of the sequence within the repository"})
    ret.items.append({"item": "Run Accession Numbers", "value": sub.run_ids, "tooltip": "Comma-separated list of accession number(s) of the run(s) listing the raw sequences from which this inference was made"})
    return ret

