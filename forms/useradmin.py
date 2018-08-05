# Form definitions for user admin with flask-admin

from flask_security import current_user
from flask_admin.contrib.sqla import ModelView
from app import admin, db
from db.userdb import User, Role
from db.submissiondb import Submission
from db.miscdb import *


class AdminView(ModelView):
    def is_accessible(self):
#        return current_user.has_role('Admin')
        return True

class UserView(AdminView):
    column_exclude_list = ('password')


admin.add_view(UserView(User, db.session))
admin.add_view(AdminView(Role, db.session))
admin.add_view(AdminView(Submission, db.session))
admin.add_view(AdminView(Committee, db.session))
