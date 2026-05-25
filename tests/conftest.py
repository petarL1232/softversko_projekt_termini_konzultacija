import os
from pathlib import Path

# TestClient pokrece FastAPI lifespan, a aplikacija po defaultu u Dockeru koristi
# host "db". Na lokalnom Windows pytestu taj host ne postoji, zato testovi koriste
# privremenu SQLite bazu. Ovo se postavlja prije importa app.main u testovima.
TEST_DB_PATH = Path(__file__).resolve().parent / ".pytest_test.db"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"