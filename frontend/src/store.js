import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useStore = create(
  persist(
    (set) => ({
      activeToolId: null,
      isModalOpen: false,
      currentFiles: [],
      files: [],
      uploadProgress: 0,
      processingStep: 0, // 0: upload, 1: processing, 2: success
      activeStep: 1, // 1: preparing, 2: decoding, 3: generating
      jobIds: [],
      analysisResult: null,
      error: null,
      theme: localStorage.getItem('theme') || 'light',

      setTheme: (theme) => {
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        set({ theme });
      },

      setActiveTool: (toolId) => set({ activeToolId: toolId, isModalOpen: true, processingStep: 0, currentFiles: [], files: [], uploadProgress: 0, analysisResult: null, error: null }),
      closeModal: () => set({ isModalOpen: false, activeToolId: null }),
      
      setFiles: (files) => {
        const formatted = Array.from(files).map((f) => {
          if (f.id) return f;
          return {
            id: Math.random().toString(36).substring(2, 9),
            name: f.name,
            size: f.size,
            type: f.type || f.name.split('.').pop().toLowerCase(),
            outputFormat: '',
            status: 'idle',
            file: f,
            downloadUrl: null,
            progress: 0,
            error: null,
          };
        });
        set({ files: formatted, currentFiles: files, error: null });
      },
      
      addFiles: (incoming) => {
        set((state) => {
          const formatted = Array.from(incoming).map((f) => {
            if (f.id) return f;
            return {
              id: Math.random().toString(36).substring(2, 9),
              name: f.name,
              size: f.size,
              type: f.type || f.name.split('.').pop().toLowerCase(),
              outputFormat: '',
              status: 'idle',
              file: f,
              downloadUrl: null,
              progress: 0,
              error: null,
            };
          });
          const existingNames = new Set(state.files.map((f) => f.name));
          const fresh = formatted.filter((f) => !existingNames.has(f.name));
          const mergedFiles = [...state.files, ...fresh];
          const mergedCurrentFiles = [...state.currentFiles, ...fresh.map((f) => f.file).filter(Boolean)];
          return { files: mergedFiles, currentFiles: mergedCurrentFiles, error: null };
        });
      },

      updateFile: (id, updates) => {
        set((state) => ({
          files: state.files.map((f) => (f.id === id ? { ...f, ...updates } : f)),
        }));
      },

      clearFiles: () => set({ files: [], currentFiles: [] }),

      setUploadProgress: (progress) => set({ uploadProgress: progress }),
      setProcessingStep: (step) => set({ processingStep: step }),
      setActiveStep: (step) => set({ activeStep: step }),
      setJobIds: (ids) => set({ jobIds: ids }),
      setAnalysisResult: (result) => set({ analysisResult: result }),
      setError: (err) => set({ error: err }),
      resetWorkspace: () => set({ currentFiles: [], files: [], uploadProgress: 0, processingStep: 0, activeStep: 1, analysisResult: null, error: null }),
    }),
    {
      name: 'indic-pdf-workspace-store',
      partialize: (state) => ({
        theme: state.theme,
        files: state.files.map(({ file, downloadUrl, ...rest }) => ({
          ...rest,
          downloadUrl: null, // objectURLs expire, so reset on storage restore
        })),
      }),
    }
  )
);

