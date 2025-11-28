import path from "path";
import mammoth from "mammoth";
import { LlamaParseReader } from "llama-cloud-services";
import * as fs from "fs/promises";
import * as os from "os";
import { createHash } from "crypto";
import { readParseCache, writeParseCache } from "./parse-cache";

export interface DocumentChunk {
  id: string;
  text: string;
  metadata: {
    source: string;
    chunkIndex: number;
    fileName: string;
    pageStart?: number;
    pageEnd?: number;
    totalPages?: number;
  };
}

export interface PageText {
  pageNumber: number;
  text: string;
}

// Initialize LlamaParse reader lazily to ensure env vars are loaded
let llamaParseReader: LlamaParseReader | null = null;

function getLlamaParseReader(): LlamaParseReader {
  if (!llamaParseReader) {
    const apiKey = process.env.LLAMA_CLOUD_API_KEY;
    if (!apiKey) {
      throw new Error("LLAMA_CLOUD_API_KEY environment variable is required");
    }

    llamaParseReader = new LlamaParseReader({
      resultType: "markdown", // Use markdown for better table/structure preservation
      apiKey: apiKey,
    });
  }
  return llamaParseReader;
}

/**
 * Extract text from PDF buffer using LlamaParse (replaces OCR + pdf-parse)
 */
async function extractTextFromPDF(
  buffer: Buffer,
  fileName: string,
  cacheKey?: string
): Promise<PageText[]> {
  console.log(`  📄 Processing ${fileName} with LlamaParse...`);

  const bufferHash = createHash("sha256").update(buffer).digest("hex");

  // Check cache first
  if (cacheKey) {
    const cachedPages = await readParseCache(cacheKey, bufferHash);
    if (cachedPages) {
      console.log(`    ↩︎ Using cached LlamaParse results for ${fileName}`);
      return cachedPages;
    }
  }

  try {
    // Save PDF to temp file (LlamaParse requires file path)
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "llamaparse-"));
    const tempPdfPath = path.join(tempDir, fileName);

    try {
      await fs.writeFile(tempPdfPath, buffer);
      console.log(`    ✓ Saved temp PDF for parsing`);

      // Parse with LlamaParse using JSON mode for accurate page numbers
      console.log(`    🔍 Running LlamaParse...`);
      const reader = getLlamaParseReader();
      const jsonObjs = await reader.loadJson(tempPdfPath);

      console.log(`    ✓ LlamaParse completed: ${jsonObjs.length} document(s)`);

      // Extract pages with explicit page numbers from JSON
      const pages: PageText[] = [];

      for (const jsonObj of jsonObjs) {
        // Each JSON object has a "pages" array with page number and text
        const pagesList = jsonObj.pages || [];

        for (const pageData of pagesList) {
          pages.push({
            pageNumber: pageData.page || 1,
            text: pageData.text || "",
          });
        }
      }

      // Sort by page number to ensure correct order
      pages.sort((a, b) => a.pageNumber - b.pageNumber);

      const totalChars = pages.reduce((acc, page) => acc + page.text.length, 0);
      console.log(`    ✅ Extracted ${pages.length} page(s), ${totalChars} chars\n`);

      // Cleanup temp files
      await fs.rm(tempDir, { recursive: true, force: true });

      // Cache the results
      if (cacheKey && pages.length > 0) {
        await writeParseCache(cacheKey, bufferHash, pages);
      }

      return pages;

    } catch (error) {
      // Cleanup on error
      await fs.rm(tempDir, { recursive: true, force: true }).catch(() => {});
      throw error;
    }

  } catch (error) {
    console.error(`    ❌ LlamaParse failed for ${fileName}:`, error);

    // Return empty result with error logged
    const fallback = [{
      pageNumber: 1,
      text: `[Error parsing PDF: ${error instanceof Error ? error.message : 'Unknown error'}]`,
    }];

    if (cacheKey) {
      await writeParseCache(cacheKey, bufferHash, fallback);
    }

    return fallback;
  }
}

/**
 * Extract text from Word document buffer
 */
async function extractTextFromWord(buffer: Buffer): Promise<string> {
  const result = await mammoth.extractRawText({ buffer });
  return result.value;
}

/**
 * Extract text from plain text buffer
 */
async function extractTextFromTxt(buffer: Buffer): Promise<string> {
  return buffer.toString("utf-8");
}

/**
 * Extract text from buffer based on file extension
 */
export async function extractTextFromBuffer(
  buffer: Buffer,
  fileName: string,
  options?: { cacheKey?: string }
): Promise<string | PageText[]> {
  const ext = path.extname(fileName).toLowerCase();

  switch (ext) {
    case ".pdf":
      return await extractTextFromPDF(buffer, fileName, options?.cacheKey);
    case ".docx":
    case ".doc":
      return await extractTextFromWord(buffer);
    case ".txt":
      return await extractTextFromTxt(buffer);
    case ".pptx":
    case ".ppt":
      // PowerPoint extraction would need additional library
      // For now, return placeholder
      console.warn(`PowerPoint files not yet supported: ${fileName}`);
      return "";
    default:
      throw new Error(`Unsupported file type: ${ext}`);
  }
}

/**
 * Split text into chunks for better retrieval
 */
export function chunkText(
  text: string,
  chunkSize: number = 1000,
  overlap: number = 200
): string[] {
  const chunks: string[] = [];
  let start = 0;

  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.slice(start, end));
    start += chunkSize - overlap;
  }

  return chunks;
}

/**
 * Process a single document buffer into chunks
 */
export async function processDocumentBuffer(
  buffer: Buffer,
  fileName: string,
  source: string
): Promise<DocumentChunk[]> {
  const extractedText = await extractTextFromBuffer(buffer, fileName, { cacheKey: source });

  if (!extractedText || (typeof extractedText === "string" && extractedText.trim().length === 0)) {
    console.warn(`No text extracted from: ${fileName}`);
    return [];
  }

  // Handle PDF output (per-page text array) separately so we can keep page metadata
  if (Array.isArray(extractedText)) {
    const totalPages = extractedText.length;
    const chunks: DocumentChunk[] = [];
    let chunkIndex = 0;

    for (const page of extractedText) {
      const pageText = page.text ?? "";
      if (!pageText.trim()) continue;

      const pageChunks = chunkText(pageText);
      for (const chunk of pageChunks) {
        if (!chunk.trim()) continue;

        chunks.push({
          id: `${fileName}_chunk_${chunkIndex}`,
          text: chunk,
          metadata: {
            source,
            chunkIndex,
            fileName,
            pageStart: page.pageNumber,
            pageEnd: page.pageNumber,
            totalPages,
          },
        });

        chunkIndex++;
      }
    }

    return chunks;
  }

  // Handle non-PDF documents (Word, Text files)
  const textChunks = chunkText(extractedText);

  return textChunks
    .map((chunk, index) => {
      if (!chunk.trim()) {
        return null;
      }

      return {
        id: `${fileName}_chunk_${index}`,
        text: chunk,
        metadata: {
          source,
          chunkIndex: index,
          fileName,
        },
      } as DocumentChunk;
    })
    .filter((chunk): chunk is DocumentChunk => chunk !== null);
}

/**
 * Process multiple documents from a Map of buffers
 */
export async function processDocumentBuffers(
  documents: Map<string, Buffer>
): Promise<DocumentChunk[]> {
  const allChunks: DocumentChunk[] = [];
  const totalDocs = documents.size;
  let currentDoc = 0;

  for (const [key, buffer] of documents.entries()) {
    currentDoc++;
    const fileName = path.basename(key);
    const docProgress = ((currentDoc / totalDocs) * 100).toFixed(1);

    console.log(`\n📑 [${currentDoc}/${totalDocs}] (${docProgress}%) ${fileName}`);

    try {
      const chunks = await processDocumentBuffer(buffer, fileName, key);
      allChunks.push(...chunks);
      console.log(`  ✅ Created ${chunks.length} chunks (total so far: ${allChunks.length})`);
    } catch (error) {
      console.error(`  ❌ Error processing ${fileName}:`, error);
    }
  }

  return allChunks;
}
