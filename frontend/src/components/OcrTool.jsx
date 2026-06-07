import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import ToolLayout from './ToolLayout';
import ProcessingSteps from './ProcessingSteps';
import SuccessView from './SuccessView';

const LANGUAGES = [
  { value: 'auto', label: 'Auto Detect' },
  { value: 'hindi', label: 'Hindi (Devanagari)' },
  { value: 'telugu', label: 'Telugu' },
  { value: 'tamil', label: 'Tamil' },
  { value: 'bengali', label: 'Bengali' },
  { value: 'gujarati', label: 'Gujarati' },
  { value: 'kannada', label: 'Kannada' },
  { value: 'malayalam', label: 'Malayalam' },
  { value: 'odia', label: 'Odia' },
  { value: 'punjabi', label: 'Punjabi' },
  { value: 'english', label: 'English' },
];

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
};

export default function OcrTool() {
  const [file, setFile] = useState(null);
  const [lang, setLang] = useState('auto');
  const [status, setStatus] = useState('idle');
  const [resultUrl, setResultUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [steps, setSteps] = useState([
    { label: 'Uploading file', state: 'pending' },
    { label: 'Running OCR', state: 'pending' },
    { label: 'Extracting text', state: 'pending' },
  ]);

  const updateStep = (index, state) =>
    setSteps(prev => prev.map((s, i) => i === index ? { ...s, state } : s));

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: ACCEPTED_TYPES, multiple: false,
  });

  const handleConvert = async () => {
    if (!file) return;
    setStatus('uploading');
    updateStep(0, 'active');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lang', lang);
      const { data } = await axios.post('/ocr', formData);
      updateStep(0, 'done');
      updateStep(1, 'active');
      setStatus('processing');
      const poll = setInterval(async () => {
        try {
          const { data: s } = await axios.get(`/status/${data.job_id}`);
          if (s.status === 'finished') {
            clearInterval(poll);
            updateStep(1, 'done');
            updateStep(2, 'done');
            setResultUrl(`/download/${data.job_id}`);
            setStatus('done');
          } else if (s.status === 'failed') {
            clearInterval(poll);
            setStatus('error');
            setErrorMsg('OCR processing failed. Please try again.');
          }
        } catch {
          clearInterval(poll);
          setStatus('error');
          setErrorMsg('Connection error while checking status.');
        }
      }, 2000);
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.response?.data?.detail || 'Upload failed.');
      updateStep(0, 'error');
    }
  };

  const handleReset = () => {
    setFile(null); setStatus('idle'); setResultUrl(null); setErrorMsg('');
    setSteps(steps.map(s => ({ ...s, state: 'pending' })));
  };

  return (
    <ToolLayout title="OCR — Extract Text from Scanned Documents" description="Upload a scanned PDF or image. We'll extract the text using Tesseract with full Indic script support.">
      {status === 'idle' && (
        <div className="workspace-card p-8">
          <div className="mb-6">
            <label className="block text-sm font-black uppercase tracking-widest text-text-muted mb-2">Document Language</label>
            <select value={lang} onChange={e => setLang(e.target.value)} className="w-full bg-surface border border-border rounded-xl p-3 text-text font-semibold focus:outline-none focus:border-primary">
              {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>
          <div {...getRootProps()} className={`drop-zone ${isDragActive ? 'dragover' : ''} ${file ? 'has-file' : ''}`}>
            <input {...getInputProps()} />
            {file ? (
              <div><p className="text-2xl mb-2">📄</p><p className="font-black text-text">{file.name}</p><p className="text-text-muted text-sm mt-1">{(file.size / 1024).toFixed(1)} KB</p></div>
            ) : (
              <div><p className="text-4xl mb-4">🔍</p><p className="font-black text-lg">Drop a scanned PDF or image here</p><p className="text-text-muted text-sm mt-2">PDF, JPG, PNG, TIFF supported</p></div>
            )}
          </div>
          <button className="action-btn" disabled={!file} onClick={handleConvert}>Extract Text</button>
        </div>
      )}
      {(status === 'uploading' || status === 'processing') && <ProcessingSteps steps={steps} />}
      {status === 'done' && <SuccessView downloadUrl={resultUrl} fileName={`${file?.name?.replace(/\.[^.]+$/, '')}_ocr.txt`} onReset={handleReset} message="Text extracted successfully!" />}
      {status === 'error' && (
        <div className="workspace-card p-8 text-center">
          <p className="text-red-500 font-black text-lg mb-4">⚠ {errorMsg}</p>
          <button className="action-btn" onClick={handleReset}>Try Again</button>
        </div>
      )}
    </ToolLayout>
  );
}
