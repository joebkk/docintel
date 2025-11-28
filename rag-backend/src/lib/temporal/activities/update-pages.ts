/**
 * Activity: Update Pages Collection
 *
 * Updates MongoDB doc_pages collection with parsed pages.
 * Uses delete + insert pattern for incremental updates.
 */

import { getMongoClient } from "../../ai-search/mongo-client";
import type { UpdatePagesInput, UpdatePagesOutput } from "./types";

export async function updatePagesCollection(
  input: UpdatePagesInput
): Promise<UpdatePagesOutput> {
  const { documentId, filename, pages, totalPages } = input;

  console.log(`[updatePages] Updating ${pages.length} pages for ${filename}`);

  try {
    const client = await getMongoClient();
    const db = client.db(process.env.MONGODB_DATABASE);
    const collection = db.collection("doc_pages");

    // Delete existing pages for this document
    const deleteResult = await collection.deleteMany({ documentId });
    console.log(`[updatePages] Deleted ${deleteResult.deletedCount} existing pages`);

    // Insert new pages
    const documentsToInsert = pages.map((page) => ({
      documentId,
      filename,
      page_number: page.page_number,
      total_pages: totalPages,
      text: page.text,
      created_at: new Date(),
    }));

    const insertResult = await collection.insertMany(documentsToInsert);
    console.log(`[updatePages] Inserted ${insertResult.insertedCount} pages`);

    return {
      deletedCount: deleteResult.deletedCount,
      insertedCount: insertResult.insertedCount,
    };
  } catch (error: any) {
    console.error(`[updatePages] Error:`, error);
    throw new Error(`Failed to update pages collection: ${error.message}`);
  }
}
