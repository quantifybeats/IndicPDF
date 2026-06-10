import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer style={{ background: '#2D2D2D', color: '#aaa', padding: '48px 24px 24px' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {/* Top row: counter + links */}
        <div className="footer-grid">
          {/* Counter */}
          <div>
            <p style={{ fontSize: 12, color: '#888', marginBottom: 8 }}>Documents Processed:</p>
            <p style={{ fontSize: 28, fontWeight: 700, color: '#fff', letterSpacing: 1, margin: 0 }}>10,000,000+</p>
          </div>

          {/* Links col 1 */}
          <div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                ['TXT to PDF', '/txt-to-pdf'],
                ['PDF Analyser', '/pdf-analyser'],
                ['Video Converter', '/video-converter'],
                ['English Fonts', '/english-font-converter'],
              ].map(([label, to]) => (
                <li key={label}><Link to={to} style={{ color: '#aaa', textDecoration: 'none', fontSize: 14 }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* Links col 2 */}
          <div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                ['DOCX to PDF', '/docx-to-pdf'],
                ['PDF to DOCX', '/pdf-to-docx'],
                ['OCR', '/ocr'],
                ['Image Converter', '/image-converter'],
                ['Audio Converter', '/audio-converter'],
              ].map(([label, to]) => (
                <li key={label}><Link to={to} style={{ color: '#aaa', textDecoration: 'none', fontSize: 14 }}>{label}</Link></li>
              ))}
            </ul>
          </div>

          {/* Free badge col */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ background: '#22a861', color: '#fff', borderRadius: 4, padding: '4px 12px', fontSize: 12, fontWeight: 700, display: 'inline-block', width: 'fit-content' }}>100% Free</span>
            <p style={{ color: '#888', fontSize: 13, margin: 0, lineHeight: 1.5 }}>No account needed.<br />No limits on usage.</p>
          </div>
        </div>

        {/* Bottom copyright */}
        <div style={{ borderTop: '1px solid #444', paddingTop: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ margin: 0, fontSize: 13, color: '#888' }}>© 2024–2026 IndicPDF. All rights reserved.</p>
          <p style={{ margin: 0, fontSize: 13, color: '#888' }}>Made with ❤ for the Indic Web</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
