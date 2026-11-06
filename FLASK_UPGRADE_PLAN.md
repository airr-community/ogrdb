# OGRDB Flask stack upgrade plan

Baseline (before any change): `pytest tests/ -v` in `ogre314` (Python 3.11.9) = 12 passed.
This is a historical baseline; the current project testing environment is `ogre314`.

This plan replaces the earlier upgrade documents, which used outdated version numbers and contained errors.

## Target versions (verified on PyPI)

| Package | Current pin | Target | Notes |
|---|---|---|---|
| Flask / Werkzeug / Jinja2 | env already 3.1.3 / 3.1.9 / 3.1.6 | same | requirements.txt has drifted; just re-pin |
| Flask-Admin | 1.6.1 | 2.2.1 | Breaking: `template_mode` removed; only a Bootstrap 4 theme ships |
| Flask-Security-Too | 5.4.3 | 5.9.2 | Needs libpass (replaces passlib), WTForms >=3.2.1; logout is POST-only by default |
| WTForms / Flask-WTF | 3.1.2 / 1.2.1 | 3.3.2 / 1.3.0 | |
| SQLAlchemy | 2.0.30 | 2.1.6 (trial) | Flask-SQLAlchemy 3.1.1 untested against 2.1; fall back to latest 2.0.x |
| Flask-Migrate / alembic | | 4.1.0 / 1.20.1 | |
| flask-restx / flask-swagger-ui / Flask-Mail | | 1.3.2 / 5.34.0 / 0.10.0 | |
| passlib | 1.7.4 | remove, add libpass>=1.9.3 | |
| bcrypt | | 5.0.0 | Verify existing hashes still verify |

Dependencies with weak or no latest-version support:
- Flask-Table: unmaintained, repo uses a fork. It works on Flask 3.1.3 today.
- Flask-OAuth, oauth2, httplib2, Flask-Moment, Flask-DebugToolbar, speaklater, Flask-Bootstrap, marshmallow, apispec, sphinx*: not imported anywhere. Remove after a grep check.
- Flask-Limiter: only referenced in `schema/schema_to_tabfile.py`. Verify before removing.
- Flask-SQLAlchemy 3.1.1: last released in 2023. SQLAlchemy 2.1 is the risk.

## Compatibility issues in the codebase

1. `head.py:13` `Admin(template_mode='bootstrap3')` must become `Admin(theme=Bootstrap4Theme(...))`. Flask-Admin 2.x has no Bootstrap 5 theme, so admin pages will be Bootstrap 4, while the app itself is Bootstrap 5.3.2.
2. `forms/useradmin.py` has 19 `ModelView(Model, db.session)` calls. Change to `ModelView(Model, db)` (deprecated since 2.1).
3. GET logout links in `templates/base.html:57`, `templates/base_wide.html:54` and `templates/index.html:127`. Either set `SECURITY_LOGOUT_METHODS = ['GET','POST']` in `config.cfg`, or switch to a POST form with CSRF.
4. Flask-Security 5.9: `SECURITY_CSRF_COOKIE` and the 2FA cookie now default to `secure=True` (this may break plain-HTTP dev). Timedelta config values. `ExtendedRegisterForm` and the `templates/security/*` overrides need checking.
5. SQLAlchemy 2.1: unconditional autoflush, `filter_by()` across all FROM entities, loader-option path changes. Check `db.session.query(...)` and `lazy='dynamic'` backrefs. Auto-generated `db/_*.py` files must be fixed via the generator, not by hand.
6. Greps found no `Query.get`, `engine.execute`, `before_first_request` or `json_encoder` usage.

## Stages (Copilot does the work and runs automated checks; you do the manual tests)

Each stage is a separate commit on branch `upgrade/flask-stack`.

**Stage 0: Baseline.** Create the branch and record the 12-test baseline. DONE (12 passed).

**Stage 1: Clean requirements and re-pin core.**
- Verify unused packages by grep, then remove them. Remove Windows-only `wincertstore`.
- Re-pin Flask/Werkzeug/Jinja2/Migrate/alembic/restx/swagger-ui/Mail/WTF to the targets. Keep SQLAlchemy 2.0.x for now.
- Check: fresh env install, app imports, `pytest tests/`.

**Stage 2: Flask-Admin 2.2.1.**
- Switch to `Bootstrap4Theme`, `ModelView(Model, db)`, and check `FLASK_ADMIN_*` config.
- Check: tests, plus a test-client smoke request to `/admin` pages as an Admin user.
- Manual: browse all 19 admin views (list, create, edit, delete).

**Stage 3: WTForms 3.3.2 and Flask-Security-Too 5.9.2.**
- Swap passlib for libpass, bump bcrypt, fix logout, review cookie, token and CSRF config and security templates.
- Check: tests, plus a script that verifies an existing bcrypt hash.
- Manual: login with an existing account, logout, register, confirm email, forgot and reset password, change password.

**Stage 4: SQLAlchemy 2.1.6 trial.**
- Install and run the tests. Review the autoflush and `filter_by` code. Run `flask db migrate` to confirm there is no spurious diff.
- If Flask-SQLAlchemy, Flask-Admin or Flask-Security break, pin the latest 2.0.x and note why.
- Manual: submissions, germline sets, sequences, file uploads, and the API and swagger pages.

**Stage 5: Docs and CI.** Update `README`, `tests/README.md` and CI notes. Optional separate phase: numpy 2, pandas 3, biopython, receptor_utils and MySQL drivers (these need Python >=3.11/3.12).

## Decisions and status

- Target Python: 3.14 (verified: full stack resolves, installs and passes the 12 tests in a fresh `ogre314` env). Production uses mysqlclient 2.3.0. No Bootstrap 5 admin theme is wanted.
- Done on branch `upgrade/flask-stack`: new minimal `requirements.txt` (direct deps only, dev tools in `requirements-dev.txt`), Flask-Admin 2.2.1 (`Bootstrap4Theme`, `ModelView(Model, db)`), Flask-Security-Too 5.9.2 with libpass (old bcrypt hashes verified), `SECURITY_LOGOUT_METHODS = ['GET','POST']`, SQLAlchemy 2.1.6, CI on Python 3.14.
- Remaining: manual tests (admin views, login/logout/register/reset flows, submissions, uploads, API/swagger), then production deploy on Python 3.14.

## Open questions
- Confirm production can run Python 3.14.
