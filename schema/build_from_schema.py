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

    schema = yaml.load(open(args.schemafile, 'r'), Loader=yamlordereddictloader.Loader)
    #markup =  yaml.load(open(args.markupfile, 'r'), Loader=yamlordereddictloader.Loader)
    #schema = merge_markup(schema, markup)

    write_model(schema, 'Submission', 'db/submission_db.py')
    write_flaskform(schema, 'Submission', 'forms/submission_form.py')
    write_inp(schema, 'Submission', 'templates/submission_form.html')
    write_model(schema, 'PubId', 'db/repertoire_db.py')
    write_model(schema, 'Acknowledgements', 'db/repertoire_db.py', True)
    write_model(schema, 'Repertoire', 'db/repertoire_db.py', True)
    write_flaskform(schema, 'PubId', 'forms/repertoire_form.py')
    write_flaskform(schema, 'Acknowledgements', 'forms/repertoire_form.py', True)
    # TODO: from AIRR
    write_flaskform(schema, 'Repertoire', 'forms/repertoire_form.py', True)
    write_inp(schema, 'Repertoire', 'templates/repertoire_form.html')

    # TODO: The execution of an InferenceTool is related to DataProcessing
    write_model(schema, 'InferenceTool', 'db/inference_tool_db.py')
    write_flaskform(schema, 'InferenceTool', 'forms/inference_tool_form.py')
    write_inp(schema, 'InferenceTool', 'templates/inference_tool_form.html')

    write_model(schema, 'Genotype', 'db/genotype_db.py')
    write_genotype_tables(schema, 'Genotype', 'db/genotype_tables.py')
    write_model(schema, 'GenotypeDescription', 'db/genotype_description_db.py')
    write_flaskform(schema, 'GenotypeDescription', 'forms/genotype_description_form.py')
    write_inp(schema, 'GenotypeDescription', 'templates/genotype_description_form.html')

    # TODO: from AIRR
    write_model(schema, 'InferredSequence', 'db/inferred_sequence_db.py')
    write_flaskform(schema, 'InferredSequence', 'forms/inferred_sequence_form.py')
    write_inp(schema, 'InferredSequence', 'templates/inferred_sequence_form.html')

    write_model(schema, 'JournalEntry', 'db/journal_entry_db.py')
    write_flaskform(schema, 'JournalEntry', 'forms/journal_entry_form.py')
    write_inp(schema, 'JournalEntry', 'templates/journal_entry_form.html')
    write_model(schema, 'NotesEntry', 'db/notes_entry_db.py')
    write_flaskform(schema, 'NotesEntry', 'forms/notes_entry_form.py')
    write_inp(schema, 'NotesEntry', 'templates/notes_entry_form.html')

    # TODO: from AIRR
    write_model(schema, 'GeneDescription', 'db/gene_description_db.py')
    write_flaskform(schema, 'GeneDescription', 'forms/gene_description_form.py')
    write_inp(schema, 'GeneDescription', 'templates/gene_description_form.html')

    write_model(schema, 'GermlineSet', 'db/germline_set_db.py')
    write_flaskform(schema, 'GermlineSet', 'forms/germline_set_form.py')
    write_inp(schema, 'GermlineSet', 'templates/germline_set_form.html')

    write_model(schema, 'GenomicSupport', 'db/gene_description_db.py', True)
    write_flaskform(schema, 'GenomicSupport', 'forms/genomic_support_form.py')
    write_inp(schema, 'GenomicSupport', 'templates/genomic_support_form.html')
    
    write_model(schema, 'DupeGeneNote', 'db/dupe_gene_note_db.py')
    write_model(schema, 'PrimerSet', 'db/primer_set_db.py')
    write_flaskform(schema, 'PrimerSet', 'forms/primer_set_form.py')
    write_inp(schema, 'PrimerSet', 'templates/primer_set_form.html')
    write_model(schema, 'Primer', 'db/primer_db.py')
    write_flaskform(schema, 'Primer', 'forms/primer_form.py')
    write_inp(schema, 'Primer', 'templates/primer_form.html')
    write_model(schema, 'RecordSet', 'db/record_set_db.py')
    write_model(schema, 'SampleName', 'db/sample_name_db.py')
    write_model(schema, 'AttachedFile', 'db/attached_file_db.py')
    write_flaskform(schema, 'AttachedFile', 'forms/attached_file_form.py')
    write_model(schema, 'NovelVdjbase', 'db/novel_vdjbase_db.py')
    write_flaskform(schema, 'NovelVdjbase', 'forms/novel_vdjbase_form.py')


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

from head import db
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

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False):
                continue
            if 'many-relationship' in v:
                rel = v['many-relationship']
                fo.write("""
                        
%s = db.Table('%s',
    db.Column('%s_id', db.Integer(), db.ForeignKey('%s.id')),
    db.Column('%s_id', db.Integer(), db.ForeignKey('%s.id')))
    
""" % (k+'_'+rel[1], k+'_'+rel[1], k, rel[2], rel[1], rel[3]))

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

        for k, v in schema[section]['properties'].items():
            try:
                if v.get('ignore', False):
                    continue
                p_type = v['type']
                if isinstance(p_type, list):   # enum
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif 'list of' in p_type:
                    if 'relationship' in v:
                        rel = v['relationship']
                        fo.write("\n    %s = db.relationship('%s', backref = '%s')" % (rel[0], rel[1], rel[2]))
                    elif 'self-relationship' in v:
                        rel = v['self-relationship']
                        fo.write("\n    %s = db.relationship('%s', backref = backref('%s', remote_side = [%s]))" % (rel[0], k, rel[1], rel[2]))
                    elif 'many-relationship' in v:
                        rel = v['many-relationship']
                        fo.write("\n    %s = db.relationship('%s', secondary = %s, backref = db.backref('%s', lazy='dynamic'))" % (k, rel[0], k +'_'+ rel[1], rel[1]))
                elif p_type == 'string':
                    fo.write("    %s = db.Column(db.String(1000))" % k)
                elif p_type == 'string_50':
                    fo.write("    %s = db.Column(db.String(50))" % k)
                elif p_type == 'hidden':
                    fo.write("    %s = db.Column(db.String(1000))" % k)
                elif p_type == 'date':
                    fo.write("    %s = db.Column(db.DateTime)" % k)
                elif p_type == 'email_address':
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif p_type == 'phone_number':
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif 'species' in p_type:
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif 'list' in p_type:
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif p_type == 'url':
                    fo.write("    %s = db.Column(db.String(500))" % k)
                elif p_type == 'doi':
                    fo.write("    %s = db.Column(db.String(500))" % k)
                elif p_type == 'boolean':
                    fo.write("    %s = db.Column(db.Boolean)" % k)
                elif 'IUPAC' in p_type:
                    fo.write("    %s = db.Column(db.Text())" % k)
                elif p_type == 'integer':
                    if 'foreign_key' in v:
                        fo.write("    %s = db.Column(db.Integer, db.ForeignKey('%s'))" % (k, v['foreign_key']))
                        if 'relationship' in v:
                            rel = v['relationship']
                            fo.write("\n    %s = db.relationship('%s', backref = '%s')" % (rel[0], rel[1], rel[2]))
                        elif 'self-relationship' in v:
                            rel = v['self-relationship']
                            fo.write("\n    %s = db.relationship('%s', backref = backref('%s', remote_side = [%s]))" % (rel[0], section, rel[1], rel[2]))
                    else:
                        fo.write("    %s = db.Column(db.Integer)" % k)
                elif p_type == 'number':
                    fo.write("    %s = db.Column(db.Numeric(precision=(12,2)))" % k)
                elif p_type == 'dictionary':
                    fo.write("    %s = db.Column(db.String(1000))" % k)
                elif p_type == 'text':
                    fo.write("    %s = db.Column(db.Text())" % k)
                elif p_type == 'file':
                    pass
                elif p_type == 'multifile':
                    pass
                elif p_type == 'ORCID ID':
                    fo.write("    %s = db.Column(db.String(255))" % k)
                elif p_type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = db.Column(db.String(1000))" % k)
                else:
                    raise (ValueError('Unrecognised type: %s' % p_type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, k, e))
        fo.write("\n")

# Save details from form

        fo.write(
"""
def save_%s(db, object, form, new=False):   
""" % (section))

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False) or \
                     v.get('hide', False) or \
                     v['type'] == 'file' or \
                     v['type'] == 'multifile':
                continue

            fo.write("    object.%s = form.%s.data\n" % (k, k))

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

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False) \
                    or v.get('hide', False) \
                    or v['type'] == 'file' \
                    or v['type'] == 'multifile' \
                    or 'relationship' in v:   # relationship selectors are too complex to auto-generate
                continue

            fo.write("    form.%s.data = object.%s\n" % (k, k))

        fo.write(
"""


""")
# Copy to another instance

        fo.write(
"""
def copy_%s(c_from, c_to):   
""" % (section))

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False) \
                    or v.get('nocopy', False) \
                    or 'many-relationship' in v \
                    or 'self-relationship' in v \
                    or v['type'] == 'file' \
                    or v['type'] == 'multifile' \
                    or 'relationship' in v:
                continue

            fo.write("    c_to.%s = c_from.%s\n" % (k, k))

        fo.write(
"""


""")
        # Table class

        fo.write('class %s_table(StyledTable):\n    id = Col("id", show=False)\n' % section)

        for k, v in schema[section]['properties'].items():
            if v.get('tableview', False):
                label = v.get('label', k)
                tooltip = ', tooltip="%s"' % v.get('description', '')
                fo.write('    %s = StyledCol("%s"%s)\n' % (k, label, tooltip))
        fo.write('\n\n')

        # Results view

        fo.write('def make_%s_table(results, private = False, classes=()):\n    t = create_table(base=%s_table)\n    ret = t(results, classes=classes)\n' % (section,section))

        ps = ''
        for k, v in schema[section]['properties'].items():
            if v.get('tableview', False) and v.get('private', False):
                ps += '       ret.%s.show = False\n' % k
        if len(ps) > 0:
            fo.write('    if not private:\n' + ps)
        fo.write('    return ret\n\n')

        # Object view

        fo.write('class %s_view(Table):\n    item = ViewCol("", column_html_attrs={"class": "view-table-row"})\n    value = Col("")\n\n\n' % section)

        fo.write('def make_%s_view(sub, private = False):\n    ret = %s_view([])\n' % (section, section))

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False) or \
                    (v.get('hide', False) and not v.get('inview', False)) or \
                    'foreign_key' in v or \
                    v['type'] == 'file' or \
                    v['type'] == 'multifile' or \
                    v['type'] == 'hidden':
                continue
            if v.get('private', False):
                fo.write('    if private:\n    ')
            tooltip = (', "tooltip": "' + v['description'] + '"') if 'description' in v else ''
            fo.write('    ret.items.append({"item": "%s", "value": sub.%s%s, "field": "%s"})\n' % (v.get('label', k), k, tooltip, k))
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
from wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField, TextAreaField, HiddenField, validators, MultipleFileField
class %sForm(FlaskForm):
""" % (section, section))
        for k, v in schema[section]['properties'].items():
            try:
                if v.get('ignore', False) or v.get('hide', False):
                    continue
                p_type = v['type']
                description = (', description="%s"' % v['description']) if 'description' in v else ''
                label = v.get('label', k)
                nonblank = ''
                if 'nonblank' in v:
                    if v['nonblank']:
                        nonblank = ', NonEmpty()'
                    else:
                        nonblank = ', validators.Optional()'

                if isinstance(p_type, list):   # enum
                    if len(p_type) == 0:
                        fo.write("    %s = SelectField('%s')" % (k, label))
                    else:
                        # yaml processor turns Yes, No into bool
                        if len(p_type) == 2 and p_type[0] == True and p_type[1] == False:
                            p_type = ['Yes', 'No']
                        choices = [(str(item), str(item)) for item in p_type]
                        fo.write("    %s = SelectField('%s', choices=%s%s)" % (k, label, repr(choices), description))
                elif p_type == 'string':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'string_50':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'hidden':
                    fo.write("    %s = HiddenField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'date':
                    fo.write("    %s = DateField('%s'%s)" % (k, label, description))
                elif p_type == 'email_address':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'phone_number':
                    fo.write("    %s = StringField('%s', [validators.Length(max=40)%s]%s)" % (k, label, nonblank, description))
                elif 'species' in p_type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif 'list' in p_type:
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'url':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s, validators.URL()]%s)" % (k, label, nonblank, description))
                elif p_type == 'doi':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'boolean':
                    fo.write("    %s = BooleanField('%s', []%s)" % (k, label, description))
                elif 'IUPAC' in p_type:
                    if 'GAPPED' in p_type:
                        fo.write("    %s = TextAreaField('%s', [ValidNucleotideSequence(ambiguous=False, gapped=True)%s]%s)" % (k, label, nonblank, description))
                    elif 'DOTTED' in p_type:
                        fo.write("    %s = TextAreaField('%s', [ValidNucleotideSequence(ambiguous=False, dot=True)%s]%s)" % (k, label, nonblank, description))
                    else:
                        fo.write("    %s = TextAreaField('%s', [ValidNucleotideSequence(ambiguous=False)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'integer':
                    if 'relationship' in schema[section]['properties'][k]:
                        fo.write("    %s = SelectField('%s', [validators.Optional()], choices=[]%s)" % (k, label, description))
                    else:
                        fo.write("    %s = IntegerField('%s', [%s]%s)" % (k, label, nonblank[2:], description))
                elif p_type == 'number':
                    fo.write("    %s = DecimalField('%s', [%s]%s)" % (k, label, nonblank[2:], description))
                elif p_type == 'dictionary':
                    fo.write("    %s = StringField('%s', [validators.Length(max=255)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'text':
                    fo.write("    %s = TextAreaField('%s', [validators.Length(max=10000)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'ORCID ID':
                    fo.write("    %s = StringField('%s', [validators.Optional(), ValidOrcidID()%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'ambiguous nucleotide sequence':
                    fo.write("    %s = StringField('%s', [ValidNucleotideSequence(ambiguous=True)%s]%s)" % (k, label, nonblank, description))
                elif p_type == 'file':
                    fo.write("    %s = FileField('%s'%s)" % (k, label, description))
                elif p_type == 'multifile':
                    fo.write("    %s = MultipleFileField('%s'%s)" % (k, label, description))
                else:
                    raise (ValueError('Unrecognised type: %s' % p_type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, k, e))
        fo.write("\n\n")

def write_inp(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        fo.write("{# This file is automatically generated from the schema by schema/build_from_schema.py #}\n\n")

        for k, v in schema[section]['properties'].items():
            if v.get('ignore', False) or v.get('hide', False):
                continue

            if v.get('readonly', False):
                fo.write(
"""
        {{ render_static_field(form.%s) }}
""" % (k))
            else:
                rows = ', rows="%s"' % v['rows'] if 'rows' in v else ''
                css_class = 'checkbox' if v['type'] == 'boolean' else 'form-control'
                width = v['width'] + '_' if 'width' in v else ''
                fo.write(
"""
        {{ render_%sfield_with_errors(form.%s, class="%s"%s) }}
""" % (width, k, css_class, rows))


# Genotype specific form, which writes the full_table and novel_table using the novel_only and segments attributes in the schema

def write_genotype_tables(schema, section, outfile, append=False):
    attrs = 'a' if append else 'w'
    with open(outfile, attrs) as fo:
        fo.write("""
# ORM definitions for %s
# This file is automatically generated from the schema by schema/build_from_schema.py

from head import db
from db.styled_table import *
from flask_table import Table, Col, LinkCol, create_table
from db.view_table import ViewCol

""" % section)

        # novel_table

        fo.write('class %s_novel_table(StyledTable):\n    id = Col("id", show=False)\n' % section)

        for k, v in schema[section]['properties'].items():
            if v.get('tableview', False) and (v.get('novel_only', False) or k in ['sequence_id', 'sequences']):
                label = v.get('label', k)
                tooltip = ', tooltip="%s"' % v.get('description', '')
                fo.write('    %s = StyledCol("%s"%s)\n' % (k, label, tooltip))
        fo.write('\n\n')

        fo.write('def make_%s_novel_table(results, private = False, classes=()):\n    t=create_table(base=%s_novel_table)\n    return t(results, classes=classes)\n\n\n' % (section,section))

        # full_table

        fo.write('class %s_full_table(StyledTable):\n    id = Col("id", show=False)\n' % section)

        for k, v in schema[section]['properties'].items():
            if v.get('tableview', False) and ((not v.get('novel_only', False)) or k in ['sequence_id', 'sequences']):
                label = v.get('label', k)
                tooltip = ', tooltip="%s"' % v.get('description', '')
                fo.write('    %s = StyledCol("%s"%s)\n' % (k, label, tooltip))
        fo.write('\n\n')

        fo.write('def make_%s_full_table(results, segment, private = False, classes=()):\n    t=create_table(base=%s_full_table)\n' % (section,section))

        for k, v in schema[section]['properties'].items():
            if 'segments' in v and 'tableview' in v:
                els = ['"' + x + '"' for x in v['segments']]
                fo.write('    if segment not in %s:\n' % ('[' + ', '.join(els) + ']'))
                fo.write('        t._cols["%s"].show = False\n' % k)

        fo.write('    return t(results, classes=classes)\n')

        # segment types and required fields

        segments = []
        for k, v in schema[section]['properties'].items():
            if 'segments' in v:
                for seg in v['segments']:
                    if seg not in segments:
                        segments.append(seg)

        fo.write('\n\nreqd_gen_fields = {\n')

        for seg in segments:
            fo.write('    "%s": ' % seg)
            fields = []
            for k, v in schema[section]['properties'].items():
                if v.get('nonblank', False):
                    if ('segments' not in v) or (seg in v['segments']):
                        fields.append('"' + k + '"')
            fo.write('[%s],\n' % ', '.join(fields))
        fo.write('}\n')





if __name__=="__main__":
    main(sys.argv)

