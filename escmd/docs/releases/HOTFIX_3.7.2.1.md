# Hotfix 3.7.2.1 — ILM Remove Policy Fix

**Date**: February 26, 2026
**Version**: 3.7.2.1 (internal hotfix, no version bump)
**Status**: ✅ RESOLVED

---

## Overview

Two related issues were discovered and fixed immediately after the 3.7.2 release, both
affecting the `ilm remove-policy --file` command introduced in that release.

| # | Issue | Root Cause | Affected Indices |
|---|-------|-----------|-----------------|
| 1 | `AttributeError` on `remove_ilm_policy_from_indices` | Method was never added to `ElasticsearchClient` | All indices |
| 2 | `index_not_found_exception` (404) on removal | Two distinct sub-causes (see below) | Indices without ILM policies; data stream backing indices |

Both issues were resolved in `esclient.py` with no breaking changes to existing
functionality.

---

## Issue 1 — Missing Method

### Symptom

```
Error during ILM policy removal: 'ElasticsearchClient' object has no attribute
'remove_ilm_policy_from_indices'
```

### Root Cause

The 3.7.2 release updated `handlers/lifecycle_handler.py` to call
`es_client.remove_ilm_policy_from_indices()`, but the corresponding method was never
implemented in the `ElasticsearchClient` class. The symmetric method
`set_ilm_policy_for_indices()` already existed; its counterpart for removal was simply
omitted.

### Fix

Added `remove_ilm_policy_from_indices()` to `ElasticsearchClient` in `esclient.py`
(~95 lines, placed directly after `set_ilm_policy_for_indices()`).

**Method signature:**

```python
def remove_ilm_policy_from_indices(
    self,
    indices,
    dry_run=False,
    max_concurrent=5,
    continue_on_error=True,
):
```

**Features:**
- Accepts both string index names and dictionary objects in the `indices` list
- Concurrent processing via `ThreadPoolExecutor` (configurable worker count)
- Rich progress bars during execution
- Dry-run mode for safe previewing
- Pre-checks whether each index actually has an ILM policy before attempting removal
  (see Issue 2 below)
- Consistent return format matching `set_ilm_policy_for_indices()`

---

## Issue 2 — `index_not_found_exception` on Valid Indices

This manifested as two distinct sub-cases, both producing a 404 from Elasticsearch.

### Sub-case A — Index Has No ILM Policy

**Symptom:**
```
❌ Failed | NotFoundError(404, 'index_not_found_exception', ...)
```
for an index that exists but has never been assigned an ILM policy.

**Root Cause:**
Elasticsearch's `ilm.remove_policy` API returns `404 index_not_found_exception` when
called on an index with no ILM policy, even though the index itself exists. This is
misleading but expected API behaviour.

**Fix:**
Before calling `ilm.remove_policy`, the method now pre-checks via
`ilm.explain_lifecycle`. If the index is not managed (`managed: false`) or has no
policy name, it is returned as `skipped` with the message `"No ILM policy attached"`,
rather than being counted as a failure.

```python
explain_result = self.es.ilm.explain_lifecycle(index=index_name)
index_info = explain_result.get("indices", {}).get(index_name, {})

is_managed = index_info.get("managed", False)
current_policy = index_info.get("policy", None)

if not is_managed or not current_policy:
    return {"status": "skipped", "reason": "No ILM policy attached"}
```

### Sub-case B — Data Stream Backing Indices

**Symptom:**
```
❌ Failed | NotFoundError(404, 'index_not_found_exception', ...)
```
for indices like `.ds-iad41-c01-logs-agw-app-2026.02.12-000644` that both exist *and*
have an ILM policy (confirmed via `./escmd.py indice`).

**Root Cause:**
Data stream backing indices (`.ds-*` prefix) are managed differently by Elasticsearch.
The `ilm.remove_policy` API (`POST /{index}/_ilm/remove`) does not support them and
returns 404 despite the index being present and policy-managed.

**Fix:**
A fallback strategy was added inside `remove_policy_single()`. If `ilm.remove_policy`
raises `index_not_found_exception`, the method retries using `indices.put_settings` to
set `index.lifecycle.name` to `null`, which works for all index types including data
stream backing indices.

```python
try:
    self.es.ilm.remove_policy(index=index_name)
except Exception as ilm_error:
    if "index_not_found_exception" in str(ilm_error):
        # Fallback for data stream backing indices
        self.es.indices.put_settings(
            index=index_name,
            body={"index": {"lifecycle": {"name": None}}}
        )
    else:
        raise
```

**APIs used per index type:**

| Index Type | Primary API | Fallback API |
|-----------|------------|-------------|
| Regular indices | `POST /{index}/_ilm/remove` | — |
| Data stream backing indices (`.ds-*`) | `POST /{index}/_ilm/remove` (fails) | `PUT /{index}/_settings` |
| Index aliases | `POST /{index}/_ilm/remove` | `PUT /{index}/_settings` if needed |

---

## Return Format

All three outcomes are represented in the result dictionary:

```python
{
    "successful": [
        {
            "index": "logs-prod-001",
            "status": "success",
            "action": "removed_policy",
            "removed_policy": "30-days-default"
        }
    ],
    "skipped": [
        {
            "index": "unmanaged-index",
            "status": "skipped",
            "reason": "No ILM policy attached",
            "action": "remove_policy"
        }
    ],
    "failed": [
        {
            "index": "error-index",
            "status": "failed",
            "error": "connection timeout",
            "action": "remove_policy"
        }
    ],
    "total_processed": 3,
    "start_time": 1740566400.0,
    "end_time": 1740566402.3,
    "duration": 2.3
}
```

---

## Before and After

### Before

```bash
./escmd.py ilm remove-policy --file emergency/emergency_indices_iad41p9201

# Results:
❌ AttributeError: 'ElasticsearchClient' object has no attribute
   'remove_ilm_policy_from_indices'
```

After the method was added, running against a mixed list:

```bash
❌ .ds-iad41-c01-logs-agw-app-2026.02.12-000644 → index_not_found_exception
❌ unmanaged-index                               → index_not_found_exception
```

### After

```bash
./escmd.py ilm remove-policy --file emergency/emergency_indices_iad41p9201

✅ .ds-iad41-c01-logs-agw-app-2026.02.12-000644 → Success (removed policy)
✅ .ds-iad41-c01-logs-agw-app-2026.02.13-000645 → Success (removed policy)
✅ .ds-iad41-c01-logs-agw-app-2026.02.14-000646 → Success (removed policy)
⏭️  unmanaged-index                              → Skipped (No ILM policy attached)

Summary:
✅ Successful: 3
⏭️  Skipped:    1
❌ Failed:      0
```

---

## Usage Examples

```bash
# Standard file-based removal
./escmd.py ilm remove-policy --file indices.txt --yes

# Dry-run preview (always recommended first)
./escmd.py ilm remove-policy --file indices.txt --dry-run

# Higher concurrency for large index lists
./escmd.py ilm remove-policy --file indices.txt --max-concurrent 10 --yes

# Pattern-based removal (pre-existing, unaffected)
./escmd.py ilm remove-policy "temp-*" --yes
```

---

## Files Changed

| File | Change |
|------|--------|
| `esclient.py` | Added `remove_ilm_policy_from_indices()` method (~95 lines) |

No other files were modified. `handlers/lifecycle_handler.py` and
`cli/argument_parser.py` were already correct from the 3.7.2 release.

---

## Compatibility

✅ **100% backward compatible.** No existing methods, signatures, or return formats
were changed. This hotfix only adds previously missing functionality.

---

## Verification

```bash
# Syntax check
python3 -m py_compile esclient.py

# Quick functional test (dry-run — no cluster writes)
echo "test-index" > /tmp/test-indices.txt
./escmd.py ilm remove-policy --file /tmp/test-indices.txt --dry-run
```

Expected: progress bar completes, results summary appears, no `AttributeError` or
`index_not_found_exception` errors.