import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { CloudUpload, FileText } from 'lucide-react';
import { useStore } from '../store';

const PILLS = ['PDF', 'DOCX', 'TXT', 'Images', '+15 more'];
const ACCEPT = '.docx,.doc,.pdf,.txt,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.mkv,.mp3,.wav,.flac,.aac,.ogg';

const Hero = () => {
  const navigate = useNavigate();
  const inputRef = useRef();
  const addFiles = useStore((state) => state.addFiles);
  const [dragActive, setDragActive] = useState(false);
  const [hover, setHover] = useState(false);

  const accept = (files) => {
    const list = Array.from(files || []);
    if (list.length === 0) return;
    addFiles(list);
    navigate('/converter');
  };

  const handleFile = (e) => accept(e.target.files);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    accept(e.dataTransfer.files);
  };

  return (
    <section className="relative overflow-hidden pt-16 pb-20 md:pt-24 md:pb-28 px-4">
      {/* Floating brand orbs */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="orb orb-primary animate-float-slow w-[520px] h-[520px] -top-32 left-1/4 -translate-x-1/2" />
        <div className="orb orb-indigo animate-float-slow w-[460px] h-[460px] top-24 right-1/4 translate-x-1/2" style={{ animationDelay: '2s' }} />
      </div>

      <div className="max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span className="inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full text-xs font-semibold tracking-wide bg-primary/10 text-primary border border-primary/20">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Built for Indian languages
          </span>

          <h1 className="font-display text-4xl md:text-6xl font-extrabold tracking-tight mb-5 leading-[1.05]">
            <span className="text-gradient">Indic File Converter</span>
            <br />
            <span className="text-gradient-brand">Without Limits</span>
          </h1>
          <p className="text-lg md:text-xl text-text-muted max-w-2xl mx-auto leading-relaxed">
            Convert your documents to any format. Fast, free, and secure — with
            perfect glyph rendering for Telugu, Devanagari, Tamil and more.
          </p>
        </motion.div>

        {/* Upload dropzone — front and center on landing */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-10"
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current.click(); }}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            className={`group relative cursor-pointer overflow-hidden rounded-radius-xl p-10 md:p-12 max-w-3xl mx-auto
              flex flex-col items-center justify-center min-h-[340px] glass shadow-shadow-lg
              border-2 border-dashed transition-all duration-300
              ${dragActive
                ? 'border-primary ring-4 ring-primary/15 scale-[1.01]'
                : 'border-border hover:border-primary/50'}`}
          >
            {/* inner glow */}
            <div className="absolute inset-0 -z-10 pointer-events-none">
              <div className="absolute -top-24 -left-24 w-64 h-64 rounded-full bg-primary/10 blur-3xl opacity-60 group-hover:opacity-90 transition-opacity" />
              <div className="absolute -bottom-24 -right-24 w-64 h-64 rounded-full bg-[var(--accent-indigo)]/10 blur-3xl opacity-50 group-hover:opacity-80 transition-opacity" />
            </div>

            <motion.div
              animate={{ y: dragActive || hover ? -8 : 0, scale: dragActive || hover ? 1.08 : 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              className="relative mb-6"
            >
              <div className="w-20 h-20 md:w-24 md:h-24 rounded-2xl flex items-center justify-center shadow-glow"
                style={{ background: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)' }}>
                <CloudUpload className="w-10 h-10 md:w-12 md:h-12 text-white" />
              </div>
              <AnimatePresence>
                {(dragActive || hover) && (
                  <motion.span
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    className="absolute -top-1.5 -right-1.5 w-7 h-7 bg-surface rounded-full shadow-shadow flex items-center justify-center"
                  >
                    <span className="w-2 h-2 bg-primary rounded-full animate-ping" />
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.div>

            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); inputRef.current.click(); }}
              className="px-8 py-3.5 rounded-xl text-white text-base font-bold tracking-wide bg-primary hover:bg-primary-hover transition-all hover:-translate-y-0.5 shadow-glow"
            >
              Choose Files
            </button>
            <p className="mt-4 text-text-muted text-sm">
              {dragActive ? 'Drop your files now' : 'or drag & drop here — free for everyone, no account needed'}
            </p>

            <div className="mt-8 flex items-center gap-2.5 flex-wrap justify-center opacity-70 group-hover:opacity-100 transition-opacity">
              {PILLS.map((p) => (
                <span key={p} className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium bg-surface-overlay text-text-muted border border-border">
                  <FileText className="w-3 h-3" /> {p}
                </span>
              ))}
            </div>

            <input
              ref={inputRef}
              type="file"
              multiple
              style={{ display: 'none' }}
              onChange={handleFile}
              accept={ACCEPT}
            />
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Hero;
