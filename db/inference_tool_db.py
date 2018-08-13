
# ORM definitions for InferenceTool
from app import db
from db.userdb import User
from db.styled_table import *
from flask_table import Table, Col, LinkCol

class InferenceTool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tool_settings_name = db.Column(db.String(255))
    tool_name = db.Column(db.String(255))
    tool_version = db.Column(db.String(255))
    tool_starting_database = db.Column(db.Text())
    tool_settings = db.Column(db.Text())
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'))
    submission = db.relationship('Submission', backref = 'inference_tools')


def save_InferenceTool(db, object, form, new=False):   
    object.tool_settings_name = form.tool_settings_name.data
    object.tool_name = form.tool_name.data
    object.tool_version = form.tool_version.data
    object.tool_starting_database = form.tool_starting_database.data
    object.tool_settings = form.tool_settings.data

    if new:
        db.session.add(object)
        
    db.session.commit()   



def populate_InferenceTool(db, object, form):   
    form.tool_settings_name.data = object.tool_settings_name
    form.tool_name.data = object.tool_name
    form.tool_version.data = object.tool_version
    form.tool_starting_database.data = object.tool_starting_database
    form.tool_settings.data = object.tool_settings



class InferenceTool_table(StyledTable):
    id = Col("id", show=False)
    tool_settings_name = StyledCol("tool_settings_name")
    tool_name = StyledCol("tool_name")


def make_InferenceTool_table(results, private = False, classes=()):
    ret = InferenceTool_table(results, classes=classes)
    return ret

class InferenceTool_view(Table):
    item = Col("", column_html_attrs={"class": "col-sm-3 text-right font-weight-bold view-table-row"})
    value = Col("")


def make_InferenceTool_view(sub, private = False):
    ret = InferenceTool_view([])
    ret.items.append({"item": "tool_settings_name", "value": sub.tool_settings_name})
    ret.items.append({"item": "tool_name", "value": sub.tool_name})
    ret.items.append({"item": "tool_version", "value": sub.tool_version})
    ret.items.append({"item": "tool_starting_database", "value": sub.tool_starting_database})
    ret.items.append({"item": "tool_settings", "value": sub.tool_settings})
    return ret

