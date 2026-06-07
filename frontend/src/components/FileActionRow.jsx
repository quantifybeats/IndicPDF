import FormatSelector from './FormatSelector.jsx';

const STATUS_BADGE = {
  idle: null,
  converting: <span data-testid="converting-spinner" className="inline-flex items-center gap-1 text-primary text-xs font-bold"><span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />Converting…</span>,
  done: <span className="text-green-600 text-xs font-black">✓ Done</span>,
  error: <span className="text-red-500 text-xs font-black">✗ Error</span>,
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileActionRow({ file, outputFormat, status, downloadUrl, formats, onFormatChange, onRemove }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-surface border border-border rounded-xl">
      <div className="flex-1 min-w-0">
        <p className="font-bold text-sm truncate text-text">{file.name}</p>
        <p className="text-xs text-text-muted">{formatBytes(file.size)}</p>
      </div>
      <FormatSelector formats={formats} value={outputFormat} onChange={onFormatChange} disabled={status === 'converting' || status === 'done'} />
      <div className="w-28 text-center">{STATUS_BADGE[status]}</div>
      {status === 'done' && downloadUrl ? (
        <a href={downloadUrl} download={`${file.name.replace(/\.[^.]+$/, '')}.${outputFormat}`} className="dl-btn text-xs py-2 px-3">Download</a>
      ) : status !== 'converting' ? (
        <button onClick={onRemove} className="text-text-muted hover:text-red-500 transition-colors text-lg leading-none" aria-label="Remove file">×</button>
      ) : null}
    </div>
  );
}
