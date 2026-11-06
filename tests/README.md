# Tests

## What CI runs

The **Playwright E2E** workflow (`.github/workflows/playwright.yml`) runs
`pytest tests/ -v` on pushes and pull requests. It starts MySQL 8 as a service,
installs the Python requirements and Chromium, and then runs browser and Flask
test-client checks. On failure, Playwright traces, screenshots, and captured
browser console errors or failed requests are uploaded as the
`playwright-diagnostics` artifact.

The separate **Schema** workflow (`.github/workflows/schema-test.yaml`) runs
`python tests/check-schema.py` to validate the OpenAPI schema.

## Run tests locally

Use the project Conda environment and make sure MySQL is running and accessible:

```bash
conda activate ogre314
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
pytest tests/ -v
```

The end-to-end suite starts its own Flask server on an available port. Set
`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, and `MYSQL_PASSWORD` if your local
MySQL connection differs from the defaults (`127.0.0.1:3306`, `root`/`root`).
To run only the API tests, use `pytest tests/test_api.py -v`; they still require
the test MySQL database. The OpenAPI schema check can be run separately with
`python tests/check-schema.py`.

## Test database and fixtures

At the start of a test run, `tests/conftest.py` creates a uniquely named
`ogrdb_test_*` database and configures the app to use it. After the app imports
the ORM models, `db.create_all()` constructs the test schema from their current
metadata. The `published_records` fixture inserts controlled species, sequence,
and germline-set records for a test and removes them afterward. The test server
then drops the schema, and the fixture drops the database at the end of the run.
No production database or pre-existing application data is used.

When schema changes affect tests, update the source YAML schema and regenerate
the model/forms/templates with `python schema/build_from_schema.py` as described
in `schema/README_schema.txt`; update the test fixture or assertions if the
expected test records or API shape changed. For a deployed application
database, use the normal migration cycle after generation:
`flask db migrate -m "Description"` followed by `flask db upgrade`. To change
test contents, update the `published_records` fixture in `tests/conftest.py`
and the focused assertions that consume it.
