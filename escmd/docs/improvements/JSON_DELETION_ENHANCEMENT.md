# JSON Deletion Enhancement

## Overview

This enhancement improves the JSON output format for index deletion operations in escmd to provide better support for automation and scripting.

## Problem Statement

Previously, when using `--format json` with `--delete` flag, the output was inconsistent:

1. Index information was printed first in JSON format
2. Deletion status was displayed separately in human-readable format
3. No structured way to determine deletion success/failure for automation

Example of old behavior:
```bash
./escmd.py indices .ds-rehydrated_ams02-c01-logs-igl-main-2025.09.25-000024 --delete -y --format json
[{'health': 'green', 'status': 'open', ...}]
✅ Successfully deleted 1 indices:
  • .ds-rehydrated_ams02-c01-logs-igl-main-2025.09.25-000024
```

## Solution

The enhancement provides a comprehensive JSON output that includes both the original index information and the deletion results in a single structured response.

### New JSON Output Structure

```json
{
  "indices": [
    {
      "index": "index-name",
      "health": "green",
      "status": "open",
      "pri": "1",
      "rep": "1",
      "docs.count": "1500000",
      "docs.deleted": "0",
      "store.size": "2.1gb",
      "pri.store.size": "1.1gb"
    }
  ],
  "deletion_requested": true,
  "deletion_results": {
    "status": "completed|cancelled|error",
    "successful_deletions": ["index1", "index2"],
    "failed_deletions": [
      {
        "index": "index3",
        "error": "error message"
      }
    ],
    "total_requested": 3,
    "message": "Optional status message"
  }
}
```

## Usage

The enhancement automatically activates when both `--format json` and `--delete` flags are used:

```bash
# Delete single index with JSON output
./escmd.py indices my-index --delete -y --format json

# Delete multiple indices matching pattern
./escmd.py indices "logs-2025.*" --delete -y --format json

# Interactive deletion (shows confirmation prompt)
./escmd.py indices old-indices --delete --format json
```

## Response Status Types

### 1. Completed (`status: "completed"`)
All operations finished, check individual results:
```json
{
  "deletion_results": {
    "status": "completed",
    "successful_deletions": ["index1", "index2"],
    "failed_deletions": [],
    "total_requested": 2
  }
}
```

### 2. Cancelled (`status: "cancelled"`)
User cancelled the operation:
```json
{
  "deletion_results": {
    "status": "cancelled",
    "message": "Operation cancelled by user",
    "total_requested": 1
  }
}
```

### 3. Error (`status: "error"`)
System error occurred during deletion:
```json
{
  "deletion_results": {
    "status": "error",
    "message": "Error during deletion: Connection timeout",
    "total_requested": 1,
    "successful_deletions": [],
    "failed_deletions": [{"error": "Connection timeout"}]
  }
}
```

## Automation Benefits

### 1. Single JSON Response
- No need to parse mixed human-readable and JSON output
- Complete information in one structured response

### 2. Programmatic Status Checking
```bash
# Check if deletion was successful
result=$(./escmd.py indices old-logs --delete -y --format json)
status=$(echo "$result" | jq -r '.deletion_results.status')

if [ "$status" = "completed" ]; then
    echo "Deletion completed successfully"
    # Check for any failures
    failures=$(echo "$result" | jq '.deletion_results.failed_deletions | length')
    if [ "$failures" -gt 0 ]; then
        echo "Some indices failed to delete"
        echo "$result" | jq '.deletion_results.failed_deletions'
    fi
elif [ "$status" = "cancelled" ]; then
    echo "Operation was cancelled"
    exit 1
elif [ "$status" = "error" ]; then
    echo "Error occurred during deletion"
    echo "$result" | jq -r '.deletion_results.message'
    exit 1
fi
```

### 3. Detailed Failure Analysis
```bash
# Extract failed deletions for retry logic
failed_indices=$(echo "$result" | jq -r '.deletion_results.failed_deletions[].index // empty')
for index in $failed_indices; do
    echo "Retry deletion for: $index"
done
```

### 4. Logging and Auditing
```python
import json
import subprocess

# Run deletion command
result = subprocess.run([
    './escmd.py', 'indices', 'logs-*', '--delete', '-y', '--format', 'json'
], capture_output=True, text=True)

# Parse and log results
data = json.loads(result.stdout)
deletion_results = data['deletion_results']

# Log successful deletions
for index in deletion_results.get('successful_deletions', []):
    logger.info(f"Successfully deleted index: {index}")

# Log failures
for failure in deletion_results.get('failed_deletions', []):
    logger.error(f"Failed to delete {failure.get('index', 'unknown')}: {failure.get('error', 'unknown error')}")
```

## Backward Compatibility

- Non-JSON format output remains unchanged
- JSON format without `--delete` flag works as before
- All existing functionality preserved

## Implementation Details

The enhancement modifies the `handle_indices` method in `IndexHandler` to:

1. Detect when both JSON format and deletion are requested
2. Capture deletion results from the ES client
3. Combine original index data with deletion status
4. Output single comprehensive JSON response

### Files Modified

- `handlers/index_handler.py`: Added `_handle_indices_deletion_json()` method
- Enhanced `handle_indices()` method for JSON deletion support

### Dependencies

- Uses existing `rich.prompt.Confirm` for user confirmation
- Leverages existing `es_client.delete_indices()` method
- Standard `json` library for output formatting

## Testing

Run the test suite to validate functionality:

```bash
python test_json_deletion.py
```

View example outputs:

```bash
python example_json_deletion_output.py
```

## Future Enhancements

1. **Batch Processing**: Support for processing large numbers of indices in batches
2. **Progress Reporting**: Add progress indicators for long-running deletions
3. **Dry Run Mode**: Preview what would be deleted without actual deletion
4. **Export Results**: Save deletion results to file for audit trails