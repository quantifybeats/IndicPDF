import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Zap, Shield, Sparkles } from 'lucide-react';

const Hero = () => {
  return (
    <section className="hero-section pt-24 pb-16 px-6 text-center overflow-hidden relative">
      {/* Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-primary/5 rounded-full blur-[100px] pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="max-w-[900px] mx-auto relative z-10"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface border border-border mb-8">
          <Sparkles size={14} className="text-primary" />
          <span className="text-[11px] font-black uppercase tracking-widest text-text-muted">Enterprise Indic Shaping Engine</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight leading-[1.05]">
          Indic script documents,<br />
          <span className="text-primary">perfectly rendered.</span>
        </h1>
        
        <p className="text-lg md:text-xl text-text-muted mb-10 max-w-[700px] mx-auto leading-relaxed">
          High-fidelity PDF conversion and text extraction for Telugu, Hindi, and Tamil. 
          Zero broken glyphs, zero matra displacement, 100% Unicode compliant.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a href="#all" className="action-btn !mt-0 !w-auto px-10 py-4 flex items-center gap-2 group">
            Start Using Tools <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </a>
          <button className="px-10 py-4 bg-surface border border-border rounded-lg font-bold hover:bg-surface/80 transition-all">
            View Documentation
          </button>
        </div>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-[800px] mx-auto opacity-60">
          <div className="flex items-center gap-3 justify-center">
            <Zap size={18} className="text-primary" />
            <span className="text-xs font-bold uppercase tracking-widest">Fast Processing</span>
          </div>
          <div className="flex items-center gap-3 justify-center">
            <Shield size={18} className="text-primary" />
            <span className="text-xs font-bold uppercase tracking-widest">Secure & Private</span>
          </div>
          <div className="flex items-center gap-3 justify-center">
            <Sparkles size={18} className="text-primary" />
            <span className="text-xs font-bold uppercase tracking-widest">Perfect Ligatures</span>
          </div>
        </div>
      </motion.div>
    </section>
  );
};

export default Hero;
