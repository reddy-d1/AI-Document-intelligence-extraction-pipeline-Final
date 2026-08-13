import React, { useState, useRef } from 'react';
import { UploadCloud, AlertCircle } from 'lucide-react';

interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.tiff', '.tif'];
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onFilesSelected, disabled = false }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndFilterFiles = (rawFiles: FileList | File[]): File[] => {
    const validFiles: File[] = [];
    let err: string | null = null;

    Array.from(rawFiles).forEach((file) => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        err = `File "${file.name}" has unsupported format. Allowed: PDF, PNG, JPG, DOCX, TIFF.`;
      } else if (file.size > MAX_SIZE_BYTES) {
        err = `File "${file.name}" exceeds 20MB size limit.`;
      } else {
        validFiles.push(file);
      }
    });

    if (err) {
      setErrorMsg(err);
    } else {
      setErrorMsg(null);
    }

    return validFiles;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles = validateAndFilterFiles(e.dataTransfer.files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = validateAndFilterFiles(e.target.files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`glass-panel p-8 rounded-2xl border-2 border-dashed transition-all duration-200 text-center cursor-pointer group ${
          isDragOver
            ? 'border-blue-500 bg-blue-950/20 scale-[1.01]'
            : 'border-slate-800 hover:border-slate-700'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.docx,.tiff,.tif"
          className="hidden"
          onChange={handleFileChange}
          disabled={disabled}
        />
        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="p-4 rounded-2xl bg-blue-600/10 text-blue-400 group-hover:scale-110 border border-blue-500/20 transition-transform">
            <UploadCloud className="w-10 h-10" />
          </div>
          <div>
            <p className="text-base font-semibold text-slate-200">
              Drag & drop document files here, or <span className="text-blue-400 underline">browse files</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Supports multi-file upload for PDF, PNG, JPG, DOCX, TIFF (Up to 20MB per file)
            </p>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};
