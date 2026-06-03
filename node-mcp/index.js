const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema } = require("@modelcontextprotocol/sdk/types.js");
const FastApiClient = require("./FastApiClient.js");
const stream = require('stream');

// Configuration
const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || "http://localhost:8000";
const INDICPDF_API_KEY = process.env.INDICPDF_API_KEY || "dev-key-placeholder";

const apiClient = new FastApiClient(FASTAPI_BASE_URL, INDICPDF_API_KEY);

const server = new Server(
  {
    name: "indic-pdf-converter",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "convert_docx_to_pdf",
        description: "Convert a DOCX file to a high-fidelity PDF (especially for Indic scripts)",
        inputSchema: {
          type: "object",
          properties: {
            file_base64: { type: "string", description: "Base64 encoded DOCX file content" },
            filename: { type: "string", description: "Original filename (e.g., document.docx)" },
          },
          required: ["file_base64", "filename"],
        },
      },
      {
        name: "convert_pdf_to_docx",
        description: "Extract text from a PDF and convert it to a DOCX file",
        inputSchema: {
          type: "object",
          properties: {
            file_base64: { type: "string", description: "Base64 encoded PDF file content" },
            filename: { type: "string", description: "Original filename (e.g., report.pdf)" },
          },
          required: ["file_base64", "filename"],
        },
      },
      {
        name: "convert_txt_to_pdf",
        description: "Convert a plain text (TXT) file to a high-fidelity PDF with Indic shaping",
        inputSchema: {
          type: "object",
          properties: {
            file_base64: { type: "string", description: "Base64 encoded TXT file content" },
            filename: { type: "string", description: "Original filename (e.g., notes.txt)" },
          },
          required: ["file_base64", "filename"],
        },
      },
    ],
  };
});

// Helper to convert base64 to stream
function base64ToStream(base64) {
    const buffer = Buffer.from(base64, 'base64');
    const readStream = new stream.PassThrough();
    readStream.end(buffer);
    return readStream;
}

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    if (name === "convert_docx_to_pdf" || name === "convert_pdf_to_docx" || name === "convert_txt_to_pdf") {
      const { file_base64, filename } = args;
      const fileStream = base64ToStream(file_base64);

      // 1. Upload
      const jobId = await apiClient.upload(fileStream, filename);
      
      // 2. Poll for completion
      await apiClient.pollStatus(jobId);
      
      // 3. Download result
      const resultBuffer = await apiClient.download(jobId);
      
      return {
        content: [
          {
            type: "text",
            text: `Successfully converted ${filename}. Result size: ${resultBuffer.length} bytes.`,
          },
          {
            type: "text",
            text: `RESULT_BASE64_START:${Buffer.from(resultBuffer).toString('base64')}:RESULT_BASE64_END`,
          }
        ],
      };
    }
    
    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("IndicPDF MCP Server running on Stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
