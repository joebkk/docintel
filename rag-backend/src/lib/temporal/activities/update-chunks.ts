/**
 * Activity: Update Chunks Collection
 *
 * Updates MongoDB doc_chunks collection with chunks and embeddings.
 * Uses delete + insert pattern for incremental updates.
 */

import { getMongoClient } from "../../ai-search/mongo-client";
import type { UpdateChunksInput, UpdateChunksOutput } from "./types";

export async function updateChunksCollection(
  input: UpdateChunksInput
): Promise<UpdateChunksOutput> {
  const { documentId, chunks } = input;

  console.log(`[updateChunks] Updating ${chunks.length} chunks for documentId: ${documentId}`);

  try {
    const client = await getMongoClient();
    const db = client.db(process.env.MONGODB_DATABASE);
    const collection = db.collection("doc_chunks");

    // Delete existing chunks for this document
    const deleteResult = await collection.deleteMany({ documentId });
    console.log(`[updateChunks] Deleted ${deleteResult.deletedCount} existing chunks`);

    // Insert new chunks
    const documentsToInsert = chunks.map((chunk) => ({
      chunk_id: chunk.chunk_id,
      documentId: chunk.documentId,
      filename: chunk.filename,
      page_start: chunk.page_start,
      page_end: chunk.page_end,
      total_pages: chunk.total_pages,
      chunk_index: chunk.chunk_index,
      text: chunk.text,
      embedding: chunk.embedding,
      created_at: new Date(),
    }));

    const insertResult = await collection.insertMany(documentsToInsert);
    console.log(`[updateChunks] Inserted ${insertResult.insertedCount} chunks`);

    return {
      deletedCount: deleteResult.deletedCount,
      insertedCount: insertResult.insertedCount,
    };
  } catch (error: any) {
    console.error(`[updateChunks] Error:`, error);
    throw new Error(`Failed to update chunks collection: ${error.message}`);
  }
}
