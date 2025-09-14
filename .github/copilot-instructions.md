# OGRDB Copilot Instructions

## Architecture Overview

OGRDB is a Flask-based web application for managing immunoglobulin/antibody germline reference databases. The app uses a modular structure with domain-specific packages under `ogrdb/`:

- **Core modules**: `sequence/`, `submission/`, `germline_set/`, `genotype_stats/`, `vdjbase/`  
- **Global app setup**: `head.py` (Flask app factory), `app.py` (main entry point)
- **Database layer**: `db/` contains SQLAlchemy models and custom table classes
- **Frontend**: Jinja2 templates with Bootstrap 5 + custom OGRDB design system

## Key Patterns & Conventions

### 1. Flask Route Organization
Routes are organized by domain in separate modules (not Blueprints). Import routes in `app.py`:
```python
# Each domain module defines routes using @app.route directly
from ogrdb.sequence.sequence_routes import *
from ogrdb.submission.submission_routes import *
```

### 2. Custom Table System
Uses custom `StyledTable` classes extending `flask_table` with OGRDB-specific styling:
```python
# All tables inherit from StyledTable in db/styled_table.py
class MyTable(StyledTable):
    classes = ['table', 'table_back']  # Applied automatically
    rotate_header = True  # For rotated column headers
```

### 3. Template Hierarchy
Three-tier template system:
- `bootstrap5_base.html` - Core Bootstrap 5 + OGRDB design system
- `base.html` / `base_wide.html` - Standard/wide layouts with navigation
- Domain templates extend these bases

### 4. Form Patterns
Forms follow a consistent pattern with separate form classes and save functions:
```python
# Form definition
class MyForm(FlaskForm):
    field = StringField('Label', [DataRequired()])

# Save function
def save_MyModel(db, object, form, new=False):
    # Populate model from form, handle validation
```

### 5. Database Models
SQLAlchemy models in `db/*_db.py` files. Each has corresponding save/populate functions:
- Models use declarative base from `head.py`
- Save functions handle form-to-model mapping
- Populate functions handle model-to-form mapping

## Design System (Bootstrap 5 + OGRDB)

### CSS Custom Properties
Core design tokens in `templates/bootstrap5_base.html`:
```css
:root {
    --ogrdb-primary: #3279A6;
    --ogrdb-warning: #aa6e25;
    /* Extended color palette, spacing, shadows */
}
```

### Button Standards
- Primary actions: `btn-primary`
- Cancel actions: `btn-warning` (OGRDB convention)
- Secondary actions: `btn-secondary`
- Layout: Use Bootstrap 5 flexbox with `d-flex gap-3`

### Form Layout Pattern
```html
<div class="form-group row">
    <div class="col-sm-10 offset-sm-1">
        <div class="d-flex gap-3 justify-content-start">
            <!-- Buttons here -->
        </div>
    </div>
</div>
```

## Development Workflows

### Running the App
```bash
# Standard Flask development
python app.py
# Or via Flask CLI with specific environment
flask run --debug
```

### Database Operations
Uses Flask-Migrate for schema management:
```bash
flask db migrate -m "Description"
flask db upgrade
```

### Testing
Limited test suite in `tests/`:
- `check-schema.py` - Schema consistency validation
- GitHub Actions workflow validates schema on push

## Security & Authentication

Uses Flask-Security-Too for user management:
- Custom registration form in `forms/security.py` 
- Extended user model with institution/address fields
- Role-based access control (check `current_user.has_role()`)

## File Upload & Attachments

Attachments stored in configured `ATTACHPATH`:
```python
# File handling pattern
attach_path = app.config['ATTACHPATH'] + '/'
# Files linked via AttachedFile model in db/attached_file_db.py
```

## External Integrations

- **IMGT**: Reference germline data import (`imgt/` directory)
- **VDJbase**: External sequence database integration
- **NCBI**: API integration for sequence metadata (requires API key)
- **Email**: Flask-Mail for notifications and confirmations

## Common Gotchas

1. **Template Syntax**: When editing templates, preserve Jinja2 blocks exactly - VS Code linter shows false errors for `{% %}` syntax
2. **Button Classes**: Always use `btn-warning` for cancel buttons (OGRDB convention)
3. **Table Inheritance**: Use `StyledTable` not raw `flask_table.Table`
4. **Route Registration**: Import route modules in `app.py`, don't use Blueprints
5. **Configuration**: Split between `config.cfg` (public) and `secret.cfg` (private)

## Key Files to Reference

- `head.py` - Flask app initialization and global objects
- `db/styled_table.py` - Base table class with OGRDB styling
- `templates/bootstrap5_base.html` - Design system foundation
- `ogrdb/sequence/sequence_routes.py` - Example of route organization
- `DESIGN_SYSTEM.md` - Complete design system documentation

## Cautions

- jinja2 templating is used. Be careful to respect its syntax and preserve blocks. Check the block structure after changes to html files.
- when testing code always use the conda environment ogre311
- some python files are auto generated. If the first few lines of a file indicate that it is automatically generated, do not modify it.

## File Creation Standards
- All python files and other text files must end with a single newline character
- Do not create files with trailing null bytes
- Use simple string concatenation: `content + '\n'` when creating files
- Avoid multiple attempts to add newlines if the first approach does not work. Ask the user to add it manually if needed.
