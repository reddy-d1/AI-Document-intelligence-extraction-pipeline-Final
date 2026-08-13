import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  Cpu 
} from 'lucide-react';
import { DocumentViewer } from '../components/DocumentViewer';
import { EditableFieldForm } from '../components/EditableFieldForm';
import { ProcessingStatusBadge } from '../components/ProcessingStatusBadge';
import { 
  fetchDocumentApi, 
  fetchDocumentFieldsApi, 
  fetchDocumentValidationApi, 
  updateExtractedFieldApi, 
  overrideClassificationApi, 
  triggerValidateDocumentApi, 
  exportDocumentApi, 
  ExtractedFieldItem, 
  ValidationItem, 
  ValidationGroupedResponse 
} from '../services/api';
import { DocumentMetadata } from '../types';

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [document, setDocument] = useState<DocumentMetadata | null>(null);
  const [fields, setFields] = useState<ExtractedFieldItem[]>([]);
  const [validationData, setValidationData] = useState<ValidationGroupedResponse | null>(null);
  const [editedFields, setEditedFields] = useState<Record<string, string>>({});
  const [selectedBox, setSelectedBox] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadReviewData(id);
    }
  }, [id]);

  const loadReviewData = async (docId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [doc, fList, val] = await Promise.all([
        fetchDocumentApi(docId),
        fetchDocumentFieldsApi(docId),
        fetchDocumentValidationApi(docId),
      ]);
      setDocument(doc);
      setFields(fList);
      setValidationData(val);
    } catch (err: any) {
      console.error('Failed to load review data:', err);
      setError(err.message || 'Failed to connect to backend for document review details.');
    } finally {
      setIsLoading(false);
    }
  };


  const handleFieldChange = (fieldId: string, newValue: string) => {
    setEditedFields((prev) => ({ ...prev, [fieldId]: newValue }));
  };

  const handleSaveCorrections = async () => {
    if (!id || Object.keys(editedFields).length === 0) return;
    setIsSaving(true);
    try {
      for (const [fieldId, val] of Object.entries(editedFields)) {
        await updateExtractedFieldApi(id, fieldId, val);
      }
      // Re-trigger validation engine to update document status & rule flags in real time
      await triggerValidateDocumentApi(id);
      showToast('Field corrections saved & document re-validated successfully!');
      setEditedFields({});
      await loadReviewData(id);
    } catch (err: any) {
      showToast('Error saving corrections', true);
    } finally {
      setIsSaving(false);
    }
  };

  const handleProcessDocument = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      await apiClient.post(`/documents/${id}/process`);
      showToast('Pipeline processing completed successfully!');
      await loadReviewData(id);
    } catch (err: any) {
      showToast('Processing failed: ' + (err.message || 'Pipeline error'), true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClassificationOverride = async (newType: string) => {
    if (!id) return;
    try {
      await overrideClassificationApi(id, newType);
      showToast(`Document reclassified as ${newType.toUpperCase()}`);
      await loadReviewData(id);
    } catch (err) {
      showToast('Error overriding classification', true);
    }
  };

  const handleApproveAndExport = async (format: 'json' | 'csv' = 'json') => {
    if (!id) return;
    setIsExporting(true);
    try {
      // 1. Run validation pipeline first
      await triggerValidateDocumentApi(id);

      // 2. Fetch export payload
      const exportData = await exportDocumentApi(id, format);

      if (format === 'csv') {
        const url = window.URL.createObjectURL(new Blob([exportData]));
        const link = window.document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${document?.filename || 'export'}_${id}.csv`);
        window.document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        const jsonStr = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${document?.filename || 'export'}_${id}.json`);
        window.document.body.appendChild(link);
        link.click();
        link.remove();
      }

      showToast(`Document approved and exported as ${format.toUpperCase()}!`);
      await loadReviewData(id);
    } catch (err) {
      showToast('Export failed', true);
    } finally {
      setIsExporting(false);
    }
  };

  const showToast = (msg: string, isError = false) => {
    setToastMsg(isError ? `Error: ${msg}` : msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const allValidationItems: ValidationItem[] = [
    ...(validationData?.errors || []),
    ...(validationData?.warnings || []),
  ];

  const hasUnsavedChanges = Object.keys(editedFields).length > 0;

  return (
    <div className="space-y-4">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed top-20 right-8 z-50 glass-panel px-4 py-3 rounded-xl border border-blue-500/40 text-blue-300 text-xs shadow-2xl flex items-center space-x-2 animate-bounce">
          <CheckCircle2 className="w-4 h-4 text-blue-400" />
          <span>{toastMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>Error loading document details: {error}</span>
          </div>
          {id && (
            <button
              onClick={() => loadReviewData(id)}
              className="px-3 py-1 bg-red-900/40 hover:bg-red-900/60 rounded text-xs font-semibold transition-colors text-red-200"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Top Header Navigation & Action Bar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            to="/documents"
            className="p-2 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-lg font-bold text-slate-100">
                {isLoading ? 'Loading review details...' : document?.filename || 'Document Review'}
              </h1>
              <ProcessingStatusBadge status={document?.status || (isLoading ? 'processing' : 'uploaded')} />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Review and correct extracted key-values for ID: <span className="font-mono text-slate-400">{id}</span>
            </p>
          </div>
        </div>


        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          {/* Unsaved Changes Counter Badge */}
          {hasUnsavedChanges && (
            <span className="px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-bold animate-pulse flex items-center space-x-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>{Object.keys(editedFields).length} Unsaved Edits</span>
            </span>
          )}

          {/* Document Type Selector */}
          <div className="flex items-center space-x-1 text-xs bg-slate-900 border border-slate-800 rounded-lg px-2 py-1">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <select
              value={document?.document_type || 'other'}
              onChange={(e) => handleClassificationOverride(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer uppercase text-[11px] font-semibold"
            >
              {['invoice', 'contract', 'form', 'report', 'receipt', 'purchase_order', 'resume', 'bank_statement', 'id_document', 'medical_report', 'other'].map((t) => (
                <option key={t} value={t} className="bg-slate-900 text-slate-200">
                  {t.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSaveCorrections}
            disabled={isSaving || !hasUnsavedChanges}
            title={hasUnsavedChanges ? "Click to save all pending field corrections" : "Edit any field below to enable saving corrections"}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              hasUnsavedChanges
                ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-600/30 scale-105'
                : 'bg-slate-800/80 text-slate-400 opacity-60 cursor-not-allowed'
            }`}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Saving...' : 'Save Corrections'}</span>
          </button>

          <button
            onClick={() => handleApproveAndExport('json')}
            disabled={isExporting}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-blue-600/20 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{isExporting ? 'Exporting...' : 'Approve & Export'}</span>
          </button>
        </div>
      </div>

      {/* Split-Screen Layout (50 / 50 Grid) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[680px]">
        {/* Left Pane: Document Viewer */}
        <DocumentViewer
          documentId={id || ''}
          pageCount={document?.page_count || 1}
          selectedBox={selectedBox}
        />

        {/* Right Pane: Editable Fields Form */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col h-full overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <h2 className="text-sm font-semibold text-slate-200">Extracted Fields ({fields.length})</h2>
            {validationData?.failed_count ? (
              <span className="text-[11px] font-medium text-amber-400 flex items-center space-x-1 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-500/30">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{validationData.failed_count} Validation Issue(s)</span>
              </span>
            ) : (
              <span className="text-[11px] font-medium text-emerald-400 flex items-center space-x-1 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>All Rules Passed</span>
              </span>
            )}
          </div>

          <div className="flex-1 overflow-auto pr-1">
            <EditableFieldForm
              fields={fields}
              validationErrors={allValidationItems}
              onFieldChange={handleFieldChange}
              onFieldSelect={(box) => setSelectedBox(box)}
              onProcessDocument={handleProcessDocument}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
