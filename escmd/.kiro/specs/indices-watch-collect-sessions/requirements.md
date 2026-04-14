# Requirements Document

## Introduction

`indices-watch-collect-sessions` extends the existing index-watch collection system to support multiple distinct collection sessions per day per cluster. Currently, all runs on the same day for the same cluster land in a single `<YYYY-MM-DD>` directory, mixing data from unrelated collection windows. This feature introduces a **session** layer beneath the date directory, gives each session a short human-readable identifier, and provides an interactive prompt at startup that lets the user either join an existing session (append samples to it) or start a new one (fresh directory). The same session logic applies to the `--collect` flag on the `es-top` / `top` command when no explicit `--collect-dir` is given.

---

## Glossary

- **Session**: A single, named collection run stored in its own subdirectory under the date folder. A session directory holds a `run.json` metadata file and one or more timestamped sample files.
- **Session_ID**: A short, filesystem-safe identifier for a session, composed of a UTC wall-clock time prefix and an optional user-supplied label (e.g. `1430`, `1430-load-test`).
- **Session_Directory**: The directory `~/.escmd/index-watch/<cluster>/<YYYY-MM-DD>/<session_id>/` that contains all sample files and the `run.json` for one session.
- **Date_Directory**: The directory `~/.escmd/index-watch/<cluster>/<YYYY-MM-DD>/` that groups all sessions for a given cluster on a given UTC date.
- **Session_Picker**: The interactive terminal prompt shown at startup when the user has not supplied an explicit output directory and at least one session already exists for the current cluster and date.
- **Session_Registry**: The ordered list of existing sessions discovered by scanning the Date_Directory at startup.
- **Collector**: The component that writes sample files and run metadata; used by both `indices-watch-collect` and the `es-top --collect` path.
- **Base_Dir**: The root watch directory, defaulting to `~/.escmd/index-watch/` and overridable via the `ESCMD_INDEX_WATCH_DIR` environment variable.
- **Run_Metadata**: The `run.json` file written at the start of each session recording cluster, interval, start time, label, and schema version.

---

## Requirements

### Requirement 1: Session Directory Structure

**User Story:** As an operator, I want each collection run to be stored in its own subdirectory so that data from different runs on the same day is never mixed together.

#### Acceptance Criteria

1. THE Collector SHALL store all sample files and `run.json` for a session inside a Session_Directory whose path is `<Base_Dir>/<cluster>/<YYYY-MM-DD>/<session_id>/`.
2. THE Collector SHALL derive the Session_ID from the UTC wall-clock time at session start, formatted as `HHMM` (zero-padded, 24-hour), producing identifiers such as `0930` or `1445`.
3. WHERE the user supplies a `--label` argument, THE Collector SHALL append the sanitized label to the time prefix with a hyphen separator, producing identifiers such as `1430-load-test`.
4. THE Collector SHALL sanitize the label by replacing any character that is not alphanumeric, a hyphen, or an underscore with an underscore, and truncating the result to 40 characters before appending.
5. IF a Session_Directory with the computed Session_ID already exists at startup, THEN THE Collector SHALL append a numeric suffix (`-2`, `-3`, …) to the Session_ID until a non-conflicting name is found.
6. THE Collector SHALL create the Session_Directory with `mkdir -p` semantics before writing any files.

---

### Requirement 2: Session Picker Prompt

**User Story:** As an operator, I want to be asked whether to join an existing session or start a new one when I run `indices-watch-collect` on a day that already has sessions, so that I can choose the right context without having to remember directory paths.

#### Acceptance Criteria

1. WHEN `indices-watch-collect` starts and the Date_Directory for the current cluster and UTC date contains at least one existing Session_Directory, THE Session_Picker SHALL display the list of existing sessions and prompt the user to join one or start a new session.
2. THE Session_Picker SHALL display each existing session's Session_ID, its start time (from `run.json`), its sample count (number of non-`run.json` JSON files), and its label (if present) in a numbered list.
3. WHEN the user selects an existing session, THE Collector SHALL use that session's Session_Directory as the output directory and append new sample files to it without overwriting existing files.
4. WHEN the user selects "new session", THE Collector SHALL create a fresh Session_Directory using the current UTC time as described in Requirement 1.
5. WHEN `indices-watch-collect` is invoked with `--output-dir` pointing to an explicit path, THE Session_Picker SHALL NOT be shown and THE Collector SHALL write directly to the specified path.
6. WHEN `indices-watch-collect` is invoked with `--new-session`, THE Session_Picker SHALL NOT be shown and THE Collector SHALL always create a fresh Session_Directory.
7. WHEN `indices-watch-collect` is invoked with `--join-latest`, THE Session_Picker SHALL NOT be shown and THE Collector SHALL automatically join the most recently started existing session for the current cluster and date; IF no existing session exists, THE Collector SHALL create a new one.
8. IF the Date_Directory contains no existing sessions, THE Session_Picker SHALL NOT be shown and THE Collector SHALL create a new Session_Directory automatically.
9. WHEN the Session_Picker is shown in a non-interactive environment (stdin is not a TTY), THE Collector SHALL behave as if `--new-session` was passed and log a notice to stderr.

---

### Requirement 3: Run Metadata for Sessions

**User Story:** As an operator, I want each session's `run.json` to record when the session started and what label was given, so that I can identify sessions in reports and tooling.

#### Acceptance Criteria

1. THE Collector SHALL write a `run.json` file into the Session_Directory at the start of every new session containing: `kind`, `schema_version`, `cluster`, `session_id`, `label` (null if not provided), `started_at` (UTC ISO-8601), `interval_seconds`, `duration_seconds`, and `pattern`.
2. WHEN joining an existing session, THE Collector SHALL NOT overwrite the existing `run.json`; the original session metadata SHALL be preserved.
3. THE `run.json` schema_version for sessions SHALL be `2` to distinguish session-aware metadata from the legacy version-1 format.

---

### Requirement 4: `es-top --collect` Session Integration

**User Story:** As an operator using `es-top --collect`, I want the same session logic to apply so that my live-monitoring snapshots are organized into sessions just like `indices-watch-collect` runs.

#### Acceptance Criteria

1. WHEN `es-top` starts with `--collect` and no `--collect-dir` is given, THE Collector SHALL apply the same session directory resolution logic as `indices-watch-collect`, including showing the Session_Picker if existing sessions are present.
2. WHEN `es-top` starts with `--collect` and `--collect-dir` is given, THE Collector SHALL write directly to the specified path without session logic, preserving the existing behavior.
3. WHEN `es-top` starts with `--collect` and `--new-session` is given, THE Collector SHALL skip the Session_Picker and create a fresh Session_Directory.
4. WHEN `es-top` starts with `--collect` and `--join-latest` is given, THE Collector SHALL automatically join the most recently started existing session without prompting.
5. THE `--new-session`, `--join-latest`, and `--label` arguments SHALL be accepted by the `es-top` / `top` command parser and SHALL have no effect when `--collect` is not set.

---

### Requirement 5: `indices-watch-report` Compatibility

**User Story:** As an operator, I want `indices-watch-report` to work with both the new session layout and the legacy flat date-directory layout, so that existing collected data is not broken.

#### Acceptance Criteria

1. WHEN `--dir` is supplied to `indices-watch-report`, THE Report_Reader SHALL load samples from that exact directory regardless of whether it is a Session_Directory or a legacy Date_Directory.
2. WHEN `--dir` is not supplied, `--session` is not supplied, the resolved Date_Directory contains more than one Session_Directory, and stdin is a TTY, THE Report_Reader SHALL display the list of available sessions and prompt the user to select one interactively before loading samples.
3. WHEN `--dir` is not supplied, `--session` is not supplied, the resolved Date_Directory contains more than one Session_Directory, and stdin is not a TTY, THE Report_Reader SHALL load samples from the most recently started session and log a notice to stderr identifying the selected session.
4. WHEN `--dir` is not supplied, `--session` is not supplied, and the resolved Date_Directory contains exactly one Session_Directory, THE Report_Reader SHALL load samples from that session without prompting.
5. WHEN `--dir` is not supplied and the resolved Date_Directory contains only flat sample files (legacy layout), THE Report_Reader SHALL load those files directly, preserving backward compatibility.
6. THE `indices-watch-report` command SHALL accept a `--session` argument whose value is a Session_ID; WHEN provided, THE Report_Reader SHALL load samples from the matching Session_Directory under the resolved Date_Directory without prompting.
7. IF the Session_ID supplied via `--session` does not match any existing session, THEN THE Report_Reader SHALL print an error listing the available sessions and exit with a non-zero status code.
8. THE `indices-watch-report` command SHALL accept a `--list-sessions` flag; WHEN provided, THE Report_Reader SHALL print the available sessions for the resolved cluster and date (Session_ID, start time, sample count, label) and exit without producing a report.

---

### Requirement 6: Session Discovery and Listing

**User Story:** As an operator, I want to be able to list all sessions for a given cluster and date from the command line, so that I can choose which session to report on without guessing directory names.

#### Acceptance Criteria

1. THE Session_Registry SHALL be built by scanning the Date_Directory for subdirectories that contain a `run.json` file with `schema_version` 2.
2. THE Session_Registry SHALL order sessions by the `started_at` timestamp recorded in each session's `run.json`, ascending.
3. WHEN the Date_Directory does not exist or contains no valid session subdirectories, THE Session_Registry SHALL return an empty list.
4. THE Session_Registry SHALL ignore subdirectories that do not contain a `run.json` or whose `run.json` cannot be parsed as valid JSON.

---

### Requirement 7: Backward Compatibility with Legacy Date Directories

**User Story:** As an operator with existing collected data in the legacy flat `<YYYY-MM-DD>` layout, I want the tool to continue working without requiring migration, so that I do not lose access to historical data.

#### Acceptance Criteria

1. WHEN `indices-watch-collect` is run and the Date_Directory contains flat sample files but no Session_Directories, THE Session_Picker SHALL treat the existing flat files as belonging to a legacy session and offer the user the option to continue appending to the legacy directory or start a new session.
2. WHEN the user chooses to continue appending to the legacy directory, THE Collector SHALL write new sample files directly into the Date_Directory without creating a Session_Directory subdirectory.
3. THE `default_run_dir` function SHALL continue to return the `<Base_Dir>/<cluster>/<YYYY-MM-DD>/` path unchanged; session subdirectory resolution SHALL be handled by a new `resolve_session_dir` function so that callers using `default_run_dir` directly are unaffected.
4. FOR ALL existing `run.json` files with `schema_version` 1, THE Report_Reader SHALL continue to parse and display them correctly without error.
