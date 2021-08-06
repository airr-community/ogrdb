# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Items for handling journal entries and mail notification

import datetime
from db.journal_entry_db import *
from db.gene_description_db import GeneDescription
from db.submission_db import Submission
from db.germline_set_db import GermlineSet

from textile_filter import safe_textile

def add_note(user, title, body, obj, db, parent_id=None):
    journal_entry = JournalEntry()
    journal_entry.type = 'note'
    journal_entry.author = user.name
    journal_entry.date = datetime.datetime.now()
    journal_entry.title = title
    journal_entry.body = safe_textile(body)
    if hasattr(obj, 'submission_id'):
        journal_entry.submission = obj
    elif hasattr(obj, 'description_id'):
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
    elif isinstance(obj, GermlineSet):
        journal_entry.germline_set = obj
    db.session.add(journal_entry)
    db.session.commit()
    return journal_entry

