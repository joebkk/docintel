import { MongoClient, Db, Collection } from "mongodb";

// MongoDB client singleton
let client: MongoClient | null = null;
let db: Db | null = null;

/**
 * Get MongoDB client (singleton pattern)
 */
export async function getMongoClient(): Promise<MongoClient> {
  if (client) {
    return client;
  }

  const uri = process.env.MONGODB_URI;
  if (!uri) {
    throw new Error("MONGODB_URI environment variable is not set");
  }

  client = new MongoClient(uri);
  await client.connect();
  console.log("✅ Connected to MongoDB Atlas");

  return client;
}

/**
 * Get database instance
 */
export async function getDatabase(): Promise<Db> {
  if (db) {
    return db;
  }

  const mongoClient = await getMongoClient();
  const dbName = process.env.MONGODB_DATABASE || "docurepo";
  db = mongoClient.db(dbName);

  return db;
}

/**
 * Get doc_pages collection
 */
export async function getDocPagesCollection(): Promise<Collection<DocPage>> {
  const database = await getDatabase();
  const collectionName = process.env.MONGODB_COLLECTION_PAGES || "doc_pages";
  return database.collection<DocPage>(collectionName);
}

/**
 * Get doc_chunks collection
 */
export async function getDocChunksCollection(): Promise<Collection<DocChunk>> {
  const database = await getDatabase();
  const collectionName = process.env.MONGODB_COLLECTION_CHUNKS || "doc_chunks";
  return database.collection<DocChunk>(collectionName);
}

/**
 * Close MongoDB connection
 */
export async function closeMongoConnection(): Promise<void> {
  if (client) {
    await client.close();
    client = null;
    db = null;
    console.log("✅ MongoDB connection closed");
  }
}

// TypeScript interfaces for documents

export interface DocPage {
  _id?: any;
  filename: string;
  page_number: number;
  total_pages: number;
  text: string;
  created_at: Date;
}

export interface DocChunk {
  _id?: any;
  chunk_id: string;
  filename: string;
  page_start: number;
  page_end: number;
  total_pages: number;
  chunk_index: number;
  text: string;
  embedding: number[];
  created_at: Date;
}
