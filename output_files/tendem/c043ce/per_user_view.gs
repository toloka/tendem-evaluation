/**
 * Google Apps Script: Per-user filtered views by email (Column C) with admin bypass
 *
 * HOW IT WORKS
 * - Adds a "Customer View" custom menu on open.
 * - Non-admin users are automatically taken to a per-user view sheet that shows only rows
 *   where Column C equals their Google account email (via USEREMAIL()).
 * - Admin users can access the full dataset and use a menu action to jump to it.
 * - Filtering logic is implemented with a sheet formula and is not using the shared filter UI,
 *   ensuring independent views that do not overlap or conflict.
 *
 * NOTES
 * - This is for convenience/UX and does not enforce data access security. Viewers with access to
 *   the spreadsheet can still navigate to other sheets unless further restricted via protections.
 * - USEREMAIL() requires that viewers are signed in and may return blank for anonymous users.
 */

/*************************
 * CONFIGURATION CONSTANTS
 *************************/
const CONFIG = {
  DATA_SHEET_NAME: 'Data',       // Main data sheet name (update if different)
  VIEW_SHEET_NAME: 'My View',    // Per-user view sheet name
  EMAIL_COLUMN_INDEX: 3,         // Column C contains email (1=A, 2=B, 3=C, ...)
  ADMIN_EMAILS: [                // Add additional admin emails here (owner auto-detected when possible)
    // e.g. 'admin@example.com'
  ],
  PROTECT_VIEW_SHEET_FOR_NONADMINS: true // Prevent non-admins from editing the view sheet
};

/** Utility: Convert a positive column index (1-based) to column letter(s). */
function columnIndexToLetter(index) {
  let col = '';
  let n = index;
  while (n > 0) {
    const rem = (n - 1) % 26;
    col = String.fromCharCode(65 + rem) + col;
    n = Math.floor((n - 1) / 26);
  }
  return col;
}

/** Safe owner email retrieval (handles Shared Drives where owner may be null). */
function getSafeOwnerEmail_() {
  try {
    const file = DriveApp.getFileById(SpreadsheetApp.getActive().getId());
    const owner = file.getOwner();
    return owner ? owner.getEmail() : null;
  } catch (e) {
    return null;
  }
}

/** Returns true if the active user is an admin (owner or listed email). */
function isAdmin_() {
  try {
    const email = Session.getActiveUser().getEmail();
    const ownerEmail = getSafeOwnerEmail_();
    const adminList = CONFIG.ADMIN_EMAILS.map(e => e.toLowerCase());
    if (ownerEmail) adminList.push(ownerEmail.toLowerCase());
    if (!email) return false;
    return adminList.includes(email.toLowerCase());
  } catch (e) {
    return false;
  }
}

/** Ensures the per-user view sheet exists with the correct formula and protections. */
function ensureMyViewSheet_() {
  const ss = SpreadsheetApp.getActive();
  let viewSheet = ss.getSheetByName(CONFIG.VIEW_SHEET_NAME);
  const dataSheet = ss.getSheetByName(CONFIG.DATA_SHEET_NAME);
  if (!dataSheet) throw new Error(`Data sheet not found: ${CONFIG.DATA_SHEET_NAME}`);

  const lastCol = dataSheet.getLastColumn();
  const lastColLetter = columnIndexToLetter(lastCol);
  const admin = isAdmin_();

  // Create view sheet if missing
  if (!viewSheet) viewSheet = ss.insertSheet(CONFIG.VIEW_SHEET_NAME);

  // Admins can rebuild; non-admins should not modify protected content unless formula is missing
  if (admin) {
    // Clear only the content area (preserve user column widths and formatting)
    viewSheet.getRange('A2:' + lastColLetter + viewSheet.getMaxRows()).clearContent();

    // Header text
    viewSheet.getRange('A1').setValue('Per-user view (filtered by Column C = USEREMAIL())');

    // Build QUERY formula covering A1:<lastColLetter>
    const headerRows = 1; // First row in Data is header
    const emailColInQuery = CONFIG.EMAIL_COLUMN_INDEX; // QUERY uses Col1-based indexing
    const dataRange = `'${CONFIG.DATA_SHEET_NAME}'!A1:${lastColLetter}`;
    const formula = `=QUERY(${dataRange}, "select * where Col${emailColInQuery} = '" & USEREMAIL() & "'", ${headerRows})`;

    viewSheet.getRange(2, 1).setFormula(formula);
  } else if (viewSheet.getRange(2, 1).getFormula() === '') {
    // Allow non-admin to insert formula only if missing (in case protection is warning-only)
    const headerRows = 1;
    const emailColInQuery = CONFIG.EMAIL_COLUMN_INDEX;
    const dataRange = `'${CONFIG.DATA_SHEET_NAME}'!A1:${lastColLetter}`;
    const formula = `=QUERY(${dataRange}, "select * where Col${emailColInQuery} = '" & USEREMAIL() & "'", ${headerRows})`;
    viewSheet.getRange(2, 1).setFormula(formula);
  }

  // Optional: Protect the view sheet from non-admin edits
  if (CONFIG.PROTECT_VIEW_SHEET_FOR_NONADMINS) {
    let protections = viewSheet.getProtections(SpreadsheetApp.ProtectionType.SHEET);
    let protection = protections && protections.length ? protections[0] : viewSheet.protect();
    protection.setDescription('My View is protected to avoid conflicts. Admins may edit.');

    const ownerEmail = getSafeOwnerEmail_();
    const admins = CONFIG.ADMIN_EMAILS.slice();
    if (ownerEmail) admins.push(ownerEmail);

    const existingEditors = protection.getEditors().map(e => e.getEmail().toLowerCase());
    const targetEditors = admins.map(e => e.toLowerCase());
    const needUpdate = existingEditors.sort().join() !== targetEditors.sort().join();

    if (admins && admins.length) {
      protection.setWarningOnly(false);
      if (needUpdate) {
        protection.removeEditors(protection.getEditors());
        protection.addEditors(admins);
      }
    } else {
      protection.setWarningOnly(true);
    }
  }

  // Ensure view sheet has enough columns
  if (viewSheet.getMaxColumns() < lastCol) {
    viewSheet.insertColumnsAfter(viewSheet.getMaxColumns(), lastCol - viewSheet.getMaxColumns());
  }
}

/** Menu action: Apply My View (ensures view exists and activates it). */
function applyMyView_() {
  ensureMyViewSheet_();
  const ss = SpreadsheetApp.getActive();
  const viewSheet = ss.getSheetByName(CONFIG.VIEW_SHEET_NAME);
  if (viewSheet) ss.setActiveSheet(viewSheet);
}

/** Menu action: View All Data (Admin only). */
function viewAllDataAdmin_() {
  const ss = SpreadsheetApp.getActive();
  const dataSheet = ss.getSheetByName(CONFIG.DATA_SHEET_NAME);
  if (!dataSheet) {
    SpreadsheetApp.getActive().toast(`Data sheet not found: ${CONFIG.DATA_SHEET_NAME}`);
    return;
  }
  if (!isAdmin_()) {
    SpreadsheetApp.getActive().toast('Only admins can open the full dataset.');
    return;
  }
  ss.setActiveSheet(dataSheet);
}

/** Menu action: Refresh My View (forces recalculation). */
function refreshMyView_() {
  const ss = SpreadsheetApp.getActive();
  const viewSheet = ss.getSheetByName(CONFIG.VIEW_SHEET_NAME);
  if (!viewSheet) {
    applyMyView_();
    return;
  }
  const cell = viewSheet.getRange(2, 1);
  const currentFormula = cell.getFormula();
  if (currentFormula) {
    cell.setFormula('');
    Utilities.sleep(200);
    cell.setFormula(currentFormula);
  } else {
    applyMyView_();
  }
}

/** Adds custom menu and applies appropriate view on open. */
function onOpen(e) {
  try {
    const ui = SpreadsheetApp.getUi();
    ui.createMenu('Customer View')
      .addItem('Apply My View', 'applyMyView_')
      .addItem('Refresh My View', 'refreshMyView_')
      .addItem('View All Data (Admin)', 'viewAllDataAdmin_')
      .addToUi();

    const ss = SpreadsheetApp.getActive();
    if (isAdmin_()) {
      // Admins can maintain and see the main sheet
      ensureMyViewSheet_();
      const dataSheet = ss.getSheetByName(CONFIG.DATA_SHEET_NAME);
      if (dataSheet) ss.setActiveSheet(dataSheet);
    } else {
      // Non-admin users — open view sheet
      const viewSheet = ss.getSheetByName(CONFIG.VIEW_SHEET_NAME);
      if (!viewSheet) applyMyView_();
      else ss.setActiveSheet(viewSheet);
    }
  } catch (err) {
    SpreadsheetApp.getActive().toast('onOpen error: ' + err);
  }
}
