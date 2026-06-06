import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useStore } from '../store';
import axios from 'axios';
import { FileText, Upload } from 'lucide-react';

const Dropzone = ({ tool }) => {
  const { currentFiles, setFiles, setUploadProgress, setProcessingStep, setJobIds, setActiveStep, setError, error, activeToolId, setAnalysisResult } = useStore();

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(acceptedFiles);
  }, [setFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: tool.accept,
    multiple: activeToolId !== 'pdf-analyser'
  });

  const handleUpload = async () => {
    if (currentFiles.length === 0) return;

    if (activeToolId === 'pdf-analyser') {
      await runAnalysis(currentFiles[0]);
      return;
    }

    setProcessingStep(1); // Move to processing stage
    setUploadProgress(0);
    setActiveStep(1);

    const formData = new FormData();
    currentFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await axios.post(tool.endpoint, formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      if (response.data.jobs) {
        setJobIds(response.data.jobs.map(j => j.job_id));
        startPolling(response.data.jobs[0].job_id);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Check file size or connection.');
      setProcessingStep(0);
    }
  };

  const runAnalysis = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post('/analyse-pdf-quality', formData);
      setAnalysisResult(res.data);
    } catch (e) {
      setError('Analysis failed.');
    }
  };

  const startPolling = async (jobId) => {
    setActiveStep(2);
    let attempts = 0;
    const poll = async () => {
      try {
        const res = await axios.get(`/status/${jobId}`);
        const status = res.data.status;

        if (status === 'finished') {
          setActiveStep(3);
          setTimeout(() => setProcessingStep(2), 500);
        } else if (status === 'failed') {
          setError(res.data.exc_info || 'Processing failed.');
          setProcessingStep(0);
        } else {
          attempts++;
          // Basic exponential backoff-ish
          const delay = Math.min(1000 + attempts * 500, 5000);
          setTimeout(poll, delay);
        }
      } catch (e) {
        setError('Polling error.');
        setProcessingStep(0);
      }
    };
    poll();
  };

  return (
    <div id="ws-upload-stage">
      <div 
        {...getRootProps()} 
        className={`drop-zone ${isDragActive ? 'dragover' : ''} ${currentFiles.length > 0 ? 'has-file' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="dz-icon mb-4">
          {currentFiles.length > 0 ? <FileText size={48} className="text-green-500 mx-auto" /> : <Upload size={48} className="mx-auto" />}
        </div>
        <div className="dz-title text-lg font-bold mb-2">
          {currentFiles.length === 1 ? currentFiles[0].name : currentFiles.length > 1 ? `${currentFiles.length} files selected` : `Select ${tool.title.split(' ')[0]} files`}
        </div>
        <p className="dz-sub text-text-muted text-[0.9rem]">
          {currentFiles.length > 0 
            ? `${(currentFiles.reduce((acc, f) => acc + f.size, 0) / 1024 / 1024).toFixed(2)} MB`
            : `or drag and drop your ${Object.values(tool.accept)[0][0]} files here`}
        </p>
      </div>

      {error && <div className="mt-4 text-red-500 text-center font-semibold">{error}</div>}

      <button 
        className="action-btn" 
        disabled={currentFiles.length === 0}
        onClick={handleUpload}
      >
        {currentFiles.length > 0 ? tool.action : 'Upload a file to start'}
      </button>
    </div>
  );
};

export default Dropzone;
