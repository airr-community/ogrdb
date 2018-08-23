
# ORM definitions for GenotypeDescription
from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol

class GenotypeDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    genotype_name = db.Column(db.String(255))
    genotype_subject_id = db.Column(db.String(255))
    genotype_biosample_ids = db.Column(db.String(255))
    genotype_filename = db.Column(db.String(255))
    genotype_file = db.Column(db.LargeBinary())
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'genotype_descriptions')
    inference_tool_id = db.Column(db.Integer, db.ForeignKey('inference_tool.id'))
    inference_tool = db.relationship('InferenceTool', backref = 'genotype_descriptions')


def save_GenotypeDescription(db, object, form, new=False):   
    object.genotype_name = form.genotype_name.data
    object.genotype_subject_id = form.genotype_subject_id.data
    object.genotype_biosample_ids = form.genotype_biosample_ids.data
    object.genotype_filename = form.genotype_filename.data
    object.inference_tool_id = form.inference_tool_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_GenotypeDescription(db, object, form):   
    form.genotype_name.data = object.genotype_name
    form.genotype_subject_id.data = object.genotype_subject_id
    form.genotype_biosample_ids.data = object.genotype_biosample_ids
    form.genotype_filename.data = object.genotype_filename
    form.genotype_file.data = object.genotype_file



class GenotypeDescription_table(StyledTable):
    id = Col("id", show=False)
    genotype_name = StyledCol("genotype_name")
    genotype_subject_id = StyledCol("genotype_subject_id")
    genotype_filename = StyledCol("genotype_filename")


def make_GenotypeDescription_table(results, private = False, classes=()):
    ret = GenotypeDescription_table(results, classes=classes)
    return ret

class GenotypeDescription_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_GenotypeDescription_view(sub, private = False):
    ret = GenotypeDescription_view([])
    ret.items.append({"item": "genotype_name", "value": sub.genotype_name})
    ret.items.append({"item": "genotype_subject_id", "value": sub.genotype_subject_id})
    ret.items.append({"item": "genotype_biosample_ids", "value": sub.genotype_biosample_ids})
    ret.items.append({"item": "genotype_filename", "value": sub.genotype_filename})
    ret.items.append({"item": "inference_tool_id", "value": sub.inference_tool_id})
    return ret

