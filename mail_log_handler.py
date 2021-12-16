# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import logging

from flask_mail import Message
from head import app


class FlaskMailLogHandler(logging.Handler):

    def __init__(self, mail, sender, recipients, subject, *args, **kwargs):
        super(FlaskMailLogHandler, self).__init__(*args, **kwargs)
        self.mail = mail
        self.sender = sender
        self.recipients = recipients
        self.subject = subject

    def emit(self, record):
        with app.app_context():
            self.mail.send(
                Message(
                    sender=self.sender,
                    recipients=self.recipients,
                    body=self.format(record),
                    subject=self.subject
                )
            )