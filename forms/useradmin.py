# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Form definitions for user admin with flask-admin

from flask_security import current_user
from flask_admin.contrib.sqla import ModelView
from app import admin_obj, db
from db.userdb import User, Role
from db.submission_db import Submission
from db.gene_description_db import GeneDescription
from db.misc_db import *
from db.repertoire_db import Repertoire
from db.attached_file_db import AttachedFile
from db.genotype_description_db import GenotypeDescription
from db.inference_tool_db import InferenceTool
from db.inferred_sequence_db import InferredSequence
from db.journal_entry_db import JournalEntry
from db.notes_entry_db import NotesEntry
from db.primer_db import Primer
from db.primer_set_db import PrimerSet
from db.record_set_db import RecordSet
from db.sample_name_db import SampleName




class AdminView(ModelView):
    def is_accessible(self):
        return current_user.has_role('Admin')

class UserView(AdminView):
    column_exclude_list = ('password')


admin_obj.add_view(UserView(User, db.session))
admin_obj.add_view(AdminView(Role, db.session))
admin_obj.add_view(AdminView(Committee, db.session))
admin_obj.add_view(AdminView(Submission, db.session))
admin_obj.add_view(AdminView(Repertoire, db.session))
admin_obj.add_view(AdminView(PrimerSet, db.session))
admin_obj.add_view(AdminView(Primer, db.session))
admin_obj.add_view(AdminView(InferenceTool, db.session))
admin_obj.add_view(AdminView(GenotypeDescription, db.session))
admin_obj.add_view(AdminView(GeneDescription, db.session))
admin_obj.add_view(AdminView(NotesEntry, db.session))
admin_obj.add_view(AdminView(AttachedFile, db.session))
admin_obj.add_view(AdminView(JournalEntry, db.session))
admin_obj.add_view(AdminView(RecordSet, db.session))
admin_obj.add_view(AdminView(SampleName, db.session))
admin_obj.add_view(AdminView(InferredSequence, db.session))
