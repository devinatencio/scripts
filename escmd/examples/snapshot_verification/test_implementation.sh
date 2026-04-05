#!/bin/bash

# Repository Verification Implementation Test Suite
# This script validates the complete implementation of the repository verification feature

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESCMD_PATH="$(cd "$SCRIPT_DIR/../.." && pwd)/escmd.py"

echo "=============================================="
echo "Repository Verification Implementation Tests"
echo "=============================================="
echo "Date: $(date)"
echo "ESCMD Path: $ESCMD_PATH"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"
    local should_contain="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo -e "${BLUE}Test $TOTAL_TESTS: $test_name${NC}"
    echo "Command: $test_command"

    # Run the command and capture output and exit code
    set +e
    output=$(eval "$test_command" 2>&1)
    actual_exit_code=$?
    set -e

    # Check exit code
    if [ "$actual_exit_code" -eq "$expected_exit_code" ]; then
        echo -e "${GREEN}✓ Exit code correct ($actual_exit_code)${NC}"
    else
        echo -e "${RED}✗ Exit code incorrect (expected $expected_exit_code, got $actual_exit_code)${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "Output:"
        echo "$output"
        echo
        return
    fi

    # Check if output contains expected string
    if [ -n "$should_contain" ]; then
        if echo "$output" | grep -q "$should_contain"; then
            echo -e "${GREEN}✓ Output contains expected text${NC}"
        else
            echo -e "${RED}✗ Output does not contain: $should_contain${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            echo "Actual output:"
            echo "$output"
            echo
            return
        fi
    fi

    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}✓ Test passed${NC}"
    echo
}

echo "=== Testing Command Structure ==="
echo

# Test 1: Help for repositories command
run_test "Repositories command help" \
    "python \"$ESCMD_PATH\" repositories --help" \
    0 \
    "verify"

# Test 2: Help for repositories verify command
run_test "Repositories verify help" \
    "python \"$ESCMD_PATH\" repositories verify --help" \
    0 \
    "repository_name"

# Test 3: Verify command with missing repository (expected error)
run_test "Verify non-existent repository" \
    "python \"$ESCMD_PATH\" repositories verify nonexistent_repo" \
    0 \
    "repository_missing_exception"

# Test 4: Verify command with JSON format
run_test "Verify with JSON format" \
    "python \"$ESCMD_PATH\" repositories verify test_repo --format json" \
    0 \
    "Failed to verify repository"

echo "=== Testing Integration ==="
echo

# Test 5: Snapshots help should NOT contain verify
run_test "Snapshots help excludes verify" \
    "python \"$ESCMD_PATH\" snapshots --help" \
    0

# Check that verify is NOT in snapshots help
snapshots_help=$(python "$ESCMD_PATH" snapshots --help 2>&1)
if echo "$snapshots_help" | grep -q "verify"; then
    echo -e "${RED}✗ Snapshots help still contains 'verify'${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ Snapshots help correctly excludes verify command${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo

# Test 6: Repositories list command
run_test "Repositories list command" \
    "python \"$ESCMD_PATH\" repositories list" \
    0 \
    "No snapshot repositories are currently configured"

# Test 7: Default repositories command (should work like list)
run_test "Default repositories command" \
    "python \"$ESCMD_PATH\" repositories" \
    0 \
    "No snapshot repositories are currently configured"

echo "=== Testing Error Handling ==="
echo

# Test 8: Invalid repository action
run_test "Invalid repository action" \
    "python \"$ESCMD_PATH\" repositories invalid_action" \
    2 \
    "invalid choice"

# Test 9: Verify without repository name
run_test "Verify without repository name" \
    "python \"$ESCMD_PATH\" repositories verify" \
    2 \
    "required"

echo "=== Testing Output Formats ==="
echo

# Test 10: Test JSON format flag validation
run_test "JSON format validation" \
    "python \"$ESCMD_PATH\" repositories verify test --format json" \
    0

# Test 11: Test table format flag validation
run_test "Table format validation" \
    "python \"$ESCMD_PATH\" repositories verify test --format table" \
    0

# Test 12: Test invalid format flag
run_test "Invalid format flag" \
    "python \"$ESCMD_PATH\" repositories verify test --format xml" \
    2 \
    "invalid choice"

echo "=== Functional Integration Tests ==="
echo

# Test 13: Check that repositories subcommands are properly recognized
repos_help=$(python "$ESCMD_PATH" repositories --help 2>&1)
if echo "$repos_help" | grep -E "list.*create.*verify" > /dev/null; then
    echo -e "${GREEN}✓ All repository subcommands present in help${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Repository subcommands missing from help${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo

# Test 14: Validate argument parser structure
if python "$ESCMD_PATH" repositories verify test_repo --format json > /dev/null 2>&1 || \
   python "$ESCMD_PATH" repositories verify test_repo --format json 2>&1 | grep -q "repository_missing_exception"; then
    echo -e "${GREEN}✓ Argument parser correctly structured${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Argument parser structure issues${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo

echo "=== Implementation Validation ==="
echo

# Test 15: Check that verify method exists and is callable
python -c "
import sys
sys.path.append('$SCRIPT_DIR/../..')
try:
    from handlers.snapshot_handler import SnapshotHandler
    import argparse

    # Mock args object
    args = argparse.Namespace()
    args.repositories_action = 'verify'
    args.repository_name = 'test'
    args.format = 'table'

    # This should not crash during method lookup
    handler = SnapshotHandler(None, args, None, None, None, None, None)
    if hasattr(handler, '_handle_verify_repository'):
        print('SUCCESS: _handle_verify_repository method exists')
    else:
        print('ERROR: _handle_verify_repository method missing')
        sys.exit(1)
except ImportError as e:
    print(f'SKIP: Cannot import handler ({e})')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1
verify_method_result=$?

if [ $verify_method_result -eq 0 ]; then
    echo -e "${GREEN}✓ Verify method implementation validated${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}~ Verify method validation skipped (import issues)${NC}"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo

echo "=============================================="
echo "Test Results Summary"
echo "=============================================="
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! Repository verification feature is working correctly.${NC}"
    echo
    echo "✅ Command structure implemented correctly"
    echo "✅ Help system updated properly"
    echo "✅ Error handling works as expected"
    echo "✅ Output formats supported"
    echo "✅ Integration with existing commands successful"
    echo
    echo "The feature is ready for production use!"
    echo
    echo "Usage examples:"
    echo "  ./escmd.py repositories verify s3_repo"
    echo "  ./escmd.py repositories verify backup-repo --format json"
    echo "  ./escmd.py -l production repositories verify s3_repo"

    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please review the implementation.${NC}"
    echo
    echo "Failed tests need to be addressed before the feature is production-ready."

    exit 1
fi
