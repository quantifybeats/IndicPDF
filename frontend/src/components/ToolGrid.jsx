import React from 'react';
import { Languages, Zap, Cloud, ScanText, ShieldCheck, MonitorSmartphone } from 'lucide-react';

const features = [
  {
    icon: Languages,
    title: 'Indic Script Support',
    desc: 'Telugu, Devanagari, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia and more — with perfect glyph rendering.',
  },
  {
    icon: Zap,
    title: 'Fast and easy',
    desc: 'Drop your file, choose a tool and click Convert. Most conversions finish in under 1–2 minutes.',
  },
  {
    icon: Cloud,
    title: 'Server-side processing',
    desc: 'Conversions run on our cloud servers and never consume your device’s capacity.',
  },
  {
    icon: ScanText,
    title: '9 Language OCR',
    desc: 'Hindi, Telugu, Tamil, Bengali, Gujarati, Kannada, Malayalam, Odia and Punjabi via Tesseract.',
  },
  {
    icon: ShieldCheck,
    title: 'Security guaranteed',
    desc: 'Uploaded files are deleted instantly and outputs after 24 hours. Your privacy is guaranteed.',
  },
  {
    icon: MonitorSmartphone,
    title: 'All devices supported',
    desc: 'IndicPDF is browser-based and works everywhere. No download or install required.',
  },
];

const ToolGrid = () => {
  return (
    <section className="bg-surface-overlay/60 py-20 px-4 border-t border-border">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="font-display text-3xl md:text-4xl font-extrabold tracking-tight mb-3 text-gradient">
            Everything you need
          </h2>
          <p className="text-text-muted text-base max-w-xl mx-auto">
            One workspace for every Indic document conversion — built for fidelity, speed and privacy.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="group bg-surface border border-border rounded-radius-xl p-7 shadow-shadow transition-all duration-300 hover:-translate-y-1.5 hover:shadow-shadow-lg hover:border-primary/40"
            >
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 bg-primary/10 text-primary border border-primary/20 group-hover:scale-110 transition-transform">
                <Icon className="w-6 h-6" />
              </div>
              <h3 className="font-display text-lg font-bold mb-2 text-text">{title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ToolGrid;
