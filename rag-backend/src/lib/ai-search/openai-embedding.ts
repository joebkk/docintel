import OpenAI from "openai";

// Initialize OpenAI client lazily to ensure env vars are loaded
let client: OpenAI | null = null;

function getOpenAIClient(): OpenAI {
  if (!client) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error("OPENAI_API_KEY environment variable is required");
    }

    client = new OpenAI({
      apiKey: apiKey,
    });
  }
  return client;
}

/**
 * Generate embeddings using OpenAI text-embedding-3-large
 * @param text - The text to embed
 * @returns 3072-dimensional embedding vector
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  const openai = getOpenAIClient();

  const response = await openai.embeddings.create({
    model: "text-embedding-3-large",
    input: text,
    dimensions: 3072, // Maximum quality for finance/PE documents
  });

  return response.data[0].embedding;
}
