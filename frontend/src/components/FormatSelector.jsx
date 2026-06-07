export default function FormatSelector({ formats, value, onChange, disabled }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled}
      className="bg-surface border border-border rounded-lg px-3 py-2 text-sm font-bold text-text focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed">
      <option value="">Convert to…</option>
      {formats.map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
    </select>
  );
}
