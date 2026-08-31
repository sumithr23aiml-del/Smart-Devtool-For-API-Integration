import React, { useEffect, useRef } from 'react';
import { Terminal, Trash2 } from 'lucide-react';

export interface LogLine {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'system';
  message: string;
}

interface TerminalLogsProps {
  logs: LogLine[];
  onClear: () => void;
}

export const TerminalLogs: React.FC<TerminalLogsProps> = ({ logs, onClear }) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const getLogColorClass = (type: LogLine['type']): string => {
    switch (type) {
      case 'success':
        return 'text-successGreen';
      case 'error':
        return 'text-errorRed';
      case 'warning':
        return 'text-warningOrange';
      case 'info':
        return 'text-accentCyan';
      case 'system':
      default:
        return 'text-zinc-300';
    }
  };

  return (
    <div className="flex flex-col border border-white/5 rounded-2xl bg-black shadow-xl overflow-hidden h-[550px]">
      {/* Terminal Header */}
      <div className="flex h-12 items-center justify-between border-b border-white/5 bg-zinc-900/60 px-4">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-successGreen" />
          <span className="text-xs font-semibold text-gray-300 font-sans">
            Build Execution Console
          </span>
        </div>
        
        <button
          onClick={onClear}
          className="p-1.5 rounded-lg border border-white/5 bg-zinc-950 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
          title="Clear Logs"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Terminal Screen */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed space-y-1.5 bg-black select-text">
        <div className="text-zinc-500 italic mb-2">
          ⚡ Smart DevTool Engine Console v0.1.0 started.
        </div>

        {logs.map((log, idx) => (
          <div key={idx} className="flex items-start gap-1">
            <span className="text-zinc-600 select-none">
              [{log.timestamp}]
            </span>
            <span className="text-primaryPurple select-none font-bold">
              $
            </span>
            <span className={getLogColorClass(log.type)}>
              {log.message}
            </span>
          </div>
        ))}

        {/* Anchor for Auto Scroll */}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};
