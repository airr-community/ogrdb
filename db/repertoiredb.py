
# ORM definitions for PubId
from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol

class PubId(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pubmed_id = db.Column(db.String(255))
    pub_title = db.Column(db.String(255))
    pub_authors = db.Column(db.String(255))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'pub_ids')


def save_PubId(db, object, form, new=False):   
    object.pubmed_id = form.pubmed_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_PubId(db, object, form):   
    form.pubmed_id.data = object.pubmed_id



class PubId_table(StyledTable):
    id = Col("id", show=False)
    pubmed_id = StyledCol("pubmed_id")
    pub_title = StyledCol("pub_title")
    pub_authors = StyledCol("pub_authors")


def make_PubId_table(results, private = False, classes=()):
    ret = PubId_table(results, classes=classes)
    return ret

class PubId_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_PubId_view(sub, private = False):
    ret = PubId_view([])
    ret.items.append({"item": "pubmed_id", "value": sub.pubmed_id})
    return ret


class ForwardPrimer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fw_primer_name = db.Column(db.Text())
    fw_primer_seq = db.Column(db.String(1000))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'forward_primer_set')


def save_ForwardPrimer(db, object, form, new=False):   
    object.fw_primer_name = form.fw_primer_name.data
    object.fw_primer_seq = form.fw_primer_seq.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_ForwardPrimer(db, object, form):   
    form.fw_primer_name.data = object.fw_primer_name
    form.fw_primer_seq.data = object.fw_primer_seq



class ForwardPrimer_table(StyledTable):
    id = Col("id", show=False)
    fw_primer_name = StyledCol("fw_primer_name")
    fw_primer_seq = StyledCol("fw_primer_seq")


def make_ForwardPrimer_table(results, private = False, classes=()):
    ret = ForwardPrimer_table(results, classes=classes)
    return ret

class ForwardPrimer_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_ForwardPrimer_view(sub, private = False):
    ret = ForwardPrimer_view([])
    ret.items.append({"item": "fw_primer_name", "value": sub.fw_primer_name})
    ret.items.append({"item": "fw_primer_seq", "value": sub.fw_primer_seq})
    return ret


class ReversePrimer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rv_primer_name = db.Column(db.Text())
    rv_primer_seq = db.Column(db.String(1000))
    repertoire_id = db.Column(db.Integer, db.ForeignKey('repertoire.id'))
    repertoire = db.relationship('Repertoire', backref = 'reverse_primer_set')


def save_ReversePrimer(db, object, form, new=False):   
    object.rv_primer_name = form.rv_primer_name.data
    object.rv_primer_seq = form.rv_primer_seq.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_ReversePrimer(db, object, form):   
    form.rv_primer_name.data = object.rv_primer_name
    form.rv_primer_seq.data = object.rv_primer_seq



class ReversePrimer_table(StyledTable):
    id = Col("id", show=False)
    rv_primer_name = StyledCol("rv_primer_name")
    rv_primer_seq = StyledCol("rv_primer_seq")


def make_ReversePrimer_table(results, private = False, classes=()):
    ret = ReversePrimer_table(results, classes=classes)
    return ret

class ReversePrimer_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_ReversePrimer_view(sub, private = False):
    ret = ReversePrimer_view([])
    ret.items.append({"item": "rv_primer_name", "value": sub.rv_primer_name})
    ret.items.append({"item": "rv_primer_seq", "value": sub.rv_primer_seq})
    return ret


class Acknowledgements(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ack_name = db.Column(db.Text())
    ack_institution_name = db.Column(db.String(255))
    ack_ORCID_id = db.Column(db.String(255))
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'acknowledgements')


def save_Acknowledgements(db, object, form, new=False):   
    object.ack_name = form.ack_name.data
    object.ack_institution_name = form.ack_institution_name.data
    object.ack_ORCID_id = form.ack_ORCID_id.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_Acknowledgements(db, object, form):   
    form.ack_name.data = object.ack_name
    form.ack_institution_name.data = object.ack_institution_name
    form.ack_ORCID_id.data = object.ack_ORCID_id



class Acknowledgements_table(StyledTable):
    id = Col("id", show=False)
    ack_name = StyledCol("ack_name")
    ack_institution_name = StyledCol("ack_institution_name")
    ack_ORCID_id = StyledCol("ack_ORCID_id")


def make_Acknowledgements_table(results, private = False, classes=()):
    ret = Acknowledgements_table(results, classes=classes)
    return ret

class Acknowledgements_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_Acknowledgements_view(sub, private = False):
    ret = Acknowledgements_view([])
    ret.items.append({"item": "ack_name", "value": sub.ack_name})
    ret.items.append({"item": "ack_institution_name", "value": sub.ack_institution_name})
    ret.items.append({"item": "ack_ORCID_id", "value": sub.ack_ORCID_id})
    return ret


class Repertoire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repository_name = db.Column(db.String(255))
    repository_id = db.Column(db.String(255))
    dataset_url = db.Column(db.String(255))
    dataset_doi = db.Column(db.String(255))
    miarr_compliant = db.Column(db.String(255))
    miairr_link = db.Column(db.String(255))
    sequencing_platform = db.Column(db.String(255))
    read_length = db.Column(db.String(255))
    primers_overlapping = db.Column(db.String(255))
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
    object.primers_overlapping = form.primers_overlapping.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_Repertoire(db, object, form):   
    form.repository_name.data = object.repository_name
    form.repository_id.data = object.repository_id
    form.dataset_url.data = object.dataset_url
    form.dataset_doi.data = object.dataset_doi
    form.miarr_compliant.data = object.miarr_compliant
    form.miairr_link.data = object.miairr_link
    form.sequencing_platform.data = object.sequencing_platform
    form.read_length.data = object.read_length
    form.primers_overlapping.data = object.primers_overlapping



class Repertoire_table(StyledTable):
    id = Col("id", show=False)


def make_Repertoire_table(results, private = False, classes=()):
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
    ret.items.append({"item": "primers_overlapping", "value": sub.primers_overlapping})
    return ret

