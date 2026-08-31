import React, { useState, useMemo } from 'react';
import { Search, Copy, Check, Info, Server, Shield, Layers } from 'lucide-react';
import type { ExtractedSchema } from '../types';

interface SchemaViewerProps {
  schema: ExtractedSchema | null;
}

export const SchemaViewer: React.FC<SchemaViewerProps> = ({ schema }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState<'endpoints' | 'json'>('endpoints');
  const [collapsedNodes, setCollapsedNodes] = useState<Record<string, boolean>>({});

  const handleCopy = async () => {
    if (!schema) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(schema, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy schema: ', err);
    }
  };

  const filteredEndpoints = useMemo(() => {
    if (!schema || !schema.endpoints) return [];
    if (!searchQuery) return schema.endpoints;
    const query = searchQuery.toLowerCase();
    return schema.endpoints.filter(
      (ep) =>
        ep.path.toLowerCase().includes(query) ||
        ep.method.toLowerCase().includes(query) ||
        (ep.description && ep.description.toLowerCase().includes(query))
    );
  }, [schema, searchQuery]);

  const toggleNode = (nodePath: string) => {
    setCollapsedNodes((prev) => ({
      ...prev,
      [nodePath]: !prev[nodePath],
    }));
  };

  const renderJsonNode = (node: any, path = 'root', depth = 0): React.ReactNode => {
    if (node === null) return <span className="text-zinc-500">null</span>;
    if (typeof node === 'undefined') return <span className="text-zinc-500">undefined</span>;

    if (typeof node === 'string') {
      return <span className="text-successGreen">"{node}"</span>;
    }
    if (typeof node === 'number') {
      return <span className="text-amber-500">{node}</span>;
    }
    if (typeof node === 'boolean') {
      return <span className="text-secondaryBlue">{node ? 'true' : 'false'}</span>;
    }

    const isArray = Array.isArray(node);
    const keys = isArray ? node.map((_, i) => i.toString()) : Object.keys(node);
    const isCollapsed = collapsedNodes[path] || false;

    if (keys.length === 0) {
      return isArray ? <span>[]</span> : <span>{"{}"}</span>;
    }

    return (
      <div className="pl-4 font-mono text-xs">
        <span
          onClick={() => toggleNode(path)}
          className="cursor-pointer select-none text-zinc-500 hover:text-zinc-300 font-bold"
        >
          {isCollapsed ? '▶' : '▼'} {isArray ? '[' : '{'}
          <span className="text-[10px] text-zinc-600 bg-zinc-950 px-1 py-0.5 rounded border border-white/5 ml-1">
            {keys.length} items
          </span>
        </span>

        {!isCollapsed && (
          <div className="border-l border-white/5 pl-4 py-1 space-y-1">
            {keys.map((key) => {
              const childNode = node[isArray ? parseInt(key) : key];
              const childPath = `${path}.${key}`;
              return (
                <div key={key} className="flex items-start gap-1">
                  {!isArray && (
                    <span className="text-zinc-400 font-semibold select-none">
                      "{key}":
                    </span>
                  )}
                  {renderJsonNode(childNode, childPath, depth + 1)}
                </div>
              );
            })}
          </div>
        )}

        <div className="text-zinc-500 font-bold">
          {isArray ? ']' : '}'}
        </div>
      </div>
    );
  };

  const getMethodBadgeClass = (method: string): string => {
    const m = method.toUpperCase();
    if (m === 'GET') return 'bg-successGreen/10 border-successGreen/20 text-successGreen';
    if (m === 'POST') return 'bg-secondaryBlue/10 border-secondaryBlue/20 text-secondaryBlue';
    if (m === 'PUT') return 'bg-warningOrange/10 border-warningOrange/20 text-warningOrange';
    if (m === 'DELETE') return 'bg-errorRed/10 border-errorRed/20 text-errorRed';
    return 'bg-white/5 border-white/10 text-white';
  };

  if (!schema) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-zinc-950/20 text-center rounded-2xl border border-white/5 h-[450px]">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 border border-white/10 mb-4 shadow-lg text-zinc-400">
          <Layers className="h-6 w-6 text-gray-500" />
        </div>
        <p className="text-sm font-semibold text-gray-300">
          No Schema Details Available
        </p>
        <p className="text-xs text-gray-500 max-w-sm mt-1.5 leading-relaxed">
          The extracted API routes, query schemas, and payload parameters will populate here once the wrapper client compiler completes.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col border border-white/5 rounded-2xl bg-zinc-950/80 shadow-xl overflow-hidden h-[550px]">
      {/* Viewer Header */}
      <div className="flex h-12 items-center justify-between border-b border-white/5 bg-zinc-900/60 px-4">
        {/* Toggle between Tree Mode and list view */}
        <div className="flex h-8 items-center rounded-lg bg-zinc-950 border border-white/5 p-0.5">
          <button
            onClick={() => setViewMode('endpoints')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
              viewMode === 'endpoints'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Endpoints List
          </button>
          <button
            onClick={() => setViewMode('json')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
              viewMode === 'json'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            JSON Document
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {viewMode === 'endpoints' && (
            <div className="relative flex items-center">
              <Search className="absolute left-2.5 h-3.5 w-3.5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search schema..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-[180px] sm:w-[240px] rounded-lg border border-white/5 bg-zinc-950 pl-8 pr-3 py-1 text-xs text-white placeholder-gray-500 focus:border-primaryPurple/50 focus:outline-none transition-colors"
              />
            </div>
          )}
          
          <button
            onClick={handleCopy}
            className="flex h-8 items-center gap-1.5 rounded-lg border border-white/5 bg-zinc-950 px-3 text-xs font-medium text-gray-300 hover:text-white hover:bg-white/5 hover:border-white/10 active:scale-[0.98] transition-all"
            title="Copy entire schema payload"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-successGreen" />
                <span className="text-successGreen">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-zinc-400" />
                <span>Copy JSON</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content scroll area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {viewMode === 'endpoints' ? (
          <>
            {/* API Metadata Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              <div className="p-3 bg-zinc-900/40 border border-white/5 rounded-xl flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primaryPurple/10 border border-primaryPurple/20 text-primaryPurple">
                  <Info className="h-4 w-4" />
                </div>
                <div className="overflow-hidden">
                  <span className="text-[10px] text-zinc-500 uppercase font-bold block">
                    API Name
                  </span>
                  <span className="text-xs font-semibold text-white truncate block">
                    {schema.api_name || 'N/A'}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-zinc-900/40 border border-white/5 rounded-xl flex items-center gap-3">
                <div className="p-2 rounded-lg bg-secondaryBlue/10 border border-secondaryBlue/20 text-secondaryBlue">
                  <Server className="h-4 w-4" />
                </div>
                <div className="overflow-hidden">
                  <span className="text-[10px] text-zinc-500 uppercase font-bold block">
                    Base URL
                  </span>
                  <span className="text-xs font-semibold text-white truncate block" title={schema.base_url}>
                    {schema.base_url || 'N/A'}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-zinc-900/40 border border-white/5 rounded-xl flex items-center gap-3">
                <div className="p-2 rounded-lg bg-accentCyan/10 border border-accentCyan/20 text-accentCyan">
                  <Shield className="h-4 w-4" />
                </div>
                <div className="overflow-hidden">
                  <span className="text-[10px] text-zinc-500 uppercase font-bold block">
                    Authentication
                  </span>
                  <span className="text-xs font-semibold text-white truncate block">
                    {schema.authentication?.type?.toUpperCase() || 'NONE'}
                  </span>
                </div>
              </div>
            </div>

            {/* Endpoints List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider pl-1">
                Extracted Endpoints ({filteredEndpoints.length})
              </h4>
              
              {filteredEndpoints.length > 0 ? (
                filteredEndpoints.map((ep, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 bg-zinc-900/30 border border-white/5 hover:border-white/10 hover:bg-zinc-900/50 rounded-xl space-y-2 transition-all"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getMethodBadgeClass(ep.method)}`}>
                          {ep.method.toUpperCase()}
                        </span>
                        <span className="text-xs font-mono font-semibold text-white tracking-wide">
                          {ep.path}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-500 font-medium font-sans">
                        Target endpoint {idx + 1}
                      </span>
                    </div>

                    {ep.description && (
                      <p className="text-xs text-zinc-400 leading-relaxed pl-1">
                        {ep.description}
                      </p>
                    )}

                    {/* Parameter rendering */}
                    {ep.parameters && ep.parameters.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-white/5 space-y-1">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase pl-1 block">
                          Parameters:
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-1">
                          {ep.parameters.map((param, pIdx) => (
                            <div
                              key={pIdx}
                              className="text-[10px] flex items-center justify-between p-1.5 bg-zinc-950 border border-white/5 rounded"
                            >
                              <span className="font-mono text-zinc-300">
                                {param.name}
                                {param.required && <span className="text-errorRed ml-0.5">*</span>}
                              </span>
                              <span className="text-zinc-500">
                                {param.type} ({param.location})
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-10 bg-zinc-900/10 border border-dashed border-white/5 rounded-xl">
                  <span className="text-xs text-zinc-500">
                    No endpoints match your query.
                  </span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-3 bg-zinc-950 border border-white/5 rounded-xl h-full overflow-auto">
            {renderJsonNode(schema)}
          </div>
        )}
      </div>
    </div>
  );
};
