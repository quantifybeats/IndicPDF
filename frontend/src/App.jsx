import React, { Suspense } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ToolGrid from './components/ToolGrid';
import Footer from './components/Footer';
import { useStore } from './store';

const WorkspaceModal = React.lazy(() => import('./components/WorkspaceModal'));

function App() {
  const isModalOpen = useStore((state) => state.isModalOpen);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-grow">
        <Hero />
        <ToolGrid />
      </main>
      <Footer />
      
      {/* Lazy loaded Workspace Modal */}
      <Suspense fallback={null}>
        {isModalOpen && <WorkspaceModal />}
      </Suspense>

      {/* Global Toast Stack Placeholder */}
      <div id="toasts" className="fixed bottom-6 right-6 z-[2000] flex flex-col gap-2"></div>
    </div>
  );
}

export default App;
