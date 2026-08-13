import database
import argparse
from tabulate import tabulate, SEPARATING_LINE

def main():
    database.init_db() # Initialises database

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="action")

    # Display a list of all transactions in the database, optionally filtered by month
    display_parser = subparsers.add_parser("display", help="Display a list of all transactions in the database")
    display_parser.add_argument("month", nargs="*", type=str, help="Month for which to display transactions (format: YYYY-MM)")

    # Display a list of all transactions in the database under a specific category
    category_parser = subparsers.add_parser("category_display",
                                            help="Display a list of all transactions in the database under a specific category")
    category_parser.add_argument("category", nargs="+", type=str, help="Category of the transactions to display")

    # Add a transaction to the database
    add_parser = subparsers.add_parser("add", help="Record a new transaction")
    add_parser.add_argument("category", type=str, help="Category of the transaction to add")
    add_parser.add_argument("amount", nargs="+", type=float, help="Amount of the transaction to add")

    # Delete a transaction from the database by its rowid, or all transactions if no rowid is provided
    delete_parser = subparsers.add_parser("delete", help="Delete a transaction from history")
    delete_parser.add_argument("id", nargs="*", type=int, help="ID of the transaction to delete")

    # Get a summary of transactions for a given month (or the current month if none is provided)
    summary_parser = subparsers.add_parser("summary", help="Get a summary of transactions for a given month")
    summary_parser.add_argument("month", nargs="*", type=str, help="Month for which to display summary (format: YYYY-MM)")

    # Read and write budgets
    budget_parser = subparsers.add_parser("budget", help="Check or set budgets")
    budget_parser.add_argument("category", nargs="?", type=str, help="Category for which to check or set budget")
    budget_parser.add_argument("amount", nargs="?", type=float,
                            help="Amount to set for the budget (if not provided, will display current budget)")

    # Remove budgets
    remove_budget_parser = subparsers.add_parser("remove_budget", help="Delete a budget for a specific category")
    remove_budget_parser.add_argument("category", nargs="*", type=str, help="Category for which to delete the budget")

    # Reset the database (delete all transactions and budgets)
    subparsers.add_parser("reset", help="Reset the database (delete all transactions and budgets)")

    # Export transactions and budgets into csv files
    subparsers.add_parser("export", help="Export transactions and budgets into csv files")

    # Import transactions and budgets from csv files
    import_parser = subparsers.add_parser("import", help="Import transactions and budgets from csv files")
    import_parser.add_argument("table", type=str, help="The table you would like to import into: 'transactions' or 'budgets'")
    import_parser.add_argument("path", type=str, help="The path to the csv file you want to import from")
    import_parser.add_argument("--date", type=str, help="The name of the column which corresponds to the 'date' column")
    import_parser.add_argument("--category", type=str, help="The name of the column which corresponds to the 'category' column")
    import_parser.add_argument("--amount", type=str, help="The name of the column which corresponds to the 'amount' column")

    args = parser.parse_args()

    if args.action == "display":
        if not args.month: args.month = [None]
        for month in args.month:
            res = database.get_transactions(month)
            if isinstance(res, tuple):
                rows, headers, title_msg = res
                rows.insert(-1, SEPARATING_LINE)
                print(f"\n{title_msg}")
                print(tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=('left', 'right')))
            else:
                print(res)

    elif args.action == "category_display":
        for category in args.category:
            res = database.get_transactions_by_category(category)
            if isinstance(res, tuple):
                rows, headers = res
                rows.insert(-1, SEPARATING_LINE)
                print(f"\n{category.title()} Transactions:")
                print(tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=('left', 'right')))
            else:
                print(res)

    elif args.action == "add":
        if not args.category.strip():
            raise ValueError("Please enter a valid category.")
        for amount in args.amount:
            try:
                print(database.add_transaction(args.category, amount))
            except ValueError as error:
                print(f"Could not add transaction: {error}")

    elif args.action == "delete":
        if not args.id: args.id = [None]
        for id in args.id:
            print(database.delete_transaction(id))

    elif args.action == "summary":
        if not args.month: args.month = [None]
        for month in args.month:
            res = database.summary(month)
            if isinstance(res, tuple):
                rows, headers, title_msg = res
                rows.insert(-1, SEPARATING_LINE)
                print(f"\n{title_msg}")
                print(tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=('left', 'right')))
            else:
                print(res)

    elif args.action == "budget":
        res = database.budgets(args.category, args.amount)
        if res is None:
            print("No budgets have been set.")
        elif isinstance(res, tuple):
            rows, headers = res
            rows.insert(-1, SEPARATING_LINE)
            print("\nBudgets:")
            print(tabulate(rows, headers=headers, tablefmt="fancy_grid", colalign=('left', 'right')))
        else:
            print(res)

    elif args.action == "remove_budget":
        if not args.category: args.category = [None]
        for category in args.category:
            print(database.remove_budget(category))

    elif args.action == "reset":
        check = input("Are you sure you want to reset the database? This will delete all transactions and budgets. (y/n): ") \
            .lower().strip()
        if check == "y":
            database.delete_transaction(None)
            database.remove_budget(None)
            print("Reset complete.")
        elif check == "n":
            print("Database reset cancelled.")
        else:
            print("Invalid input. Database reset cancelled.")

    elif args.action == "export":
        print(database.export_csv())

    elif args.action == "import":
        res = database.import_csv(args.table, args.path, args.date, args.category, args.amount)
        print(f"Imported: {res['imported']}\nFailed: {res['failed']}")
        if res['errors']:
            print("\nErrors:")
            for error in res['errors']:
                print(error)

    else:
        print("No actions specified. Use -h for help.")

if __name__ == "__main__":
    main()
