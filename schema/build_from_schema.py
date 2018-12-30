# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2, 
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Build ORM models, Forms and Templates from the germline schema

import yaml
import yamlordereddictloader
import argparse
import sys
import os.path

def main(argv):
    parser = argparse.ArgumentParser(description='Build ORM models, Forms and Templates from the germline schema.')
    parser.add_argument('schemafile', help='Schema file (.yaml)')
    parser.add_argument('markupfile', help='Markup file (.yaml)')
    args = parser.parse_args()

    schema =  yaml.load(open(args.schemafile, 'r'), Loader=yamlordereddictloader.Loader)
    markup =  yaml.load(open(args.markupfile, 'r'), Loader=yamlordereddictloader.Loader)

    schema = merge_markup(schema, markup)

    write_model(schema, 'Submission', 'db/submission_db.py')
    write_flaskform(schema, 'Submission', 'forms/submission_form.py')
    write_inp(schema, 'Submission', 'templates/submission_form.html')
    write_model(schema, 'PubId', 'db/repertoire_db.py')
    write_model(schema, 'Acknowledgements', 'db/repertoire_db.py', True)
    write_model(schema, 'Repertoire', 'db/repertoire_db.py', True)
    write_flaskform(schema, 'PubId', 'forms/repertoire_form.py')
    write_flaskform(schema, 'Acknowledgements', 'forms/repertoire_form.py', True)
    write_flaskform(schema, 'Repertoire', 'forms/repertoire_form.py', True)
    write_inp(schema, 'Repertoire', 'templates/repertoire_form.html')
    write_model(schema, 'InferenceTool', 'db/inference_tool_db.py')
    write_flaskform(schema, 'InferenceTool', 'forms/inference_tool_form.py')
    write_inp(schema, 'InferenceTool', 'templates/inference_tool_form.html')
    write_model(schema, 'Genotype', 'db/genotype_db.py')
    write_model(schema, 'GenotypeDescription', 'db/genotype_description_db.py')
    write_flaskform(schema, 'GenotypeDescription', 'forms/genotype_description_form.py')
    write_inp(schema, 'GenotypeDescription', 'templates/genotype_description_form.html')
    write_model(schema, 'InferredSequence', 'db/inferred_sequence_db.py')
    write_flaskform(schema, 'InferredSequence', 'forms/inferred_sequence_form.py')
    write_inp(schema, 'InferredSequence', 'templates/inferred_sequence_form.html')
    write_model(schema, 'JournalEntry', 'db/journal_entry_db.py')
    write_flaskform(schema, 'JournalEntry', 'forms/journal_entry_form.py')
    write_inp(schema, 'JournalEntry', 'templates/journal_entry_form.html')
    write_model(schema, 'NotesEntry', 'db/notes_entry_db.py')
    write_flaskform(schema, 'NotesEntry', 'forms/notes_entry_form.py')
    write_inp(schema, 'NotesEntry', 'templates/notes_entry_form.html')
    write_model(schema, 'GeneDescription', 'db/gene_description_db.py')
    write_flaskform(schema, 'GeneDescription', 'forms/gene_description_form.py')
    write_inp(schema, 'GeneDescription', 'templates/gene_description_form.html')
    write_model(schema, 'PrimerSet', 'db/primer_set_db.py')
    write_flaskform(schema, 'PrimerSet', 'forms/primer_set_form.py')
    write_inp(schema, 'PrimerSet', 'templates/primer_set_form.html')
    write_model(schema, 'Primer', 'db/primer_db.py')
    write_flaskform(schema, 'Primer', 'forms/primer_form.py')
    write_inp(schema, 'Primer', 'templates/primer_form.html')

# Merge markup properties with schema
# In the event of a conflict, markup always wins. Otherwise properties are merged.
def merge_markup(schema, markup):
    res = schema

    if markup is not None:
        for section in markup:
            if section in schema:
                for prop in markup[section]['properties']:
                    if markup[section]['properties'][prop] is not None:
                        for att in markup[section]['properties'][prop]:
                            if prop not in schema[section]['properties']:
                                res[section]['properties'][prop] = {}
                            res[section]['properties'][prop][att] = markup[section]['properties'][prop][att]
            else:
                print('Error: section %s not found in schema file.')
                quit()

    return res


# The db model is fairly permissive, in that a number of special types are stored as strings
# these types are checked more stringently during form validation, but we'll keep some more
# flexibility in the db itself
def write_model(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        if attrs == 'w':
            fo.write(
"""
# ORM definitions for %s
# This file is automatically generated from the schema by schema/build_from_schema.py

from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol
from sqlalchemy.orm import backref
""" % section)

# If there is a _ file corresponding to this file, check it for a mixin

        found_mixin = False
        (head, tail) = os.path.split(outfile)
        mixin_file = os.path.join(head, '_' + tail)
        if os.path.exists(mixin_file):
            mixin_name = section + 'Mixin'
            with open(mixin_file, 'r') as fm:
                for line in fm:
                    if mixin_name in line:
                        found_mixin = True
                        break


        # first pass to create any necessary link tables

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item]:
                continue
            type = schema[section]['properties'][sc_item]['type']
            if 'many-relationship' in schema[section]['properties'][sc_item]:
                rel = schema[section]['properties'][sc_item]['many-relationship']
                fo.write("""
                        
%s = db.Table('%s',
    db.Column('%s_id', db.Integer(), db.ForeignKey('%s.id')),
    db.Column('%s_id', db.Integer(), db.ForeignKey('%s.id')))
    
""" % (sc_item+'_'+rel[1], sc_item+'_'+rel[1], sc_item, rel[2], rel[1], rel[3]))

        # second pass for everything else



        if found_mixin:
            fo.write(
"""
from %s import *

class %s(db.Model, %s):
    id = db.Column(db.Integer, primary_key=True)
""" % (mixin_file.replace('.py', '').replace('\\', '.'), section, mixin_name))
        else:
            fo.write(
"""
class %s(db.Model):
    id = db.Column(db.Integer, primary_key=True)
""" % section)

        for sc_item in schema[section]['properties']:
            try:
                if 'ignore' in schema[section]['properties'][sc_item]:
                    continue
                type = schema[section]['properties'][sc_item]['type']
                if isinstance(type, list):   # enum
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif 'list of' in type:
                    if 'relationship' in schema[section]['properties'][sc_item]:
                        rel = schema[section]['properties'][sc_item]['relationship']
                        fo.write("\n    %s = db.relationship('%s', backref = '%s')" % (rel[0], rel[1], rel[2]))
                    elif 'self-relationship' in schema[section]['properties'][sc_item]:
                        rel = schema[section]['properties'][sc_item]['self-relationship']
                        fo.write("\n    %s = db.relationship('%s', backref = backref('%s', remote_side = [%s]))" % (rel[0], sc_item, rel[1], rel[2]))
                    elif 'many-relationship' in schema[section]['properties'][sc_item]:
                        rel = schema[section]['properties'][sc_item]['many-relationship']
                        fo.write("\n    %s = db.relationship('%s', secondary = %s, backref = db.backref('%s', lazy='dynamic'))" % (sc_item, rel[0], sc_item +'_'+ rel[1], rel[1]))
                elif type == 'string':
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                elif type == 'date':
                    fo.write("    %s = db.Column(db.DateTime)" % sc_item)
                elif type == 'email_address':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'phone_number':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif 'species' in type:
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif 'list' in type:
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'url':
                    fo.write("    %s = db.Column(db.String(500))" % sc_item)
                elif type == 'doi':
                    fo.write("    %s = db.Column(db.String(500))" % sc_item)
                elif type == 'boolean':
                    fo.write("    %s = db.Column(db.Boolean)" % sc_item)
                elif 'IUPAC' in type:
                    fo.write("    %s = db.Column(db.Text())" % sc_item)
                elif type == 'integer':
                    if 'foreign_key' in schema[section]['properties'][sc_item]:
                        fo.write("    %s = db.Column(db.Integer, db.ForeignKey('%s'))" % (sc_item, schema[section]['properties'][sc_item]['foreign_key']))
                        if 'relationship' in schema[section]['properties'][sc_item]:
                            rel = schema[section]['properties'][sc_item]['relationship']
                            fo.write("\n    %s = db.relationship('%s', backref = '%s')" % (rel[0], rel[1], rel[2]))
                        elif 'self-relationship' in schema[section]['properties'][sc_item]:
                            rel = schema[section]['properties'][sc_item]['self-relationship']
                            fo.write("\n    %s = db.relationship('%s', backref = backref('%s', remote_side = [%s]))" % (rel[0], section, rel[1], rel[2]))
                    else:
                        fo.write("    %s = db.Column(db.Integer)" % sc_item)
                elif type == 'number':
                    fo.write("    %s = db.Column(db.Numeric(precision=(12,2)))" % sc_item)
                elif type == 'dictionary':
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                elif type == 'text':
                    fo.write("    %s = db.Column(db.Text())" % sc_item)
                elif type == 'blob':
                    fo.write("    %s = db.Column(db.LargeBinary(length=(2**32)-1))" % sc_item)
                elif type == 'ORCID ID':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        fo.write("\n")

# Save details from form

        fo.write(
"""
def save_%s(db, object, form, new=False):   
""" % (section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or 'hide' in schema[section]['properties'][sc_item]:
                continue

            # write blobs by outside this function using read() - should only do this at download time
            if schema[section]['properties'][sc_item]['type'] != 'blob':
                fo.write("    object.%s = form.%s.data\n" % (sc_item, sc_item))

        fo.write(
"""
    if new:
        db.session.add(object)
        
    db.session.commit()   


""")
# Populate details to form

        fo.write(
"""
def populate_%s(db, object, form):   
""" % (section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or 'hide' in schema[section]['properties'][sc_item] \
                    or 'relationship' in schema[section]['properties'][sc_item]:   # relationship selectors are too complex to auto-generate
                continue

            fo.write("    form.%s.data = object.%s\n" % (sc_item, sc_item))

        fo.write(
"""


""")
# Copy to another instance

        fo.write(
"""
def copy_%s(c_from, c_to):   
""" % (section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or 'nocopy' in schema[section]['properties'][sc_item] \
                    or 'many-relationship' in schema[section]['properties'][sc_item] \
                    or 'self-relationship' in schema[section]['properties'][sc_item] \
                    or 'relationship' in schema[section]['properties'][sc_item]:
                continue

            fo.write("    c_to.%s = c_from.%s\n" % (sc_item, sc_item))

        fo.write(
"""


""")
        # Table class

        fo.write('class %s_table(StyledTable):\n    id = Col("id", show=False)\n' % section)

        for sc_item in schema[section]['properties']:
            if 'tableview' in schema[section]['properties'][sc_item]:
                label = schema[section]['properties'][sc_item].get('label', sc_item)
                tooltip = ', tooltip="%s"' % schema[section]['properties'][sc_item].get('description', '')
                fo.write('    %s = StyledCol("%s"%s)\n' % (sc_item, label, tooltip))
        fo.write('\n\n')

        # Results view

        fo.write('def make_%s_table(results, private = False, classes=()):\n    t=create_table(base=%s_table)\n    ret = t(results, classes=classes)\n' % (section,section))

        ps = ''
        for sc_item in schema[section]['properties']:
            if 'tableview' in schema[section]['properties'][sc_item] and 'private' in schema[section]['properties'][sc_item]:
                ps += '       ret.%s.show = False\n' % sc_item
        if len(ps) > 0:
            fo.write('    if not private:\n' + ps)
        fo.write('    return ret\n\n')

        # Object view

        fo.write('class %s_view(Table):\n    item = ViewCol("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})\n    value = Col("")\n\n\n' % section)

        fo.write('def make_%s_view(sub, private = False):\n    ret = %s_view([])\n' % (section, section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or ('hide' in schema[section]['properties'][sc_item] and not 'inview' in schema[section]['properties'][sc_item])\
                    or 'foreign_key' in schema[section]['properties'][sc_item]\
                    or schema[section]['properties'][sc_item]['type'] == 'blob':        # don't put blobs in the view
                continue
            if 'private' in schema[section]['properties'][sc_item]:
                fo.write('    if private:\n    ')
            tooltip = (', "tooltip": "' + schema[section]['properties'][sc_item]['description'] + '"') if 'description' in schema[section]['properties'][sc_item] else ''
            fo.write('    ret.items.append({"item": "%s", "value": sub.%s%s, "field": "%s"})\n' % (schema[section]['properties'][sc_item].get('label', sc_item), sc_item, tooltip, sc_item))
        fo.write('    return ret\n\n')



def write_flaskform(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        fo.write("""
# FlaskForm class definitions for %s
# This file is automatically generated from the schema by schema/build_from_schema.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from custom_validators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class %sForm(FlaskForm):
""" % (section, section))
        for sc_item in schema[section]['properties']:
            try:
                if 'ignore' in schema[section]['properties'][sc_item] or 'hide' in schema[section]['properties'][sc_item]:
                    continue
                type = schema[section]['properties'][sc_item]['type']
                description = (', description="%s"' % schema[section]['properties'][sc_item]['description']) if 'description' in schema[section]['properties'][sc_item] else ''
                label = schema[section]['properties'][sc_item]['label'] if 'label' in schema[section]['properties'][sc_item] else sc_item
                nonblank = ''
                if 'nonblank' in schema[section]['properties'][sc_item]:
                    if schema[section]['properties'][sc_item]['nonblank']:
                        nonblank = ', NonEmpty()'
                    else:
                        nonblank = ', validators.Optional()'

                if isinstance(type, list):   # enum
                    if len(type) == 0:
                        fo.write("    %s = SelectField('%s')" % (sc_item, label))
                    else:
                        # yaml processor turns Yes, No into bool
                        if len(type) == 2 and type[0] == True and type[1] == False:
                            type = ['Yes', 'No']
                        choices = [(str(item), str(item)) for item in type]
                        fo.write("    %s = SelectField('%s', choices=%s%s)" % (sc_item, label, repr(choices), description))
                elif type == 'string':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'date':
                    fo.write("    %s = DateField('%s'%s)" % (sc_item, label, description))
                elif type == 'email_address':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'phone_number':
                    fo.write("    %s = StringField('%s', [validators.Length(max=40)%s]%s)" % (sc_item, label, nonblank, description))
                elif 'species' in type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif 'list' in type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'url':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s, validators.URL()]%s)" % (sc_item, label, nonblank, description))
                elif type == 'doi':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'boolean':
                    fo.write("    %s = BooleanField('%s', []%s)" % (sc_item, label, description))
                elif 'IUPAC' in type:
                    if 'GAPPED' in type:
                        fo.write("    %s = TextAreaField('%s', [ValidNucleotideSequence(ambiguous=False, gapped=True)%s]%s)" % (sc_item, label, nonblank, description))
                    else:
                        fo.write("    %s = TextAreaField('%s', [ValidNucleotideSequence(ambiguous=False)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'integer':
                    if 'relationship' in schema[section]['properties'][sc_item]:
                        fo.write("    %s = SelectField('%s', [validators.Optional()], choices=[]%s)" % (sc_item, label, description))
                    else:
                        fo.write("    %s = IntegerField('%s', [%s]%s)" % (sc_item, label, nonblank[2:], description))
                elif type == 'number':
                    fo.write("    %s = DecimalField('%s', [%s]%s)" % (sc_item, label, nonblank[2:], description))
                elif type == 'dictionary':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'text':
                    fo.write("    %s = TextAreaField('%s', [validators.Length(max=10000)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'ORCID ID':
                    fo.write("    %s = StringField('%s', [validators.Optional(), ValidOrcidID()%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = StringField('%s', [ValidNucleotideSequence(ambiguous=True)%s]%s)" % (sc_item, label, nonblank, description))
                elif type == 'blob':
                    fo.write("    %s = FileField('%s'%s)" % (sc_item, label, description))
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        fo.write("\n\n")

def write_inp(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        fo.write("{# This file is automatically generated from the schema by schema/build_from_schema.py #}\n\n")

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] or 'hide' in schema[section]['properties'][sc_item]:
                continue

            if 'readonly' in schema[section]['properties'][sc_item]:
                fo.write(
"""
        {{ render_static_field(form.%s) }}
""" % (sc_item))
            else:
                rows = ', rows="%s"' % schema[section]['properties'][sc_item]['rows'] if 'rows' in schema[section]['properties'][sc_item] else ''
                css_class = 'checkbox' if schema[section]['properties'][sc_item]['type'] == 'boolean' else 'form-control'
                width = schema[section]['properties'][sc_item]['width'] + '_' if 'width' in schema[section]['properties'][sc_item] else ''
                fo.write(
"""
        {{ render_%sfield_with_errors(form.%s, class="%s"%s) }}
""" % (width, sc_item, css_class, rows))


if __name__=="__main__":
    main(sys.argv)
