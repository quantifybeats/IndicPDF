import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import axios from 'axios';
import { FileText, Upload, Loader2, FolderOpen } from 'lucide-react';
import UploadErrorList from './UploadErrorList';
import { validateFiles, readFolderEntries } from '../hooks/useFileValidation';

const Dropzone = ({ tool }) => {
  const navigate = useNavigate();
  const addFilesToStore = useStore((state) => state.addFiles);
  const { currentFiles, setFiles, setUploadProgress, setProcessingStep, setJobIds, setActiveStep, setError, error, activeToolId, setAnalysisResult } = useStore();
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);

  const acceptedExts = tool.accept ? Object.values(tool.accept).flat() : null;

  const addFiles = useCallback((incoming) => {
    const { valid, errors } = validateFiles(incoming, acceptedExts);
    if (errors.length) setValidationErrors(prev => [...prev, ...errors]);
    if (valid.length) {
      if (activeToolId === 'pdf-analyser') {
        const existing = Array.isArray(currentFiles) ? currentFiles : [];
        const names = new Set(existing.map(f => f.name));
        const fresh = valid.filter(f => !names.has(f.name));
        setFiles([...existing, ...fresh]);
      } else {
        addFilesToStore(valid);
        navigate('/converter');
      }
    }
  }, [acceptedExts, activeToolId, currentFiles, setFiles, addFilesToStore, navigate]);

  const onDrop = useCallback((acceptedFiles) => {
    addFiles(acceptedFiles);
  }, [addFiles]);

  const onDropRaw = useCallback(async (e) => {
    e.preventDefault();
    const items = Array.from(e.dataTransfer.items || []);
    const hasFolder = items.some(i => i.webkitGetAsEntry?.()?.isDirectory);
    if (hasFolder) {
      const files = await readFolderEntries(items);
      addFiles(files);
    }
  }, [addFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: tool.accept,
    multiple: activeToolId !== 'pdf-analyser',
  });

  const handleFolderPick = useCallback((e) => {
    addFiles(Array.from(e.target.files || []));
  }, [addFiles]);

  const handleUpload = async () => {
    if (currentFiles.length === 0) return;

    if (activeToolId === 'pdf-analyser') {
      await runAnalysis(currentFiles[0]);
      return;
    }

    setProcessingStep(1);
    setUploadProgress(0);
    setActiveStep(1);

    const formData = new FormData();
    currentFiles.forEach(file => formData.append('files', file));

    try {
      const response = await axios.post(tool.endpoint, formData, {
        onUploadProgress: (e) => setUploadProgress(Math.round((e.loaded * 100) / e.total)),
      });
      if (response.data.jobs) {
        setJobIds(response.data.jobs.map(j => j.job_id));
        startPolling(response.data.jobs[0].job_id);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      const code = err.response?.data?.code;
      const msg = code === 'TOO_LARGE' ? 'File exceeds 25 MB limit.'
        : code === 'UNSUPPORTED_TYPE' ? 'File type not supported.'
        : code === 'INVALID_SIGNATURE' ? 'File appears corrupt or invalid.'
        : detail || 'Upload failed. Check file size or connection.';
      setError(msg);
      setProcessingStep(0);
    }
  };

  const runAnalysis = async (file) => {
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post('/analyse-pdf-quality', formData);
      setAnalysisResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed. The PDF might be corrupted or too large.');
    } finally {
      setLoading(false);
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
          setTimeout(poll, Math.min(1000 + attempts * 500, 5000));
        }
      } catch {
        setError('Polling error. Please try again.');
        setProcessingStep(0);
      }
    };
    poll();
  };

  const hasErrors = validationErrors.length > 0;

  return (
    <div id="ws-upload-stage">
      <div
        {...getRootProps()}
        onDrop={async (e) => { getRootProps().onDrop?.(e); await onDropRaw(e); }}
        className={`drop-zone ${isDragActive ? 'dragover' : ''} ${currentFiles.length > 0 ? 'has-file' : ''} ${hasErrors ? 'border-red-400' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="dz-icon mb-4">
          {currentFiles.length > 0
            ? <FileText size={48} className="text-primary mx-auto" />
            : <Upload size={48} className="mx-auto" />}
        </div>
        <div className="dz-title text-lg font-bold mb-2">
          {currentFiles.length === 1
            ? currentFiles[0].name
            : currentFiles.length > 1
              ? `${currentFiles.length} files selected`
              : `Select ${tool.title.split(' ')[0]} files`}
        </div>
        <p className="dz-sub text-text-muted text-[0.9rem]">
          {currentFiles.length > 0
            ? `${(currentFiles.reduce((a, f) => a + f.size, 0) / 1024 / 1024).toFixed(2)} MB`
            : `Drop files or folders here · ${acceptedExts?.join(', ') || 'any file'}`}
        </p>
      </div>

      {/* Folder picker button */}
      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 8, cursor: 'pointer', fontSize: 13, color: '#777', userSelect: 'none' }}>
        <FolderOpen size={15} />
        Add folder
        <input type="file" webkitdirectory="true" multiple style={{ display: 'none' }} onChange={handleFolderPick} />
      </label>

      <UploadErrorList
        errors={validationErrors}
        onDismiss={(i) => setValidationErrors(prev => prev.filter((_, idx) => idx !== i))}
        onClearAll={() => setValidationErrors([])}
      />

      {error && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-500 text-center rounded-lg text-sm font-bold">
          {error}
        </div>
      )}

      <button
        className="action-btn flex items-center justify-center gap-2"
        disabled={currentFiles.length === 0 || loading}
        onClick={handleUpload}
      >
        {loading && <Loader2 size={20} className="animate-spin" />}
        {loading ? 'Analysing…' : currentFiles.length > 0 ? tool.action : 'Upload a file to start'}
      </button>
    </div>
  );
};

export default Dropzone;
