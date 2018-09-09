from flask_wtf import FlaskForm

class AggregateForm(FlaskForm):
    def __init__(self, *args):
        super().__init__()
        self.subforms = []

        for form in args:
            for field in form._fields:
                if field in self._fields and field != 'csrf_token':
                    raise(AttributeError('Field %s is present in multiple child forms.' % field))
            self.subforms.append(form)
            self._fields.update(form._fields)

    def __getattr__(self, attr):
        for form in self.subforms:
            a = getattr(form, attr, None)
            if a is not None: return a
        raise(AttributeError())
