# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Flask-login and flask-security signal handling

from flask_login import user_logged_in, user_logged_out, user_unauthorized
from flask_security import user_registered, user_confirmed
from mail import send_mail

def init_security_logging():
    user_logged_in.connect(log_user_logged_in)
    user_logged_out.connect(log_user_logged_out)

    user_registered.connect(log_user_registered)
    user_confirmed.connect(log_user_confirmed)

def log_user_logged_in(app, user):
    if hasattr(user, 'email'):      
        app.logger.info('User %s logged in' % user.email)

def log_user_logged_out(app, user):
    if hasattr(user, 'email'):      # Anonymous users can log out during registration/confirmation
        app.logger.info('User %s logged out' % user.email)

def log_user_registered(app, user, **extras):
    app.logger.info('User %s registered' % user.email)
    send_mail('User Registered', ['Admin'], 'user_registered', name=user.email)

def log_user_confirmed(app, user):
    app.logger.info('User %s confirmed registration' % user.email)
    send_mail('User Confirmed', ['Admin'], 'user_confirmed', name=user.email)

