import React from 'react';
import { useStore } from '../store';

const UploadProgress = () => {
  const { uploadProgress } = useStore();

  if (uploadProgress === 100) return null;

  return (
    <div id="ws-upload-progress" className="mt-6">
      <div className="bg-[#eee] h-[6px] rounded-[10px] overflow-hidden">
        <div 
          className="bg-primary h-full transition-[width] duration-300" 
          style={{ width: `${uploadProgress}%` }}
        ></div>
      </div>
      <p className="text-[0.8rem] text-center mt-2">
        Uploading... {uploadProgress}%
      </p>
    </div>
  );
};

export default UploadProgress;
