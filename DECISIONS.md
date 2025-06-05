---
description: Architectural and workflow decisions for this project.
---

# DECISIONS.md

This file documents important architectural, workflow, and process decisions for this project, along with the reasoning behind them.

---

## 2024-06-10: Always reset resting timer on any mtime change

**Decision:**  
The watcher now resets the resting timer for a job on any mtime change (increase or decrease), not just increases.

**Context:**  
Previously, if a file was copied into the hotfolder with an older mtime (e.g., restored from backup or copied from another system), the watcher would not reset the resting timer, causing jobs to get stuck and never process. This was due to only resetting the timer when mtime increased.

**Consequences:**  
Any change in mtime (increase or decrease) is now treated as a new file, ensuring jobs are always processed after the configured resting time. Debug logging now records both the old and new mtime for traceability.

**Related Issues/PRs:**  
- See CHANGELOG.md [1.9.2]

---

## 2024-06-10: Only remove 'seen' state for the current job

**Decision:**  
The watcher now only removes 'seen' entries for the specific job being processed or deleted, rather than for all jobs in the hotfolder.

**Context:**  
Previously, the watcher would sometimes remove 'seen' state for all jobs when processing or deleting a single job. This caused jobs to be stuck in a loop, as their 'seen' state was reset by the processing of other jobs, preventing them from ever reaching the resting time needed for processing.

**Consequences:**  
'Seen' state is now scoped to the current job, preventing interference between jobs and ensuring each job's resting timer is managed independently.

**Related Issues/PRs:**  
- See CHANGELOG.md [1.9.2]

---

## 2024-06-11: Version 1.10.0 - Improved watcher stability and parallel job handling

**Decision:**  
Released version 1.10.0 with improved watcher logic and robust handling of multiple jobs in parallel.

**Context:**  
Recent testing confirmed that all jobs are picked up, rested, processed, and deleted after retention as expected, with all state correctly scrubbed from the database. The watcher now resets the resting timer on any mtime change and only removes 'seen' state for the current job. Debug logging for mtime changes has been improved.

**Consequences:**  
The system is now more robust, predictable, and easier to debug, especially when handling multiple jobs in parallel.

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.0]

---

## 2024-06-12: Fixed mtime comparison logic in watcher

**Decision:**  
Modified the mtime comparison logic to only reset seen_time when there are actual changes to files, not just when the latest mtime is greater than the last seen time.

**Context:**  
The watcher was incorrectly resetting the seen_time whenever the latest mtime was greater than the last seen time, causing unnecessary resets and preventing jobs from reaching their resting time. This was particularly problematic when files had newer mtimes than when they were first seen.

**Consequences:**  
The seen_time is now only reset when there are actual changes to the files (additions, removals, or mtime changes), ensuring jobs can properly reach their resting time and be processed. This maintains the stability improvements from version 1.10.0 while fixing the mtime comparison issue.

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.1]

---