
# ORM definitions for NovelVdjbase
# This file is automatically generated from the schema by schema/build_from_schema.py

from head import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol
from sqlalchemy.orm import backref

class NovelVdjbase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vdjbase_name = db.Column(db.String(1000))
    species = db.Column(db.String(50))
    locus = db.Column(db.String(255))
    subject_count = db.Column(db.Integer)
    j_haplotypes = db.Column(db.Integer)
    d_haplotypes = db.Column(db.Integer)
    hetero_alleleic_j_haplotypes = db.Column(db.Integer)
    status = db.Column(db.String(255))
    sequence = db.Column(db.String(1000))
    example = db.Column(db.String(50))
    first_seen = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)
    updated_by = db.Column(db.String(50))


def save_NovelVdjbase(db, object, form, new=False):   
    object.vdjbase_name = form.vdjbase_name.data
    object.species = form.species.data
    object.locus = form.locus.data
    object.subject_count = form.subject_count.data
    object.j_haplotypes = form.j_haplotypes.data
    object.d_haplotypes = form.d_haplotypes.data
    object.hetero_alleleic_j_haplotypes = form.hetero_alleleic_j_haplotypes.data
    object.status = form.status.data
    object.sequence = form.sequence.data
    object.example = form.example.data
    object.first_seen = form.first_seen.data
    object.last_seen = form.last_seen.data
    object.last_updated = form.last_updated.data
    object.updated_by = form.updated_by.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_NovelVdjbase(db, object, form):   
    form.vdjbase_name.data = object.vdjbase_name
    form.species.data = object.species
    form.locus.data = object.locus
    form.subject_count.data = object.subject_count
    form.j_haplotypes.data = object.j_haplotypes
    form.d_haplotypes.data = object.d_haplotypes
    form.hetero_alleleic_j_haplotypes.data = object.hetero_alleleic_j_haplotypes
    form.status.data = object.status
    form.sequence.data = object.sequence
    form.example.data = object.example
    form.first_seen.data = object.first_seen
    form.last_seen.data = object.last_seen
    form.last_updated.data = object.last_updated
    form.updated_by.data = object.updated_by




def copy_NovelVdjbase(c_from, c_to):   
    c_to.vdjbase_name = c_from.vdjbase_name
    c_to.species = c_from.species
    c_to.locus = c_from.locus
    c_to.subject_count = c_from.subject_count
    c_to.j_haplotypes = c_from.j_haplotypes
    c_to.d_haplotypes = c_from.d_haplotypes
    c_to.hetero_alleleic_j_haplotypes = c_from.hetero_alleleic_j_haplotypes
    c_to.status = c_from.status
    c_to.sequence = c_from.sequence
    c_to.example = c_from.example
    c_to.first_seen = c_from.first_seen
    c_to.last_seen = c_from.last_seen
    c_to.last_updated = c_from.last_updated
    c_to.updated_by = c_from.updated_by



class NovelVdjbase_table(StyledTable):
    id = Col("id", show=False)
    vdjbase_name = StyledCol("Name", tooltip="Allele name (as recorded in VDJbase)")
    subject_count = StyledCol("Subjects", tooltip="Number of subjects in which this allele is found")
    j_haplotypes = StyledCol("J-haplotypes", tooltip="Number of samples in which this allele is J-haplotyped")
    d_haplotypes = StyledCol("D-haplotypes", tooltip="Number of samples in which this allele is D-haplotyped")
    hetero_alleleic_j_haplotypes = StyledCol("hetero J-haplotypes", tooltip="Number of samples in which this allele and at least one other allele of this gene are haplotyped")
    status = StyledCol("Status", tooltip="Review status")
    sequence = StyledCol("VDJbase sequence", tooltip="Sequence in VDJbase")
    example = StyledCol("Example", tooltip="Example sample in VDJbase displaying this allele")
    last_updated = StyledCol("Last updated", tooltip="Date the comments or status were last updated")
    updated_by = StyledCol("Updated by", tooltip="Name of last updater")


def make_NovelVdjbase_table(results, private = False, classes=()):
    t = create_table(base=NovelVdjbase_table)
    ret = t(results, classes=classes)
    return ret

class NovelVdjbase_view(Table):
    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_NovelVdjbase_view(sub, private = False):
    ret = NovelVdjbase_view([])
    ret.items.append({"item": "Name", "value": sub.vdjbase_name, "tooltip": "Allele name (as recorded in VDJbase)", "field": "vdjbase_name"})
    ret.items.append({"item": "species", "value": sub.species, "tooltip": "Species", "field": "species"})
    ret.items.append({"item": "Locus", "value": sub.locus, "tooltip": "Gene locus", "field": "locus"})
    ret.items.append({"item": "Subjects", "value": sub.subject_count, "tooltip": "Number of subjects in which this allele is found", "field": "subject_count"})
    ret.items.append({"item": "J-haplotypes", "value": sub.j_haplotypes, "tooltip": "Number of samples in which this allele is J-haplotyped", "field": "j_haplotypes"})
    ret.items.append({"item": "D-haplotypes", "value": sub.d_haplotypes, "tooltip": "Number of samples in which this allele is D-haplotyped", "field": "d_haplotypes"})
    ret.items.append({"item": "hetero J-haplotypes", "value": sub.hetero_alleleic_j_haplotypes, "tooltip": "Number of samples in which this allele and at least one other allele of this gene are haplotyped", "field": "hetero_alleleic_j_haplotypes"})
    ret.items.append({"item": "Status", "value": sub.status, "tooltip": "Review status", "field": "status"})
    ret.items.append({"item": "VDJbase sequence", "value": sub.sequence, "tooltip": "Sequence in VDJbase", "field": "sequence"})
    ret.items.append({"item": "Example", "value": sub.example, "tooltip": "Example sample in VDJbase displaying this allele", "field": "example"})
    ret.items.append({"item": "First seen", "value": sub.first_seen, "tooltip": "Date VDJbase record was first seen", "field": "first_seen"})
    ret.items.append({"item": "Last seeen", "value": sub.last_seen, "tooltip": "Date VDJbase record was last seen", "field": "last_seen"})
    ret.items.append({"item": "Last updated", "value": sub.last_updated, "tooltip": "Date the comments or status were last updated", "field": "last_updated"})
    ret.items.append({"item": "Updated by", "value": sub.updated_by, "tooltip": "Name of last updater", "field": "updated_by"})
    return ret

