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

  console.log(`[getPresignedUrl] Generating mock URL for: ${filename}`);

  try {
    // For demo purposes, return mock presigned URL data
    // In production, this would integrate with your storage solution (S3, DO Spaces, etc.)

    const mockPresignedUrl = `https://demo-storage.example.com/documents/${encodeURIComponent(filename)}?expires=3600`;

    const mockMetadata = {
      contentType: "application/pdf",
      contentLength: 1024 * 100, // 100KB mock size
      lastModified: new Date().toISOString(),
      etag: `"${Date.now()}"`, // Simple mock etag
    };

    console.log(`[getPresignedUrl] Mock URL generated:`, {
      filename,
      size: mockMetadata.contentLength,
      type: mockMetadata.contentType,
    });

    return {
      presignedUrl: mockPresignedUrl,
      metadata: mockMetadata,
    };
  } catch (error: any) {
    console.error(`[getPresignedUrl] Error:`, error);
    throw new Error(`Failed to generate presigned URL: ${error.message}`);
  }
}
