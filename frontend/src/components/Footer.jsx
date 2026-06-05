import React from 'react';
import { useStore } from '../store';

const Footer = () => {
  const setActiveTool = useStore((state) => state.setActiveTool);

  return (
    <footer className="bg-[#2d3748] text-[#cbd5e0] py-12 px-6">
      <div className="footer-inner max-w-[1200px] mx-auto flex justify-between flex-wrap gap-8">
        <div>
          <div className="footer-logo text-white font-extrabold text-xl mb-4">Indic PDF</div>
          <p className="text-[0.85rem] max-w-[240px]">Enterprise-grade document processing for Indian languages.</p>
        </div>
        <div className="footer-links">
          <h4 className="text-white text-[0.9rem] mb-4 uppercase font-bold">Products</h4>
          <ul className="list-none flex flex-col gap-2">
            <li><a href="#" onClick={() => setActiveTool('docx-to-pdf')} className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">DOCX to PDF</a></li>
            <li><a href="#" onClick={() => setActiveTool('pdf-to-docx')} className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">PDF to DOCX</a></li>
            <li><a href="#" onClick={() => setActiveTool('txt-to-pdf')} className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">TXT to PDF</a></li>
            <li><a href="#" onClick={() => setActiveTool('analyser')} className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">PDF Quality Analyser</a></li>
          </ul>
        </div>
        <div className="footer-links">
          <h4 className="text-white text-[0.9rem] mb-4 uppercase font-bold">Company</h4>
          <ul className="list-none flex flex-col gap-2">
            <li><a href="#" className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">About</a></li>
            <li><a href="#" className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">Privacy</a></li>
            <li><a href="#" className="text-[#a0aec0] no-underline text-[0.85rem] hover:text-white">Terms</a></li>
          </ul>
        </div>
      </div>
      <div className="max-w-[1200px] mx-auto mt-8 pt-8 border-t border-[#444] text-[0.75rem] opacity-60 flex justify-between">
        <span>© 2026 Indic PDF · Made in India 🇮🇳</span>
        <span>Secure Temporary Storage Only</span>
      </div>
    </footer>
  );
};

export default Footer;
