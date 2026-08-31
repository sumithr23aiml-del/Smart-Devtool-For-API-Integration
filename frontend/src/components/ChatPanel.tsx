import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, MessageSquare, Bot, User, CornerDownLeft } from 'lucide-react';
import type { ChatMessage } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onSendMessage, isStreaming }) => {
  const [input, setInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleChipClick = (prompt: string) => {
    if (isStreaming) return;
    onSendMessage(prompt);
  };

  // Helper to highlight markdown formatting (bold, inline-code, code-blocks) safely
  const formatMessageText = (text: string) => {
    // HTML Escape
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Fenced Code Blocks (```lang ... ```)
    escaped = escaped.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
      return `
        <div class="my-3 border border-white/5 rounded-xl bg-zinc-950 overflow-hidden font-mono text-xs">
          <div class="flex items-center justify-between px-4 py-1.5 bg-zinc-900 border-b border-white/5 text-[10px] text-zinc-500 font-bold uppercase select-none">
            <span>${lang || 'code'}</span>
          </div>
          <pre class="p-3.5 overflow-x-auto text-zinc-300"><code>${code.trim()}</code></pre>
        </div>
      `;
    });

    // Inline Code (`code`)
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="bg-zinc-950 border border-white/5 px-1 py-0.5 rounded font-mono text-[11px] text-primaryPurple font-semibold">$1</code>');

    // Bold (**text**)
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-white">$1</strong>');

    // Newlines to breaks (ignoring breaks inside generated code structures)
    const segments = escaped.split(/(<div[\s\S]*?<\/div>)/g);
    const finalHtml = segments
      .map((seg, idx) => {
        if (idx % 2 === 1) return seg; // Inside container
        return seg.replace(/\n/g, '<br />');
      })
      .join('');

    return <div dangerouslySetInnerHTML={{ __html: finalHtml }} />;
  };

  const chips = [
    { label: 'Explain Auth', prompt: 'Explain the authentication mechanism of this API and how it is implemented in the wrapper.' },
    { label: 'Show Usage', prompt: 'Provide a complete code snippet showing how to initialize and run this generated SDK client.' },
    { label: 'Optimize Client', prompt: 'Suggest potential optimizations or retry handlers to make this wrapper client enterprise-ready.' },
  ];

  return (
    <div className="flex flex-col border border-white/5 rounded-2xl bg-zinc-950/60 shadow-xl overflow-hidden h-[550px]">
      {/* Chat Header */}
      <div className="flex h-12 items-center justify-between border-b border-white/5 bg-zinc-900/60 px-4">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-primaryPurple animate-pulse" />
          <span className="text-xs font-semibold text-gray-300 font-sans">
            AI Helper Assistant
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-medium text-accentCyan border border-accentCyan/20 bg-accentCyan/5 px-2 py-0.5 rounded-full">
          <Sparkles className="h-3 w-3" />
          RAG Context Enabled
        </div>
      </div>

      {/* Messages Scroll Panel */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 select-none">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 border border-white/10 mb-4 shadow-lg text-zinc-400">
              <Bot className="h-6 w-6 text-primaryPurple" />
            </div>
            <p className="text-sm font-semibold text-gray-300">
              Ask Smart DevTool Assistant
            </p>
            <p className="text-xs text-gray-500 max-w-xs mt-1.5 leading-relaxed">
              I have direct context on the crawled documentation. Ask me to write implementation examples, clarify routes, or review auth parameters.
            </p>
          </div>
        ) : (
          messages.map((m, idx) => {
            const isBot = m.role === 'assistant';
            return (
              <div
                key={idx}
                className={`flex gap-3 max-w-[85%] ${
                  isBot ? 'mr-auto' : 'ml-auto flex-row-reverse'
                }`}
              >
                {/* Bubble Avatar */}
                <div
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-xs select-none shadow-sm ${
                    isBot
                      ? 'bg-primaryPurple/10 border-primaryPurple/20 text-primaryPurple'
                      : 'bg-zinc-900 border-white/5 text-zinc-300'
                  }`}
                >
                  {isBot ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
                </div>

                {/* Bubble Box */}
                <div
                  className={`rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                    isBot
                      ? 'bg-zinc-900/60 border border-white/5 text-gray-300'
                      : 'bg-primaryPurple text-white shadow-md shadow-primaryPurple/15'
                  }`}
                >
                  {isBot && m.content === '' && isStreaming ? (
                    <span className="streaming-cursor"></span>
                  ) : (
                    <>
                      {formatMessageText(m.content)}
                      {isBot && isStreaming && idx === messages.length - 1 && (
                        <span className="streaming-cursor inline-block ml-0.5" />
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggestions and Form Input area */}
      <div className="border-t border-white/5 p-3.5 bg-zinc-900/40 space-y-3">
        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-2">
          {chips.map((chip, idx) => (
            <button
              key={idx}
              disabled={isStreaming}
              onClick={() => handleChipClick(chip.prompt)}
              className="text-[10px] font-semibold text-zinc-400 bg-zinc-950 border border-white/5 hover:text-white hover:border-white/10 px-2.5 py-1 rounded-lg active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              disabled={isStreaming}
              placeholder="Ask helper (e.g. explain the endpoints)..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="w-full rounded-xl border border-white/5 bg-zinc-950 pl-4 pr-12 py-3 text-xs text-white placeholder-gray-500 focus:border-primaryPurple/50 focus:outline-none transition-colors disabled:opacity-50"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[9px] font-mono text-zinc-600 select-none">
              <span>Enter</span>
              <CornerDownLeft className="h-3 w-3" />
            </div>
          </div>

          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-primaryPurple to-secondaryBlue text-white shadow-md active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
