import { S3Client, ListObjectsV2Command, GetObjectCommand } from "@aws-sdk/client-s3";
import path from "path";

/**
 * Create DigitalOcean Spaces S3 client
 */
function createDOSpacesClient() {
  return new S3Client({
    endpoint: process.env.DO_SPACES_ENDPOINT || "https://sgp1.digitaloceanspaces.com",
    region: process.env.DO_SPACES_REGION || "sgp1",
    credentials: {
      accessKeyId: process.env.DO_SPACES_ACCESS_KEY_ID!,
      secretAccessKey: process.env.DO_SPACES_SECRET_ACCESS_KEY!,
    },
    forcePathStyle: false,
  });
}

/**
 * List all documents in DO Spaces bucket
 */
export async function listDocumentsInDOSpaces(bucket: string): Promise<string[]> {
  const client = createDOSpacesClient();

  const command = new ListObjectsV2Command({
    Bucket: bucket,
    MaxKeys: 1000,
  });

  const response = await client.send(command);
  const documents: string[] = [];

  if (response.Contents) {
    for (const item of response.Contents) {
      if (item.Key) {
        // Only include supported file types
        const ext = path.extname(item.Key).toLowerCase();
        if ([".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt"].includes(ext)) {
          documents.push(item.Key);
        }
      }
    }
  }

  return documents;
}

/**
 * Fetch document content from DO Spaces into memory
 */
export async function fetchDocumentFromDOSpaces(
  bucket: string,
  key: string
): Promise<Buffer> {
  const client = createDOSpacesClient();

  const command = new GetObjectCommand({
    Bucket: bucket,
    Key: key,
  });

  const response = await client.send(command);

  if (!response.Body) {
    throw new Error(`Document not found: ${key}`);
  }

  // Convert stream to buffer
  const bodyBytes = await response.Body.transformToByteArray();
  return Buffer.from(bodyBytes);
}

/**
 * Fetch all documents from DO Spaces bucket
 */
export async function fetchAllDocumentsFromDOSpaces(
  bucket: string
): Promise<Map<string, Buffer>> {
  console.log(`\nFetching documents from DigitalOcean Spaces bucket: ${bucket}`);

  const documentKeys = await listDocumentsInDOSpaces(bucket);
  console.log(`Found ${documentKeys.length} documents\n`);

  const documents = new Map<string, Buffer>();

  for (const key of documentKeys) {
    console.log(`Fetching: ${key}`);
    const buffer = await fetchDocumentFromDOSpaces(bucket, key);
    documents.set(key, buffer);
  }

  console.log(`\n✅ Successfully fetched ${documents.size} documents into memory`);
  return documents;
}
