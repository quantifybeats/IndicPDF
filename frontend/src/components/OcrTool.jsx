import React, { useState, useCallback, useRef } from 'react';
import axios from 'axios';
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
  { value: 'sanskrit', label: 'Sanskrit' },
  { value: 'english', label: 'English' },
];

export default function OcrTool() {
  const [file, setFile] = useState(null);
  const [lang, setLang] = useState('auto');
  const [status, setStatus] = useState('idle');
  const [resultUrl, setResultUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef();

  const handleFileSelect = (selected) => {
    if (selected) setFile(selected);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  }, []);

  const handleConvert = async () => {
    if (!file) return;
    setStatus('uploading');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lang', lang);
      const { data } = await axios.post('/ocr', formData);
      setStatus('processing');
      const poll = setInterval(async () => {
        try {
          const { data: s } = await axios.get(`/status/${data.job_id}`);
          if (s.status === 'finished') {
            clearInterval(poll);
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
    }
  };

  const handleReset = () => {
    setFile(null);
    setStatus('idle');
    setResultUrl(null);
    setErrorMsg('');
  };

  if (status === 'done') {
    return (
      <div style={{ background: '#fff', minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <SuccessView
          downloadUrl={resultUrl}
          fileName={`${file?.name?.replace(/\.[^.]+$/, '')}_ocr.txt`}
          onReset={handleReset}
          message="Text extracted successfully!"
        />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div style={{ background: '#fff', minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ color: '#FF4B4B', fontSize: 16, fontWeight: 600, marginBottom: 24 }}>⚠ {errorMsg}</p>
          <button
            onClick={handleReset}
            style={{ background: '#FF4B4B', color: '#fff', border: 'none', borderRadius: 4, padding: '12px 32px', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (status === 'uploading' || status === 'processing') {
    return (
      <div style={{ background: '#fff', minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 48, height: 48, border: '4px solid #E8E8E8', borderTopColor: '#FF4B4B', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 24px' }}></div>
          <p style={{ fontSize: 16, color: '#555', fontWeight: 600 }}>
            {status === 'uploading' ? 'Uploading your file...' : 'Running OCR — extracting text...'}
          </p>
          <p style={{ fontSize: 13, color: '#999', marginTop: 8 }}>This may take a minute for large files.</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: '#fff', minHeight: '80vh' }}>
      {/* Hero section */}
      <div style={{ textAlign: 'center', padding: '60px 24px 48px' }}>
        <h1 style={{ fontSize: 36, fontWeight: 700, color: '#FF4B4B', marginBottom: 12 }}>
          Optical Character Recognition (OCR). Online &amp; Free
        </h1>
        <p style={{ fontSize: 18, color: '#777', marginBottom: 40 }}>
          Convert Scanned Documents and Images into Text
        </p>

        {/* Dark upload box */}
        <div style={{ background: '#2D2D2D', borderRadius: 8, padding: '48px 40px', maxWidth: 680, margin: '0 auto' }}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 16 }}>
            <button
              onClick={() => inputRef.current.click()}
              style={{ background: '#FF4B4B', color: '#fff', border: 'none', borderRadius: 4, padding: '14px 32px', fontSize: 16, fontWeight: 600, cursor: 'pointer' }}
              onMouseEnter={e => e.currentTarget.style.background = '#e03e3e'}
              onMouseLeave={e => e.currentTarget.style.background = '#FF4B4B'}
            >
              Choose Files
            </button>
          </div>
          {file ? (
            <p style={{ color: '#ddd', fontSize: 14, margin: 0 }}>
              Selected: <strong style={{ color: '#fff' }}>{file.name}</strong>{' '}
              ({(file.size / 1024).toFixed(1)} KB)
            </p>
          ) : (
            <p style={{ color: '#888', fontSize: 13, margin: 0 }}>
              {dragOver ? 'Drop the file here!' : 'Drop PDF or image here. PDF, JPG, PNG, TIFF supported.'}
            </p>
          )}
          <input
            ref={inputRef}
            type="file"
            style={{ display: 'none' }}
            accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif"
            onChange={e => handleFileSelect(e.target.files[0])}
          />
        </div>

        {/* Language selector */}
        <div style={{ maxWidth: 680, margin: '32px auto 0', textAlign: 'left' }}>
          <label style={{ display: 'block', fontSize: 14, fontWeight: 600, color: '#555', marginBottom: 8 }}>
            Select language used in your document
          </label>
          <select
            value={lang}
            onChange={e => setLang(e.target.value)}
            style={{ width: '100%', border: '1px solid #E8E8E8', borderRadius: 4, padding: '10px 14px', fontSize: 14, color: '#333', background: '#fff', cursor: 'pointer' }}
          >
            {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </div>

        {/* Recognize button */}
        <div style={{ maxWidth: 680, margin: '20px auto 0' }}>
          <button
            onClick={handleConvert}
            disabled={!file}
            style={{
              width: '100%', background: file ? '#FF4B4B' : '#ccc', color: '#fff',
              border: 'none', borderRadius: 4, padding: '16px 0', fontSize: 16,
              fontWeight: 700, cursor: file ? 'pointer' : 'not-allowed', letterSpacing: 0.5,
            }}
            onMouseEnter={e => { if (file) e.currentTarget.style.background = '#e03e3e'; }}
            onMouseLeave={e => { if (file) e.currentTarget.style.background = '#FF4B4B'; }}
          >
            Recognize
          </button>
        </div>
      </div>

      {/* How to section */}
      <div style={{ background: '#F7F7F7', padding: '60px 24px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#333', textAlign: 'center', marginBottom: 40 }}>
            How to recognize text from image?
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 40 }}>
            {[
              { step: '1', title: 'Upload your file', desc: 'Click "Choose Files" or drag and drop your scanned PDF or image onto the upload area.' },
              { step: '2', title: 'Select language', desc: 'Choose the language of the text in your document from the dropdown for best OCR accuracy.' },
              { step: '3', title: 'Download text', desc: 'Click "Recognize" and download the extracted text file once processing is complete.' },
            ].map(item => (
              <div key={item.step} style={{ textAlign: 'center' }}>
                <div style={{ width: 48, height: 48, borderRadius: '50%', background: '#FF4B4B', color: '#fff', fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                  {item.step}
                </div>
                <h4 style={{ fontSize: 15, fontWeight: 700, color: '#333', marginBottom: 8 }}>{item.title}</h4>
                <p style={{ fontSize: 14, color: '#777', lineHeight: 1.6, margin: 0 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
