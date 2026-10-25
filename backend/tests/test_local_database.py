from pathlib import Path
from unittest.mock import Mock

import pytest

from app import local_database


@pytest.mark.parametrize("existing", [".env", ".tools/dev-postgres"])
def test_init_refuses_existing_configuration_or_data(tmp_path, monkeypatch, existing):
    path = tmp_path / existing
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("keep existing work")
    pg = Mock()
    monkeypatch.setattr(local_database, "pg", pg)
    with pytest.raises(local_database.SetupError, match="Refusing to overwrite"):
        local_database.initialize(tmp_path, Path("unused"), 55432)
    assert path.read_text() == "keep existing work"
    pg.assert_not_called()


def test_secret_file_is_private_and_exclusive(tmp_path):
    path = tmp_path / ".env"
    local_database.private_file(path, "test-only")
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        local_database.private_file(path, "replacement")
    assert path.read_text() == "test-only"
