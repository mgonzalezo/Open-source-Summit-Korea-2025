#!/usr/bin/env node
/**
 * MCP SSE Bridge for Claude Desktop on Windows
 *
 * Bridges Claude Desktop (STDIO) to MCP Server (SSE)
 *
 * Usage: node mcp-sse-bridge-windows.js <SSE_ENDPOINT>
 * Example: node mcp-sse-bridge-windows.js http://52.198.28.44:30800/sse
 */

const https = require('https');
const http = require('http');
const { URL } = require('url');

// Parse command line arguments
const sseEndpoint = process.argv[2];
if (!sseEndpoint) {
  console.error('[Bridge] Error: SSE endpoint required');
  console.error('[Bridge] Usage: node mcp-sse-bridge-windows.js <SSE_ENDPOINT>');
  process.exit(1);
}

console.error(`[Bridge] Starting MCP SSE Bridge`);
console.error(`[Bridge] SSE Endpoint: ${sseEndpoint}`);

let sessionEndpoint = null;
let messageBuffer = [];

// Connect to SSE endpoint
function connectSSE() {
  console.error('[Bridge] Connecting to SSE server...');

  const url = new URL(sseEndpoint);
  const client = url.protocol === 'https:' ? https : http;

  const req = client.get(sseEndpoint, {
    headers: {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache'
    }
  }, (res) => {
    console.error(`[Bridge] Connected (${res.statusCode})`);

    let buffer = '';

    res.on('data', (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line

      let event = null;
      let data = null;

      for (const line of lines) {
        const trimmedLine = line.trim();

        if (line.startsWith('event:')) {
          event = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          data = line.substring(5).trim();
        } else if (trimmedLine === '' && event && data) {
          // Complete SSE message received
          console.error(`[Bridge] Received SSE event: ${event}`);

          if (event === 'endpoint') {
            sessionEndpoint = data;
            console.error(`[Bridge] Session endpoint: ${sessionEndpoint}`);
            // Send any buffered messages
            messageBuffer.forEach(msg => sendToMCPServer(msg));
            messageBuffer = [];
          } else if (event === 'message') {
            try {
              const message = JSON.parse(data);
              // Forward to Claude Desktop (stdout)
              console.log(JSON.stringify(message));
            } catch (err) {
              console.error(`[Bridge] Parse error:`, err.message);
            }
          }
          event = null;
          data = null;
        } else if (line.startsWith(':')) {
          // Ignore SSE comments (ping messages)
          continue;
        }
      }

      // Check if we have both event and data but haven't processed yet
      if (event && data && buffer === '') {
        console.error(`[Bridge] Processing pending event: ${event}`);

        if (event === 'endpoint') {
          sessionEndpoint = data;
          console.error(`[Bridge] Session endpoint: ${sessionEndpoint}`);
          messageBuffer.forEach(msg => sendToMCPServer(msg));
          messageBuffer = [];
        } else if (event === 'message') {
          try {
            const message = JSON.parse(data);
            console.log(JSON.stringify(message));
          } catch (err) {
            console.error(`[Bridge] Parse error:`, err.message);
          }
        }
        event = null;
        data = null;
      }
    });

    res.on('end', () => {
      console.error('[Bridge] SSE connection closed');
      process.exit(1);
    });
  });

  req.on('error', (err) => {
    console.error(`[Bridge] Connection error:`, err.message);
    process.exit(1);
  });
}

// Send message to MCP server
function sendToMCPServer(message) {
  if (!sessionEndpoint) {
    console.error('[Bridge] Buffering message (no session yet)');
    messageBuffer.push(message);
    return;
  }

  const url = new URL(sessionEndpoint, sseEndpoint);
  const client = url.protocol === 'https:' ? https : http;

  const postData = JSON.stringify(message);

  const options = {
    hostname: url.hostname,
    port: url.port,
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(postData)
    }
  };

  const req = client.request(options, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      if (res.statusCode !== 202 && res.statusCode !== 200) {
        console.error(`[Bridge] POST error (${res.statusCode}):`, data);
      }
    });
  });

  req.on('error', (err) => {
    console.error(`[Bridge] POST request error:`, err.message);
  });

  req.write(postData);
  req.end();
}

// Read from Claude Desktop (stdin)
let stdinBuffer = '';
process.stdin.setEncoding('utf8');

process.stdin.on('data', (chunk) => {
  stdinBuffer += chunk;
  const lines = stdinBuffer.split('\n');
  stdinBuffer = lines.pop(); // Keep incomplete line

  for (const line of lines) {
    if (line.trim()) {
      try {
        const message = JSON.parse(line);
        sendToMCPServer(message);
      } catch (err) {
        console.error(`[Bridge] Invalid JSON from stdin:`, err.message);
      }
    }
  }
});

process.stdin.on('end', () => {
  console.error('[Bridge] Stdin closed, exiting');
  process.exit(0);
});

// Handle process termination
process.on('SIGINT', () => {
  console.error('[Bridge] Interrupted, exiting');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('[Bridge] Terminated, exiting');
  process.exit(0);
});

// Start SSE connection
connectSSE();

console.error('[Bridge] Bridge ready');
