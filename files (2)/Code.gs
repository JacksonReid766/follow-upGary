// ─────────────────────────────────────────────────────────────
//  FIBER SALES — Lead Intake Backend
//  Paste this entire file into Google Apps Script
//  Extensions → Apps Script → paste → save → deploy
// ─────────────────────────────────────────────────────────────

// ── REPLACE with your Google Sheet ID (from the URL) ──
const SHEET_ID = '1DkuvQZbLDF4RyZkBt1VwfvOW0GYfzDxO0jHLQWn-6WI';
// ── Tab names — must match exactly ──
const WARM_LEADS_TAB   = 'Warm Leads';
const CUSTOMERS_TAB    = 'Customers';

// Column headers for each tab
const LEAD_HEADERS     = ['Timestamp', 'First Name', 'Last Name', 'Phone', 'Address', 'Notes', 'Referred By', 'Status', 'Last Contacted'];
const CUSTOMER_HEADERS = ['Timestamp', 'First Name', 'Last Name', 'Phone', 'Address', 'Notes', 'Status', 'Referral Count'];


// ─────────────────────────────────────────────────────────────
//  Main entry point — handles POST from the form
// ─────────────────────────────────────────────────────────────
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const ss   = SpreadsheetApp.openById(SHEET_ID);

    if (data.type === 'lead') {
      writeToTab(ss, WARM_LEADS_TAB, LEAD_HEADERS, [
        data.timestamp,
        data.firstName,
        data.lastName,
        data.phone,
        data.address,
        data.notes,
        data.referredBy,
        'New',          // Status
        ''              // Last Contacted
      ]);
    } else if (data.type === 'customer') {
      writeToTab(ss, CUSTOMERS_TAB, CUSTOMER_HEADERS, [
        data.timestamp,
        data.firstName,
        data.lastName,
        data.phone,
        data.address,
        data.notes,
        'Active',       // Status
        0               // Referral Count
      ]);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}


// ─────────────────────────────────────────────────────────────
//  Writes a row to the correct tab, creating it if needed
// ─────────────────────────────────────────────────────────────
function writeToTab(ss, tabName, headers, row) {
  let sheet = ss.getSheetByName(tabName);

  // Create the tab and add headers if it doesn't exist yet
  if (!sheet) {
    sheet = ss.insertSheet(tabName);
    sheet.appendRow(headers);

    // Style the header row
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#1a472a');
    headerRange.setFontColor('#ffffff');
    sheet.setFrozenRows(1);
  }

  sheet.appendRow(row);
}


// ─────────────────────────────────────────────────────────────
//  Utility — adds a referral lead directly from agent code
//  Call this when a customer texts a referral name + number
// ─────────────────────────────────────────────────────────────
function addReferralLead(firstName, lastName, phone, referredBy, notes) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  writeToTab(ss, WARM_LEADS_TAB, LEAD_HEADERS, [
    new Date().toISOString(),
    firstName,
    lastName,
    phone,
    '',
    notes || '',
    referredBy,
    'New',
    ''
  ]);
}


// ─────────────────────────────────────────────────────────────
//  Test function — run this manually to verify sheet access
// ─────────────────────────────────────────────────────────────
function testWrite() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  writeToTab(ss, WARM_LEADS_TAB, LEAD_HEADERS, [
    new Date().toISOString(),
    'Test',
    'User',
    '6155550100',
    '123 Main St',
    'Test entry — delete me',
    '',
    'New',
    ''
  ]);
  Logger.log('Test write successful');
}
