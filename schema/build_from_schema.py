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
    write_inp(schema, 'Submission', 'templates/submissioninp.html')

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
def write_model(schema, section, outfile):
    with open(outfile, 'w') as fo:
        fo.write("# ORM definitions for %s\n\nfrom app import db\n\nclass %s(db.Model):\n    id = db.Column(db.Integer, primary_key=True)\n" % (section, section))
        for sc_item in schema[section]['properties']:
            try:
                if 'ignore' in schema[section]['properties'][sc_item]:
                    continue
                type = schema[section]['properties'][sc_item]['type']
                if isinstance(type, list):   # enum
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
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
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                elif type == 'integer':
                    fo.write("    %s = db.Column(db.Integer)" % sc_item)
                elif type == 'number':
                    fo.write("    %s = db.Column(db.Numeric)" % sc_item)
                elif type == 'dictionary':
                    fo.write("    %s = db.Column(db.String(10000))" % sc_item)
                elif type == 'text':
                    fo.write("    %s = db.Column(db.String(10000))" % sc_item)
                elif type == 'ORCID ID':
                    fo.write("    %s = db.Column(db.String(255))" % sc_item)
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        fo.write("\n\n")

        fo.write(
"""
def save_%s(db, mod, form, new=False):
    obj = %s()
    
""" % (section, section))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item] \
                    or 'hide' in schema[section]['properties'][sc_item]:
                continue

            fo.write("    obj.%s = %s.%s\n" % (sc_item, section, sc_item))

        fo.write(
"""
    if new:
        db.add(obj)
        
    db.commit()   
""")



def write_flaskform(schema, section, outfile):
    with open(outfile, 'w') as fo:
        fo.write("# FlaskForm class definitions for %s\n\nfrom flask_wtf import FlaskForm\nfrom wtforms import StringField, SelectField, DateField, BooleanField, IntegerField, DecimalField\nclass %sForm(FlaskForm):\n" % (section, section))
        for sc_item in schema[section]['properties']:
            try:
                if 'ignore' in schema[section]['properties'][sc_item]:
                    continue
                type = schema[section]['properties'][sc_item]['type']
                if isinstance(type, list):   # enum
                    choices = []
                    for item in type:
                        choices.append((item, item))
                    fo.write("    %s = SelectField('%s', choices=%s)" % (sc_item, sc_item, repr(choices)))
                elif type == 'string':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'date':
                    fo.write("    %s = DateField('%s')" % (sc_item, sc_item))
                elif type == 'email_address':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'phone_number':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif 'species' in type:
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif 'list' in type:
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'url':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'doi':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'boolean':
                    fo.write("    %s = BooleanField('%s')" % (sc_item, sc_item))
                elif 'IUPAC' in type:
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'integer':
                    fo.write("    %s = IntegerField('%s')" % (sc_item, sc_item))
                elif type == 'number':
                    fo.write("    %s = DecimalField('%s')" % (sc_item, sc_item))
                elif type == 'dictionary':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'text':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                elif type == 'ORCID ID':
                    fo.write("    %s = StringField('%s')" % (sc_item, sc_item))
                else:
                    raise (ValueError('Unrecognised type: %s' % type))
                fo.write("\n")
            except Exception as e:
                print("Error in section %s item %s: %s" % (section, sc_item, e))
        fo.write("\n\n")

def write_inp(schema, section, outfile):
    with open(outfile, 'w') as fo:
        fo.write(
"""{%% extends "base.html" %%}
{%% block title %%} %s {%% endblock %%}

{%% block c_body %%}
<div class="pageTitle"> %s </div>
    <div class="row pad">

        <form action="{{ url_for('%s') }}" method="POST" name="form" class="form-horizontal">
            {{ form.hidden_tag() }}
""" % (section, section, section.lower()))

        for sc_item in schema[section]['properties']:
            if 'ignore' in schema[section]['properties'][sc_item]:
                continue

            fo.write(
"""
            <div class="form-group col-sm-10">
                    {{ form.%s.label(class="col-sm-3 control-label") }}
                <div class="col-sm-6">
                    {{ form.%s(class="form-control"%s) }}
                </div>
            </div>
""" % (sc_item, sc_item, ', readonly=true' if 'readonly' in schema[section]['properties'][sc_item] else ''))

        fo.write(
"""
            <div class="form-group row col-sm-10">
                <input type="submit" value="Submit" class="btn btn-primary  col-sm-offset-1">
            </div>
        </form>
    </div>
</div>
{% endblock %}
""")


if __name__=="__main__":
    main(sys.argv)
