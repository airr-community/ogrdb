from flask_mail import Message
from app import db
from db.userdb import Role, User
from sqlalchemy import distinct
import time


from flask import current_app, render_template

def log_mail(message, app):
    app.logger.info("Sending Mail: %s" % message.subject)
    app.logger.info("To: %s" % ', '.join(message.recipients))
    if message.cc and len(message.cc) > 0:
        app.logger.info("To: %s" % ', '.join(message.recipients))
    app.logger.info(message.body)
    app.logger.info(message.html)


# send mail - modelled after the same function in flask_security
# recipients list can include role names - which will be expanded to include role owners

def send_mail(subject, recipients, template, **context):
    sender = current_app.config['MAIL_DEFAULT_SENDER']

    # Expand role names into role owners
    rec = []
    role_names = db.session.query(distinct(Role.name)).all()
    role_names = [el[0] for el in role_names]

    for recipient in recipients:
        if recipient in role_names:
            role_owners = db.session.query(User.email).join(User.roles).filter(Role.name == recipient).all()
            if len(role_owners) == 0:
                current_app.logger.info('Empty role: %s' % recipient)
            else:
                role_owners = [el[0] for el in role_owners]
                rec.extend(role_owners)
        else:
            rec.append(recipient)

    if len(rec) == 0:
        current_app.logger.info('No recpients for mail %s' % (subject))
        return

    msg = Message(subject, sender=sender, recipients=rec)
    ctx = ('email', template)
    msg.body = render_template('%s/%s.txt' % ctx, **context)
    msg.html = render_template('%s/%s.html' % ctx, **context)
    mail = current_app.extensions.get('mail')
    mail.send(msg)
    time.sleep(3)