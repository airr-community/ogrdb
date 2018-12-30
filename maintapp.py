# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask import Flask

app = Flask(__name__)

@app.before_request
def before_request():
    return "OGRDB is down for maintenance. Please try again in half an hour."