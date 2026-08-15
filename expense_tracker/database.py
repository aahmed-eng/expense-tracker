import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
import calendar
import csv

DB_PATH = "tracker.db"

# Connects to database
@contextmanager
def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Creates 'transactions' and 'budgets' tables if they don't already exist
def init_db(db_path=DB_PATH):
    with get_connection(db_path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS transactions
        (date TEXT, category TEXT, amount REAL)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS budgets
        (category TEXT PRIMARY KEY, amount REAL)""")

# Parses a month into a (year, month) tuple
def parse_month(month: str) -> tuple[int, int]:
    today = date.today()
    if month is None:
        return today.year, today.month

    try:
        if "-" in month:
            parsed = datetime.strptime(month, "%Y-%m").date()
        else:
            parsed = datetime.strptime(month, "%m").date().replace(year=today.year)
    except ValueError:
        raise ValueError(f"Invalid format: '{month}'. Use YYYY-MM or MM.")

    if parsed > today.replace(day=1):
        raise ValueError("month cannot be in the future.")

    return parsed.year, parsed.month

# Add a transaction to the database, with an optional date (defaults to today)
# Date has to be in the format YYYY-MM-DD
def add_transaction(category, amount, transaction_date=None, db_path=DB_PATH):
    if amount <= 0:
        raise ValueError("Transactions must be positive.")
    if transaction_date is None:
        transaction_date = date.today().isoformat()
    if datetime.strptime(transaction_date, "%Y-%m-%d") > datetime.today():
        raise ValueError("Transaction date cannot be in the future.")
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO transactions VALUES (:date, :category, :amount)",
                {'date': transaction_date, 'category': category, 'amount': round(amount, 2)})
        return f"Added transaction: {transaction_date} - {category} - £{amount:.2f}"

# Delete a transaction from the database by its rowid, or all transactions if no rowid is provided
def delete_transaction(rowid, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        if rowid is not None:
            if conn.execute("SELECT * FROM transactions WHERE rowid = :rowid", {'rowid': rowid}).fetchone():
                conn.execute("DELETE FROM transactions WHERE rowid = :rowid", {'rowid': rowid})
                return f"Transaction {rowid} has been deleted from the database."
            raise ValueError("The ID you provided doesn't exist.")
        else:
            conn.execute("DELETE FROM transactions")
            return "All transactions have been deleted from the database."

# Return a list of all transactions in the database
# Month has to be in the format YYYY-MM or MM (in which case the current year is assumed)
def get_transactions(month, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        if month is None:
            c = conn.execute("SELECT rowid, * FROM transactions")
        else:
            year, month_num = parse_month(month)

            leap = year % 400 == 0 or (year % 100 != 0 and year % 4 == 0)
            days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            start_date = f"{year:04d}-{month_num:02d}-01"
            end_date = f"{year:04d}-{month_num:02d}-{days_in_month[month_num - 1]:02d}"

            c = conn.execute("SELECT rowid, * FROM transactions WHERE date >= :start_date AND date <= :end_date",
                             {'start_date': start_date, 'end_date': end_date})

        headers = [description[0] for description in c.description]
        rows = c.fetchall()

    if rows:
        title_msg = f"{calendar.month_name[month_num]} {year} Transactions:" if month is not None else "All Transactions:"
        total = sum(amount for _, _, _, amount in rows)
        rows.append(("Total", "", "", total))

        return rows, headers, title_msg
    return "No transactions found for the specified month." if month is not None else "No transactions found in the database."

# Return a list of all transaction under a given category
def get_transactions_by_category(category, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        c = conn.execute("SELECT rowid, * FROM transactions WHERE category = :category", {'category': category})
        rows = c.fetchall()
        headers = [description[0] for description in c.description]

    if rows:
        total = sum(amount for _, _, _, amount in rows)
        rows.append(("Total", "", "", total))

        return rows, headers
    return f"No transactions found under category '{category}'."

# Get a summary of transactions for a given month (or the current month if none is provided)
# Month has to be in the format YYYY-MM or MM (in which case the current year is assumed)
def summary(month, db_path=DB_PATH):
    year, month_num = parse_month(month)

    leap = year % 400 == 0 or (year % 100 != 0 and year % 4 == 0)
    days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    start_date = f"{year:04d}-{month_num:02d}-01"
    end_date = f"{year:04d}-{month_num:02d}-{days_in_month[month_num - 1]:02d}"

    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT category, SUM(amount) FROM transactions WHERE date >= :start_date AND date <= :end_date GROUP BY category",
            {'start_date': start_date, 'end_date': end_date}).fetchall()

    if rows:
        headers = ["Category", "Amount"]
        total = sum(amount for _, amount in rows)
        rows.append(("Total", total))
        

        title_msg = f"{calendar.month_name[month_num]} {year} Summary:"
        return rows, headers, title_msg
    return ("No transactions found for the specified month." if month is not None
            else "No transactions have been recorded this month.")

# Read and write budgets
# If no category is provided, all budgets will be returned
# If an amount is provided, the budget for the given category will be set to that amount
def budgets(category, amount, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        if category is None:
            rows = conn.execute("SELECT * FROM budgets").fetchall()
            if rows:
                headers = ["Category", "Amount"]
                total = sum(amount for _, amount in rows)
                rows.append(("Total", total))

                return rows, headers
            return None
        else:
            if not category.strip():
                raise ValueError("Please enter a valid category.")
            if amount is None:
                result = conn.execute("SELECT * FROM budgets WHERE category = :category", {'category': category}).fetchone()
                if result:
                    return f"Budget for category '{category}': £{result[1]:.2f}"
                return f"No budget has been set for category '{category}'."
            else:
                conn.execute("""INSERT INTO budgets VALUES (:category, :amount)
                                ON CONFLICT(category) DO UPDATE SET amount = :amount""",
                                {'category': category, 'amount': round(amount, 2)})
                return f"The budget for category '{category}' has been set to £{amount:.2f}."

# Remove budgets
# If no category is provided, all budgets will be removed
def remove_budget(category, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        if category is not None:
            res = conn.execute("SELECT category FROM budgets WHERE category = :category", {'category': category}).fetchone()
            if res:
                conn.execute("DELETE FROM budgets WHERE category = :category", {'category': category})
                return f"The budget for category '{category}' has been deleted from the database."
            return f"The budget for the category '{category}' doesn't exist."
        else:
            conn.execute("DELETE FROM budgets")
            return "All budgets have been deleted from the database."

# Export the 'transactions' and 'budgets' tables as 2 separate csv files
def export_csv(output_dir=".", db_path=DB_PATH):
    with get_connection(db_path) as conn:
        c = conn.execute("SELECT * FROM transactions") # rowid is not needed
        rows = c.fetchall()
        if rows:
            with open(f"{output_dir}/transactions.csv", "w", newline="") as csv_file:
                w = csv.writer(csv_file)
                w.writerow([description[0] for description in c.description])
                w.writerows(rows)
            empty1 = False
        else:
            empty1 = True

        c = conn.execute("SELECT * FROM budgets")
        rows = c.fetchall()
        if rows:
            with open(f"{output_dir}/budgets.csv", "w", newline="") as csv_file:
                w = csv.writer(csv_file)
                w.writerow([description[0] for description in c.description])
                w.writerows(rows)
            empty2 = False
        else:
            empty2 = True

    if empty1 and empty2:
        return "There is no data to export."
    elif empty1:
        return "There is no transactions data to export.\nBudgets data has been exported successfully."
    elif empty2:
        return "There is no budgets data to export.\nTransactions data has been exported successfully."
    else:
        return "Budgets and transactions data has been exported successfully."

# Import transactions and budgets from csv files
def import_csv(table, path, ndate, ncategory, namount, db_path=DB_PATH):
    column_mapping = {'date':ndate if ndate is not None else 'date',
                      'category':ncategory if ncategory is not None else 'category',
                      'amount':namount if namount is not None else 'amount'}

    table = table.lower()
    if table == "transactions":
        required_columns = [column_mapping["date"], column_mapping["category"], column_mapping["amount"]]
    elif table == "budgets":
        required_columns = [column_mapping["category"], column_mapping["amount"]]
    else:
        raise ValueError("Invalid table name. Please enter 'transactions' or 'budgets'.")

    errors = []
    imported = failed = 0

    with open(path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for column in required_columns:
            if column not in reader.fieldnames:
                raise KeyError(f"Column '{column}' not found in the CSV file.")

        if table == "transactions":
            for row in reader:
                date = row[column_mapping['date']]
                category = row[column_mapping['category']]
                if not category.strip():
                    failed += 1
                    errors.append(f"Line {reader.line_num}: The category is invalid.")
                    continue

                try:
                    amount = float(row[column_mapping['amount']])
                except ValueError:
                    errors.append(f"Line {reader.line_num}: The amount is not a number.")
                    failed += 1
                    continue
                
                try:
                    add_transaction(category, amount, date, db_path)
                    imported += 1
                except ValueError as error:
                    errors.append(f"Line {reader.line_num}: {error}")
                    failed += 1
                    continue

        elif table == "budgets":
            for row in reader:
                category = row[column_mapping['category']]
                if not category.strip():
                    failed += 1
                    errors.append(f"Line {reader.line_num}: The category is invalid.")
                    continue

                try:
                    amount = float(row[column_mapping['amount']])
                except ValueError:
                    errors.append(f"Line {reader.line_num}: The amount is not a number.")
                    failed += 1
                    continue

                try:
                    budgets(category, amount, db_path)
                    imported += 1
                except ValueError as error:
                    errors.append(f"Line {reader.line_num}: {error}")
                    failed += 1
                    continue
            
    return {"imported": imported, "failed": failed, "errors": errors}
