# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Code to allocate and retried unique sequence identifiers, based on a partial hash of the sequence with checks to avoid clashes

import random
import hashlib
from db.sequence_identifier_db import *
from app import db

DIGITS = 4      # number of digits to include in the hash
PREFIX = 'OGRDB:'    # prefix to use before hash


# return the identifier for a sequence. If it is not found in the database, add a new entry

def sequence_identifier(seq):
    seq = seq.replace('.', '')
    seq = seq.replace('-', '')
    identifier = db.session.query(SequenceIdentifier.sequence_identifier).filter(SequenceIdentifier.sequence == seq).one_or_none()

    if identifier and identifier[0]:
        return identifier[0]

    h = int(hashlib.md5(seq.encode()).hexdigest(), base=16)

    while True:
        hashval = PREFIX + base36encode(h)[:DIGITS]
        identifier = db.session.query(SequenceIdentifier.sequence_identifier).filter(SequenceIdentifier.sequence_identifier == hashval).one_or_none()

        if not identifier or not identifier[0]:
            break

        h += random.randrange(100)

    rec = SequenceIdentifier()
    rec.sequence = seq
    rec.sequence_identifier = hashval
    db.session.add(rec)
    db.session.commit()
    return hashval

def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


