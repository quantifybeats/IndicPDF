import React from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  AlertTriangle, 
  FileSearch, 
  Activity, 
  Type, 
  Database, 
  Zap, 
  Layout, 
  ExternalLink 
} from 'lucide-react';

const AnalysisResult = ({ result }) => {
  if (!result) return null;

  const cards = [
    { 
      label: 'Filesize & Pages', 
      value: `${result.size} • ${result.pages} Pages`, 
      icon: <Database size={20} />, 
      color: 'blue' 
    },
    { 
      label: 'Text Layer', 
      value: result.text, 
      icon: <FileSearch size={20} />, 
      color: 'purple' 
    },
    { 
      label: 'Font Status', 
      value: result.fonts, 
      icon: <Type size={20} />, 
      color: 'indigo' 
    },
    { 
      label: 'Render Quality', 
      value: result.render, 
      icon: <CheckCircle2 size={20} />, 
      color: 'green' 
    }
  ];

  return (
    <div className="analysis-dashboard space-y-8">
      {/* Primary Score Card */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden bg-surface-overlay border border-border rounded-radius-xl p-8 shadow-shadow"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 relative z-10">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center text-primary border border-primary/20">
              <Activity size={40} />
            </div>
            <div>
              <h3 className="text-xs font-black text-text-muted uppercase tracking-[0.2em] mb-1">Quality Score</h3>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-black font-display tracking-tighter">{result.score.split('/')[0]}</span>
                <span className="text-xl text-text-muted font-bold">/ 100</span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col items-start md:items-end">
            <div className={`px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest flex items-center gap-2 ${
              result.recommendation.includes('Ready') ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
            }`}>
              <Zap size={14} className="fill-current" />
              {result.recommendation}
            </div>
            <p className="mt-3 text-sm text-text-muted font-medium italic">Standard compliance verified.</p>
          </div>
        </div>
      </motion.div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cards.map((card, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="group bg-surface border border-border rounded-radius-xl p-6 hover:border-primary/30 transition-all shadow-shadow flex items-center gap-5"
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-bg border border-border group-hover:bg-primary/5 group-hover:text-primary transition-colors`}>
              {card.icon}
            </div>
            <div className="min-w-0">
              <span className="text-[10px] font-black text-text-muted uppercase tracking-widest block mb-0.5">{card.label}</span>
              <span className="text-lg font-bold truncate block">{card.value}</span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Warnings & Improvements */}
      {result.warnings && result.warnings.length > 0 && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-yellow-500/5 border border-yellow-500/10 rounded-radius-xl p-6"
        >
          <div className="flex items-center gap-3 text-yellow-500 font-black text-xs uppercase tracking-[0.15em] mb-4">
            <AlertTriangle size={16} /> Warnings Detected
          </div>
          <ul className="space-y-3">
            {result.warnings.map((warning, i) => (
              <li key={i} className="text-sm text-text-muted flex items-start gap-3 leading-relaxed">
                <div className="mt-1.5 w-1.5 h-1.5 bg-yellow-500 rounded-full shrink-0"></div>
                {warning}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Action Area */}
      <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t border-border/50">
        <button 
          onClick={() => window.location.reload()} 
          className="flex-grow py-4 bg-primary text-white rounded-xl font-black text-sm uppercase tracking-widest hover:bg-primary-hover shadow-glow transition-all active:scale-[0.98]"
        >
          Analyse Another PDF
        </button>
      </div>
    </div>
  );
};

export default AnalysisResult;
