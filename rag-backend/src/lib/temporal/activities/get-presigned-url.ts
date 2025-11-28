/**
 * Activity: Get Presigned URL
 *
 * Calls backend API to get presigned URL and metadata for document.
 * Backend API: GET /api/files/do/signed/{filename}
 */

import type {
  GetPresignedUrlInput,
  GetPresignedUrlOutput,
} from "./types";

export async function getPresignedUrl(
  input: GetPresignedUrlInput
): Promise<GetPresignedUrlOutput> {
  const { filename } = input;

  console.log(`[getPresignedUrl] Requesting URL for: ${filename}`);

  try {
    const backendApiKey = process.env.DOCS_BACKEND_API_KEY;
    const backendUrl = process.env.DOCS_BACKEND_URL || "https://docs-backend.sunventure.com";

    if (!backendApiKey) {
      throw new Error("DOCS_BACKEND_API_KEY not configured");
    }

    // URL encode the filename
    const encodedFilename = encodeURIComponent(filename);
    const url = `${backendUrl}/api/files/do/signed/${encodedFilename}`;

    console.log(`[getPresignedUrl] Calling: ${url}`);

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "x-api-key": backendApiKey,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Backend API error (${response.status}): ${errorText}`
      );
    }

    const data = await response.json();

    console.log(`[getPresignedUrl] Success:`, {
      etag: data.metadata?.etag,
      size: data.metadata?.contentLength,
      urlExpires: data.urlExpiresAt,
    });

    return {
      presignedUrl: data.presignedUrl,
      metadata: {
        contentType: data.metadata.contentType,
        contentLength: data.metadata.contentLength,
        lastModified: data.metadata.lastModified,
        etag: data.metadata.etag,
      },
    };
  } catch (error: any) {
    console.error(`[getPresignedUrl] Error:`, error);
    throw new Error(`Failed to get presigned URL: ${error.message}`);
  }
}
