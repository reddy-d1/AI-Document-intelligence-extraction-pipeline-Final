import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { FileText, LayoutDashboard, Upload, Layers, Activity, AlertTriangle, RefreshCw } from 'lucide-react';
import { fetchHealthStatus } from '../services/api';

export const Navbar: React.FC = () => {
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const checkConnection = async () => {
    setIsChecking(true);
    try {
      await fetchHealthStatus();
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkConnection();
    const timer = setInterval(checkConnection, 30000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/upload', label: 'Upload & Process', icon: Upload },
    { to: '/documents', label: 'Document Library', icon: Layers },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-xl text-blue-400">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
                  DocIntel AI
                </span>
                {/* Live Backend Connection Status Indicator */}
                {isConnected === true ? (
                  <span
                    className="inline-flex items-center space-x-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 cursor-pointer"
                    title="Backend API operational and reachable"
                    onClick={checkConnection}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>API Connected</span>
                  </span>
                ) : isConnected === false ? (
                  <button
                    onClick={checkConnection}
                    className="inline-flex items-center space-x-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-red-950/80 text-red-300 border border-red-500/30 hover:bg-red-900/60 transition-colors"
                    title="Backend API unreachable. Click to retry connection."
                  >
                    <AlertTriangle className="w-3 h-3 text-red-400" />
                    <span>Backend Offline</span>
                    {isChecking && <RefreshCw className="w-2.5 h-2.5 animate-spin" />}
                  </button>
                ) : (
                  <span className="inline-flex items-center space-x-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                    <Activity className="w-3 h-3 animate-spin text-blue-400" />
                    <span>Checking API...</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          <nav className="flex space-x-1 sm:space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-lg shadow-blue-500/10'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
};

