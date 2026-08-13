import React, { useEffect, useState } from 'react';
import { X, Clock, CheckCircle2, Loader2, Cpu, FileSearch, Layers } from 'lucide-react';
import { fetchDocumentLogsApi, ProcessingLogItem } from '../services/api';

interface AuditLogModalProps {
  documentId: string | null;
  onClose: () => void;
}

export const AuditLogModal: React.FC<AuditLogModalProps> = ({ documentId, onClose }) => {
  const [logs, setLogs] = useState<ProcessingLogItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (documentId) {
      loadLogs(documentId);
    }
  }, [documentId]);

  const loadLogs = async (id: string) => {
    try {
      setLoading(true);
      const res = await fetchDocumentLogsApi(id);
      setLogs(res);
    } catch (err) {
      // Handled silently
    } finally {
      setLoading(false);
    }
  };

  if (!documentId) return null;

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'upload':
        return Clock;
      case 'preprocessing':
        return Loader2;
      case 'ocr':
        return FileSearch;
      case 'classification':
        return Cpu;
      case 'extraction':
        return Layers;
      case 'validation':
        return CheckCircle2;
      default:
        return Clock;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-panel w-full max-w-xl rounded-2xl border border-slate-800 p-6 space-y-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span>Processing Audit Log & Timeline</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5 font-mono">Document ID: {documentId}</p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Timeline Content */}
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
            <span>Loading audit log events...</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs italic">
            No audit log records found for this document.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
            {logs.map((log) => {
              const Icon = getStageIcon(log.stage);
              const isError = log.status === 'failed';

              return (
                <div key={log.id} className="relative flex items-start space-x-3 group">
                  {/* Timeline Dot */}
                  <div
                    className={`absolute -left-6 p-1 rounded-full border ${
                      isError
                        ? 'bg-red-950 border-red-500 text-red-400'
                        : 'bg-slate-900 border-slate-700 text-blue-400'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>

                  {/* Event Details Card */}
                  <div className="glass-card p-3 rounded-xl flex-1 space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-200 uppercase tracking-wider text-[11px]">
                        {log.stage}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                          isError
                            ? 'bg-red-950/60 text-red-400 border-red-500/30'
                            : 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        {log.status}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>
                        Started: {log.started_at ? new Date(log.started_at).toLocaleTimeString() : 'N/A'}
                      </span>
                      {log.duration_ms !== null && (
                        <span className="font-mono text-blue-300 bg-blue-950/60 px-1.5 py-0.5 rounded border border-blue-500/30">
                          {log.duration_ms} ms
                        </span>
                      )}
                    </div>

                    {log.error_message && (
                      <p className="text-[11px] text-red-400 bg-red-950/40 p-2 rounded border border-red-500/30 font-mono mt-2">
                        {log.error_message}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors"
          >
            Close Timeline
          </button>
        </div>
      </div>
    </div>
  );
};
