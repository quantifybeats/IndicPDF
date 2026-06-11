import React from 'react';

const Logo = ({ iconOnly = false, className = "" }) => {
  return (
    <div className={`flex items-center gap-3 ${className} group`}>
      <div className="relative w-10 h-10 flex items-center justify-center">
        {/* Dynamic geometric logo */}
        <svg 
          viewBox="0 0 100 100" 
          className="w-full h-full transform group-hover:rotate-12 transition-transform duration-500"
        >
          <defs>
            <linearGradient id="logo-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--primary)" />
              <stop offset="100%" stopColor="#FDBA74" />
            </linearGradient>
          </defs>
          
          {/* Main diamond/sheet shape */}
          <path 
            d="M50 10 L85 35 V75 L50 95 L15 75 V35 L50 10 Z" 
            fill="none" 
            stroke="url(#logo-gradient)" 
            strokeWidth="8" 
            strokeLinejoin="round"
          />
          
          {/* Abstract 'i' + Indic glyph node */}
          <circle cx="50" cy="35" r="8" fill="var(--primary)" />
          <path 
            d="M50 50 V75" 
            stroke="var(--primary)" 
            strokeWidth="8" 
            strokeLinecap="round" 
          />
          
          {/* Subtle Indic 'अ' node connection */}
          <path 
            d="M40 60 C 35 60, 30 65, 30 70" 
            stroke="var(--primary)" 
            strokeWidth="4" 
            strokeLinecap="round" 
            opacity="0.5"
          />
        </svg>
      </div>
      
      {!iconOnly && (
        <div className="flex flex-col -gap-1">
          <span className="font-display font-black text-2xl tracking-tighter text-text leading-none">
            INDIC<span className="text-primary italic">PDF</span>
          </span>
          <span className="text-[9px] font-black tracking-[0.25em] text-text-muted uppercase leading-none mt-1 ml-1 opacity-60">
            ENGINE
          </span>
        </div>
      )}
    </div>
  );
};

export default Logo;
