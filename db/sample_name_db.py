
# ORM definitions for SampleName
# This file is automatically generated from the schema by schema/build_from_schema.py

from head import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol
from sqlalchemy.orm import backref

class SampleName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sam_accession_no = db.Column(db.String(1000))
    sam_record_title = db.Column(db.String(1000))
    sam_url = db.Column(db.String(1000))
    genotype_description_id = db.Column(db.Integer, db.ForeignKey('genotype_description.id'))
    genotype_description = db.relationship('GenotypeDescription', backref = 'sample_names')


def save_SampleName(db, object, form, new=False):   
    object.sam_accession_no = form.sam_accession_no.data
    object.sam_record_title = form.sam_record_title.data
    object.sam_url = form.sam_url.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_SampleName(db, object, form):   
    form.sam_accession_no.data = object.sam_accession_no
    form.sam_record_title.data = object.sam_record_title
    form.sam_url.data = object.sam_url




def copy_SampleName(c_from, c_to):   
    c_to.sam_accession_no = c_from.sam_accession_no
    c_to.sam_record_title = c_from.sam_record_title
    c_to.sam_url = c_from.sam_url



class SampleName_table(StyledTable):
    id = Col("id", show=False)
    sam_accession_no = StyledCol("Accession Number", tooltip="Accession number of the record set within the repository (eg SAMN06821283)")
    sam_record_title = StyledCol("Record Title", tooltip="Title of sequence record in the repository")


def make_SampleName_table(results, private = False, classes=()):
    t = create_table(base=SampleName_table)
    ret = t(results, classes=classes)
    return ret

class SampleName_view(Table):
    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_SampleName_view(sub, private = False):
    ret = SampleName_view([])
    ret.items.append({"item": "Accession Number", "value": sub.sam_accession_no, "tooltip": "Accession number of the record set within the repository (eg SAMN06821283)", "field": "sam_accession_no"})
    ret.items.append({"item": "Record Title", "value": sub.sam_record_title, "tooltip": "Title of sequence record in the repository", "field": "sam_record_title"})
    ret.items.append({"item": "URL", "value": sub.sam_url, "tooltip": "URL to record in NCBI", "field": "sam_url"})
    return ret

