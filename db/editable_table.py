# Editable Table base class

from flask import url_for
from copy import deepcopy
from wtforms import SubmitField, validators, IntegerField
from wtforms.meta import DefaultMeta
from db.styled_table import *

class DelCol(StyledCol):
    def __init__(self, name):
        super().__init__('')
        self.cname = name
    def td_format(self, content):
        return '<button id="%s_del_%s" name="%s_del_%s" type="submit" value="Del" class="btn btn-xs btn-danger"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>'  % (self.cname, content, self.cname, content)

class DelEditCol(StyledCol):
    def __init__(self, name, route):
        super().__init__('')
        self.route = route
        self.cname = name
    def td_format(self, content):
        return  '<a href="%s" class="btn btn-xs btn-warning"><span class="glyphicon glyphicon-pencil"></span>&nbsp;</a>'  % (url_for(self.route, id=content)) +\
                '&nbsp<button id="%s_del_%s" name="%s_del_%s" type="submit" value="Del" class="btn btn-xs btn-danger"><span class="glyphicon glyphicon-trash"></span>&nbsp;</button>'  % (self.cname, content, self.cname, content)

class EditableTable():
    def __init__(self, table, name, form, items, legend='Add', edit_route=None):
        # Additional fields can only be added before the form's process() method is called. The multiple contexts in which we
        # want to use the schema-built forms means that the most practical way to achieve this is by adding them to the class
        # rather than to an instance. This is not without its issues, though, as we need to keep the class 'clean' to use in
        # other contexts.
        self.table = table
        self.name = name
        self.items = items
        self.formclass = form
        self.added_fields = []

        # Add the dynamic controls to the form
        field_name = 'add_%s' % (name)
        setattr(self.formclass, field_name, SubmitField(legend))
        self.added_fields.append(field_name)

        for item in items:
            field_name = '%s_del_%d' % (name, item.id)
            setattr(self.formclass, field_name, SubmitField('Del'))
            self.added_fields.append(field_name)

        self.form = form()

        # Add Optional validators to the instance - using standalone objects so we don't contaminate class validators

        for field in self.form:
            field.validators = deepcopy(field.validators) + [validators.Optional()]

        self.__clean_form__()

        # Subclass the table to provide refs to the delete/edit buttons
        if edit_route:
            table.add_column('id', DelEditCol(name, edit_route))
        else:
            table.add_column('id', DelCol(name))

    def __getattr__(self, attr):
        return getattr(self.table, attr)

    def __clean_form__(self):
        # Clean up form by removing any previously added fields and validators

        for field in self.added_fields:
            delattr(self.formclass, field)
        self.added_fields = []

    def process_deletes(self, db):
        tag = '%s_del_' % self.name
        for field in self.form._fields:
            if tag in field and self.form[field].data:
                for p in self.items:
                    if p.id == int(field.replace(tag, '')):
                        self.items.remove(p)
                        if isinstance(p, db.Model):
                            self.delete_if_unrefd(db, p)
                        return True
        return False

    # Subclass if there can be multiple references to an object
    # - in which case you'll need to decide whether it can be
    # deleted or not.
    def delete_if_unrefd(self, db, obj):
        db.session.delete(obj)

