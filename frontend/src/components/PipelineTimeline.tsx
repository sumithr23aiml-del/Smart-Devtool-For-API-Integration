import React from 'react';
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

export interface PipelineStep {
  id: number;
  name: string;
  description: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  timeTaken?: string;
}

interface PipelineTimelineProps {
  steps: PipelineStep[];
}

export const PipelineTimeline: React.FC<PipelineTimelineProps> = ({ steps }) => {
  return (
    <div className="glass-panel rounded-2xl border border-white/5 p-6 shadow-xl relative overflow-hidden h-full">
      <div className="absolute top-0 right-0 w-[120px] h-[120px] bg-accentCyan/5 rounded-full blur-2xl pointer-events-none" />
      
      <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-primaryPurple animate-ping" />
        Pipeline Visualizer
      </h3>
      <p className="text-xs text-gray-400 mb-6">
        Step-by-step progress tracking of the AI generation workflow.
      </p>

      <div className="relative pl-6 space-y-6">
        {/* Vertical Timeline Bar */}
        <div className="absolute left-[13px] top-2 bottom-2 w-[1px] bg-white/10" />

        {steps.map((step) => {
          const isCompleted = step.status === 'completed';
          const isRunning = step.status === 'running';
          const isFailed = step.status === 'failed';

          return (
            <div key={step.id} className="relative flex gap-4 text-left group">
              {/* Bullet Node Icon */}
              <div className="absolute -left-[23px] top-0.5 bg-darkBg z-10 rounded-full">
                {isCompleted && (
                  <CheckCircle2 className="h-[18px] w-[18px] text-successGreen bg-darkBg fill-successGreen/10" />
                )}
                {isFailed && (
                  <XCircle className="h-[18px] w-[18px] text-errorRed bg-darkBg fill-errorRed/10" />
                )}
                {isRunning && (
                  <div className="relative h-[18px] w-[18px] flex items-center justify-center bg-darkBg">
                    <Loader2 className="h-4 w-4 text-primaryPurple animate-spin" />
                  </div>
                )}
                {!isCompleted && !isRunning && !isFailed && (
                  <Circle className="h-[18px] w-[18px] text-gray-600 bg-darkBg fill-transparent" />
                )}
              </div>

              {/* Step Info */}
              <div className="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 p-3 rounded-xl bg-zinc-950/40 border border-white/0 hover:border-white/5 hover:bg-zinc-950/70 transition-all duration-200">
                <div>
                  <h4
                    className={`text-xs font-semibold tracking-wide uppercase transition-colors duration-200 ${
                      isRunning
                        ? 'text-primaryPurple'
                        : isCompleted
                        ? 'text-successGreen'
                        : isFailed
                        ? 'text-errorRed'
                        : 'text-gray-400'
                    }`}
                  >
                    {step.name}
                  </h4>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {step.description}
                  </p>
                </div>

                {/* Progress / Time Badge */}
                <div className="flex items-center gap-2 text-right">
                  {isRunning && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-primaryPurple/10 border border-primaryPurple/20 text-primaryPurple font-mono font-bold">
                      {step.progress}%
                    </span>
                  )}
                  {isCompleted && step.timeTaken && (
                    <span className="text-[10px] text-gray-400 font-mono">
                      {step.timeTaken}
                    </span>
                  )}
                  {isFailed && (
                    <span className="text-[10px] text-errorRed font-semibold uppercase">
                      Error
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
