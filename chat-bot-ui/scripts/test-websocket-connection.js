#!/usr/bin/env node
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0


/**
 * WebSocket Connection Test Script
 *
 * This script tests WebSocket connections to verify:
 * 1. Connection establishment
 * 2. Reconnection logic with proper limits
 * 3. Remote server connectivity
 *
 * Usage:
 *   node test-websocket-connection.js [websocket-url]
 *
 * Examples:
 *   node test-websocket-connection.js ws://localhost:8081
 *   node test-websocket-connection.js wss://your-alb-domain.com/ws
 */

const WebSocket = require('ws');

// Configuration
const DEFAULT_URL = 'ws://localhost:8081';
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 1000; // 1 second base delay

class WebSocketTester {
  constructor(url) {
    this.url = url;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = MAX_RECONNECT_ATTEMPTS;
    this.ws = null;
    this.isConnected = false;
    this.testStartTime = Date.now();
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const elapsed = ((Date.now() - this.testStartTime) / 1000).toFixed(2);
    const prefix = {
      'info': '🔌',
      'success': '✅',
      'error': '❌',
      'warning': '⚠️',
      'reconnect': '🔄'
    }[type] || 'ℹ️';

    console.log(`[${elapsed}s] ${prefix} ${message}`);
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.log(`Attempting connection to: ${this.url}`);

      try {
        this.ws = new WebSocket(this.url);

        this.ws.on('open', () => {
          this.isConnected = true;
          this.reconnectAttempts = 0; // Reset on successful connection
          this.log('Connection established successfully!', 'success');

          // Send a test message
          const testMessage = {
            type: 'TEST_CONNECTION',
            timestamp: new Date().toISOString(),
            message: 'Hello from WebSocket test script'
          };

          this.ws.send(JSON.stringify(testMessage));
          this.log('Test message sent', 'info');

          resolve();
        });

        this.ws.on('message', (data) => {
          try {
            const message = JSON.parse(data.toString());
            this.log(`Received message: ${JSON.stringify(message)}`, 'success');
          } catch (e) {
            this.log(`Received raw message: ${data.toString()}`, 'info');
          }
        });

        this.ws.on('error', (error) => {
          this.log(`Connection error: ${error.message}`, 'error');
          this.isConnected = false;
          reject(error);
        });

        this.ws.on('close', (code, reason) => {
          this.isConnected = false;
          this.log(`Connection closed: code=${code}, reason=${reason || 'No reason provided'}`, 'warning');

          // Trigger reconnection if not a clean close
          if (code !== 1000) {
            this.handleConnectionDrop();
          }
        });

      } catch (error) {
        this.log(`Failed to create WebSocket: ${error.message}`, 'error');
        reject(error);
      }
    });
  }

  async reconnect() {
    return new Promise((resolve, reject) => {
      this.reconnectAttempts++;

      if (this.reconnectAttempts > this.maxReconnectAttempts) {
        this.log(`Max reconnection attempts (${this.maxReconnectAttempts}) exceeded`, 'error');
        reject(new Error('Max reconnection attempts exceeded'));
        return;
      }

      // Calculate exponential backoff delay
      const delay = Math.min(RECONNECT_DELAY * Math.pow(2, this.reconnectAttempts - 1), 30000);

      this.log(`Reconnecting in ${delay}ms... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'reconnect');

      setTimeout(async () => {
        try {
          await this.connect();
          this.log('Reconnection successful!', 'success');
          resolve();
        } catch (error) {
          this.log(`Reconnection attempt ${this.reconnectAttempts} failed: ${error.message}`, 'error');

          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect().then(resolve).catch(reject);
          } else {
            reject(error);
          }
        }
      }, delay);
    });
  }

  handleConnectionDrop() {
    this.log('Connection dropped, attempting to reconnect...', 'warning');
    this.reconnect().catch(error => {
      this.log(`All reconnection attempts failed: ${error.message}`, 'error');
    });
  }

  close() {
    if (this.ws) {
      this.log('Closing connection...', 'info');
      this.ws.close(1000, 'Test completed');
    }
  }

  async runTest(duration = 10000) {
    this.log('Starting WebSocket connection test...', 'info');

    try {
      await this.connect();

      // Keep connection alive for specified duration
      this.log(`Keeping connection alive for ${duration/1000} seconds...`, 'info');

      await new Promise(resolve => setTimeout(resolve, duration));

      this.log('Test completed successfully!', 'success');

    } catch (error) {
      this.log(`Test failed: ${error.message}`, 'error');
      throw error;
    } finally {
      this.close();
    }
  }
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  const websocketUrl = args[0] || DEFAULT_URL;

  console.log('🧪 WebSocket Connection Test');
  console.log('============================');
  console.log(`Target URL: ${websocketUrl}`);
  console.log(`Max Reconnect Attempts: ${MAX_RECONNECT_ATTEMPTS}`);
  console.log('');

  const tester = new WebSocketTester(websocketUrl);

  try {
    await tester.runTest(10000); // Run test for 10 seconds
    console.log('\n✅ All tests passed!');
    process.exit(0);
  } catch (error) {
    console.log(`\n❌ Test failed: ${error.message}`);
    process.exit(1);
  }
}

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n🛑 Test interrupted by user');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Test terminated');
  process.exit(0);
});

if (require.main === module) {
  main().catch(error => {
    console.error('❌ Unexpected error:', error);
    process.exit(1);
  });
}

module.exports = { WebSocketTester };
