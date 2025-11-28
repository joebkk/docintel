import { NextRequest } from "next/server";
import {
  ChatMessage,
  generateEmbedding,
  generateStreamingAIChatResponse,
} from "@/lib/ai-search/bedrock-client";
import { VectorStore } from "@/lib/ai-search/vector-store";

export const dynamic = "force-dynamic";

let vectorStore: VectorStore | null = null;

async function getVectorStore(): Promise<VectorStore> {
  if (!vectorStore) {
    vectorStore = new VectorStore();
    await vectorStore.load();
  }
  return vectorStore;
}

interface ChatRequestMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatRequestBody {
  documentKey?: string;
  fileName?: string;
  messages: ChatRequestMessage[];
}

const MAX_HISTORY_MESSAGES = 12;

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequestBody = await request.json();

    if (!body || !Array.isArray(body.messages) || body.messages.length === 0) {
      return new Response(
        JSON.stringify({ error: "Messages are required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const latestUserMessage = [...body.messages]
      .reverse()
      .find((message) => message.role === "user");

    if (!latestUserMessage) {
      return new Response(
        JSON.stringify({ error: "At least one user message is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    const trimmedHistory = body.messages.slice(-MAX_HISTORY_MESSAGES);

    const queryEmbedding = await generateEmbedding(latestUserMessage.content);
    const store = await getVectorStore();

    const searchResults = await store.search(
      queryEmbedding,
      6,
      body.fileName ? [body.fileName] : undefined
    );

    const filteredResults = searchResults.filter((result) => {
      const matchesFileName = body.fileName
        ? result.document.metadata.fileName === body.fileName
        : true;
      const matchesSource = body.documentKey
        ? result.document.metadata.source === body.documentKey
        : true;
      return matchesFileName && matchesSource;
    });

    const context = filteredResults.map((result) => result.document.text);
    const sources = filteredResults.map((result) => ({
      fileName: result.document.metadata.fileName,
      score: result.score,
      chunkIndex: result.document.metadata.chunkIndex,
      pageStart: result.document.metadata.pageStart,
      pageEnd: result.document.metadata.pageEnd,
      totalPages: result.document.metadata.totalPages,
    }));

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: "sources", sources })}\n\n`
            )
          );

          const systemPrompt = `You are an AI assistant helping the user understand the document "${body.fileName || "current document"}".
Only rely on the provided document excerpts when answering.
If the excerpts do not contain the requested information, politely explain that it is not available.
Respond in a conversational manner.`;

          const conversation: ChatMessage[] = trimmedHistory.map((message) => ({
            role: message.role,
            content: message.content,
          }));

          for await (const chunk of generateStreamingAIChatResponse(
            systemPrompt,
            conversation,
            context
          )) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: "text", content: chunk })}\n\n`
              )
            );
          }

          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "done" })}\n\n`)
          );
          controller.close();
        } catch (error) {
          console.error("Error in AI chat stream:", error);
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: "error",
                error:
                  error instanceof Error ? error.message : "Unknown error occurred",
              })}\n\n`
            )
          );
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("Error in /api/ai-chat:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to process chat request",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
