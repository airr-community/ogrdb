import re
from app import app
import textile

from jinja2 import evalcontextfilter, Markup

@app.template_filter()
@evalcontextfilter
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