import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import { useFFmpeg } from '../hooks/useFFmpeg';
import { 
  FileText, 
  Upload, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  ArrowRight, 
  FolderOpen, 
  Download, 
  RefreshCw, 
  Plus, 
  Sparkles 
} from 'lucide-react';
import axios from 'axios';
import FormatSelector from '../components/FormatSelector';
import { motion, AnimatePresence } from 'framer-motion';

// Helper to format bytes
function formatBytes(bytes) {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Map of available output formats based on input file extension
// Formats handled by backend /convert (LibreOffice)
const LO_FORMATS = {
  'doc':  ['pdf', 'docx', 'odt', 'rtf', 'html', 'txt'],
  'docx': ['pdf', 'odt', 'rtf', 'html', 'txt', 'doc'],
  'odt':  ['pdf', 'docx', 'doc', 'rtf', 'html', 'txt'],
  'rtf':  ['pdf', 'docx', 'odt', 'html', 'txt'],
  'html': ['pdf', 'docx', 'odt', 'rtf', 'txt'],
  'htm':  ['pdf', 'docx', 'odt', 'rtf', 'txt'],
  'txt':  ['pdf', 'docx', 'odt', 'rtf', 'html'],
  'docm': ['pdf', 'docx', 'odt', 'rtf', 'txt'],
  'dotx': ['pdf', 'docx', 'odt', 'rtf', 'txt'],
  'dot':  ['pdf', 'docx', 'odt', 'rtf', 'txt'],
  'xls':  ['pdf', 'xlsx', 'csv', 'ods'],
  'xlsx': ['pdf', 'xls', 'csv', 'ods'],
  'csv':  ['pdf', 'xlsx', 'xls', 'ods'],
  'ods':  ['pdf', 'xlsx', 'xls', 'csv'],
  'ppt':  ['pdf', 'pptx', 'odp'],
  'pptx': ['pdf', 'ppt', 'odp'],
  'odp':  ['pdf', 'pptx', 'ppt'],
  'pps':  ['pdf', 'pptx', 'odp'],
  'ppsx': ['pdf', 'pptx', 'odp'],
  // PDF → LibreOffice can open and re-export (backend /convert has no image
  // target, so no 'jpg' here — every offered format maps to a real conversion)
  'pdf':  ['docx', 'odt', 'html', 'txt', 'rtf'],
};

const getAvailableOutputFormats = (ext) => {
  const normalized = ext.toLowerCase().replace('.', '');

  // LibreOffice-backed formats (includes pdf now)
  if (LO_FORMATS[normalized]) return LO_FORMATS[normalized];

  // Image formats (client-side FFmpeg / canvas)
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'ico', 'tiff'].includes(normalized)) {
    return ['png', 'jpg', 'pdf', 'webp', 'bmp'];
  }
  // Video formats (client-side FFmpeg)
  if (['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', '3gp'].includes(normalized)) {
    return ['mp4', 'webm', 'avi', 'mov', 'gif', 'mkv'];
  }
  // Audio formats (client-side FFmpeg)
  if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma', 'amr'].includes(normalized)) {
    return ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'];
  }
  return ['pdf', 'docx', 'txt'];
};

// Map of colors for file extensions
const getFileColor = (ext) => {
  const normalized = ext.toLowerCase().replace('.', '');
  if (['docx', 'doc'].includes(normalized)) return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
  if (normalized === 'pdf') return 'text-red-500 bg-red-500/10 border-red-500/20';
  if (normalized === 'txt') return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'ico', 'tiff'].includes(normalized)) return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
  if (['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'].includes(normalized)) return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
  if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(normalized)) return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
  return 'text-slate-500 bg-slate-500/10 border-slate-500/20';
};

export default function Converter() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Zustand Store
  const { 
    files, 
    addFiles, 
    updateFile, 
    clearFiles, 
    theme 
  } = useStore();

  // FFmpeg client-side hook
  const { 
    loaded: ffmpegLoaded, 
    loading: ffmpegLoading, 
    progress: ffmpegProgress, 
    load: loadFFmpeg, 
    convertFile: ffmpegConvert 
  } = useFFmpeg();

  // No auto-redirect — empty state shows "Choose Files" UI inline

  // Handle Drag & Drop Events
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
    const dropped = Array.from(e.dataTransfer.files || []);
    if (dropped.length > 0) {
      addFiles(dropped);
    }
  };

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length > 0) {
      addFiles(selected);
    }
  };

  const handleFolderSelect = (e) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length > 0) {
      addFiles(selected);
    }
  };

  const handleRemoveFile = (id) => {
    // Filter out the file from Zustand store
    const updated = files.filter(f => f.id !== id);
    useStore.getState().setFiles(updated.map(f => f.file).filter(Boolean));
  };

  // Main Conversion Dispatcher
  const handleConvertAll = async () => {
    const idleFiles = files.filter(f => f.status !== 'done' && f.status !== 'converting' && f.outputFormat);
    if (idleFiles.length === 0) return;

    setIsProcessing(true);

    // Process files sequentially to avoid browser CPU lockups and FFmpeg filesystem collisions
    for (const fileItem of idleFiles) {
      await processFile(fileItem);
    }

    setIsProcessing(false);
  };

  const processFile = async (fileItem) => {
    const { id, file, name, outputFormat } = fileItem;
    
    // Safety check: if native file object was lost due to page refresh / localStorage restore
    if (!file) {
      updateFile(id, { 
        status: 'error', 
        error: 'File contents lost. Please remove and re-upload this file.' 
      });
      return;
    }

    updateFile(id, { status: 'converting', progress: 10, error: null });

    const ext = name.split('.').pop().toLowerCase();
    const outExt = outputFormat.toLowerCase();

    // 1. Client-Side FFmpeg Conversions (Image/Video/Audio)
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'ico', 'tiff'].includes(ext);
    const isVideo = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'].includes(ext);
    const isAudio = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(ext);

    const targetImage = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico', 'tiff'].includes(outExt);
    const targetVideo = ['mp4', 'webm', 'avi', 'mov', 'gif'].includes(outExt);
    const targetAudio = ['mp3', 'wav', 'flac', 'aac', 'ogg'].includes(outExt);

    try {
      if ((isImage && targetImage) || (isVideo && targetVideo) || (isAudio && targetAudio)) {
        if (!ffmpegLoaded) {
          updateFile(id, { progress: 20 });
          await loadFFmpeg();
        }
        updateFile(id, { progress: 40 });
        const convertedBlob = await ffmpegConvert(file, outExt);
        const downloadUrl = URL.createObjectURL(convertedBlob);
        updateFile(id, { status: 'done', progress: 100, downloadUrl });
        return;
      }

      // Helper: poll a job ID until finished/failed
      const pollJob = (jobId) => new Promise((resolve) => {
        let attempts = 0;
        const poll = async () => {
          try {
            const res = await axios.get(`/status/${jobId}`);
            const status = res.data.status;
            if (status === 'finished') {
              updateFile(id, { status: 'done', progress: 100, downloadUrl: `/download/${jobId}` });
              resolve();
            } else if (status === 'failed') {
              updateFile(id, { status: 'error', error: res.data.exc_info || 'Server conversion failed.' });
              resolve();
            } else {
              attempts++;
              updateFile(id, { progress: Math.min(70 + attempts * 3, 98) });
              setTimeout(poll, Math.min(1000 + attempts * 500, 5000));
            }
          } catch (e) {
            updateFile(id, { status: 'error', error: 'Failed to retrieve job status.' });
            resolve();
          }
        };
        poll();
      });

      // 2a. LibreOffice general document conversion (/convert endpoint)
      // Exception: pdf->docx uses legacy /upload (pdfminer, higher quality)
      const isPdfToDocx = ext === 'pdf' && outExt === 'docx';
      if (!isPdfToDocx && LO_FORMATS[ext] && LO_FORMATS[ext].includes(outExt)) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('target_format', outExt);
        updateFile(id, { progress: 25 });
        const response = await axios.post('/convert', formData, {
          onUploadProgress: (e) => {
            const pct = Math.round((e.loaded * 35) / e.total) + 25;
            updateFile(id, { progress: pct });
          }
        });
        const jobId = response.data.job_id;
        if (!jobId) throw new Error('Server did not return a job ID.');
        updateFile(id, { progress: 70 });
        await pollJob(jobId);
        return;
      }

      // 2b. Legacy specific-route conversions (DOCX/TXT -> PDF, PDF -> DOCX)
      const isDocx = ['docx', 'doc'].includes(ext);
      const isPdf = ext === 'pdf';
      const isTxt = ext === 'txt';
      const targetPdf = outExt === 'pdf';
      const targetDocx = outExt === 'docx';

      if ((isDocx && targetPdf) || (isTxt && targetPdf) || (isPdf && targetDocx)) {
        const formData = new FormData();
        formData.append('files', file);
        updateFile(id, { progress: 25 });
        const response = await axios.post('/upload', formData, {
          onUploadProgress: (e) => {
            const pct = Math.round((e.loaded * 35) / e.total) + 25;
            updateFile(id, { progress: pct });
          }
        });
        const job = response.data.jobs?.[0];
        if (!job || !job.job_id) throw new Error('Server upload succeeded but did not return a job ID.');
        updateFile(id, { progress: 70 });
        await pollJob(job.job_id);
        return;
      }

      // 3. Unsupported combination — tell user clearly
      updateFile(id, {
        status: 'error',
        error: `Converting .${ext} → .${outExt} is not yet supported. Supported outputs for .${ext}: ${(LO_FORMATS[ext] || ['pdf', 'docx']).join(', ')}.`
      });
      return;

      // eslint-disable-next-line no-unreachable
      let simulatedBlob;
      let mime = 'application/octet-stream';

      if (outExt === 'txt') {
        simulatedBlob = new Blob([`INDICPDF TEXT CONVERTER\n=======================\nFile Name: ${name}\nOriginal Size: ${file.size} bytes\n\n[Successfully extracted plain text representation]\n`], { type: 'text/plain' });
        mime = 'text/plain';
      } else if (outExt === 'jpg' || outExt === 'jpeg') {
        const canvas = document.createElement('canvas');
        canvas.width = 600;
        canvas.height = 450;
        const ctx = canvas.getContext('2d');
        
        // Premium Mock Page Design
        ctx.fillStyle = '#111827';
        ctx.fillRect(0, 0, 600, 450);
        
        ctx.fillStyle = '#FF4B4B';
        ctx.font = 'bold 24px sans-serif';
        ctx.fillText('IndicPDF Converter Core', 50, 70);
        
        ctx.fillStyle = '#9CA3AF';
        ctx.font = '16px monospace';
        ctx.fillText(`Source: ${name}`, 50, 130);
        ctx.fillText(`Target Form: JPEG image`, 50, 160);
        ctx.fillText(`Output Code: OK-200`, 50, 190);
        
        ctx.strokeStyle = '#374151';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(50, 230);
        ctx.lineTo(550, 230);
        ctx.stroke();

        ctx.fillStyle = '#10B981';
        ctx.font = 'bold 18px sans-serif';
        ctx.fillText('✓ Document render completed successfully.', 50, 280);

        ctx.fillStyle = '#6B7280';
        ctx.font = '12px sans-serif';
        ctx.fillText('Processed locally in high-fidelity browser context.', 50, 390);

        const canvasBlobPromise = new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));
        simulatedBlob = await canvasBlobPromise;
        mime = 'image/jpeg';
      } else if (outExt === 'pdf') {
        simulatedBlob = new Blob([`%PDF-1.4\n%mock pdf format for ${name}\n`], { type: 'application/pdf' });
        mime = 'application/pdf';
      } else {
        simulatedBlob = new Blob([`Mock formatted content in ${outExt.toUpperCase()}`], { type: 'application/octet-stream' });
      }

      await new Promise(r => setTimeout(r, 800));
      const downloadUrl = URL.createObjectURL(simulatedBlob);
      updateFile(id, { status: 'done', progress: 100, downloadUrl });

    } catch (e) {
      updateFile(id, { status: 'error', error: e.message || 'An unexpected conversion error occurred.' });
    }
  };

  // Computed Values
  const allReady = files.length > 0 && files.every(f => f.outputFormat || f.status === 'done');
  const finishedCount = files.filter(f => f.status === 'done').length;
  const isAllDone = files.length > 0 && files.every(f => f.status === 'done');
  const overallProgress = files.length > 0 
    ? Math.round(files.reduce((sum, f) => sum + (f.progress || 0), 0) / files.length)
    : 0;

  return (
    <div className={`min-h-[85vh] transition-colors duration-300 ${theme === 'dark' ? 'bg-[#0B0B0B] text-white' : 'bg-[#F8F9FA] text-[#111827]'}`}>
      
      {/* Dragover Blur Overlay */}
      {dragActive && (
        <div 
          className="fixed inset-0 bg-primary/10 backdrop-blur-md z-50 flex items-center justify-center pointer-events-none"
          style={{ border: '4px dashed #FF4B4B' }}
        >
          <div className="text-center p-8 bg-white dark:bg-zinc-900 border border-primary/20 rounded-2xl shadow-2xl max-w-sm">
            <Upload className="w-16 h-16 text-primary mx-auto animate-bounce mb-4" />
            <h3 className="text-xl font-bold mb-2">Drop your files</h3>
            <p className="text-text-muted text-sm">Add them directly to your workspace queue</p>
          </div>
        </div>
      )}

      <div className="max-w-[950px] mx-auto px-6 py-12"
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
      >
        
        {/* Header Section */}
        <div className="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-black mb-2 tracking-tight flex items-center gap-2">
              Workspace Converter <Sparkles size={24} className="text-primary animate-pulse" />
            </h1>
            <p className="text-text-muted leading-relaxed">
              Batch convert Indic scripts, images, audio and video files locally and securely.
            </p>
          </div>

          {files.length > 0 && (
            <div className="bg-surface-overlay border border-border dark:bg-zinc-900/60 dark:border-zinc-800/80 px-5 py-4 rounded-radius shadow-shadow flex flex-col min-w-[200px]">
              <div className="flex justify-between items-center text-xs font-bold text-text-muted uppercase tracking-wider mb-2">
                <span>Batch Status</span>
                <span>{finishedCount} / {files.length} Done</span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-zinc-800 h-2 rounded-full overflow-hidden mb-2">
                <div 
                  className="bg-primary h-full transition-all duration-500 rounded-full"
                  style={{ width: `${overallProgress}%` }}
                />
              </div>
              <span className="text-[10px] text-primary font-black uppercase text-right tracking-widest">{overallProgress}% COMPLETED</span>
            </div>
          )}
        </div>

        {/* Files Workspace Area */}
        <div className="workspace-card p-6 border border-border dark:bg-zinc-900/40 dark:border-zinc-800/60 shadow-shadow-lg rounded-radius-xl min-h-[350px] flex flex-col">
          <AnimatePresence mode="popLayout">
            {files.length === 0 ? (
              <motion.div 
                key="empty-state"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex-grow flex flex-col items-center justify-center text-center py-16"
              >
                <div className="w-16 h-16 bg-primary/10 border border-primary/20 rounded-2xl flex items-center justify-center text-3xl mb-5 text-primary">
                  <Upload size={24} />
                </div>
                <h3 className="text-xl font-bold mb-1">No files in your workspace</h3>
                <p className="text-text-muted text-sm max-w-[340px] mb-6">
                  Select, drag, or drop multiple files or folders here to configure your format conversions.
                </p>
                <div className="flex gap-4">
                  <button 
                    onClick={() => fileInputRef.current.click()}
                    className="py-3 px-6 bg-primary hover:bg-primary-hover text-white rounded-lg font-black text-sm transition-all hover:shadow-glow"
                  >
                    Choose Files
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div key="files-list" className="flex-grow space-y-4">
                {files.map((fileItem) => {
                  const availableFormats = getAvailableOutputFormats(fileItem.name.split('.').pop());
                  const fileColor = getFileColor(fileItem.name.split('.').pop());
                  
                  return (
                    <motion.div
                      key={fileItem.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                      className="relative overflow-visible bg-white dark:bg-zinc-900 border border-border dark:border-zinc-800/80 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm hover:shadow-md transition-shadow"
                    >
                      {/* File Info Left */}
                      <div className="flex items-center gap-4 min-w-0 flex-grow md:flex-grow-0 md:max-w-[50%]">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl shrink-0 border ${fileColor}`}>
                          <FileText size={20} />
                        </div>
                        <div className="min-w-0">
                          <h4 className="font-bold text-sm text-text truncate max-w-full" title={fileItem.name}>
                            {fileItem.name}
                          </h4>
                          <p className="text-xs text-text-muted mt-0.5">
                            {formatBytes(fileItem.size)} · {fileItem.name.split('.').pop().toUpperCase()}
                          </p>
                        </div>
                      </div>

                      {/* Config Area Right */}
                      <div className="flex items-center flex-wrap md:flex-nowrap gap-4 justify-between md:justify-end shrink-0">
                        
                        {/* Format Select Dropdown */}
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-text-muted uppercase tracking-wider">to</span>
                          <FormatSelector
                            formats={availableFormats}
                            value={fileItem.outputFormat}
                            onChange={(val) => updateFile(fileItem.id, { outputFormat: val })}
                            disabled={fileItem.status === 'converting' || fileItem.status === 'done'}
                          />
                        </div>

                        {/* Status Badge */}
                        <div className="min-w-[110px] text-center flex justify-center">
                          {fileItem.status === 'converting' && (
                            <span className="inline-flex items-center gap-1.5 text-primary text-xs font-black uppercase tracking-wider">
                              <Loader2 size={13} className="animate-spin" />
                              {fileItem.progress || 10}%
                            </span>
                          )}
                          {fileItem.status === 'done' && (
                            <span className="inline-flex items-center gap-1 text-emerald-500 text-xs font-black uppercase tracking-wider">
                              <CheckCircle2 size={14} /> Done
                            </span>
                          )}
                          {fileItem.status === 'error' && (
                            <span className="inline-flex items-center gap-1 text-red-500 text-xs font-black uppercase tracking-wider" title={fileItem.error}>
                              <AlertCircle size={14} /> Error
                            </span>
                          )}
                          {fileItem.status === 'idle' && (
                            <span className="inline-flex items-center gap-1 text-text-muted text-xs font-bold uppercase tracking-wider">
                              Ready
                            </span>
                          )}
                        </div>

                        {/* Download / Action Button */}
                        <div className="flex items-center gap-2">
                          {fileItem.status === 'done' && fileItem.downloadUrl ? (
                            <a 
                              href={fileItem.downloadUrl}
                              download={`IndicPDF_${fileItem.name.replace(/\.[^.]+$/, '')}.${fileItem.outputFormat}`}
                              className="inline-flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold py-2.5 px-4 rounded-lg transition-colors hover:shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                            >
                              <Download size={14} /> Download
                            </a>
                          ) : (
                            <button
                              onClick={() => handleRemoveFile(fileItem.id)}
                              disabled={fileItem.status === 'converting'}
                              className="text-text-muted hover:text-red-500 transition-colors p-2 disabled:opacity-30 disabled:cursor-not-allowed"
                              aria-label="Remove file"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* File Card Progress Indicator */}
                      {fileItem.status === 'converting' && (
                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-100 dark:bg-zinc-800 rounded-b-xl overflow-hidden">
                          <div 
                            className="bg-primary h-full transition-all duration-300"
                            style={{ width: `${fileItem.progress || 10}%` }}
                          />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Bottom Toolbar */}
          {files.length > 0 && (
            <div className="mt-8 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
              
              {/* Left Buttons: Add More */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => fileInputRef.current.click()}
                  disabled={isProcessing}
                  className="flex items-center gap-1.5 py-2.5 px-4 bg-surface-overlay dark:bg-zinc-900 border border-border rounded-lg text-xs font-bold text-text-muted hover:text-text hover:border-text transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus size={14} /> Add files
                </button>
                <button
                  onClick={() => folderInputRef.current.click()}
                  disabled={isProcessing}
                  className="flex items-center gap-1.5 py-2.5 px-4 bg-surface-overlay dark:bg-zinc-900 border border-border rounded-lg text-xs font-bold text-text-muted hover:text-text hover:border-text transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FolderOpen size={14} /> Add folder
                </button>
              </div>

              {/* Right Buttons: Clear & Convert */}
              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <button
                  onClick={clearFiles}
                  disabled={isProcessing}
                  className="py-2.5 px-4 rounded-lg text-xs font-bold text-text-muted hover:text-red-500 hover:border-red-500 border border-transparent transition-all disabled:opacity-50"
                >
                  Clear all
                </button>

                {isAllDone ? (
                  <button
                    onClick={() => {
                      clearFiles();
                      navigate('/');
                    }}
                    className="flex items-center justify-center gap-1.5 py-3 px-6 bg-primary text-white rounded-lg font-black text-sm transition-all hover:bg-primary-hover hover:shadow-glow"
                  >
                    <RefreshCw size={14} /> Start Fresh
                  </button>
                ) : (
                  <button
                    onClick={handleConvertAll}
                    disabled={!allReady || isProcessing}
                    className="flex items-center justify-center gap-2 py-3 px-6 bg-primary text-white rounded-lg font-black text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary-hover hover:shadow-glow hover:-translate-y-0.5 active:translate-y-0"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Converting...
                      </>
                    ) : (
                      <>
                        Convert All
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Hidden file & folder inputs */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        style={{ display: 'none' }}
        accept=".docx,.doc,.pdf,.txt,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.avi,.mov,.mkv,.mp3,.wav,.flac,.aac,.ogg"
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        webkitdirectory="true"
        onChange={handleFolderSelect}
        style={{ display: 'none' }}
      />
    </div>
  );
}
