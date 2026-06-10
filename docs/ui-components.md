# UI Components & Workspace Layout

This document describes the design layout, interactive elements, and details of the unified Converter workspace UI and file cards.

## Problem
The application lacked a central workspace interface. Files could only be processed one-by-one or within specialized tool-specific pages. The user interface lacked clear file cards, individual progress indicators, remove file options, and format dropdown selections for the files in the queue.

## Root Cause
Components were built to handle specific files singly. `FormatSelector` was only used inside specialized tools like `ImageConverter` and relied on local component arrays. The landing page and dropzones did not have a shared layout capable of presenting and managing a mixed queue of documents, images, videos, and audios.

## Fix Implemented
1. **Unified Workspace Layout (`Converter.jsx`):** Developed a unified page mapping the central Zustand `files` list into a clean, modern card queue.
2. **Searchable Category Popover Dropdown (`FormatSelector.jsx`):** Developed a custom double-pane popover selector matching the Convertio style:
   - **Search Filter:** A live search bar filters formats in real time.
   - **Categories Pane (Left):** Lists file categories: *Image, Document, EBook, Presentation, Font, Vector, Audio, Video* with right chevrons for the active category.
   - **Formats Grid Pane (Right):** Displays the formats grid for the selected category.
   - **Allowed Formats Constraint:** Displays all formats but only enables selection of target output formats that are valid for the file type, disabling invalid ones for safety.
   - **Outside Click Closing:** Automatically closes on outside click.
3. **Card Layout & Feedback:**
   - **Visual Accents:** Cards render with colored borders and backgrounds based on the file type (blue for DOCX, red for PDF, purple for video, etc.).
   - **Status Badges:** Displays dynamic tags: `Ready` (idle), `Converting... (X%)` (progress indicator), `Done` (green checkmark), or `Error` (with hoverable error details).
   - **Individual Progress Bar:** Progress bar slides along the bottom of the card during active conversions.
   - **Download Button:** Done files swap out format configuration for a direct download button.
   - **Remove Button:** The close icon (`×`) deletes the item from the Zustand queue, disabling itself during active conversions.
4. **Drag & Drop Overlay:** An interactive fullscreen drop zone overlay triggers whenever files are dragged over the workspace page, allowing files to be added instantly.
5. **Add More Toolbar:** A bottom toolbar lets the user add more files or entire folder directories, clear the workspace, and initiate bulk conversion.
6. **Workspace Theme:** Clean light mode interface design with slate text, soft borders, and smooth shadows.

## Before vs After Behavior

| Component / Feature | Before Refactor | After Refactor |
| :--- | :--- | :--- |
| **Workspace Page** | None. Users had to use separate pages for each format. | Single, unified `/converter` page handling all files in one queue. |
| **File Cards** | Basic row structure with hardcoded inputs. | Sleek, glassmorphic cards with animated entry, color-coded file type icons, and progress bars. |
| **Output Dropdown** | Simple select input with static options. | Dynamically computed options list tailored specifically to each file's input extension. |
| **Removal Options** | Limited or non-functional. | Clean trash icon on each card, disabled during active conversions. |
| **Drag & Drop Workspace** | Limited dropzone card. | Full-window drag-and-drop overlay with bounce animations. |
| **Add More Files** | No support. | Toolbar supports adding more files or full folder directories in-place. |
