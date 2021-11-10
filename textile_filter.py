# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
#

from app import app
import textile

from jinja2 import pass_eval_context, Markup

@app.template_filter()
@pass_eval_context
def textile_filter(eval_ctx, value):
    result = safe_textile(value)
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

def safe_textile(text, **kwargs):
    if text is None:
        return None

    if len(text) < 1:
        return ''

    return textile.textile(text, **kwargs)
