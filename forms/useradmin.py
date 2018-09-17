# Form definitions for user admin with flask-admin

from flask_security import current_user
from flask_admin.contrib.sqla import ModelView
from app import admin_obj, db
from db.userdb import User, Role
from db.submission_db import Submission
from db.misc_db import *


class AdminView(ModelView):
    def is_accessible(self):
#        return current_user.has_role('Admin')
        return True

class UserView(AdminView):
    column_exclude_list = ('password')


admin_obj.add_view(UserView(User, db.session))
admin_obj.add_view(AdminView(Role, db.session))
admin_obj.add_view(AdminView(Submission, db.session))
admin_obj.add_view(AdminView(Committee, db.session))
