import { NextRequest } from "next/server";
import { search, SearchMode } from "@/lib/ai-search/search-service";
import { generateStreamingAIResponse } from "@/lib/ai-search/bedrock-client";

// Force dynamic rendering
export const dynamic = "force-dynamic";

// Mock file metadata for demo purposes
// In a real implementation, this could come from a local database or config file
function getFilesMapping() {
  const mockMapping = new Map();

  // Add mock metadata for test documents
  mockMapping.set('Q3-2024-Portfolio-Report.pdf', {
    name: 'Q3-2024-Portfolio-Report.pdf',
    file_path: 'demo/Q3-2024-Portfolio-Report.pdf',
    year: 2024,
    quarter: 'Q3',
    month: null
  });

  mockMapping.set('Company-A-DD-Report.pdf', {
    name: 'Company-A-DD-Report.pdf',
    file_path: 'demo/Company-A-DD-Report.pdf',
    year: 2024,
    quarter: null,
    month: null
  });

  mockMapping.set('LP-Update-2024.pdf', {
    name: 'LP-Update-2024.pdf',
    file_path: 'demo/LP-Update-2024.pdf',
    year: 2024,
    quarter: null,
    month: 8
  });

  // For any other files, generate basic metadata from filename
  // This allows the system to work with dynamically uploaded files
  return mockMapping;
}

export async function POST(request: NextRequest) {
  try {
    const { query, fileNames, mode = "lexical" } = await request.json();

    // Validate request
    if (!query || typeof query !== "string") {
      return new Response(
        JSON.stringify({ error: "Query is required" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Validate search mode
    const validModes: SearchMode[] = ["lexical", "semantic", "hybrid"];
    const searchMode = validModes.includes(mode) ? mode : "lexical";

    // Log search info
    console.log(`🔍 Search Mode: ${searchMode}`);
    if (fileNames && Array.isArray(fileNames)) {
      console.log(`📁 Filtering to ${fileNames.length} files`);
    } else {
      console.log(`📚 Searching all documents`);
    }

    // Step 1: Search using selected mode
    const searchResults = await search(query, {
      mode: searchMode,
      limit: 5,
      fileNames: fileNames && Array.isArray(fileNames) ? fileNames : undefined,
    });

    console.log(`✅ Found ${searchResults.length} results (${searchMode} mode)`);

    // Handle no results
    if (searchResults.length === 0) {
      return new Response(
        JSON.stringify({
          error: "No relevant documents found",
          answer: "I couldn't find any relevant information in the documents to answer your question.",
          sources: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }

    // Step 2: Enrich sources with mock file metadata
    const filesMapping = getFilesMapping();
    const context = searchResults.map((result) => result.text);
    const sources = searchResults.map((result) => {
      const fileData = filesMapping.get(result.filename);
      return {
        fileName: result.filename,
        score: result.score,
        pageNumber: result.pageNumber,
        pageStart: result.pageStart,
        pageEnd: result.pageEnd,
        totalPages: result.totalPages,
        chunkIndex: result.chunkIndex,
        searchMode: result.searchMode,
        // Add metadata for sorting (from mock data)
        year: fileData?.year ?? null,
        month: fileData?.month ?? null,
        quarter: fileData?.quarter ?? null,
      };
    });

    // Step 3: Stream AI response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Send metadata first
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: "metadata",
                searchMode,
                resultCount: searchResults.length,
              })}\n\n`
            )
          );

          // Send sources
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: "sources", sources })}\n\n`
            )
          );

          // Stream AI response
          for await (const chunk of generateStreamingAIResponse(query, context)) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: "text", content: chunk })}\n\n`
              )
            );
          }

          // Send completion signal
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: "done" })}\n\n`)
          );

          controller.close();
        } catch (error) {
          console.error("❌ Error in streaming:", error);
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: "error",
                error: error instanceof Error ? error.message : "Unknown error",
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
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("❌ Error in unified search:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to process search query",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
