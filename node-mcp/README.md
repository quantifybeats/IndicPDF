# IndicPDF Node.js MCP Server

This is an MCP (Model Context Protocol) server that wraps the IndicPDF FastAPI backend.

## Prerequisites
- Node.js v18+
- The FastAPI backend must be running (default: `http://localhost:8000`)
- The FastAPI backend must have an API Key configured.

## Configuration
The following environment variables are required:
- `FASTAPI_BASE_URL`: URL of the FastAPI backend (e.g., `http://localhost:8000`)
- `INDICPDF_API_KEY`: The same API key configured in the FastAPI backend.

## Installation
```bash
npm install
```

## Running
```bash
# Run with env variables
FASTAPI_BASE_URL=http://localhost:8000 INDICPDF_API_KEY=your-secret-key npm start
```

## Tools Provided
- `convert_docx_to_pdf`: Converts DOCX (base64) to PDF.
- `convert_pdf_to_docx`: Converts PDF (base64) to DOCX.
