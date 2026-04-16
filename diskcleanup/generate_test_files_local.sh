#!/bin/bash

# Local test file generator for diskcleanup validation
# Creates test files under ./test_data/ so no sudo or /var/log access needed

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

BASE="./test_data"

echo -e "${GREEN}=== Local Disk Cleanup Test File Generator ===${NC}"
echo "Creating test files under ${BASE}/"
echo

# Create a file with a given size (in bytes) and age (in days)
create_file() {
    local filepath="$1"
    local size_bytes="$2"
    local age_days="$3"

    mkdir -p "$(dirname "$filepath")"

    # Generate file of requested size
    dd if=/dev/zero of="$filepath" bs=1 count=0 seek="$size_bytes" 2>/dev/null

    # Backdate the file
    if [[ "$age_days" -gt 0 ]]; then
        local ts
        ts=$(date -j -v-${age_days}d "+%Y%m%d%H%M.%S" 2>/dev/null || \
             date -d "$age_days days ago" "+%Y%m%d%H%M.%S" 2>/dev/null)
        touch -t "$ts" "$filepath" 2>/dev/null || true
    fi

    printf "  %-60s  %8s  age: %2d days\n" "$filepath" "$(du -h "$filepath" | cut -f1)" "$age_days"
}

MB=$((1024 * 1024))
KB=1024

# ── 1. Main directory cleanup (extensions + age) ────────────────────────
echo -e "${GREEN}1. Files in directories_to_check (./test_data/var/log)${NC}"
echo -e "${YELLOW}   Should clean: old .tar.gz, .gz, and date-pattern files older than 30 days${NC}"
create_file "${BASE}/var/log/old_backup.tar.gz"        $((10 * MB))  35
create_file "${BASE}/var/log/recent_backup.tar.gz"     $((5  * MB))   5
create_file "${BASE}/var/log/compressed_log.gz"        $((8  * MB))  40
create_file "${BASE}/var/log/recent_compressed.gz"     $((3  * MB))  10
create_file "${BASE}/var/log/logfile-20240101"         $((6  * MB))  45
create_file "${BASE}/var/log/logfile-20241215"         $((4  * MB))   2

# ── 2. Monitored files (truncation) ────────────────────────────────────
echo
echo -e "${GREEN}2. Monitored files (should truncate when over size limit)${NC}"
create_file "${BASE}/var/log/mysqld.log"                       $((8  * MB))  10
create_file "${BASE}/var/log/mysql/mysql-slow.log"             $((15 * MB))  20
create_file "${BASE}/var/log/app/logstash-plain.log"           $((25 * MB))  25
create_file "${BASE}/var/log/kibana/kibana.log"                $((12 * MB))  15

# ── 3. Pattern-based directory cleanup ─────────────────────────────────
echo
echo -e "${GREEN}3. Pattern directories (haproxy: 10-day, kibana-1: 3-day)${NC}"
create_file "${BASE}/var/log/haproxy/haproxy-old.log"          $((5  * MB))  15
create_file "${BASE}/var/log/haproxy/haproxy-very-old.log"     $((8  * MB))  20
create_file "${BASE}/var/log/haproxy/haproxy-recent.log"       $((3  * MB))   2
create_file "${BASE}/var/log/haproxy/other-log.log"            $((2  * MB))  15

create_file "${BASE}/var/log/kibana-1/kibana-old.log"          $((6  * MB))   5
create_file "${BASE}/var/log/kibana-1/kibana-very-old.log"     $((8  * MB))  10
create_file "${BASE}/var/log/kibana-1/kibana-recent.log"       $((4  * MB))   1
create_file "${BASE}/var/log/kibana-1/other-log.log"           $((2  * MB))  10

# ── 4. ABRT crash directories ─────────────────────────────────────────
echo
echo -e "${GREEN}4. ABRT crash directories (age > 30 days, total size > 50 MB)${NC}"

create_abrt() {
    local name="$1" size_bytes="$2" age_days="$3"
    local dir="${BASE}/crash/abrt/${name}"
    mkdir -p "$dir"
    create_file "$dir/coredump"  "$size_bytes"  "$age_days"
    create_file "$dir/backtrace" "$KB"           "$age_days"

    # Backdate the directory itself
    if [[ "$age_days" -gt 0 ]]; then
        local ts
        ts=$(date -j -v-${age_days}d "+%Y%m%d%H%M.%S" 2>/dev/null || \
             date -d "$age_days days ago" "+%Y%m%d%H%M.%S" 2>/dev/null)
        touch -t "$ts" "$dir" 2>/dev/null || true
    fi
}

old35=$(date -j -v-35d "+%Y-%m-%d" 2>/dev/null || date -d "35 days ago" "+%Y-%m-%d")
old40=$(date -j -v-40d "+%Y-%m-%d" 2>/dev/null || date -d "40 days ago" "+%Y-%m-%d")
recent5=$(date -j -v-5d "+%Y-%m-%d" 2>/dev/null || date -d "5 days ago" "+%Y-%m-%d")
recent3=$(date -j -v-3d "+%Y-%m-%d" 2>/dev/null || date -d "3 days ago" "+%Y-%m-%d")

create_abrt "ccpp-${old35}-10-30-45-1234"       $((60 * MB))  35
create_abrt "python3-${old40}-15-20-30-5678"     $((70 * MB))  40
create_abrt "httpd-${recent5}-09-45-15-9999"     $((80 * MB))   5
create_abrt "mysqld-${old35}-14-10-25-3333"      $((10 * MB))  35
create_abrt "nginx-${recent3}-11-30-50-7777"     $((10 * MB))   3

# ── 5. Control files (should NOT be cleaned) ──────────────────────────
echo
echo -e "${GREEN}5. Control files (should be preserved)${NC}"
create_file "${BASE}/var/log/recent_important.log"     $((1 * MB))    1
create_file "${BASE}/var/log/recent_system.log"        $((1 * MB))    2

echo
echo -e "${GREEN}=== Done ===${NC}"
echo
echo -e "Run cleanup with:  ${YELLOW}./diskcleanup.py --config diskcleanup_test.yaml --dry-run${NC}"
echo -e "Live cleanup:      ${YELLOW}./diskcleanup.py --config diskcleanup_test.yaml${NC}"
echo -e "Clean up test dir: ${RED}rm -rf ./test_data${NC}"
