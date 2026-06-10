// frontend/src/pages/ReconstructionTool.jsx
import React, { useState, useCallback, useRef } from 'react';
import axios from 'axios';

const MAX_FILE_BYTES = 25 * 1024 * 1024;
const MAX_FILES = 10;
const SUPPORTED = ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];

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

// Client-side pre-check (QA F10): reject before any bytes leave the browser.
export function validateFiles(fileList) {
  const accepted = [];
  const rejected = [];
  for (const file of fileList) {
    const ext = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!SUPPORTED.includes(ext)) {
      rejected.push({ file, reason: `Unsupported type ${ext}` });
    } else if (file.size > MAX_FILE_BYTES) {
      rejected.push({ file, reason: 'Exceeds the 25 MB limit' });
    } else if (accepted.length >= MAX_FILES) {
      rejected.push({ file, reason: `Max ${MAX_FILES} files per batch` });
    } else {
      accepted.push(file);
    }
  }
  return { accepted, rejected };
}

const POLL_MS = 2000;

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const tone = pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-32 h-2 rounded bg-gray-200 overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm tabular-nums">{pct}%</span>
    </div>
  );
}

function ResultCard({ item, onExport }) {
  // QA F3: explicit failure state — never render a success-looking panel
  // for processing_incomplete results.
  if (item.status === 'failed') {
    return (
      <div className="border border-red-300 bg-red-50 rounded-lg p-4">
        <p className="font-semibold text-red-700">✗ {item.name} — processing failed</p>
        {item.payload?.quality_assessment?.detected_issues?.map((issue) => (
          <p key={issue} className="text-sm text-red-600 font-mono">{issue}</p>
        ))}
        {item.payload?.quality_assessment?.recommendations?.map((rec) => (
          <p key={rec} className="text-sm text-red-600">{rec}</p>
        ))}
        {!item.payload && <p className="text-sm text-red-600">{item.error}</p>}
      </div>
    );
  }
  if (item.status !== 'done') {
    return (
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <span>{item.name}</span>
        <span className="text-sm text-gray-500 capitalize animate-pulse">{item.status}…</span>
      </div>
    );
  }
  const p = item.payload;
  return (
    <div className="border border-green-300 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="font-semibold text-green-700">✓ {item.name}</p>
        <button
          onClick={() => onExport(item)}
          className="px-3 py-1.5 rounded bg-orange-700 text-white text-sm hover:bg-orange-800"
        >
          {item.exporting ? 'Preparing PDF…' : 'Download PDF'}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <span>Document confidence</span>
        <ConfidenceBar value={p.confidence_scores?.document} />
        <span>Word average</span>
        <ConfidenceBar value={p.confidence_scores?.word_avg} />
        <span>Language</span>
        <span>{p.language_metadata?.detected_language} ({p.language_metadata?.script})</span>
      </div>
      {p.warning_flags?.length > 0 && (
        <p className="text-sm text-yellow-700">⚠ {p.warning_flags.join(', ')}</p>
      )}
      <details>
        <summary className="cursor-pointer text-sm text-gray-600">Reconstructed text</summary>
        <pre className="mt-2 p-3 bg-gray-50 rounded text-sm whitespace-pre-wrap max-h-64 overflow-auto">
          {p.clean_text}
        </pre>
      </details>
    </div>
  );
}

export default function ReconstructionTool() {
  const [items, setItems] = useState([]);
  const [rejectedLocal, setRejectedLocal] = useState([]);
  const [lang, setLang] = useState('auto');
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef();

  const updateItem = (jobId, patch) =>
    setItems((prev) => prev.map((it) => (it.jobId === jobId ? { ...it, ...patch } : it)));

  const pollJob = useCallback((jobId) => {
    const poll = setInterval(async () => {
      try {
        const { data: s } = await axios.get(`/status/${jobId}`);
        if (s.status === 'finished') {
          clearInterval(poll);
          try {
            const { data: payload } = await axios.get(`/api/process/result/${jobId}`);
            updateItem(jobId, { status: payload.success ? 'done' : 'failed', payload });
          } catch (e) {
            // 422 carries the diagnostic payload in the body (QA F3)
            if (e.response?.status === 422) {
              updateItem(jobId, { status: 'failed', payload: e.response.data });
            } else {
              updateItem(jobId, { status: 'failed', error: 'Could not fetch result.' });
            }
          }
        } else if (s.status === 'failed') {
          clearInterval(poll);
          updateItem(jobId, { status: 'failed', error: 'Processing job failed.' });
        }
      } catch {
        clearInterval(poll);
        updateItem(jobId, { status: 'failed', error: 'Lost contact with server.' });
      }
    }, POLL_MS);
  }, []);

  const handleFiles = async (fileList) => {
    const { accepted, rejected } = validateFiles(Array.from(fileList));
    setRejectedLocal(rejected);
    if (!accepted.length) return;

    const formData = new FormData();
    accepted.forEach((f) => formData.append('files', f));
    formData.append('lang', lang);
    try {
      const { data } = await axios.post('/api/process', formData);
      const next = data.jobs.map((j) => ({
        jobId: j.job_id,
        name: j.original_name,
        status: j.job_id ? 'processing' : 'failed',
        error: j.detail,
      }));
      setItems(next);
      next.filter((it) => it.jobId).forEach((it) => pollJob(it.jobId));
    } catch (e) {
      setRejectedLocal([
        { file: { name: 'upload' }, reason: e.response?.data?.detail || 'Upload failed.' },
      ]);
    }
  };

  const handleExport = async (item) => {
    updateItem(item.jobId, { exporting: true });
    try {
      const { data } = await axios.post('/api/export/pdf', {
        clean_text: item.payload.clean_text,
        filename: item.name,
      });
      const poll = setInterval(async () => {
        const { data: s } = await axios.get(`/status/${data.job_id}`);
        if (s.status === 'finished') {
          clearInterval(poll);
          updateItem(item.jobId, { exporting: false });
          window.location.href = `/download/${data.job_id}`;
        } else if (s.status === 'failed') {
          clearInterval(poll);
          updateItem(item.jobId, { exporting: false, error: 'PDF export failed.' });
        }
      }, POLL_MS);
    } catch (e) {
      updateItem(item.jobId, {
        exporting: false,
        error: e.response?.data?.detail || 'PDF export failed.',
      });
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-6">
      <h1 className="text-3xl font-bold">Document Reconstruction</h1>
      <p className="text-gray-600">
        Confidence-scored text extraction for Indic-script PDFs, scans, and DOCX.
        Up to {MAX_FILES} files, 25 MB each.
      </p>

      <label className="block text-sm font-medium" htmlFor="recon-lang">Language</label>
      <select
        id="recon-lang"
        value={lang}
        onChange={(e) => setLang(e.target.value)}
        className="border rounded px-3 py-2"
      >
        {LANGUAGES.map((l) => (
          <option key={l.value} value={l.value}>{l.label}</option>
        ))}
      </select>

      <div
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition
          ${dragOver ? 'border-orange-600 bg-orange-50' : 'border-gray-300'}`}
      >
        <p>Drop files here or click to browse</p>
        <p className="text-sm text-gray-500">{SUPPORTED.join(' ')}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff,.tif"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {rejectedLocal.length > 0 && (
        <div className="border border-yellow-300 bg-yellow-50 rounded-lg p-3 text-sm">
          {rejectedLocal.map((r, i) => (
            <p key={i}>⚠ {r.file.name}: {r.reason}</p>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <ResultCard key={item.jobId || item.name} item={item} onExport={handleExport} />
        ))}
      </div>
    </div>
  );
}
