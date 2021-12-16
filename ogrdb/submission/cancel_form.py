# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm
from wtforms import SubmitField

class CancelForm(FlaskForm):
    cancel = SubmitField('Cancel')