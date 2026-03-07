# Nuwa AI Chat Channel for OpenClaw

This plugin integrates OpenClaw with the Nuwa AI system, allowing you to use Nuwa's conversational AI capabilities across all supported chat channels.

## Features

- Real-time communication with Nuwa AI via WebSocket
- Full compatibility with OpenClaw's channel architecture
- Automatic reconnection on connection loss
- Support for text messages and streaming responses
- Configurable WebSocket server URL

## Installation

1. Install dependencies:
```bash
npm install
```

2. Build the plugin:
```bash
npm run build
```

3. Add the plugin to OpenClaw's configuration

## Configuration

```json
{
  "channels": {
    "nuwa": {
      "websocketUrl": "ws://127.0.0.1:8766"
    }
  }
}
```

## Usage

### Sending Messages

Messages from any chat channel will be automatically forwarded to Nuwa AI. The AI's responses will be sent back to the original channel.

### WebSocket Protocol

The plugin communicates with Nuwa AI using a simple JSON protocol:

#### Sending Messages
```json
{
  "type": "text",
  "content": "Hello, Nuwa!"
}
```

#### Receiving Messages
```json
{
  "type": "stream_chunk",
  "content": "Hello! I'm Nuwa, your AI assistant."
}
```

```json
{
  "type": "active_message",
  "content": "I have something to tell you..."
}
```

## Compatibility

- OpenClaw v2.0+
- Nuwa AI v1.0+
- Node.js v16+

## Development

### Watch Mode
```bash
npm run watch
```

### Testing
```bash
npm test
```

## License

MIT