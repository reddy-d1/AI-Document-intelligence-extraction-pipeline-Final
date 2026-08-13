import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { ReviewPage } from './pages/ReviewPage';
import { DocumentListPage } from './pages/DocumentListPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600/30 selection:text-blue-200">
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/documents" element={<DocumentListPage />} />
              <Route path="/review/:id" element={<ReviewPage />} />
            </Routes>
          </main>
          <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500 bg-slate-950/80">
            AI Document Intelligence & Extraction Engine v1.0 — Powered by Anthropic Claude 3.5 Sonnet & PyMuPDF
          </footer>
        </div>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
