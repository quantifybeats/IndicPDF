import React from 'react';
import { useStore } from '../store';
import { Download, CheckCircle2, RefreshCw } from 'lucide-react';

const SuccessView = () => {
  const { jobIds, resetWorkspace } = useStore();

  const handleDownload = (e, jobId) => {
    e.preventDefault();
    window.location.href = `/download/${jobId}`;
  };

  const handleDownloadAll = (e) => {
    e.preventDefault();
    jobIds.forEach((id, index) => {
      setTimeout(() => {
        const link = document.createElement('a');
        link.href = `/download/${id}`;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }, index * 800);
    });
  };

  return (
    <div className="success-view p-8 text-center bg-green-500/5 border border-green-500/20 rounded-radius">
      <div className="mb-6 flex justify-center">
        <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center text-green-500">
          <CheckCircle2 size={48} />
        </div>
      </div>
      <h3 className="text-2xl font-black mb-2 tracking-tight">Success!</h3>
      <p className="mb-8 text-text-muted leading-relaxed">
        {jobIds.length === 1 
          ? 'Your document has been processed with enterprise precision.' 
          : `All ${jobIds.length} documents have been successfully converted.`}
      </p>
      
      <div className="flex flex-col gap-4 max-w-[300px] mx-auto">
        {jobIds.length === 1 ? (
          <button 
            className="dl-btn flex items-center justify-center gap-2 !mt-0" 
            onClick={(e) => handleDownload(e, jobIds[0])}
          >
            <Download size={18} /> Download Result
          </button>
        ) : (
          <button 
            className="dl-btn flex items-center justify-center gap-2 !mt-0" 
            onClick={handleDownloadAll}
          >
            <Download size={18} /> Download All ({jobIds.length})
          </button>
        )}

        <button 
          className="flex items-center justify-center gap-2 py-3 px-6 bg-surface border border-border rounded-md font-bold text-sm text-text-muted hover:text-text hover:border-text transition-all" 
          onClick={resetWorkspace}
        >
          <RefreshCw size={16} /> Process another
        </button>
      </div>
    </div>
  );
};

export default SuccessView;
