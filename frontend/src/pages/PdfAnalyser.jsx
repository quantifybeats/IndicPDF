import React, { Suspense, useEffect, useState } from 'react';
import { useStore } from '../store';
import { motion } from 'framer-motion';

const Dropzone = React.lazy(() => import('../components/Dropzone'));
const AnalysisResult = React.lazy(() => import('../components/AnalysisResult'));

const TOOL = { 
  id: 'analyser',
  title: 'PDF Quality Analyser', 
  accept: { 'application/pdf': ['.pdf'] }, 
  icon: '🔍', 
  action: 'Analyse PDF', 
  endpoint: '/analyse-pdf-quality' 
};

const PdfAnalyser = () => {
  const { analysisResult, resetWorkspace, setActiveTool, error } = useStore();
  const [isAnalysing, setIsAnalysing] = useState(false);

  useEffect(() => {
    setActiveTool(TOOL.id);
    return () => resetWorkspace();
  }, []);

  // Monitor analysisResult to stop loading state if we had one
  // (Though Dropzone handles the call, we can improve UX here)

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
            {!analysisResult ? (
              <Dropzone tool={TOOL} />
            ) : (
              <AnalysisResult result={analysisResult} />
            )}
          </Suspense>

          <div className="mt-8 text-[0.75rem] text-text-muted text-center border-t border-border pt-4">
            🔒 Secure 256-bit SSL encryption. All files are deleted automatically after 2 hours.
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default PdfAnalyser;
