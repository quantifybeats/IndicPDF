import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function MediaDropzone({ accept, onFiles, label, icon = '📂' }) {
  const onDrop = useCallback(accepted => { if (accepted.length > 0) onFiles(accepted); }, [onFiles]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept, multiple: true });
  return (
    <div {...getRootProps()} className={`drop-zone ${isDragActive ? 'dragover' : ''}`}>
      <input {...getInputProps()} />
      <div className="text-5xl mb-4">{icon}</div>
      <p className="font-black text-lg text-text mb-2">{isDragActive ? 'Drop files here…' : label}</p>
      <p className="text-text-muted text-sm mb-4">or click to browse — multiple files supported</p>
    </div>
  );
}
