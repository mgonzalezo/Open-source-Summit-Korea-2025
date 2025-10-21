#!/usr/bin/env node

/**
 * MCP SSE-to-Stdio Bridge
 *
 * This bridge connects Claude Desktop (which uses stdio) to a remote
 * MCP server using SSE (Server-Sent Events) transport.
 *
 * Usage: node mcp-sse-bridge.js <SSE_URL>
 * Example: node mcp-sse-bridge.js http://57.182.90.243:30800/sse
 */

const http = require('http');
const https = require('https');

const SSE_URL = process.argv[2] || 'http://57.182.90.243:30800/sse';

console.error(`[MCP Bridge] Starting bridge to ${SSE_URL}`);

// Parse URL to determine protocol
const url = new URL(SSE_URL);
const client = url.protocol === 'https:' ? https : http;

let messageId = 0;
let sessionEndpoint = null;

// Connect to SSE endpoint
console.error('[MCP Bridge] Connecting to SSE server...');

const req = client.get(SSE_URL, (res) => {
  if (res.statusCode !== 200) {
    console.error(`[MCP Bridge] Server returned status ${res.statusCode}`);
    process.exit(1);
  }

  console.error('[MCP Bridge] Connected to SSE server');

  let buffer = '';

  res.on('data', (chunk) => {
    buffer += chunk.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('event: endpoint')) {
        // Next line should have the session endpoint
        continue;
      }

      if (line.startsWith('data: ')) {
        const data = line.substring(6);

        // Check if this is the session endpoint
        if (data.startsWith('/messages/')) {
          sessionEndpoint = data;
          console.error(`[MCP Bridge] Session endpoint: ${sessionEndpoint}`);

          // Send initialize request
          sendInitialize();
          continue;
        }

        // Try to parse as JSON
        try {
          const jsonData = JSON.parse(data);
          // Forward JSON-RPC responses to stdout
          process.stdout.write(JSON.stringify(jsonData) + '\n');
        } catch (e) {
          // Not JSON, might be ping or other message
          console.error(`[MCP Bridge] Non-JSON data: ${data.substring(0, 50)}...`);
        }
      }

      if (line.startsWith(': ping')) {
        console.error('[MCP Bridge] Received ping');
      }
    }
  });

  res.on('end', () => {
    console.error('[MCP Bridge] SSE connection closed');
    process.exit(0);
  });

  res.on('error', (err) => {
    console.error(`[MCP Bridge] SSE error: ${err.message}`);
    process.exit(1);
  });
});

req.on('error', (err) => {
  console.error(`[MCP Bridge] Connection error: ${err.message}`);
  process.exit(1);
});

// Send initialize message to MCP server
function sendInitialize() {
  if (!sessionEndpoint) {
    console.error('[MCP Bridge] Cannot initialize: no session endpoint');
    return;
  }

  const initMessage = {
    jsonrpc: '2.0',
    id: messageId++,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'claude-desktop-bridge',
        version: '1.0.0'
      }
    }
  };

  sendToServer(initMessage);
}

// Send JSON-RPC message to SSE server via POST
function sendToServer(message) {
  if (!sessionEndpoint) {
    console.error('[MCP Bridge] Cannot send: no session endpoint');
    return;
  }

  const payload = JSON.stringify(message);

  console.error(`[MCP Bridge] Sending to ${url.protocol}//${url.host}${sessionEndpoint}: ${payload.substring(0, 100)}...`);

  // Build the full URL for the POST request
  const postUrl = new URL(sessionEndpoint, `${url.protocol}//${url.host}`);

  const options = {
    hostname: postUrl.hostname,
    port: postUrl.port,
    path: postUrl.pathname + postUrl.search,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  const postReq = client.request(options, (res) => {
    let responseData = '';

    res.on('data', (chunk) => {
      responseData += chunk;
    });

    res.on('end', () => {
      console.error(`[MCP Bridge] POST response (${res.statusCode}): ${responseData.substring(0, 100)}`);
    });
  });

  postReq.on('error', (err) => {
    console.error(`[MCP Bridge] POST error: ${err.message}`);
  });

  postReq.write(payload);
  postReq.end();
}

// Handle stdin from Claude Desktop
let stdinBuffer = '';

process.stdin.on('data', (chunk) => {
  stdinBuffer += chunk.toString();

  // Process complete JSON-RPC messages (newline-delimited)
  const lines = stdinBuffer.split('\n');
  stdinBuffer = lines.pop(); // Keep incomplete line

  for (const line of lines) {
    if (!line.trim()) continue;

    try {
      const message = JSON.parse(line);
      console.error(`[MCP Bridge] Received from Claude Desktop: ${JSON.stringify(message).substring(0, 100)}...`);
      sendToServer(message);
    } catch (e) {
      console.error(`[MCP Bridge] Failed to parse stdin: ${e.message}`);
    }
  }
});

process.stdin.on('end', () => {
  console.error('[MCP Bridge] Stdin closed');
  process.exit(0);
});

// Handle shutdown signals
process.on('SIGINT', () => {
  console.error('[MCP Bridge] Shutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('[MCP Bridge] Shutting down...');
  process.exit(0);
});

console.error('[MCP Bridge] Bridge initialized, waiting for session endpoint...');
