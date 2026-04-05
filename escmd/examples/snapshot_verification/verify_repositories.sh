#!/bin/bash

# Repository Verification Example Script
# This script demonstrates how to use the new snapshot repository verification feature

set -e

CLUSTER_NAME="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESCMD_PATH="$(cd "$SCRIPT_DIR/../.." && pwd)/escmd.py"

echo "==================================="
echo "Repository Verification Workflow"
echo "==================================="
echo "Cluster: $CLUSTER_NAME"
echo "Date: $(date)"
echo

# Function to print section headers
print_section() {
    echo
    echo "--- $1 ---"
    echo
}

# Function to handle errors gracefully
handle_error() {
    echo "❌ Error: $1"
    echo "Continuing with next step..."
    echo
}

print_section "Step 1: List Available Repositories"

echo "Checking what repositories are configured..."
if ! $ESCMD_PATH -l "$CLUSTER_NAME" repositories list; then
    handle_error "Failed to list repositories"
    exit 1
fi

print_section "Step 2: Get Repository List for Verification"

echo "Getting repository names for verification..."
REPO_JSON=$($ESCMD_PATH -l "$CLUSTER_NAME" repositories list --format json 2>/dev/null || echo "{}")

if [ "$REPO_JSON" = "{}" ]; then
    echo "⚠️  No repositories found - skipping verification"
    exit 0
fi

# Extract repository names from JSON
REPO_NAMES=$(echo "$REPO_JSON" | jq -r 'keys[]' 2>/dev/null || echo "")

if [ -z "$REPO_NAMES" ]; then
    echo "⚠️  No repository names could be extracted"
    exit 0
fi

echo "Found repositories:"
echo "$REPO_NAMES" | sed 's/^/  • /'
echo

print_section "Step 3: Verify Each Repository"

VERIFICATION_RESULTS=""
TOTAL_REPOS=0
SUCCESSFUL_REPOS=0

for repo in $REPO_NAMES; do
    echo "🔍 Verifying repository: $repo"
    TOTAL_REPOS=$((TOTAL_REPOS + 1))

    if $ESCMD_PATH -l "$CLUSTER_NAME" repositories verify "$repo"; then
        echo "✅ Repository '$repo' verification: SUCCESS"
        SUCCESSFUL_REPOS=$((SUCCESSFUL_REPOS + 1))
        VERIFICATION_RESULTS="${VERIFICATION_RESULTS}✅ $repo: SUCCESS\n"
    else
        echo "❌ Repository '$repo' verification: FAILED"
        VERIFICATION_RESULTS="${VERIFICATION_RESULTS}❌ $repo: FAILED\n"
    fi
    echo
done

print_section "Step 4: Verification Summary"

echo "Repository Verification Summary:"
echo "================================"
echo -e "$VERIFICATION_RESULTS"
echo "Total Repositories: $TOTAL_REPOS"
echo "Successfully Verified: $SUCCESSFUL_REPOS"
echo "Failed Verifications: $((TOTAL_REPOS - SUCCESSFUL_REPOS))"

if [ $SUCCESSFUL_REPOS -eq $TOTAL_REPOS ]; then
    echo
    echo "🎉 All repositories verified successfully!"
    exit 0
elif [ $SUCCESSFUL_REPOS -eq 0 ]; then
    echo
    echo "💥 All repository verifications failed!"
    echo "Action required: Check repository configuration and connectivity"
    exit 1
else
    echo
    echo "⚠️  Some repositories failed verification"
    echo "Action required: Investigate failed repositories"
    exit 1
fi

print_section "Step 5: Export Verification Results (JSON)"

echo "Exporting detailed verification results..."
REPORT_FILE="repository-verification-$(date +%Y%m%d-%H%M%S).json"

echo "{" > "$REPORT_FILE"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$REPORT_FILE"
echo "  \"cluster\": \"$CLUSTER_NAME\"," >> "$REPORT_FILE"
echo "  \"total_repositories\": $TOTAL_REPOS," >> "$REPORT_FILE"
echo "  \"successful_verifications\": $SUCCESSFUL_REPOS," >> "$REPORT_FILE"
echo "  \"failed_verifications\": $((TOTAL_REPOS - SUCCESSFUL_REPOS))," >> "$REPORT_FILE"
echo "  \"results\": [" >> "$REPORT_FILE"

FIRST_RESULT=true
for repo in $REPO_NAMES; do
    if [ "$FIRST_RESULT" = false ]; then
        echo "    ," >> "$REPORT_FILE"
    fi
    FIRST_RESULT=false

    echo -n "    {" >> "$REPORT_FILE"
    echo -n "\"repository\": \"$repo\", " >> "$REPORT_FILE"

    # Get detailed verification result
    if VERIFY_JSON=$($ESCMD_PATH -l "$CLUSTER_NAME" repositories verify "$repo" --format json 2>/dev/null); then
        echo -n "\"status\": \"success\", " >> "$REPORT_FILE"
        echo -n "\"details\": $VERIFY_JSON" >> "$REPORT_FILE"
    else
        echo -n "\"status\": \"failed\", " >> "$REPORT_FILE"
        echo -n "\"details\": {\"error\": \"Verification failed\"}" >> "$REPORT_FILE"
    fi
    echo -n "}" >> "$REPORT_FILE"
done

echo >> "$REPORT_FILE"
echo "  ]" >> "$REPORT_FILE"
echo "}" >> "$REPORT_FILE"

echo "✅ Verification report saved to: $REPORT_FILE"

print_section "Example Integration with Monitoring"

cat << 'EOF'
# Integration Examples:

# 1. Cron job for daily verification
# Add to crontab: 0 6 * * * /path/to/verify_repositories.sh production >> /var/log/repo-verify.log 2>&1

# 2. Nagios/Icinga check
# command_line: /path/to/verify_repositories.sh $ARG1$ && echo "OK - All repositories verified" || echo "CRITICAL - Repository verification failed"

# 3. Prometheus metrics export
# ./verify_repositories.sh production && echo "repository_verification_success 1" || echo "repository_verification_success 0"

# 4. Slack notification (add to end of script)
# if [ $? -eq 0 ]; then
#   curl -X POST -H 'Content-type: application/json' --data '{"text":"✅ All snapshot repositories verified for '$CLUSTER_NAME'"}' $SLACK_WEBHOOK
# else
#   curl -X POST -H 'Content-type: application/json' --data '{"text":"❌ Repository verification failed for '$CLUSTER_NAME'"}' $SLACK_WEBHOOK
# fi
EOF

echo
echo "Script completed: $(date)"
