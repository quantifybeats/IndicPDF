import React from 'react';
import { useStore } from '../store';
import { Loader2, CheckCircle2 } from 'lucide-react';

const ProcessingSteps = () => {
  const { activeStep } = useStore();

  const steps = [
    { id: 1, label: 'Preparing secure pipeline' },
    { id: 2, label: 'Decoding Indic scripts' },
    { id: 3, label: 'Generating output document' },
  ];

  return (
    <div className="processing-view text-center py-10">
      <div className="relative w-20 h-20 mx-auto mb-8">
        <div className="absolute inset-0 border-4 border-surface border-t-primary rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center text-primary/40">
          <Loader2 size={32} />
        </div>
      </div>
      
      <h3 className="text-2xl font-black mb-2 tracking-tight">Processing Pipeline</h3>
      <p className="text-text-muted text-sm mb-10 max-w-[300px] mx-auto leading-relaxed">
        Our enterprise rendering core is processing your request. Please do not close this tab.
      </p>

      <div className="steps max-w-[320px] mx-auto text-left space-y-4">
        {steps.map((step) => {
          const isActive = activeStep === step.id;
          const isDone = activeStep > step.id;
          
          return (
            <div 
              key={step.id} 
              className={`flex items-center gap-4 transition-all duration-500 ${isActive ? 'opacity-100' : isDone ? 'opacity-100' : 'opacity-30'}`}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all ${
                isDone ? 'bg-green-500/20 text-green-500' : isActive ? 'bg-primary/20 text-primary border border-primary/30 animate-pulse' : 'bg-surface border border-border'
              }`}>
                {isDone ? <CheckCircle2 size={14} /> : <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-primary' : 'bg-text-muted'}`}></div>}
              </div>
              <span className={`text-sm font-bold tracking-tight ${isActive ? 'text-text' : 'text-text-muted'}`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProcessingSteps;
