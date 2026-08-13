import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, ChevronLeft, ChevronRight, FileText } from 'lucide-react';

interface DocumentViewerProps {
  documentId: string;
  pageCount: number;
  selectedBox?: { x: number; y: number; w: number; h: number } | null;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  pageCount = 1,
  selectedBox,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [imgError, setImgError] = useState(false);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const handleNextPage = () => {
    if (currentPage < pageCount) setCurrentPage((prev) => prev + 1);
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 200));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50));
  const handleResetZoom = () => setZoom(100);

  // Storage path for preprocessed page images
  const pageImgUrl = `/api/v1/documents/${documentId}/image?page=${currentPage}`;

  return (
    <div className="glass-panel rounded-2xl flex flex-col h-full overflow-hidden border border-slate-800">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 text-xs">
        <div className="flex items-center space-x-2 text-slate-300">
          <FileText className="w-4 h-4 text-blue-400" />
          <span className="font-semibold">Document Preview</span>
        </div>

        {/* Page Navigation */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 rounded hover:bg-slate-800 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-slate-300 font-medium px-2">
            Page {currentPage} of {pageCount || 1}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= pageCount}
            className="p-1 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 rounded hover:bg-slate-800 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-1">
          <button
            onClick={handleZoomOut}
            className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-slate-400 font-mono text-[11px] w-12 text-center">{zoom}%</span>
          <button
            onClick={handleZoomIn}
            className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
            title="Fit Width"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Viewport Canvas Container */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-slate-950/80 relative">
        {!imgError ? (
          <div className="relative inline-block transition-transform duration-200 origin-top" style={{ transform: `scale(${zoom / 100})` }}>
            <img
              src={pageImgUrl}
              alt={`Document Page ${currentPage}`}
              onError={() => setImgError(true)}
              className="max-w-full h-auto rounded-lg shadow-2xl border border-slate-800"
            />

            {/* Interactive Bounding Box Highlight Overlay */}
            {selectedBox && (
              <div
                className="absolute border-2 border-blue-400 bg-blue-500/20 rounded transition-all duration-200 animate-pulse pointer-events-none"
                style={{
                  left: `${selectedBox.x}px`,
                  top: `${selectedBox.y}px`,
                  width: `${selectedBox.w}px`,
                  height: `${selectedBox.h}px`,
                }}
              />
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center space-y-3 p-8">
            <div className="p-4 rounded-full bg-slate-900 text-slate-500 border border-slate-800">
              <FileText className="w-10 h-10" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-300">Document Image Page {currentPage}</p>
              <p className="text-xs text-slate-500 mt-1">Processed page image stored under `/storage/{documentId}/processed/`</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
