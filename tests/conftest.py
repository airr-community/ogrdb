from contextlib import ExitStack, contextmanager
import importlib
import os
from pathlib import Path
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
            "LOGPATH = 'app.log'",
            "ATTACHPATH = 'attachments'",
            "WORDPRESS_NEWS_URL = 'http://127.0.0.1:9/'",
            "WORDPRESS_REST = ''",
            "VDJBASE_NOVEL_FILE = 'static/docs/vdjbase.json'",
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
        server = make_server("127.0.0.1", 0, application, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
