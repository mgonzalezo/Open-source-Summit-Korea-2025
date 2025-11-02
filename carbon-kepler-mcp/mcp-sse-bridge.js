#!/usr/bin/env node

/**
 * MCP SSE Bridge (Mac/Linux/Windows)
 *
 * Bridges STDIO (used by Claude Desktop) to SSE (Server-Sent Events)
 * allowing Claude Desktop to connect to remote MCP servers via SSE transport.
 *
 * Fixed version: Properly handles multi-line JSON in tool descriptions
 */

const https = require('https');
const http = require('http');

// SSE endpoint - pass as first argument
const SSE_ENDPOINT = process.argv[2] || 'http://localhost:30800/sse';

console.error('[Bridge] Starting MCP SSE Bridge');
console.error('[Bridge] SSE Endpoint:', SSE_ENDPOINT);

let sessionId = null;
let eventSource = null;
let buffer = [];

// Parse SSE endpoint
const url = new URL(SSE_ENDPOINT);
const client = url.protocol === 'https:' ? https : http;

// Connect to SSE server
console.error('[Bridge] Connecting to SSE server...');

const sseRequest = client.request(url, {
    method: 'GET',
    headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }
}, (res) => {
    console.error('[Bridge] Connected (' + res.statusCode + ')');

    let eventType = null;
    let dataLines = [];

    res.setEncoding('utf8');

    res.on('data', (chunk) => {
        const lines = chunk.toString().split('\n');

        for (const line of lines) {
            if (line.startsWith('event: ')) {
                eventType = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
                dataLines.push(line.substring(6));
            } else if (line === '' && eventType && dataLines.length > 0) {
                // Process complete event (SSE uses blank line as delimiter)
                const data = dataLines.join('\n').trim();

                if (eventType === 'endpoint') {
                    const match = data.match(/session_id=([^&]+)/);
                    if (match) {
                        sessionId = match[1];
                        console.error('[Bridge] Session endpoint:', data);
                        console.error('[Bridge] Session ID:', sessionId);
                        console.error('[Bridge] Bridge ready');

                        // Send any buffered messages
                        buffer.forEach(msg => sendToServer(msg));
                        buffer = [];
                    }
                } else if (eventType === 'message') {
                    // Forward message to stdout (Claude Desktop)
                    // Ensure proper JSON formatting
                    try {
                        // Validate it's proper JSON before forwarding
                        JSON.parse(data);
                        console.log(data);
                    } catch (e) {
                        console.error('[Bridge] Invalid JSON from server:', e.message);
                        console.error('[Bridge] Data:', data.substring(0, 200));
                    }
                }

                // Reset for next event
                eventType = null;
                dataLines = [];
            }
        }
    });

    res.on('end', () => {
        console.error('[Bridge] SSE connection closed');
        process.exit(0);
    });
});

sseRequest.on('error', (err) => {
    console.error('[Bridge] Connection error:', err.message);
    process.exit(1);
});

sseRequest.end();

// Read from stdin (Claude Desktop)
let stdinBuffer = '';
process.stdin.setEncoding('utf8');

process.stdin.on('data', (chunk) => {
    stdinBuffer += chunk.toString();

    // Process complete JSON-RPC messages (delimited by newlines)
    const lines = stdinBuffer.split('\n');
    stdinBuffer = lines.pop() || ''; // Keep incomplete line in buffer

    for (const line of lines) {
        const message = line.trim();
        if (message) {
            try {
                // Validate JSON before sending
                JSON.parse(message);

                if (sessionId) {
                    sendToServer(message);
                } else {
                    console.error('[Bridge] Buffering message (no session yet)');
                    buffer.push(message);
                }
            } catch (e) {
                console.error('[Bridge] Invalid JSON from client:', e.message);
            }
        }
    }
});

process.stdin.on('end', () => {
    console.error('[Bridge] Stdin closed, exiting');
    process.exit(0);
});

function sendToServer(message) {
    if (!sessionId) {
        console.error('[Bridge] No session ID yet, buffering');
        buffer.push(message);
        return;
    }

    const postData = message;
    const postUrl = new URL(`/messages/?session_id=${sessionId}`, SSE_ENDPOINT);

    const postRequest = client.request(postUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData, 'utf8')
        }
    }, (res) => {
        let responseData = '';
        res.setEncoding('utf8');

        res.on('data', (chunk) => {
            responseData += chunk;
        });

        res.on('end', () => {
            if (res.statusCode !== 202) {
                console.error('[Bridge] POST failed:', res.statusCode, responseData);
            }
        });
    });

    postRequest.on('error', (err) => {
        console.error('[Bridge] POST error:', err.message);
    });

    postRequest.write(postData, 'utf8');
    postRequest.end();
}
