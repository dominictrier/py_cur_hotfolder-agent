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
Modified the mtime comparison logic to reset seen_time on any mtime change, independent of the seen_time.

**Context:**  
The watcher was inconsistently handling mtime changes:
- For individual files, it reset on any mtime change
- For job folders, it only reset when mtime was newer than recorded mtime

This inconsistency could cause issues where files with older mtimes weren't properly triggering the resting timer reset.

**Consequences:**  
The seen_time is now reset when:
1. Files are added to the job
2. Files are removed from the job
3. File mtimes are different from their recorded mtime (any change)
4. Files are deleted from the seen state

This ensures consistent behavior across all file operations. The mtime comparison is independent of the seen_time, which is only used for resting time calculations.

A folder can only be processed when ALL files inside have:
- No mtime changes during the resting period
- Been present for the full resting period
- Reached their individual resting times

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.1]

---

## 2024-06-12: Fixed folder processing logic to ensure all files must rest

**Decision:**  
Modified the folder processing logic to ensure ALL files in a folder must rest before the folder can be processed.

**Context:**  
The watcher was not properly checking if all files in a folder had rested before processing. This could lead to premature processing of folders where some files were still being modified.

**Consequences:**  
- Each file in a folder must independently rest for the full resting time
- A folder can only be processed when ALL files inside have rested
- Debug logging now shows which files haven't rested long enough
- Clear separation between seen_time (for resting) and mtime (for changes)

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.2]

---

## 2024-06-12: Added cleanup of seen and processed states for all removal cases

**Decision:**  
Added automatic cleanup of both seen and processed database entries in all cases where files or folders are removed from the IN folder.

**Context:**  
The database entries needed to be cleaned up in three scenarios:
1. When files/folders are removed by the workflow (moved to OUT)
2. When files/folders are removed by retention policy
3. When files/folders are deleted by the user

Without proper cleanup, files could be processed immediately when moved back to IN, bypassing the resting time requirement.

**Consequences:**  
- Database entries are cleaned up whenever a file or folder is removed from IN, regardless of how it was removed
- This ensures proper resting time is enforced for all files, even those that were previously in IN
- Cleanup happens for both seen and processed states
- Debug logging shows when states are cleaned up for removed items

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.2]

---

## 2024-06-12: Added cleanup of ghost entries during retention

**Decision:**  
Modified retention cleanup to also remove database entries for files that no longer exist, regardless of their retention time.

**Context:**  
The retention cleanup was only removing database entries for files that:
1. Still existed in the filesystem
2. Had exceeded the retention time

This meant we could have "ghost" entries in the database for files that were deleted or moved but still had processed entries.

**Consequences:**  
- During retention cleanup, we now check if each file exists
- Database entries are cleaned up if:
  1. The file no longer exists (regardless of retention time)
  2. The file exists but has exceeded retention time
- This ensures the database stays clean and doesn't accumulate ghost entries
- Debug logging now shows whether files exist and why they're being cleaned up

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.2]

---

## 2024-06-12: Separated business logic from debug output

**Decision:**  
Keep business logic and debug output strictly separate, ensuring that debug/logging changes never influence the actual behavior of the system.

**Context:**  
During development, there can be a temptation to modify business logic to make debugging easier or to improve log output. This can lead to unintended side effects and make the code harder to maintain.

**Consequences:**  
- Business logic is driven solely by functional requirements
- Debug output and logging are treated as presentation concerns
- Changes to debug output never affect the actual behavior of the system
- Makes it easier to modify logging without risking functional changes
- Improves code maintainability by keeping concerns separated

**Examples:**
- Debug output can show processed times from child files without changing how folders are processed
- Logging can be enhanced to show more information without modifying the underlying logic
- Debug statements can be added or removed without affecting the business rules

**Related Issues/PRs:**  
- See CHANGELOG.md [1.10.2]

---