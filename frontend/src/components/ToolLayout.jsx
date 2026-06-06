import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Clock, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const ToolLayout = ({ title, description, icon, children }) => {
  return (
    <div className="container mx-auto px-6 py-12 max-w-[900px]">
      <div className="mb-8">
        <Link to="/" className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors text-sm font-bold uppercase tracking-wider mb-6">
          <ArrowLeft size={16} /> Back to Tools
        </Link>
        <div className="flex items-start gap-6">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center text-3xl text-primary border border-primary/20 shrink-0">
            {icon}
          </div>
          <div>
            <h1 className="text-3xl font-black mb-2 tracking-tight">{title}</h1>
            <p className="text-text-muted leading-relaxed max-w-[600px]">{description}</p>
          </div>
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="workspace-card"
      >
        <div className="p-8 md:p-12">
          {children}

          <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-center gap-8 opacity-60">
            <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-widest">
              <ShieldCheck size={16} className="text-green-500" /> Files are not stored
            </div>
            <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-widest">
              <Clock size={16} className="text-primary" /> Auto-deleted after processing
            </div>
            <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-widest">
              <ShieldCheck size={16} className="text-primary" /> SSL Encrypted
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ToolLayout;
