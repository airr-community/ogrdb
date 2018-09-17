import logging.handlers
from flask import request
from flask import has_request_context
from flask_mail import email_dispatched
import sys

from mail_log_handler import FlaskMailLogHandler
from mail import log_mail
from security_log_handler import init_security_logging

class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            return super().format(record)
        else:
            record.url = ''
            record.remote_addr = ''
            return super().format(record)


formatter = RequestFormatter(
    '--------------------------------\n'
    '[%(asctime)s] %(levelname)s (%(module)s) :\n'
    '%(remote_addr)s %(url)s\n%(message)s\n'
)

def init_logging(app, mail):
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if app.config['REMOTE_DEBUG']:
        sys.path.append("pycharm-debug-py3k.egg")
        import pydevd
        pydevd.settrace('127.0.0.1', port=30000, stdoutToServer=True, stderrToServer=True)

    if app.config['MAIL_LOG']:
        mail_handler = FlaskMailLogHandler(mail, 'wlees@mail.cryst.bbk.ac.uk', ['william@lees.org.uk'], 'Error from Shrek')
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(formatter)
        root.addHandler(mail_handler)

    handler = logging.handlers.RotatingFileHandler(app.config['LOGPATH'], maxBytes=1024 * 1024)
    handler.setLevel(int(app.config['LOGLEVEL']))
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    email_dispatched.connect(log_mail)
    init_security_logging()

