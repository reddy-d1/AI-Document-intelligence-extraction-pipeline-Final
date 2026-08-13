import React from 'react';
import { Search, Filter } from 'lucide-react';

export const DocumentsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Document Library</h1>
          <p className="text-slate-400 text-sm mt-1">Search, filter, and export extracted documents.</p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search documents..." 
              className="bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 w-64"
            />
          </div>
          <button className="p-2 bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 rounded-lg text-xs flex items-center space-x-1">
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-xs text-slate-400">
          <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-300 font-semibold">
            <tr>
              <th className="p-4">Filename</th>
              <th className="p-4">Type</th>
              <th className="p-4">Status</th>
              <th className="p-4">Upload Date</th>
              <th className="p-4">Confidence</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            <tr>
              <td className="p-4 text-slate-500 italic" colSpan={6}>No documents uploaded yet. Go to Upload to ingest your first file.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
