#!/bin/bash
# Sample cron job script for escmd with logging
# This script demonstrates how to use escmd commands with logging for cron jobs

# Set the path to your escmd installation
ESCMD_DIR="/path/to/escmd"
cd "$ESCMD_DIR" || exit 1

# Set environment variables if needed
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${ESCMD_DIR}/logs/cron_job.log"
}

# Function to run escmd command with error handling
run_escmd_command() {
    local cmd="$1"
    local description="$2"

    log_message "Starting: $description"

    if eval "$cmd"; then
        log_message "SUCCESS: $description completed"
        return 0
    else
        local exit_code=$?
        log_message "ERROR: $description failed with exit code $exit_code"
        return $exit_code
    fi
}

# Main execution
main() {
    log_message "=== Starting escmd cron job execution ==="

    # Example 1: Run dangling metrics for US environment
    run_escmd_command \
        "./escmd.py dangling --metrics --env us --log-level INFO" \
        "Dangling metrics collection for US environment"

    # Example 2: Run dangling metrics for EU environment
    run_escmd_command \
        "./escmd.py dangling --metrics --env eu --log-level INFO" \
        "Dangling metrics collection for EU environment"

    # Example 3: Run storage analysis (uncomment if needed)
    # run_escmd_command \
    #     "./escmd.py storage --env prod --log-level INFO" \
    #     "Storage analysis for production environment"

    # Example 4: Run dangling cleanup (uncomment for actual cleanup - BE CAREFUL!)
    # run_escmd_command \
    #     "./escmd.py dangling --cleanup-all --env dev --dry-run --log-level DEBUG" \
    #     "Dangling cleanup (dry-run) for development environment"

    log_message "=== Completed escmd cron job execution ==="
}

# Execute main function
main

# Optional: Clean up old log files (older than 30 days)
find "${ESCMD_DIR}/logs" -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true

exit 0
