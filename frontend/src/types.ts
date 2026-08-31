export interface CrawlJob {
  crawl_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  pages_indexed: number;
  current_action: string;
  error?: string | null;
}

export interface Endpoint {
  method: string;
  path: string;
  description?: string;
  parameters?: Array<{
    name: string;
    type: string;
    required: boolean;
    description?: string;
    location: 'query' | 'path' | 'header' | 'body';
  }>;
  request_body?: any;
  responses?: any;
}

export interface ExtractedSchema {
  api_name: string;
  base_url: string;
  authentication?: {
    type: string;
    description?: string;
    key_name?: string;
    placeholder?: string;
  };
  endpoints: Endpoint[];
}

export interface GenerationResponse {
  status: string;
  wrapper_code: string;
  target_language: string;
  schema_details: ExtractedSchema;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface PipelineStats {
  pagesCrawled: number;
  chunksIndexed: number;
  embeddingTimeMs: number;
  retrievedChunksCount: number;
  llmTokensUsed: number;
  generationTimeMs: number;
  wrapperSizeBytes: number;
}
