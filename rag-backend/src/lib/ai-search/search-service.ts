import { getDocPagesCollection, getDocChunksCollection, DocPage, DocChunk } from "./mongo-client";
import { generateEmbedding } from "./openai-embedding";

/**
 * Search mode types
 */
export type SearchMode = "lexical" | "semantic" | "hybrid";

/**
 * Search result with metadata
 */
export interface SearchResult {
  filename: string;
  score: number;
  pageNumber?: number;
  pageStart?: number;
  pageEnd?: number;
  totalPages: number;
  text: string;
  chunkIndex?: number;
  searchMode: SearchMode;
}

/**
 * Search options
 */
export interface SearchOptions {
  mode: SearchMode;
  limit?: number;
  fileNames?: string[];
}

/**
 * Lexical search using MongoDB Atlas Search (BM25)
 * Searches doc_pages collection using full-text search
 */
export async function lexicalSearch(
  query: string,
  limit: number = 5,
  fileNames?: string[]
): Promise<SearchResult[]> {
  const collection = await getDocPagesCollection();

  // Build search pipeline
  const pipeline: any[] = [
    {
      $search: {
        index: "doc_pages_search",
        text: {
          query: query,
          path: "text",
        },
      },
    },
    {
      $addFields: {
        score: { $meta: "searchScore" },
      },
    },
  ];

  // Add filename filter after search (simpler and more reliable)
  if (fileNames && fileNames.length > 0) {
    pipeline.push({
      $match: {
        filename: { $in: fileNames },
      },
    });
  }

  // Limit results
  pipeline.push({ $limit: limit });

  // Project fields
  pipeline.push({
    $project: {
      filename: 1,
      page_number: 1,
      total_pages: 1,
      text: 1,
      score: 1,
    },
  });

  const results = await collection.aggregate(pipeline).toArray();

  return results.map((doc) => ({
    filename: doc.filename,
    score: doc.score,
    pageNumber: doc.page_number,
    totalPages: doc.total_pages,
    text: doc.text,
    searchMode: "lexical" as SearchMode,
  }));
}

/**
 * Semantic search using MongoDB Atlas Vector Search
 * Searches doc_chunks collection using vector similarity
 */
export async function semanticSearch(
  query: string,
  limit: number = 5,
  fileNames?: string[]
): Promise<SearchResult[]> {
  const collection = await getDocChunksCollection();

  // Generate embedding for query
  const queryEmbedding = await generateEmbedding(query);

  // Build vector search pipeline
  const pipeline: any[] = [
    {
      $vectorSearch: {
        index: "doc_chunks_vector",
        path: "embedding",
        queryVector: queryEmbedding,
        numCandidates: limit * 10, // Oversample for better results
        limit: limit,
      },
    },
    {
      $addFields: {
        score: { $meta: "vectorSearchScore" },
      },
    },
  ];

  // Add file filter if provided
  if (fileNames && fileNames.length > 0) {
    pipeline.splice(1, 0, {
      $match: {
        filename: { $in: fileNames },
      },
    });
  }

  // Project fields
  pipeline.push({
    $project: {
      filename: 1,
      page_start: 1,
      page_end: 1,
      total_pages: 1,
      chunk_index: 1,
      text: 1,
      score: 1,
    },
  });

  const results = await collection.aggregate(pipeline).toArray();

  return results.map((doc) => ({
    filename: doc.filename,
    score: doc.score,
    pageStart: doc.page_start,
    pageEnd: doc.page_end,
    totalPages: doc.total_pages,
    text: doc.text,
    chunkIndex: doc.chunk_index,
    searchMode: "semantic" as SearchMode,
  }));
}

/**
 * Hybrid search using Reciprocal Rank Fusion (RRF)
 * Combines lexical and semantic search results
 */
export async function hybridSearch(
  query: string,
  limit: number = 5,
  fileNames?: string[]
): Promise<SearchResult[]> {
  // Run both searches in parallel
  const [lexicalResults, semanticResults] = await Promise.all([
    lexicalSearch(query, limit * 2, fileNames), // Get more results for fusion
    semanticSearch(query, limit * 2, fileNames),
  ]);

  // Reciprocal Rank Fusion (RRF)
  // Score = sum(1 / (k + rank)) for each result
  const k = 60; // RRF constant (common default)
  const scoreMap = new Map<string, { result: SearchResult; rrfScore: number }>();

  // Process lexical results
  lexicalResults.forEach((result, index) => {
    const key = `${result.filename}:${result.pageNumber || result.pageStart}`;
    const rrfScore = 1 / (k + index + 1);

    scoreMap.set(key, {
      result: { ...result, searchMode: "hybrid" as SearchMode },
      rrfScore,
    });
  });

  // Process semantic results
  semanticResults.forEach((result, index) => {
    const key = `${result.filename}:${result.pageStart}`;
    const rrfScore = 1 / (k + index + 1);

    const existing = scoreMap.get(key);
    if (existing) {
      // Combine scores if found in both
      existing.rrfScore += rrfScore;
    } else {
      scoreMap.set(key, {
        result: { ...result, searchMode: "hybrid" as SearchMode },
        rrfScore,
      });
    }
  });

  // Sort by RRF score and take top results
  const hybridResults = Array.from(scoreMap.values())
    .sort((a, b) => b.rrfScore - a.rrfScore)
    .slice(0, limit)
    .map((item) => ({
      ...item.result,
      score: item.rrfScore, // Use RRF score
    }));

  return hybridResults;
}

/**
 * Universal search function
 * Routes to the appropriate search method based on mode
 */
export async function search(
  query: string,
  options: SearchOptions
): Promise<SearchResult[]> {
  const { mode, limit = 5, fileNames } = options;

  switch (mode) {
    case "lexical":
      return lexicalSearch(query, limit, fileNames);
    case "semantic":
      return semanticSearch(query, limit, fileNames);
    case "hybrid":
      return hybridSearch(query, limit, fileNames);
    default:
      throw new Error(`Invalid search mode: ${mode}`);
  }
}
