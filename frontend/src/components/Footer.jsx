import React from 'react';
import { Link } from 'react-router-dom';
import Logo from './Logo';
import { Github, Twitter, Linkedin, Heart } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-surface border-t border-border pt-16 pb-8 px-6">
      <div className="max-w-[1200px] mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
        <div className="col-span-1 md:col-span-1">
          <Logo className="mb-6" />
          <p className="text-text-muted text-sm leading-relaxed mb-6">
            The professional document processing pipeline for complex Indic scripts. 
            Deterministic rendering, zero data storage, 100% precision.
          </p>
          <div className="flex gap-4">
            <a href="#" className="p-2 rounded-lg bg-bg border border-border text-text-muted hover:text-primary transition-colors"><Github size={18} /></a>
            <a href="#" className="p-2 rounded-lg bg-bg border border-border text-text-muted hover:text-primary transition-colors"><Twitter size={18} /></a>
            <a href="#" className="p-2 rounded-lg bg-bg border border-border text-text-muted hover:text-primary transition-colors"><Linkedin size={18} /></a>
          </div>
        </div>

        <div>
          <h4 className="text-[11px] font-black uppercase tracking-widest text-text mb-6">PDF Tools</h4>
          <ul className="space-y-3">
            <li><Link to="/docx-to-pdf" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">DOCX to PDF</Link></li>
            <li><Link to="/pdf-to-docx" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">PDF to DOCX</Link></li>
            <li><Link to="/txt-to-pdf" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">TXT to PDF</Link></li>
            <li><Link to="/pdf-analyser" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">PDF Analyser</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="text-[11px] font-black uppercase tracking-widest text-text mb-6">Converters</h4>
          <ul className="space-y-3">
            <li><Link to="/english-font-converter" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">English Stylish Fonts</Link></li>
            <li><a href="#" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">Telugu Font Converter</a></li>
            <li><a href="#" className="text-text-muted text-sm hover:text-primary transition-colors no-underline">Unicode Normalizer</a></li>
          </ul>
        </div>

        <div>
          <h4 className="text-[11px] font-black uppercase tracking-widest text-text mb-6">Security</h4>
          <p className="text-text-muted text-sm leading-relaxed">
            All documents are processed in-memory and automatically deleted within 2 hours. 
            We use AES-256 encryption for all data handling.
          </p>
        </div>
      </div>

      <div className="max-w-[1200px] mx-auto pt-8 border-t border-border flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-text-muted text-xs font-bold uppercase tracking-widest">
          &copy; 2026 IndicPDF Engine. All rights reserved.
        </p>
        <p className="text-text-muted text-xs font-bold uppercase tracking-widest flex items-center gap-1">
          Made with <Heart size={12} className="text-red-500 fill-red-500" /> for the Indic Web
        </p>
      </div>
    </footer>
  );
};

export default Footer;
