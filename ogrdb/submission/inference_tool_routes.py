# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

import sys

from flask import flash, redirect, request, url_for, render_template
from flask_login import current_user, login_required
from markupsafe import Markup

from db.inference_tool_db import InferenceTool, save_InferenceTool, populate_InferenceTool, make_InferenceTool_view
from forms.aggregate_form import AggregateForm
from forms.inference_tool_form import InferenceToolForm
from head import db, app
from ogrdb.submission.cancel_form import CancelForm
from textile_filter import safe_textile


def check_tool_edit(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_edit(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool


@app.route('/edit_tool/<id>', methods=['GET', 'POST'])
@login_required
def edit_tool(id):
    tool = check_tool_edit(id)
    if tool is None:
        return redirect('/')

    form = AggregateForm(InferenceToolForm(), CancelForm())

    if request.method == 'POST':
        if form.cancel.data:
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor= 'tools'))

        if form.validate():
            save_InferenceTool(db, tool, form, new=False)
            return redirect(url_for('edit_submission', id=tool.submission.submission_id, _anchor='tools'))
    else:
        populate_InferenceTool(db, tool, form)

    return render_template('inference_tool_edit.html', form=form, submission_id=tool.submission.submission_id, id=id)


@app.route('/delete_tool/<id>', methods=['POST'])
@login_required
def delete_tool(id):
    tool = check_tool_edit(id)
    if tool is not None:
        tool.delete_dependencies(db)
        db.session.delete(tool)
        db.session.commit()
    return ''


def check_tool_view(id):
    try:
        tool = db.session.query(InferenceTool).filter_by(id = id).one_or_none()
        if tool is None:
            flash('Record not found')
            return None
        elif not tool.submission.can_see(current_user):
            flash('You do not have rights to edit that entry')
            return None
    except Exception as e:
        exc_type, exc_value = sys.exc_info()[:2]
        flash('Error : exception %s with message %s' % (exc_type, exc_value))
        return None

    return tool


@app.route('/inference_tool/<id>', methods=['GET'])
def inference_tool(id):
    tool = check_tool_view(id)
    if tool is None:
        return redirect('/')

    table = make_InferenceTool_view(tool, tool.submission.can_edit(current_user))

    for item in table.items:
        if (item['item'] == 'Starting Database' or item['item'] == 'Settings') and len(item['value']) > 0 :
            item['value'] = Markup(safe_textile(item['value']))

    return render_template('inference_tool_view.html', table=table)