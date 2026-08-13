import React, { useState } from 'react';
import { UploadDropzone } from '../components/UploadDropzone';
import { FileProgressCard } from '../components/FileProgressCard';
import { Layers } from 'lucide-react';

export const UploadPage: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleFilesSelected = (newFiles: File[]) => {
    setSelectedFiles((prev) => [...newFiles, ...prev]);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page Title & Intro */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-100">Document Upload & Ingestion</h1>
        <p className="text-slate-400 text-sm">
          Upload documents for automated OCR text extraction, LLM classification, entity extraction, and validation rules.
        </p>
      </div>

      {/* Drag & Drop Area */}
      <UploadDropzone onFilesSelected={handleFilesSelected} />

      {/* Uploaded Files Queue */}
      {selectedFiles.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-200 flex items-center space-x-2">
              <Layers className="w-4 h-4 text-blue-400" />
              <span>Processing Queue ({selectedFiles.length} files)</span>
            </h2>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Clear Queue
            </button>
          </div>

          <div className="space-y-3">
            {selectedFiles.map((file, idx) => (
              <FileProgressCard key={`${file.name}-${idx}`} file={file} onRemove={() => handleRemoveFile(idx)} />
            ))}
          </div>
        </div>
      )}

      {/* Informational Guidance Banner */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800 space-y-3">
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Automated Processing Pipeline Stages</h3>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-center text-xs">
          {[
            { label: '1. Upload', desc: 'FastAPI Multipart Ingest' },
            { label: '2. Preprocess', desc: 'OpenCV Deskew & CLAHE' },
            { label: '3. OCR', desc: 'Tesseract & Vector PDF' },
            { label: '4. Classify', desc: 'Claude LLM Classifier' },
            { label: '5. Extract', desc: 'Schema Key-Values' },
            { label: '6. Validate', desc: 'Cross-Field Rule Engine' },
          ].map((stage, i) => (
            <div key={i} className="p-2.5 bg-slate-900/60 border border-slate-800 rounded-lg">
              <span className="font-semibold text-blue-400 block">{stage.label}</span>
              <span className="text-[11px] text-slate-400 mt-1 block">{stage.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
