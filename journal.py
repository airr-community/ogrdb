# Items for handling journal entries and mail notification

import datetime
from db.journal_entry_db import *

def add_note(user, title, body, sub, db, parent_id=None):
    journal_entry = JournalEntry()
    journal_entry.type = 'note'
    journal_entry.author = user.name
    journal_entry.date = datetime.datetime.now()
    journal_entry.title = title
    journal_entry.body = body
    journal_entry.submission = sub
    if parent_id:
        journal_entry.parent_id = parent_id
    db.session.add(journal_entry)
    db.session.commit()
    return journal_entry

def add_history(user, title, sub, db):
    journal_entry = JournalEntry()
    journal_entry.type = 'history'
    journal_entry.author = user.name
    journal_entry.date = datetime.datetime.now()
    journal_entry.title = title
    journal_entry.body = title
    journal_entry.submission = sub
    db.session.add(journal_entry)
    db.session.commit()
    return journal_entry
