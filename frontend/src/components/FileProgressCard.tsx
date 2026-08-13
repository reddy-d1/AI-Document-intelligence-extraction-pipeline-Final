import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FileText, ArrowRight, RotateCcw, X, CheckCircle2, AlertTriangle, Layers, Cpu } from 'lucide-react';
import { ProcessingStatusBadge } from './ProcessingStatusBadge';
import { 
  uploadDocumentApi, 
  triggerProcessDocumentApi, 
  fetchDocumentStatusApi, 
  fetchDocumentFieldsApi, 
  fetchDocumentValidationApi, 
  PipelineStatusResponse 
} from '../services/api';

interface FileProgressCardProps {
  file: File;
  onRemove?: () => void;
}

export const FileProgressCard: React.FC<FileProgressCardProps> = ({ file, onRemove }) => {
  const [docId, setDocId] = useState<string | null>(null);
  const [statusState, setStatusState] = useState<PipelineStatusResponse | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [fieldsCount, setFieldsCount] = useState<number>(0);
  const [hasValidationErrors, setHasValidationErrors] = useState<boolean>(false);

  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    startUploadAndPipeline();
    return () => {
      isMountedRef.current = false;
    };
  }, [file]);

  const startUploadAndPipeline = async () => {
    try {
      setErrorMsg(null);
      setUploadProgress(20);

      // 1. Upload Document
      const uploadRes = await uploadDocumentApi(file);
      if (!isMountedRef.current) return;
      
      setDocId(uploadRes.id);
      setUploadProgress(30);

      // 2. Trigger Full Pipeline Process
      triggerProcessDocumentApi(uploadRes.id).catch(() => {});

      // 3. Start Polling Pipeline Status
      pollStatus(uploadRes.id);
    } catch (err: any) {
      if (!isMountedRef.current) return;
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      setErrorMsg(msg);
    }
  };

  const pollStatus = async (id: string) => {
    const interval = setInterval(async () => {
      if (!isMountedRef.current) {
        clearInterval(interval);
        return;
      }

      try {
        const stat = await fetchDocumentStatusApi(id);
        if (!isMountedRef.current) return;

        setStatusState(stat);
        setUploadProgress(stat.progress_percentage);

        if (['validated', 'needs_review', 'failed'].includes(stat.status)) {
          clearInterval(interval);

          if (stat.status !== 'failed') {
            fetchSummaryData(id);
          }
        }
      } catch (err) {
        // Continue polling silently
      }
    }, 1500);
  };

  const fetchSummaryData = async (id: string) => {
    try {
      const fields = await fetchDocumentFieldsApi(id);
      if (isMountedRef.current && Array.isArray(fields)) {
        setFieldsCount(fields.length);
      }

      const valData = await fetchDocumentValidationApi(id);
      if (isMountedRef.current && valData && Array.isArray(valData.errors)) {
        setHasValidationErrors(valData.errors.length > 0);
      }
    } catch (err) {
      // Ignore summary fetch errors
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const isComplete = statusState?.status === 'validated' || statusState?.status === 'needs_review';

  return (
    <div className="glass-card p-5 rounded-xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-blue-600/10 border border-blue-500/30 text-blue-400">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200 truncate max-w-xs sm:max-w-md">{file.name}</h3>
            <span className="text-xs text-slate-500">{formatFileSize(file.size)}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <ProcessingStatusBadge status={statusState?.status || (errorMsg ? 'failed' : 'uploaded')} />
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1 text-slate-500 hover:text-slate-300 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {!errorMsg && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{statusState?.current_stage || 'Preparing upload...'}</span>
            <span className="font-semibold text-blue-400">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                statusState?.status === 'failed'
                  ? 'bg-red-500'
                  : statusState?.status === 'validated'
                  ? 'bg-emerald-500'
                  : statusState?.status === 'needs_review'
                  ? 'bg-amber-500'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-500 animate-pulse'
              }`}
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Retry Display */}
      {errorMsg && (
        <div className="p-3 bg-red-950/40 border border-red-500/30 rounded-lg text-xs text-red-400 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button
            onClick={startUploadAndPipeline}
            className="flex items-center space-x-1 px-2.5 py-1 bg-red-900/40 hover:bg-red-900/60 rounded text-red-300 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Completion Summary Card */}
      {isComplete && docId && (
        <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs bg-slate-900/40 p-3 rounded-lg">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-1 text-slate-300">
              <Cpu className="w-4 h-4 text-purple-400" />
              <span className="text-slate-500">Type:</span>
              <span className="font-semibold uppercase tracking-wider text-purple-300">
                {statusState?.document_type || 'Unknown'}
              </span>
            </div>
            <div className="flex items-center space-x-1 text-slate-300">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-500">Extracted:</span>
              <span className="font-semibold text-slate-200">{fieldsCount} Fields</span>
            </div>
            <div className="flex items-center space-x-1">
              {hasValidationErrors ? (
                <span className="text-amber-400 flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Validation Warning</span>
                </span>
              ) : (
                <span className="text-emerald-400 flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Validated</span>
                </span>
              )}
            </div>
          </div>

          <Link
            to={`/review/${docId}`}
            className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
          >
            <span>Review Data</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};
