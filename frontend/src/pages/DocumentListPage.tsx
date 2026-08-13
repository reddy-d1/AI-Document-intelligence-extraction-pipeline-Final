import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Search, 
  Download, 
  LayoutGrid, 
  LayoutList, 
  ArrowRight, 
  Clock, 
  FileText 
} from 'lucide-react';
import { ProcessingStatusBadge } from '../components/ProcessingStatusBadge';
import { AuditLogModal } from '../components/AuditLogModal';
import { apiClient } from '../services/api';
import { DocumentMetadata } from '../types';

export const DocumentListPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [activeAuditDocId, setActiveAuditDocId] = useState<string | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isExportingBatch, setIsExportingBatch] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, [selectedStatus, selectedType]);

  const loadDocuments = async (queryStr = searchQuery) => {
    try {
      let url = `/documents?page_size=50`;
      if (selectedStatus !== 'all') url += `&status=${selectedStatus}`;
      if (selectedType !== 'all') url += `&document_type=${selectedType}`;
      if (queryStr.trim()) url += `&q=${encodeURIComponent(queryStr.trim())}`;

      const res = await apiClient.get(url);
      setDocuments(res.data.items || []);
    } catch (err) {
      // Handled silently
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadDocuments(searchQuery);
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedDocIds(documents.map((d) => d.id));
    } else {
      setSelectedDocIds([]);
    }
  };

  const handleSelectOne = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleBatchExport = async () => {
    if (selectedDocIds.length === 0) return;
    setIsExportingBatch(true);
    try {
      const response = await apiClient.post('/documents/batch-export', {
        document_ids: selectedDocIds,
        format: 'json',
        as_zip: true,
      }, { responseType: 'blob' });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = window.document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'documents_batch_export.zip');
      window.document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      // Handled silently
    } finally {
      setIsExportingBatch(false);
    }
  };

  const statusTabs = [
    { key: 'all', label: 'All Documents' },
    { key: 'needs_review', label: 'Needs Review' },
    { key: 'validated', label: 'Validated' },
    { key: 'ocr_complete', label: 'OCR Complete' },
    { key: 'failed', label: 'Failed' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Document Repository</h1>
          <p className="text-slate-400 text-sm">
            Search, filter, inspect processing audit logs, and export document datasets.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {selectedDocIds.length > 0 && (
            <button
              onClick={handleBatchExport}
              disabled={isExportingBatch}
              className="flex items-center space-x-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isExportingBatch ? 'Exporting...' : `Export ZIP (${selectedDocIds.length})`}</span>
            </button>
          )}

          <Link
            to="/upload"
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            <FileText className="w-4 h-4 text-blue-400" />
            <span>Upload New</span>
          </Link>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex items-center space-x-3">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Search filename, OCR text, or extracted key-values..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 pl-10 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          </div>

          <button
            type="submit"
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl transition-colors"
          >
            Search
          </button>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2.5 focus:outline-none focus:border-blue-500 cursor-pointer uppercase font-medium"
          >
            <option value="all">All Types</option>
            {['invoice', 'contract', 'form', 'report', 'receipt', 'purchase_order', 'other'].map((t) => (
              <option key={t} value={t}>
                {t.replace('_', ' ')}
              </option>
            ))}
          </select>

          {/* View Mode Toggle */}
          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-xl p-1">
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === 'table' ? 'bg-slate-800 text-blue-400' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <LayoutList className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg transition-colors ${
                viewMode === 'grid' ? 'bg-slate-800 text-blue-400' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </form>

        {/* Status Filter Tabs */}
        <div className="flex items-center space-x-2 border-t border-slate-800/60 pt-3 overflow-x-auto">
          {statusTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setSelectedStatus(tab.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                selectedStatus === tab.key
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Document View Area */}
      {viewMode === 'table' ? (
        <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      onChange={handleSelectAll}
                      checked={selectedDocIds.length > 0 && selectedDocIds.length === documents.length}
                      className="rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-0 cursor-pointer"
                    />
                  </th>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Upload Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Audit Log</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500 italic">
                      No documents matching filter criteria found.
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-900/50 transition-colors group">
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={selectedDocIds.includes(doc.id)}
                          onChange={() => handleSelectOne(doc.id)}
                          className="rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-0 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-200 truncate max-w-xs">{doc.filename}</td>
                      <td className="py-3 px-4 font-mono text-[11px] uppercase text-purple-400">{doc.document_type}</td>
                      <td className="py-3 px-4 text-slate-400">{new Date(doc.upload_date).toLocaleDateString()}</td>
                      <td className="py-3 px-4">
                        <ProcessingStatusBadge status={doc.status} />
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => setActiveAuditDocId(doc.id)}
                          className="p-1 text-slate-400 hover:text-blue-400 hover:bg-slate-800 rounded transition-colors"
                          title="View Processing Audit Log"
                        >
                          <Clock className="w-4 h-4 mx-auto" />
                        </button>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <Link
                          to={`/review/${doc.id}`}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 rounded-lg border border-blue-500/30 font-medium transition-colors"
                        >
                          <span>Review</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="glass-card p-5 rounded-2xl space-y-3 border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-purple-400 uppercase font-semibold">{doc.document_type}</span>
                <ProcessingStatusBadge status={doc.status} />
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 text-sm truncate">{doc.filename}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{new Date(doc.upload_date).toLocaleString()}</p>
              </div>

              <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
                <button
                  onClick={() => setActiveAuditDocId(doc.id)}
                  className="text-xs text-slate-400 hover:text-blue-400 flex items-center space-x-1"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Audit Log</span>
                </button>

                <Link
                  to={`/review/${doc.id}`}
                  className="inline-flex items-center space-x-1 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  <span>Review</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Audit Log Modal Drawer */}
      <AuditLogModal documentId={activeAuditDocId} onClose={() => setActiveAuditDocId(null)} />
    </div>
  );
};
