import pytest


@pytest.fixture(autouse=True)
def isolate_default_sqlite_store(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "tripplanner.sqlite3"))
