# ILM Policy Backup/Restore Workflow

This document provides visual workflows for the ILM backup and restore functionality.

## Overview Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ILM Policy Management                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Create indices list (text file)    │
        │  - One index per line               │
        │  - Simple and readable              │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │   ilm backup-policies               │
        │   --input-file indices.txt          │
        │   --output-file backup.json         │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Backup JSON created                │
        │  - Contains index names             │
        │  - Contains ILM policies            │
        │  - Contains current phase/state     │
        └─────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │ Remove Policies  │          │   Keep Backup    │
    │  (Maintenance)   │          │  (Documentation) │
    └──────────────────┘          └──────────────────┘
              │
              ▼
    ┌──────────────────┐
    │ Perform Tasks    │
    └──────────────────┘
              │
              ▼
    ┌──────────────────┐
    │ Restore Policies │
    └──────────────────┘
```

## Detailed Backup Workflow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. Prepare Input File               │
│                                     │
│ Options:                            │
│ • Text file (one index per line)    │
│ • JSON array                        │
│ • JSON object with "indices" key    │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 2. Run Backup Command               │
│                                     │
│ ./escmd.py ilm backup-policies \    │
│   --input-file indices.txt \        │
│   --output-file backup.json         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 3. For Each Index in File:         │
│                                     │
│ a. Query Elasticsearch for ILM info │
│ b. Extract policy name              │
│ c. Extract current phase/action     │
│ d. Record managed status            │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 4. Generate Backup JSON             │
│                                     │
│ {                                   │
│   "operation": "backup_policies",   │
│   "timestamp": "...",               │
│   "indices": [...]                  │
│ }                                   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 5. Display Results                  │
│                                     │
│ ✅ Successfully backed up: X        │
│ ⚠️  Errors encountered: Y           │
│ 📁 Backup saved to: backup.json    │
└─────────────────────────────────────┘
  │
  ▼
END
```

## Detailed Restore Workflow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. Load Backup JSON                 │
│                                     │
│ ./escmd.py ilm restore-policies \   │
│   --input-file backup.json          │
│   [--dry-run]                       │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 2. Parse Backup File                │
│                                     │
│ • Validate JSON structure           │
│ • Extract indices array             │
│ • Validate required fields          │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 3. For Each Index in Backup:       │
└─────────────────────────────────────┘
  │
  ├─────────────────────────────────┐
  │                                 │
  ▼                                 ▼
┌───────────────┐           ┌───────────────┐
│ Has Policy?   │           │ No Policy?    │
│ managed=true  │           │ managed=false │
└───────────────┘           └───────────────┘
  │                                 │
  ▼                                 ▼
┌───────────────┐           ┌───────────────┐
│ Apply Policy  │           │ Skip Index    │
│               │           │               │
│ PUT /{index}  │           │ (Unmanaged)   │
│  /_settings   │           └───────────────┘
│   lifecycle   │
└───────────────┘
  │
  ├──────┬──────┤
  │      │      │
  ▼      ▼      ▼
┌────┐ ┌────┐ ┌────┐
│ ✅  │ │ ⏭️  │ │ ❌  │
│ OK │ │Skip│ │Err │
└────┘ └────┘ └────┘
  │      │      │
  └──────┴──────┘
        │
        ▼
┌─────────────────────────────────────┐
│ 4. Display Summary                  │
│                                     │
│ ✅ Successfully restored: X         │
│ ⏭️  Skipped (no policy): Y         │
│ ❌ Errors encountered: Z            │
└─────────────────────────────────────┘
  │
  ▼
END
```

## Maintenance Window Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                    MAINTENANCE WORKFLOW                       │
└──────────────────────────────────────────────────────────────┘

BEFORE MAINTENANCE
═══════════════════
  │
  ▼
┌─────────────────────────────────────┐
│ Create indices list                 │
│ indices.txt                         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ Backup ILM policies                 │
│                                     │
│ ./escmd.py ilm backup-policies \    │
│   --input-file indices.txt \        │
│   --output-file backup-YYYYMMDD.json│
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ Verify backup created               │
│                                     │
│ cat backup-YYYYMMDD.json | jq      │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ Remove ILM policies (optional)      │
│                                     │
│ ./escmd.py ilm remove-policy \      │
│   --file indices.txt --yes          │
└─────────────────────────────────────┘
  │
  ▼
╔═════════════════════════════════════╗
║    PERFORM MAINTENANCE TASKS        ║
║                                     ║
║  • Reindex operations               ║
║  • Snapshot operations              ║
║  • Cluster maintenance              ║
║  • Index modifications              ║
╚═════════════════════════════════════╝
  │
  ▼

AFTER MAINTENANCE
═════════════════
  │
  ▼
┌─────────────────────────────────────┐
│ Preview restore (dry-run)           │
│                                     │
│ ./escmd.py ilm restore-policies \   │
│   --input-file backup-YYYYMMDD.json \│
│   --dry-run                         │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ Restore ILM policies                │
│                                     │
│ ./escmd.py ilm restore-policies \   │
│   --input-file backup-YYYYMMDD.json │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ Verify restoration                  │
│                                     │
│ ./escmd.py ilm errors               │
│ ./escmd.py ilm status               │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ MAINTENANCE COMPLETE ✅             │
└─────────────────────────────────────┘
```

## Pattern-Based vs File-Based Operations

```
┌──────────────────────────────────────────────────────────────┐
│              PATTERN-BASED OPERATIONS                         │
└──────────────────────────────────────────────────────────────┘

                    Use When:
    • You have a consistent naming pattern
    • You want to match multiple indices dynamically
    • Pattern changes over time

┌─────────────────────────────────────┐
│ ./escmd.py ilm remove-policy \      │
│   "logs-2024.*"                     │
└─────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Elasticsearch Query   │
    │ • Matches pattern     │
    │ • Returns index list  │
    └───────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Process all matches   │
    └───────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│               FILE-BASED OPERATIONS                           │
└──────────────────────────────────────────────────────────────┘

                    Use When:
    • You have specific indices to manage
    • You need precise control
    • You want to track/audit specific indices

┌─────────────────────────────────────┐
│ indices.txt                         │
│ ─────────────                       │
│ index-1                             │
│ index-2                             │
│ index-3                             │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ ./escmd.py ilm remove-policy \      │
│   --file indices.txt                │
└─────────────────────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Read file directly    │
    │ • Known indices       │
    │ • No wildcards        │
    └───────────────────────┘
                │
                ▼
    ┌───────────────────────┐
    │ Process exact list    │
    └───────────────────────┘
```

## State Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Index ILM States                           │
└──────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │ Index Created   │
    │ (No ILM Policy) │
    └─────────────────┘
            │
            │ set-policy
            ▼
    ┌─────────────────┐
    │  ILM Managed    │
    │  Policy: X      │
    │  Phase: hot     │
    └─────────────────┘
            │
            │ backup-policies
            │ (snapshot state)
            ▼
    ┌─────────────────┐
    │  Backup Exists  │
    │  backup.json    │
    └─────────────────┘
            │
            ├─────────────────────┐
            │                     │
            │ remove-policy       │ restore-policies
            ▼                     ▼
    ┌─────────────────┐   ┌─────────────────┐
    │  ILM Removed    │   │  ILM Restored   │
    │  (Unmanaged)    │   │  Policy: X      │
    └─────────────────┘   │  Phase: hot     │
            │             └─────────────────┘
            │                     │
            │ restore-policies    │
            └─────────────────────┘
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                        Data Flow                              │
└──────────────────────────────────────────────────────────────┘

INPUT FILES                ESCMD                   ELASTICSEARCH
───────────               ──────                   ─────────────

indices.txt ──────┐
                  │
   OR             ├──> Read ──> Parse ──> Query ──> /_ilm/
                  │      │         │        │          explain
indices.json ─────┘      │         │        │
                         │         │        ▼
                         │         │   ┌─────────┐
                         │         │   │ Policy  │
                         │         │   │ Phase   │
                         │         │   │ Action  │
                         │         │   └─────────┘
                         │         │        │
                         │         ▼        ▼
                         │    ┌─────────────────┐
                         │    │ Build Response  │
                         │    └─────────────────┘
                         │             │
                         ▼             ▼
                    ┌──────────────────────┐
                    │   backup.json        │
                    │   ─────────────      │
                    │   {                  │
                    │     "indices": [     │
                    │       {              │
                    │         "index": "X",│
                    │         "policy": "Y"│
                    │       }              │
                    │     ]                │
                    │   }                  │
                    └──────────────────────┘
                             │
                             │ (Later)
                             ▼
                    ┌──────────────────────┐
                    │ restore-policies     │
                    └──────────────────────┘
                             │
                             ▼
                         Parse JSON
                             │
                             ▼
                    ┌──────────────────────┐
                    │ For each index:      │
                    │ PUT /{index}         │
                    │   /_settings         │
                    │     lifecycle.name   │
                    └──────────────────────┘
                             │
                             ▼
                        Elasticsearch
                     (Policies Restored)
```

## Error Handling Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     Error Handling                            │
└──────────────────────────────────────────────────────────────┘

    Process Index ──────┬────────┬────────┐
                        │        │        │
                        ▼        ▼        ▼
                   ┌────────┐ ┌────┐ ┌────────┐
                   │Success │ │Skip│ │ Error  │
                   └────────┘ └────┘ └────────┘
                        │        │        │
                        │        │        ├─> Log Error
                        │        │        │
                        │        │        ├─> Continue?
                        │        │        │   (Don't stop)
                        │        │        │
                        └────────┴────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ Collect all  │
                        │ results      │
                        └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ Display      │
                        │ Summary:     │
                        │ ✅ Success: X│
                        │ ⏭️  Skip: Y  │
                        │ ❌ Error: Z  │
                        └──────────────┘
```

## Best Practices Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Best Practices                             │
└──────────────────────────────────────────────────────────────┘

ALWAYS:                          RECOMMENDED:
───────                          ────────────
  │                                  │
  ├─> Use --dry-run first            ├─> Name backups with dates
  │                                  │   backup-YYYYMMDD.json
  ├─> Verify backup exists           │
  │   before removing                ├─> Keep multiple backups
  │                                  │
  ├─> Test on non-prod first         ├─> Document what/when
  │                                  │
  └─> Check for errors after         └─> Automate with scripts
      ./escmd.py ilm errors


WORKFLOW:
─────────

Plan ──> Dry-Run ──> Backup ──> Execute ──> Verify ──> Document

  │         │          │           │          │           │
  │         │          │           │          │           │
  ▼         ▼          ▼           ▼          ▼           ▼
Review   Preview   Save State   Apply    Check     Keep Records
Goals    Changes   (JSON)       Changes  Results   (Audit Trail)
```
