import React from 'react';

export default function UploadErrorList({ errors, onDismiss, onClearAll }) {
  if (!errors || errors.length === 0) return null;

  return (
    <div style={{ marginTop: 12, borderRadius: 6, border: '1px solid #FFCDD2', background: '#FFF5F5', padding: '10px 14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#C62828' }}>
          {errors.length} file{errors.length > 1 ? 's' : ''} could not be added
        </span>
        {errors.length > 1 && (
          <button onClick={onClearAll} style={{ fontSize: 12, color: '#F97316', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 500 }}>
            Clear all
          </button>
        )}
      </div>
      {errors.map((e, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderTop: i > 0 ? '1px solid #FFCDD2' : 'none' }}>
          <div style={{ fontSize: 13, color: '#333' }}>
            <span style={{ fontWeight: 500 }}>{e.name}</span>
            <span style={{ color: '#E53935', marginLeft: 8 }}>— {e.reason}</span>
          </div>
          {onDismiss && (
            <button onClick={() => onDismiss(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999', fontSize: 16, lineHeight: 1, padding: '0 4px' }}>×</button>
          )}
        </div>
      ))}
    </div>
  );
}
