/**
 * Type definitions for Temporal activities
 */

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Shared Types
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface DocumentInput {
  documentId: string; // UUID from backend
  filename: string; // Actual filename
  operation: "created" | "updated";
}

export interface DocumentMetadata {
  contentType: string;
  contentLength: number;
  lastModified: string;
  etag: string;
}

export interface PageText {
  page_number: number;
  text: string;
}

export interface ChunkWithEmbedding {
  chunk_id: string;
  documentId: string;
  filename: string;
  page_start: number;
  page_end: number;
  total_pages: number;
  chunk_index: number;
  text: string;
  embedding: number[];
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Activity Input/Output Types
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface CheckDocumentStateInput {
  documentId: string;
  filename: string;
}

export interface CheckDocumentStateOutput {
  exists: boolean;
  etag?: string;
  status?: string;
  shouldProcess: boolean; // Will be set to true if etag differs or doesn't exist
}

export interface GetPresignedUrlInput {
  filename: string;
}

export interface GetPresignedUrlOutput {
  presignedUrl: string;
  metadata: DocumentMetadata;
}

export interface FetchDocumentBlobInput {
  presignedUrl: string;
}

export interface FetchDocumentBlobOutput {
  blob: Buffer;
  size: number;
}

export interface ParseDocumentInput {
  blob: Buffer;
  filename: string;
  documentId: string;
}

export interface ParseDocumentOutput {
  pages: PageText[];
  totalPages: number;
}

export interface UpdatePagesInput {
  documentId: string;
  filename: string;
  pages: PageText[];
  totalPages: number;
}

export interface UpdatePagesOutput {
  deletedCount: number;
  insertedCount: number;
}

export interface GenerateEmbeddingsInput {
  documentId: string;
  filename: string;
  pages: PageText[];
  totalPages: number;
}

export interface GenerateEmbeddingsOutput {
  chunks: ChunkWithEmbedding[];
  totalChunks: number;
}

export interface UpdateChunksInput {
  documentId: string;
  chunks: ChunkWithEmbedding[];
}

export interface UpdateChunksOutput {
  deletedCount: number;
  insertedCount: number;
}

export interface UpdateDocumentStateInput {
  documentId: string;
  filename: string;
  etag: string;
  status: "completed" | "failed";
  error?: string;
}

export interface UpdateDocumentStateOutput {
  success: boolean;
}

export interface LogProcessingHistoryInput {
  workflowId: string;
  documentId: string;
  filename: string;
  startedAt: Date;
  completedAt: Date;
  status: "success" | "failed";
  error?: string;
  stats?: {
    pagesProcessed: number;
    chunksGenerated: number;
    processingTimeMs: number;
  };
}

export interface LogProcessingHistoryOutput {
  success: boolean;
}
