/**
 * Activity: Log Processing History
 *
 * Logs processing history to processing_history collection for audit trail.
 */

import { getMongoClient } from "../../ai-search/mongo-client";
import type {
  LogProcessingHistoryInput,
  LogProcessingHistoryOutput,
} from "./types";

export async function logProcessingHistory(
  input: LogProcessingHistoryInput
): Promise<LogProcessingHistoryOutput> {
  const {
    workflowId,
    documentId,
    filename,
    startedAt,
    completedAt,
    status,
    error,
    stats,
  } = input;

  console.log(`[logHistory] Logging processing history for ${filename}`);

  try {
    const client = await getMongoClient();
    const db = client.db(process.env.MONGODB_DATABASE);
    const collection = db.collection("processing_history");

    const historyDoc = {
      workflowId,
      documentId,
      filename,
      startedAt,
      completedAt,
      status,
      error: error || null,
      stats: stats || null,
      createdAt: new Date(),
    };

    await collection.insertOne(historyDoc);

    console.log(`[logHistory] History logged successfully`);

    return {
      success: true,
    };
  } catch (err: any) {
    console.error(`[logHistory] Error:`, err);
    // Don't throw - logging failure shouldn't fail the workflow
    console.warn(`[logHistory] Failed to log history, but continuing: ${err.message}`);
    return {
      success: false,
    };
  }
}
