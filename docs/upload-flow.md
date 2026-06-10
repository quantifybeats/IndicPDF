# File Upload and Processing Flow

This document details the lifecycle of uploaded files in the application, from user selection on the landing page through queue management, navigation routing, format selection, backend/client-side conversion execution, and down to downloading the resulting files.

## Problem
When a user uploaded a file on the landing page, the page redirected to a specific converter page (e.g. `/docx-to-pdf`), but the file state was not persisted across the route transition. The target page mounted in an empty state, rendering a fresh upload dropzone rather than displaying the selected file. This forced the user to upload the file a second time. Additionally, there was no support for uploading multiple files of different types simultaneously.

## Root Cause
The landing page used component-level routing but did not store the uploaded file objects in a persistent global store. Upon redirecting to the tool routes, the new components mounted with their default state (`processingStep = 0` and empty `currentFiles`), losing the previously uploaded file context. Multiple file selections were also ignored as the landing page input only read `e.target.files[0]`.

## Fix Implemented
1. **Centralized Store Hooks:** We refactored `store.js` to contain a persistent `files: []` array that maintains file metadata (name, size, extension, status, downloadUrl, progress) and the raw native browser `File` handles.
2. **Landing Page Interceptors:** The landing page file upload input (and drag-and-drop listener) was updated to convert the input `FileList` to an array, commit the files to the Zustand store via `addFiles()`, and only then trigger navigation to `/converter`.
3. **Workspace Dropzone Redirects:** All file drops/selections inside tool dropzones (excluding the PDF Analyser) are now stored globally and redirect immediately to the unified `/converter` route, establishing a clean, unified workspace experience.
4. **Sequential Processing Engine:** The workspace runs a sequential converter loop that processes document conversions on the server (DOCX, PDF, TXT) and handles media conversions (images, audio, video) client-side using FFmpeg.
5. **Streamed and Encrypted Ingestion:** The FastAPI backend streams uploaded files to a temporary location in 1MB chunks and encrypts them using 64KB AES-GCM chunks to keep memory consumption low (<1MB constant RAM).
6. **Size-Based Queue Routing:** The backend checks the file size: files under 5MB are routed to the `"fast"` queue, and files above 5MB are routed to the `"slow"` queue.
7. **LibreOffice Fallback Engine:** When processing a DOCX file to PDF in the background task:
   - The worker looks for the `soffice` command.
   - If present (e.g. in the production Docker image), it converts it using LibreOffice headless.
   - If absent (e.g. in local development), it falls back to native python-based FPDF rendering with HarfBuzz shaping.
8. **Decrypted Download Streaming:** When the user downloads a converted document, the backend decrypts the ciphertext file in memory on-the-fly and streams it to the client, preventing unencrypted data from sitting on the server.

## Before vs After Behavior

| Behavior / Feature | Before Refactor | After Refactor |
| :--- | :--- | :--- |
| **Landing Page Upload** | Single file selection only; redirects to specific page but loses file reference on navigation. | Multiple files/folders allowed; commits files to Zustand store and redirects seamlessly to `/converter`. |
| **Dropzone Uploads** | Directly processed file on the current route; no multi-step queue or route persistence. | Intercepts files, appends them to the global workspace queue, and redirects to `/converter`. |
| **Queue Management** | None. Re-uploading required if route changes. | Workspace holds files dynamically. Supports additions, individual removals, and batch actions. |
| **Lifecycle Transitions** | UI instantly swapped between dropzone, progress, and success view. | Clear transitions on each file card: `idle` -> `converting (X%)` -> `done` (showing individual download button). |
| **Server Encryption** | Ingested entire file into memory before encrypting, causing OOM risks. | Streams 1MB chunks to temp file, and encrypts using 64KB chunks to keep memory flat. |
| **Task Queue Routing** | Sent all tasks to a single queue regardless of file size. | Automatically routes files: <=5MB to `fast` queue, >5MB to `slow` queue for prioritized processing. |
| **Conversion Engines** | Strictly failed docx-to-pdf conversions locally if LibreOffice was missing. | Dual-engine setup: uses LibreOffice headless in production and falls back to FPDF locally. |
