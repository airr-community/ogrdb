# Table to translate binomial species names to common names

from head import db


class SpeciesLookup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    binomial = db.Column(db.String(255))
    common = db.Column(db.String(255))
    ncbi_taxon_id = db.Column(db.Integer)
