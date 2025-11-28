/**
 * Temporal Workflow: Document Processing
 *
 * Orchestrates the complete document processing pipeline:
 * 1. Check state (deduplication)
 * 2. Get presigned URL
 * 3. Fetch blob
 * 4. Parse with LlamaParse
 * 5. Update pages
 * 6. Generate embeddings
 * 7. Update chunks
 * 8. Update state
 * 9. Log history
 */

import { proxyActivities } from "@temporalio/workflow";
import type * as activities from "../activities";

// Configure activity options with retries and timeouts
const {
  checkDocumentState,
  getPresignedUrl,
  fetchDocumentBlob,
  parseDocumentWithLlamaParse,
  updatePagesCollection,
  generateEmbeddings,
  updateChunksCollection,
  updateDocumentState,
  logProcessingHistory,
} = proxyActivities<typeof activities>({
  startToCloseTimeout: "10 minutes", // Max time for a single activity
  retry: {
    initialInterval: "5s",
    maximumInterval: "1m",
    backoffCoefficient: 2,
    maximumAttempts: 3,
  },
});

// Workflow input type
export interface DocumentProcessingInput {
  documents: Array<{
    documentId: string;
    filename: string;
    operation: "created" | "updated";
  }>;
  triggeredBy: string; // "webhook" | "manual"
  timestamp: string;
}

// Workflow result type
export interface DocumentProcessingResult {
  workflowId: string;
  totalDocuments: number;
  successful: number;
  failed: number;
  skipped: number;
  results: Array<{
    documentId: string;
    filename: string;
    status: "success" | "failed" | "skipped";
    error?: string;
    stats?: {
      pagesProcessed: number;
      chunksGenerated: number;
      processingTimeMs: number;
    };
  }>;
}

/**
 * Main Document Processing Workflow
 */
export async function DocumentProcessingWorkflow(
  input: DocumentProcessingInput
): Promise<DocumentProcessingResult> {
  const { documents, triggeredBy, timestamp } = input;
  const workflowId = `doc-proc-${Date.now()}`;

  console.log(`[Workflow] Starting processing for ${documents.length} document(s)`);
  console.log(`[Workflow] Triggered by: ${triggeredBy} at ${timestamp}`);

  const results: DocumentProcessingResult["results"] = [];
  let successful = 0;
  let failed = 0;
  let skipped = 0;

  // Process each document
  for (const doc of documents) {
    const { documentId, filename, operation } = doc;
    const startTime = Date.now();

    console.log(`[Workflow] Processing: ${filename} (${documentId})`);

    try {
      // Step 1: Check document state for deduplication
      const stateCheck = await checkDocumentState({ documentId, filename });

      // Step 2: Get presigned URL and metadata (includes ETag)
      const urlData = await getPresignedUrl({ filename });
      const { presignedUrl, metadata } = urlData;
      const newEtag = metadata.etag;

      // Deduplication: Skip if ETag matches
      if (stateCheck.exists && stateCheck.etag === newEtag) {
        console.log(`[Workflow] Skipping ${filename} - ETag unchanged (${newEtag})`);
        results.push({
          documentId,
          filename,
          status: "skipped",
        });
        skipped++;
        continue;
      }

      console.log(`[Workflow] Processing ${filename} - ETag changed or new document`);

      // Step 3: Fetch document blob
      const { blob } = await fetchDocumentBlob({ presignedUrl });

      try {
        // Step 4: Parse with LlamaParse
        const { pages, totalPages } = await parseDocumentWithLlamaParse({
          blob,
          filename,
          documentId,
        });

        // Step 5: Update doc_pages collection
        await updatePagesCollection({
          documentId,
          filename,
          pages,
          totalPages,
        });

        // Step 6: Generate embeddings
        const { chunks, totalChunks } = await generateEmbeddings({
          documentId,
          filename,
          pages,
          totalPages,
        });

        // Step 7: Update doc_chunks collection
        await updateChunksCollection({
          documentId,
          chunks,
        });

        // Step 8: Update document state (success)
        await updateDocumentState({
          documentId,
          filename,
          etag: newEtag,
          status: "completed",
        });

        const processingTimeMs = Date.now() - startTime;

        // Step 9: Log processing history
        await logProcessingHistory({
          workflowId,
          documentId,
          filename,
          startedAt: new Date(startTime),
          completedAt: new Date(),
          status: "success",
          stats: {
            pagesProcessed: totalPages,
            chunksGenerated: totalChunks,
            processingTimeMs,
          },
        });

        console.log(`[Workflow] ✅ Completed ${filename} in ${(processingTimeMs / 1000).toFixed(2)}s`);

        results.push({
          documentId,
          filename,
          status: "success",
          stats: {
            pagesProcessed: totalPages,
            chunksGenerated: totalChunks,
            processingTimeMs,
          },
        });
        successful++;
      } catch (activityError: any) {
        // Caught errors from activities (parse, embed, etc.)
        throw activityError;
      }

      // Note: Memory is automatically managed:
      // - The 'blob' variable exists only during parseDocumentWithLlamaParse activity execution
      // - Each activity runs in its own execution context and cleans up after completion
      // - Temporal doesn't persist large binary data in workflow state
    } catch (error: any) {
      console.error(`[Workflow] ❌ Failed to process ${filename}:`, error);

      const processingTimeMs = Date.now() - startTime;

      // Update document state (failed)
      try {
        await updateDocumentState({
          documentId,
          filename,
          etag: "", // Keep empty on failure
          status: "failed",
          error: error.message,
        });
      } catch (stateError) {
        console.error(`[Workflow] Failed to update state for ${filename}:`, stateError);
      }

      // Log processing history (failure)
      try {
        await logProcessingHistory({
          workflowId,
          documentId,
          filename,
          startedAt: new Date(startTime),
          completedAt: new Date(),
          status: "failed",
          error: error.message,
        });
      } catch (historyError) {
        console.error(`[Workflow] Failed to log history for ${filename}:`, historyError);
      }

      results.push({
        documentId,
        filename,
        status: "failed",
        error: error.message,
      });
      failed++;
    }
  }

  console.log(`[Workflow] Complete: ${successful} successful, ${failed} failed, ${skipped} skipped`);

  return {
    workflowId,
    totalDocuments: documents.length,
    successful,
    failed,
    skipped,
    results,
  };
}
