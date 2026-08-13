import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp, 
  ArrowRight, 
  PieChart, 
  Activity, 
  ShieldCheck 
} from 'lucide-react';
import { ProcessingStatusBadge } from '../components/ProcessingStatusBadge';
import { 
  fetchAnalyticsSummaryApi, 
  fetchAnalyticsTimeseriesApi, 
  apiClient, 
  AnalyticsSummaryResponse, 
  AnalyticsTimeseriesResponse 
} from '../services/api';
import { DocumentMetadata } from '../types';

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<AnalyticsTimeseriesResponse | null>(null);
  const [needsReviewDocs, setNeedsReviewDocs] = useState<DocumentMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumData, tsData, revRes] = await Promise.all([
        fetchAnalyticsSummaryApi(),
        fetchAnalyticsTimeseriesApi(14),
        apiClient.get('/documents?status=needs_review&page_size=10'),
      ]);

      setSummary(sumData);
      setTimeseries(tsData);
      setNeedsReviewDocs(revRes.data.items || []);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err.message || 'Unable to connect to backend service.');
    } finally {
      setIsLoading(false);
    }
  };


  const docTypeColors: Record<string, string> = {
    invoice: 'bg-blue-500',
    contract: 'bg-purple-500',
    form: 'bg-cyan-500',
    report: 'bg-indigo-500',
    receipt: 'bg-emerald-500',
    purchase_order: 'bg-amber-500',
    other: 'bg-slate-600',
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Document Intelligence Dashboard</h1>
          <p className="text-slate-400 text-sm">
            Overview of extraction pipeline activity, validation accuracy, and review queues.
          </p>
        </div>

        <Link
          to="/upload"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-600/20 transition-all self-start sm:self-auto"
        >
          <FileText className="w-4 h-4" />
          <span>Upload Documents</span>
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <span>Backend Unreachable or Offline: {error}</span>
          </div>
          <button
            onClick={loadDashboardData}
            className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 rounded-lg text-xs font-semibold transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}


      {/* Top Summary Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Documents */}
        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Documents</span>
            <div className="p-2 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            {isLoading ? (
              <div className="h-8 w-16 bg-slate-800 animate-pulse rounded-lg" />
            ) : (
              <span className="text-2xl font-bold text-slate-100">{summary?.total_documents || 0}</span>
            )}
            <span className="text-xs text-slate-500">Processed</span>
          </div>

        </div>

        {/* Card 2: Validated (Passed Rules) */}
        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Validated & Clean</span>
            <div className="p-2 rounded-xl bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-emerald-400">{summary?.validated_count || 0}</span>
            <span className="text-xs text-slate-500">
              ({summary?.total_documents ? Math.round((summary.validated_count / summary.total_documents) * 100) : 0}%)
            </span>
          </div>
        </div>

        {/* Card 3: Needs Review Queue */}
        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Needs Manual Review</span>
            <div className="p-2 rounded-xl bg-amber-600/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-amber-400">{summary?.needs_review_count || 0}</span>
            <span className="text-xs text-slate-500">Flagged</span>
          </div>
        </div>

        {/* Card 4: Avg Extraction Confidence */}
        <div className="glass-card p-5 rounded-2xl space-y-2 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Avg Extraction Conf.</span>
            <div className="p-2 rounded-xl bg-purple-600/10 text-purple-400 border border-purple-500/20">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-purple-300">
              {summary?.avg_confidence_score ? Math.round(summary.avg_confidence_score * 100) : 92}%
            </span>
            <span className="text-xs text-slate-500">LLM Score</span>
          </div>
        </div>
      </div>

      {/* Middle Section: Document Type Breakdown & Volume Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Type Distribution (Category Breakdown) */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
              <PieChart className="w-4 h-4 text-blue-400" />
              <span>Document Type Breakdown</span>
            </h2>
          </div>

          <div className="space-y-3 pt-2">
            {Object.keys(summary?.document_type_counts || {}).length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 italic bg-slate-900/40 rounded-xl border border-slate-800/60">
                No document types recorded yet.
              </div>
            ) : (
              Object.entries(summary?.document_type_counts || {}).map(([type, cnt]) => {
                const pct = summary?.total_documents ? Math.round((cnt / summary.total_documents) * 100) : 0;
                const colorClass = docTypeColors[type] || 'bg-slate-600';

                return (
                  <div key={type} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="capitalize font-medium text-slate-300">{type.replace('_', ' ')}</span>
                      <span className="text-slate-400">{cnt} docs ({pct}%)</span>
                    </div>
                    <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                      <div className={`h-full ${colorClass} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>


        {/* Processing Volume Over Time */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
              <Activity className="w-4 h-4 text-purple-400" />
              <span>Pipeline Volume & Validation Trends (Last 14 Days)</span>
            </h2>
            <div className="text-xs text-slate-400 font-mono">
              Total 14D Volume: {(timeseries?.data_points || []).reduce((acc, d) => acc + d.processed, 0)} docs
            </div>
          </div>

          {/* Interactive Dual-Series Bar Chart */}
          <div className="h-48 flex items-end justify-between space-x-1.5 pt-8 pb-2 px-2 border-b border-slate-800/80">
            {(() => {
              const pts = timeseries?.data_points || [];
              const maxVal = Math.max(...pts.map((d) => d.processed), 1);

              return pts.map((dp, idx) => {
                const heightPct = dp.processed > 0 ? Math.max(Math.round((dp.processed / maxVal) * 100), 12) : 4;

                return (
                  <div key={idx} className="flex-1 flex flex-col items-center group relative h-full justify-end">
                    {/* Rich Tooltip */}
                    <div className="absolute -top-16 hidden group-hover:flex flex-col items-start bg-slate-900/95 backdrop-blur-md text-[10px] text-slate-200 px-3 py-2 rounded-xl border border-slate-700 shadow-2xl z-30 space-y-0.5 whitespace-nowrap min-w-[120px]">
                      <span className="font-semibold text-slate-300 border-b border-slate-800 pb-0.5 w-full">{dp.date}</span>
                      <div className="flex justify-between w-full space-x-3 pt-0.5">
                        <span className="text-slate-400">Total:</span>
                        <span className="font-bold text-blue-400">{dp.processed}</span>
                      </div>
                      <div className="flex justify-between w-full space-x-3">
                        <span className="text-slate-400">Validated:</span>
                        <span className="font-bold text-emerald-400">{dp.validated}</span>
                      </div>
                      <div className="flex justify-between w-full space-x-3">
                        <span className="text-slate-400">Flagged:</span>
                        <span className="font-bold text-amber-400">{dp.needs_review}</span>
                      </div>
                    </div>

                    {/* Bar visual */}
                    <div
                      className={`w-full max-w-[24px] rounded-t-md transition-all duration-300 relative overflow-hidden ${
                        dp.processed > 0
                          ? 'bg-gradient-to-t from-blue-900/80 to-blue-600/80 group-hover:from-blue-800 group-hover:to-blue-500 shadow-md shadow-blue-900/20'
                          : 'bg-slate-800/40'
                      }`}
                      style={{ height: `${heightPct}%` }}
                    >
                      {dp.processed > 0 && dp.validated > 0 && (
                        <div
                          className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 absolute bottom-0 rounded-t-sm transition-all duration-500"
                          style={{ height: `${Math.round((dp.validated / dp.processed) * 100)}%` }}
                        />
                      )}
                    </div>
                    <span className="text-[9px] text-slate-500 mt-2 font-mono tracking-tighter">
                      {dp.date.slice(5)}
                    </span>
                  </div>
                );
              });
            })()}
          </div>

          <div className="flex items-center justify-end space-x-4 text-[11px] text-slate-400 pt-1">
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block shadow-sm shadow-blue-500/50" />
              <span>Total Volume</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block shadow-sm shadow-emerald-500/50" />
              <span>Validated Clean</span>
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Section: Needs Review Queue Table */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-200 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Needs Manual Review Queue</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Documents flagged for review due to rule failures or low LLM confidence.
            </p>
          </div>

          <Link
            to="/documents"
            className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center space-x-1"
          >
            <span>View All Documents</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {needsReviewDocs.length === 0 ? (
          <div className="p-8 text-center bg-slate-900/40 rounded-xl border border-slate-800/60 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto opacity-80" />
            <p className="text-xs font-semibold text-slate-300">Review Queue Empty!</p>
            <p className="text-[11px] text-slate-500">All uploaded documents have passed validation rules cleanly.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Upload Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {needsReviewDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-900/60 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200 truncate max-w-xs">{doc.filename}</td>
                    <td className="py-3 px-4 uppercase text-[11px] font-mono text-purple-400">{doc.document_type}</td>
                    <td className="py-3 px-4 text-slate-400">{new Date(doc.upload_date).toLocaleDateString()}</td>
                    <td className="py-3 px-4">
                      <ProcessingStatusBadge status={doc.status} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/review/${doc.id}`}
                        className="inline-flex items-center space-x-1 px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded-lg font-medium border border-amber-500/30 transition-colors"
                      >
                        <span>Review Now</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
