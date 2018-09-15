import logging

from flask_mail import Message


class FlaskMailLogHandler(logging.Handler):

    def __init__(self, mail, sender, recipients, subject, *args, **kwargs):
        super(FlaskMailLogHandler, self).__init__(*args, **kwargs)
        self.mail = mail
        self.sender = sender
        self.recipients = recipients
        self.subject = subject

    def emit(self, record):
        self.mail.send(
            Message(
                sender=self.sender,
                recipients=self.recipients,
                body=self.format(record),
                subject=self.subject
            )
        )