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

## Requirements

- `fastapi` and `uvicorn` (API)
- `tabulate` (CLI)
- `pytest` (tests)

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

### Using the CLI

Run commands from inside `expense_tracker/`:

```bash
python cli.py <action> [arguments]
```

Use `python cli.py -h` for help.

### Using the API

Start the server from inside `expense_tracker/`:

```bash
uvicorn api:app --reload
```

### Using the frontend

With the API running, open `frontend/index.html` directly in a browser. The page lets you add and delete transactions, filter by month, set budgets with live progress bars against the current month's spend, export/import CSVs, and reset the database.

`script.js` points at `API_BASE = "http://127.0.0.1:8000"` by default; change this constant if the API is running somewhere else.
