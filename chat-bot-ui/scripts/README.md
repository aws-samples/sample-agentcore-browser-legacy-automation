# WebSocket Testing Scripts

## test-websocket-connection.js

Tests WebSocket connections with proper reconnection logic and limits.

### Usage

```bash
# Test local connection
node chat-bot-ui/scripts/test-websocket-connection.js

# Test remote ALB / gateway connection
node chat-bot-ui/scripts/test-websocket-connection.js wss://<alb-dns>/ws
```

### What it tests

- Connection establishment
- Message sending/receiving
- Reconnection attempts (max 5)
- Exponential backoff delays
- Proper connection cleanup

### For ECS Fargate + ALB

Use WSS (secure WebSocket) for production:
```bash
node chat-bot-ui/scripts/test-websocket-connection.js wss://<alb-dns>/ws
```

### Environment Variables

Set WebSocket URL for your app:
```bash
export WEBSOCKET_URL="wss://<alb-dns>/ws"
npm run dev
```

The app will fail fast if no WebSocket URL is configured (no hardcoded fallbacks).
