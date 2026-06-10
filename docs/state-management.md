# State Management

This document outlines the state architecture, Zustand store schema, actions, and persistence layer utilized to manage files and workspace configuration.

## Problem
File metadata, progress, job IDs, and active views were stored in isolated components using standard React `useState` hooks. Because React Router unmounts components when routes change, navigating away from a tool page instantly destroyed the state. Furthermore, page reloads completely wiped the workspace, resulting in a poor user experience.

## Root Cause
The application lacked a central source of truth for workspace files. The existing Zustand store in `store.js` only contained simple layout variables (`activeToolId`, `isModalOpen`, `currentFiles`, etc.) but did not handle complex files lists, specific file formats, status tracking, or persistence configurations.

## Fix Implemented
1. **Centralized Zustand Store:** Refactored `store.js` using Zustand.
2. **Workspace Store Schema:** Defined a `files: []` array containing file items structured as follows:
   ```typescript
   interface WorkspaceFile {
     id: string;          // Random unique ID for component keys and updates
     name: string;        // Original file name (e.g. "report.docx")
     size: number;        // Raw size in bytes
     type: string;        // MIME type or normalized extension
     outputFormat: string;// User-selected output extension (e.g. "pdf")
     status: 'idle' | 'converting' | 'done' | 'error';
     file: File;          // Native browser File object (non-serializable)
     downloadUrl: string; // Browser ObjectURL or backend download endpoint
     progress: number;    // Conversion completion percentage (0 to 100)
     error?: string;      // Error message if processing fails
   }
   ```
3. **Workspace Core Actions:**
   - `setFiles(files)`: Overwrites the workspace queue with a formatted list of new files.
   - `addFiles(incoming)`: Appends new files to the existing queue, ignoring files with duplicate names.
   - `updateFile(id, updates)`: Modifies a file item by ID (e.g., updating output format, progress, status, or download URLs).
   - `clearFiles()`: Completely resets the files array.
4. **Zustand Persistence:** Integrated the `persist` middleware. It stores the `theme` and the `files` array (file metadata only) in `localStorage`. The native browser `file` handles and temporary `downloadUrl` references are omitted during serialization to prevent crashes, as these cannot be saved in JSON.

## Before vs After Behavior

| Behavior / Feature | Before Refactor | After Refactor |
| :--- | :--- | :--- |
| **State Storage** | Isolated component-level `useState` in `Dropzone.jsx`, `ImageConverter.jsx`, etc. | Centralized store in `store.js` accessed by landing pages, dropzones, and the workspace. |
| **Navigation Persistence** | File objects and queues destroyed instantly on route transitions. | File metadata persists across all route navigation. |
| **LocalStorage Sync** | None. Only theme was manually synced. | Automated localStorage syncing of theme and file metadata using Zustand's `persist` middleware. |
| **Page Refreshes** | Entire workspace resets, forcing user to start from scratch. | Restores file list metadata. Shows a "needs re-upload" notice if the raw file handle is missing. |
| **Duplicate Prevention** | No validation against duplicate filenames. | `addFiles` checks filenames and filters duplicates. |
