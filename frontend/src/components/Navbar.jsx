import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';

const ico = (paths) => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">{paths}</svg>
);

const TOOLS = [
  { label: 'DOCX to PDF', to: '/docx-to-pdf', icon: ico(<><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 6h6M7 9h6M7 12h4"/></>) },
  { label: 'PDF to DOCX', to: '/pdf-to-docx', icon: ico(<><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 7h6M7 10h6M7 13h4"/><path d="M11 2v4h5"/></>) },
  { label: 'TXT to PDF', to: '/txt-to-pdf', icon: ico(<><rect x="4" y="2" width="12" height="16" rx="2"/><path d="M7 6h6M7 9h6M7 12h6M7 15h3"/></>) },
  { label: 'PDF Analyser', to: '/pdf-analyser', icon: ico(<><circle cx="9" cy="9" r="5"/><path d="M14 14l3 3"/></>) },
  { label: 'English Fonts', to: '/english-font-converter', icon: ico(<><path d="M4 15L8 5l4 10M5.5 12h5M13 5h3M14.5 5v10"/></>) },
  { label: 'OCR', to: '/ocr', icon: ico(<><rect x="3" y="5" width="14" height="10" rx="1"/><path d="M7 9h6M7 12h4"/></>) },
  { label: 'Reconstruct', to: '/reconstruct', icon: ico(<><rect x="3" y="5" width="14" height="10" rx="1"/><path d="M7 9h6M7 12h4"/></>) },
  { label: 'Image Converter', to: '/image-converter', icon: ico(<><rect x="3" y="4" width="14" height="12" rx="2"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="M3 14l4-4 3 3 2-2 5 5"/></>) },
  { label: 'Video Converter', to: '/video-converter', icon: ico(<><rect x="2" y="5" width="12" height="10" rx="2"/><path d="M14 8l4-2v8l-4-2V8z"/></>) },
  { label: 'Audio Converter', to: '/audio-converter', icon: ico(<><path d="M9 4v12M6 7v6M3 9v2M12 7v6M15 9v2"/></>) },
];

const linkCls = 'text-sm font-medium text-text-muted hover:text-primary transition-colors';

const Navbar = () => {
  const [convertOpen, setConvertOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-[1000] w-full border-b border-border glass">
      <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="no-underline flex-shrink-0">
          <Logo />
        </Link>

        {/* Center nav — desktop only */}
        <ul className="nav-links list-none gap-8 m-0 p-0 items-center">
          <li className="relative"
            onMouseEnter={() => setConvertOpen(true)}
            onMouseLeave={() => setConvertOpen(false)}>
            <span className={`cursor-pointer select-none flex items-center gap-1 ${linkCls}`}>
              Convert
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6"/></svg>
            </span>
            {convertOpen && (
              <div className="absolute top-full left-0 pt-3">
                <div className="bg-surface border border-border rounded-radius shadow-shadow-lg p-2 min-w-[420px] grid grid-cols-2 gap-1">
                  {TOOLS.map(t => (
                    <Link key={t.to} to={t.to}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg no-underline text-sm text-text hover:bg-primary/10 hover:text-primary transition-colors">
                      <span className="text-primary">{t.icon}</span>{t.label}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </li>
          <li><Link to="/ocr" className={linkCls}>OCR</Link></li>
          <li><Link to="/reconstruct" className={linkCls}>Reconstruct</Link></li>
          <li><Link to="/pricing" className={linkCls}>Pricing</Link></li>
        </ul>

        {/* Free badge — desktop only */}
        <div className="nav-actions">
          <span className="inline-flex items-center gap-1.5 bg-primary/10 text-primary border border-primary/20 rounded-full px-3.5 py-1.5 text-xs font-bold tracking-wide">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            100% Free
          </span>
        </div>

        {/* Hamburger — mobile only */}
        <button className="nav-hamburger" onClick={() => setMobileOpen(o => !o)} aria-label="Menu">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-text">
            {mobileOpen
              ? <><path d="M18 6L6 18"/><path d="M6 6l12 12"/></>
              : <><path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h18"/></>}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown menu */}
      <div className={`mobile-menu${mobileOpen ? ' open' : ''}`}>
        <Link to="/" onClick={() => setMobileOpen(false)} className="text-text no-underline font-semibold text-[15px]">Home</Link>
        {TOOLS.map(t => (
          <Link key={t.to} to={t.to} onClick={() => setMobileOpen(false)}
            className="flex items-center gap-2.5 text-text-muted no-underline text-sm pl-2 hover:text-primary transition-colors">
            <span className="text-primary">{t.icon}</span>{t.label}
          </Link>
        ))}
        <hr className="border-none border-t border-border my-1" />
        <Link to="/pricing" onClick={() => setMobileOpen(false)} className="text-text-muted no-underline text-sm">Pricing</Link>
      </div>
    </nav>
  );
};

export default Navbar;
