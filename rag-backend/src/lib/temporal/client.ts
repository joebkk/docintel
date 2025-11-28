import { Connection, Client } from "@temporalio/client";

let client: Client | null = null;

/**
 * Get or create Temporal client (singleton pattern)
 * Connects to Temporal Cloud using environment variables
 */
export async function getTemporalClient(): Promise<Client> {
  if (!client) {
    const address = process.env.TEMPORAL_ADDRESS;
    const namespace = process.env.TEMPORAL_NAMESPACE;
    const apiKey = process.env.TEMPORAL_API_KEY;

    if (!address || !namespace || !apiKey) {
      throw new Error(
        "Missing required Temporal environment variables: TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, and TEMPORAL_API_KEY"
      );
    }

    console.log(`Connecting to Temporal: ${address} (namespace: ${namespace})`);

    // Create connection with TLS and API key for Temporal Cloud
    const connection = await Connection.connect({
      address,
      tls: true,
      apiKey,
    });

    // Then create client with connection and namespace
    client = new Client({
      connection,
      namespace,
    });

    console.log("✅ Temporal client connected");
  }

  return client;
}

/**
 * Close Temporal client connection (cleanup)
 */
export async function closeTemporalClient(): Promise<void> {
  if (client) {
    await client.connection.close();
    client = null;
    console.log("✅ Temporal client disconnected");
  }
}
