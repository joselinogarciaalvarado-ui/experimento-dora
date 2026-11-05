import os
import tempfile

import pytest

# La base de datos de pruebas vive en una carpeta temporal.
_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "pruebas.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def cliente():
    with TestClient(app) as c:
        yield c
