import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const TOOLS = [
  { label: 'DOCX to PDF', to: '/docx-to-pdf' },
  { label: 'PDF to DOCX', to: '/pdf-to-docx' },
  { label: 'TXT to PDF', to: '/txt-to-pdf' },
  { label: 'PDF Analyser', to: '/pdf-analyser' },
  { label: 'OCR', to: '/ocr' },
  { label: 'English Fonts', to: '/english-font-converter' },
  { label: 'Image Converter', to: '/image-converter' },
  { label: 'Video Converter', to: '/video-converter' },
  { label: 'Audio Converter', to: '/audio-converter' },
];

const FAQ_ITEMS = [
  { q: 'Is IndicPDF really free?', a: 'Yes, 100% free. No account, no subscription, no credit card. Every tool is available to everyone.' },
  { q: 'Are there any conversion limits?', a: 'No hard limits. Convert as many files as you need.' },
  { q: 'Will my files be safe?', a: 'Files are encrypted during processing and deleted immediately after conversion. We never store or share your documents.' },
  { q: 'What file formats are supported?', a: 'DOCX, PDF, TXT, images (JPG, PNG, GIF, BMP, WebP), video (MP4, AVI, MOV, MKV), audio (MP3, WAV, FLAC, AAC, OGG), and more.' },
  { q: 'Do I need to create an account?', a: 'No account needed. Open any tool and start converting immediately.' },
];

const Pricing = () => {
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <div style={{ background: '#fff', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', padding: '60px 24px 48px' }}>
        <div style={{ display: 'inline-block', background: '#22a861', color: '#fff', borderRadius: 50, padding: '6px 20px', fontSize: 13, fontWeight: 700, letterSpacing: 0.5, marginBottom: 20 }}>
          FREE FOREVER
        </div>
        <h1 style={{ fontSize: 36, fontWeight: 700, color: '#333', marginBottom: 16 }}>
          Every Tool. Always Free.
        </h1>
        <p style={{ fontSize: 16, color: '#777', marginBottom: 40, maxWidth: 520, margin: '0 auto 40px' }}>
          IndicPDF is built for the Indic web. No accounts, no subscriptions, no limits — just tools that work.
        </p>

        {/* Big free card */}
        <div style={{ maxWidth: 440, margin: '0 auto', border: '2px solid #22a861', borderRadius: 12, padding: '36px 32px', background: '#fff', boxShadow: '0 8px 32px rgba(34,168,97,0.08)' }}>
          <div style={{ fontSize: 48, fontWeight: 700, color: '#333', marginBottom: 4 }}>Free</div>
          <div style={{ fontSize: 14, color: '#999', marginBottom: 28 }}>No credit card required</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 28px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              'All 9 conversion tools',
              'Unlimited conversions',
              'No account required',
              'Files deleted after processing',
              'Indic script support (9 languages)',
              'Client-side media conversion',
              'OCR text extraction',
              'PDF quality analysis',
            ].map(f => (
              <li key={f} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: '#555' }}>
                <span style={{ color: '#22a861', fontWeight: 700 }}>✓</span>
                {f}
              </li>
            ))}
          </ul>
          <Link to="/converter" style={{ display: 'block', background: '#22a861', color: '#fff', borderRadius: 6, padding: '13px 0', fontSize: 15, fontWeight: 700, textDecoration: 'none', textAlign: 'center', letterSpacing: 0.3 }}
            onMouseEnter={e => e.currentTarget.style.background = '#1a9053'}
            onMouseLeave={e => e.currentTarget.style.background = '#22a861'}
          >
            Start Converting →
          </Link>
        </div>
      </div>

      {/* Tools grid */}
      <div style={{ background: '#F7F7F7', padding: '48px 24px' }}>
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#333', marginBottom: 32 }}>All Tools Included</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {TOOLS.map(tool => (
              <Link key={tool.to} to={tool.to}
                style={{ background: '#fff', border: '1px solid #E8E8E8', borderRadius: 8, padding: '16px 12px', textDecoration: 'none', color: '#333', fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#22a861'; e.currentTarget.style.color = '#22a861'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#E8E8E8'; e.currentTarget.style.color = '#333'; }}
              >
                <span style={{ color: '#22a861', fontWeight: 700, fontSize: 12 }}>✓</span>
                {tool.label}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div style={{ maxWidth: 700, margin: '0 auto', padding: '60px 24px' }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#333', marginBottom: 32, textAlign: 'center' }}>
          Frequently Asked Questions
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {FAQ_ITEMS.map((item, i) => (
            <div key={i} style={{ borderBottom: '1px solid #E8E8E8' }}>
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '18px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', textAlign: 'left' }}
              >
                <span style={{ fontSize: 15, fontWeight: 600, color: '#333' }}>{item.q}</span>
                <span style={{ fontSize: 18, color: '#aaa', marginLeft: 16, flexShrink: 0 }}>{openFaq === i ? '−' : '+'}</span>
              </button>
              {openFaq === i && (
                <p style={{ fontSize: 14, color: '#777', lineHeight: 1.6, padding: '0 0 18px', margin: 0 }}>{item.a}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      <div style={{ textAlign: 'center', padding: '0 24px 40px', color: '#bbb', fontSize: 13 }}>
        © 2024–2026 IndicPDF. All rights reserved.
      </div>
    </div>
  );
};

export default Pricing;
