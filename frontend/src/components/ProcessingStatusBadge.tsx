import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertOctagon, 
  Clock, 
  Loader2, 
  FileSearch, 
  Cpu, 
  Layers 
} from 'lucide-react';
import { DocumentStatus } from '../types';

interface ProcessingStatusBadgeProps {
  status: DocumentStatus | string;
  className?: string;
}

export const ProcessingStatusBadge: React.FC<ProcessingStatusBadgeProps> = ({ status, className = '' }) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'uploaded':
        return {
          label: 'Uploaded',
          bg: 'bg-slate-900/80 text-slate-300 border-slate-700',
          icon: Clock,
          animate: false,
        };
      case 'processing':
      case 'preprocessed':
        return {
          label: 'Preprocessing',
          bg: 'bg-blue-950/60 text-blue-400 border-blue-500/30',
          icon: Loader2,
          animate: true,
        };
      case 'ocr_complete':
        return {
          label: 'OCR Complete',
          bg: 'bg-indigo-950/60 text-indigo-400 border-indigo-500/30',
          icon: FileSearch,
          animate: false,
        };
      case 'classified':
        return {
          label: 'Classified',
          bg: 'bg-purple-950/60 text-purple-400 border-purple-500/30',
          icon: Cpu,
          animate: false,
        };
      case 'extracted':
        return {
          label: 'Extracted',
          bg: 'bg-cyan-950/60 text-cyan-400 border-cyan-500/30',
          icon: Layers,
          animate: false,
        };
      case 'validated':
        return {
          label: 'Validated',
          bg: 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30',
          icon: CheckCircle2,
          animate: false,
        };
      case 'needs_review':
        return {
          label: 'Needs Review',
          bg: 'bg-amber-950/60 text-amber-400 border-amber-500/30',
          icon: AlertTriangle,
          animate: false,
        };
      case 'failed':
        return {
          label: 'Failed',
          bg: 'bg-red-950/60 text-red-400 border-red-500/30',
          icon: AlertOctagon,
          animate: false,
        };
      default:
        return {
          label: status,
          bg: 'bg-slate-800 text-slate-400 border-slate-700',
          icon: Clock,
          animate: false,
        };
    }
  };

  const config = getBadgeConfig();
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${config.bg} ${className}`}
    >
      <Icon className={`w-3.5 h-3.5 ${config.animate ? 'animate-spin' : ''}`} />
      <span>{config.label}</span>
    </span>
  );
};
