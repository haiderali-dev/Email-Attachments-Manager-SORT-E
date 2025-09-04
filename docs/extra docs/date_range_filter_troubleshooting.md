# Date Range Filter Troubleshooting Guide

## Issue Description
The user reported: "date function not working, showing no emails" for the date range filter.

## Debugging Steps

### 1. Run the Debug Test
```bash
python test_date_filter_user.py
```

This will open the application with debug logging enabled. Follow the instructions in the console to test the date range filter.

### 2. Check Debug Output
When you use the date range filter, look for debug messages in the console like:
```
🔍 DEBUG: filter_emails called - Current filter: 'Date Range'
🔍 DEBUG: Date range widgets set to visible
🔍 DEBUG: Date Range Filter - Account ID: 1
🔍 DEBUG: Start Date: 2025-07-08, End Date: 2025-08-14
🔍 DEBUG: Found 12 emails with date range filter
```

### 3. Common Issues and Solutions

#### Issue 1: No Account Selected
**Symptoms**: No emails displayed, debug shows "Current account ID: None"
**Solution**: Select an email account from the dropdown first

#### Issue 2: Date Range Too Narrow
**Symptoms**: No emails displayed, but emails exist with "All" filter
**Solution**: Try a broader date range (e.g., last 30 days)

#### Issue 3: No Emails in Database
**Symptoms**: No emails displayed with any filter
**Solution**: Fetch emails first using the "📩 Fetch" button

#### Issue 4: Date Range Widgets Not Visible
**Symptoms**: Date pickers don't appear when "Date Range" is selected
**Solution**: Check if the filter dropdown is set to "Date Range"

### 4. Manual Testing Steps

1. **Select Account**: Choose an email account from the dropdown
2. **Check Initial State**: Verify emails are displayed with "All" filter
3. **Switch to Date Range**: Change filter dropdown to "Date Range"
4. **Verify Widgets**: Date pickers should become visible
5. **Set Date Range**: Choose start and end dates
6. **Check Results**: Emails should be filtered by date range

### 5. Database Verification

If the issue persists, check the database directly:

```sql
-- Check if emails exist
SELECT COUNT(*) FROM emails;

-- Check email dates
SELECT id, subject, date, account_id 
FROM emails 
ORDER BY date DESC 
LIMIT 5;

-- Check date range for specific account
SELECT MIN(DATE(date)), MAX(DATE(date)) 
FROM emails 
WHERE account_id = 1;
```

### 6. Expected Behavior

✅ **Working Correctly**:
- Date range widgets appear when "Date Range" is selected
- Emails are filtered by the selected date range
- Count label shows "X emails from [start_date] to [end_date]"
- Debug messages appear in console

❌ **Not Working**:
- No emails displayed with date range filter
- Date range widgets don't appear
- No debug messages in console

### 7. Reporting Issues

When reporting issues, please include:
1. Debug output from console
2. Steps to reproduce the issue
3. Account being used
4. Date range selected
5. Expected vs actual behavior

### 8. Quick Fixes

#### Fix 1: Reset Filter
```python
# In the application
filter_combo.setCurrentText("All")
filter_combo.setCurrentText("Date Range")
```

#### Fix 2: Refresh Emails
```python
# In the application
refresh_emails()
```

#### Fix 3: Check Account Selection
```python
# In the application
print(f"Current account ID: {current_account_id}")
```

### 9. Advanced Debugging

If the issue persists, run the comprehensive debug script:
```bash
python debug_date_filter.py
```

This will provide detailed information about:
- Database state
- Email data
- SQL queries
- UI functionality
- Account selection

### 10. Contact Information

If you continue to experience issues:
1. Run the debug scripts
2. Collect the console output
3. Document the exact steps to reproduce
4. Report the issue with all relevant information

## Technical Details

### Date Range Filter Implementation
- Uses SQL `BETWEEN` operator with `DATE()` function
- Filters by `DATE(e.date) BETWEEN %s AND %s`
- Supports any date range (start date to end date)
- Respects account isolation

### UI Components
- `QComboBox` for filter selection
- `QDateEdit` widgets for start and end dates
- `QLabel` for "From:" and "To:" labels
- Dynamic visibility based on filter selection

### Database Schema
```sql
emails table:
- id (PRIMARY KEY)
- account_id (FOREIGN KEY)
- date (DATETIME)
- subject (TEXT)
- sender (TEXT)
- body (TEXT)
- read_status (BOOLEAN)
- has_attachment (BOOLEAN)
``` 