import re
from app import app
import textile

from jinja2 import evalcontextfilter, Markup

@app.template_filter()
@evalcontextfilter
def textile_filter(eval_ctx, value):
    result = textile.textile(value)
    if eval_ctx.autoescape:
        result = Markup(result)
    return result
