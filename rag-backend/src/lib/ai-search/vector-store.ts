import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";
import { DocumentChunk } from "./document-processor";

export interface VectorDocument extends DocumentChunk {
  embedding: number[];
}

export interface SearchResult {
  document: DocumentChunk;
  score: number;
}

/**
 * Calculate cosine similarity between two vectors
 */
function cosineSimilarity(vecA: number[], vecB: number[]): number {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }

  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

/**
 * Create DigitalOcean Spaces S3 client for vector store
 */
function createVectorStoreClient() {
  return new S3Client({
    endpoint: process.env.VECTOR_STORE_ENDPOINT || "https://sgp1.digitaloceanspaces.com",
    region: process.env.VECTOR_STORE_REGION || "sgp1",
    credentials: {
      accessKeyId: process.env.VECTOR_STORE_ACCESS_KEY_ID!,
      secretAccessKey: process.env.VECTOR_STORE_SECRET_ACCESS_KEY!,
    },
    forcePathStyle: false,
  });
}

export class VectorStore {
  private documents: VectorDocument[] = [];
  private bucket: string;
  private key: string;

  /**
   * @param bucket - S3 bucket name (defaults to VECTOR_STORE_BUCKET env var)
   * @param key - S3 object key for the vector store file (default: "vector-store.json")
   */
  constructor(
    bucket: string = process.env.VECTOR_STORE_BUCKET || "sv-vector-store-temp",
    key: string = "vector-store.json"
  ) {
    this.bucket = bucket;
    this.key = key;
  }

  /**
   * Add documents with embeddings to the store
   */
  addDocuments(documents: VectorDocument[]): void {
    this.documents.push(...documents);
  }

  /**
   * Search for similar documents
   * @param queryEmbedding - The query embedding vector
   * @param topK - Number of top results to return
   * @param fileNames - Optional array of file names to filter search results (e.g., ["report.pdf", "summary.xlsx"])
   */
  async search(
    queryEmbedding: number[],
    topK: number = 3,
    fileNames?: string[]
  ): Promise<SearchResult[]> {
    // Filter documents by file names if provided
    let documentsToSearch = this.documents;

    if (fileNames && fileNames.length > 0) {
      documentsToSearch = this.documents.filter((doc) =>
        fileNames.includes(doc.metadata.fileName)
      );

      console.log(`Filtered vector search to ${documentsToSearch.length} documents from ${fileNames.length} file names`);

      // If no documents match the filter, return empty results
      if (documentsToSearch.length === 0) {
        console.warn('No documents found matching the provided file names');
        return [];
      }
    }

    const results = documentsToSearch.map((doc) => ({
      document: {
        id: doc.id,
        text: doc.text,
        metadata: doc.metadata,
      },
      score: cosineSimilarity(queryEmbedding, doc.embedding),
    }));

    // Sort by score descending
    results.sort((a, b) => b.score - a.score);

    // Return top K results
    return results.slice(0, topK);
  }

  /**
   * Save vector store to DigitalOcean Spaces (S3)
   */
  async save(): Promise<void> {
    const client = createVectorStoreClient();
    const jsonData = JSON.stringify(this.documents);
    const buffer = Buffer.from(jsonData, "utf-8");

    const command = new PutObjectCommand({
      Bucket: this.bucket,
      Key: this.key,
      Body: buffer,
      ContentType: "application/json",
    });

    await client.send(command);

    const sizeKB = (buffer.length / 1024).toFixed(2);
    console.log(`✅ Vector store saved to s3://${this.bucket}/${this.key} (${sizeKB} KB)`);
  }

  /**
   * Load vector store from DigitalOcean Spaces (S3)
   */
  async load(): Promise<void> {
    try {
      const client = createVectorStoreClient();

      const command = new GetObjectCommand({
        Bucket: this.bucket,
        Key: this.key,
      });

      const response = await client.send(command);

      if (!response.Body) {
        throw new Error(`Vector store not found: s3://${this.bucket}/${this.key}`);
      }

      // Convert stream to buffer
      const bodyBytes = await response.Body.transformToByteArray();
      const jsonData = Buffer.from(bodyBytes).toString("utf-8");
      this.documents = JSON.parse(jsonData);

      const sizeKB = (bodyBytes.length / 1024).toFixed(2);
      console.log(`✅ Loaded ${this.documents.length} documents from s3://${this.bucket}/${this.key} (${sizeKB} KB)`);
    } catch (error) {
      if (error instanceof Error && error.name === "NoSuchKey") {
        console.log("ℹ️  No existing vector store found in S3, starting fresh");
        this.documents = [];
      } else {
        console.log("⚠️  No existing vector store found, starting fresh");
        this.documents = [];
      }
    }
  }

  /**
   * Get number of documents in store
   */
  size(): number {
    return this.documents.length;
  }

  /**
   * Clear all documents
   */
  clear(): void {
    this.documents = [];
  }
}
