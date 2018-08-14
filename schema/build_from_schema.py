# Build ORM models, Forms and Templates from the germline schema

import yaml
import yamlordereddictloader
import argparse
import sys

def main(argv):
    parser = argparse.ArgumentParser(description='Build ORM models, Forms and Templates from the germline schema.')
    parser.add_argument('schemafile', help='Schema file (.yaml)')
    parser.add_argument('markupfile', help='Markup file (.yaml)')
    args = parser.parse_args()

    schema =  yaml.load(open(args.schemafile, 'r'), Loader=yamlordereddictloader.Loader)
    markup =  yaml.load(open(args.markupfile, 'r'), Loader=yamlordereddictloader.Loader)

    schema = merge_markup(schema, markup)

    write_model(schema, 'Submission', 'db/submissiondb.py')
    write_flaskform(schema, 'Submission', 'forms/submissionform.py')
    write_inp(schema, 'Submission', 'templates/submission_form.html')
    write_model(schema, 'PubId', 'db/repertoiredb.py')
    write_model(schema, 'ForwardPrimer', 'db/repertoiredb.py', True)
    write_model(schema, 'ReversePrimer', 'db/repertoiredb.py', True)
    write_model(schema, 'Acknowledgements', 'db/repertoiredb.py', True)
    write_model(schema, 'Repertoire', 'db/repertoiredb.py', True)
    write_flaskform(schema, 'PubId', 'forms/repertoireform.py')
    write_flaskform(schema, 'ForwardPrimer', 'forms/repertoireform.py', True)
    write_flaskform(schema, 'ReversePrimer', 'forms/repertoireform.py', True)
    write_flaskform(schema, 'Acknowledgements', 'forms/repertoireform.py', True)
    write_flaskform(schema, 'Repertoire', 'forms/repertoireform.py', True)
    write_inp(schema, 'Repertoire', 'templates/repertoire_form.html')
    write_model(schema, 'InferenceTool', 'db/inference_tool_db.py')
    write_flaskform(schema, 'InferenceTool', 'forms/inference_tool_form.py')
    write_inp(schema, 'InferenceTool', 'templates/inference_tool_form.html')
    write_model(schema, 'Genotype', 'db/genotype_db.py')
    write_model(schema, 'GenotypeDescription', 'db/genotype_description_db.py')
    write_flaskform(schema, 'GenotypeDescription', 'forms/genotype_description_form.py')
    write_inp(schema, 'GenotypeDescription', 'templates/genotype_description_form.html')


# Merge markup properties with schema
# In the event of a conflict, markup always wins. Otherwise properties are merged.
def merge_markup(schema, markup):
    res = schema

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
from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol
""" % section)

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
                elif type == 'string':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'date':
                    fo.write("    %s = db.Column(db.Date)" % sc_item)
                elif type == 'email_address':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'phone_number':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif 'species' in type:
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif 'list' in type:
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'url':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'doi':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'boolean':
                    fo.write("    %s = db.Column(db.Boolean)" % sc_item)
                elif 'IUPAC' in type:
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                elif type == 'integer':
                    if 'foreign_key' in schema[section]['properties'][sc_item]:
                        fo.write("    %s = db.Column(db.Integer, db.ForeignKey('%s'))" % (sc_item, schema[section]['properties'][sc_item]['foreign_key']))
                        if 'relationship' in schema[section]['properties'][sc_item]:
                            rel = schema[section]['properties'][sc_item]['relationship']
                            fo.write("\n    %s = db.relationship('%s', backref = '%s')" % (rel[0], rel[1], rel[2]))
                    else:
                        fo.write("    %s = db.Column(db.Integer)" % sc_item)
                elif type == 'number':
                    fo.write("    %s = db.Column(db.Numeric)" % sc_item)
                elif type == 'dictionary':
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                elif type == 'text':
                    fo.write("    %s = db.Column(db.Text())" % sc_item)
                elif type == 'blob':
                    fo.write("    %s = db.Column(db.LargeBinary())" % sc_item)
                elif type == 'ORCID ID':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = db.Column(db.String(1000))" % sc_item)
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        if section == 'Submission':
            fo.write('    from db._submissionrights import can_see, can_edit\n')
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
        # Table class

        fo.write('class %s_table(StyledTable):\n    id = Col("id", show=False)\n' % section)

        for sc_item in schema[section]['properties']:
            if 'tableview' in schema[section]['properties'][sc_item]:
                # special for submission_id. Will need to generalise for inferences, maybe other things
                if sc_item == 'submission_id':
                    fo.write('    submission_id = StyledLinkCol("submission_id", "submission", url_kwargs={"id": "submission_id"}, attr_list=["submission_id"])\n')
                else:
                    fo.write('    %s = StyledCol("%s")\n' % (sc_item, sc_item))
        fo.write('\n\n')

        # Results view

        fo.write('def make_%s_table(results, private = False, classes=()):\n    ret = %s_table(results, classes=classes)\n' % (section,section))

        ps = ''
        for sc_item in schema[section]['properties']:
            if 'tableview' in schema[section]['properties'][sc_item] and 'private' in schema[section]['properties'][sc_item]:
                ps += '       ret.%s.show = False\n' % sc_item
        if len(ps) > 0:
            fo.write('    if not private:\n' + ps)
        fo.write('    return ret\n\n')

        # Object view

        fo.write('class %s_view(Table):\n    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})\n    value = Col("")\n\n\n' % section)

        fo.write('def make_%s_view(sub, private = False):\n    ret = %s_view([])\n' % (section, section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or 'hide' in schema[section]['properties'][sc_item]:
                continue
            if 'private' in schema[section]['properties'][sc_item]:
                fo.write('    if private:\n    ')
            fo.write('    ret.items.append({"item": "%s", "value": sub.%s})\n' % (sc_item, sc_item))
        fo.write('    return ret\n\n')



def write_flaskform(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        fo.write("""
# FlaskForm class definitions for %s

from flask_wtf import FlaskForm
from customvalidators import *
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, validators
class %sForm(FlaskForm):
""" % (section, section))
        for sc_item in schema[section]['properties']:
            try:
                if 'ignore' in schema[section]['properties'][sc_item] or 'hide' in schema[section]['properties'][sc_item]:
                    continue
                type = schema[section]['properties'][sc_item]['type']

                nonblank = ''
                if 'nonblank' in schema[section]['properties'][sc_item] and schema[section]['properties'][sc_item]['nonblank']:
                   nonblank = ', NonEmpty()'

                if isinstance(type, list):   # enum
                    if len(type) == 0:
                        fo.write("    %s = SelectField('%s')" % (sc_item, sc_item))
                    else:
                        # yamal processor turns Yes, No into bool
                        if len(type) == 2 and type[0] == True and type[1] == False:
                            type = ['Yes', 'No']
                        choices = [(item, item) for item in type]
                        fo.write("    %s = SelectField('%s', choices=%s)" % (sc_item, sc_item, repr(choices)))
                elif type == 'string':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'date':
                    fo.write("    %s = DateField('%s')" % (sc_item, sc_item))
                elif type == 'email_address':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'phone_number':
                    fo.write("    %s = StringField('%s', [validators.Length(max=40)%s])" % (sc_item, sc_item, nonblank))
                elif 'species' in type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif 'list' in type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])=" % (sc_item, sc_item, nonblank))
                elif type == 'url':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'doi':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'boolean':
                    fo.write("    %s = BooleanField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif 'IUPAC' in type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'integer':
                    if 'relationship' in schema[section]['properties'][sc_item]:
                        fo.write("    %s = SelectField('%s', choices=[])" % (sc_item, sc_item))
                    else:
                        fo.write("    %s = IntegerField('%s', [%s])" % (sc_item, sc_item, nonblank[2:]))
                elif type == 'number':
                    fo.write("    %s = DecimalField('%s', [%s])" % (sc_item, sc_item, nonblank[2:]))
                elif type == 'dictionary':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'text':
                    fo.write("    %s = TextAreaField('%s', [validators.Length(max=10000)%s])" % (sc_item, sc_item, nonblank))
                elif type == 'ORCID ID':
                    fo.write("    %s = StringField('%s', [validators.Optional(), ValidOrcidID()%s])" % (sc_item, sc_item, nonblank))
                elif type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = StringField('%s', [ValidNucleotideSequence(ambiguous=True)%s])" % (sc_item, sc_item, nonblank))
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        fo.write("\n\n")

def write_inp(schema, section, outfile):
    with open(outfile, 'w') as fo:
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
                fo.write(
"""
        {{ render_field_with_errors(form.%s, class="form-control"%s) }}
""" % (sc_item, rows))


if __name__=="__main__":
    main(sys.argv)
