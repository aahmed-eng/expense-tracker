// ===========================================================================
// Expense Tracker frontend
// ===========================================================================

// Change this if your API runs somewhere else.
const API_BASE = "http://127.0.0.1:8000";

// Formats a number as a price, e.g. 12.5 -> "£12.50"
function formatMoney(amount) {
  return "£" + Number(amount).toFixed(2);
}

// Shows a message under a form (green for success, red for error).
function showStatus(element, message, isError) {
  element.textContent = message;
  element.className = isError ? "status error" : "status ok";
}

// -----------------------------------------------------------------------
// A helper function for calling the API.
// Every fetch() call in this file goes through here so we only have to
// write the "check for errors" logic once.
// -----------------------------------------------------------------------
async function callApi(path, options) {
  const response = await fetch(API_BASE + path, options);
  const data = await response.json();

  if (!response.ok) {
    // FastAPI sends errors as { "detail": "some message" }
    throw new Error(data.detail || "Something went wrong");
  }

  return data;
}


// ===========================================================================
// TRANSACTIONS
// ===========================================================================

async function loadTransactions() {
  const monthInput = document.getElementById("filter-month").value;
  const path = monthInput ? "/transactions?month=" + monthInput : "/transactions";

  const result = await callApi(path);
  const transactions = result.transactions;
  const total = result.total;

  const tableBody = document.getElementById("transactions-body");
  tableBody.innerHTML = "";

  if (transactions.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="4" class="empty-note">No transactions yet.</td></tr>';
    return;
  }

  // Add one row per transaction
  for (let i = 0; i < transactions.length; i++) {
    const t = transactions[i];

    const row = document.createElement("tr");
    row.innerHTML =
      "<td>" + t.date + "</td>" +
      "<td>" + t.category + "</td>" +
      "<td>" + formatMoney(t.amount) + "</td>" +
      '<td><button class="small">Delete</button></td>';

    // Connect delete button to delete functions
    const deleteButton = row.querySelector("button");
    deleteButton.addEventListener("click", function () {
      deleteTransaction(t.rowid);
    });

    tableBody.appendChild(row);
  }

  // Total row at the bottom
  const totalRow = document.createElement("tr");
  totalRow.className = "total-row";
  totalRow.innerHTML = "<td></td><td>Total</td><td>" + formatMoney(total) + "</td><td></td>";
  tableBody.appendChild(totalRow);
}

async function deleteTransaction(id) {
  try {
    await callApi("/transactions/" + id, { method: "DELETE" });
    loadTransactions();
    loadBudgets(); // budget progress bars depend on current spending
  } catch (error) {
    alert(error.message);
  }
}

// Handle the "Add transaction" form
document.getElementById("add-transaction-form").addEventListener("submit", async function (event) {
  event.preventDefault(); // stop the page from reloading

  const statusBox = document.getElementById("add-status");
  const category = document.getElementById("tx-category").value.trim();
  const amount = parseFloat(document.getElementById("tx-amount").value);
  const date = document.getElementById("tx-date").value || null;

  try {
    const result = await callApi("/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: category, amount: amount, date: date }),
    });

    showStatus(statusBox, result.message, false);
    event.target.reset();
    loadTransactions();
    loadBudgets();
  } catch (error) {
    showStatus(statusBox, error.message, true);
  }
});

// Delete all transactions
document.getElementById("delete-all-btn").addEventListener("click", async function () {
  const confirmed = confirm("Delete every transaction? This can't be undone.");
  if (!confirmed) return;

  await callApi("/transactions", { method: "DELETE" });
  loadTransactions();
  loadBudgets();
});

// Month filter
document.getElementById("filter-month").addEventListener("change", loadTransactions);

document.getElementById("clear-filter-btn").addEventListener("click", function () {
  document.getElementById("filter-month").value = "";
  loadTransactions();
});


// ===========================================================================
// BUDGETS
// ===========================================================================

async function loadBudgets() {
  // Get the list of budgets, and this month's spending per category (to draw
  // the progress bars).
  const budgetsResult = await callApi("/budgets");
  const summaryResult = await callApi("/summary");

  const budgets = budgetsResult.budgets;
  const categories = summaryResult.categories;

  // Turn the summary list into a lookup table: { "food": 12.50, "rent": 500 }
  const spendByCategory = {};
  for (let i = 0; i < categories.length; i++) {
    spendByCategory[categories[i].Category] = categories[i].Amount;
  }

  const list = document.getElementById("budgets-list");
  list.innerHTML = "";

  if (budgets.length === 0) {
    list.innerHTML = '<p class="empty-note">No budgets set yet.</p>';
    return;
  }

  for (let i = 0; i < budgets.length; i++) {
    const budget = budgets[i];
    const spent = spendByCategory[budget.Category] || 0;
    const percentUsed = Math.min(100, (spent / budget.Amount) * 100);
    const isOverBudget = spent > budget.Amount;

    const item = document.createElement("div");
    item.className = "budget-item";
    item.innerHTML =
      '<div class="budget-head">' +
      "<span>" + budget.Category + "</span>" +
      "<span>" + formatMoney(spent) + " / " + formatMoney(budget.Amount) +
      ' <button class="small">Remove</button></span>' +
      "</div>" +
      '<div class="budget-bar-track">' +
      '<div class="budget-bar-fill' + (isOverBudget ? " over" : "") + '" style="width:' + percentUsed + '%"></div>' +
      "</div>";

    const removeButton = item.querySelector("button");
    removeButton.addEventListener("click", function () {
      deleteBudget(budget.Category);
    });

    list.appendChild(item);
  }
}

async function deleteBudget(category) {
  try {
    await callApi("/budgets/" + encodeURIComponent(category), { method: "DELETE" });
    loadBudgets();
  } catch (error) {
    alert(error.message);
  }
}

// Handle the "Set budget" form
document.getElementById("budget-form").addEventListener("submit", async function (event) {
  event.preventDefault();

  const category = document.getElementById("budget-category").value.trim();
  const amount = parseFloat(document.getElementById("budget-amount").value);

  try {
    await callApi("/budgets/" + encodeURIComponent(category), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: amount }),
    });

    event.target.reset();
    loadBudgets();
  } catch (error) {
    alert(error.message);
  }
});


// ===========================================================================
// EXPORT / IMPORT
// ===========================================================================

document.getElementById("export-btn").addEventListener("click", async function () {
  const linksBox = document.getElementById("export-links");

  try {
    const result = await callApi("/export", { method: "POST" });
    const files = result.files; // e.g. { transactions: "/export/transactions.csv", budgets: "..." }

    let linksHtml = "";
    for (const name in files) {
      const url = API_BASE + files[name];
      linksHtml += ' <a href="' + url + '" target="_blank">' + name + ".csv</a>";
    }
    linksBox.innerHTML = linksHtml;
  } catch (error) {
    alert(error.message);
  }
});

// Handle the "Import CSV" form
document.getElementById("import-form").addEventListener("submit", async function (event) {
  event.preventDefault();

  const statusBox = document.getElementById("import-status");
  const table = document.getElementById("import-table").value;
  const file = document.getElementById("import-file").files[0];

  // File uploads use FormData instead of JSON.
  const formData = new FormData();
  formData.append("table", table);
  formData.append("file", file);

  try {
    const result = await callApi("/import", { method: "POST", body: formData });
    const message = "Imported " + result.imported + ", failed " + result.failed + ".";
    showStatus(statusBox, message, result.failed > 0);
    event.target.reset();
    loadTransactions();
    loadBudgets();
  } catch (error) {
    showStatus(statusBox, error.message, true);
  }
});


// ===========================================================================
// RESET
// ===========================================================================

document.getElementById("reset-btn").addEventListener("click", async function () {
  const confirmed = confirm("This deletes ALL transactions and budgets. Continue?");
  if (!confirmed) return;

  await callApi("/reset", { method: "POST" });
  loadTransactions();
  loadBudgets();
});


// ===========================================================================
// Load everything when the page first opens
// ===========================================================================
loadTransactions();
loadBudgets();
