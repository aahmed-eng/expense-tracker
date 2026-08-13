import pytest
from expense_tracker import database
from datetime import date
import calendar
import csv

today = date.today()

def test_parse_month():
    assert database.parse_month(None) == (today.year, today.month), "this should return the current year and month"
    assert database.parse_month("2024-03") == (2024, 3)
    assert database.parse_month("03") == (today.year, 3), "it should default to the current year if a year isn't given"
    with pytest.raises(ValueError, match="Invalid format:"):
        database.parse_month("abc")
    with pytest.raises(ValueError, match="Invalid format: "):
        database.parse_month(f"{today.month}-{today.year}"),
        "the program will think that we are either using an out-of-bounds month or using the wrong format"
    with pytest.raises(ValueError, match="Invalid format: "):
            database.parse_month("-2"), "the program will think the dash separates the year and the month"
    with pytest.raises(ValueError, match="Invalid format: "):
        database.parse_month("0"), "this is outside the range of possible months"
    with pytest.raises(ValueError, match="Invalid format: "):
        database.parse_month("13"), "this is outside the range of possible months"
    with pytest.raises(ValueError, match="month cannot be in the future"):
        database.parse_month(f"{today.year + 1}-{today.month}"), "this is in the future"


def test_add_transaction(db_path):
    assert database.add_transaction("travel", 12, None, db_path) == \
        f"Added transaction: {today.isoformat()} - travel - £12.00", "check that the correct message was outputted"
    database.add_transaction("holiday", 18, "2021-07-25", db_path)
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT date FROM transactions WHERE category = 'travel'").fetchone()[0] == today.isoformat(), \
            "when no date is given, the date should default to today's date"
        assert conn.execute("SELECT date FROM transactions WHERE category = 'holiday'").fetchone()[0] == "2021-07-25", \
            "when a date is given, that data should be stored as the transaction date"
    with pytest.raises(ValueError, match="Transactions must be positive."):
        database.add_transaction("travel", 0, None, db_path), "it should reject non-positive transaction amounts"
    with pytest.raises(ValueError, match="Transactions must be positive."):
        database.add_transaction("travel", -18, None, db_path), "it should reject non-positive transaction amounts"
    with pytest.raises(ValueError, match="Transaction date cannot be in the future."):
        database.add_transaction("holiday", 18, f"{today.year + 1}-07-25", db_path), \
            "it should reject transactions that haven't happened yet"


def test_delete_transaction(db_path):
    database.add_transaction("travel", 12, None, db_path), "creates a transaction to be deleted"
    with pytest.raises(ValueError, match="The ID you provided doesn't exist."):
        assert database.delete_transaction(2, db_path), "there is no transaction with id '2'"
    assert database.delete_transaction(1, db_path) == "Transaction 1 has been deleted from the database.", \
        "this message should be returned when the transaction is deleted from the database"
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT * FROM transactions WHERE category = 'travel'").fetchone() == None, \
            "transaction '1' with category 'travel' should have been deleted"
    database.add_transaction("travel", 12, None, db_path)
    database.add_transaction("holiday", 18, "2021-07-25", db_path)
    assert database.delete_transaction(None, db_path) == "All transactions have been deleted from the database.", \
        "this message should be returned when deleting all transactions from the database"
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT * FROM transactions").fetchone() == None, "the database should now be empty"


def test_get_transactions(db_path):
    assert database.get_transactions(None, db_path) == "No transactions found in the database.", \
        "empty database should return this message when no month is given"
    assert database.get_transactions("2024-01", db_path) == "No transactions found for the specified month.", \
        "empty database should return this message when a month is given"

    database.add_transaction("travel", 50, "2024-01-15", db_path)
    database.add_transaction("food", 12.50, "2024-01-20", db_path)
    database.add_transaction("food", 8, "2024-02-01", db_path)  # outside January

    rows, headers, title_msg = database.get_transactions("2024-01", db_path)
    assert title_msg == "January 2024 Transactions:"
    assert headers == ["rowid", "date", "category", "amount"]
    assert len(rows) == 3, "2 transactions plus the total row"
    assert rows[-1] == ("Total", "", "", "£62.50"), "the total should only include January's transactions"

    rows, headers, title_msg = database.get_transactions(None, db_path)
    assert title_msg == "All Transactions:"
    assert len(rows) == 4, "all 3 transactions plus the total row"
    assert rows[-1] == ("Total", "", "", "£70.50")

def test_get_transactions_month_boundaries(db_path):
    database.add_transaction("travel", 10, "2024-01-01", db_path)  # first day
    database.add_transaction("travel", 20, "2024-01-31", db_path)  # last day
    database.add_transaction("travel", 30, "2023-12-31", db_path)  # day before
    database.add_transaction("travel", 40, "2024-02-01", db_path)  # day after

    rows, headers, title_msg = database.get_transactions("2024-01", db_path)
    assert len(rows) == 3, "only the 2 January transactions plus the total should be included"
    assert rows[-1] == ("Total", "", "", "£30.00")

def test_get_transactions_leap_year(db_path):
    database.add_transaction("travel", 15, "2024-02-29", db_path)  # 2024 is a leap year
    rows, _, _ = database.get_transactions("2024-02", db_path)
    assert len(rows) == 2, "the Feb 29th transaction should be included"
    assert rows[0][1] == "2024-02-29"


def test_get_transactions_by_category(db_path):
    assert database.get_transactions_by_category("travel", db_path) == "No transactions found under category 'travel'.", \
        "empty database should return this message"

    database.add_transaction("travel", 50, "2024-01-15", db_path)
    database.add_transaction("travel", 25, "2024-02-01", db_path)
    database.add_transaction("food", 12, "2024-01-20", db_path)

    rows, headers = database.get_transactions_by_category("travel", db_path)
    assert headers == ["rowid", "date", "category", "amount"]
    assert len(rows) == 3, "2 travel transactions plus the total row"
    assert rows[-1] == ("Total", "", "", "£75.00")
    assert all(row[2] == "travel" for row in rows[:-1]), "only travel transactions should be returned, food should be excluded"


def test_summary_no_transactions(db_path):
    assert database.summary(None, db_path) == "No transactions have been recorded this month.", \
        "this specific message is used when no month is given and there's nothing to summarise"
    assert database.summary("2024-01", db_path) == "No transactions found for the specified month.", \
        "this message is used when an explicit month is given"

def test_summary_groups_by_category(db_path):
    database.add_transaction("travel", 50, "2024-01-15", db_path)
    database.add_transaction("travel", 25, "2024-01-20", db_path)
    database.add_transaction("food", 12, "2024-01-10", db_path)
    database.add_transaction("food", 8, "2024-02-01", db_path)  # outside January

    rows, headers, title_msg = database.summary("2024-01", db_path)
    assert title_msg == "January 2024 Summary:"
    assert headers == ["Category", "Amount"]
    assert len(rows) == 3, "2 categories plus the total row"
    row_dict = dict(rows[:-1])
    assert row_dict["travel"] == "£75.00"
    assert row_dict["food"] == "£12.00"
    assert rows[-1] == ("Total", "£87.00")

def test_summary_defaults_to_current_month(db_path):
    database.add_transaction("travel", 30, today.isoformat(), db_path)
    rows, _, title_msg = database.summary(None, db_path)
    assert title_msg == f"{calendar.month_name[today.month]} {today.year} Summary:"
    assert rows[-1] == ("Total", "£30.00")

def test_summary_future_month_raises(db_path):
    with pytest.raises(ValueError, match="month cannot be in the future"):
        database.summary(f"{today.year + 1}-{today.month:02d}", db_path)


def test_budgets(db_path):
    assert database.budgets(None, None, db_path) == None, "there are no saved budgets"
    with pytest.raises(ValueError, match="Please enter a valid category."):
        assert database.budgets(" ", None, db_path), "this should raise an error since the category isn't valid"
    assert database.budgets("travel", None, db_path) == "No budget has been set for category 'travel'."
    assert database.budgets("travel", 200.327, db_path) == "The budget for category 'travel' has been set to £200.33.", \
        "this message should be returned, with the correctly rounded value"
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT amount FROM budgets WHERE category = 'travel'").fetchone()[0] == 200.33, \
            "the budget should be saved correctly"
    assert database.budgets("travel", None, db_path) == "Budget for category 'travel': £200.33", \
        "it should return the appropriate budget message"
    database.budgets("holiday", 500, db_path)
    result = database.budgets(None, None, db_path)
    assert isinstance(result, tuple)
    assert isinstance(result[0], list)
    assert len(result[0]) == 3, "2 budgets have been saved, and the 3rd is the total"
    assert result[0][2][1] == "£700.33", "checks that the total is correct"
    assert len(result[1]) == 2, "there are 2 headers"
    database.budgets("travel", 300, db_path)
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT amount FROM budgets WHERE category = 'travel'").fetchall()[0][0] == 300, \
            "the new budget should have replaced the old one"


def test_remove_budget(db_path):
    assert database.remove_budget("travel", db_path) == "The budget for the category 'travel' doesn't exist.", \
        "this should be returned when a budget for the category doesn't exist"
    database.budgets("travel", 300, db_path)
    database.budgets("holiday", 500, db_path)
    with database.get_connection(db_path) as conn: # making sure the budget has been added
        assert conn.execute("SELECT amount FROM budgets WHERE category = 'travel'").fetchone()[0] == 300
    assert database.remove_budget("travel", db_path) == \
        "The budget for category 'travel' has been deleted from the database.", \
            "this should be returned when a budget is deleted"
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT * FROM budgets WHERE category = 'travel'").fetchone() == None, \
            "the 'travel' budget should have been deleted"
    database.budgets("travel", 300, db_path) # adding the budget back
    with database.get_connection(db_path) as conn:
        assert len(conn.execute("SELECT * FROM budgets").fetchall()[0]) == 2, \
            "there are now 2 budgets set, 'travel' and 'holiday'"
    assert database.remove_budget(None, db_path) == "All budgets have been deleted from the database.", \
        "this message should be returned when all budgets are deleted"
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT * FROM budgets").fetchone() == None, "all budgets should have been deleted"


def test_export_csv_empty(tmp_path, db_path):
    assert database.export_csv(tmp_path, db_path) == "There is no data to export.", "the database is initially empty"
    assert ((tmp_path/"transactions.csv").exists() is False) and ((tmp_path/"budgets.csv").exists() is False), \
        "neither folder should've been made since there's no data"

def test_export_csv_transactions(tmp_path, db_path):
    database.add_transaction("travel", 55.43, None, db_path)
    assert database.export_csv(tmp_path, db_path) == \
        "There is no budgets data to export.\nTransactions data has been exported successfully."
    assert (tmp_path/"transactions.csv").exists() and ((tmp_path/"budgets.csv").exists() is False), \
        "there shouldn't be a budgets folder since there is no budgets data"
    
    # making sure the data was exported correctly
    with open(tmp_path/"transactions.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            assert ("rowid" not in row) and ("date" in row) and ("category" in row) and ("amount" in row), \
                "the file should have these columns"
            assert row['date'] == today.isoformat() and row['category'] == "travel" and row['amount'] == "55.43"

def test_export_csv_budgets(tmp_path, db_path):
    database.budgets("travel", 300, db_path)
    assert database.export_csv(tmp_path, db_path) == \
        "There is no transactions data to export.\nBudgets data has been exported successfully."
    assert ((tmp_path/"transactions.csv").exists() is False) and (tmp_path/"budgets.csv").exists()

    # making sure the data was exported correctly
    with open(tmp_path/"budgets.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            assert ("rowid" not in row) and ("category" in row) and ("amount" in row), "the file should have these columns"
            assert row['category'] == "travel" and row['amount'] == "300.0"

def test_export_csv_both(tmp_path, db_path):
    database.add_transaction("travel", 50, None, db_path)
    database.budgets("travel", 15, db_path)
    assert database.export_csv(tmp_path, db_path) == "Budgets and transactions data has been exported successfully."
    assert (tmp_path/"transactions.csv").exists() and (tmp_path/"budgets.csv").exists()

    # we already showed that the data would be exported correctly


def test_import_csv(db_path, csv_path):
    # valid transactions import
    path = csv_path("transactions.csv",
                     [("2024-01-15", "travel", "50.00"),
                      ("2024-02-01", "food", "12.50")],
                     ["date", "category", "amount"])
    result = database.import_csv("transactions", path, None, None, None, db_path)
    assert result == {"imported": 2, "failed": 0, "errors": []}, \
        "both valid rows should be imported with no errors"
    with database.get_connection(db_path) as conn:
        rows = conn.execute("SELECT date, category, amount FROM transactions ORDER BY date").fetchall()
        assert rows == [("2024-01-15", "travel", 50.0), ("2024-02-01", "food", 12.5)], \
            "the imported rows should match the csv data"

    # valid budgets import
    path = csv_path("budgets.csv",
                     [("travel", "300"), ("food", "150")],
                     ["category", "amount"])
    result = database.import_csv("budgets", path, None, None, None, db_path)
    assert result == {"imported": 2, "failed": 0, "errors": []}
    with database.get_connection(db_path) as conn:
        rows = conn.execute("SELECT category, amount FROM budgets ORDER BY category").fetchall()
        assert rows == [("food", 150.0), ("travel", 300.0)]

def test_import_csv_missing_column(db_path, csv_path):
    path = csv_path("transactions.csv",
                     [("2024-01-15", "50.00")],
                     ["date", "amount"])  # missing 'category'
    with pytest.raises(KeyError, match="Column 'category' not found"):
        database.import_csv("transactions", path, None, None, None, db_path)

def test_import_csv_blank_category(db_path, csv_path):
    path = csv_path("transactions.csv",
                     [("2024-01-15", " ", "50.00"),
                      ("2024-01-16", "travel", "20.00")],
                     ["date", "category", "amount"])
    result = database.import_csv("transactions", path, None, None, None, db_path)
    assert result["imported"] == 1, "only the valid row should be imported"
    assert result["failed"] == 1
    assert result["errors"] == ["Line 2: The category is invalid."]

def test_import_csv_invalid_amount(db_path, csv_path):
    path = csv_path("transactions.csv",
                     [("2024-01-15", "travel", "not_a_number"),
                      ("2024-01-16", "travel", "20.00")],
                     ["date", "category", "amount"])
    result = database.import_csv("transactions", path, None, None, None, db_path)
    assert result["imported"] == 1
    assert result["failed"] == 1
    assert result["errors"] == ["Line 2: The amount is not a number."]

def test_import_csv_future_date(db_path, csv_path):
    future_date = f"{today.year + 1}-01-15"
    path = csv_path("transactions.csv",
                     [(future_date, "travel", "50.00")],
                     ["date", "category", "amount"])
    result = database.import_csv("transactions", path, None, None, None, db_path)
    assert result["imported"] == 0, "future-dated transactions should not be imported"
    assert result["failed"] == 1
    assert "Transaction date cannot be in the future." in result["errors"][0]

def test_import_csv_custom_column_names(db_path, csv_path):
    path = csv_path("transactions.csv",
                     [("2024-01-15", "travel", "50.00")],
                     ["transaction_date", "type", "value"])
    result = database.import_csv("transactions", path, "transaction_date", "type", "value", db_path)
    assert result == {"imported": 1, "failed": 0, "errors": []}
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT date, category, amount FROM transactions").fetchone() == ("2024-01-15", "travel", 50.0)

def test_import_csv_invalid_table_name(db_path, csv_path):
    path = csv_path("data.csv", [("travel", "300")], ["category", "amount"])
    with pytest.raises(ValueError, match="Invalid table name"):
        database.import_csv("invalid_table", path, None, None, None, db_path)

def test_import_csv_mixed_valid_and_invalid_rows(db_path, csv_path):
    path = csv_path("transactions.csv",
                     [("2024-01-15", "travel", "50.00"),
                      ("2024-01-16", "", "20.00"),
                      ("2024-01-17", "food", "not_a_number"),
                      ("2024-01-18", "food", "15.00")],
                     ["date", "category", "amount"])
    result = database.import_csv("transactions", path, None, None, None, db_path)
    assert result["imported"] == 2
    assert result["failed"] == 2
    assert len(result["errors"]) == 2
    with database.get_connection(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2, \
            "only the two valid rows should have persisted"


def test_export_import_round_trip(db_path, tmp_path):
    # populate the source database
    database.add_transaction("travel", 50.00, "2024-01-15", db_path)
    database.add_transaction("food", 12.50, "2024-02-01", db_path)
    database.budgets("travel", 300, db_path)
    database.budgets("food", 150, db_path)

    export_dir = tmp_path / "export"
    export_dir.mkdir()
    result = database.export_csv(export_dir, db_path)
    assert result == "Budgets and transactions data has been exported successfully."

    # import the exported csvs into a fresh database
    fresh_db_path = tmp_path / "fresh.db"
    database.init_db(fresh_db_path)

    tx_result = database.import_csv("transactions", export_dir / "transactions.csv", None, None, None, fresh_db_path)
    assert tx_result == {"imported": 2, "failed": 0, "errors": []}

    budget_result = database.import_csv("budgets", export_dir / "budgets.csv", None, None, None, fresh_db_path)
    assert budget_result == {"imported": 2, "failed": 0, "errors": []}

    with database.get_connection(db_path) as original_conn, database.get_connection(fresh_db_path) as fresh_conn:
        original_tx = original_conn.execute("SELECT date, category, amount FROM transactions ORDER BY date").fetchall()
        fresh_tx = fresh_conn.execute("SELECT date, category, amount FROM transactions ORDER BY date").fetchall()
        assert original_tx == fresh_tx, "transactions should survive the export/import round trip"

        original_budgets = original_conn.execute("SELECT category, amount FROM budgets ORDER BY category").fetchall()
        fresh_budgets = fresh_conn.execute("SELECT category, amount FROM budgets ORDER BY category").fetchall()
        assert original_budgets == fresh_budgets, "budgets should survive the export/import round trip"
