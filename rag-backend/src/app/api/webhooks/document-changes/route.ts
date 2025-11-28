import { NextRequest, NextResponse } from "next/server";
import { getTemporalClient } from "@/lib/temporal/client";

/**
 * Webhook payload types
 */
interface SingleDocumentPayload {
  documentId: string; // UUID
  filename: string; // Actual filename
  operation: "created" | "updated";
}

interface BatchDocumentPayload {
  documents: Array<{
    documentId: string; // UUID
    filename: string; // Actual filename
    operation: "created" | "updated";
  }>;
}

type WebhookPayload = SingleDocumentPayload | BatchDocumentPayload;

/**
 * Webhook endpoint for document change notifications
 * Receives notifications from backend system and triggers Temporal workflow
 *
 * POST /api/webhooks/document-changes
 *
 * Headers:
 *   Authorization: Bearer <DOCUMENT_WEBHOOK_API_KEY>
 *
 * Body (single document):
 *   { "documentId": "uuid-123", "filename": "Report.pdf", "operation": "created" }
 *
 * Body (batch):
 *   { "documents": [{ "documentId": "uuid-123", "filename": "Report.pdf", "operation": "created" }, ...] }
 */
export async function POST(request: NextRequest) {
  try {
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // Step 1: Authenticate
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    const authHeader = request.headers.get("authorization");
    const expectedKey = process.env.DOCUMENT_WEBHOOK_API_KEY;

    if (!expectedKey) {
      console.error("❌ DOCUMENT_WEBHOOK_API_KEY not configured");
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      console.warn("⚠️  Webhook request missing or invalid Authorization header");
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const providedKey = authHeader.slice(7); // Remove "Bearer " prefix
    if (providedKey !== expectedKey) {
      console.warn("⚠️  Webhook request with invalid API key");
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // Step 2: Parse and validate payload
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    const payload: WebhookPayload = await request.json();

    // Normalize to array format
    const documents = "documents" in payload
      ? payload.documents
      : "documentId" in payload
      ? [{ documentId: payload.documentId, filename: payload.filename, operation: payload.operation }]
      : [];

    if (documents.length === 0) {
      console.warn("⚠️  Webhook received empty or invalid payload", payload);
      return NextResponse.json(
        { error: "No documents provided" },
        { status: 400 }
      );
    }

    // Validate document payloads
    for (const doc of documents) {
      if (!doc.documentId || !doc.filename || !doc.operation) {
        console.warn("⚠️  Invalid document in payload:", doc);
        return NextResponse.json(
          { error: "Invalid document format: documentId, filename, and operation required" },
          { status: 400 }
        );
      }
    }

    console.log(`📥 Webhook received: ${documents.length} document(s)`);
    documents.forEach((doc, idx) => {
      console.log(`  ${idx + 1}. ${doc.filename} [${doc.documentId}] (${doc.operation})`);
    });

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // Step 3: Start Temporal workflow
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    const client = await getTemporalClient();
    const workflowId = `doc-proc-${Date.now()}`;
    const taskQueue = process.env.TEMPORAL_TASK_QUEUE || "document-processing";

    // Note: This will fail until we implement the workflow in Week 2
    // For now, we're just setting up the API structure
    try {
      await client.workflow.start("DocumentProcessingWorkflow", {
        taskQueue,
        workflowId,
        args: [
          {
            documents: documents.map((d) => ({
              documentId: d.documentId,
              filename: d.filename,
              operation: d.operation,
            })),
            triggeredBy: "webhook",
            timestamp: new Date().toISOString(),
          },
        ],
      });

      console.log(`✅ Workflow started: ${workflowId}`);
      console.log(`   Task queue: ${taskQueue}`);
      console.log(`   Documents: ${documents.length}`);

      return NextResponse.json({
        success: true,
        workflowId,
        documentsQueued: documents.length,
      });
    } catch (workflowError: any) {
      // Workflow not implemented yet (expected in Week 1)
      if (workflowError.message?.includes("not registered")) {
        console.warn("⚠️  Workflow not registered yet (expected in Week 1)");
        console.warn("   Webhook endpoint is working, but workflow needs to be implemented");
        return NextResponse.json({
          success: false,
          error: "Workflow not registered yet",
          message: "Webhook endpoint is working, but DocumentProcessingWorkflow needs to be registered in Week 2",
          workflowId,
          documentsReceived: documents.length,
        });
      }

      // Other workflow errors
      throw workflowError;
    }
  } catch (error: any) {
    console.error("❌ Webhook error:", error);
    return NextResponse.json(
      {
        error: "Internal server error",
        message: error.message,
      },
      { status: 500 }
    );
  }
}
