# Track A — Multimedia Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add browser-side image, video, and audio conversion tools using FFmpeg.wasm. No server changes. Users drop files, pick output format per file, click Convert, download results.

**Architecture:** FFmpeg.wasm v0.12 runs in a Web Worker inside the user's browser. A `useFFmpeg` hook lazy-loads the WASM (~30MB, cached after first load). Three new pages (`/image-converter`, `/video-converter`, `/audio-converter`) share four new components: `MediaDropzone`, `FileActionRow`, `FormatSelector`, and the `useFFmpeg` hook.

**Tech Stack:** `@ffmpeg/ffmpeg@0.12.x`, `@ffmpeg/util@0.12.x`, React 19, Vite, Vitest + React Testing Library

---

## File Map

| Action | Path |
|---|---|
| Modify | `frontend/package.json` |
| Create | `frontend/src/hooks/useFFmpeg.js` |
| Create | `frontend/src/components/FormatSelector.jsx` |
| Create | `frontend/src/components/FileActionRow.jsx` |
| Create | `frontend/src/components/MediaDropzone.jsx` |
| Create | `frontend/src/pages/ImageConverter.jsx` |
| Create | `frontend/src/pages/VideoConverter.jsx` |
| Create | `frontend/src/pages/AudioConverter.jsx` |
| Modify | `frontend/src/App.jsx` |
| Modify | `frontend/src/components/Navbar.jsx` |
| Create | `frontend/src/hooks/__tests__/useFFmpeg.test.js` |
| Create | `frontend/src/components/__tests__/FormatSelector.test.jsx` |
| Create | `frontend/src/components/__tests__/FileActionRow.test.jsx` |

---

### Task 1: Install FFmpeg.wasm packages

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install packages**

```bash
cd /Users/jay/IndicPdf-Main/frontend
npm install @ffmpeg/ffmpeg@0.12.15 @ffmpeg/util@0.12.1
```

- [ ] **Step 2: Install Vitest + React Testing Library (if not present)**

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 3: Add test script to package.json if missing**

In `frontend/package.json`, ensure scripts has:
```json
"test": "vitest"
```

And add vitest config to `frontend/vite.config.js` (or create it):
```js
// Add inside defineConfig:
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: './src/test-setup.js',
}
```

Create `frontend/src/test-setup.js`:
```js
import '@testing-library/jest-dom';
```

- [ ] **Step 4: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/src/test-setup.js
git commit -m "feat: install @ffmpeg/ffmpeg and test tooling (Track A)"
```

---

### Task 2: Write failing tests for useFFmpeg hook

**Files:**
- Create: `frontend/src/hooks/__tests__/useFFmpeg.test.js`

- [ ] **Step 1: Create test directory and write tests**

```bash
mkdir -p frontend/src/hooks/__tests__
```

```js
// frontend/src/hooks/__tests__/useFFmpeg.test.js
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@ffmpeg/ffmpeg', () => ({
  FFmpeg: vi.fn(() => ({
    load: vi.fn().mockResolvedValue(undefined),
    on: vi.fn(),
    writeFile: vi.fn().mockResolvedValue(undefined),
    exec: vi.fn().mockResolvedValue(undefined),
    readFile: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3])),
    deleteFile: vi.fn().mockResolvedValue(undefined),
  })),
}));

vi.mock('@ffmpeg/util', () => ({
  fetchFile: vi.fn().mockResolvedValue(new Uint8Array()),
  toBlobURL: vi.fn(url => Promise.resolve(url)),
}));

describe('useFFmpeg', () => {
  beforeEach(() => vi.clearAllMocks());

  it('starts with loaded=false and loading=false', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    expect(result.current.loaded).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it('sets loaded=true after load()', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    expect(result.current.loaded).toBe(true);
  });

  it('does not reload if already loaded', async () => {
    const { FFmpeg } = await import('@ffmpeg/ffmpeg');
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    await act(async () => { await result.current.load(); });
    const instance = FFmpeg.mock.results[0].value;
    expect(instance.load).toHaveBeenCalledTimes(1);
  });

  it('convertFile returns a Blob', async () => {
    const { useFFmpeg } = await import('../useFFmpeg.js');
    const { result } = renderHook(() => useFFmpeg());
    await act(async () => { await result.current.load(); });
    const mockFile = new File(['data'], 'test.mp4', { type: 'video/mp4' });
    let blob;
    await act(async () => {
      blob = await result.current.convertFile(mockFile, 'webm');
    });
    expect(blob).toBeInstanceOf(Blob);
  });
});
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd /Users/jay/IndicPdf-Main/frontend
npm test -- src/hooks/__tests__/useFFmpeg.test.js
```

Expected: `Cannot find module '../useFFmpeg.js'`

---

### Task 3: Implement useFFmpeg hook

**Files:**
- Create: `frontend/src/hooks/useFFmpeg.js`

- [ ] **Step 1: Create hooks directory and write hook**

```bash
mkdir -p frontend/src/hooks
```

```js
// frontend/src/hooks/useFFmpeg.js
import { useState, useRef } from 'react';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

const FFMPEG_CORE_URL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/umd';

const MIME_TYPES = {
  mp4: 'video/mp4',   webm: 'video/webm',    avi: 'video/x-msvideo',
  mov: 'video/quicktime', mkv: 'video/x-matroska',
  mp3: 'audio/mpeg',  wav: 'audio/wav',       flac: 'audio/flac',
  aac: 'audio/aac',   ogg: 'audio/ogg',
  jpg: 'image/jpeg',  jpeg: 'image/jpeg',     png: 'image/png',
  gif: 'image/gif',   webp: 'image/webp',     bmp: 'image/bmp',
};

export function useFFmpeg() {
  const ffmpegRef = useRef(null);
  const [loaded, setLoaded]   = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const load = async () => {
    if (loaded) return;
    setLoading(true);
    setProgress(0);

    if (!ffmpegRef.current) {
      ffmpegRef.current = new FFmpeg();
    }
    const ffmpeg = ffmpegRef.current;

    ffmpeg.on('progress', ({ progress: p }) => setProgress(Math.round(p * 100)));

    await ffmpeg.load({
      coreURL:  await toBlobURL(`${FFMPEG_CORE_URL}/ffmpeg-core.js`,   'text/javascript'),
      wasmURL:  await toBlobURL(`${FFMPEG_CORE_URL}/ffmpeg-core.wasm`, 'application/wasm'),
    });

    setLoaded(true);
    setLoading(false);
  };

  /**
   * Convert a single File to a different format.
   * @param {File} file - Source file.
   * @param {string} outputFormat - Target extension (e.g. 'mp4', 'png').
   * @returns {Promise<Blob>} Converted file as Blob.
   */
  const convertFile = async (file, outputFormat) => {
    const ffmpeg = ffmpegRef.current;
    const inputExt  = file.name.split('.').pop().toLowerCase();
    const inputName  = `input.${inputExt}`;
    const outputName = `output.${outputFormat}`;

    await ffmpeg.writeFile(inputName, await fetchFile(file));
    await ffmpeg.exec(['-i', inputName, outputName]);

    const data = await ffmpeg.readFile(outputName);
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);

    const mimeType = MIME_TYPES[outputFormat] || 'application/octet-stream';
    return new Blob([data.buffer], { type: mimeType });
  };

  return { loaded, loading, progress, load, convertFile };
}
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/jay/IndicPdf-Main/frontend
npm test -- src/hooks/__tests__/useFFmpeg.test.js
```

Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/hooks/useFFmpeg.js frontend/src/hooks/__tests__/useFFmpeg.test.js
git commit -m "feat: add useFFmpeg hook with tests (Track A)"
```

---

### Task 4: FormatSelector component

**Files:**
- Create: `frontend/src/components/__tests__/FormatSelector.test.jsx`
- Create: `frontend/src/components/FormatSelector.jsx`

- [ ] **Step 1: Write failing test**

```jsx
// frontend/src/components/__tests__/FormatSelector.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FormatSelector from '../FormatSelector.jsx';

const formats = ['mp4', 'webm', 'avi'];

describe('FormatSelector', () => {
  it('renders a select with all format options', () => {
    render(<FormatSelector formats={formats} value="" onChange={() => {}} disabled={false} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    formats.forEach(f => expect(screen.getByText(f.toUpperCase())).toBeInTheDocument());
  });

  it('calls onChange with selected value', () => {
    const onChange = vi.fn();
    render(<FormatSelector formats={formats} value="" onChange={onChange} disabled={false} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'webm' } });
    expect(onChange).toHaveBeenCalledWith('webm');
  });

  it('is disabled when disabled prop is true', () => {
    render(<FormatSelector formats={formats} value="mp4" onChange={() => {}} disabled={true} />);
    expect(screen.getByRole('combobox')).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd /Users/jay/IndicPdf-Main/frontend
npm test -- src/components/__tests__/FormatSelector.test.jsx
```

Expected: `Cannot find module '../FormatSelector.jsx'`

- [ ] **Step 3: Implement FormatSelector**

```jsx
// frontend/src/components/FormatSelector.jsx
export default function FormatSelector({ formats, value, onChange, disabled }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      className="bg-surface border border-border rounded-lg px-3 py-2 text-sm font-bold text-text focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <option value="">Convert to…</option>
      {formats.map(f => (
        <option key={f} value={f}>{f.toUpperCase()}</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
npm test -- src/components/__tests__/FormatSelector.test.jsx
```

Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/components/FormatSelector.jsx frontend/src/components/__tests__/FormatSelector.test.jsx
git commit -m "feat: add FormatSelector component with tests (Track A)"
```

---

### Task 5: FileActionRow component

**Files:**
- Create: `frontend/src/components/__tests__/FileActionRow.test.jsx`
- Create: `frontend/src/components/FileActionRow.jsx`

- [ ] **Step 1: Write failing test**

```jsx
// frontend/src/components/__tests__/FileActionRow.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FileActionRow from '../FileActionRow.jsx';

const baseProps = {
  file: new File(['data'], 'video.mp4', { type: 'video/mp4' }),
  outputFormat: '',
  status: 'idle',
  downloadUrl: null,
  formats: ['mp4', 'webm', 'avi'],
  onFormatChange: vi.fn(),
  onRemove: vi.fn(),
};

describe('FileActionRow', () => {
  it('renders filename and file size', () => {
    render(<FileActionRow {...baseProps} />);
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
  });

  it('shows spinner when status is converting', () => {
    render(<FileActionRow {...baseProps} status="converting" />);
    expect(screen.getByTestId('converting-spinner')).toBeInTheDocument();
  });

  it('shows done badge when status is done', () => {
    render(<FileActionRow {...baseProps} status="done" downloadUrl="blob:test" />);
    expect(screen.getByText('✓ Done')).toBeInTheDocument();
  });

  it('shows download button when done with downloadUrl', () => {
    render(<FileActionRow {...baseProps} status="done" downloadUrl="blob:test" />);
    expect(screen.getByRole('link', { name: /download/i })).toBeInTheDocument();
  });

  it('shows error badge when status is error', () => {
    render(<FileActionRow {...baseProps} status="error" />);
    expect(screen.getByText('✗ Error')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
npm test -- src/components/__tests__/FileActionRow.test.jsx
```

Expected: `Cannot find module '../FileActionRow.jsx'`

- [ ] **Step 3: Implement FileActionRow**

```jsx
// frontend/src/components/FileActionRow.jsx
import FormatSelector from './FormatSelector.jsx';

const STATUS_BADGE = {
  idle:       null,
  converting: <span data-testid="converting-spinner" className="inline-flex items-center gap-1 text-primary text-xs font-bold"><span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />Converting…</span>,
  done:       <span className="text-green-600 text-xs font-black">✓ Done</span>,
  error:      <span className="text-red-500 text-xs font-black">✗ Error</span>,
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileActionRow({
  file, outputFormat, status, downloadUrl,
  formats, onFormatChange, onRemove,
}) {
  return (
    <div className="flex items-center gap-3 p-3 bg-surface border border-border rounded-xl">
      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="font-bold text-sm truncate text-text">{file.name}</p>
        <p className="text-xs text-text-muted">{formatBytes(file.size)}</p>
      </div>

      {/* Format selector */}
      <FormatSelector
        formats={formats}
        value={outputFormat}
        onChange={onFormatChange}
        disabled={status === 'converting' || status === 'done'}
      />

      {/* Status badge */}
      <div className="w-28 text-center">
        {STATUS_BADGE[status]}
      </div>

      {/* Download / Remove */}
      {status === 'done' && downloadUrl ? (
        <a
          href={downloadUrl}
          download={`${file.name.replace(/\.[^.]+$/, '')}.${outputFormat}`}
          className="dl-btn text-xs py-2 px-3"
        >
          Download
        </a>
      ) : status !== 'converting' ? (
        <button
          onClick={onRemove}
          className="text-text-muted hover:text-red-500 transition-colors text-lg leading-none"
          aria-label="Remove file"
        >
          ×
        </button>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
npm test -- src/components/__tests__/FileActionRow.test.jsx
```

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/components/FileActionRow.jsx frontend/src/components/__tests__/FileActionRow.test.jsx
git commit -m "feat: add FileActionRow component with tests (Track A)"
```

---

### Task 6: MediaDropzone component

**Files:**
- Create: `frontend/src/components/MediaDropzone.jsx`

- [ ] **Step 1: Implement MediaDropzone**

```jsx
// frontend/src/components/MediaDropzone.jsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function MediaDropzone({ accept, onFiles, label, icon = '📂' }) {
  const onDrop = useCallback(accepted => {
    if (accepted.length > 0) onFiles(accepted);
  }, [onFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    multiple: true,
  });

  return (
    <div
      {...getRootProps()}
      className={`drop-zone ${isDragActive ? 'dragover' : ''}`}
    >
      <input {...getInputProps()} />
      <div className="text-5xl mb-4">{icon}</div>
      <p className="font-black text-lg text-text mb-2">
        {isDragActive ? 'Drop files here…' : label}
      </p>
      <p className="text-text-muted text-sm mb-4">
        or click to browse — multiple files supported
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/components/MediaDropzone.jsx
git commit -m "feat: add MediaDropzone component (Track A)"
```

---

### Task 7: Create the three converter pages

**Files:**
- Create: `frontend/src/pages/ImageConverter.jsx`
- Create: `frontend/src/pages/VideoConverter.jsx`
- Create: `frontend/src/pages/AudioConverter.jsx`

- [ ] **Step 1: Write shared converter page factory**

All three pages share identical logic — only the accepted formats differ. Create the three pages:

```jsx
// frontend/src/pages/ImageConverter.jsx
import { useState } from 'react';
import ToolLayout from '../components/ToolLayout';
import MediaDropzone from '../components/MediaDropzone';
import FileActionRow from '../components/FileActionRow';
import { useFFmpeg } from '../hooks/useFFmpeg';

const ACCEPT = { 'image/*': ['.jpg','.jpeg','.png','.gif','.bmp','.webp','.ico','.tiff'] };
const OUTPUT_FORMATS_MAP = {
  jpg: ['png','gif','bmp','webp','ico'],
  jpeg: ['png','gif','bmp','webp','ico'],
  png: ['jpg','gif','bmp','webp','ico'],
  gif: ['jpg','png','bmp','webp'],
  bmp: ['jpg','png','gif','webp'],
  webp: ['jpg','png','gif','bmp'],
  ico: ['jpg','png'],
  tiff: ['jpg','png','bmp'],
};

export default function ImageConverter() {
  const { loaded, loading, progress, load, convertFile } = useFFmpeg();
  const [actions, setActions] = useState([]); // [{file, outputFormat, status, downloadUrl}]

  const handleFiles = async (files) => {
    if (!loaded) await load();
    setActions(prev => [
      ...prev,
      ...files.map(f => ({ file: f, outputFormat: '', status: 'idle', downloadUrl: null })),
    ]);
  };

  const updateAction = (index, patch) =>
    setActions(prev => prev.map((a, i) => i === index ? { ...a, ...patch } : a));

  const handleConvertAll = async () => {
    for (let i = 0; i < actions.length; i++) {
      const { file, outputFormat, status } = actions[i];
      if (!outputFormat || status === 'done') continue;
      updateAction(i, { status: 'converting' });
      try {
        const blob = await convertFile(file, outputFormat);
        const url = URL.createObjectURL(blob);
        updateAction(i, { status: 'done', downloadUrl: url });
      } catch {
        updateAction(i, { status: 'error' });
      }
    }
  };

  const removeAction = (index) =>
    setActions(prev => prev.filter((_, i) => i !== index));

  const getFormats = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    return OUTPUT_FORMATS_MAP[ext] || ['jpg','png'];
  };

  const allReady = actions.length > 0 && actions.every(a => a.outputFormat || a.status === 'done');

  return (
    <ToolLayout title="Image Converter" description="Convert images between JPG, PNG, GIF, BMP, WEBP and more — right in your browser.">
      {loading && (
        <div className="text-center py-8">
          <div className="spinner" />
          <p className="text-text-muted text-sm">Loading FFmpeg… {progress}%</p>
        </div>
      )}

      <MediaDropzone
        accept={ACCEPT}
        onFiles={handleFiles}
        label="Drop images here"
        icon="🖼️"
      />

      {actions.length > 0 && (
        <div className="mt-6 space-y-2">
          {actions.map((action, i) => (
            <FileActionRow
              key={`${action.file.name}-${i}`}
              file={action.file}
              outputFormat={action.outputFormat}
              status={action.status}
              downloadUrl={action.downloadUrl}
              formats={getFormats(action.file)}
              onFormatChange={fmt => updateAction(i, { outputFormat: fmt })}
              onRemove={() => removeAction(i)}
            />
          ))}
          <button
            className="action-btn"
            disabled={!allReady || !loaded}
            onClick={handleConvertAll}
          >
            Convert All
          </button>
        </div>
      )}
    </ToolLayout>
  );
}
```

```jsx
// frontend/src/pages/VideoConverter.jsx
import { useState } from 'react';
import ToolLayout from '../components/ToolLayout';
import MediaDropzone from '../components/MediaDropzone';
import FileActionRow from '../components/FileActionRow';
import { useFFmpeg } from '../hooks/useFFmpeg';

const ACCEPT = { 'video/*': ['.mp4','.avi','.mov','.mkv','.webm','.flv'] };
const OUTPUT_FORMATS = ['mp4','webm','avi','mov','gif'];

export default function VideoConverter() {
  const { loaded, loading, progress, load, convertFile } = useFFmpeg();
  const [actions, setActions] = useState([]);

  const handleFiles = async (files) => {
    if (!loaded) await load();
    setActions(prev => [...prev, ...files.map(f => ({ file: f, outputFormat: '', status: 'idle', downloadUrl: null }))]);
  };

  const updateAction = (index, patch) =>
    setActions(prev => prev.map((a, i) => i === index ? { ...a, ...patch } : a));

  const handleConvertAll = async () => {
    for (let i = 0; i < actions.length; i++) {
      const { file, outputFormat, status } = actions[i];
      if (!outputFormat || status === 'done') continue;
      updateAction(i, { status: 'converting' });
      try {
        const blob = await convertFile(file, outputFormat);
        updateAction(i, { status: 'done', downloadUrl: URL.createObjectURL(blob) });
      } catch {
        updateAction(i, { status: 'error' });
      }
    }
  };

  const removeAction = (index) => setActions(prev => prev.filter((_, i) => i !== index));
  const allReady = actions.length > 0 && actions.every(a => a.outputFormat || a.status === 'done');

  return (
    <ToolLayout title="Video Converter" description="Convert MP4, AVI, MOV, MKV, WEBM — processed locally in your browser.">
      {loading && <div className="text-center py-8"><div className="spinner" /><p className="text-text-muted text-sm">Loading FFmpeg… {progress}%</p></div>}
      <MediaDropzone accept={ACCEPT} onFiles={handleFiles} label="Drop videos here" icon="🎬" />
      {actions.length > 0 && (
        <div className="mt-6 space-y-2">
          {actions.map((a, i) => (
            <FileActionRow key={`${a.file.name}-${i}`} file={a.file} outputFormat={a.outputFormat}
              status={a.status} downloadUrl={a.downloadUrl} formats={OUTPUT_FORMATS}
              onFormatChange={fmt => updateAction(i, { outputFormat: fmt })}
              onRemove={() => removeAction(i)} />
          ))}
          <button className="action-btn" disabled={!allReady || !loaded} onClick={handleConvertAll}>Convert All</button>
        </div>
      )}
    </ToolLayout>
  );
}
```

```jsx
// frontend/src/pages/AudioConverter.jsx
import { useState } from 'react';
import ToolLayout from '../components/ToolLayout';
import MediaDropzone from '../components/MediaDropzone';
import FileActionRow from '../components/FileActionRow';
import { useFFmpeg } from '../hooks/useFFmpeg';

const ACCEPT = { 'audio/*': ['.mp3','.wav','.flac','.aac','.ogg','.m4a'] };
const OUTPUT_FORMATS = ['mp3','wav','flac','aac','ogg'];

export default function AudioConverter() {
  const { loaded, loading, progress, load, convertFile } = useFFmpeg();
  const [actions, setActions] = useState([]);

  const handleFiles = async (files) => {
    if (!loaded) await load();
    setActions(prev => [...prev, ...files.map(f => ({ file: f, outputFormat: '', status: 'idle', downloadUrl: null }))]);
  };

  const updateAction = (index, patch) =>
    setActions(prev => prev.map((a, i) => i === index ? { ...a, ...patch } : a));

  const handleConvertAll = async () => {
    for (let i = 0; i < actions.length; i++) {
      const { file, outputFormat, status } = actions[i];
      if (!outputFormat || status === 'done') continue;
      updateAction(i, { status: 'converting' });
      try {
        const blob = await convertFile(file, outputFormat);
        updateAction(i, { status: 'done', downloadUrl: URL.createObjectURL(blob) });
      } catch {
        updateAction(i, { status: 'error' });
      }
    }
  };

  const removeAction = (index) => setActions(prev => prev.filter((_, i) => i !== index));
  const allReady = actions.length > 0 && actions.every(a => a.outputFormat || a.status === 'done');

  return (
    <ToolLayout title="Audio Converter" description="Convert MP3, WAV, FLAC, AAC, OGG — processed locally in your browser.">
      {loading && <div className="text-center py-8"><div className="spinner" /><p className="text-text-muted text-sm">Loading FFmpeg… {progress}%</p></div>}
      <MediaDropzone accept={ACCEPT} onFiles={handleFiles} label="Drop audio files here" icon="🎵" />
      {actions.length > 0 && (
        <div className="mt-6 space-y-2">
          {actions.map((a, i) => (
            <FileActionRow key={`${a.file.name}-${i}`} file={a.file} outputFormat={a.outputFormat}
              status={a.status} downloadUrl={a.downloadUrl} formats={OUTPUT_FORMATS}
              onFormatChange={fmt => updateAction(i, { outputFormat: fmt })}
              onRemove={() => removeAction(i)} />
          ))}
          <button className="action-btn" disabled={!allReady || !loaded} onClick={handleConvertAll}>Convert All</button>
        </div>
      )}
    </ToolLayout>
  );
}
```

- [ ] **Step 2: Commit all three pages**

```bash
cd /Users/jay/IndicPdf-Main
git add frontend/src/pages/ImageConverter.jsx frontend/src/pages/VideoConverter.jsx frontend/src/pages/AudioConverter.jsx frontend/src/components/MediaDropzone.jsx
git commit -m "feat: add Image, Video, Audio converter pages (Track A)"
```

---

### Task 8: Wire routing and navbar

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Navbar.jsx`

- [ ] **Step 1: Add lazy imports and routes to App.jsx**

Add after existing lazy imports:
```jsx
const ImageConverter = React.lazy(() => import('./pages/ImageConverter'));
const VideoConverter = React.lazy(() => import('./pages/VideoConverter'));
const AudioConverter = React.lazy(() => import('./pages/AudioConverter'));
```

Add inside `<Routes>`:
```jsx
<Route path="/image-converter" element={<ImageConverter />} />
<Route path="/video-converter" element={<VideoConverter />} />
<Route path="/audio-converter" element={<AudioConverter />} />
```

- [ ] **Step 2: Add Media nav group to Navbar.jsx**

Add a Media section to the nav `<ul>` alongside existing links:
```jsx
<li className="relative group">
  <span className="no-underline text-text-muted text-[0.8rem] font-black uppercase hover:text-primary transition-all tracking-widest cursor-pointer">
    Media ▾
  </span>
  <ul className="absolute top-full left-0 hidden group-hover:flex flex-col bg-surface border border-border rounded-xl shadow-shadow-lg py-2 z-50 min-w-[160px]">
    <li><Link to="/image-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary hover:bg-surface-overlay no-underline">🖼️ Image</Link></li>
    <li><Link to="/video-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary hover:bg-surface-overlay no-underline">🎬 Video</Link></li>
    <li><Link to="/audio-converter" className="block px-4 py-2 text-sm text-text-muted hover:text-primary hover:bg-surface-overlay no-underline">🎵 Audio</Link></li>
  </ul>
</li>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/Navbar.jsx
git commit -m "feat: add Media nav dropdown and routes (Track A)"
```

---

### Task 9: Build check + ECC review

- [ ] **Step 1: Run the full test suite**

```bash
cd /Users/jay/IndicPdf-Main/frontend
npm test
```

Expected: All tests PASS

- [ ] **Step 2: Run Vite build to catch any type/import errors**

```bash
npm run build
```

Expected: `built in Xs` with no errors

- [ ] **Step 3: Run ecc:react-review**

```
/react-review frontend/src/hooks/useFFmpeg.js
/react-review frontend/src/pages/ImageConverter.jsx
```

Fix any issues flagged.

- [ ] **Step 4: Run ecc:vite-patterns**

```
/vite-patterns
```

- [ ] **Step 5: Run ecc:security-scan**

```
/security-scan
```

- [ ] **Step 6: Create PR**

```
/pr
```

- [ ] **Step 7: Final commit**

```bash
cd /Users/jay/IndicPdf-Main
git add -A
git commit -m "feat: complete Track A — multimedia tools (image, video, audio)"
```
