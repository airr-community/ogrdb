
# ORM definitions for Genotype
from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol

class Genotype(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.String(255))
    sequences = db.Column(db.Integer)
    closest_reference = db.Column(db.String(255))
    closest_host = db.Column(db.String(255))
    nt_diff = db.Column(db.Integer)
    nt_substitutions = db.Column(db.String(255))
    aa_diff = db.Column(db.Integer)
    aa_substitutions = db.Column(db.String(255))
    unmutated_frequency = db.Column(db.Numeric)
    unmutated_sequences = db.Column(db.Integer)
    unmutated_umis = db.Column(db.Integer)
    allelic_percentage = db.Column(db.Numeric)
    unique_ds = db.Column(db.Integer)
    unique_js = db.Column(db.Integer)
    unique_cdr3s = db.Column(db.Integer)
    haplotyping_locus = db.Column(db.String(255))
    haplotyping_ratio = db.Column(db.String(255))
    nt_sequence = db.Column(db.String(1000))
    description_id = db.Column(db.Integer, db.ForeignKey('genotype_description.id'))
    genotype_description = db.relationship('GenotypeDescription', backref = 'genotypes')


def save_Genotype(db, object, form, new=False):   
    object.sequence_id = form.sequence_id.data
    object.sequences = form.sequences.data
    object.closest_reference = form.closest_reference.data
    object.closest_host = form.closest_host.data
    object.nt_diff = form.nt_diff.data
    object.nt_substitutions = form.nt_substitutions.data
    object.aa_diff = form.aa_diff.data
    object.aa_substitutions = form.aa_substitutions.data
    object.unmutated_frequency = form.unmutated_frequency.data
    object.unmutated_sequences = form.unmutated_sequences.data
    object.unmutated_umis = form.unmutated_umis.data
    object.allelic_percentage = form.allelic_percentage.data
    object.unique_ds = form.unique_ds.data
    object.unique_js = form.unique_js.data
    object.unique_cdr3s = form.unique_cdr3s.data
    object.haplotyping_locus = form.haplotyping_locus.data
    object.haplotyping_ratio = form.haplotyping_ratio.data
    object.nt_sequence = form.nt_sequence.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_Genotype(db, object, form):   
    form.sequence_id.data = object.sequence_id
    form.sequences.data = object.sequences
    form.closest_reference.data = object.closest_reference
    form.closest_host.data = object.closest_host
    form.nt_diff.data = object.nt_diff
    form.nt_substitutions.data = object.nt_substitutions
    form.aa_diff.data = object.aa_diff
    form.aa_substitutions.data = object.aa_substitutions
    form.unmutated_frequency.data = object.unmutated_frequency
    form.unmutated_sequences.data = object.unmutated_sequences
    form.unmutated_umis.data = object.unmutated_umis
    form.allelic_percentage.data = object.allelic_percentage
    form.unique_ds.data = object.unique_ds
    form.unique_js.data = object.unique_js
    form.unique_cdr3s.data = object.unique_cdr3s
    form.haplotyping_locus.data = object.haplotyping_locus
    form.haplotyping_ratio.data = object.haplotyping_ratio
    form.nt_sequence.data = object.nt_sequence



class Genotype_table(StyledTable):
    id = Col("id", show=False)


def make_Genotype_table(results, private = False, classes=()):
    ret = Genotype_table(results, classes=classes)
    return ret

class Genotype_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_Genotype_view(sub, private = False):
    ret = Genotype_view([])
    ret.items.append({"item": "sequence_id", "value": sub.sequence_id})
    ret.items.append({"item": "sequences", "value": sub.sequences})
    ret.items.append({"item": "closest_reference", "value": sub.closest_reference})
    ret.items.append({"item": "closest_host", "value": sub.closest_host})
    ret.items.append({"item": "nt_diff", "value": sub.nt_diff})
    ret.items.append({"item": "nt_substitutions", "value": sub.nt_substitutions})
    ret.items.append({"item": "aa_diff", "value": sub.aa_diff})
    ret.items.append({"item": "aa_substitutions", "value": sub.aa_substitutions})
    ret.items.append({"item": "unmutated_frequency", "value": sub.unmutated_frequency})
    ret.items.append({"item": "unmutated_sequences", "value": sub.unmutated_sequences})
    ret.items.append({"item": "unmutated_umis", "value": sub.unmutated_umis})
    ret.items.append({"item": "allelic_percentage", "value": sub.allelic_percentage})
    ret.items.append({"item": "unique_ds", "value": sub.unique_ds})
    ret.items.append({"item": "unique_js", "value": sub.unique_js})
    ret.items.append({"item": "unique_cdr3s", "value": sub.unique_cdr3s})
    ret.items.append({"item": "haplotyping_locus", "value": sub.haplotyping_locus})
    ret.items.append({"item": "haplotyping_ratio", "value": sub.haplotyping_ratio})
    ret.items.append({"item": "nt_sequence", "value": sub.nt_sequence})
    return ret

