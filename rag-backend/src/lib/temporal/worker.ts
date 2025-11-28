/**
 * Temporal Worker: Document Processing
 *
 * Long-running process that polls Temporal Cloud for work.
 * Executes workflows and activities for document processing.
 *
 * Run with: npx tsx src/lib/temporal/worker.ts
 * Or deploy with PM2/systemd for production.
 */

import { NativeConnection, Worker } from "@temporalio/worker";
import * as activities from "./activities";
import * as dotenv from "dotenv";

// Load environment variables
dotenv.config({ path: ".env.local" });

async function startWorker() {
  console.log("🚀 Starting Temporal Document Processing Worker...\n");

  // Validate environment variables
  const requiredEnvVars = [
    "TEMPORAL_ADDRESS",
    "TEMPORAL_NAMESPACE",
    "TEMPORAL_API_KEY",
    "TEMPORAL_TASK_QUEUE",
    "MONGODB_URI",
    "LLAMA_CLOUD_API_KEY",
    "OPENAI_API_KEY",
    "DOCS_BACKEND_API_KEY",
  ];

  const missing = requiredEnvVars.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    console.error("❌ Missing required environment variables:");
    missing.forEach((key) => console.error(`   - ${key}`));
    process.exit(1);
  }

  const address = process.env.TEMPORAL_ADDRESS!;
  const namespace = process.env.TEMPORAL_NAMESPACE!;
  const apiKey = process.env.TEMPORAL_API_KEY!;
  const taskQueue = process.env.TEMPORAL_TASK_QUEUE!;

  console.log("⚙️  Configuration:");
  console.log(`   Temporal Address: ${address}`);
  console.log(`   Namespace: ${namespace}`);
  console.log(`   Task Queue: ${taskQueue}`);
  console.log("");

  try {
    // Connect to Temporal Cloud with TLS and API key
    console.log("🔌 Connecting to Temporal Cloud...");
    const connection = await NativeConnection.connect({
      address,
      tls: true,
      apiKey,
    });
    console.log("✅ Connected to Temporal Cloud\n");

    // Create worker
    console.log("👷 Creating worker...");
    const worker = await Worker.create({
      connection,
      namespace,
      taskQueue,
      workflowsPath: require.resolve("./workflows/document-processing"),
      activities,
      maxConcurrentActivityTaskExecutions: 5, // Process up to 5 activities concurrently
      maxConcurrentWorkflowTaskExecutions: 10, // Handle up to 10 workflows concurrently
    });

    console.log("✅ Worker created\n");
    console.log("=" + "=".repeat(70));
    console.log("🎉 Worker is running and polling for tasks!");
    console.log("=" + "=".repeat(70));
    console.log("");
    console.log("📋 Worker Details:");
    console.log(`   Max Concurrent Activities: 5`);
    console.log(`   Max Concurrent Workflows: 10`);
    console.log(`   Activities Registered: 9`);
    console.log(`   Workflows Registered: DocumentProcessingWorkflow`);
    console.log("");
    console.log("Press Ctrl+C to stop the worker");
    console.log("");

    // Run worker
    await worker.run();
  } catch (error: any) {
    console.error("\n❌ Worker failed:", error);
    console.error("\nError details:", error.message);
    if (error.stack) {
      console.error("\nStack trace:", error.stack);
    }
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on("SIGINT", () => {
  console.log("\n\n🛑 Received SIGINT, shutting down gracefully...");
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("\n\n🛑 Received SIGTERM, shutting down gracefully...");
  process.exit(0);
});

// Start the worker
startWorker();
