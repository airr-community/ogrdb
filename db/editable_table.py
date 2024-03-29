# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

# Editable Table base class
# This is used to handle the tables in edit_submission, which can grow, delete items etc

from flask import url_for
from copy import deepcopy
from wtforms import SubmitField, validators, IntegerField
from db.styled_table import *

class ActionCol(StyledCol):
    def __init__(self, name, delete=True, edit_route=None, view_route=None, delete_route=None, delete_message='Are you sure?', download_route=None):
        super().__init__('')
        self.cname = name
        self.delete = delete
        self.edit_route = edit_route
        self.view_route = view_route
        self.delete_route = delete_route
        self.download_route = download_route
        self.delete_message = delete_message

    def td_format(self, content):
        fmt_string = []

        if self.view_route:
            fmt_string.append('<a href="%s" class="btn btn-xs text-info icon_back"><span class="glyphicon glyphicon-sunglasses" data-toggle="tooltip" title="View Detail"></span>&nbsp;</a>'  % (url_for(self.view_route, id=content)))
        if self.edit_route:
            fmt_string.append('<a href="%s" class="btn btn-xs text-warning icon_back"><span class="glyphicon glyphicon-pencil" data-toggle="tooltip" title="Edit"></span>&nbsp;</a>'  % (url_for(self.edit_route, id=content)))
        if self.download_route:
            fmt_string.append('<a href="%s" class="btn btn-xs text-info icon_back"><span class="glyphicon glyphicon-download-alt" data-toggle="tooltip" title="Download"></span>&nbsp;</a>'  % (url_for(self.download_route, id=content)))
        if self.delete_route:
            fmt_string.append('<button onclick="delete_warn(this.id, \'%s\')" type="button" class="btn btn-xs text-danger icon_back" id="%s"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>' % (self.delete_message, url_for(self.delete_route, id=content)))
        elif self.delete:
            fmt_string.append('<button id="%s_del_%s" name="%s_del_%s" type="submit" value="Del" class="btn btn-xs text-danger icon_back"><span class="glyphicon glyphicon-trash" data-toggle="tooltip" title="Delete"></span>&nbsp;</button>'  % (self.cname, content, self.cname, content))

        return '&nbsp'.join(fmt_string)


class EditableTable():
    def __init__(self, table, name, form, items, legend='Add', delete=True, edit_route=None, view_route=None, delete_route=None, download_route=None, delete_message='Are you sure?'):
        # Additional fields can only be added before the form's process() method is called. The multiple contexts in which we
        # want to use the schema-built forms means that the most practical way to achieve this is by adding them to the class
        # rather than to an instance. This is not without its issues, though, as we need to keep the class 'clean' to use in
        # other contexts.
        self.table = table
        self.name = name
        self.items = items
        self.formclass = form
        self.added_fields = []

        self.prep_table()

        # Add the dynamic controls to the form
        field_name = 'add_%s' % (name)
        setattr(self.formclass, field_name, SubmitField(legend))
        self.added_fields.append(field_name)

        for item in items:
            if hasattr(item, 'id'):
                field_name = '%s_del_%d' % (name, item.id)
            else:
                field_name = '%s_del_%d' % (name, item['id'])

            setattr(self.formclass, field_name, SubmitField('Del'))
            self.added_fields.append(field_name)

        self.form = form()

        # Add Optional validators to the instance - using standalone objects so we don't contaminate class validators

        for field in self.form:
            field.validators = list(deepcopy(field.validators))
            field.validators.append(validators.Optional())

        self.__clean_form__()

        # Subclass the table to provide refs to the delete/edit buttons

        if delete or edit_route or view_route or delete_route or download_route:
            table.add_column('id', ActionCol(name, delete=delete, edit_route=edit_route, view_route=view_route, delete_route=delete_route, download_route=download_route, delete_message=delete_message))

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
                        if callable(getattr(p, "delete_dependencies", None)):
                            p.delete_dependencies(db)
                        db.session.delete(p)
                        db.session.commit()
                        return True
        return False

    # Subclass to modify the table, for example to add columns
    def prep_table(self):
        return

