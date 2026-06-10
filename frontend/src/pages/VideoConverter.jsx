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
  const updateAction = (i, patch) => setActions(prev => prev.map((a, j) => j === i ? { ...a, ...patch } : a));
  const handleFiles = async (files) => {
    if (!loaded) await load();
    setActions(prev => [...prev, ...files.map(f => ({ file: f, outputFormat: '', status: 'idle', downloadUrl: null }))]);
  };
  const handleConvertAll = async () => {
    for (let i = 0; i < actions.length; i++) {
      const { file, outputFormat, status } = actions[i];
      if (!outputFormat || status === 'done') continue;
      updateAction(i, { status: 'converting' });
      try {
        const blob = await convertFile(file, outputFormat);
        updateAction(i, { status: 'done', downloadUrl: URL.createObjectURL(blob) });
      } catch { updateAction(i, { status: 'error' }); }
    }
  };
  const allReady = actions.length > 0 && actions.every(a => a.outputFormat || a.status === 'done');
  return (
    <ToolLayout title="Video Converter" description="Convert MP4, AVI, MOV, MKV, WEBM — processed locally in your browser.">
      {loading && <div className="text-center py-8"><p className="text-text-muted text-sm">Loading FFmpeg… {progress}%</p></div>}
      <MediaDropzone accept={ACCEPT} onFiles={handleFiles} label="Drop videos here" icon="🎬" />
      {actions.length > 0 && (
        <div className="mt-6 space-y-2">
          {actions.map((a, i) => <FileActionRow key={`${a.file.name}-${i}`} file={a.file} outputFormat={a.outputFormat} status={a.status} downloadUrl={a.downloadUrl} formats={OUTPUT_FORMATS} onFormatChange={fmt => updateAction(i, { outputFormat: fmt })} onRemove={() => setActions(prev => prev.filter((_, j) => j !== i))} />)}
          <button className="action-btn" disabled={!allReady || !loaded} onClick={handleConvertAll}>Convert All</button>
        </div>
      )}
    </ToolLayout>
  );
}
