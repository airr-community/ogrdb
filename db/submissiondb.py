# ORM definitions for Submission

from app import db

class Submission(db.Model):
    __tablename__ = 'Submission'
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



def save_Submission(db, mod, form, new=False):
    obj = Submission()
    
    obj.submission_id = Submission.submission_id
    obj.submission_date = Submission.submission_date
    obj.submission_status = Submission.submission_status
    obj.submitter_name = Submission.submitter_name
    obj.submitter_address = Submission.submitter_address
    obj.submitter_email = Submission.submitter_email
    obj.submitter_phone = Submission.submitter_phone
    obj.species = Submission.species
    obj.population_ethnicity = Submission.population_ethnicity

    if new:
        db.add(obj)
        
    db.commit()   
