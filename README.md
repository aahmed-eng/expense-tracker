# Expense Tracker

A SQLite-backed expense and budget tracker with three ways to use it: a command-line interface, a REST API, and a browser-based frontend that talks to the API. All three sit on top of the same `database.py` module, so behaviour stays consistent regardless of how you interact with it.

## Features

- Add, delete, and view transactions
- Filter transactions by month or category
- Monthly summaries grouped by category
- Set, view, and remove per-category budgets, with visual progress bars in the frontend
- Export transactions and budgets to CSV, and import them back in (with custom column mapping)
- Reset the database
- A FastAPI backend exposing all of the above over HTTP, with interactive docs included
- A lightweight HTML/CSS/JS frontend for managing everything in the browser

## Project structure

```
expense-tracker/
├── pyproject.toml
├── README.md
├── requirements.txt
├── expense_tracker/
|   ├── api.py
|   ├── cli.py
|   └── database.py
├── frontend/
|   ├── index.html
|   ├── script.js
|   └── style.css
└── tests/
    ├── conftest.py
    └── test_database.py
```

`database.py` is the shared data layer — every read/write goes through it. `cli.py` and `api.py` are two independent interfaces built on top of it; the frontend talks only to `api.py` over HTTP.

## Requirements

- Python 3
- [`fastapi`](https://pypi.org/project/fastapi/) and [`uvicorn`](https://pypi.org/project/uvicorn/) (API)
- [`tabulate`](https://pypi.org/project/tabulate/) (CLI)
- [`pytest`](https://pypi.org/project/pytest/) (tests)

Install everything with:

```bash
pip install -r requirements.txt
```

## Using the CLI

Run commands from inside `expense_tracker/`:

```bash
cd expense_tracker
python cli.py <action> [arguments]
```

The database (`tracker.db`) is created automatically on first run.

### Display transactions

```bash
python cli.py display                # all transactions
python cli.py display 2024-05         # transactions for May 2024
python cli.py display 2024-05 2024-06 # multiple months at once
```

### Display transactions by category

```bash
python cli.py category_display groceries
python cli.py category_display groceries rent
```

### Add a transaction

```bash
python cli.py add groceries 12.50
python cli.py add groceries 12.50 8.75   # add multiple amounts at once
```

### Delete a transaction

```bash
python cli.py delete 3        # delete transaction with rowid 3
python cli.py delete          # delete all transactions
```

### Monthly summary

```bash
python cli.py summary          # current month
python cli.py summary 2024-05  # specific month
```

### Budgets

```bash
python cli.py budget                     # show all budgets
python cli.py budget groceries           # show budget for a category
python cli.py budget groceries 200       # set budget for a category
```

### Remove budgets

```bash
python cli.py remove_budget groceries    # remove one budget
python cli.py remove_budget              # remove all budgets
```

### Reset the database

```bash
python cli.py reset
```

Prompts for confirmation before deleting all transactions and budgets.

### Export to CSV

```bash
python cli.py export
```

Writes `transactions.csv` and/or `budgets.csv` to the current directory.

### Import from CSV

```bash
python cli.py import transactions path/to/file.csv
python cli.py import budgets path/to/file.csv
```

If your CSV columns aren't named `date`, `category`, and `amount`, map them explicitly:

```bash
python cli.py import transactions path/to/file.csv --date "Date" --category "Type" --amount "Value"
```

## Using the API

Start the server from inside `expense_tracker/`:

```bash
cd expense_tracker
uvicorn api:app --reload
```

The API runs at `http://127.0.0.1:8000`. FastAPI generates interactive docs for every endpoint automatically — visit `http://127.0.0.1:8000/docs` to try requests directly in the browser.

CORS is wide open (`allow_origins=["*"]`) so the frontend can call the API from a different origin during local development. Lock this down before deploying anywhere public.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/transactions` | List transactions, optionally filtered with `?month=YYYY-MM` |
| GET    | `/transactions/category/{category}` | List transactions in a category |
| POST   | `/transactions` | Add a transaction (`category`, `amount`, optional `date`) |
| DELETE | `/transactions/{id}` | Delete a transaction by rowid |
| DELETE | `/transactions` | Delete all transactions |
| GET    | `/summary` | Category totals, optionally filtered with `?month=YYYY-MM` |
| GET    | `/budgets` | List all budgets |
| GET    | `/budgets/{category}` | Get the budget for a category |
| PUT    | `/budgets/{category}` | Set the budget for a category (`amount`) |
| DELETE | `/budgets/{category}` | Remove a category's budget |
| DELETE | `/budgets` | Remove all budgets |
| POST   | `/reset` | Delete all transactions and budgets |
| POST   | `/export` | Write CSV exports on the server and return download URLs |
| GET    | `/export/{filename}` | Download an exported CSV (`transactions.csv` or `budgets.csv`) |
| POST   | `/import` | Import a CSV file (multipart form: `table`, `file`, optional column overrides) |

## Using the frontend

With the API running, open `frontend/index.html` directly in a browser (or serve the `frontend/` folder with any static file server). The page lets you add and delete transactions, filter by month, set budgets with live progress bars against the current month's spend, export/import CSVs, and reset the database — all via calls to the API.

`script.js` points at `API_BASE = "http://127.0.0.1:8000"` by default; change this constant if the API is running somewhere else.

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

Tests are written with `pytest` and live in `tests/test_database.py`, covering `expense_tracker/database.py` directly — since the CLI, API, and frontend all sit on top of this one module, testing it thoroughly covers the logic behind all three interfaces (the CLI and API layers themselves aren't separately tested).

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

- Add tests for `cli.py` and `api.py`
- Allow a custom date to be specified when adding a transaction via the CLI (the API and frontend already support this)
- Allow filtering by both category and month at the same time
- Support custom date ranges, not just calendar months
- Add optional descriptions/notes to transactions
- Support separate budgets each month, rather than one budget per category overall
- Serve the frontend directly from the API so the whole app runs from a single process
- Add authentication so the API can support multiple users
- Deploy the API and frontend so it's usable outside of localhost
