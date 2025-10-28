#!/usr/bin/env node

/**
 * MCP SSE Bridge for Windows
 * 
 * Bridges STDIO (used by Claude Desktop) to SSE (Server-Sent Events)
 * allowing Claude Desktop to connect to remote MCP servers via SSE transport.
 */

const https = require('https');
const http = require('http');

// SSE endpoint - UPDATE THIS to your current EC2 IP
const SSE_ENDPOINT = process.argv[2] || 'http://3.115.147.150:30800/sse';

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
    let data = '';

    res.on('data', (chunk) => {
        const lines = chunk.toString().split('\n');
        
        for (const line of lines) {
            if (line.startsWith('event: ')) {
                eventType = line.substring(7).trim();
            } else if (line.startsWith('data: ')) {
                data = line.substring(6).trim();
            } else if (line === '' && eventType && data) {
                // Process complete event
                if (eventType === 'endpoint') {
                    sessionId = data.match(/session_id=([^&]+)/)[1];
                    console.error('[Bridge] Session endpoint:', data);
                    console.error('[Bridge] Bridge ready');
                    
                    // Send any buffered messages
                    buffer.forEach(msg => sendToServer(msg));
                    buffer = [];
                } else if (eventType === 'message') {
                    // Forward message to stdout (Claude Desktop)
                    console.log(data);
                }
                
                eventType = null;
                data = '';
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
process.stdin.on('data', (chunk) => {
    stdinBuffer += chunk.toString();
    
    // Try to parse complete JSON messages
    let startIdx = 0;
    for (let i = 0; i < stdinBuffer.length; i++) {
        if (stdinBuffer[i] === '\n') {
            const message = stdinBuffer.substring(startIdx, i).trim();
            if (message) {
                if (sessionId) {
                    sendToServer(message);
                } else {
                    console.error('[Bridge] Buffering message (no session yet)');
                    buffer.push(message);
                }
            }
            startIdx = i + 1;
        }
    }
    stdinBuffer = stdinBuffer.substring(startIdx);
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
            'Content-Length': Buffer.byteLength(postData)
        }
    }, (res) => {
        let responseData = '';
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

    postRequest.write(postData);
    postRequest.end();
}
