import React from 'react';
import { Layers, Timer, Search, FileText, Database, Cpu, HardDrive } from 'lucide-react';
import type { PipelineStats } from '../types';

interface StatsSidebarProps {
  stats: PipelineStats;
}

export const StatsSidebar: React.FC<StatsSidebarProps> = ({ stats }) => {
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const statItems = [
    {
      label: 'Pages Crawled',
      value: stats.pagesCrawled,
      icon: <Layers className="h-4 w-4 text-primaryPurple" />,
      color: 'bg-primaryPurple/10 border-primaryPurple/20',
    },
    {
      label: 'Total Chunks',
      value: stats.chunksIndexed,
      icon: <Database className="h-4 w-4 text-secondaryBlue" />,
      color: 'bg-secondaryBlue/10 border-secondaryBlue/20',
    },
    {
      label: 'Embedding Time',
      value: `${(stats.embeddingTimeMs / 1000).toFixed(2)}s`,
      icon: <Timer className="h-4 w-4 text-accentCyan" />,
      color: 'bg-accentCyan/10 border-accentCyan/20',
    },
    {
      label: 'Retrieved Chunks',
      value: stats.retrievedChunksCount,
      icon: <Search className="h-4 w-4 text-successGreen" />,
      color: 'bg-successGreen/10 border-successGreen/20',
    },
    {
      label: 'LLM Token Usage',
      value: stats.llmTokensUsed.toLocaleString(),
      icon: <Cpu className="h-4 w-4 text-warningOrange" />,
      color: 'bg-warningOrange/10 border-warningOrange/20',
    },
    {
      label: 'Generation Time',
      value: `${(stats.generationTimeMs / 1000).toFixed(2)}s`,
      icon: <Timer className="h-4 w-4 text-primaryPurple" />,
      color: 'bg-primaryPurple/10 border-primaryPurple/20',
    },
    {
      label: 'Wrapper File Size',
      value: formatBytes(stats.wrapperSizeBytes),
      icon: <HardDrive className="h-4 w-4 text-white" />,
      color: 'bg-white/5 border-white/10',
    },
  ];

  return (
    <div className="glass-panel rounded-2xl border border-white/5 p-6 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[120px] h-[120px] bg-secondaryBlue/5 rounded-full blur-2xl pointer-events-none" />

      <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
        <FileText className="h-4 w-4 text-secondaryBlue" />
        Pipeline Metrics
      </h3>
      <p className="text-xs text-gray-400 mb-5">
        Real-time statistical logs of current integration run.
      </p>

      <div className="space-y-4">
        {statItems.map((item, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-3 rounded-xl bg-zinc-950 border border-white/5 hover:border-white/10 transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <div className={`p-2 rounded-lg border ${item.color}`}>
                {item.icon}
              </div>
              <span className="text-xs font-medium text-gray-400">
                {item.label}
              </span>
            </div>
            <span className="text-sm font-semibold text-white font-mono">
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
