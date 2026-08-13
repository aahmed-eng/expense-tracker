# Expense Tracker CLI

A simple command-line expense and budget tracker backed by SQLite. Record transactions, view summaries by month or category, set budgets, and import/export your data as CSV.

## Features

- Add, delete, and display transactions
- Filter transactions by month or category
- Monthly summaries grouped by category
- Set, view, and remove per-category budgets
- Export transactions and budgets to CSV
- Import transactions and budgets from CSV (with custom column mapping)
- Reset the database

## Project structure

```
cli-expense-tracker/
├── pyproject.toml
├── README.md
├── requirements.txt
├── expense_tracker/
|   ├── cli.py
|   └── database.py
└── tests/
    ├── conftest.py
    └── test_database.py
```

## Requirements

- Python 3
- [`tabulate`](https://pypi.org/project/tabulate/)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run commands via `expense_tracker/cli.py`:

```bash
python -m expense_tracker.cli <action> [arguments]
```

The database (`tracker.db`) is created automatically on first run.

### Display transactions

```bash
python -m expense_tracker.cli display                # all transactions
python -m expense_tracker.cli display 2024-05         # transactions for May 2024
python -m expense_tracker.cli display 2024-05 2024-06 # multiple months at once
```

### Display transactions by category

```bash
python -m expense_tracker.cli category_display groceries
python -m expense_tracker.cli category_display groceries rent
```

### Add a transaction

```bash
python -m expense_tracker.cli add groceries 12.50
python -m expense_tracker.cli add groceries 12.50 8.75   # add multiple amounts at once
```

### Delete a transaction

```bash
python -m expense_tracker.cli delete 3        # delete transaction with rowid 3
python -m expense_tracker.cli delete          # delete all transactions
```

### Monthly summary

```bash
python -m expense_tracker.cli summary          # current month
python -m expense_tracker.cli summary 2024-05  # specific month
```

### Budgets

```bash
python -m expense_tracker.cli budget                     # show all budgets
python -m expense_tracker.cli budget groceries           # show budget for a category
python -m expense_tracker.cli budget groceries 200       # set budget for a category
```

### Remove budgets

```bash
python -m expense_tracker.cli remove_budget groceries    # remove one budget
python -m expense_tracker.cli remove_budget              # remove all budgets
```

### Reset the database

```bash
python -m expense_tracker.cli reset
```

Prompts for confirmation before deleting all transactions and budgets.

### Export to CSV

```bash
python -m expense_tracker.cli export
```

Writes `transactions.csv` and/or `budgets.csv` to the current directory.

### Import from CSV

```bash
python -m expense_tracker.cli import transactions path/to/file.csv
python -m expense_tracker.cli import budgets path/to/file.csv
```

If your CSV columns aren't named `date`, `category`, and `amount`, map them explicitly:

```bash
python -m expense_tracker.cli import transactions path/to/file.csv --date "Date" --category "Type" --amount "Value"
```

## Data model

**transactions**
| Column   | Type |
|----------|------|
| date     | TEXT (`YYYY-MM-DD`) |
| category | TEXT |
| amount   | REAL |

**budgets**
| Column   | Type |
|----------|------|
| category | TEXT (primary key) |
| amount   | REAL |

## Testing

Tests are written with `pytest` and live in `tests/test_database.py`, covering `expense_tracker/database.py` directly (the CLI layer isn't tested).

Install `pytest` and run the suite from the project root:

```bash
pip install pytest
pytest
```

### Fixtures

`tests/conftest.py` defines two fixtures used throughout the suite:

- **`db_path`** — creates a fresh, initialised SQLite database in a `pytest` temp directory for each test, so tests never touch your real `tracker.db` and can't interfere with each other.
- **`csv_path`** — a factory fixture for quickly writing out a temporary CSV file with a given filename, header, and rows, used by the import tests.

### What's covered

- **Month parsing** — valid `YYYY-MM` and `MM` formats, defaulting to the current year/month, and rejecting invalid formats or future months.
- **Adding transactions** — correct return messages, default vs. explicit dates, rejecting non-positive amounts and future-dated transactions.
- **Deleting transactions** — deleting a single transaction by rowid, rejecting unknown ids, and deleting all transactions at once.
- **Retrieving transactions** — filtering by month and by category, month-boundary edge cases (first/last day, leap years), and the "no transactions found" messages for empty results.
- **Summaries** — grouping by category within a month, correct totals, and defaulting to the current month.
- **Budgets** — setting, updating, and reading budgets (including rounding), rejecting invalid categories, and listing all budgets with a total.
- **Removing budgets** — deleting a single category's budget vs. all budgets, and the messages returned when a budget doesn't exist.
- **CSV export** — behaviour when transactions/budgets/both/neither are present, and that the exported files contain the correct columns and values.
- **CSV import** — successful imports, custom column-name mapping, invalid table names, and per-row error handling (missing columns, blank categories, non-numeric amounts, future dates, and a mix of valid/invalid rows in the same file).
- **Export/import round trip** — exporting to CSV and re-importing into a fresh database reproduces the original transactions and budgets exactly.

## Future improvements

- Rebuild as a full-stack app: a backend API on top of the existing database logic, with a simple HTML/JS frontend to interact with it
- Allow a custom date to be specified when adding a transaction via the CLI
- Allow filtering by both category and month at the same time
- Support custom date ranges, not just calendar months
- Add optional descriptions/notes to transactions
- Support separate budgets per month, rather than one budget per category overall
