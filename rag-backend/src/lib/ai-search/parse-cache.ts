import path from "path";
import fs from "fs/promises";
import { existsSync, mkdirSync } from "fs";
import { createHash } from "crypto";
import type { PageText } from "./document-processor";

const CACHE_DIR = path.resolve(process.cwd(), "data/parse-cache");

interface ParseCacheFile {
  hash: string;
  pages: PageText[];
  createdAt: string;
}

function ensureCacheDir() {
  if (!existsSync(CACHE_DIR)) {
    mkdirSync(CACHE_DIR, { recursive: true });
  }
}

function buildCacheFileName(cacheKey: string, bufferHash: string): { filePath: string; keyPrefix: string } {
  const keyHash = createHash("sha256").update(cacheKey).digest("hex").slice(0, 16);
  const fileName = `${keyHash}-${bufferHash}.json`;
  return {
    filePath: path.join(CACHE_DIR, fileName),
    keyPrefix: `${keyHash}-`,
  };
}

export async function readParseCache(cacheKey: string, bufferHash: string): Promise<PageText[] | null> {
  ensureCacheDir();
  const { filePath } = buildCacheFileName(cacheKey, bufferHash);

  try {
    const raw = await fs.readFile(filePath, "utf-8");
    const data: ParseCacheFile = JSON.parse(raw);

    if (data.hash === bufferHash && Array.isArray(data.pages)) {
      return data.pages;
    }
  } catch (error) {
    // Cache miss or invalid file; treat as miss
  }

  return null;
}

export async function writeParseCache(cacheKey: string, bufferHash: string, pages: PageText[]): Promise<void> {
  ensureCacheDir();
  const { filePath, keyPrefix } = buildCacheFileName(cacheKey, bufferHash);

  try {
    const existingFiles = await fs.readdir(CACHE_DIR);
    await Promise.all(
      existingFiles
        .filter((file) => file.startsWith(keyPrefix) && file !== path.basename(filePath))
        .map((file) => fs.rm(path.join(CACHE_DIR, file), { force: true }))
    );
  } catch (error) {
    // Ignore cleanup errors
  }

  const payload: ParseCacheFile = {
    hash: bufferHash,
    pages,
    createdAt: new Date().toISOString(),
  };

  await fs.writeFile(filePath, JSON.stringify(payload, null, 2), "utf-8");
}
