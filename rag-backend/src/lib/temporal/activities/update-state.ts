/**
 * Activity: Update Document State
 *
 * Updates doc_states collection with processing status and ETag.
 * Used for deduplication and tracking.
 */

import { getMongoClient } from "../../ai-search/mongo-client";
import type {
  UpdateDocumentStateInput,
  UpdateDocumentStateOutput,
} from "./types";

export async function updateDocumentState(
  input: UpdateDocumentStateInput
): Promise<UpdateDocumentStateOutput> {
  const { documentId, filename, etag, status, error } = input;

  console.log(`[updateState] Updating state for ${filename}: ${status}`);

  try {
    const client = await getMongoClient();
    const db = client.db(process.env.MONGODB_DATABASE);
    const collection = db.collection("doc_states");

    // Upsert document state
    const updateDoc: any = {
      documentId,
      filename,
      etag,
      status,
      processedAt: new Date(),
    };

    if (error) {
      updateDoc.error = error;
    }

    await collection.updateOne(
      { documentId } as any,
      { $set: updateDoc },
      { upsert: true }
    );

    console.log(`[updateState] State updated successfully`);

    return {
      success: true,
    };
  } catch (err: any) {
    console.error(`[updateState] Error:`, err);
    throw new Error(`Failed to update document state: ${err.message}`);
  }
}
