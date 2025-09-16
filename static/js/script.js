// Function to show a specific section and hide all others
function showSection(sectionId) {
  const sections = [
    "incomplete-table",
    "completed-table",
    "add-module-section",
    "users-section",
    "modules-section",
  ];

  sections.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.style.display = id === sectionId ? "block" : "none";
    }
  });

  // Handle Admin Dashboard Buttons
  const addModuleBtn = document.getElementById("add-module-btn");
  const viewUsersBtn = document.getElementById("view-users-btn");
  const viewModulesBtn = document.getElementById("view-modules-btn");

  if (addModuleBtn && viewUsersBtn && viewModulesBtn) {
    addModuleBtn.disabled = sectionId === "add-module-section";
    viewUsersBtn.disabled = sectionId === "users-section";
    viewModulesBtn.disabled = sectionId === "modules-section";
  }

  // Logic to control the show/hide buttons on ALL training dashboard pages
  const showIncompleteBtn = document.getElementById("show-incomplete-btn");
  const showCompletedBtn = document.getElementById("show-completed-btn");

  if (showIncompleteBtn && showCompletedBtn) {
    if (sectionId === "incomplete-table") {
      showIncompleteBtn.style.display = "none";
      showCompletedBtn.style.display = "inline-block";
    } else if (sectionId === "completed-table") {
      showIncompleteBtn.style.display = "inline-block";
      showCompletedBtn.style.display = "none";
    }
  }

  // Logic to control print button visibility on the user report page
  const printIncompleteBtn = document.getElementById("print-incomplete");
  const printCompletedBtn = document.getElementById("print-completed");

  if (printIncompleteBtn && printCompletedBtn) {
    if (sectionId === "incomplete-table") {
      printIncompleteBtn.style.display = "inline-block";
      printCompletedBtn.style.display = "none";
    } else if (sectionId === "completed-table") {
      printIncompleteBtn.style.display = "none";
      printCompletedBtn.style.display = "inline-block";
    }
  }
}

// Function to print a specific table
function printTable(tableId, title) {
  const originalContents = document.body.innerHTML;
  let printContents = "";

  const tableContainer = document.getElementById(tableId);

  // Get the table itself from inside the container
  let tableElement = tableContainer
    ? tableContainer.querySelector("table")
    : null;

  if (!tableElement) {
    console.error(`Table not found for ID: ${tableId}`);
    return;
  }

  // Special case for the users table to remove the 'Action' column
  if (tableId === "users-section") {
    const clonedTable = tableElement.cloneNode(true);
    const rows = clonedTable.querySelectorAll("tr");
    rows.forEach((row) => {
      if (row.cells.length > 3) {
        row.deleteCell(3);
      }
    });
    printContents = clonedTable.outerHTML;
  } else {
    printContents = tableElement.outerHTML;
  }

  let fullTitle = title;
  const headingElement = document.querySelector("h2");
  if (
    headingElement &&
    headingElement.textContent.includes("Training Report for")
  ) {
    const reportUsername = headingElement.textContent.split(" for ")[1];
    fullTitle = `${title} - ${reportUsername}`;
  }

  document.body.innerHTML = `<h1>${fullTitle}</h1>${printContents}`;
  window.print();
  document.body.innerHTML = originalContents;
}

function confirmReset() {
  if (
    confirm(
      "Are you sure you want to reset the database? This will delete ALL custom users and training data"
    )
  ) {
    window.location.href = "/admin/reset_db";
  }
}

// Add event listeners for the reset button and initial section display
document.addEventListener("DOMContentLoaded", () => {
  const resetButton = document.getElementById("reset-button");
  if (resetButton) {
    resetButton.addEventListener("click", confirmReset);
  }

  // Check the new is_admin_page variable to determine which section to show by default
  if (typeof is_admin_page !== "undefined") {
    if (is_admin_page) {
      showSection("add-module-section");
    } else {
      showSection("incomplete-table");
    }
  } else if (window.location.pathname.startsWith("/admin/user_report")) {
    // Fallback for user reports if is_admin_page is not available
    showSection("incomplete-table");
  }
});
