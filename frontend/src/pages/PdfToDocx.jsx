import React, { Suspense, useEffect } from 'react';
import { useStore } from '../store';
import ToolLayout from '../components/ToolLayout';

const Dropzone = React.lazy(() => import('../components/Dropzone'));
const UploadProgress = React.lazy(() => import('../components/UploadProgress'));
const ProcessingSteps = React.lazy(() => import('../components/ProcessingSteps'));
const SuccessView = React.lazy(() => import('../components/SuccessView'));

const TOOL = { 
  id: 'pdf-to-docx',
  title: 'PDF to DOCX', 
  description: 'Extract text from PDFs and convert them into editable Word files while preserving structure and scrubbing CID artifacts.',
  accept: { 'application/pdf': ['.pdf'] }, 
  icon: '📋', 
  action: 'Convert to DOCX', 
  endpoint: '/upload' 
};

const PdfToDocx = () => {
  const { processingStep, resetWorkspace, setActiveTool } = useStore();

  useEffect(() => {
    setActiveTool(TOOL.id);
    return () => resetWorkspace();
  }, []);

  return (
    <ToolLayout title={TOOL.title} description={TOOL.description} icon={TOOL.icon}>
      <Suspense fallback={<div className="text-center p-8"><div className="spinner"></div><p>Loading Workspace...</p></div>}>
        {processingStep === 0 && <Dropzone tool={TOOL} />}
        {processingStep === 1 && (
          <div className="max-w-[500px] mx-auto">
            <UploadProgress />
            <ProcessingSteps />
          </div>
        )}
        {processingStep === 2 && <SuccessView />}
      </Suspense>
    </ToolLayout>
  );
};

export default PdfToDocx;
