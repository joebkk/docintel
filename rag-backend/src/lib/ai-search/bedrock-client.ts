import {
  BedrockRuntimeClient,
  InvokeModelCommand,
  InvokeModelWithResponseStreamCommand,
} from "@aws-sdk/client-bedrock-runtime";

// Initialize Bedrock client lazily to ensure env vars are loaded
let bedrockClient: BedrockRuntimeClient | null = null;

function getBedrockClient(): BedrockRuntimeClient {
  if (!bedrockClient) {
    bedrockClient = new BedrockRuntimeClient({
      region: process.env.AWS_REGION || "us-east-1",
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
      },
    });
  }
  return bedrockClient;
}

/**
 * Generate embeddings using Amazon Titan Embeddings V2
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  const input = {
    modelId: "amazon.titan-embed-text-v2:0",
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      inputText: text,
      dimensions: 1024, // V2 supports: 256, 512, 1024 (NOT 1536)
      normalize: true,
    }),
  };

  try {
    const command = new InvokeModelCommand(input);
    const response = await getBedrockClient().send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));
    return responseBody.embedding;
  } catch (error) {
    console.error("Error generating embedding:", error);
    throw error;
  }
}

/**
 * Generate AI response using Claude Sonnet 4.5 with context
 */
export async function generateAIResponse(
  query: string,
  context: string[]
): Promise<string> {
  const prompt = `You are a helpful AI assistant that answers questions based on the provided context from documents.

Context from documents:
${context.join("\n\n---\n\n")}

User question: ${query}

Please provide a clear and concise answer based on the context above. If the context doesn't contain relevant information, say so politely.`;

  const input = {
    modelId: "us.anthropic.claude-sonnet-4-5-20250929-v1:0", // Claude Sonnet 4.5 (cross-region inference)
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: prompt,
        },
      ],
    }),
  };

  try {
    const command = new InvokeModelCommand(input);
    const response = await getBedrockClient().send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));
    return responseBody.content[0].text;
  } catch (error) {
    console.error("Error generating AI response:", error);
    throw error;
  }
}

/**
 * Generate streaming AI response using Claude Sonnet 4.5
 */
export async function* generateStreamingAIResponse(
  query: string,
  context: string[]
): AsyncGenerator<string> {
  const prompt = `You are a helpful AI assistant that answers questions based on the provided context from documents.

Context from documents:
${context.join("\n\n---\n\n")}

User question: ${query}

Please provide a clear and concise answer based on the context above. If the context doesn't contain relevant information, say so politely.`;

  const input = {
    modelId: "us.anthropic.claude-sonnet-4-5-20250929-v1:0", // Claude Sonnet 4.5 (cross-region inference)
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: prompt,
        },
      ],
    }),
  };

  try {
    const command = new InvokeModelWithResponseStreamCommand(input);
    const response = await getBedrockClient().send(command);

    if (response.body) {
      for await (const event of response.body) {
        if (event.chunk) {
          const chunk = JSON.parse(new TextDecoder().decode(event.chunk.bytes));
          if (chunk.type === "content_block_delta") {
            yield chunk.delta.text;
          }
        }
      }
    }
  } catch (error) {
    console.error("Error generating streaming response:", error);
    throw error;
  }
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * Generate streaming conversational AI response with history and context
 */
export async function* generateStreamingAIChatResponse(
  systemPrompt: string,
  conversation: ChatMessage[],
  context: string[]
): AsyncGenerator<string> {
  const conversationText =
    conversation
      .map((message) => {
        const speaker = message.role === "assistant" ? "Assistant" : "User";
        return `${speaker}: ${message.content}`;
      })
      .join("\n") || "No prior conversation.";

  const prompt = `${systemPrompt}

Document excerpts:
${context.length > 0 ? context.join("\n\n---\n\n") : "No relevant context was found for this document."}

Conversation so far:
${conversationText}

Respond to the most recent user message. Reference page numbers when provided in the context.`;

  const input = {
    modelId: "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: prompt,
        },
      ],
    }),
  };

  try {
    const command = new InvokeModelWithResponseStreamCommand(input);
    const response = await getBedrockClient().send(command);

    if (response.body) {
      for await (const event of response.body) {
        if (event.chunk) {
          const chunk = JSON.parse(new TextDecoder().decode(event.chunk.bytes));
          if (chunk.type === "content_block_delta") {
            yield chunk.delta.text;
          }
        }
      }
    }
  } catch (error) {
    console.error("Error generating conversational response:", error);
    throw error;
  }
}
