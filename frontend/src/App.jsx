import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';

// Pages
import Home from './pages/Home';
const DocxToPdf = React.lazy(() => import('./pages/DocxToPdf'));
const PdfToDocx = React.lazy(() => import('./pages/PdfToDocx'));
const TxtToPdf = React.lazy(() => import('./pages/TxtToPdf'));
const PdfAnalyser = React.lazy(() => import('./pages/PdfAnalyser'));
const EnglishFontConverter = React.lazy(() => import('./pages/EnglishFontConverter'));

function App() {
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
              <Route path="/docx-to-pdf" element={<DocxToPdf />} />
              <Route path="/pdf-to-docx" element={<PdfToDocx />} />
              <Route path="/txt-to-pdf" element={<TxtToPdf />} />
              <Route path="/pdf-analyser" element={<PdfAnalyser />} />
              <Route path="/english-font-converter" element={<EnglishFontConverter />} />
              
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
