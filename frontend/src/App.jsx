import React, { Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import axios from 'axios';
import { useStore } from './store';

// Pages
import Home from './pages/Home';
const DocxToPdf = React.lazy(() => import('./pages/DocxToPdf'));
const PdfToDocx = React.lazy(() => import('./pages/PdfToDocx'));
const TxtToPdf = React.lazy(() => import('./pages/TxtToPdf'));
const PdfAnalyser = React.lazy(() => import('./pages/PdfAnalyser'));
const EnglishFontConverter = React.lazy(() => import('./pages/EnglishFontConverter'));
const OcrTool = React.lazy(() => import('./components/OcrTool'));
const ImageConverter = React.lazy(() => import('./pages/ImageConverter'));
const VideoConverter = React.lazy(() => import('./pages/VideoConverter'));
const AudioConverter = React.lazy(() => import('./pages/AudioConverter'));

function App() {
  const [isWakingUp, setIsWakingUp] = useState(true);
  const { theme, setTheme } = useStore();

  useEffect(() => {
    // Initial theme setup
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    const wakeServer = async () => {
      try {
        await axios.get('/health', { timeout: 10000 });
      } catch (e) {
        console.log("Server still sleeping or health check failed");
      } finally {
        setIsWakingUp(false);
      }
    };
    wakeServer();
  }, []);

  if (isWakingUp) {
    return (
      <div className={`min-h-screen flex flex-col items-center justify-center p-6 text-center transition-colors duration-500 ${theme === 'dark' ? 'bg-[#0B0B0B] text-white' : 'bg-[#F8F9FA] text-[#111827]'}`}>
        <div className="w-16 h-16 border-4 border-surface-overlay border-t-primary rounded-full animate-spin mb-8"></div>
        <h1 className="text-2xl font-black mb-2 tracking-tight">Initializing Engine...</h1>
        <p className="text-text-muted max-w-[400px]">Connecting to our high-fidelity rendering core on Render Cloud. Thank you for your patience.</p>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-bg text-text">
        <Navbar />
        <main className="flex-grow">
          <Suspense fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <div className="animate-pulse text-text-muted font-black italic tracking-widest uppercase text-xs">Synchronizing Workspace...</div>
            </div>
          }>
            <Routes>
              <Route path="/" element={<Home />} />
              
              {/* Tool Routes */}
              <Route path="/docx-to-pdf" element={<DocxToPdf />} />
              <Route path="/pdf-to-docx" element={<PdfToDocx />} />
              <Route path="/txt-to-pdf" element={<TxtToPdf />} />
              <Route path="/pdf-analyser" element={<PdfAnalyser />} />
              <Route path="/english-font-converter" element={<EnglishFontConverter />} />
              <Route path="/ocr" element={<OcrTool />} />
              <Route path="/image-converter" element={<ImageConverter />} />
              <Route path="/video-converter" element={<VideoConverter />} />
              <Route path="/audio-converter" element={<AudioConverter />} />

              {/* Redirects for requested paths */}
              <Route path="/pdf-tools" element={<Navigate to="/" replace />} />
              <Route path="/font-converter" element={<Navigate to="/english-font-converter" replace />} />
              
              {/* Fallback */}
              <Route path="*" element={<Home />} />
            </Routes>
          </Suspense>
        </main>
        <Footer />
        
        {/* Global Toast Stack Placeholder */}
        <div id="toasts" className="fixed bottom-6 right-6 z-[2000] flex flex-col gap-2"></div>
      </div>
    </Router>
  );
}

export default App;
