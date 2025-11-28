/**
 * Activity: Parse Document with LlamaParse
 *
 * Parses PDF document using LlamaParse and returns page-by-page text.
 * Reuses existing LlamaParse logic from document-processor.ts with caching.
 */

import path from "path";
import * as fs from "fs/promises";
import * as os from "os";
import { createHash } from "crypto";
import { LlamaParseReader } from "llama-cloud-services";
import { readParseCache, writeParseCache } from "../../ai-search/parse-cache";
import type { ParseDocumentInput, ParseDocumentOutput, PageText } from "./types";

// LlamaParse reader singleton
let llamaParseReader: LlamaParseReader | null = null;

function getLlamaParseReader(): LlamaParseReader {
  if (!llamaParseReader) {
    const apiKey = process.env.LLAMA_CLOUD_API_KEY;
    if (!apiKey) {
      throw new Error("LLAMA_CLOUD_API_KEY environment variable is required");
    }

    llamaParseReader = new LlamaParseReader({
      resultType: "markdown",
      apiKey: apiKey,
    });
  }
  return llamaParseReader;
}

export async function parseDocumentWithLlamaParse(
  input: ParseDocumentInput
): Promise<ParseDocumentOutput> {
  const { blob, filename, documentId } = input;

  console.log(`[parseDocument] Parsing ${filename} (${blob.length} bytes)`);

  try {
    const bufferHash = createHash("sha256").update(blob).digest("hex");

    // Check cache first (using documentId as cache key)
    const cachedPages = await readParseCache(documentId, bufferHash);
    if (cachedPages) {
      console.log(`[parseDocument] Using cached LlamaParse results`);
      return {
        pages: cachedPages.map((p) => ({
          page_number: p.pageNumber,
          text: p.text,
        })),
        totalPages: cachedPages.length,
      };
    }

    // Save PDF to temp file (LlamaParse requires file path)
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "llamaparse-"));
    const tempPdfPath = path.join(tempDir, filename);

    try {
      await fs.writeFile(tempPdfPath, blob);
      console.log(`[parseDocument] Saved temp PDF for parsing`);

      // Parse with LlamaParse using JSON mode for accurate page numbers
      console.log(`[parseDocument] Running LlamaParse...`);
      const reader = getLlamaParseReader();
      const jsonObjs = await reader.loadJson(tempPdfPath);

      console.log(`[parseDocument] LlamaParse completed: ${jsonObjs.length} document(s)`);

      // Extract pages from JSON
      const pages: PageText[] = [];
      for (const doc of jsonObjs) {
        if (doc.pages && Array.isArray(doc.pages)) {
          for (const page of doc.pages) {
            pages.push({
              page_number: page.page || pages.length + 1,
              text: page.text || page.md || "",
            });
          }
        }
      }

      console.log(`[parseDocument] Extracted ${pages.length} pages`);

      // Save to cache
      await writeParseCache(
        documentId,
        bufferHash,
        pages.map((p) => ({ pageNumber: p.page_number, text: p.text }))
      );

      return {
        pages,
        totalPages: pages.length,
      };
    } finally {
      // Cleanup temp file
      try {
        await fs.rm(tempDir, { recursive: true, force: true });
      } catch (err) {
        console.warn(`[parseDocument] Failed to cleanup temp directory:`, err);
      }
    }
  } catch (error: any) {
    console.error(`[parseDocument] Error:`, error);
    throw new Error(`Failed to parse document: ${error.message}`);
  }
}
