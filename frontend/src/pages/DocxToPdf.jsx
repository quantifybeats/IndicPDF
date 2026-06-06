import React, { Suspense, useEffect } from 'react';
import { useStore } from '../store';
import { motion } from 'framer-motion';

const Dropzone = React.lazy(() => import('../components/Dropzone'));
const UploadProgress = React.lazy(() => import('../components/UploadProgress'));
const ProcessingSteps = React.lazy(() => import('../components/ProcessingSteps'));
const SuccessView = React.lazy(() => import('../components/SuccessView'));

const TOOL = { 
  id: 'docx-to-pdf',
  title: 'DOCX to PDF', 
  accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] }, 
  icon: '📝', 
  action: 'Convert to PDF', 
  endpoint: '/upload' 
};

const DocxToPdf = () => {
  const { processingStep, resetWorkspace, setActiveTool } = useStore();

  useEffect(() => {
    setActiveTool(TOOL.id);
    return () => resetWorkspace();
  }, []);

  return (
    <div className="container mx-auto px-6 py-12 max-w-[800px]">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="workspace-card bg-surface rounded-radius overflow-hidden shadow-shadow-lg"
      >
        <div className="workspace-header px-8 py-5 border-b border-border">
          <h1 className="text-2xl font-extrabold flex items-center gap-3">
            <span>{TOOL.icon}</span> {TOOL.title}
          </h1>
        </div>
        <div className="workspace-body p-8">
          <Suspense fallback={<div className="text-center p-8">Loading...</div>}>
            {processingStep === 0 && <Dropzone tool={TOOL} />}
            {processingStep === 1 && (
              <>
                <UploadProgress />
                <ProcessingSteps />
              </>
            )}
            {processingStep === 2 && <SuccessView />}
          </Suspense>

          <div className="mt-8 text-[0.75rem] text-text-muted text-center border-t border-border pt-4">
            🔒 Secure 256-bit SSL encryption. All files are deleted automatically after 2 hours.
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default DocxToPdf;
