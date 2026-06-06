import React, { Suspense, useEffect } from 'react';
import { useStore } from '../store';
import ToolLayout from '../components/ToolLayout';

const Dropzone = React.lazy(() => import('../components/Dropzone'));
const UploadProgress = React.lazy(() => import('../components/UploadProgress'));
const ProcessingSteps = React.lazy(() => import('../components/ProcessingSteps'));
const SuccessView = React.lazy(() => import('../components/SuccessView'));

const TOOL = { 
  id: 'txt-to-pdf',
  title: 'TXT to PDF', 
  description: 'Convert plain text files to professional PDFs with automated font shaping and layout for Indic scripts.',
  accept: { 'text/plain': ['.txt'] }, 
  icon: '📜', 
  action: 'Convert to PDF', 
  endpoint: '/upload' 
};

const TxtToPdf = () => {
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

export default TxtToPdf;
