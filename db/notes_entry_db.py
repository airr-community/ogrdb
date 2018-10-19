
# ORM definitions for NotesEntry
# This file is automatically generated from the schema by schema/build_from_schema.py

from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol
from sqlalchemy.orm import backref

class NotesEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notes_text = db.Column(db.Text())
    notes_attachment = db.Column(db.LargeBinary(length=(2**32)-1))
    notes_attachment_filename = db.Column(db.String(1000))
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'notes_entries')


def save_NotesEntry(db, object, form, new=False):   
    object.notes_text = form.notes_text.data
    object.notes_attachment_filename = form.notes_attachment_filename.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_NotesEntry(db, object, form):   
    form.notes_text.data = object.notes_text
    form.notes_attachment.data = object.notes_attachment
    form.notes_attachment_filename.data = object.notes_attachment_filename




def copy_NotesEntry(c_from, c_to):   
    c_to.notes_text = c_from.notes_text
    c_to.notes_attachment = c_from.notes_attachment
    c_to.notes_attachment_filename = c_from.notes_attachment_filename



class NotesEntry_table(StyledTable):
    id = Col("id", show=False)


def make_NotesEntry_table(results, private = False, classes=()):
    t=create_table(base=NotesEntry_table)
    ret = t(results, classes=classes)
    return ret

class NotesEntry_view(Table):
    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_NotesEntry_view(sub, private = False):
    ret = NotesEntry_view([])
    ret.items.append({"item": "Notes", "value": sub.notes_text, "tooltip": "Notes from submitter accompanying submission", "field": "notes_text"})
    ret.items.append({"item": "Attachment File Name", "value": sub.notes_attachment_filename, "tooltip": "File attachment name", "field": "notes_attachment_filename"})
    return ret
