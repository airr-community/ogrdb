# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# ORM definitions for misclellaneous non schema generated tables

from app import db

class Committee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    committee = db.Column(db.String(80), unique=True)
    species = db.Column(db.String(80), unique=True)
    loci = db.Column(db.String(80))
    sequence_types = db.Column(db.String(80))
