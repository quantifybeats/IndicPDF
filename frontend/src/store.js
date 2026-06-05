import { create } from 'zustand';

export const useStore = create((set) => ({
  activeToolId: null,
  isModalOpen: false,
  currentFiles: [],
  uploadProgress: 0,
  processingStep: 0, // 0: upload, 1: processing, 2: success
  activeStep: 1, // 1: preparing, 2: decoding, 3: generating
  jobIds: [],
  analysisResult: null,
  error: null,

  setActiveTool: (toolId) => set({ activeToolId: toolId, isModalOpen: true, processingStep: 0, currentFiles: [], uploadProgress: 0, analysisResult: null, error: null }),
  closeModal: () => set({ isModalOpen: false, activeToolId: null }),
  setFiles: (files) => set({ currentFiles: files, error: null }),
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  setProcessingStep: (step) => set({ processingStep: step }),
  setActiveStep: (step) => set({ activeStep: step }),
  setJobIds: (ids) => set({ jobIds: ids }),
  setAnalysisResult: (result) => set({ analysisResult: result }),
  setError: (err) => set({ error: err }),
  resetWorkspace: () => set({ currentFiles: [], uploadProgress: 0, processingStep: 0, activeStep: 1, analysisResult: null, error: null }),
}));
