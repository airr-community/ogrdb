# ORM definitions for PubId

from app import db
from db.userdb import User

class PubId(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pubmed_id = db.Column(db.Integer)
    pub_title = db.Column(db.String(255))
    pub_authors = db.Column(db.String(255))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'pub_ids')


def save_PubId(db, object, form, new=False):   
    object.pubmed_id = form.pubmed_id.data
    object.pub_title = form.pub_title.data
    object.pub_authors = form.pub_authors.data
    object.repertoire_id = form.repertoire_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   


from flask_table import Table, Col, LinkCol


class PubId_table(Table):
    id = Col("id", show=False)
    pubmed_id = Col("pubmed_id")
    pub_title = Col("pub_title")
    pub_authors = Col("pub_authors")


def make_PubId_table(results, private = False, classes=()):
    ret = PubId_table(results, classes=classes)
    return ret

class PubId_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_PubId_view(sub, private = False):
    ret = PubId_view([])
    ret.items.append({"item": "pubmed_id", "value": sub.pubmed_id})
    ret.items.append({"item": "pub_title", "value": sub.pub_title})
    ret.items.append({"item": "pub_authors", "value": sub.pub_authors})
    ret.items.append({"item": "repertoire_id", "value": sub.repertoire_id})
    return ret

# ORM definitions for ForwardPrimer

from app import db
from db.userdb import User

class ForwardPrimer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primer_seq = db.Column(db.String(255))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'forward_primer_set')


def save_ForwardPrimer(db, object, form, new=False):   
    object.primer_seq = form.primer_seq.data
    object.repertoire_id = form.repertoire_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   


from flask_table import Table, Col, LinkCol

class ForwardPrimer_table(Table):
    id = Col("id", show=False)


def make_ForwardPrimer_table(results, private = False, classes=[]):
    ret = ForwardPrimer_table(results, classes=classes)
    return ret

class ForwardPrimer_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_ForwardPrimer_view(sub, private = False):
    ret = ForwardPrimer_view([])
    ret.items.append({"item": "primer_seq", "value": sub.primer_seq})
    ret.items.append({"item": "repertoire_id", "value": sub.repertoire_id})
    return ret

# ORM definitions for ReversePrimer

from app import db
from db.userdb import User

class ReversePrimer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    primer_seq = db.Column(db.String(255))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'reverse_primer_set')


def save_ReversePrimer(db, object, form, new=False):   
    object.primer_seq = form.primer_seq.data
    object.repertoire_id = form.repertoire_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   


from flask_table import Table, Col, LinkCol

class ReversePrimer_table(Table):
    id = Col("id", show=False)


def make_ReversePrimer_table(results, private = False, classes=[]):
    ret = ReversePrimer_table(results, classes=classes)
    return ret

class ReversePrimer_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_ReversePrimer_view(sub, private = False):
    ret = ReversePrimer_view([])
    ret.items.append({"item": "primer_seq", "value": sub.primer_seq})
    ret.items.append({"item": "repertoire_id", "value": sub.repertoire_id})
    return ret

# ORM definitions for Repertoire

from app import db
from db.userdb import User

class Repertoire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repository_name = db.Column(db.String(255))
    repository_id = db.Column(db.String(255))
    dataset_url = db.Column(db.String(255))
    dataset_doi = db.Column(db.String(255))
    miarr_compliant = db.Column(db.Boolean)
    miairr_link = db.Column(db.String(255))
    sequencing_platform = db.Column(db.String(255))
    read_length = db.Column(db.String(255))
    primers_not_overlapping = db.Column(db.Boolean)
    notes = db.Column(db.String(10000))
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'repertoire')


def save_Repertoire(db, object, form, new=False):   
    object.repository_name = form.repository_name.data
    object.repository_id = form.repository_id.data
    object.dataset_url = form.dataset_url.data
    object.dataset_doi = form.dataset_doi.data
    object.miarr_compliant = form.miarr_compliant.data
    object.miairr_link = form.miairr_link.data
    object.sequencing_platform = form.sequencing_platform.data
    object.read_length = form.read_length.data
    object.primers_not_overlapping = form.primers_not_overlapping.data
    object.notes = form.notes.data

    if new:
        db.session.add(object)
        
    db.session.commit()   


from flask_table import Table, Col, LinkCol

class Repertoire_table(Table):
    id = Col("id", show=False)


def make_Repertoire_table(results, private = False, classes=[]):
    ret = Repertoire_table(results, classes=classes)
    return ret

class Repertoire_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_Repertoire_view(sub, private = False):
    ret = Repertoire_view([])
    ret.items.append({"item": "repository_name", "value": sub.repository_name})
    ret.items.append({"item": "repository_id", "value": sub.repository_id})
    ret.items.append({"item": "dataset_url", "value": sub.dataset_url})
    ret.items.append({"item": "dataset_doi", "value": sub.dataset_doi})
    ret.items.append({"item": "miarr_compliant", "value": sub.miarr_compliant})
    ret.items.append({"item": "miairr_link", "value": sub.miairr_link})
    ret.items.append({"item": "sequencing_platform", "value": sub.sequencing_platform})
    ret.items.append({"item": "read_length", "value": sub.read_length})
    ret.items.append({"item": "primers_not_overlapping", "value": sub.primers_not_overlapping})
    ret.items.append({"item": "notes", "value": sub.notes})
    return ret

