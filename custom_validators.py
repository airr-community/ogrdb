# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Custom validators for WTF

from wtforms import ValidationError
from collections import namedtuple

class ValidationResult:
    def __init__(self, valid=True, tag=None, route=None, id=None):
        self.valid = valid
        self.tag = tag
        self.route = route
        self.id = id

class ValidOrcidID(object):
    def __init__(self, message=None):
        if not message:
            message = 'ORCID Id must have the format NNNN-NNNN-NNNN-NNNN.'
        self.message = message

    def __call__(self, form, field):
        try:
            fields = field.data.split('-')

            if len(fields) != 4:
                raise ValidationError(self.message)

            for f in fields:
                if len(f) != 4:
                    raise ValidationError(self.message)
                i = int(f)
        except ValidationError as e:
            raise ValidationError(e)
        except:
            raise ValidationError(self.message)

class ValidNucleotideSequence(object):
    def __init__(self, gapped=False, rna=False, ambiguous=False, message=None, x=False):
        self.permitted = 'ACGU' if rna else 'ACGT'
        self.permitted += 'RYSWKMBDHVN' if ambiguous else ''
        self.permitted += 'X' if x else ''
        self.permitted += '.-' if gapped else ''

        if not message:
            message = 'Sequence may only contain the characters %s (in either upper or lower case)' % self.permitted
        self.message = message

    def __call__(self, form, field):
        try:
            for c in list(field.data):
                if c.upper() not in self.permitted:
                    message = self.message
                    message = message + " ('%s' is not allowed)" % c
                    raise ValidationError(message)
        except ValidationError as e:
            raise ValidationError(e)
        except:
            raise ValidationError(self.message)

class ValidAASequence(object):
    def __init__(self, gapped=False, message=None, x=False):
        self.permitted = 'ACDEFGHIKLMNPQRSTVWY'
        self.permitted += 'X' if x else ''
        self.permitted += '.-' if gapped else ''

        if not message:
            message = 'Sequence may only contain the characters %s (in either upper or lower case)' % self.permitted
        self.message = message

    def __call__(self, form, field):
        try:
            for c in list(field.data.upper()):
                if c not in self.permitted:
                    raise ValidationError(self.message)
        except:
            raise ValidationError(self.message)

# validators.DataRequired and InputRequired stop the validation chain if they fail
# This continues, so that if Optional() has been added to the chain, it takes precedence
# This is needed by EditableTable, which adds Optional to force validation
class NonEmpty(object):
    def __init__(self, message=None):
        if not message:
            message = 'Field cannot be blank.'
        self.message = message

    def __call__(self, form, field):
        if not field.raw_data or not field.raw_data[0]:
            raise ValidationError(self.message)

class NullValidator(object):
    def __call__(self, form, field):
        return