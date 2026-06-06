import React, { Suspense, useEffect } from 'react';
import { useStore } from '../store';
import ToolLayout from '../components/ToolLayout';

const Dropzone = React.lazy(() => import('../components/Dropzone'));
const AnalysisResult = React.lazy(() => import('../components/AnalysisResult'));

const TOOL = { 
  id: 'pdf-analyser',
  title: 'PDF Quality Analyser', 
  description: 'Analyse your PDF for font embedding, text searchability, and quality metrics to ensure compatibility across all devices.',
  accept: { 'application/pdf': ['.pdf'] }, 
  icon: '🔍', 
  action: 'Analyse PDF', 
  endpoint: '/analyse-pdf-quality' 
};

const PdfAnalyser = () => {
  const { analysisResult, resetWorkspace, setActiveTool } = useStore();

  useEffect(() => {
    setActiveTool(TOOL.id);
    return () => resetWorkspace();
  }, []);

  return (
    <ToolLayout title={TOOL.title} description={TOOL.description} icon={TOOL.icon}>
      <Suspense fallback={<div className="text-center p-8"><div className="spinner"></div><p>Analysing Document...</p></div>}>
        {!analysisResult ? (
          <Dropzone tool={TOOL} />
        ) : (
          <div className="max-w-[700px] mx-auto">
            <AnalysisResult result={analysisResult} />
          </div>
        )}
      </Suspense>
    </ToolLayout>
  );
};

export default PdfAnalyser;
