# ORM definitions for Submission

from app import db

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


from flask_table import Table, Col

class Submission_table(Table):
    id = Col("id", show=False)
    submission_id = Col("submission_id")
    submission_date = Col("submission_date")
    submission_status = Col("submission_status")
    submitter_name = Col("submitter_name")
    species = Col("species")
