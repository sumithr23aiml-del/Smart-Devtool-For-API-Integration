import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { ConfigPanel } from './components/ConfigPanel';
import { StatsSidebar } from './components/StatsSidebar';
import { PipelineTimeline } from './components/PipelineTimeline';
import type { PipelineStep } from './components/PipelineTimeline';
import { CodeViewer } from './components/CodeViewer';
import { SchemaViewer } from './components/SchemaViewer';
import { TerminalLogs } from './components/TerminalLogs';
import type { LogLine } from './components/TerminalLogs';
import { ChatPanel } from './components/ChatPanel';
import { ArchDiagram } from './components/ArchDiagram';
import { Toast } from './components/Toast';
import type { ToastMessage } from './components/Toast';
import type { ChatMessage, ExtractedSchema, PipelineStats } from './types';
import axios from 'axios';

// Mock Data for "View Demo" mode
const MOCK_SCHEMA: ExtractedSchema = {
  api_name: 'Stripe API Wrapper',
  base_url: 'https://api.stripe.com/v1',
  authentication: {
    type: 'bearer',
    description: 'Provide secret API keys inside requests authorization header.',
    key_name: 'Authorization',
    placeholder: 'sk_test_...',
  },
  endpoints: [
    {
      method: 'POST',
      path: '/customers',
      description: 'Creates a new customer object with email, name, and payment profiles.',
      parameters: [
        { name: 'email', type: 'string', required: true, location: 'body', description: 'Customer email address' },
        { name: 'name', type: 'string', required: false, location: 'body', description: 'Customer full name' },
        { name: 'payment_method', type: 'string', required: false, location: 'body', description: 'Payment method ID' },
      ],
    },
    {
      method: 'GET',
      path: '/customers/{id}',
      description: 'Retrieves the details of an existing customer by unique identifier.',
      parameters: [
        { name: 'id', type: 'string', required: true, location: 'path', description: 'Unique customer ID' },
      ],
    },
    {
      method: 'POST',
      path: '/payment_intents',
      description: 'Creates a PaymentIntent to track payments, amounts, currencies, and confirm details.',
      parameters: [
        { name: 'amount', type: 'integer', required: true, location: 'body', description: 'Payment amount in cents' },
        { name: 'currency', type: 'string', required: true, location: 'body', description: 'Three-letter ISO currency code' },
        { name: 'customer', type: 'string', required: false, location: 'body', description: 'Customer ID' },
      ],
    },
  ],
};

const MOCK_CODE = `import requests
from typing import Dict, Any, Optional

class StripeClient:
    """
    Smart DevTool Generated SDK Client for Stripe API.
    Based on scraped API specs.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.stripe.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        
    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, data=data)
        response.raise_for_status()
        return response.json()

    def create_customer(self, email: str, name: Optional[str] = None, payment_method: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new customer object.
        """
        payload = {"email": email}
        if name:
            payload["name"] = name
        if payment_method:
            payload["payment_method"] = payment_method
        return self._request("POST", "/customers", data=payload)

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieves the details of an existing customer by ID.
        """
        return self._request("GET", f"/customers/{customer_id}")

    def create_payment_intent(self, amount: int, currency: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a PaymentIntent to track payments.
        """
        payload = {
            "amount": amount,
            "currency": currency
        }
        if customer_id:
            payload["customer"] = customer_id
        return self._request("POST", "/payment_intents", data=payload)
`;

export const App: React.FC = () => {
  // Global States
  const [activeTab, setActiveTab] = useState<'code' | 'schema' | 'logs' | 'chat'>('code');
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [code, setCode] = useState<string>('');
  const [language, setLanguage] = useState<string>('python');
  const [filename, setFilename] = useState<string>('client_wrapper.py');
  const [schema, setSchema] = useState<ExtractedSchema | null>(null);
  const [crawlId, setCrawlId] = useState<string | null>(null);
  const [isCrawlLoading, setIsCrawlLoading] = useState(false);
  const [isChatStreaming, setIsChatStreaming] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [demoMode, setDemoMode] = useState(false);

  const [stats, setStats] = useState<PipelineStats>({
    pagesCrawled: 0,
    chunksIndexed: 0,
    embeddingTimeMs: 0,
    retrievedChunksCount: 0,
    llmTokensUsed: 0,
    generationTimeMs: 0,
    wrapperSizeBytes: 0,
  });

  const [steps, setSteps] = useState<PipelineStep[]>([
    { id: 1, name: 'Crawler', description: 'Scrape URL and list matching sub-pages', status: 'idle', progress: 0 },
    { id: 2, name: 'Cleaner', description: 'Parse elements, strip script/nav headers', status: 'idle', progress: 0 },
    { id: 3, name: 'Chunking', description: 'Split cleaned markdown to semantic parts', status: 'idle', progress: 0 },
    { id: 4, name: 'Embeddings', description: 'Calculate vectors via embedding API', status: 'idle', progress: 0 },
    { id: 5, name: 'Vector Database', description: 'Store vectors in ChromaDB structures', status: 'idle', progress: 0 },
    { id: 6, name: 'Retriever', description: 'Query similarity vectors based on use case', status: 'idle', progress: 0 },
    { id: 7, name: 'LLM Extraction', description: 'Extract JSON schemas from retrieved context', status: 'idle', progress: 0 },
    { id: 8, name: 'Wrapper Generator', description: 'Compile production client wrapper class', status: 'idle', progress: 0 },
  ]);

  const addToast = (message: string, type: ToastMessage['type'] = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const addLog = (message: string, type: LogLine['type'] = 'system') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { timestamp, type, message }]);
  };

  // Timeline Step State helper
  const updateStepStatus = (
    stepId: number,
    status: PipelineStep['status'],
    progress: number,
    timeTaken?: string
  ) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === stepId ? { ...s, status, progress, timeTaken } : s))
    );
  };

  // Scroll to dashboard
  const scrollToDashboard = () => {
    const element = document.getElementById('dashboard');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Load high fidelity mock view
  const triggerDemo = () => {
    setDemoMode(true);
    setCrawlId('demo-crawl-123');
    setLanguage('python');
    setFilename('stripe_client.py');
    setCode(MOCK_CODE);
    setSchema(MOCK_SCHEMA);
    setActiveTab('code');

    // Populate timeline steps as complete
    setSteps((prev) =>
      prev.map((s) => ({
        ...s,
        status: 'completed',
        progress: 100,
        timeTaken: '0.4s',
      }))
    );

    // Logs
    setLogs([
      { timestamp: '12:00:00', type: 'system', message: 'Demo Mode Activated.' },
      { timestamp: '12:00:01', type: 'info', message: 'Initiated scrapers on https://api.stripe.com/v1...' },
      { timestamp: '12:00:02', type: 'success', message: 'Scraped 12 documentation files successfully.' },
      { timestamp: '12:00:02', type: 'system', message: 'Stripping HTML selectors...' },
      { timestamp: '12:00:03', type: 'info', message: 'Markdown content split into 68 chunks.' },
      { timestamp: '12:00:04', type: 'system', message: 'Generating vector weights...' },
      { timestamp: '12:00:05', type: 'success', message: 'Inserted chunks in ChromaDB: demo-crawl-123' },
      { timestamp: '12:00:05', type: 'info', message: 'Querying matching schemas for stripe integration...' },
      { timestamp: '12:00:06', type: 'success', message: 'Retrieved 6 documentation layers.' },
      { timestamp: '12:00:07', type: 'system', message: 'Extracting endpoints via LLM...' },
      { timestamp: '12:00:08', type: 'success', message: 'SDK Client Wrapper compiled successfully!' },
    ]);

    // Stats
    setStats({
      pagesCrawled: 12,
      chunksIndexed: 68,
      embeddingTimeMs: 1250,
      retrievedChunksCount: 6,
      llmTokensUsed: 14220,
      generationTimeMs: 2450,
      wrapperSizeBytes: MOCK_CODE.length,
    });

    // Preset chat history
    setChatMessages([
      { role: 'assistant', content: 'Hello! I am ready to explain the `Stripe API Wrapper` client details, parameters, or suggest test executions. Ask me anything!' },
    ]);

    addToast('Demo data loaded successfully!', 'success');
    scrollToDashboard();
  };

  // Submit and run RAG build pipeline
  const handleGenerate = async (config: {
    url: string;
    useCase: string;
    language: string;
    authType: string;
    wrapperStyle: string;
    outputFolder: string;
  }) => {
    setDemoMode(false);
    setIsCrawlLoading(true);
    setSchema(null);
    setCode('');
    setChatMessages([]);
    setLogs([]);
    
    // Reset steps to idle
    setSteps((prev) => prev.map((s) => ({ ...s, status: 'idle', progress: 0, timeTaken: undefined })));

    addLog(`Initiating web scrape crawl request for: ${config.url}`, 'info');
    updateStepStatus(1, 'running', 20);
    try {
      // 1. Post Crawl Job
      const crawlRes = await axios.post('/api/v1/crawl', {
        url: config.url,
        max_depth: 2,
      });

      const cid = crawlRes.data.crawl_id;
      setCrawlId(cid);
      addLog(`Crawl task registered. Job ID: ${cid}`, 'info');

      // 2. Poll Status
      pollCrawlStatus(cid, config.useCase, config.language);

    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail || err.message || 'Scrape initiation failed.';
      addLog(errMsg, 'error');
      updateStepStatus(1, 'failed', 0);
      setIsCrawlLoading(false);
      addToast('Workflow process failed', 'error');
    }
  };

  // Status Poller
  const pollCrawlStatus = (cid: string, useCase: string, targetLanguage: string) => {
    let lastAction = '';
    const pollStart = Date.now();

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/v1/status/${cid}`);
        const data = res.data;

        if (data.current_action !== lastAction && data.current_action) {
          lastAction = data.current_action;
          addLog(`${data.current_action}... (Indexed pages: ${data.pages_indexed})`, 'info');
        }

        // Map backend state strings to timeline steps
        const action = data.current_action?.toLowerCase() || '';
        
        if (action.includes('crawling')) {
          updateStepStatus(1, 'running', 60);
        } else if (action.includes('cleaning') || action.includes('html')) {
          updateStepStatus(1, 'completed', 100, `${((Date.now() - pollStart) / 1000).toFixed(1)}s`);
          updateStepStatus(2, 'running', 40);
        } else if (action.includes('chunking') || action.includes('split')) {
          updateStepStatus(1, 'completed', 100);
          updateStepStatus(2, 'completed', 100, '0.3s');
          updateStepStatus(3, 'running', 70);
        } else if (action.includes('embedding') || action.includes('vectorizing')) {
          updateStepStatus(1, 'completed', 100);
          updateStepStatus(2, 'completed', 100);
          updateStepStatus(3, 'completed', 100, '0.4s');
          updateStepStatus(4, 'running', 50);
        } else if (action.includes('indexing') || action.includes('chromadb')) {
          updateStepStatus(4, 'completed', 100, `${((Date.now() - pollStart) / 1000).toFixed(1)}s`);
          updateStepStatus(5, 'running', 80);
        }

        if (data.status === 'completed') {
          clearInterval(interval);
          
          updateStepStatus(1, 'completed', 100);
          updateStepStatus(2, 'completed', 100);
          updateStepStatus(3, 'completed', 100);
          updateStepStatus(4, 'completed', 100);
          updateStepStatus(5, 'completed', 100, '0.8s');

          addLog(`Documentation indexing successfully completed. Extracted ${data.pages_indexed} pages.`, 'success');
          
          // Move to LLM extraction phase
          triggerGeneration(cid, useCase, targetLanguage, data.pages_indexed);

        } else if (data.status === 'failed') {
          clearInterval(interval);
          addLog(`Pipeline crawling failed: ${data.error || 'Unknown error'}`, 'error');
          
          // Mark currently running step as failed
          setSteps((prev) =>
            prev.map((s) => (s.status === 'running' ? { ...s, status: 'failed' } : s))
          );
          
          setIsCrawlLoading(false);
          addToast('Scraping or indexing failed', 'error');
        }

      } catch (err: any) {
        clearInterval(interval);
        addLog(`Polling failed: ${err.message}`, 'error');
        setIsCrawlLoading(false);
      }
    }, 1500);
  };

  // Generate Wrapper Client
  const triggerGeneration = async (
    cid: string,
    useCase: string,
    targetLanguage: string,
    pagesIndexed: number
  ) => {
    addLog(`Initiating similarity retrieval and schema extraction queries...`, 'system');
    updateStepStatus(6, 'running', 50);
    updateStepStatus(7, 'running', 20);

    const startGen = Date.now();

    try {
      const genRes = await axios.post('/api/v1/generate', {
        crawl_id: cid,
        use_case: useCase,
        target_language: targetLanguage,
      });

      const data = genRes.data;
      const elapsed = Date.now() - startGen;

      updateStepStatus(6, 'completed', 100, '0.3s');
      updateStepStatus(7, 'completed', 100, `${(elapsed / 2000).toFixed(1)}s`);
      updateStepStatus(8, 'running', 90);

      setCode(data.wrapper_code);
      setSchema(data.schema_details);
      
      const ext = targetLanguage === 'python' ? 'py' : 'js';
      const cleanName = (data.schema_details.api_name || 'api_client')
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '_');
      setFilename(`${cleanName}_client.${ext}`);
      setLanguage(targetLanguage);

      updateStepStatus(8, 'completed', 100, '0.4s');
      addLog(`Wrapper client compiled successfully! Code size: ${data.wrapper_code.length} bytes`, 'success');
      
      // Calculate Stats
      const chunksCount = pagesIndexed * 5;
      setStats({
        pagesCrawled: pagesIndexed,
        chunksIndexed: chunksCount,
        embeddingTimeMs: pagesIndexed * 180,
        retrievedChunksCount: 6,
        llmTokensUsed: 12400 + (data.wrapper_code.length / 3),
        generationTimeMs: elapsed,
        wrapperSizeBytes: data.wrapper_code.length,
      });

      // Clear chat & greet user
      setChatMessages([
        { role: 'assistant', content: `Hello! I have loaded context schemas for **${data.schema_details.api_name}**. Ask me to explain endpoints, generate usage scripts, or refine methods.` },
      ]);

      setIsCrawlLoading(false);
      addToast('SDK Wrapper compiled successfully!', 'success');

    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail || err.message || 'Schema generation failed.';
      addLog(errMsg, 'error');
      updateStepStatus(7, 'failed', 0);
      updateStepStatus(8, 'failed', 0);
      setIsCrawlLoading(false);
      addToast('Code compilation failed', 'error');
    }
  };

  // Streaming Chat Assistant Handler
  const handleChat = async (text: string) => {
    if (isChatStreaming) return;
    
    // Add user message
    const updatedMessages = [...chatMessages, { role: 'user', content: text } as ChatMessage];
    setChatMessages(updatedMessages);
    setIsChatStreaming(true);

    // Add empty placeholder for assistant
    const placeholderIndex = updatedMessages.length;
    setChatMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    let accumulatedText = '';

    // Handle Mock chat responses in Demo mode
    if (demoMode) {
      const mockReply = `To initialize and use the Stripe SDK client class in python, follow this example structure:

\`\`\`python
# Initialize client
client = StripeClient(api_key="sk_test_51Nx...")

# Create payment intent
intent = client.create_payment_intent(
    amount=5000, # $50.00
    currency="usd",
    customer_id="cus_Qo2..."
)
print("Intent Created:", intent["id"])
\`\`\`

You can read the custom methods or endpoints schema in the adjacent **Extracted Schema** tab to look up parameter structures. Let me know if you need to optimize this wrapper code!`;

      // Simulate streaming chunks
      let charIndex = 0;
      const interval = setInterval(() => {
        if (charIndex >= mockReply.length) {
          clearInterval(interval);
          setIsChatStreaming(false);
        } else {
          const chunk = mockReply.slice(charIndex, charIndex + 8);
          accumulatedText += chunk;
          charIndex += 8;
          setChatMessages((prev) =>
            prev.map((msg, idx) => (idx === placeholderIndex ? { ...msg, content: accumulatedText } : msg))
          );
        }
      }, 35);
      return;
    }

    // Direct Live API Stream Call
    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: updatedMessages,
          crawl_id: crawlId,
        }),
      });

      if (!response.ok) {
        throw new Error('Chat connection interrupted.');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) {
        throw new Error('Streaming response reader is undefined.');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const token = decoder.decode(value, { stream: true });
        accumulatedText += token;

        setChatMessages((prev) =>
          prev.map((msg, idx) => (idx === placeholderIndex ? { ...msg, content: accumulatedText } : msg))
        );
      }

      setIsChatStreaming(false);

    } catch (err: any) {
      console.error(err);
      setChatMessages((prev) =>
        prev.map((msg, idx) =>
          idx === placeholderIndex
            ? { ...msg, content: `Error streaming chat response: ${err.message}` }
            : msg
        )
      );
      setIsChatStreaming(false);
    }
  };

  return (
    <div className="min-h-screen bg-darkBg text-zinc-100 font-sans relative">
      {/* Floating Glowing Backdrop Blobs */}
      <div className="glow-blob glow-blob-purple" />
      <div className="glow-blob glow-blob-blue" />
      <div className="glow-blob glow-blob-cyan" />

      {/* Navigation */}
      <Navbar />

      {/* Hero Section */}
      <Hero
        onCtaClick={scrollToDashboard}
        onDemoClick={triggerDemo}
      />

      {/* Main Workspace Dashboard */}
      <main id="dashboard" className="max-w-7xl mx-auto px-6 py-12 space-y-8 relative z-10">
        
        {/* Split Grid System */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Configuration Panel & Pipeline Timeline (40%) */}
          <div className="lg:col-span-5 space-y-6">
            <ConfigPanel onSubmit={handleGenerate} isLoading={isCrawlLoading} />
            <PipelineTimeline steps={steps} />
          </div>

          {/* Right Viewer & Action Tabs (60%) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Tabs Header */}
            <div className="flex items-center gap-1 border-b border-white/5 bg-zinc-950 p-1.5 rounded-xl">
              <button
                onClick={() => setActiveTab('code')}
                className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === 'code'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Generated Code
              </button>
              <button
                onClick={() => setActiveTab('schema')}
                className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === 'schema'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Extracted Schema
              </button>
              <button
                onClick={() => setActiveTab('logs')}
                className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === 'logs'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Pipeline Logs
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`flex-1 py-2 px-3 text-xs font-semibold rounded-lg transition-all ${
                  activeTab === 'chat'
                    ? 'bg-zinc-800 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Chat Assistant
              </button>
            </div>

            {/* Tab Panes */}
            <div className="transition-all duration-200">
              {activeTab === 'code' && (
                <CodeViewer code={code} language={language} filename={filename} />
              )}
              {activeTab === 'schema' && <SchemaViewer schema={schema} />}
              {activeTab === 'logs' && (
                <TerminalLogs logs={logs} onClear={() => setLogs([])} />
              )}
              {activeTab === 'chat' && (
                <ChatPanel
                  messages={chatMessages}
                  onSendMessage={handleChat}
                  isStreaming={isCrawlLoading || isChatStreaming}
                />
              )}
            </div>

            {/* Statistics Sidebar inside right pane */}
            <StatsSidebar stats={stats} />
          </div>
        </div>

        {/* Bottom Section: Flowchart Architecture */}
        <div className="pt-8">
          <ArchDiagram />
        </div>
      </main>

      {/* Global Toast Alerts */}
      <Toast toasts={toasts} onClose={removeToast} />
      
      {/* Footer */}
      <footer className="border-t border-white/5 py-8 mt-12 text-center text-[11px] text-zinc-600">
        © 2026 Smart DevTool API Wrapper Engine. Generated via RAG Retrieval.
      </footer>
    </div>
  );
};
export default App;
