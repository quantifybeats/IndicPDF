import React from 'react';
import { CheckCircle, AlertTriangle, Info, FileText, BarChart } from 'lucide-react';

const AnalysisResult = ({ result }) => {
  if (!result) return null;

  return (
    <div className="analysis-result space-y-6">
      <div className="flex items-center justify-between bg-surface p-6 rounded-radius border border-border">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-full">
            <BarChart size={32} className="text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-text-muted uppercase tracking-wider">Quality Score</h3>
            <p className="text-3xl font-black text-text">{result.score}</p>
          </div>
        </div>
        <div className="text-right">
          <span className={`px-4 py-1 rounded-full text-sm font-bold ${
            result.recommendation.includes('Ready') ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'
          }`}>
            {result.recommendation}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface p-4 rounded-radius border border-border flex items-center gap-3">
          <FileText size={20} className="text-primary" />
          <div>
            <span className="text-xs text-text-muted block">Filesize & Pages</span>
            <span className="text-sm font-bold">{result.size} • {result.pages} Pages</span>
          </div>
        </div>
        <div className="bg-surface p-4 rounded-radius border border-border flex items-center gap-3">
          <Info size={20} className="text-primary" />
          <div>
            <span className="text-xs text-text-muted block">Text Layer</span>
            <span className="text-sm font-bold">{result.text}</span>
          </div>
        </div>
        <div className="bg-surface p-4 rounded-radius border border-border flex items-center gap-3">
          <CheckCircle size={20} className="text-green-500" />
          <div>
            <span className="text-xs text-text-muted block">Font Status</span>
            <span className="text-sm font-bold">{result.fonts}</span>
          </div>
        </div>
        <div className="bg-surface p-4 rounded-radius border border-border flex items-center gap-3">
          <CheckCircle size={20} className="text-green-500" />
          <div>
            <span className="text-xs text-text-muted block">Render Quality</span>
            <span className="text-sm font-bold">{result.render}</span>
          </div>
        </div>
      </div>

      {result.warnings && result.warnings.length > 0 && (
        <div className="bg-yellow-500/5 border border-yellow-500/20 p-4 rounded-radius">
          <h4 className="flex items-center gap-2 text-yellow-600 font-bold text-sm mb-2">
            <AlertTriangle size={16} /> Warnings & Improvements
          </h4>
          <ul className="space-y-1">
            {result.warnings.map((warning, i) => (
              <li key={i} className="text-sm text-text-muted flex items-start gap-2">
                <span className="mt-1.5 w-1 h-1 bg-yellow-500 rounded-full flex-shrink-0"></span>
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button 
        onClick={() => window.location.reload()} 
        className="w-full py-3 bg-bg border border-border rounded-radius font-bold hover:bg-surface transition-colors"
      >
        Analyse Another PDF
      </button>
    </div>
  );
};

export default AnalysisResult;
