import pytest
from expense_tracker import database
import csv

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    database.init_db(path)
    return path

@pytest.fixture
def csv_path(tmp_path):
    def _make_csv(filename, rows, header):
        path = tmp_path / filename
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        return path
    return _make_csv
