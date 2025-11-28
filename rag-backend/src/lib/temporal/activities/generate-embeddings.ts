/**
 * Activity: Generate Embeddings
 *
 * Chunks text and generates embeddings using OpenAI text-embedding-3-large.
 * Reuses existing chunking and embedding logic.
 */

import { generateEmbedding } from "../../ai-search/openai-embedding";
import type {
  GenerateEmbeddingsInput,
  GenerateEmbeddingsOutput,
  ChunkWithEmbedding,
} from "./types";

/**
 * Split text into chunks with overlap
 * Reused from scripts/build-doc-chunks-bulletproof.ts
 */
function chunkText(
  text: string,
  chunkSize: number = 1000,
  overlap: number = 200
): string[] {
  const chunks: string[] = [];

  if (!text || text.length === 0) return chunks;
  if (text.length <= chunkSize) {
    chunks.push(text);
    return chunks;
  }

  let start = 0;
  const maxIterations = Math.ceil(text.length / (chunkSize - overlap)) + 10;
  let iterations = 0;

  while (start < text.length && iterations < maxIterations) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.slice(start, end));
    start += chunkSize - overlap;
    iterations++;
  }

  return chunks;
}

export async function generateEmbeddings(
  input: GenerateEmbeddingsInput
): Promise<GenerateEmbeddingsOutput> {
  const { documentId, filename, pages, totalPages } = input;

  console.log(`[generateEmbeddings] Processing ${pages.length} pages for ${filename}`);

  try {
    const allChunks: ChunkWithEmbedding[] = [];

    // Process each page
    for (const page of pages) {
      const pageChunks = chunkText(page.text, 1000, 200);

      // Generate embeddings for each chunk
      for (let chunkIdx = 0; chunkIdx < pageChunks.length; chunkIdx++) {
        const chunkText = pageChunks[chunkIdx];

        // Generate embedding using OpenAI
        const embedding = await generateEmbedding(chunkText);

        // Create chunk with embedding
        const chunkId = `${documentId}_chunk_${allChunks.length}`;
        const chunk: ChunkWithEmbedding = {
          chunk_id: chunkId,
          documentId,
          filename,
          page_start: page.page_number,
          page_end: page.page_number,
          total_pages: totalPages,
          chunk_index: chunkIdx,
          text: chunkText,
          embedding: embedding,
        };

        allChunks.push(chunk);
      }
    }

    console.log(`[generateEmbeddings] Generated ${allChunks.length} chunks with embeddings`);

    return {
      chunks: allChunks,
      totalChunks: allChunks.length,
    };
  } catch (error: any) {
    console.error(`[generateEmbeddings] Error:`, error);
    throw new Error(`Failed to generate embeddings: ${error.message}`);
  }
}
