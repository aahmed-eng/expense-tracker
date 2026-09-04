# Expense Tracker

A SQLite-backed expense and budget tracker with three ways to use it: a command-line interface, a REST API, and a browser-based frontend that talks to the API.

## Features

- Add, delete, and view transactions
- Filter transactions by month or category
- Monthly summaries grouped by category
- Set, view, and remove per-category budgets
- Export transactions and budgets to CSV, and import them back in
- Reset the database
- A FastAPI backend exposing all of the above over HTTP
- An HTML/CSS/JS frontend for managing everything in the browser

## Installation

```bash
pip install -r requirements.txt
```

## Using the CLI

Run commands from inside `expense_tracker/`:

```bash
python cli.py <action> [arguments]
```

## Using the API

Start the server from inside `expense_tracker/`:

```bash
uvicorn api:app --reload
```

## Using the frontend

With the API running, open `frontend/index.html` directly in a browser. The page lets you add and delete transactions, filter by month, set budgets with live progress bars against the current month's spend, export/import CSVs, and reset the database.

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

Tests are written with `pytest` and live in `tests/test_database.py`, covering `database.py` directly - since the CLI, API, and frontend all sit on top of this one module, testing it thoroughly covers the logic behind all three interfaces.

Install `pytest` and run the suite from the project root:

```bash
pip install pytest
pytest
```

### What's covered

- **Month parsing** - valid `YYYY-MM` and `MM` formats, defaulting to the current year/month, and rejecting invalid formats or future months.
- **Adding transactions** - correct return messages, default vs. explicit dates, rejecting non-positive amounts and future-dated transactions.
- **Deleting transactions** - deleting a single transaction by rowid, rejecting unknown ids, and deleting all transactions at once.
- **Retrieving transactions** - filtering by month and by category, month-boundary edge cases (first/last day, leap years), and the "no transactions found" messages for empty results.
- **Summaries** - grouping by category within a month, correct totals, and defaulting to the current month.
- **Budgets** - setting, updating, and reading budgets (including rounding), rejecting invalid categories, and listing all budgets with a total.
- **Removing budgets** - deleting a single category's budget vs. all budgets, and the messages returned when a budget doesn't exist.
- **CSV export** - behaviour when transactions/budgets/both/neither are present, and that the exported files contain the correct columns and values.
- **CSV import** - successful imports, custom column-name mapping, invalid table names, and per-row error handling (missing columns, blank categories, non-numeric amounts, future dates, and a mix of valid/invalid rows in the same file).
- **Export/import round trip** - exporting to CSV and re-importing into a fresh database reproduces the original transactions and budgets exactly.

## Future improvements

- Add tests for `cli.py` and `api.py`
- Allow a custom date to be specified when adding a transaction via the CLI (the API and frontend already support this)
- Allow filtering by both category and month at the same time
- Support custom date ranges, not just calendar months
- Add optional descriptions/notes to transactions
- Support separate budgets each month, rather than one budget per category overall
- Add authentication so the API can support multiple users
- Deploy the API and frontend so it's usable outside of localhost
