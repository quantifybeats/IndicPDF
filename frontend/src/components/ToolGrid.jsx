import React from 'react';
import ToolCard from './ToolCard';

const tools = [
  {
    id: 'docx-to-pdf',
    icon: '📝',
    title: 'DOCX to PDF',
    description: 'Convert Microsoft Word documents to high-fidelity PDF with perfect Indic script rendering.',
  },
  {
    id: 'pdf-to-docx',
    icon: '📋',
    title: 'PDF to DOCX',
    description: 'Extract text from PDFs and convert them into editable Word files while preserving structure.',
  },
  {
    id: 'txt-to-pdf',
    icon: '📜',
    title: 'TXT to PDF',
    description: 'Convert plain text files to professional PDFs with automated font shaping and layout.',
  },
  {
    id: 'analyser',
    icon: '🔍',
    title: 'PDF Analyser',
    description: 'Check PDF health, font embedding, and searchability. Get a quality score for your documents.',
  },
];

const ToolGrid = () => {
  return (
    <section className="tool-grid-section py-8 px-6 max-w-[1200px] mx-auto" id="all">
      <div className="tool-grid grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-6">
        {tools.map((tool) => (
          <ToolCard key={tool.id} {...tool} />
        ))}
      </div>
    </section>
  );
};

export default ToolGrid;
