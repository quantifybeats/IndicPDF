import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';

const TOOLS = [
  { label: 'DOCX to PDF', to: '/docx-to-pdf', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 6h6M7 9h6M7 12h4"/></svg> },
  { label: 'PDF to DOCX', to: '/pdf-to-docx', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 7h6M7 10h6M7 13h4"/><path d="M11 2v4h5" strokeWidth="1.5"/></svg> },
  { label: 'TXT to PDF', to: '/txt-to-pdf', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 6h6M7 9h6M7 12h6M7 15h3"/></svg> },
  { label: 'PDF Analyser', to: '/pdf-analyser', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="9" r="5"/><path d="M14 14l3 3"/></svg> },
  { label: 'English Fonts', to: '/english-font-converter', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4 15L8 5l4 10M5.5 12h5M13 5h3M14.5 5v10"/></svg> },
  { label: 'OCR', to: '/ocr', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="14" height="10" rx="1"/><path d="M7 9h6M7 12h4"/></svg> },
  { label: 'Image Converter', to: '/image-converter', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="14" height="12" rx="2"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="M3 14l4-4 3 3 2-2 5 5"/></svg> },
  { label: 'Video Converter', to: '/video-converter', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="12" height="10" rx="2"/><path d="M14 8l4-2v8l-4-2V8z"/></svg> },
  { label: 'Audio Converter', to: '/audio-converter', icon: <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FF4B4B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 4v12M6 7v6M3 9v2M12 7v6M15 9v2"/></svg> },
];

const Navbar = () => {
  const [convertOpen, setConvertOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav style={{ background: '#fff', borderBottom: '1px solid #E8E8E8', position: 'sticky', top: 0, zIndex: 1000 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px', height: 60, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>

        {/* Logo */}
        <Link to="/" style={{ textDecoration: 'none', flexShrink: 0 }}>
          <Logo />
        </Link>

        {/* Center nav — desktop only */}
        <ul className="nav-links" style={{ listStyle: 'none', gap: 32, margin: 0, padding: 0, alignItems: 'center' }}>
          <li style={{ position: 'relative' }}
            onMouseEnter={() => setConvertOpen(true)}
            onMouseLeave={() => setConvertOpen(false)}>
            <span style={{ cursor: 'pointer', color: '#555', fontSize: 14, fontWeight: 500, userSelect: 'none' }}>
              Convert ▾
            </span>
            {convertOpen && (
              <div style={{ position: 'absolute', top: '100%', left: 0, background: '#fff', border: '1px solid #E8E8E8', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 16, minWidth: 400, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, zIndex: 100 }}>
                {TOOLS.map(t => (
                  <Link key={t.to} to={t.to}
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, textDecoration: 'none', color: '#333', fontSize: 14 }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F7F7F7'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    {t.icon}{t.label}
                  </Link>
                ))}
              </div>
            )}
          </li>
          <li><Link to="/ocr" style={{ color: '#555', fontSize: 14, fontWeight: 500, textDecoration: 'none' }}>OCR</Link></li>
          <li><Link to="/pricing" style={{ color: '#555', fontSize: 14, fontWeight: 500, textDecoration: 'none' }}>Pricing</Link></li>
        </ul>

        {/* Free badge — desktop only */}
        <div className="nav-actions">
          <span style={{ background: '#22a861', color: '#fff', borderRadius: 4, padding: '6px 14px', fontSize: 13, fontWeight: 700, letterSpacing: 0.3 }}>
            100% Free
          </span>
        </div>

        {/* Hamburger — mobile only */}
        <button className="nav-hamburger" onClick={() => setMobileOpen(o => !o)} aria-label="Menu">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2" strokeLinecap="round">
            {mobileOpen
              ? <><path d="M18 6L6 18"/><path d="M6 6l12 12"/></>
              : <><path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h18"/></>}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown menu */}
      <div className={`mobile-menu${mobileOpen ? ' open' : ''}`}>
        <Link to="/" onClick={() => setMobileOpen(false)} style={{ color: '#333', textDecoration: 'none', fontWeight: 600, fontSize: 15 }}>Home</Link>
        {TOOLS.map(t => (
          <Link key={t.to} to={t.to} onClick={() => setMobileOpen(false)}
            style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#555', textDecoration: 'none', fontSize: 14, paddingLeft: 8 }}>
            {t.icon}{t.label}
          </Link>
        ))}
        <hr style={{ border: 'none', borderTop: '1px solid #E8E8E8', margin: '4px 0' }} />
        <Link to="/pricing" onClick={() => setMobileOpen(false)} style={{ color: '#555', textDecoration: 'none', fontSize: 14 }}>Pricing</Link>
      </div>
    </nav>
  );
};

export default Navbar;
