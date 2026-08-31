import React from 'react';
import { Database, Cpu, Network, Layers, GitPullRequest } from 'lucide-react';

export const ArchDiagram: React.FC = () => {
  return (
    <div className="glass-panel rounded-2xl border border-white/5 p-6 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 left-0 w-[150px] h-[150px] bg-primaryPurple/5 rounded-full blur-2xl pointer-events-none" />

      <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
        <Network className="h-4 w-4 text-accentCyan" />
        System Architecture Workflow
      </h3>
      <p className="text-xs text-gray-400 mb-8">
        Visual diagram tracing documentation scraping down to client wrapper generation.
      </p>

      {/* SVG Pipeline Diagram */}
      <div className="w-full overflow-x-auto pb-4">
        <div className="min-w-[850px] flex items-center justify-between gap-2 py-4 px-2">
          {/* User Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[90px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-white shadow-lg">
              <span className="text-sm font-bold">👤</span>
            </div>
            <span className="text-[10px] font-semibold text-gray-300">User Prompt</span>
          </div>

          {/* Arrow 1 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-1)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#7C3AED" />
              <defs>
                <linearGradient id="line-grad-1" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#7C3AED" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Crawler Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[95px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-primaryPurple/10 border border-primaryPurple/20 text-primaryPurple shadow-lg shadow-primaryPurple/5">
              <span className="text-sm">🕸️</span>
            </div>
            <span className="text-[10px] font-semibold text-gray-300">1. Crawler</span>
          </div>

          {/* Arrow 2 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-2)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#3B82F6" />
              <defs>
                <linearGradient id="line-grad-2" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7C3AED" />
                  <stop offset="100%" stopColor="#3B82F6" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Cleaner Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[95px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-secondaryBlue/10 border border-secondaryBlue/20 text-secondaryBlue shadow-lg shadow-secondaryBlue/5">
              <span className="text-sm">🧹</span>
            </div>
            <span className="text-[10px] font-semibold text-gray-300">2. HTML Clean</span>
          </div>

          {/* Arrow 3 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-3)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#06B6D4" />
              <defs>
                <linearGradient id="line-grad-3" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#3B82F6" />
                  <stop offset="100%" stopColor="#06B6D4" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Chunker Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[95px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-accentCyan/10 border border-accentCyan/20 text-accentCyan shadow-lg shadow-accentCyan/5">
              <Layers className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-semibold text-gray-300">3. Chunker</span>
          </div>

          {/* Arrow 4 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-4)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#22C55E" />
              <defs>
                <linearGradient id="line-grad-4" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#06B6D4" />
                  <stop offset="100%" stopColor="#22C55E" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* ChromaDB Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[100px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-successGreen/10 border border-successGreen/20 text-successGreen shadow-lg shadow-successGreen/5">
              <Database className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-semibold text-gray-300 text-center">4. ChromaDB</span>
          </div>

          {/* Arrow 5 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-5)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#F59E0B" />
              <defs>
                <linearGradient id="line-grad-5" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#22C55E" />
                  <stop offset="100%" stopColor="#F59E0B" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Retriever Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[95px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-warningOrange/10 border border-warningOrange/20 text-warningOrange shadow-lg shadow-warningOrange/5">
              <span className="text-sm">🔍</span>
            </div>
            <span className="text-[10px] font-semibold text-gray-300">5. Retriever</span>
          </div>

          {/* Arrow 6 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-6)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#7C3AED" />
              <defs>
                <linearGradient id="line-grad-6" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#F59E0B" />
                  <stop offset="100%" stopColor="#7C3AED" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* LLM Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[95px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-primaryPurple/10 border border-primaryPurple/20 text-primaryPurple shadow-lg shadow-primaryPurple/5">
              <Cpu className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-semibold text-gray-300">6. LLM Agent</span>
          </div>

          {/* Arrow 7 */}
          <div className="flex-1 flex items-center justify-center">
            <svg className="w-full h-6" viewBox="0 0 100 24" fill="none">
              <path d="M0 12H90" stroke="url(#line-grad-7)" strokeWidth="2" strokeDasharray="4,4" className="animate-[dash_15s_linear_infinite]" />
              <polygon points="90,7 100,12 90,17" fill="#06B6D4" />
              <defs>
                <linearGradient id="line-grad-7" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7C3AED" />
                  <stop offset="100%" stopColor="#06B6D4" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          {/* Wrapper SDK Node */}
          <div className="flex flex-col items-center gap-2 flex-1 max-w-[100px]">
            <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-gradient-to-tr from-accentCyan to-successGreen text-white shadow-lg shadow-accentCyan/20">
              <GitPullRequest className="h-5 w-5" />
            </div>
            <span className="text-[10px] font-semibold text-white text-center">SDK Wrapper</span>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -100;
          }
        }
      `}</style>
    </div>
  );
};
