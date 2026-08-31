import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Check, Download, Maximize2, Minimize2, FileCode } from 'lucide-react';

interface CodeViewerProps {
  code: string;
  language: string;
  filename: string;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({ code, language, filename }) => {
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleCopy = async () => {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code: ', err);
    }
  };

  const handleDownload = () => {
    if (!code) return;
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const monacoLanguage =
    language === 'typescript' || language === 'ts'
      ? 'typescript'
      : language === 'javascript' || language === 'js'
      ? 'javascript'
      : language === 'go'
      ? 'go'
      : language === 'rust'
      ? 'rust'
      : language === 'csharp' || language === 'cs'
      ? 'csharp'
      : language === 'cpp'
      ? 'cpp'
      : 'python';

  return (
    <div
      className={`flex flex-col border border-white/5 rounded-2xl bg-zinc-950/80 shadow-xl overflow-hidden transition-all duration-300 ${
        isFullscreen
          ? 'fixed inset-4 z-50 bg-zinc-950'
          : 'relative h-[550px]'
      }`}
    >
      {/* Code Header Actions */}
      <div className="flex h-12 items-center justify-between border-b border-white/5 bg-zinc-900/60 px-4">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4 text-primaryPurple" />
          <span className="text-xs font-semibold text-gray-300 font-mono">
            {filename}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            disabled={!code}
            className="flex items-center gap-1.5 rounded-lg border border-white/5 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white hover:bg-white/5 hover:border-white/10 active:scale-[0.98] transition-all disabled:opacity-50"
            title="Copy to Clipboard"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-successGreen" />
                <span className="text-successGreen">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-zinc-400" />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            disabled={!code}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primaryPurple to-secondaryBlue px-3 py-1.5 text-xs font-semibold text-white shadow-md active:scale-[0.98] transition-all disabled:opacity-50"
            title="Download SDK File"
          >
            <Download className="h-3.5 w-3.5 text-white" />
            <span>Download</span>
          </button>

          {/* Fullscreen Button */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/5 bg-zinc-950 text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Monaco Editor Component */}
      <div className="flex-1 w-full relative">
        {code ? (
          <Editor
            height="100%"
            language={monacoLanguage}
            theme="vs-dark"
            value={code}
            options={{
              readOnly: true,
              fontSize: 13,
              minimap: { enabled: false },
              wordWrap: 'on',
              lineNumbers: 'on',
              folding: true,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12, bottom: 12 },
              contextmenu: false,
              renderLineHighlight: 'all',
              fontFamily: "'Fira Code', monospace",
            }}
            loading={
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-950/60 backdrop-blur-sm text-xs text-gray-400">
                <Loader2 className="h-5 w-5 text-primaryPurple animate-spin mr-2" />
                Loading Code Editor...
              </div>
            }
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 bg-zinc-950/20 text-center select-none">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 border border-white/10 mb-4 shadow-lg text-zinc-400">
              <FileCode className="h-6 w-6 text-gray-500" />
            </div>
            <p className="text-sm font-semibold text-gray-300">
              No Wrapper Generated Yet
            </p>
            <p className="text-xs text-gray-500 max-w-sm mt-1.5 leading-relaxed">
              Configure parameters on the left and trigger generation to output client SDK source code.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// Simple loader wrapper for Monaco
const Loader2 = ({ className }: { className?: string }) => (
  <svg
    className={`animate-spin ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);
