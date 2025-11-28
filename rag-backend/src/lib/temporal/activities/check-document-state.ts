/**
 * Activity: Check Document State
 *
 * Checks if document exists in doc_states collection and compares ETag
 * to determine if processing is needed (deduplication).
 */

import { getMongoClient } from "../../ai-search/mongo-client";
import type {
  CheckDocumentStateInput,
  CheckDocumentStateOutput,
} from "./types";

export async function checkDocumentState(
  input: CheckDocumentStateInput
): Promise<CheckDocumentStateOutput> {
  const { documentId, filename } = input;

  console.log(`[checkDocumentState] Checking state for: ${filename} (${documentId})`);

  try {
    const client = await getMongoClient();
    const db = client.db(process.env.MONGODB_DATABASE);
    const collection = db.collection("doc_states");

    // Query by documentId
    const existingState = await collection.findOne({ documentId });

    if (!existingState) {
      console.log(`[checkDocumentState] Document not found - will process`);
      return {
        exists: false,
        shouldProcess: true,
      };
    }

    console.log(`[checkDocumentState] Found existing state:`, {
      etag: existingState.etag,
      status: existingState.status,
    });

    return {
      exists: true,
      etag: existingState.etag,
      status: existingState.status,
      shouldProcess: true, // Will be updated in workflow after comparing ETags
    };
  } catch (error: any) {
    console.error(`[checkDocumentState] Error:`, error);
    throw new Error(`Failed to check document state: ${error.message}`);
  }
}
