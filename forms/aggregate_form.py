# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from flask_wtf import FlaskForm

class AggregateForm(FlaskForm):
    def __init__(self, *args):
        super().__init__()
        self.subforms = []

        for form in args:
            for field in form._fields:
                if field in self._fields and field != 'csrf_token':
                    raise(AttributeError('Field %s is present in multiple child forms.' % field))
            self.subforms.append(form)
            self._fields.update(form._fields)

    def __getattr__(self, attr):
        if attr == 'subforms':
            raise(AttributeError())
        for form in self.subforms:
            a = getattr(form, attr, None)
            if a is not None: return a
        raise(AttributeError())
