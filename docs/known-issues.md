# Known Issues & Architectural Safeguards

This document lists the critical bugs resolved, edge cases handled, and routing safeguards implemented during the refactoring and optimization process.

## Problem
The application suffered from multiple broken user flows:
- **Empty Redirects:** Selecting a file on the landing page redirected to a tool page (e.g. `/docx-to-pdf`), but the file itself was not passed along, leaving the user with an empty dropzone.
- **Route Persistence Loss:** Navigating to another route or reloading the page wiped out the selected files list.
- **Format Verification:** Users could click convert buttons without choosing a target output format, leading to empty or failed requests.
- **Browser State Collisions:** Attempting to convert multiple media files concurrently caused local FFmpeg instance lockups.
- **Popover Clipping:** Rendering absolute dropdowns inside file cards with `overflow-hidden` clipped the dropdown popover.
- **Dark Theme Forced:** Workspace defaulted to dark mode, ignoring the light-theme default preference.
- **Stuck Conversion at 98%:** Converting text files (.txt to .pdf) failed on the server and hung the UI.
- **Infinite Polling on Failure:** Server-side conversion failures did not propagate correctly, causing the client to poll indefinitely.
- **Slow Development Feedback:** Job failures in local development took over 40 seconds to report due to queue retries.
- **Missing LibreOffice Locally:** Converting DOCX to PDF on machines without LibreOffice (`soffice`) failed with a FileNotFoundError.

## Root Cause
- **Lack of a Persistent Global Store:** The workspace queue state was not saved globally or stored in browser storage.
- **Premature Navigation:** Router redirects were fired before file arrays were saved.
- **Missing Route Guards:** Directly visiting `/converter` (or refreshing) mounted an empty layout without redirecting or prompting the user.
- **Concurrent Execution:** No queuing mechanism existed to run browser-based FFmpeg tasks sequentially.
- **Card Overflow Style:** File cards utilized `overflow-hidden` to clip progress bars, which cut off absolute children.
- **Default Theme Config:** Zustand store initialized with `'dark'` theme, and did not force light-mode setting on first run.
- **Missing Class Definition:** The `IndicPDF` FPDF subclass was accidentally removed from `processor.py` during a previous refactoring, causing a `NameError`.
- **RQ Exception Handler Bypassing:** The custom RQ worker exception handler `handle_job_failure` returned `None`, which blocked the default RQ exception handler from marking the job status as `"failed"`.
- **Strict Retry Queueing:** The enqueued jobs used a `Retry(max=2)` logic which scheduled failed jobs for retries, showing them as `"scheduled"` and dragging out the failure time.
- **Environment Mismatches:** Headless conversion relied strictly on the `soffice` system binary, which is installed in the production Docker image but absent on developer machines.

## Fix Implemented
1. **Guarded State Navigation:** The landing page now commits the `FileList` to the Zustand store *before* firing the router navigation to `/converter`.
2. **Converter Route Guard:** Added an automatic guard in `/converter`. If the `files` array is empty, the component waits for 500ms and redirects the user back to the landing page (`/`) to select files.
3. **Format Guard:** The "Convert All" button is disabled until every file card has an output format selected.
4. **Data Loss Handling:** In Zustand's `persist` configuration, we save serializable metadata in `localStorage`. If the user refreshes, the UI displays a re-upload prompt for raw file data.
5. **Sequential Execution Queue:** Inside `handleConvertAll`, we iterate over files sequentially using a loop, ensuring only one FFmpeg execution or API request runs at a time.
6. **Card Overflow Fix:** Changed card container overflow styling to `overflow-visible`, applying `overflow-hidden` only to the progress bar container.
7. **Forced Light Mode:** Configured the store to default to `'light'` and forced `'light'` mode explicitly on app mount in `App.jsx`.
8. **Restored IndicPDF Class:** Reintroduced the `IndicPDF` class (subclassing `FPDF`) to `processor.py` and imported `FPDF` and `Document`, fixing the `NameError`.
9. **Proper RQ Exception Propagation:** Updated `handle_job_failure` in `tasks.py` to return `True`, allowing exceptions to propagate back to the default handler to mark the job as `"failed"` in Redis.
10. **Disable Retries in Development:** Modified `retry_logic()` in `main.py` to return `None` when the development API key is used, reporting errors instantly to the client.
11. **LibreOffice Headless Fallback:** Refactored `process_docx_to_pdf_final` to detect if `soffice` is in the system PATH or macOS Application directory. If absent, it automatically falls back to native FPDF rendering.

## Before vs After Behavior

| Issue / Edge Case | Before Refactor | After Refactor |
| :--- | :--- | :--- |
| **Direct Route Access** | Accessing `/converter` renders empty workspace pages and broken UI elements. | Automatically detects empty queue and redirects back to Home (`/`) within 500ms. |
| **Output Format Missing** | Fired empty API requests or client conversions, causing silent failures. | "Convert All" is disabled until all formats are specified. |
| **Page Refresh** | Reset the entire workspace and forced re-uploading. | Restores file queue metadata and displays clear re-upload prompts for raw file data. |
| **Multiple Media Conversions** | Ran concurrently, crashing the browser's shared WASM FFmpeg thread. | Sequentially converts files, safely updating progress bars in real-time. |
| **Duplicate Files** | Allowed duplicates, causing keys and name conflicts. | Filters out files that match existing filenames during upload. |
| **Server Failures & retries** | Jobs failed silently, retried for ~40s, and hung the UI at 98% progress. | Failures propagate instantly (no retries in dev) and update the UI card to **ERROR** state. |
| **Missing local soffice** | Converting DOCX files locally threw a FileNotFoundError and crashed the task. | Seamlessly falls back to native FPDF-based shaping and rendering, completing the conversion. |
