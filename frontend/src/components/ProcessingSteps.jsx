import React from 'react';
import { useStore } from '../store';

const ProcessingSteps = () => {
  const { activeStep } = useStore();

  const steps = [
    { id: 1, label: 'Preparing secure pipeline' },
    { id: 2, label: 'Decoding Indic scripts' },
    { id: 3, label: 'Generating output document' },
  ];

  return (
    <div className="processing-view active text-center py-8">
      <div className="spinner"></div>
      <h3 className="text-xl font-bold mb-2">Processing your document...</h3>
      <p className="text-text-muted text-[0.9rem] mb-6">Please keep this window open.</p>
      <div className="steps max-w-[320px] mx-auto text-left text-[0.9rem]">
        {steps.map((step) => (
          <div 
            key={step.id} 
            className={`step ${activeStep === step.id ? 'active' : ''} ${activeStep > step.id ? 'done' : ''}`}
          >
            <div className="step-dot"></div>
            {step.label}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProcessingSteps;
