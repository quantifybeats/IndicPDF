import React from 'react';

const features = [
  {
    icon: '◎',
    title: 'Indic Script Support',
    desc: 'We support Telugu, Devanagari, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia and more Indic scripts with perfect glyph rendering.',
  },
  {
    icon: '⚡',
    title: 'Fast and easy',
    desc: 'Just drop your file on the page, choose a tool and click Convert. We aim to process all conversions in under 1-2 minutes.',
  },
  {
    icon: '☁',
    title: 'Server-side processing',
    desc: 'All conversions run on our cloud servers and will not consume any capacity from your computer.',
  },
  {
    icon: '⚙',
    title: '9 Language OCR',
    desc: 'Our OCR engine supports Hindi, Telugu, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia and Punjabi using Tesseract.',
  },
  {
    icon: '✓',
    title: 'Security guaranteed',
    desc: 'We delete uploaded files instantly and converted ones after 24 hours. No one has access to your files and privacy is guaranteed.',
  },
  {
    icon: '🖥',
    title: 'All devices supported',
    desc: 'IndicPDF is browser-based and works for all platforms. There is no need to download or install any software.',
  },
];

const ToolGrid = () => {
  return (
    <section style={{ background: '#F7F7F7', padding: '60px 24px' }}>
      <div className="feature-grid" style={{ maxWidth: 900, margin: '0 auto' }}>
        {features.map(f => (
          <div key={f.title} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 16, color: '#999' }}>{f.icon}</div>
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10, color: '#333' }}>{f.title}</h3>
            <p style={{ fontSize: 14, color: '#777', lineHeight: 1.6, margin: 0 }}>{f.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default ToolGrid;
