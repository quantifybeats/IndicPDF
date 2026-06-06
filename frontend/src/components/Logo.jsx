import React from 'react';

const Logo = ({ iconOnly = false, className = "" }) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative w-8 h-8 flex items-center justify-center">
        {/* Stylized Document Shape */}
        <svg 
          viewBox="0 0 24 24" 
          fill="none" 
          className="w-full h-full text-primary"
          stroke="currentColor" 
          strokeWidth="2.5" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        >
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        {/* Language Glyph Overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-[10px] font-black mt-1 ml-1 text-bg select-none">अ</span>
        </div>
      </div>
      
      {!iconOnly && (
        <span className="font-black text-xl tracking-tight text-text">
          Indic<span className="text-primary">PDF</span>
        </span>
      )}
    </div>
  );
};

export default Logo;
