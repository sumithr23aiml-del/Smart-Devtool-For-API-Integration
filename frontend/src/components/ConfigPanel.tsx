import React, { useState } from 'react';
import { Globe, Terminal, Shield, FileCode, FolderOpen, Play } from 'lucide-react';

interface ConfigPanelProps {
  onSubmit: (config: {
    url: string;
    useCase: string;
    language: string;
    authType: string;
    wrapperStyle: string;
    outputFolder: string;
  }) => void;
  isLoading: boolean;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ onSubmit, isLoading }) => {
  const [url, setUrl] = useState('');
  const [useCase, setUseCase] = useState('');
  const [language, setLanguage] = useState('python');
  const [authType, setAuthType] = useState('auto');
  const [wrapperStyle, setWrapperStyle] = useState('production');
  const [outputFolder, setOutputFolder] = useState('./sdk');
  const [isDragOver, setIsDragOver] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !useCase) return;
    onSubmit({
      url,
      useCase,
      language,
      authType,
      wrapperStyle,
      outputFolder,
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const data = e.dataTransfer.getData('text');
    if (data && data.startsWith('http')) {
      setUrl(data);
    }
  };

  return (
    <div className="glass-panel rounded-2xl border border-white/5 p-6 shadow-xl relative overflow-hidden">
      {/* Visual background gradient reflection */}
      <div className="absolute top-0 right-0 w-[150px] h-[150px] bg-primaryPurple/5 rounded-full blur-2xl pointer-events-none" />

      <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
        <Terminal className="h-5 w-5 text-primaryPurple" />
        Configuration Panel
      </h2>
      <p className="text-xs text-gray-400 mb-6">
        Specify API specifications and generation style.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Documentation URL (Drag & Drop zone combined) */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Globe className="h-3.5 w-3.5 text-accentCyan" />
            Documentation URL
          </label>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative rounded-xl border transition-all duration-200 ${
              isDragOver
                ? 'border-primaryPurple bg-primaryPurple/5 shadow-inner'
                : 'border-white/5 bg-zinc-950 focus-within:border-primaryPurple/50'
            }`}
          >
            <input
              type="url"
              required
              placeholder="https://api.docs.example.com/reference"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full bg-transparent px-4 py-3 text-sm text-white placeholder-gray-500 border-none outline-none focus:ring-0"
            />
            {isDragOver && (
              <div className="absolute inset-0 flex items-center justify-center bg-primaryPurple/10 rounded-xl pointer-events-none">
                <span className="text-xs font-medium text-primaryPurple animate-pulse">
                  Drop link here
                </span>
              </div>
            )}
          </div>
          <span className="text-[10px] text-gray-500 block">
            Supports drag-and-drop link ingestion.
          </span>
        </div>

        {/* Use Case */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-gray-300">
            Use Case Description
          </label>
          <textarea
            required
            rows={3}
            placeholder="e.g., Build a client that manages payment checkout runs, listens to webhooks, and refunds orders."
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            className="w-full rounded-xl border border-white/5 bg-zinc-950 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-primaryPurple/50 focus:outline-none transition-colors"
          />
        </div>

        {/* 2-column Grid for selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Target Language */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <FileCode className="h-3.5 w-3.5 text-secondaryBlue" />
              Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-zinc-950 px-3 py-2.5 text-sm text-white focus:border-primaryPurple/50 focus:outline-none transition-colors cursor-pointer"
            >
              <option value="python">Python</option>
              <option value="typescript">TypeScript</option>
              <option value="javascript">JavaScript</option>
              <option value="go">Go</option>
              <option value="rust">Rust</option>
              <option value="csharp">C#</option>
              <option value="cpp">C++</option>
              <option value="php">PHP</option>
              <option value="ruby">Ruby</option>
              <option value="swift">Swift</option>
            </select>
          </div>

          {/* Authentication Type */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-accentCyan" />
              Authentication
            </label>
            <select
              value={authType}
              onChange={(e) => setAuthType(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-zinc-950 px-3 py-2.5 text-sm text-white focus:border-primaryPurple/50 focus:outline-none transition-colors cursor-pointer"
            >
              <option value="auto">Auto Detect</option>
              <option value="bearer">Bearer Token</option>
              <option value="api_key">API Key</option>
              <option value="oauth2">OAuth 2.0</option>
              <option value="basic">Basic Auth</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Wrapper Style */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <FileCode className="h-3.5 w-3.5 text-primaryPurple" />
              Style Pattern
            </label>
            <select
              value={wrapperStyle}
              onChange={(e) => setWrapperStyle(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-zinc-950 px-3 py-2.5 text-sm text-white focus:border-primaryPurple/50 focus:outline-none transition-colors cursor-pointer"
            >
              <option value="minimal">Minimal</option>
              <option value="production">Production</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          {/* Output Folder */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
              <FolderOpen className="h-3.5 w-3.5 text-secondaryBlue" />
              Output Path
            </label>
            <input
              type="text"
              value={outputFolder}
              onChange={(e) => setOutputFolder(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-zinc-950 px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:border-primaryPurple/50 focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Generate Button */}
        <button
          type="submit"
          disabled={isLoading || !url || !useCase}
          className="w-full relative group mt-3 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-white font-semibold text-sm bg-gradient-to-r from-primaryPurple via-secondaryBlue to-accentCyan shadow-lg shadow-primaryPurple/25 hover:shadow-primaryPurple/45 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
        >
          <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          {isLoading ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
              Orchestrating Pipeline...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-white" />
              Generate SDK Client
            </>
          )}
        </button>
      </form>
    </div>
  );
};
