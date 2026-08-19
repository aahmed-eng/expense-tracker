"""
FastAPI backend for the expense tracker.

Run it with:
    uvicorn api:app --reload

Then visit http://127.0.0.1:8000/docs for an interactive API playground
(FastAPI generates this automatically from the code below).
"""

import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional

import database

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Expense Tracker API")

# CORS = Cross-Origin Resource Sharing. Browsers block JS on one "origin"
# (e.g. a file opened directly, or http://localhost:5500) from calling an API on another origin (e.g. http://127.0.0.1:8000)
# unless the API explicitly allows it.
# allow_origins=["*"] means "any origin can call this API" — fine for local development,
# but you'd lock this down to a specific domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPORT_DIR = "exports"


@app.on_event("startup")
def on_startup():
    # Creates the tables if they don't already exist
    database.init_db()
    os.makedirs(EXPORT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic models — these define what JSON the frontend must send you.
# FastAPI validates incoming requests against these automatically and
# returns a clear 422 error if something's missing or the wrong type,
# before your code even runs.
# ---------------------------------------------------------------------------

class TransactionIn(BaseModel):
    category: str
    amount: float
    date: Optional[str] = None  # "YYYY-MM-DD"; defaults to today if omitted


class BudgetIn(BaseModel):
    amount: float = Field(gt=0, description="Budget amount, must be positive")


# ---------------------------------------------------------------------------
# Helpers
#
# database.py's read functions (get_transactions, get_transactions_by_category,
# summary, budgets) return raw floats, so we can use them directly instead of
# re-querying the database ourselves. They are two CLI-oriented things we do
# need to undo for a clean API response:
#   1. They append a ("Total", ..., total) sentinel row for display purposes.
#   2. They return a plain string (not a tuple) when there's no data.
# _unpack() below handles both, turning the result into a plain list of dicts
# plus a separately-computed total, or an empty list if there's no data.
# ---------------------------------------------------------------------------

def _unpack(result):
    """Turn a database.py (rows, headers, ...) result into list[dict]. Returns
    [] if the function returned a "no data" string instead of a tuple."""
    if not isinstance(result, tuple):
        return []
    rows, headers = result[0], result[1]
    data_rows = [row for row in rows if row[0] != "Total"]
    return [dict(zip(headers, row)) for row in data_rows]


# ---------------------------------------------------------------------------
# Transaction endpoints
# ---------------------------------------------------------------------------

@app.get("/transactions")
def list_transactions(month: Optional[str] = None):
    """GET /transactions or /transactions?month=2026-08"""
    try:
        result = database.get_transactions(month)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    transactions = _unpack(result)
    total = round(sum(t["amount"] for t in transactions), 2)
    return {"transactions": transactions, "total": total}


@app.get("/transactions/category/{category}")
def list_transactions_by_category(category: str):
    result = database.get_transactions_by_category(category)
    transactions = _unpack(result)
    total = round(sum(t["amount"] for t in transactions), 2)
    return {"transactions": transactions, "total": total}


@app.post("/transactions", status_code=201)
def add_transaction(transaction: TransactionIn):
    """POST /transactions with JSON body: {"category": "food", "amount": 12.5, "date": "2026-08-14"}"""
    try:
        message = database.add_transaction(transaction.category, transaction.amount, transaction.date)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return {"message": message}


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int):
    try:
        message = database.delete_transaction(transaction_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {"message": message}


@app.delete("/transactions")
def delete_all_transactions():
    message = database.delete_transaction(None)
    return {"message": message}


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------

@app.get("/summary")
def get_summary(month: Optional[str] = None):
    """GET /summary or /summary?month=2026-08 — totals grouped by category."""
    try:
        result = database.summary(month)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    categories = _unpack(result)
    total = round(sum(c["Amount"] for c in categories), 2)
    return {"categories": categories, "total": total}


# ---------------------------------------------------------------------------
# Budget endpoints
# ---------------------------------------------------------------------------

@app.get("/budgets")
def list_budgets():
    result = database.budgets(None, None)  # None means "return everything"
    budgets = _unpack(result)
    total = round(sum(b["Amount"] for b in budgets), 2)
    return {"budgets": budgets, "total": total}


@app.get("/budgets/{category}")
def get_budget(category: str):
    # budgets(category, None) returns a human-readable sentence for a single
    # category (built for the CLI), so I queried the table directly here to
    # give the frontend clean JSON instead of a string it would have to parse.
    with database.get_connection() as conn:
        row = conn.execute("SELECT amount FROM budgets WHERE category = :category", {"category": category}).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No budget set for category '{category}'.")
    return {"category": category, "amount": row[0]}


@app.put("/budgets/{category}")
def set_budget(category: str, budget: BudgetIn):
    if not category.strip():
        raise HTTPException(status_code=400, detail="Please enter a valid category.")
    message = database.budgets(category, budget.amount)
    return {"message": message}


@app.delete("/budgets/{category}")
def delete_budget(category: str):
    message = database.remove_budget(category)
    if "doesn't exist" in message:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message}


@app.delete("/budgets")
def delete_all_budgets():
    message = database.remove_budget(None)
    return {"message": message}


# ---------------------------------------------------------------------------
# Reset - convenience endpoint for the frontend
# (same as cli.py's "reset" action)
# ---------------------------------------------------------------------------

@app.post("/reset")
def reset():
    database.delete_transaction(None)
    database.remove_budget(None)
    return {"message": "Reset complete."}


# ---------------------------------------------------------------------------
# Export / import endpoints
# ---------------------------------------------------------------------------

@app.post("/export")
def export_data():
    """Writes transactions.csv and budgets.csv on the server, and returns
    URLs the frontend can use to download them."""
    message = database.export_csv(output_dir=EXPORT_DIR)

    files = {}
    if os.path.exists(f"{EXPORT_DIR}/transactions.csv"):
        files["transactions"] = "/export/transactions.csv"
    if os.path.exists(f"{EXPORT_DIR}/budgets.csv"):
        files["budgets"] = "/export/budgets.csv"

    return {"message": message, "files": files}


@app.get("/export/{filename}")
def download_export(filename: str):
    # Only allow these two exact filenames - never trust a path coming straight from the URL
    # (it could otherwise be used to read arbitrary files off the server, e.g. filename="../../etc/passwd").
    if filename not in ("transactions.csv", "budgets.csv"):
        raise HTTPException(status_code=404, detail="File not found.")
    path = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found. Call POST /export first.")
    return FileResponse(path, filename=filename, media_type="text/csv")


@app.post("/import")
async def import_data(
    table: str = Form(..., description="'transactions' or 'budgets'"),
    file: UploadFile = File(...),
    date_column: Optional[str] = Form(None),
    category_column: Optional[str] = Form(None),
    amount_column: Optional[str] = Form(None),
):
    """Multipart form upload: table + csv file + optional column-name overrides."""
    # database.import_csv needs a real file path on disk, so we save the
    # uploaded file to a temporary location, run the import, then clean up.
    suffix = ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = database.import_csv(table, tmp_path, date_column, category_column, amount_column)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    finally:
        os.remove(tmp_path)

    return result
