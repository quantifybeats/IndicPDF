import React, { Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import axios from 'axios';

// Pages
import Home from './pages/Home';
const DocxToPdf = React.lazy(() => import('./pages/DocxToPdf'));
const PdfToDocx = React.lazy(() => import('./pages/PdfToDocx'));
const TxtToPdf = React.lazy(() => import('./pages/TxtToPdf'));
const PdfAnalyser = React.lazy(() => import('./pages/PdfAnalyser'));
const EnglishFontConverter = React.lazy(() => import('./pages/EnglishFontConverter'));

function App() {
  const [isWakingUp, setIsWakingUp] = useState(true);

  useEffect(() => {
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
      <div className="min-h-screen bg-bg flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 border-4 border-surface border-t-primary rounded-full animate-spin mb-8"></div>
        <h1 className="text-2xl font-black mb-2 tracking-tight">Waking up IndicPDF Engine...</h1>
        <p className="text-text-muted max-w-[400px]">Our high-fidelity rendering core is initializing on the Render cloud. This usually takes 10-15 seconds. Thank you for your patience!</p>
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
              <div className="animate-pulse text-text-muted font-bold italic">Loading IndicPDF Workspace...</div>
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
