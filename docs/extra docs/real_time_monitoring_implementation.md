# Real-Time Email Monitoring Implementation

## Overview

This document describes the implementation of real-time email monitoring functionality that automatically fetches new emails while the application is running, while manual sync operations fetch only old emails from before the application was launched.

## Key Features

### 1. **Dual Email Fetching Strategy**
- **Manual Sync**: Fetches old emails from specified time periods (before application was running)
- **Real-Time Monitoring**: Automatically fetches new emails that arrive while the application is running

### 2. **Smart Email Classification**
- **Old Emails**: Emails received before the application was launched (fetched via manual sync)
- **New Emails**: Emails received while the application is running (fetched automatically)

### 3. **Configurable Monitoring**
- Enable/disable real-time monitoring
- Configurable check intervals (60 seconds to 1 hour)
- Automatic error recovery and restart

## Implementation Details

### 1. Configuration Changes

#### `config/settings.py`
```python
DEFAULT_CONFIG = {
    # ... existing config ...
    'real_time_monitoring': True,
    'monitoring_interval': 30  # 30 seconds
}
```

#### `config.json`
```json
{
    "real_time_monitoring": true,
    "monitoring_interval": 30
}
```

### 2. New Worker Classes

#### `RealTimeEmailMonitor` Class
- **Location**: `workers/email_fetch_worker.py`
- **Purpose**: Background thread for continuous email monitoring
- **Features**:
  - Runs in separate thread to avoid blocking UI
  - Configurable monitoring intervals
  - Automatic error recovery
  - Graceful shutdown

#### Enhanced `EmailFetchWorker` Class
- **New Method**: `fetch_new_emails_since(timestamp)`
- **Purpose**: Fetch only emails since a specific timestamp
- **Features**:
  - Uses IMAP SINCE filter for efficient server-side filtering
  - Avoids duplicate email processing
  - Updates last sync timestamp

### 3. UI Integration

#### Email Management Window
- **Real-time monitoring starts automatically** when application launches
- **Restarts monitoring** when switching between accounts
- **Stops monitoring** when closing application or logging out
- **Status updates** in status bar for monitoring activity

#### Settings Dialog
- **Real-Time Monitoring Section**:
  - Enable/disable checkbox
  - Monitoring interval configuration (60-3600 seconds)
  - Helpful tooltips and descriptions

#### Sync Dialog
- **Updated help text** explaining that sync only fetches old emails
- **Clear distinction** between manual sync and automatic monitoring

## How It Works

### 1. Application Startup
```
1. Application starts
2. User account is loaded
3. Real-time monitoring starts automatically
4. Auto-sync runs once to fetch today's emails
5. Monitoring continues in background
```

### 2. Real-Time Monitoring Loop
```
1. Get last sync time from database
2. Check for new emails since last sync
3. Process any new emails found
4. Update last sync timestamp
5. Sleep for configured interval
6. Repeat until application closes
```

### 3. Manual Sync Process
```
1. User clicks "Sync" button
2. Sync dialog opens with date range options
3. User selects time period (Today, Weekly, Monthly, Custom)
4. Only emails from that period are fetched
5. New emails continue to be monitored automatically
```

### 4. Email Processing Flow
```
1. Connect to IMAP server
2. Use SINCE filter to get emails from specific date
3. Check if email already exists in database
4. If new: Insert email and apply auto-tags
5. If existing: Only apply auto-tags (no re-download)
6. Update last sync timestamp
```

## Configuration Options

### Real-Time Monitoring Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `real_time_monitoring` | `true` | boolean | Enable/disable real-time monitoring |
| `monitoring_interval` | `30` | 60-3600 | Check interval in seconds |

### Sync Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `max_emails_per_fetch` | `100` | 10-1000 | Maximum emails per sync operation |

## User Experience

### 1. **Automatic Operation**
- No user intervention required for new emails
- Seamless background monitoring
- Status updates in status bar

### 2. **Manual Control**
- Users can disable real-time monitoring in settings
- Manual sync for old emails with date range options
- Clear distinction between old and new email fetching

### 3. **Performance Benefits**
- Efficient server-side filtering with IMAP SINCE
- Avoids duplicate email processing
- Configurable intervals to balance responsiveness and resource usage

## Error Handling

### 1. **Network Errors**
- Automatic retry after 1 minute
- Continues monitoring even after errors
- Graceful degradation

### 2. **Database Errors**
- Individual email processing errors don't stop monitoring
- Transaction rollback for failed operations
- Detailed error logging

### 3. **Application Shutdown**
- Graceful thread termination
- Proper cleanup of resources
- No orphaned processes

## Testing

### Test Script
- **File**: `test_real_time_monitoring.py`
- **Purpose**: Verify implementation structure
- **Features**:
  - Configuration validation
  - Class structure testing
  - Signal verification

### Manual Testing
1. Start application
2. Verify real-time monitoring starts
3. Send test emails to account
4. Verify emails appear automatically
5. Use manual sync to fetch old emails
6. Verify no duplicates are created

## Benefits

### 1. **User Experience**
- Immediate access to new emails
- No need to manually check for updates
- Clear separation of old vs new email fetching

### 2. **Performance**
- Efficient server-side filtering
- Reduced bandwidth usage
- Configurable resource usage

### 3. **Reliability**
- Automatic error recovery
- Graceful shutdown handling
- No data loss during errors

### 4. **Flexibility**
- Configurable monitoring intervals
- Enable/disable options
- Clear user control

## Future Enhancements

### 1. **Advanced Filtering**
- Filter by email size
- Filter by sender domain
- Custom filtering rules

### 2. **Notification System**
- Desktop notifications for new emails
- Sound alerts
- Email preview in notifications

### 3. **Performance Optimization**
- Batch processing for multiple emails
- Connection pooling
- Caching strategies

### 4. **Monitoring Dashboard**
- Real-time statistics
- Monitoring status display
- Performance metrics

## Troubleshooting

### Common Issues

1. **Monitoring not starting**
   - Check `real_time_monitoring` setting
   - Verify account credentials
   - Check database connection

2. **High resource usage**
   - Increase monitoring interval
   - Reduce max emails per fetch
   - Check for network issues

3. **Duplicate emails**
   - Verify email UID handling
   - Check database constraints
   - Review sync timestamps

### Debug Information
- Monitor console output for error messages
- Check database `last_sync` timestamps
- Verify IMAP connection settings

## Conclusion

The real-time email monitoring implementation provides a seamless user experience by automatically fetching new emails while maintaining efficient manual sync for old emails. The dual approach ensures users get immediate access to new emails while maintaining control over historical email fetching.
