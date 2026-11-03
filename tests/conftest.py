from contextlib import ExitStack, contextmanager
import datetime
import importlib
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import threading
from urllib.parse import quote_plus
import uuid

import mysql.connector
import pytest
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_database():
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "root")
    database = f"ogrdb_test_{uuid.uuid4().hex}"
    connection_options = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
    }

    connection = mysql.connector.connect(**connection_options)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{database}`")
    finally:
        connection.close()

    uri = (
        f"mysql+mysqlconnector://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )
    try:
        yield uri
    finally:
        connection = mysql.connector.connect(**connection_options)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        finally:
            connection.close()


@contextmanager
def temporary_file(path, content):
    path = ROOT / path
    original = path.read_bytes() if path.exists() else None
    original_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    try:
        yield path
    finally:
        if original is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(original)
            path.chmod(original_mode)


@pytest.fixture(scope="session")
def live_server(test_database):
    temporary_data = Path("temp") / f"playwright-{uuid.uuid4().hex}"
    temporary_data.mkdir(parents=True)
    config = "\n".join(
        (
            f"SQLALCHEMY_DATABASE_URI = {test_database!r}",
            "SECRET_KEY = 'playwright-test-secret'",
            "NCBI_API_KEY = ''",
            "REMOTE_DEBUG = False",
            "MAIL_LOG = False",
            "LOGLEVEL = 20",
            "LOGPATH = 'app.log'",
            "ATTACHPATH = 'attachments'",
            "WORDPRESS_NEWS_URL = 'http://127.0.0.1:9/'",
            "WORDPRESS_REST = ''",
            "VDJBASE_NOVEL_FILE = 'static/docs/vdjbase.json'",
            "SECURITY_PASSWORD_SALT = 'playwright-test-salt'",
        )
    ) + "\n"
    reference_config = "\n".join(
        (
            "species:",
            "  Homo sapiens:",
            "    alias: Homo sapiens",
            f"imgt_ref_pickle: {temporary_data / 'imgt.pickle'}",
            f"ogre_ref_file: {temporary_data / 'missing.fasta'}",
            f"imgt_gapped_ref_pickle: {temporary_data / 'imgt_gapped.pickle'}",
            f"gapped_ogre_ref_file: {temporary_data / 'missing_gapped.fasta'}",
            f"codon_usage_pickle: {temporary_data / 'codon_usage.pickle'}",
            f"update_file_dir: {temporary_data}",
        )
    ) + "\n"

    sys.path.insert(0, str(ROOT))
    with ExitStack() as stack:
        stack.callback(shutil.rmtree, ROOT / temporary_data, ignore_errors=True)
        stack.enter_context(temporary_file("secret.cfg", config))
        stack.enter_context(
            temporary_file("imgt/track_imgt_config.yaml", reference_config)
        )
        stack.enter_context(
            temporary_file(temporary_data / "igpdb.fasta", "")
        )
        os.chdir(ROOT)
        application = importlib.import_module("app").app
        application.config["TESTING"] = True
        from head import db

        with application.app_context(), db.engine.connect() as connection:
            db.create_all()
            connection.exec_driver_sql("SELECT 1")
        server = make_server("127.0.0.1", 0, application, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            with application.app_context():
                db.drop_all()


@pytest.fixture
def test_client(live_server):
    application = importlib.import_module("head").app
    return application.test_client()


@pytest.fixture
def published_records(live_server):
    from db.gene_description_db import GeneDescription
    from db.germline_set_db import GermlineSet
    from db.species_lookup_db import SpeciesLookup
    from head import app, db

    species_name = "Homo sapiens"
    gene_name = "IGHV_TEST01"
    germline_set_name = "test-set"
    with app.app_context():
        species = SpeciesLookup(
            binomial=species_name,
            common="human",
            ncbi_taxon_id=9606,
        )
        gene = GeneDescription(
            sequence_name=gene_name,
            species=species_name,
            locus="IGH",
            sequence_type="V",
            functionality="F",
            affirmation_level="1",
            status="published",
            sequence="ACGTACGT",
            coding_seq_imgt="ACGTACGT",
        )
        germline_set = GermlineSet(
            germline_set_id="GTEST01",
            germline_set_name=germline_set_name,
            species=species_name,
            locus="IGH",
            species_subgroup_type="none",
            status="published",
            release_version=1,
            release_date="2024-01-01",
        )
        germline_set.gene_descriptions.append(gene)
        db.session.add_all((species, gene, germline_set))
        db.session.commit()
        germline_set_id = germline_set.id

    try:
        yield {
            "species": species_name,
            "gene_name": gene_name,
            "germline_set_name": germline_set_name,
            "germline_set_id": germline_set_id,
            "api_germline_set_id": "9606.test-set",
        }
    finally:
        with app.app_context():
            db.session.delete(db.session.get(GermlineSet, germline_set_id))
            db.session.query(GeneDescription).filter_by(
                sequence_name=gene_name, species=species_name
            ).delete()
            db.session.query(SpeciesLookup).filter_by(
                binomial=species_name
            ).delete()
            db.session.commit()


@pytest.fixture
def test_user(live_server):
    """Create a test user for authenticated route testing."""
    from db.userdb import User
    from head import app, db
    from flask_security.utils import hash_password
    from datetime import datetime
    import uuid

    email = "test@example.com"
    password = "TestPassword123!"

    with app.app_context():
        hashed_password = hash_password(password)
        
        # Check if user already exists
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if user is None:
            user = User(
                email=email,
                password=hashed_password,
                name="Test User",
                address="Test Address",
                active=True,
                confirmed_at=datetime.utcnow(),
                accepted_terms=True,
                fs_uniquifier=uuid.uuid4().hex,
            )
            db.session.add(user)
            db.session.commit()

    try:
        yield {"email": email, "password": password}
    finally:
        with app.app_context():
            user = db.session.query(User).filter_by(email=email).one_or_none()
            if user:
                db.session.delete(user)
                db.session.commit()


@pytest.fixture
def authenticated_page(page, live_server, test_user):
    """Return a page fixture with authenticated user session."""
    page.goto(f"{live_server}/login")
    page.get_by_label("Email Address").fill(test_user["email"])
    page.get_by_label("Password").fill(test_user["password"])
    page.get_by_role("button", name="Login").click()
    
    # Wait for redirect to submissions page
    page.wait_for_url(f"{live_server}/submissions")
    return page


@pytest.fixture
def browser_diagnostics(page, request):
    diagnostics = []
    page.on(
        "console",
        lambda message: diagnostics.append(f"console error: {message.text}")
        if message.type == "error"
        else None,
    )
    page.on(
        "requestfailed",
        lambda failed_request: diagnostics.append(
            f"request failed: {failed_request.url} ({failed_request.failure})"
        ),
    )

    yield

    if getattr(request.node, "rep_call", None) and request.node.rep_call.failed:
        results_dir = ROOT / "test-results"
        results_dir.mkdir(exist_ok=True)
        filename = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.node.nodeid)
        artifact = results_dir / f"{filename}.log"
        artifact.write_text(
            (
                "\n".join(diagnostics)
                if diagnostics
                else "No console errors or failed requests captured.\n"
            ),
            encoding="utf-8",
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
