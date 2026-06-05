import React, { Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import { X } from 'lucide-react';

const Dropzone = React.lazy(() => import('./Dropzone'));
const UploadProgress = React.lazy(() => import('./UploadProgress'));
const ProcessingSteps = React.lazy(() => import('./ProcessingSteps'));
const SuccessView = React.lazy(() => import('./SuccessView'));

const TOOLS = {
  'docx-to-pdf': { title: 'DOCX to PDF', accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] }, icon: '📝', action: 'Convert to PDF', endpoint: '/upload' },
  'pdf-to-docx': { title: 'PDF to DOCX', accept: { 'application/pdf': ['.pdf'] }, icon: '📋', action: 'Convert to DOCX', endpoint: '/upload' },
  'txt-to-pdf': { title: 'TXT to PDF', accept: { 'text/plain': ['.txt'] }, icon: '📜', action: 'Convert to PDF', endpoint: '/upload' },
  'analyser': { title: 'PDF Quality Analyser', accept: { 'application/pdf': ['.pdf'] }, icon: '🔍', action: 'Analyse PDF', endpoint: '/analyse-pdf-quality' }
};

const WorkspaceModal = () => {
  const { isModalOpen, activeToolId, closeModal, processingStep, resetWorkspace } = useStore();

  if (!isModalOpen) return null;

  const tool = TOOLS[activeToolId];

  return (
    <AnimatePresence>
      {isModalOpen && (
        <div className="workspace-overlay fixed inset-0 bg-black/50 backdrop-blur-sm z-[1000] flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="workspace-card bg-bg w-full max-w-[800px] rounded-radius overflow-hidden shadow-shadow-lg relative max-h-[95vh] flex flex-col"
          >
            <div className="workspace-header bg-surface px-8 py-5 border-b border-border flex items-center justify-between">
              <h2 className="text-xl font-extrabold">{tool?.title || 'Tool Name'}</h2>
              <button className="close-workspace bg-none border-none text-2xl cursor-pointer text-text-muted hover:text-text transition-colors" onClick={closeModal}>
                <X size={24} />
              </button>
            </div>
            <div className="workspace-body p-8 overflow-y-auto">
              <Suspense fallback={<div className="text-center p-8">Loading...</div>}>
                {processingStep === 0 && <Dropzone tool={tool} />}
                {processingStep === 1 && (
                  <>
                    <UploadProgress />
                    <ProcessingSteps />
                  </>
                )}
                {processingStep === 2 && <SuccessView />}
              </Suspense>

              <div className="mt-8 text-[0.75rem] text-text-muted text-center border-top border-border pt-4">
                🔒 Secure 256-bit SSL encryption. All files are deleted automatically after 2 hours.
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default WorkspaceModal;
