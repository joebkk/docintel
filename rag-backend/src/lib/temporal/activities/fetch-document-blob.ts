/**
 * Activity: Fetch Document Blob
 *
 * Downloads document from presigned URL and returns as Buffer.
 * Downloaded blob will be held in memory during processing.
 */

import type {
  FetchDocumentBlobInput,
  FetchDocumentBlobOutput,
} from "./types";

export async function fetchDocumentBlob(
  input: FetchDocumentBlobInput
): Promise<FetchDocumentBlobOutput> {
  const { presignedUrl } = input;

  console.log(`[fetchDocumentBlob] Downloading document...`);

  try {
    const response = await fetch(presignedUrl, {
      method: "GET",
    });

    if (!response.ok) {
      throw new Error(
        `Failed to download document (${response.status}): ${response.statusText}`
      );
    }

    // Get content as ArrayBuffer, then convert to Buffer
    const arrayBuffer = await response.arrayBuffer();
    const blob = Buffer.from(arrayBuffer);

    console.log(`[fetchDocumentBlob] Downloaded ${blob.length} bytes`);

    return {
      blob,
      size: blob.length,
    };
  } catch (error: any) {
    console.error(`[fetchDocumentBlob] Error:`, error);
    throw new Error(`Failed to fetch document blob: ${error.message}`);
  }
}
