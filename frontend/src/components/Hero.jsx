import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';

const Hero = () => {
  const navigate = useNavigate();
  const inputRef = useRef();
  const addFiles = useStore((state) => state.addFiles);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    addFiles(files);
    navigate('/converter');
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length > 0) {
      addFiles(files);
      navigate('/converter');
    }
  };

  return (
    <section style={{ textAlign: 'center', padding: '60px 24px 48px', background: '#fff' }} className="transition-colors duration-300 dark:bg-bg">
      <h1 className="hero-h1 text-primary" style={{ fontSize: 42, fontWeight: 700, marginBottom: 12, fontFamily: 'inherit' }}>
        Indic File Converter
      </h1>
      <p className="hero-sub text-text-muted" style={{ fontSize: 18, marginBottom: 40 }}>
        Convert your Indic documents to any format
      </p>

      {/* Dark upload box */}
      <div 
        className={`hero-box transition-all duration-300 ${dragActive ? 'scale-102 ring-2 ring-primary bg-[#3A3A3A]' : 'bg-[#2D2D2D]'}`}
        style={{ borderRadius: 8, padding: '48px 40px', maxWidth: 680, margin: '0 auto', border: dragActive ? '2px dashed #FF4B4B' : '2px dashed transparent' }}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
      >
        <div className="hero-btn-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 16 }}>
          <button
            onClick={() => inputRef.current.click()}
            style={{ background: '#FF4B4B', color: '#fff', border: 'none', borderRadius: 4, padding: '14px 32px', fontSize: 16, fontWeight: 600, cursor: 'pointer', letterSpacing: 0.3 }}
            onMouseEnter={e => e.currentTarget.style.background = '#e03e3e'}
            onMouseLeave={e => e.currentTarget.style.background = '#FF4B4B'}
          >
            Choose Files
          </button>
        </div>
        <p style={{ color: '#888', fontSize: 13, margin: 0 }}>
          {dragActive ? 'Drop your files now!' : 'Drop files here. Free for everyone, no account needed.'}
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={handleFile}
          accept=".docx,.doc,.pdf,.txt,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.mkv,.mp3,.wav,.flac,.aac,.ogg"
        />
      </div>
    </section>
  );
};

export default Hero;
