import React from 'react';
import { useStore } from '../store';
import axios from 'axios';

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
    <div className="success-view active bg-[#f0fff4] border border-[#c6f6d5] rounded-lg p-8 text-center">
      <div className="text-[3rem] mb-4">🎉</div>
      <h3 className="text-xl font-bold mb-2">Conversion Complete!</h3>
      <p className="mb-6 text-text-muted">Your document has been processed successfully.</p>
      
      {jobIds.length === 1 ? (
        <a 
          href="#" 
          className="dl-btn" 
          onClick={(e) => handleDownload(e, jobIds[0])}
        >
          Download File
        </a>
      ) : (
        <a 
          href="#" 
          className="dl-btn" 
          onClick={handleDownloadAll}
        >
          Download All ({jobIds.length} files)
        </a>
      )}

      <div className="mt-6">
        <button 
          className="bg-none border border-[#ccc] py-2 px-4 rounded-md cursor-pointer hover:bg-gray-100 transition-colors" 
          onClick={resetWorkspace}
        >
          Process another file
        </button>
      </div>
    </div>
  );
};

export default SuccessView;
