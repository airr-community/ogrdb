# ORM definitions for Submission

from app import db
from db.userdb import User

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(255))
    submission_date = db.Column(db.Date)
    submission_status = db.Column(db.String(255))
    submitter_name = db.Column(db.String(255))
    submitter_address = db.Column(db.String(255))
    submitter_email = db.Column(db.String(255))
    submitter_phone = db.Column(db.String(255))
    species = db.Column(db.String(255))
    population_ethnicity = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref = 'submissions')
    from db._submissionrights import can_see, can_edit


def save_Submission(db, object, form, new=False):   
    object.submission_id = form.submission_id.data
    object.submission_date = form.submission_date.data
    object.submission_status = form.submission_status.data
    object.submitter_name = form.submitter_name.data
    object.submitter_address = form.submitter_address.data
    object.submitter_email = form.submitter_email.data
    object.submitter_phone = form.submitter_phone.data
    object.species = form.species.data
    object.population_ethnicity = form.population_ethnicity.data

    if new:
        db.session.add(object)
        
    db.session.commit()   


from flask_table import Table, Col, LinkCol

class Submission_table(Table):
    id = Col("id", show=False)
    submission_id = LinkCol("submission_id", "submission", url_kwargs={"id": "submission_id"}, attr_list=["submission_id"])
    submission_date = Col("submission_date")
    submission_status = Col("submission_status")
    submitter_name = Col("submitter_name")
    species = Col("species")


def make_Submission_table(results, private = False, classes=[]):
    ret = Submission_table(results, classes=classes)
    return ret

class Submission_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_Submission_view(sub, private = False):
    ret = Submission_view([])
    ret.items.append({"item": "submission_id", "value": sub.submission_id})
    ret.items.append({"item": "submission_date", "value": sub.submission_date})
    ret.items.append({"item": "submission_status", "value": sub.submission_status})
    ret.items.append({"item": "submitter_name", "value": sub.submitter_name})
    ret.items.append({"item": "submitter_address", "value": sub.submitter_address})
    if private:
        ret.items.append({"item": "submitter_email", "value": sub.submitter_email})
    if private:
        ret.items.append({"item": "submitter_phone", "value": sub.submitter_phone})
    ret.items.append({"item": "species", "value": sub.species})
    ret.items.append({"item": "population_ethnicity", "value": sub.population_ethnicity})
    return ret

