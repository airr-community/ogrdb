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


class AdminView(ModelView):
    def is_accessible(self):
#        return current_user.has_role('Admin')
        return True

class UserView(AdminView):
    column_exclude_list = ('password')


admin_obj.add_view(UserView(User, db.session))
admin_obj.add_view(AdminView(Role, db.session))
admin_obj.add_view(AdminView(Committee, db.session))
admin_obj.add_view(AdminView(Submission, db.session))
admin_obj.add_view(AdminView(Repertoire, db.session))
admin_obj.add_view(AdminView(GeneDescription, db.session))
