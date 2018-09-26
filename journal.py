# Items for handling journal entries and mail notification

import datetime
from db.journal_entry_db import *
from db.gene_description_db import GeneDescription
from db.submission_db import Submission

import textile

def add_note(user, title, body, obj, db, parent_id=None):
    journal_entry = JournalEntry()
    journal_entry.type = 'note'
    journal_entry.author = user.name
    journal_entry.date = datetime.datetime.now()
    journal_entry.title = title
    journal_entry.body = textile.textile(body)
    if type(obj) is type(Submission):
        journal_entry.submission = obj
    elif type(obj) is type(GeneDescription):
        journal_entry.gene_description = obj
    if parent_id:
        journal_entry.parent_id = parent_id
    db.session.add(journal_entry)
    db.session.commit()
    return journal_entry

def add_history(user, title, obj, db, body=None):
    journal_entry = JournalEntry()
    journal_entry.type = 'history'
    journal_entry.author = user.name
    journal_entry.date = datetime.datetime.now()
    journal_entry.title = title
    journal_entry.body = body if body else title
    if isinstance(obj, Submission):
        journal_entry.submission = obj
    elif isinstance(obj, GeneDescription):
        journal_entry.gene_description = obj
    db.session.add(journal_entry)
    db.session.commit()
    return journal_entry

