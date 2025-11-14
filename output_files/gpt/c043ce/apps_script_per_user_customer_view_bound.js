/*
Per-user Customer View for Google Sheets
- Adds an onOpen() trigger that automatically shows each user a sidebar containing only the rows
  where Column C equals that user's Google account email.
- Uses HTMLService to display a per-user view (this is per-user and does NOT modify/hide rows in the sheet,
  so multiple users can be in the sheet simultaneously without interfering with each other).
- Admins (defined in ADMIN_EMAILS) can still open the full sheet in the normal UI at any time.

Installation / Notes:
1) Add this script as a bound script to your spreadsheet (Extensions → Apps Script) and paste this file.
2) Update the ADMIN_EMAILS array below with your admin addresses.
3) Save the project. A simple onOpen() will try to run, but to ensure full behavior (authorization prompts,
   and consistent getActiveUser() behavior), create an *installable* onOpen trigger:
   - In the Apps Script editor: Triggers (left sidebar) → Add Trigger → select `onOpenInstalled` → Event: "On open".
   - This ensures the script runs with proper authorization and that Session.getActiveUser().getEmail() returns the
     caller's address in many domain settings.
4) Users will see a sidebar with their filtered customer rows. Admins will see the normal sheet and an admin menu.

Security / privacy:
- The sidebar view is rendered per-user — it does NOT change or hide rows in the main sheet. If a user wants
  a private copy, they can Export CSV from the sidebar.
- If you *must* hide rows inside the spreadsheet UI per-user (which is not document-isolated), we cannot do that
  safely because hidden rows are a document-level change visible to all editors/viewers.

Behavior summary:
- onOpen: if the user is in ADMIN_EMAILS, show admin menu; otherwise show per-user sidebar automatically if
  they have enabled Auto Open (default: true). Users can toggle Auto Open from the menu.
- Menu options: "Open My View", "Export My Data (CSV)", "Toggle Auto-Open", "Close My View".

How the code works:
- Reads the dataset from the sheet named DATA_SHEET_NAME (default: the first sheet). Data is read from row 1
  through last row; header row is considered row 1 and included at top of the view.
- Column C (index 3) is where the customer's email is expected. Matching is case-insensitive and trims whitespace.

Authors: ChatGPT (example), adapt freely.
*/

// ======== Configuration ========
const DATA_SHEET_NAME = null; // null => use active sheet (first sheet). Or set to exact sheet name like 'Customers'
const EMAIL_COLUMN_INDEX = 3;  // 1-based index for Column C
const ADMIN_EMAILS = [
  // Put admin emails here (full addresses). Admins will not get the per-user sidebar by default.
  'admin@example.com'
];
const DEFAULT_AUTO_OPEN = true; // whether non-admin users auto-open their view on open by default
// ===============================

/** Simple onOpen (may run as a simple trigger) */
function onOpen(e) {
  // Try to run installed-style onOpen behavior but don't require explicit trigger.
  try {
    onOpenInstalled(e);
  } catch (err) {
    // If something fails (authorization), still add a minimal menu so user can run actions manually.
    const ui = SpreadsheetApp.getUi();
    ui.createMenu('Customer View')
      .addItem('Open My View', 'showMyView')
      .addItem('Toggle Auto-Open', 'toggleAutoOpen')
      .addToUi();
  }
}

/** Recommended: create an *installable* onOpen trigger that calls this so full permissions are granted. */
function onOpenInstalled(e) {
  const ui = SpreadsheetApp.getUi();
  const userEmail = Session.getActiveUser().getEmail() || '';
  const isAdmin = ADMIN_EMAILS.indexOf(userEmail.toLowerCase()) !== -1;

  // Build menu
  const menu = ui.createMenu('Customer View')
    .addItem('Open My View', 'showMyView')
    .addItem('Export My Data (CSV)', 'exportMyData')
    .addItem('Close My View', 'closeSidebar')
    .addSeparator()
    .addItem('Toggle Auto-Open', 'toggleAutoOpen');

  if (isAdmin) {
    menu.addSeparator().addItem('Admin: Show Full Dataset Info', 'showAdminInfo');
  }

  menu.addToUi();

  // Auto-open for non-admins depending on preference
  if (!isAdmin) {
    const props = PropertiesService.getUserProperties();
    const pref = props.getProperty('CV_AUTO_OPEN');
    const autoOpen = pref === null ? DEFAULT_AUTO_OPEN : (pref === 'true');
    if (autoOpen) {
      // show sidebar for the current user
      showMyView();
    }
  }
}

/** Close sidebar */
function closeSidebar() {
  const html = HtmlService.createHtmlOutput('<script>window.top.postMessage({type:"closeSidebar"}, "*");</script>')
    .setHeight(10);
  SpreadsheetApp.getUi().showModalDialog(html, 'Closing sidebar');
}

/** Toggle user preference for auto-open */
function toggleAutoOpen() {
  const props = PropertiesService.getUserProperties();
  const pref = props.getProperty('CV_AUTO_OPEN');
  const current = pref === null ? DEFAULT_AUTO_OPEN : (pref === 'true');
  props.setProperty('CV_AUTO_OPEN', (!current).toString());
  SpreadsheetApp.getUi().alert('Auto-open personal view is now set to: ' + (!current));
}

/** Show admin info (instructions to access full dataset) */
function showAdminInfo() {
  const html = HtmlService.createHtmlOutput('<div style="font-family:Arial, sans-serif;line-height:1.4;padding:12px;">'
    + '<h3>Admin: Full dataset access</h3>'
    + '<ol>'
    + '<li>The document owner / admins can view the full sheet directly — do not use the sidebar to hide rows.</li>'
    + '<li>To export the entire dataset, use File → Download or use the sheet UI.</li>'
    + '<li>To temporarily disable the per-user sidebar for testing, remove or comment out the admin email(s) in the script's <code>ADMIN_EMAILS</code> array and redeploy, or open the script project and run <code>onOpenInstalled</code> as yourself.</li>'
    + '</ol>'
    + '<p><i>Note:</i> This per-user view is rendered in a sidebar for privacy and to avoid document-level changes.
      Hiding rows programmatically would affect all users and is not used.</p>'
    + '</div>')
    .setWidth(400);
  SpreadsheetApp.getUi().showModalDialog(html, 'Admin Info');
}

/** Entry point to show a user's filtered view in the sidebar */
function showMyView() {
  const userEmail = (Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  if (!userEmail) {
    SpreadsheetApp.getUi().alert('Could not determine your Google account email. Please make sure you are logged into an account with an email address available to Apps Script.');
    return;
  }

  const sheet = getDataSheet();
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Could not find the data sheet. Check DATA_SHEET_NAME in the script.');
    return;
  }

  // Read data
  const range = sheet.getDataRange();
  const values = range.getValues();
  if (values.length === 0) {
    SpreadsheetApp.getUi().alert('Sheet is empty.');
    return;
  }

  const headers = values[0];
  const body = values.slice(1);

  // Filter rows where Column C (EMAIL_COLUMN_INDEX) matches userEmail
  const matched = body.filter(function(row) {
    const cell = (row[EMAIL_COLUMN_INDEX - 1] || '').toString().trim().toLowerCase();
    return cell === userEmail;
  });

  // Build HTML
  const html = buildUserViewHtml(headers, matched, userEmail);
  const uiHtml = HtmlService.createHtmlOutput(html).setTitle('My Customer Rows');
  SpreadsheetApp.getUi().showSidebar(uiHtml);
}

/** Export the user's filtered rows as CSV (download) */
function exportMyData() {
  const userEmail = (Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  if (!userEmail) {
    SpreadsheetApp.getUi().alert('Could not determine your Google account email.');
    return;
  }

  const sheet = getDataSheet();
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const body = values.slice(1);
  const matched = body.filter(function(row) {
    const cell = (row[EMAIL_COLUMN_INDEX - 1] || '').toString().trim().toLowerCase();
    return cell === userEmail;
  });

  // Convert to CSV
  const csvRows = [headers].concat(matched).map(function(r){
    return r.map(function(c){
      if (c === null || c === undefined) return '';
      var s = c.toString();
      // Escape quotes
      if (s.indexOf(',') !== -1 || s.indexOf('"') !== -1 || s.indexOf('\n') !== -1) {
        s = '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    }).join(',');
  });
  const csv = csvRows.join('\n');

  // Serve CSV via HTML anchor download (since direct file creation may require Drive scopes)
  const html = HtmlService.createHtmlOutput('<html><body>'
    + '<a id="dlink" href="data:text/csv;charset=utf-8,' + encodeURIComponent(csv) + '" download="my_data.csv">Click here to download your CSV</a>'
    + '<script>document.getElementById("dlink").click();google.script.host.close();</script>'
    + '</body></html>')
    .setWidth(300).setHeight(100);
  SpreadsheetApp.getUi().showModalDialog(html, 'Download CSV');
}

/** Utility: get the data sheet object */
function getDataSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (DATA_SHEET_NAME && DATA_SHEET_NAME.length > 0) {
    return ss.getSheetByName(DATA_SHEET_NAME);
  }
  // No explicit name: use the first sheet (or active sheet)
  const sheet = ss.getSheets()[0];
  return sheet;
}

/** Build the HTML to display the header and matched rows. */
function buildUserViewHtml(headers, rows, userEmail) {
  // Limit max rows shown for performance safety (you can adjust this)
  const MAX_ROWS_DISPLAY = 1000;
  const safeRows = rows.slice(0, MAX_ROWS_DISPLAY);

  // Escape HTML helper
  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  let html = '<div style="font-family:Arial, sans-serif;padding:12px;">';
  html += '<h3>My customer rows for: ' + esc(userEmail) + '</h3>';
  html += '<p>Showing ' + rows.length + ' matching row(s)';
  if (rows.length > MAX_ROWS_DISPLAY) html += ' (first ' + MAX_ROWS_DISPLAY + ' shown)';
  html += '.</p>';

  html += '<div style="overflow:auto;max-height:520px;border:1px solid #ddd;padding:6px;background:#fff;">';

  // Table
  html += '<table border="0" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;">';
  // Header row
  html += '<thead><tr style="background:#f1f1f1;font-weight:700;">';
  headers.forEach(function(h){ html += '<th style="text-align:left;border-bottom:1px solid #ddd;">' + esc(h) + '</th>'; });
  html += '</tr></thead>';
  // Body
  html += '<tbody>';
  if (safeRows.length === 0) {
    html += '<tr><td colspan="' + headers.length + '">No matching rows found.</td></tr>';
  } else {
    safeRows.forEach(function(r){
      html += '<tr style="border-bottom:1px solid #eee;">';
      r.forEach(function(c){ html += '<td style="vertical-align:top;">' + esc(c) + '</td>'; });
      html += '</tr>';
    });
  }
  html += '</tbody>';
  html += '</table>';
  html += '</div>';

  html += '<div style="margin-top:10px;display:flex;gap:8px;">'
    + '<button onclick="google.script.run.exportMyData();google.script.host.close();">Export CSV</button>'
    + '<button onclick="google.script.host.close();">Close</button>'
    + '<button onclick="openAsSheet()">Open as new sheet</button>'
    + '</div>';

  // JS for "Open as new sheet" — this will create a new sheet tab in the spreadsheet containing the filtered rows.
  // WARNING: this creates a sheet tab visible to all users of the document. Use only if you understand that.
  html += '<script>
  function openAsSheet(){
    if(!confirm("This will create a new sheet tab with your filtered rows. The new sheet will be visible to everyone who can access this spreadsheet. Proceed?")) return;
    google.script.run.withSuccessHandler(function(){
      alert("Created sheet 'My Filtered View' (appended with your email).\nYou can delete it when finished.");
      google.script.host.close();
    }).createSheetFromFilteredRows();
  }
  window.addEventListener('message', function(e){ if(e.data && e.data.type=="closeSidebar") google.script.host.close(); }, false);
  </script>';

  html += '</div>';
  return html;
}

/** Create a new sheet tab named 'My Filtered View - user' and paste headers + matched rows there.
 * WARNING: the created sheet is visible to all document collaborators. */
function createSheetFromFilteredRows() {
  const userEmail = (Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  const sheet = getDataSheet();
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const body = values.slice(1);
  const matched = body.filter(function(row) {
    const cell = (row[EMAIL_COLUMN_INDEX - 1] || '').toString().trim().toLowerCase();
    return cell === userEmail;
  });

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const baseName = 'My Filtered View - ' + (userEmail || 'unknown');
  // Ensure unique name
  let name = baseName;
  let i = 1;
  while (ss.getSheetByName(name)) {
    name = baseName + ' (' + i + ')';
    i++;
  }
  const newSheet = ss.insertSheet(name);
  const output = [headers].concat(matched);
  if (output.length > 0) {
    newSheet.getRange(1,1,output.length, output[0].length).setValues(output);
  }
  // Auto-fit columns
  newSheet.autoResizeColumns(1, headers.length);
}

/*
Optional: admin helper to wipe any temporary sheets created by users that start with 'My Filtered View - '
Only run as admin.
*/
function adminCleanupTemporarySheets() {
  const userEmail = (Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  if (ADMIN_EMAILS.indexOf(userEmail) === -1) {
    SpreadsheetApp.getUi().alert('Only admins may run this.');
    return;
  }
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ss.getSheets();
  const prefix = 'My Filtered View - ';
  let deleted = 0;
  sheets.forEach(function(s){
    if (s.getName().indexOf(prefix) === 0) {
      ss.deleteSheet(s);
      deleted++;
    }
  });
  SpreadsheetApp.getUi().alert('Deleted ' + deleted + ' temporary sheet(s).');
}

// End of script
